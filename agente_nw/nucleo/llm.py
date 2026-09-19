from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from agente_nw.nucleo.database.queries import fila_revisao
from agente_nw.nucleo.modelos.configuracao import Roteamento, TarefaRoteamento

EsquemaT = TypeVar("EsquemaT", bound=BaseModel)


class _GeracaoDegenerada(Exception):
    """O Ollama abortou a geração (ex.: "prediction aborted, token repeat limit reached",
    quando o modelo entra num loop de repetição). É falha da tentativa, não da rede —
    tratada em ``gerar_json`` igual a JSON inválido: conta para a nova tentativa e,
    esgotada, vai para ``fila_revisao`` em vez de derrubar o chamador."""


class FalhaJsonInvalido(RuntimeError):
    def __init__(self, tarefa: str, fila_revisao_id: int, erro: str) -> None:
        super().__init__(
            f"tarefa '{tarefa}' falhou a validação de JSON (fila_revisao id={fila_revisao_id}): {erro}"
        )
        self.tarefa = tarefa
        self.fila_revisao_id = fila_revisao_id
        self.erro = erro


class ClienteOllama:
    def __init__(
        self,
        http_client: httpx.Client,
        conexao_bd: sqlite3.Connection,
        roteamento: Roteamento,
        ollama_url: str,
        caminho_log: Path,
    ) -> None:
        self._http = http_client
        self._conexao = conexao_bd
        self._roteamento = roteamento
        self._ollama_url = ollama_url
        self._caminho_log = caminho_log

    def _registrar_log_chamada(self, tarefa_nome: str, tentativas_usadas: int, sucesso: bool) -> None:
        try:
            self._caminho_log.parent.mkdir(parents=True, exist_ok=True)
            linha = json.dumps(
                {
                    "tarefa": tarefa_nome,
                    "tentativas_usadas": tentativas_usadas,
                    "sucesso": sucesso,
                    "quando": datetime.now(UTC).isoformat(),
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

    def _chamar_generate(self, tarefa: TarefaRoteamento, prompt: str, temperature: float) -> str:
        corpo = {
            "model": tarefa.modelo,
            "prompt": prompt,
            "format": tarefa.format,
            "think": tarefa.think,
            "stream": False,
            "options": {"num_ctx": tarefa.num_ctx, "temperature": temperature},
        }
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

    def gerar_json(self, tarefa_nome: str, prompt: str, esquema: type[EsquemaT]) -> EsquemaT:
        tarefa = self._tarefa(tarefa_nome)
        nova_tentativa = self._roteamento.perfis[self._roteamento.perfil_ativo].nova_tentativa

        ultimo_erro = ""
        tentativas = (tarefa.temperature, nova_tentativa.temperature)
        for indice, temperatura in enumerate(tentativas, start=1):
            try:
                texto = self._chamar_generate(tarefa, prompt, temperatura)
                bruto = json.loads(texto)
                resultado = esquema.model_validate(bruto)
                self._registrar_log_chamada(tarefa_nome, indice, True)
                return resultado
            except (json.JSONDecodeError, ValidationError, _GeracaoDegenerada) as erro:
                ultimo_erro = str(erro)

        self._registrar_log_chamada(tarefa_nome, len(tentativas), False)
        agora = datetime.now(UTC).isoformat()
        fila_id = fila_revisao.inserir(self._conexao, tarefa_nome, prompt, ultimo_erro, agora)
        self._conexao.commit()
        raise FalhaJsonInvalido(tarefa_nome, fila_id, ultimo_erro)

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
