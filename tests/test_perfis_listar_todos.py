from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import perfis

AGORA = "2026-01-02T00:00:00+00:00"


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


def _criar_contato(conn: sqlite3.Connection, nome: str, ativo: bool) -> None:
    conn.execute(
        "INSERT INTO perfil (tipo, nome, linguas, ativo, criado_em, atualizado_em) "
        "VALUES ('contato', ?, '[]', ?, ?, ?)",
        (nome, int(ativo), AGORA, AGORA),
    )
    conn.commit()


def test_listar_todos_inclui_ativos_e_inativos_em_ordem_de_nome(conn: sqlite3.Connection) -> None:
    _criar_contato(conn, "Zeca", ativo=True)
    _criar_contato(conn, "Ana", ativo=False)

    resultado = perfis.listar_todos(conn)

    assert [p.nome for p in resultado] == ["Ana", "Zeca"]
    assert resultado[0].ativo is False
    assert resultado[1].ativo is True


def test_listar_todos_nao_inclui_o_perfil_usuario(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT INTO perfil (tipo, nome, linguas, ativo, criado_em, atualizado_em) "
        "VALUES ('usuario', 'Eu', '[]', 1, ?, ?)",
        (AGORA, AGORA),
    )
    _criar_contato(conn, "Ana", ativo=False)
    conn.commit()

    resultado = perfis.listar_todos(conn)

    assert [p.nome for p in resultado] == ["Ana"]
