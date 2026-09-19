from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import assunto_contato, assuntos, perfis
from agente_nw.nucleo.modelos.assunto import Assunto
from agente_nw.nucleo.modelos.assunto_contato import AssuntoContato

AGORA = "2026-01-01T00:00:00+00:00"


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


def _criar_assunto_contato(conn: sqlite3.Connection, status: str = "novo") -> int:
    assunto_id = assuntos.inserir(conn, Assunto(primeiro_visto=AGORA, ultimo_visto=AGORA, status="novo"))
    contato = perfis.inserir_ou_atualizar_contato(
        conn, "Fulano", "+5511900000000", None, None, None, None, AGORA
    )
    assert contato.id is not None
    conn.commit()

    registro = AssuntoContato(
        assunto_id=assunto_id,
        perfil_id=contato.id,
        gerado_em="2026-09-19",
        tipo="conector",
        aderencia_contato=0.7,
        aderencia_usuario=0.6,
        conversavel=0.5,
        score=65.0,
        status=status,  # type: ignore[arg-type]
    )
    assunto_contato.inserir(conn, registro)
    conn.commit()
    (ac_id,) = conn.execute("SELECT id FROM assunto_contato").fetchone()
    return ac_id


def test_marcar_usado_em_registro_novo_devolve_true_e_persiste(conn: sqlite3.Connection) -> None:
    ac_id = _criar_assunto_contato(conn)

    resultado = assunto_contato.marcar_usado(conn, ac_id)
    conn.commit()

    assert resultado is True
    (status,) = conn.execute("SELECT status FROM assunto_contato WHERE id = ?", (ac_id,)).fetchone()
    assert status == "usado"


def test_marcar_usado_de_novo_nao_muda_nada_e_devolve_false(conn: sqlite3.Connection) -> None:
    ac_id = _criar_assunto_contato(conn, status="usado")

    resultado = assunto_contato.marcar_usado(conn, ac_id)
    conn.commit()

    assert resultado is False
    (status,) = conn.execute("SELECT status FROM assunto_contato WHERE id = ?", (ac_id,)).fetchone()
    assert status == "usado"


def test_marcar_usado_id_inexistente_devolve_false(conn: sqlite3.Connection) -> None:
    assert assunto_contato.marcar_usado(conn, 999) is False


def test_marcar_nao_serve_em_registro_novo_devolve_true_e_grava_motivo(conn: sqlite3.Connection) -> None:
    ac_id = _criar_assunto_contato(conn)

    resultado = assunto_contato.marcar_nao_serve(conn, ac_id, "velho")
    conn.commit()

    assert resultado is True
    linha = conn.execute("SELECT status, motivo FROM assunto_contato WHERE id = ?", (ac_id,)).fetchone()
    assert linha["status"] == "nao_serve"
    assert linha["motivo"] == "velho"


def test_marcar_nao_serve_ja_resolvido_nao_muda_nada_e_devolve_false(conn: sqlite3.Connection) -> None:
    ac_id = _criar_assunto_contato(conn, status="nao_serve")

    resultado = assunto_contato.marcar_nao_serve(conn, ac_id, "raso")
    conn.commit()

    assert resultado is False


def test_marcar_nao_serve_id_inexistente_devolve_false(conn: sqlite3.Connection) -> None:
    assert assunto_contato.marcar_nao_serve(conn, 999, "velho") is False
