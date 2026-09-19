from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import yaml
from pydantic import BaseModel

from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.llm import ClienteOllama, FalhaJsonInvalido
from agente_nw.nucleo.modelos.configuracao import Roteamento

RAIZ = Path(__file__).resolve().parent.parent


class _EsquemaTeste(BaseModel):
    ok: bool


def _roteamento() -> Roteamento:
    dados = yaml.safe_load((RAIZ / "config" / "llm_routing.yaml").read_text(encoding="utf-8"))
    return Roteamento.model_validate(dados)


def _ler_log(caminho: Path) -> list[dict[str, object]]:
    if not caminho.exists():
        return []
    linhas = caminho.read_text(encoding="utf-8").splitlines()
    return [json.loads(linha) for linha in linhas]


def _cliente(tmp_path: Path, handler: httpx.MockTransport, caminho_log: Path) -> ClienteOllama:
    conexao_bd = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_bd)
    cliente_http = httpx.Client(transport=handler)
    return ClienteOllama(cliente_http, conexao_bd, _roteamento(), "http://ollama.invalido", caminho_log)


def test_sucesso_na_primeira_tentativa_grava_uma_tentativa(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"response": json.dumps({"ok": True})})

    caminho_log = tmp_path / "chamadas_llm.jsonl"
    cliente = _cliente(tmp_path, httpx.MockTransport(handler), caminho_log)

    cliente.gerar_json("qualificar", "prompt", _EsquemaTeste)

    linhas = _ler_log(caminho_log)
    assert len(linhas) == 1
    assert linhas[0]["tarefa"] == "qualificar"
    assert linhas[0]["tentativas_usadas"] == 1
    assert linhas[0]["sucesso"] is True


def test_sucesso_so_na_segunda_tentativa_grava_duas_tentativas(tmp_path: Path) -> None:
    chamadas = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        chamadas["n"] += 1
        if chamadas["n"] == 1:
            return httpx.Response(200, json={"response": "isso não é um JSON válido"})
        return httpx.Response(200, json={"response": json.dumps({"ok": True})})

    caminho_log = tmp_path / "chamadas_llm.jsonl"
    cliente = _cliente(tmp_path, httpx.MockTransport(handler), caminho_log)

    cliente.gerar_json("qualificar", "prompt", _EsquemaTeste)

    linhas = _ler_log(caminho_log)
    assert len(linhas) == 1
    assert linhas[0]["tentativas_usadas"] == 2
    assert linhas[0]["sucesso"] is True


def test_falha_nas_duas_tentativas_grava_sucesso_false_e_vai_para_fila_revisao(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"response": "isso não é um JSON válido"})

    caminho_log = tmp_path / "chamadas_llm.jsonl"
    conexao_bd = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_bd)
    cliente_http = httpx.Client(transport=httpx.MockTransport(handler))
    cliente = ClienteOllama(cliente_http, conexao_bd, _roteamento(), "http://ollama.invalido", caminho_log)

    with pytest.raises(FalhaJsonInvalido):
        cliente.gerar_json("qualificar", "prompt", _EsquemaTeste)

    linhas = _ler_log(caminho_log)
    assert len(linhas) == 1
    assert linhas[0]["tentativas_usadas"] == 2
    assert linhas[0]["sucesso"] is False

    (n_fila,) = conexao_bd.execute("SELECT COUNT(*) FROM fila_revisao").fetchone()
    assert n_fila == 1
