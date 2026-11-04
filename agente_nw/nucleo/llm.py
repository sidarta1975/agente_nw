from __future__ import annotations

import json
import sqlite3
import time
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from agente_nw.nucleo.database.queries import fila_revisao
from agente_nw.nucleo.modelos.configuracao import Roteamento, TarefaRoteamento
from agente_nw.nucleo.modelos.proveniencia import Proveniencia

EsquemaT = TypeVar("EsquemaT", bound=BaseModel)

_SEED = 42
_INTERVALOS_BACKOFF_TRANSPORTE: tuple[float, ...] = (2, 4, 8, 16)
"""Erro de conexão/timeout/HTTP contra o provedor — no caso do Ollama, servidor local,
compartilhado, que pode estar carregando ou descarregando um modelo no momento exato da
chamada. Camada separada da nova tentativa por temperatura, que é só para falha de conteúdo
(JSON inválido/geração degenerada)."""


class _GeracaoDegenerada(Exception):
    """O provedor abortou a geração (ex.: "prediction aborted, token repeat limit reached",
    quando o modelo entra num loop de repetição). É falha da tentativa, não da rede —
    tratada em ``gerar_json`` igual a JSON inválido: conta para a nova tentativa e,
    esgotada, vai para ``fila_revisao`` em vez de derrubar o chamador. Quem detecta é o
    ``_chamar`` de cada provedor, porque a forma de dizer isso é específica dele."""


class FalhaJsonInvalido(RuntimeError):
    def __init__(self, tarefa: str, fila_revisao_id: int, erro: str) -> None:
        super().__init__(
            f"tarefa '{tarefa}' falhou a validação de JSON (fila_revisao id={fila_revisao_id}): {erro}"
        )
        self.tarefa = tarefa
        self.fila_revisao_id = fila_revisao_id
        self.erro = erro


class _ClienteLLMBase(ABC):
    """Orquestração de `gerar_json` que não depende de provedor (brief 074): nova tentativa por
    temperatura, backoff de transporte, validação do JSON contra o esquema Pydantic, log da chamada
    e `fila_revisao` quando tudo se esgota. Cada provedor implementa só `_chamar`.

    Não é contrato público: os módulos do produto recebem um cliente concreto (`ClienteOllama` e,
    a partir do brief 075, os clientes de API) e usam `gerar_json`/`proveniencia`/`embeddar`."""

    def __init__(
        self,
        conexao_bd: sqlite3.Connection,
        roteamento: Roteamento,
        caminho_log: Path,
    ) -> None:
        self._conexao = conexao_bd
        self._roteamento = roteamento
        self._caminho_log = caminho_log

    @abstractmethod
    def _chamar(
        self,
        tarefa: TarefaRoteamento,
        prompt: str,
        temperature: float,
        imagens: list[str] | None,
        esquema: type[BaseModel],
    ) -> str:
        """Uma chamada ao provedor, sem nova tentativa: devolve o texto bruto da resposta.
        Levanta `_GeracaoDegenerada` quando o provedor avisa que a geração degenerou, e
        `httpx.HTTPStatusError`/`httpx.RequestError` em falha de transporte — o backoff e a nova
        tentativa por temperatura ficam aqui na base, iguais para todo provedor.

        `esquema` está na assinatura para os clientes de API forçarem o formato de saída com
        `esquema.model_json_schema()`; o Ollama recebe o formato pelo `format` da tarefa e o ignora."""

    def proveniencia(self, tarefa_nome: str, versao_prompt: str | None = None) -> Proveniencia:
        """Perfil ativo, modelo da tarefa e versão do prompt — o que `gerar_json` usa e registra no log,
        para quem grava o resultado da geração (brief 066)."""
        return Proveniencia(
            modelo=self._tarefa(tarefa_nome).modelo,
            perfil=self._roteamento.perfil_ativo,
            prompt_versao=versao_prompt,
        )

    def _registrar_log_chamada(
        self,
        tarefa_nome: str,
        tentativas_usadas: int,
        sucesso: bool,
        falhas_transporte: int,
        proveniencia: Proveniencia,
        inicio: float,
    ) -> None:
        try:
            self._caminho_log.parent.mkdir(parents=True, exist_ok=True)
            linha = json.dumps(
                {
                    "tarefa": tarefa_nome,
                    "tentativas_usadas": tentativas_usadas,
                    "sucesso": sucesso,
                    "falhas_transporte": falhas_transporte,
                    "quando": datetime.now(UTC).isoformat(),
                    "perfil": proveniencia.perfil,
                    "modelo": proveniencia.modelo,
                    "versao_prompt": proveniencia.prompt_versao,
                    "latencia_ms": round((time.monotonic() - inicio) * 1000),
                },
                ensure_ascii=False,
            )
            with self._caminho_log.open("a", encoding="utf-8") as arquivo:
                arquivo.write(linha + "\n")
        except Exception:
            pass

    def _tarefa(self, nome: str) -> TarefaRoteamento:
        perfil = self._roteamento.perfis[self._roteamento.perfil_ativo]
        if nome not in perfil.tarefas:
            raise KeyError(
                f"tarefa '{nome}' não está declarada no perfil '{self._roteamento.perfil_ativo}' "
                "de config/llm_routing.yaml"
            )
        return perfil.tarefas[nome]

    def _chamar_com_backoff(
        self,
        tarefa: TarefaRoteamento,
        prompt: str,
        temperature: float,
        imagens: list[str] | None,
        esquema: type[BaseModel],
    ) -> tuple[str, int]:
        """Nova tentativa só para erro de transporte (conexão, timeout, HTTP) — não para geração
        degenerada, que é falha de tentativa e segue para a nova tentativa por temperatura."""
        ultimo_erro: httpx.HTTPStatusError | httpx.RequestError | None = None
        falhas = 0
        for espera in (0.0, *_INTERVALOS_BACKOFF_TRANSPORTE):
            if espera:
                time.sleep(espera)
            try:
                return self._chamar(tarefa, prompt, temperature, imagens, esquema), falhas
            except _GeracaoDegenerada:
                raise
            except (httpx.HTTPStatusError, httpx.RequestError) as erro:
                falhas += 1
                ultimo_erro = erro
        assert ultimo_erro is not None
        raise ultimo_erro

    def _ir_para_fila_revisao(self, tarefa_nome: str, prompt: str, erro: str) -> FalhaJsonInvalido:
        agora = datetime.now(UTC).isoformat()
        fila_id = fila_revisao.inserir(self._conexao, tarefa_nome, prompt, erro, agora)
        self._conexao.commit()
        return FalhaJsonInvalido(tarefa_nome, fila_id, erro)

    def gerar_json(
        self,
        tarefa_nome: str,
        prompt: str,
        esquema: type[EsquemaT],
        imagens: list[str] | None = None,
        versao_prompt: str | None = None,
    ) -> EsquemaT:
        """`imagens`: imagens em base64 para modelos com visão (tarefa `descrever_imagem`).
        `versao_prompt`: `VERSAO` do módulo de prompt (brief 066); só vai para o log. A latência
        registrada é a da chamada inteira, com novas tentativas e esperas do backoff."""
        inicio = time.monotonic()
        tarefa = self._tarefa(tarefa_nome)
        proveniencia = self.proveniencia(tarefa_nome, versao_prompt)
        nova_tentativa = self._roteamento.perfis[self._roteamento.perfil_ativo].nova_tentativa

        ultimo_erro = ""
        falhas_transporte_total = 0
        tentativas = (tarefa.temperature, nova_tentativa.temperature)
        for indice, temperatura in enumerate(tentativas, start=1):
            try:
                texto, falhas_transporte = self._chamar_com_backoff(
                    tarefa, prompt, temperatura, imagens, esquema
                )
            except (httpx.HTTPStatusError, httpx.RequestError) as erro:
                falhas_transporte_total += len(_INTERVALOS_BACKOFF_TRANSPORTE) + 1
                self._registrar_log_chamada(
                    tarefa_nome, indice, False, falhas_transporte_total, proveniencia, inicio
                )
                raise self._ir_para_fila_revisao(tarefa_nome, prompt, str(erro)) from erro
            except _GeracaoDegenerada as erro:
                ultimo_erro = str(erro)
                continue

            falhas_transporte_total += falhas_transporte
            try:
                bruto = json.loads(texto)
                resultado = esquema.model_validate(bruto)
                self._registrar_log_chamada(
                    tarefa_nome, indice, True, falhas_transporte_total, proveniencia, inicio
                )
                return resultado
            except (json.JSONDecodeError, ValidationError) as erro:
                ultimo_erro = str(erro)

        self._registrar_log_chamada(
            tarefa_nome, len(tentativas), False, falhas_transporte_total, proveniencia, inicio
        )
        raise self._ir_para_fila_revisao(tarefa_nome, prompt, ultimo_erro)


class ClienteOllama(_ClienteLLMBase):
    def __init__(
        self,
        http_client: httpx.Client,
        conexao_bd: sqlite3.Connection,
        roteamento: Roteamento,
        ollama_url: str,
        caminho_log: Path,
    ) -> None:
        super().__init__(conexao_bd, roteamento, caminho_log)
        self._http = http_client
        self._ollama_url = ollama_url

    @property
    def modelo_embedding(self) -> str:
        """Modelo de embedding do perfil ativo — gravado com cada centróide e conferido na leitura
        (brief 066): vetor de outro modelo é tratado como ausente."""
        return self._roteamento.perfis[self._roteamento.perfil_ativo].embeddings.modelo

    def _chamar(
        self,
        tarefa: TarefaRoteamento,
        prompt: str,
        temperature: float,
        imagens: list[str] | None,
        esquema: type[BaseModel],
    ) -> str:
        """`esquema` não é usado: o formato de saída do Ollama vem do `format` da tarefa
        (a string `"json"` do YAML), não de um esquema enviado no payload."""
        corpo: dict[str, object] = {
            "model": tarefa.modelo,
            "prompt": prompt,
            "format": tarefa.format,
            "stream": False,
            "options": {
                "num_ctx": tarefa.num_ctx,
                "temperature": temperature,
                "seed": _SEED,
                "num_predict": tarefa.num_predict,
            },
        }
        if imagens:
            corpo["images"] = imagens
        if self._roteamento.perfis[self._roteamento.perfil_ativo].enviar_think:
            corpo["think"] = tarefa.think
        resposta = self._http.post(f"{self._ollama_url}/api/generate", json=corpo)
        if resposta.status_code == 500:
            try:
                mensagem_erro = str(resposta.json().get("error", ""))
            except Exception:
                mensagem_erro = ""
            if "token repeat limit" in mensagem_erro:
                raise _GeracaoDegenerada(mensagem_erro)
        resposta.raise_for_status()
        dados: dict[str, object] = resposta.json()
        texto = dados["response"]
        assert isinstance(texto, str)
        return texto

    def embeddar(self, textos: list[str]) -> list[list[float]]:
        perfil = self._roteamento.perfis[self._roteamento.perfil_ativo]
        corpo = {"model": perfil.embeddings.modelo, "input": textos}
        resposta = self._http.post(f"{self._ollama_url}/api/embed", json=corpo)
        resposta.raise_for_status()
        dados: dict[str, object] = resposta.json()
        vetores_brutos = dados["embeddings"]
        assert isinstance(vetores_brutos, list)
        vetores: list[list[float]] = [[float(valor) for valor in vetor] for vetor in vetores_brutos]

        for vetor in vetores:
            if len(vetor) != 1024:
                raise ValueError(f"embedding com {len(vetor)} posições, esperado 1024")

        return vetores
