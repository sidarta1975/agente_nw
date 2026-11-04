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


_MEDIA_TYPE_IMAGEM = "image/jpeg"
"""As imagens publicadas chegam à tarefa `descrever_imagem` só como base64: `ImagemCapturada.mime`
guarda o `content-type` real que a extensão leu, mas `coleta/capturas/imagens.py` passa apenas
`dados_base64` para `gerar_json`. Sem o mime real chegando até aqui, os clientes de API assumem
`image/jpeg` (brief 075, item 3.2). O Ollama não precisa disso: aceita a base64 sem rótulo."""


class _ClienteApiBase(_ClienteLLMBase):
    """O que os três clientes de API têm igual (brief 075): a chave, o modelo único do provedor e os
    embeddings por composição com o `ClienteOllama` local. Cada provedor implementa só `_chamar`.

    Fica numa base privada em vez de repetido três vezes pelo mesmo motivo do brief 074: a
    composição do item 3.5 e a proveniência são idênticas nos três, e código igual copiado é o que
    aquele brief existiu para acabar."""

    def __init__(
        self,
        http_client: httpx.Client,
        conexao_bd: sqlite3.Connection,
        roteamento: Roteamento,
        chave: str,
        modelo: str,
        caminho_log: Path,
        cliente_embeddings: ClienteOllama,
    ) -> None:
        super().__init__(conexao_bd, roteamento, caminho_log)
        self._http = http_client
        self._chave = chave
        self._modelo = modelo
        self._cliente_embeddings = cliente_embeddings

    def proveniencia(self, tarefa_nome: str, versao_prompt: str | None = None) -> Proveniencia:
        """O modelo registrado é o do provedor de API, não o do `llm_routing.yaml` — é por este
        campo, no `chamadas_llm.jsonl`, que se confere qual provedor atendeu a chamada."""
        return Proveniencia(
            modelo=self._modelo,
            perfil=self._roteamento.perfil_ativo,
            prompt_versao=versao_prompt,
        )

    @property
    def modelo_embedding(self) -> str:
        """Repasse: embeddings são sempre do Ollama local, qualquer que seja o provedor de geração
        (brief 075, item 3.5) — a Anthropic não tem endpoint de embedding e trocar de modelo
        invalidaria todo centróide já gravado (brief 066)."""
        return self._cliente_embeddings.modelo_embedding

    def embeddar(self, textos: list[str]) -> list[list[float]]:
        """Repasse ao `ClienteOllama` injetado; nunca uma reimplementação (brief 075, item 3.5)."""
        return self._cliente_embeddings.embeddar(textos)


class ClienteAnthropic(_ClienteApiBase):
    """`POST /v1/messages`. O esquema é forçado por uma tool única, obrigatória por `tool_choice`:
    a resposta vem no bloco `tool_use`, já como dict conferido contra o `input_schema`."""

    _URL = "https://api.anthropic.com/v1/messages"
    _VERSAO_API = "2023-06-01"
    _NOME_TOOL = "responder"

    def _chamar(
        self,
        tarefa: TarefaRoteamento,
        prompt: str,
        temperature: float,
        imagens: list[str] | None,
        esquema: type[BaseModel],
    ) -> str:
        conteudo: list[dict[str, object]] = [
            {
                "type": "image",
                "source": {"type": "base64", "media_type": _MEDIA_TYPE_IMAGEM, "data": imagem},
            }
            for imagem in imagens or []
        ]
        conteudo.append({"type": "text", "text": prompt})
        corpo: dict[str, object] = {
            "model": self._modelo,
            "max_tokens": tarefa.num_predict,
            "temperature": temperature,
            "tools": [
                {
                    "name": self._NOME_TOOL,
                    "description": "Devolve a resposta da tarefa no formato pedido.",
                    "input_schema": esquema.model_json_schema(),
                }
            ],
            "tool_choice": {"type": "tool", "name": self._NOME_TOOL},
            "messages": [{"role": "user", "content": conteudo}],
        }
        resposta = self._http.post(
            self._URL,
            json=corpo,
            headers={
                "x-api-key": self._chave,
                "anthropic-version": self._VERSAO_API,
                "content-type": "application/json",
            },
        )
        resposta.raise_for_status()
        return _texto_da_resposta_anthropic(resposta.json())


class ClienteGemini(_ClienteApiBase):
    """`POST /v1beta/models/{modelo}:generateContent`. O esquema é forçado por
    `generationConfig.response_schema`, com `response_mime_type: application/json`."""

    _URL_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

    def _chamar(
        self,
        tarefa: TarefaRoteamento,
        prompt: str,
        temperature: float,
        imagens: list[str] | None,
        esquema: type[BaseModel],
    ) -> str:
        partes: list[dict[str, object]] = [
            {"inlineData": {"mimeType": _MEDIA_TYPE_IMAGEM, "data": imagem}} for imagem in imagens or []
        ]
        partes.append({"text": prompt})
        corpo: dict[str, object] = {
            "contents": [{"role": "user", "parts": partes}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": tarefa.num_predict,
                "response_mime_type": "application/json",
                "response_schema": esquema.model_json_schema(),
            },
        }
        resposta = self._http.post(
            f"{self._URL_BASE}/{self._modelo}:generateContent",
            json=corpo,
            # A chave vai no header, nunca em `?key=`: `str(httpx.HTTPStatusError)` carrega a URL e
            # `_ir_para_fila_revisao` grava esse texto no banco — chave na URL viraria chave gravada.
            headers={"x-goog-api-key": self._chave, "content-type": "application/json"},
        )
        resposta.raise_for_status()
        return _texto_da_resposta_gemini(resposta.json())


class ClienteOpenAI(_ClienteApiBase):
    """`POST /v1/chat/completions`. O esquema é forçado por
    `response_format: {"type": "json_schema", ...}`; a resposta já vem como string JSON."""

    _URL = "https://api.openai.com/v1/chat/completions"

    def _chamar(
        self,
        tarefa: TarefaRoteamento,
        prompt: str,
        temperature: float,
        imagens: list[str] | None,
        esquema: type[BaseModel],
    ) -> str:
        conteudo: list[dict[str, object]] = [{"type": "text", "text": prompt}]
        conteudo.extend(
            {
                "type": "image_url",
                "image_url": {"url": f"data:{_MEDIA_TYPE_IMAGEM};base64,{imagem}"},
            }
            for imagem in imagens or []
        )
        corpo: dict[str, object] = {
            "model": self._modelo,
            "max_tokens": tarefa.num_predict,
            "temperature": temperature,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": esquema.__name__,
                    "schema": esquema.model_json_schema(),
                    "strict": True,
                },
            },
            "messages": [{"role": "user", "content": conteudo}],
        }
        resposta = self._http.post(
            self._URL,
            json=corpo,
            headers={
                "Authorization": f"Bearer {self._chave}",
                "content-type": "application/json",
            },
        )
        resposta.raise_for_status()
        return _texto_da_resposta_openai(resposta.json())


def _texto_da_resposta_anthropic(dados: object) -> str:
    """O bloco `tool_use` reserializado para texto, para a base fazer o mesmo `json.loads` que faz
    com o Ollama. Sem bloco `tool_use`, devolve o texto que vier (ou vazio): resposta 200 sem o que
    se pediu é falha de **conteúdo**, e quem trata é `gerar_json` — nova tentativa por temperatura
    e, esgotada, `fila_revisao`. Nenhuma exceção nova escapa daqui (armadilha do brief 067)."""
    blocos = dados.get("content", []) if isinstance(dados, dict) else []
    if not isinstance(blocos, list):
        return ""
    for bloco in blocos:
        if isinstance(bloco, dict) and bloco.get("type") == "tool_use":
            return json.dumps(bloco.get("input", {}), ensure_ascii=False)
    textos = [
        str(bloco.get("text", ""))
        for bloco in blocos
        if isinstance(bloco, dict) and bloco.get("type") == "text"
    ]
    return "".join(textos)


def _texto_da_resposta_gemini(dados: object) -> str:
    """`candidates[0].content.parts[*].text`. Resposta fora dessa forma devolve vazio, que a base
    trata como conteúdo inválido — ver `_texto_da_resposta_anthropic`."""
    if not isinstance(dados, dict):
        return ""
    candidatos = dados.get("candidates")
    if not isinstance(candidatos, list) or not candidatos:
        return ""
    primeiro = candidatos[0]
    conteudo = primeiro.get("content") if isinstance(primeiro, dict) else None
    partes = conteudo.get("parts") if isinstance(conteudo, dict) else None
    if not isinstance(partes, list):
        return ""
    return "".join(str(parte.get("text", "")) for parte in partes if isinstance(parte, dict))


def _texto_da_resposta_openai(dados: object) -> str:
    """`choices[0].message.content`. Resposta fora dessa forma devolve vazio, que a base trata como
    conteúdo inválido — ver `_texto_da_resposta_anthropic`."""
    if not isinstance(dados, dict):
        return ""
    escolhas = dados.get("choices")
    if not isinstance(escolhas, list) or not escolhas:
        return ""
    primeira = escolhas[0]
    mensagem = primeira.get("message") if isinstance(primeira, dict) else None
    if not isinstance(mensagem, dict):
        return ""
    conteudo = mensagem.get("content")
    return conteudo if isinstance(conteudo, str) else ""
