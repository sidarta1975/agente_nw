from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import consulta_contato as queries

AGORA = "2026-09-20T10:00:00+00:00"


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

    resultado = queries.inserir(
        conn,
        perfil_id,
        AGORA,
        '{"assunto": "reunião"}',
        "postou um artigo sobre vela oceânica",
        '[{"titulo": "regata oficial"}]',
    )
    conn.commit()

    assert resultado.id is not None
    assert resultado.perfil_id == perfil_id
    assert resultado.contexto_json == '{"assunto": "reunião"}'
    assert resultado.resumo_redes_sociais == "postou um artigo sobre vela oceânica"
    assert resultado.assuntos_entregues_json == '[{"titulo": "regata oficial"}]'


def test_listar_por_perfil_ordena_da_mais_recente_para_a_mais_antiga(conn: sqlite3.Connection) -> None:
    perfil_id = _criar_contato(conn, "Beto")
    queries.inserir(conn, perfil_id, "2026-09-18T10:00:00+00:00", "{}", None, "[]")
    queries.inserir(conn, perfil_id, "2026-09-20T10:00:00+00:00", "{}", None, "[]")
    queries.inserir(conn, perfil_id, "2026-09-19T10:00:00+00:00", "{}", None, "[]")
    conn.commit()

    resultado = queries.listar_por_perfil(conn, perfil_id)

    datas = [c.criado_em for c in resultado]
    assert datas == [
        "2026-09-20T10:00:00+00:00",
        "2026-09-19T10:00:00+00:00",
        "2026-09-18T10:00:00+00:00",
    ]


def test_listar_por_perfil_respeita_limite(conn: sqlite3.Connection) -> None:
    perfil_id = _criar_contato(conn, "Carla")
    for dia in ("2026-09-16", "2026-09-17", "2026-09-18", "2026-09-19", "2026-09-20"):
        queries.inserir(conn, perfil_id, f"{dia}T10:00:00+00:00", "{}", None, "[]")
    conn.commit()

    resultado = queries.listar_por_perfil(conn, perfil_id, limite=3)

    assert [c.criado_em[:10] for c in resultado] == ["2026-09-20", "2026-09-19", "2026-09-18"]


def test_listar_por_perfil_sem_registro_devolve_lista_vazia(conn: sqlite3.Connection) -> None:
    perfil_id = _criar_contato(conn, "Dora")

    resultado = queries.listar_por_perfil(conn, perfil_id)

    assert resultado == []


def test_update_na_tabela_falha_por_trigger(conn: sqlite3.Connection) -> None:
    perfil_id = _criar_contato(conn, "Elza")
    linha = queries.inserir(conn, perfil_id, AGORA, "{}", None, "[]")
    conn.commit()
    assert linha.id is not None

    with pytest.raises(sqlite3.IntegrityError, match="consulta_contato é só inserção"):
        conn.execute("UPDATE consulta_contato SET contexto_json = '{}' WHERE id = ?", (linha.id,))


def test_delete_na_tabela_falha_por_trigger(conn: sqlite3.Connection) -> None:
    perfil_id = _criar_contato(conn, "Fabio")
    linha = queries.inserir(conn, perfil_id, AGORA, "{}", None, "[]")
    conn.commit()
    assert linha.id is not None

    with pytest.raises(sqlite3.IntegrityError, match="consulta_contato é só inserção"):
        conn.execute("DELETE FROM consulta_contato WHERE id = ?", (linha.id,))
