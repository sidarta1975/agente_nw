"""Transporte instável contra o Ollama não derruba a chamada: backoff de 2, 4, 8 e 16 segundos
para erro de conexão/HTTP, separado da nova tentativa por temperatura (que é só para falha de
conteúdo). `seed` fixo e `num_predict` da tarefa vão sempre no corpo (brief 064)."""

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


def _cliente(tmp_path: Path, handler: Any, caminho_log: Path) -> ClienteOllama:
    conexao_bd = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_bd)
    cliente_http = httpx.Client(transport=httpx.MockTransport(handler))
    return ClienteOllama(cliente_http, conexao_bd, _roteamento(), "http://ollama.invalido", caminho_log)


@pytest.fixture(autouse=True)
def _sem_sono(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """Backoff mockado: o teste não espera de verdade, só registra os intervalos pedidos."""
    esperas: list[float] = []
    monkeypatch.setattr(llm_mod.time, "sleep", lambda segundos: esperas.append(segundos))
    return esperas


def test_503_depois_200_conclui_e_conta_falha_de_transporte_fora_da_nova_tentativa(
    tmp_path: Path, _sem_sono: list[float]
) -> None:
    chamadas = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        chamadas["n"] += 1
        if chamadas["n"] == 1:
            return httpx.Response(503)
        return httpx.Response(200, json={"response": json.dumps({"ok": True})})

    caminho_log = tmp_path / "chamadas_llm.jsonl"
    cliente = _cliente(tmp_path, handler, caminho_log)

    resultado = cliente.gerar_json("qualificar", "prompt", _EsquemaTeste)

    assert resultado.ok is True
    assert chamadas["n"] == 2
    assert _sem_sono == [2]

    linhas = _ler_log(caminho_log)
    assert len(linhas) == 1
    assert linhas[0]["tentativas_usadas"] == 1
    assert linhas[0]["sucesso"] is True
    assert linhas[0]["falhas_transporte"] == 1


def test_erro_de_conexao_nas_tres_primeiras_e_sucesso_na_quarta_respeita_o_backoff(
    tmp_path: Path, _sem_sono: list[float]
) -> None:
    chamadas = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        chamadas["n"] += 1
        if chamadas["n"] <= 3:
            raise httpx.ConnectError("conexão recusada")
        return httpx.Response(200, json={"response": json.dumps({"ok": True})})

    caminho_log = tmp_path / "chamadas_llm.jsonl"
    cliente = _cliente(tmp_path, handler, caminho_log)

    resultado = cliente.gerar_json("qualificar", "prompt", _EsquemaTeste)

    assert resultado.ok is True
    assert chamadas["n"] == 4
    assert _sem_sono == [2, 4, 8]


def test_quatro_tentativas_de_transporte_esgotadas_vai_para_fila_revisao(
    tmp_path: Path, _sem_sono: list[float]
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("conexão recusada")

    caminho_log = tmp_path / "chamadas_llm.jsonl"
    conexao_bd = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_bd)
    cliente_http = httpx.Client(transport=httpx.MockTransport(handler))
    cliente = ClienteOllama(cliente_http, conexao_bd, _roteamento(), "http://ollama.invalido", caminho_log)

    with pytest.raises(FalhaJsonInvalido):
        cliente.gerar_json("qualificar", "prompt", _EsquemaTeste)

    assert _sem_sono == [2, 4, 8, 16]

    linhas = _ler_log(caminho_log)
    assert len(linhas) == 1
    assert linhas[0]["sucesso"] is False
    assert linhas[0]["falhas_transporte"] == 5

    (n_fila,) = conexao_bd.execute("SELECT COUNT(*) FROM fila_revisao").fetchone()
    assert n_fila == 1


def test_corpo_tem_seed_fixo_e_num_predict_da_tarefa(tmp_path: Path) -> None:
    roteamento = _roteamento()
    tarefa_qualificar = roteamento.perfis[roteamento.perfil_ativo].tarefas["qualificar"]
    capturado: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        capturado["corpo"] = json.loads(request.content)
        return httpx.Response(200, json={"response": json.dumps({"ok": True})})

    caminho_log = tmp_path / "chamadas_llm.jsonl"
    cliente = _cliente(tmp_path, handler, caminho_log)

    cliente.gerar_json("qualificar", "prompt", _EsquemaTeste)

    corpo = capturado["corpo"]
    assert isinstance(corpo, dict)
    assert corpo["options"]["seed"] == 42
    assert corpo["options"]["num_predict"] == tarefa_qualificar.num_predict


def test_geracao_degenerada_depois_sucesso_na_nova_tentativa_sem_subir_excecao(
    tmp_path: Path, _sem_sono: list[float]
) -> None:
    chamadas = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        chamadas["n"] += 1
        if chamadas["n"] == 1:
            return httpx.Response(500, json={"error": "prediction aborted, token repeat limit reached"})
        return httpx.Response(200, json={"response": json.dumps({"ok": True})})

    caminho_log = tmp_path / "chamadas_llm.jsonl"
    cliente = _cliente(tmp_path, handler, caminho_log)

    resultado = cliente.gerar_json("qualificar", "prompt", _EsquemaTeste)

    assert resultado.ok is True
    assert chamadas["n"] == 2
    assert _sem_sono == []

    linhas = _ler_log(caminho_log)
    assert len(linhas) == 1
    assert linhas[0]["tentativas_usadas"] == 2
    assert linhas[0]["sucesso"] is True
    assert linhas[0]["falhas_transporte"] == 0


def test_geracao_degenerada_nas_duas_tentativas_vai_para_fila_revisao_sem_excecao_subir(
    tmp_path: Path, _sem_sono: list[float]
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "prediction aborted, token repeat limit reached"})

    caminho_log = tmp_path / "chamadas_llm.jsonl"
    conexao_bd = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_bd)
    cliente_http = httpx.Client(transport=httpx.MockTransport(handler))
    cliente = ClienteOllama(cliente_http, conexao_bd, _roteamento(), "http://ollama.invalido", caminho_log)

    with pytest.raises(FalhaJsonInvalido):
        cliente.gerar_json("qualificar", "prompt", _EsquemaTeste)

    assert _sem_sono == []

    linhas = _ler_log(caminho_log)
    assert len(linhas) == 1
    assert linhas[0]["sucesso"] is False
    assert linhas[0]["falhas_transporte"] == 0

    (n_fila,) = conexao_bd.execute("SELECT COUNT(*) FROM fila_revisao").fetchone()
    assert n_fila == 1


def test_falha_de_conteudo_so_aciona_a_nova_tentativa_por_temperatura_sem_backoff(
    tmp_path: Path, _sem_sono: list[float]
) -> None:
    chamadas = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        chamadas["n"] += 1
        if chamadas["n"] == 1:
            return httpx.Response(200, json={"response": "isso não é um JSON válido"})
        return httpx.Response(200, json={"response": json.dumps({"ok": True})})

    caminho_log = tmp_path / "chamadas_llm.jsonl"
    cliente = _cliente(tmp_path, handler, caminho_log)

    resultado = cliente.gerar_json("qualificar", "prompt", _EsquemaTeste)

    assert resultado.ok is True
    assert chamadas["n"] == 2
    assert _sem_sono == []

    linhas = _ler_log(caminho_log)
    assert linhas[0]["tentativas_usadas"] == 2
    assert linhas[0]["falhas_transporte"] == 0
