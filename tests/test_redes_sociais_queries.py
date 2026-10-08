from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import redes_sociais

AGORA = "2026-09-20T00:00:00+00:00"


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


def _criar_contato(conn: sqlite3.Connection, nome: str) -> int:
    cursor = conn.execute(
        "INSERT INTO perfil (tipo, nome, linguas, ativo, criado_em, atualizado_em) "
        "VALUES ('contato', ?, '[]', 0, ?, ?)",
        (nome, AGORA, AGORA),
    )
    conn.commit()
    assert cursor.lastrowid is not None
    return cursor.lastrowid


def test_inserir_devolve_registro_com_id_e_persiste(conn: sqlite3.Connection) -> None:
    perfil_id = _criar_contato(conn, "Ana")

    resultado = redes_sociais.inserir(conn, perfil_id, "linkedin", "https://linkedin.com/in/ana", AGORA)
    conn.commit()

    assert resultado.id is not None
    assert resultado.perfil_id == perfil_id
    assert resultado.rede == "linkedin"
    assert resultado.link == "https://linkedin.com/in/ana"
    assert resultado.criado_em == AGORA


def test_listar_por_perfil_devolve_multiplas_em_ordem_de_id(conn: sqlite3.Connection) -> None:
    perfil_id = _criar_contato(conn, "Beto")
    redes_sociais.inserir(conn, perfil_id, "instagram", "https://instagram.com/beto", AGORA)
    redes_sociais.inserir(conn, perfil_id, "x", "https://x.com/beto", AGORA)
    conn.commit()

    resultado = redes_sociais.listar_por_perfil(conn, perfil_id)

    assert [r.rede for r in resultado] == ["instagram", "x"]


def test_listar_por_perfil_sem_registro_devolve_lista_vazia(conn: sqlite3.Connection) -> None:
    perfil_id = _criar_contato(conn, "Carla")

    resultado = redes_sociais.listar_por_perfil(conn, perfil_id)

    assert resultado == []


def test_remover_apaga_apenas_a_linha_indicada(conn: sqlite3.Connection) -> None:
    perfil_id = _criar_contato(conn, "Dora")
    primeira = redes_sociais.inserir(conn, perfil_id, "linkedin", "https://linkedin.com/in/dora", AGORA)
    segunda = redes_sociais.inserir(conn, perfil_id, "facebook", "https://facebook.com/dora", AGORA)
    conn.commit()
    assert primeira.id is not None and segunda.id is not None

    removeu = redes_sociais.remover(conn, primeira.id)
    conn.commit()

    assert removeu is True
    restantes = redes_sociais.listar_por_perfil(conn, perfil_id)
    assert [r.id for r in restantes] == [segunda.id]


def test_remover_id_inexistente_devolve_falso(conn: sqlite3.Connection) -> None:
    removeu = redes_sociais.remover(conn, 9999)

    assert removeu is False
