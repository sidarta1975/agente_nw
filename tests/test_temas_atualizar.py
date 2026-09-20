from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import temas

AGORA = "2026-01-02T00:00:00+00:00"


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


def test_atualizar_regrava_descricao_e_sinonimos_sem_tocar_o_nome(conn: sqlite3.Connection) -> None:
    tema = temas.obter_ou_criar(conn, "corrida de rua", "descrição original", ["maratona"], AGORA)
    conn.commit()
    assert tema.id is not None

    temas.atualizar(conn, tema.id, "descrição nova, mais completa", ["maratona", "meia maratona"])
    conn.commit()

    atualizado = temas.obter_por_id(conn, tema.id)
    assert atualizado is not None
    assert atualizado.nome == "corrida de rua"
    assert atualizado.descricao == "descrição nova, mais completa"
    assert atualizado.sinonimos == ["maratona", "meia maratona"]
