from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import perfis, rede_sem_perfil

AGORA = "2026-10-13T10:00:00+00:00"


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


def _contato(conn: sqlite3.Connection, nome: str) -> int:
    perfil = perfis.inserir_novo_contato(conn, nome, None, None, AGORA)
    assert perfil.id is not None
    return perfil.id


def test_declarar_e_listar_por_contato(conn: sqlite3.Connection) -> None:
    ana, beto = _contato(conn, "Ana Souza"), _contato(conn, "Beto Lima")

    rede_sem_perfil.declarar(conn, ana, "x", AGORA)
    rede_sem_perfil.declarar(conn, ana, "x", AGORA)  # repetir não duplica
    rede_sem_perfil.declarar(conn, ana, "facebook", AGORA)

    assert rede_sem_perfil.listar_redes(conn, ana) == {"x", "facebook"}
    assert rede_sem_perfil.listar_redes(conn, beto) == set()


def test_remover_tira_so_aquela_rede(conn: sqlite3.Connection) -> None:
    ana = _contato(conn, "Ana Souza")
    rede_sem_perfil.declarar(conn, ana, "x", AGORA)
    rede_sem_perfil.declarar(conn, ana, "facebook", AGORA)

    rede_sem_perfil.remover(conn, ana, "x")

    assert rede_sem_perfil.listar_redes(conn, ana) == {"facebook"}


def test_apagar_contato_leva_as_declaracoes(conn: sqlite3.Connection) -> None:
    ana = _contato(conn, "Ana Souza")
    rede_sem_perfil.declarar(conn, ana, "x", AGORA)

    perfis.apagar_contato_completo(conn, ana)

    assert conn.execute("SELECT COUNT(*) AS n FROM rede_sem_perfil").fetchone()["n"] == 0


def test_unir_contatos_junta_as_declaracoes_sem_duplicar(conn: sqlite3.Connection) -> None:
    canonico, duplicado = _contato(conn, "Ana Souza"), _contato(conn, "Ana S.")
    rede_sem_perfil.declarar(conn, canonico, "x", AGORA)
    rede_sem_perfil.declarar(conn, duplicado, "x", AGORA)
    rede_sem_perfil.declarar(conn, duplicado, "facebook", AGORA)

    perfis.unir_contatos(conn, canonico, duplicado)

    assert rede_sem_perfil.listar_redes(conn, canonico) == {"x", "facebook"}
