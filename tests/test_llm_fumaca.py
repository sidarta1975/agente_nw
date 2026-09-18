from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import NamedTuple

import httpx
import pytest
from pydantic import BaseModel

from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.llm import ClienteOllama, FalhaJsonInvalido
from config.container import configuracao


def _ollama_disponivel() -> bool:
    try:
        url = configuracao().local.ollama_url
        resposta = httpx.get(f"{url}/api/tags", timeout=3.0)
        resposta.raise_for_status()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _ollama_disponivel(), reason="Ollama fora do ar")


class _EsquemaFumaca(BaseModel):
    ok: bool


class _Preparo(NamedTuple):
    cliente: ClienteOllama
    conexao_bd: sqlite3.Connection


@pytest.fixture
def preparo(tmp_path: Path) -> _Preparo:
    cfg = configuracao()
    conexao_bd = conexao.abrir(tmp_path / "fumaca.db")
    migracoes.aplicar(conexao_bd)
    cliente_http = httpx.Client(timeout=60.0)
    cliente = ClienteOllama(cliente_http, conexao_bd, cfg.roteamento, cfg.local.ollama_url)
    return _Preparo(cliente=cliente, conexao_bd=conexao_bd)


def test_geracao_json_valido_vinte_de_vinte(preparo: _Preparo) -> None:
    prompt = 'Responda só com JSON, no formato exato {"ok": true}, sem texto antes ou depois.'
    for _ in range(20):
        resultado = preparo.cliente.gerar_json("qualificar", prompt, _EsquemaFumaca)
        assert resultado.ok is True


def test_embeddar_cem_textos_em_menos_de_trinta_segundos(preparo: _Preparo) -> None:
    textos = [f"texto de teste número {i} sobre um assunto qualquer" for i in range(100)]

    inicio = time.monotonic()
    vetores = preparo.cliente.embeddar(textos)
    duracao = time.monotonic() - inicio

    assert len(vetores) == 100
    assert all(len(vetor) == 1024 for vetor in vetores)
    assert duracao < 30.0


def test_esquema_impossivel_gera_falha_e_fila_de_revisao(preparo: _Preparo) -> None:
    class _EsquemaImpossivel(BaseModel):
        numero_primo_par_maior_que_dois: int

    with pytest.raises(FalhaJsonInvalido) as excinfo:
        preparo.cliente.gerar_json(
            "qualificar",
            'Responda só com JSON no formato {"ok": true}.',
            _EsquemaImpossivel,
        )

    linha = preparo.conexao_bd.execute(
        "SELECT resolvido, erro FROM fila_revisao WHERE id = ?",
        (excinfo.value.fila_revisao_id,),
    ).fetchone()
    assert linha is not None
    assert linha["resolvido"] == 0
    assert linha["erro"]
