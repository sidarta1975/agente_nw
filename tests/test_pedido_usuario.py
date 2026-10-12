from __future__ import annotations

import getpass
import sqlite3
from pathlib import Path

import pytest

from agente_nw.nucleo import pedido as pedido_mod
from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import perfis

AGORA = "2026-10-11T10:00:00+00:00"


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


def test_banco_sem_usuario_cria_com_o_nome_do_sistema(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(getpass, "getuser", lambda: "zelia")

    usuario = pedido_mod.garantir_usuario(conn, AGORA)

    assert usuario.tipo == "usuario"
    assert usuario.nome == "Zelia"
    assert perfis.obter_usuario(conn) is not None


def test_usuario_existente_nao_e_alterado(conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch) -> None:
    perfis.upsert_usuario(conn, "Nome Original", AGORA)
    conn.commit()
    monkeypatch.setattr(getpass, "getuser", lambda: "outro")

    assert pedido_mod.garantir_usuario(conn, AGORA).nome == "Nome Original"
