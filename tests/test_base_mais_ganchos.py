from __future__ import annotations

import sqlite3

import tests.test_redacao_redigir as base
from agente_nw.nucleo import redacao as redacao_mod
from agente_nw.nucleo.modelos.redacao import RespostaRedacao

conn = base.conn


def test_com_assuntos_relevantes_sai_a_base_primeiro_e_os_ganchos_de_noticia_depois(
    conn: sqlite3.Connection,
) -> None:
    usuario, contato, resultado = base._montar(conn, n_assuntos=2)
    ids = [item.assunto_id for item in resultado.itens_menu]
    llm = base._LLMFalso(RespostaRedacao(ganchos=[base._gancho(i) for i in ids]))

    redacao = redacao_mod.redigir(llm, conn, base._pedido(), resultado, contato, usuario, base.AGORA)

    assert [g.assunto_id for g in redacao.ganchos] == [None, *ids]
    assert redacao.ganchos[0].e_base and not redacao.ganchos[1].e_base
    assert "mensagem a partir do perfil" not in (redacao.aviso or "")


def test_a_base_listada_depois_dos_ganchos_volta_para_o_primeiro_lugar(conn: sqlite3.Connection) -> None:
    usuario, contato, resultado = base._montar(conn, n_assuntos=1)
    assunto_id = resultado.itens_menu[0].assunto_id
    llm = base._LLMFalso(RespostaRedacao(ganchos=[base._gancho(assunto_id), base._base()]))

    redacao = redacao_mod.redigir(llm, conn, base._pedido(), resultado, contato, usuario, base.AGORA)

    assert [g.assunto_id for g in redacao.ganchos] == [None, assunto_id]


def test_registrar_grava_a_base_e_os_ganchos_e_guarda_a_peculiaridade(conn: sqlite3.Connection) -> None:
    usuario, contato, resultado = base._montar(conn, n_assuntos=1)
    assunto_id = resultado.itens_menu[0].assunto_id
    llm = base._LLMFalso(RespostaRedacao(ganchos=[base._gancho(assunto_id)]))
    redacao = redacao_mod.redigir(llm, conn, base._pedido(), resultado, contato, usuario, base.AGORA)

    redacao_mod.registrar(conn, resultado.consulta_id, redacao, base.AGORA)

    gravados = redacao_mod.ganchos_da_consulta(conn, resultado.consulta_id)
    assert [g.assunto_id for g, _status in gravados] == [None, assunto_id]
    assert gravados[0][0].peculiaridade == "o trabalho com cooperativas de crédito"
