"""Clientes de API (brief 075): Anthropic, Gemini e OpenAI com a mesma forma pública do
`ClienteOllama`. Cada um força o JSON pela via nativa do provedor, manda imagem no formato dele,
usa o backoff e a `fila_revisao` da base do brief 074, e repassa `embeddar`/`modelo_embedding`
ao `ClienteOllama` local — nunca os reimplementa. Sem rede real e sem chave real: `MockTransport`
em tudo."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
import yaml
from pydantic import BaseModel

from agente_nw.nucleo import llm as llm_mod
from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.llm import (
    ClienteAnthropic,
    ClienteGemini,
    ClienteOllama,
    ClienteOpenAI,
    FalhaJsonInvalido,
)
from agente_nw.nucleo.modelos.configuracao import Roteamento

RAIZ = Path(__file__).resolve().parent.parent

CHAVE = "chave-de-teste-nao-serve-para-nada"
MODELO_API = "modelo-de-teste"


class _EsquemaTeste(BaseModel):
    ok: bool


def _roteamento() -> Roteamento:
    dados = yaml.safe_load((RAIZ / "config" / "llm_routing.yaml").read_text(encoding="utf-8"))
    return Roteamento.model_validate(dados)


def _tarefa_qualificar() -> Any:
    roteamento = _roteamento()
    return roteamento.perfis[roteamento.perfil_ativo].tarefas["qualificar"]


@pytest.fixture(autouse=True)
def _sem_sono(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """O mesmo fixture de `test_llm_resiliente.py`: o backoff não espera de verdade, só registra."""
    esperas: list[float] = []
    monkeypatch.setattr(llm_mod.time, "sleep", lambda segundos: esperas.append(segundos))
    return esperas


def _embeddings_falsos(request: httpx.Request) -> httpx.Response:
    corpo = json.loads(request.content)
    textos = corpo["input"]
    return httpx.Response(200, json={"embeddings": [[0.5] * 1024 for _ in textos]})


def _cliente_embeddings(tmp_path: Path, caminho_log: Path) -> ClienteOllama:
    conexao_bd = conexao.abrir(tmp_path / "embeddings.db")
    migracoes.aplicar(conexao_bd)
    http = httpx.Client(transport=httpx.MockTransport(_embeddings_falsos))
    return ClienteOllama(http, conexao_bd, _roteamento(), "http://ollama.invalido", caminho_log)


def _montar(
    classe: type[ClienteAnthropic] | type[ClienteGemini] | type[ClienteOpenAI],
    tmp_path: Path,
    handler: Any,
) -> tuple[Any, Any]:
    """Devolve o cliente de API e a conexão dele (para conferir `fila_revisao`)."""
    caminho_log = tmp_path / "chamadas_llm.jsonl"
    conexao_bd = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_bd)
    http = httpx.Client(transport=httpx.MockTransport(handler))
    cliente = classe(
        http,
        conexao_bd,
        _roteamento(),
        CHAVE,
        MODELO_API,
        caminho_log,
        _cliente_embeddings(tmp_path, caminho_log),
    )
    return cliente, conexao_bd


# --------------------------------------------------------------------------------------
# Anthropic: uma tool só, forçada por tool_choice, com o esquema como input_schema
# --------------------------------------------------------------------------------------


def test_anthropic_forca_o_esquema_por_tool_e_le_o_bloco_tool_use(tmp_path: Path) -> None:
    capturado: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        capturado["url"] = str(request.url)
        capturado["headers"] = dict(request.headers)
        capturado["corpo"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "content": [
                    {"type": "tool_use", "name": "responder", "input": {"ok": True}},
                ]
            },
        )

    cliente, _ = _montar(ClienteAnthropic, tmp_path, handler)

    resultado = cliente.gerar_json("qualificar", "prompt", _EsquemaTeste)

    assert resultado.ok is True
    assert capturado["url"] == "https://api.anthropic.com/v1/messages"
    assert capturado["headers"]["x-api-key"] == CHAVE
    assert capturado["headers"]["anthropic-version"] == "2023-06-01"

    corpo = capturado["corpo"]
    assert corpo["model"] == MODELO_API
    assert corpo["max_tokens"] == _tarefa_qualificar().num_predict
    assert corpo["temperature"] == _tarefa_qualificar().temperature
    (tool,) = corpo["tools"]
    assert tool["input_schema"] == _EsquemaTeste.model_json_schema()
    assert corpo["tool_choice"] == {"type": "tool", "name": tool["name"]}
    assert corpo["messages"][0]["content"][-1] == {"type": "text", "text": "prompt"}
    assert "num_ctx" not in json.dumps(corpo)
    assert "think" not in json.dumps(corpo)


def test_anthropic_manda_imagem_no_formato_de_bloco_base64(tmp_path: Path) -> None:
    capturado: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        capturado["corpo"] = json.loads(request.content)
        return httpx.Response(200, json={"content": [{"type": "tool_use", "input": {"ok": True}}]})

    cliente, _ = _montar(ClienteAnthropic, tmp_path, handler)

    cliente.gerar_json("descrever_imagem", "descreva", _EsquemaTeste, imagens=["base64fake"])

    conteudo = capturado["corpo"]["messages"][0]["content"]
    assert conteudo[0] == {
        "type": "image",
        "source": {"type": "base64", "media_type": "image/jpeg", "data": "base64fake"},
    }


def test_anthropic_resposta_sem_tool_use_cai_na_fila_revisao_sem_subir_outra_excecao(
    tmp_path: Path,
) -> None:
    """Resposta 200 que não traz o bloco `tool_use` é falha de conteúdo, não de transporte: segue
    pela nova tentativa por temperatura e, esgotada, vai para `fila_revisao` — nunca uma exceção
    diferente escapando de `gerar_json` (a armadilha que o brief 067 corrigiu)."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"content": [{"type": "text", "text": "desculpe, não vou"}]})

    cliente, conexao_bd = _montar(ClienteAnthropic, tmp_path, handler)

    with pytest.raises(FalhaJsonInvalido):
        cliente.gerar_json("qualificar", "prompt", _EsquemaTeste)

    (n_fila,) = conexao_bd.execute("SELECT COUNT(*) FROM fila_revisao").fetchone()
    assert n_fila == 1


# --------------------------------------------------------------------------------------
# OpenAI: response_format json_schema
# --------------------------------------------------------------------------------------


def test_openai_forca_o_esquema_por_response_format_e_le_o_content(tmp_path: Path) -> None:
    capturado: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        capturado["url"] = str(request.url)
        capturado["headers"] = dict(request.headers)
        capturado["corpo"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps({"ok": True})}}]})

    cliente, _ = _montar(ClienteOpenAI, tmp_path, handler)

    resultado = cliente.gerar_json("qualificar", "prompt", _EsquemaTeste)

    assert resultado.ok is True
    assert capturado["url"] == "https://api.openai.com/v1/chat/completions"
    assert capturado["headers"]["authorization"] == f"Bearer {CHAVE}"

    corpo = capturado["corpo"]
    assert corpo["model"] == MODELO_API
    assert corpo["max_tokens"] == _tarefa_qualificar().num_predict
    assert corpo["temperature"] == _tarefa_qualificar().temperature
    formato = corpo["response_format"]
    assert formato["type"] == "json_schema"
    assert formato["json_schema"]["name"] == _EsquemaTeste.__name__
    assert formato["json_schema"]["schema"] == _EsquemaTeste.model_json_schema()
    assert formato["json_schema"]["strict"] is True
    assert "num_ctx" not in json.dumps(corpo)


def test_openai_manda_imagem_como_data_url(tmp_path: Path) -> None:
    capturado: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        capturado["corpo"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps({"ok": True})}}]})

    cliente, _ = _montar(ClienteOpenAI, tmp_path, handler)

    cliente.gerar_json("descrever_imagem", "descreva", _EsquemaTeste, imagens=["base64fake"])

    conteudo = capturado["corpo"]["messages"][0]["content"]
    assert {
        "type": "image_url",
        "image_url": {"url": "data:image/jpeg;base64,base64fake"},
    } in conteudo


# --------------------------------------------------------------------------------------
# Gemini: response_mime_type + response_schema
# --------------------------------------------------------------------------------------


def test_gemini_forca_o_esquema_por_response_schema_e_le_a_parte_de_texto(tmp_path: Path) -> None:
    capturado: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        capturado["url"] = str(request.url)
        capturado["headers"] = dict(request.headers)
        capturado["corpo"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": json.dumps({"ok": True})}]}}]},
        )

    cliente, _ = _montar(ClienteGemini, tmp_path, handler)

    resultado = cliente.gerar_json("qualificar", "prompt", _EsquemaTeste)

    assert resultado.ok is True
    assert capturado["url"] == (
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODELO_API}:generateContent"
    )
    assert capturado["headers"]["x-goog-api-key"] == CHAVE

    corpo = capturado["corpo"]
    config = corpo["generationConfig"]
    assert config["response_mime_type"] == "application/json"
    assert config["response_schema"] == _EsquemaTeste.model_json_schema()
    assert config["maxOutputTokens"] == _tarefa_qualificar().num_predict
    assert config["temperature"] == _tarefa_qualificar().temperature
    assert corpo["contents"][0]["parts"][-1] == {"text": "prompt"}
    assert "num_ctx" not in json.dumps(corpo)


def test_gemini_nao_leva_a_chave_na_url(tmp_path: Path) -> None:
    """A chave vai no header, nunca na query: `str(httpx.HTTPStatusError)` inclui a URL e
    `_ir_para_fila_revisao` grava esse texto no banco — chave na URL viraria chave no banco."""
    capturado: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        capturado["url"] = str(request.url)
        return httpx.Response(500, json={"error": "falhou"})

    cliente, conexao_bd = _montar(ClienteGemini, tmp_path, handler)

    with pytest.raises(FalhaJsonInvalido):
        cliente.gerar_json("qualificar", "prompt", _EsquemaTeste)

    assert CHAVE not in capturado["url"]
    (erro_gravado,) = conexao_bd.execute("SELECT erro FROM fila_revisao").fetchone()
    assert CHAVE not in erro_gravado


def test_gemini_manda_imagem_como_inline_data(tmp_path: Path) -> None:
    capturado: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        capturado["corpo"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": json.dumps({"ok": True})}]}}]},
        )

    cliente, _ = _montar(ClienteGemini, tmp_path, handler)

    cliente.gerar_json("descrever_imagem", "descreva", _EsquemaTeste, imagens=["base64fake"])

    partes = capturado["corpo"]["contents"][0]["parts"]
    assert partes[0] == {"inlineData": {"mimeType": "image/jpeg", "data": "base64fake"}}


# --------------------------------------------------------------------------------------
# A base do brief 074 é a mesma para os três: backoff de transporte e fila_revisao
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("classe", [ClienteAnthropic, ClienteGemini, ClienteOpenAI])
def test_erro_de_transporte_usa_o_backoff_da_base_e_cai_na_fila_revisao(
    classe: Any, tmp_path: Path, _sem_sono: list[float]
) -> None:
    chamadas = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        chamadas["n"] += 1
        raise httpx.ConnectError("conexão recusada")

    cliente, conexao_bd = _montar(classe, tmp_path, handler)

    with pytest.raises(FalhaJsonInvalido):
        cliente.gerar_json("qualificar", "prompt", _EsquemaTeste)

    assert chamadas["n"] == 5
    assert _sem_sono == [2, 4, 8, 16]

    (n_fila,) = conexao_bd.execute("SELECT COUNT(*) FROM fila_revisao").fetchone()
    assert n_fila == 1


@pytest.mark.parametrize("classe", [ClienteAnthropic, ClienteGemini, ClienteOpenAI])
def test_json_invalido_aciona_a_nova_tentativa_por_temperatura_da_base(
    classe: Any, tmp_path: Path, _sem_sono: list[float]
) -> None:
    """Duas temperaturas, sem backoff: é falha de conteúdo, não de transporte."""
    temperaturas: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        corpo = json.loads(request.content)
        if "generationConfig" in corpo:
            temperaturas.append(corpo["generationConfig"]["temperature"])
        else:
            temperaturas.append(corpo["temperature"])
        return httpx.Response(200, json={"isso": "não tem o campo que cada provedor devolve"})

    cliente, conexao_bd = _montar(classe, tmp_path, handler)

    with pytest.raises(FalhaJsonInvalido):
        cliente.gerar_json("qualificar", "prompt", _EsquemaTeste)

    roteamento = _roteamento()
    assert temperaturas == [
        _tarefa_qualificar().temperature,
        roteamento.perfis[roteamento.perfil_ativo].nova_tentativa.temperature,
    ]
    assert _sem_sono == []

    (n_fila,) = conexao_bd.execute("SELECT COUNT(*) FROM fila_revisao").fetchone()
    assert n_fila == 1


# --------------------------------------------------------------------------------------
# Embeddings: composição com o ClienteOllama local, nunca reimplementados (item 3.5)
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("classe", [ClienteAnthropic, ClienteGemini, ClienteOpenAI])
def test_embeddar_e_modelo_embedding_so_repassam_ao_ollama_sem_chamar_a_api(
    classe: Any, tmp_path: Path
) -> None:
    chamadas_api: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        chamadas_api.append(str(request.url))
        return httpx.Response(200, json={})

    caminho_log = tmp_path / "chamadas_llm.jsonl"
    cliente_ollama = _cliente_embeddings(tmp_path, caminho_log)
    conexao_bd = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_bd)
    cliente = classe(
        httpx.Client(transport=httpx.MockTransport(handler)),
        conexao_bd,
        _roteamento(),
        CHAVE,
        MODELO_API,
        caminho_log,
        cliente_ollama,
    )

    vetores = cliente.embeddar(["um", "dois"])

    assert len(vetores) == 2
    assert all(len(vetor) == 1024 for vetor in vetores)
    assert cliente.modelo_embedding == cliente_ollama.modelo_embedding
    assert chamadas_api == []


# --------------------------------------------------------------------------------------
# Proveniência: o log tem que registrar o modelo do provedor de API, não o do Ollama
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("classe", [ClienteAnthropic, ClienteGemini, ClienteOpenAI])
def test_proveniencia_registra_o_modelo_do_provedor_de_api(classe: Any, tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={})

    cliente, _ = _montar(classe, tmp_path, handler)

    proveniencia = cliente.proveniencia("qualificar", "2026-11-03-1")

    assert proveniencia.modelo == MODELO_API
    assert proveniencia.modelo != _tarefa_qualificar().modelo
    assert proveniencia.perfil == _roteamento().perfil_ativo
    assert proveniencia.prompt_versao == "2026-11-03-1"


@pytest.mark.parametrize("classe", [ClienteAnthropic, ClienteGemini, ClienteOpenAI])
def test_tarefa_fora_do_perfil_continua_erro_claro(classe: Any, tmp_path: Path) -> None:
    """A conferência de tarefa declarada no `llm_routing.yaml` é da base e continua valendo."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={})

    cliente, _ = _montar(classe, tmp_path, handler)

    with pytest.raises(KeyError):
        cliente.gerar_json("tarefa_que_nao_existe", "prompt", _EsquemaTeste)
