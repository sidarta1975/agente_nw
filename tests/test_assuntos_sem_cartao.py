from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import assuntos
from agente_nw.nucleo.modelos.assunto import Assunto

AGORA = "2026-01-01T00:00:00+00:00"


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


def test_qualificado_sem_cartao_aparece(conn: sqlite3.Connection) -> None:
    assunto_id = assuntos.inserir(
        conn,
        Assunto(primeiro_visto=AGORA, ultimo_visto=AGORA, status="novo", substancial=0.8, conversavel=0.8),
    )
    conn.commit()

    resultado = assuntos.listar_qualificados_sem_cartao(conn, 10)

    assert [a.id for a in resultado] == [assunto_id]


def test_com_cartao_ja_gravado_nao_aparece(conn: sqlite3.Connection) -> None:
    assunto_id = assuntos.inserir(
        conn,
        Assunto(primeiro_visto=AGORA, ultimo_visto=AGORA, status="novo", substancial=0.8, conversavel=0.8),
    )
    assuntos.gravar_cartao(conn, assunto_id, "resumo já pronto")
    conn.commit()

    assert assuntos.listar_qualificados_sem_cartao(conn, 10) == []


def test_nao_qualificado_nao_aparece(conn: sqlite3.Connection) -> None:
    assuntos.inserir(conn, Assunto(primeiro_visto=AGORA, ultimo_visto=AGORA, status="novo"))
    conn.commit()

    assert assuntos.listar_qualificados_sem_cartao(conn, 10) == []


def test_respeita_limite(conn: sqlite3.Connection) -> None:
    for _ in range(5):
        assuntos.inserir(
            conn,
            Assunto(
                primeiro_visto=AGORA, ultimo_visto=AGORA, status="novo", substancial=0.8, conversavel=0.8
            ),
        )
    conn.commit()

    assert len(assuntos.listar_qualificados_sem_cartao(conn, 3)) == 3
