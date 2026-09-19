from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import assuntos, fontes, itens
from agente_nw.nucleo.modelos.assunto import Assunto
from agente_nw.nucleo.modelos.item import Item

AGORA = "2026-09-18T00:00:00+00:00"
_DIM = 1024


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


def _vetor(*valores: float) -> list[float]:
    return list(valores) + [0.0] * (_DIM - len(valores))


def _criar_fonte(conn: sqlite3.Connection, dominio: str) -> int:
    fonte = fontes.obter_ou_criar(conn, dominio, f"https://{dominio}/rss", dominio, "rss", 5)
    assert fonte.id is not None
    return fonte.id


def _criar_item(conn: sqlite3.Connection, fonte_id: int, sufixo: str) -> int:
    item = Item(
        fonte_id=fonte_id,
        url_canonica=f"https://exemplo.com/materia-{sufixo}",
        titulo=f"Título {sufixo}",
        texto="Texto de exemplo.",
        publicado_em=AGORA,
        coletado_em=AGORA,
        hash_titulo=f"hash-{sufixo}",
    )
    return itens.inserir(conn, item)


def _criar_assunto(conn: sqlite3.Connection) -> int:
    assunto = Assunto(primeiro_visto=AGORA, ultimo_visto=AGORA, n_itens=0, status="novo")
    assunto_id = assuntos.inserir(conn, assunto)
    conn.commit()
    return assunto_id


def test_listar_sem_assunto_devolve_apenas_itens_nao_vinculados(conn: sqlite3.Connection) -> None:
    fonte_id = _criar_fonte(conn, "g1.globo.com")
    id1 = _criar_item(conn, fonte_id, "a")
    _criar_item(conn, fonte_id, "b")
    conn.commit()
    assunto_id = _criar_assunto(conn)

    itens.vincular_assunto(conn, id1, assunto_id)
    conn.commit()

    pendentes = itens.listar_sem_assunto(conn, 10)

    assert [item.titulo for item in pendentes] == ["Título b"]


def test_gravar_e_obter_embedding_faz_ida_e_volta(conn: sqlite3.Connection) -> None:
    fonte_id = _criar_fonte(conn, "g1.globo.com")
    item_id = _criar_item(conn, fonte_id, "a")
    conn.commit()

    embedding = _vetor(0.1, 0.2, 0.3, 0.4)
    itens.gravar_embedding(conn, item_id, embedding)
    conn.commit()

    resultado = itens.obter_embedding(conn, item_id)

    assert resultado is not None
    assert [round(v, 6) for v in resultado] == embedding


def test_obter_embedding_devolve_none_quando_nao_gravado(conn: sqlite3.Connection) -> None:
    fonte_id = _criar_fonte(conn, "g1.globo.com")
    item_id = _criar_item(conn, fonte_id, "a")
    conn.commit()

    assert itens.obter_embedding(conn, item_id) is None


def test_gravar_embedding_duas_vezes_substitui_nao_duplica(conn: sqlite3.Connection) -> None:
    fonte_id = _criar_fonte(conn, "g1.globo.com")
    item_id = _criar_item(conn, fonte_id, "a")
    conn.commit()

    itens.gravar_embedding(conn, item_id, _vetor(0.1, 0.2, 0.3, 0.4))
    itens.gravar_embedding(conn, item_id, _vetor(0.5, 0.6, 0.7, 0.8))
    conn.commit()

    (n,) = conn.execute("SELECT COUNT(*) FROM vetor_item WHERE item_id = ?", (item_id,)).fetchone()
    resultado = itens.obter_embedding(conn, item_id)

    assert n == 1
    assert resultado is not None
    assert [round(v, 6) for v in resultado] == _vetor(0.5, 0.6, 0.7, 0.8)


def test_vincular_assunto_atualiza_coluna(conn: sqlite3.Connection) -> None:
    fonte_id = _criar_fonte(conn, "g1.globo.com")
    item_id = _criar_item(conn, fonte_id, "a")
    conn.commit()
    assunto_id = _criar_assunto(conn)

    itens.vincular_assunto(conn, item_id, assunto_id)
    conn.commit()

    (resultado,) = conn.execute("SELECT assunto_id FROM item WHERE id = ?", (item_id,)).fetchone()
    assert resultado == assunto_id


def test_listar_por_assunto_traz_dominio_da_fonte_em_ordem(conn: sqlite3.Connection) -> None:
    fonte_g1 = _criar_fonte(conn, "g1.globo.com")
    fonte_uol = _criar_fonte(conn, "uol.com.br")
    id1 = _criar_item(conn, fonte_g1, "a")
    id2 = _criar_item(conn, fonte_uol, "b")
    conn.commit()
    assunto_id = _criar_assunto(conn)

    itens.vincular_assunto(conn, id1, assunto_id)
    itens.vincular_assunto(conn, id2, assunto_id)
    conn.commit()

    resultado = itens.listar_por_assunto(conn, assunto_id)

    assert [(r.item.id, r.dominio) for r in resultado] == [(id1, "g1.globo.com"), (id2, "uol.com.br")]


def test_listar_com_embedding_so_traz_itens_com_vetor_gravado(conn: sqlite3.Connection) -> None:
    fonte_id = _criar_fonte(conn, "g1.globo.com")
    id_com = _criar_item(conn, fonte_id, "a")
    _criar_item(conn, fonte_id, "b")
    conn.commit()

    embedding = _vetor(0.1, 0.2, 0.3, 0.4)
    itens.gravar_embedding(conn, id_com, embedding)
    conn.commit()

    resultado = itens.listar_com_embedding(conn)

    assert len(resultado) == 1
    item, resultado_embedding = resultado[0]
    assert item.id == id_com
    assert [round(v, 6) for v in resultado_embedding] == embedding
