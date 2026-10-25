from __future__ import annotations

import sqlite3

import pytest

import tests.test_redacao_redigir as base
from agente_nw.nucleo.database.queries import nota_contato, pedidos, perfis

conn = base.conn


def test_nota_do_pedido_e_nota_geral_sao_recuperaveis_por_contato(conn: sqlite3.Connection) -> None:
    _usuario, contato, _resultado = base._montar(conn, n_assuntos=0)
    assert contato.id is not None
    pedido = pedidos.inserir(conn, "pedido sobre Irene", base.AGORA, None, contato.id)
    nota_contato.inserir(conn, contato.id, "trocou de escritório", "2026-10-10T10:00:00+00:00")
    nota_contato.inserir(conn, contato.id, "foca na OAB", "2026-10-11T10:00:00+00:00", pedido)

    notas = nota_contato.listar_por_perfil(conn, contato.id)

    assert [(n.texto, n.pedido_id) for n in notas] == [
        ("foca na OAB", pedido),
        ("trocou de escritório", None),
    ]
    assert [n.texto for n in nota_contato.listar_por_pedido(conn, pedido)] == ["foca na OAB"]
    assert [n.texto for n in nota_contato.listar_por_perfil(conn, contato.id, 1)] == ["foca na OAB"]


def test_nota_vazia_e_recusada_pelo_banco(conn: sqlite3.Connection) -> None:
    _usuario, contato, _resultado = base._montar(conn, n_assuntos=0)
    assert contato.id is not None

    with pytest.raises(sqlite3.IntegrityError):
        nota_contato.inserir(conn, contato.id, "   ", base.AGORA)


def test_unir_contatos_leva_as_notas_para_o_canonico(conn: sqlite3.Connection) -> None:
    _usuario, contato, _resultado = base._montar(conn, n_assuntos=0)
    assert contato.id is not None
    outro = perfis.inserir_novo_contato(conn, "Irene D.", None, None, base.AGORA)
    assert outro.id is not None
    nota_contato.inserir(conn, outro.id, "nota do duplicado", base.AGORA)

    perfis.unir_contatos(conn, contato.id, outro.id)

    assert [n.texto for n in nota_contato.listar_por_perfil(conn, contato.id)] == ["nota do duplicado"]


def test_apagar_contato_apaga_as_notas_dele(conn: sqlite3.Connection) -> None:
    novo = perfis.inserir_novo_contato(conn, "Sem histórico", None, None, base.AGORA)
    assert novo.id is not None
    nota_contato.inserir(conn, novo.id, "anotação", base.AGORA)

    perfis.apagar_contato_completo(conn, novo.id)

    assert conn.execute("SELECT COUNT(*) FROM nota_contato").fetchone()[0] == 0
