from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import perfil_tema, temas

DESCRICAO = "descrição de exemplo com palavras suficientes"


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


def test_tema_reimportado_nao_duplica(conn: sqlite3.Connection) -> None:
    temas.obter_ou_criar(conn, "corrida", DESCRICAO, [], "2026-01-01")
    temas.obter_ou_criar(conn, "corrida", DESCRICAO, [], "2026-01-02")

    (contagem,) = conn.execute("SELECT COUNT(*) FROM tema WHERE nome = 'corrida'").fetchone()
    assert contagem == 1


def test_perfil_tema_reimportado_nao_duplica(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT INTO perfil (tipo, nome, linguas, criado_em, atualizado_em) "
        "VALUES ('usuario', 'Fulano', '[]', '2026-01-01', '2026-01-01')"
    )
    (perfil_id,) = conn.execute("SELECT id FROM perfil").fetchone()
    tema = temas.obter_ou_criar(conn, "corrida", DESCRICAO, [], "2026-01-01")
    assert tema.id is not None

    perfil_tema.vincular(conn, perfil_id, tema.id, 3, "declarada", "interesse", True, "2026-01-01")
    perfil_tema.vincular(conn, perfil_id, tema.id, 5, "declarada", "dominio", True, "2026-01-02")

    (contagem,) = conn.execute(
        "SELECT COUNT(*) FROM perfil_tema WHERE perfil_id = ? AND tema_id = ?", (perfil_id, tema.id)
    ).fetchone()
    assert contagem == 1


def test_segundo_perfil_usuario_falha(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT INTO perfil (tipo, nome, linguas, criado_em, atualizado_em) "
        "VALUES ('usuario', 'Fulano', '[]', '2026-01-01', '2026-01-01')"
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO perfil (tipo, nome, linguas, criado_em, atualizado_em) "
            "VALUES ('usuario', 'Beltrano', '[]', '2026-01-01', '2026-01-01')"
        )


def test_update_em_fato_falha(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT INTO perfil (tipo, nome, linguas, criado_em, atualizado_em) "
        "VALUES ('contato', 'Fulano', '[]', '2026-01-01', '2026-01-01')"
    )
    (perfil_id,) = conn.execute("SELECT id FROM perfil").fetchone()
    conn.execute(
        "INSERT INTO fato (perfil_id, tipo, conteudo, registrado_em) "
        "VALUES (?, 'publicacao', 'x', '2026-01-01')",
        (perfil_id,),
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE fato SET conteudo = 'y' WHERE perfil_id = ?", (perfil_id,))


def test_delete_em_fato_falha(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT INTO perfil (tipo, nome, linguas, criado_em, atualizado_em) "
        "VALUES ('contato', 'Fulano', '[]', '2026-01-01', '2026-01-01')"
    )
    (perfil_id,) = conn.execute("SELECT id FROM perfil").fetchone()
    conn.execute(
        "INSERT INTO fato (perfil_id, tipo, conteudo, registrado_em) "
        "VALUES (?, 'publicacao', 'x', '2026-01-01')",
        (perfil_id,),
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("DELETE FROM fato WHERE perfil_id = ?", (perfil_id,))


def test_perfil_tema_nivel_invalido_falha(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT INTO perfil (tipo, nome, linguas, criado_em, atualizado_em) "
        "VALUES ('usuario', 'Fulano', '[]', '2026-01-01', '2026-01-01')"
    )
    (perfil_id,) = conn.execute("SELECT id FROM perfil").fetchone()
    tema = temas.obter_ou_criar(conn, "corrida", DESCRICAO, [], "2026-01-01")

    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO perfil_tema (perfil_id, tema_id, peso, origem, confirmado, nivel, registrado_em) "
            "VALUES (?, ?, 3, 'declarada', 1, 'outro', '2026-01-01')",
            (perfil_id, tema.id),
        )
