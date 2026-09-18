from __future__ import annotations

import json
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


def _criar_contato(conn: sqlite3.Connection, cidade: str | None, linguas: list[str]) -> int:
    criado_em = "2026-01-01T00:00:00+00:00"
    conn.execute(
        "INSERT INTO perfil (tipo, nome, cidade, linguas, criado_em, atualizado_em) "
        "VALUES ('contato', 'Fulano', ?, ?, ?, ?)",
        (cidade, json.dumps(linguas), criado_em, criado_em),
    )
    conn.commit()
    (perfil_id,) = conn.execute("SELECT id FROM perfil WHERE nome = 'Fulano'").fetchone()
    return perfil_id


def test_campo_ja_preenchido_nao_e_sobrescrito(conn: sqlite3.Connection) -> None:
    perfil_id = _criar_contato(conn, cidade="Santos", linguas=[])

    perfis.atualizar_campos_guiados(conn, perfil_id, {"cidade": "Rio de Janeiro"}, AGORA)

    (cidade,) = conn.execute("SELECT cidade FROM perfil WHERE id = ?", (perfil_id,)).fetchone()
    assert cidade == "Santos"


def test_campo_vazio_passa_a_valer(conn: sqlite3.Connection) -> None:
    perfil_id = _criar_contato(conn, cidade=None, linguas=[])

    perfis.atualizar_campos_guiados(conn, perfil_id, {"cidade": "Rio de Janeiro"}, AGORA)

    (cidade,) = conn.execute("SELECT cidade FROM perfil WHERE id = ?", (perfil_id,)).fetchone()
    assert cidade == "Rio de Janeiro"


def test_linguas_vazia_passa_a_valer(conn: sqlite3.Connection) -> None:
    perfil_id = _criar_contato(conn, cidade=None, linguas=[])

    perfis.atualizar_campos_guiados(conn, perfil_id, {"linguas": ["inglês", "espanhol"]}, AGORA)

    (linguas,) = conn.execute("SELECT linguas FROM perfil WHERE id = ?", (perfil_id,)).fetchone()
    assert json.loads(linguas) == ["inglês", "espanhol"]


def test_linguas_ja_preenchida_nao_e_sobrescrita(conn: sqlite3.Connection) -> None:
    perfil_id = _criar_contato(conn, cidade=None, linguas=["francês"])

    perfis.atualizar_campos_guiados(conn, perfil_id, {"linguas": ["inglês"]}, AGORA)

    (linguas,) = conn.execute("SELECT linguas FROM perfil WHERE id = ?", (perfil_id,)).fetchone()
    assert json.loads(linguas) == ["francês"]
