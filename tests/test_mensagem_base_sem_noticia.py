from __future__ import annotations

import sqlite3

import tests.test_redacao_redigir as base
from agente_nw.nucleo import redacao as redacao_mod
from agente_nw.nucleo.modelos.redacao import RespostaRedacao

conn = base.conn


def test_sem_assunto_o_modelo_e_chamado_e_sai_a_mensagem_base(conn: sqlite3.Connection) -> None:
    usuario, contato, resultado = base._montar(conn, n_assuntos=0)
    llm = base._LLMFalso(RespostaRedacao(ganchos=[base._base()]))

    redacao = redacao_mod.redigir(llm, conn, base._pedido(), resultado, contato, usuario, base.AGORA)

    assert len(llm.prompts) == 1
    assert [g.assunto_id for g in redacao.ganchos] == [None]
    assert redacao.ganchos[0].e_base and redacao.ganchos[0].noticia is None


def test_o_aviso_sem_noticia_e_informativo_e_nao_manda_desistir(conn: sqlite3.Connection) -> None:
    usuario, contato, resultado = base._montar(conn, n_assuntos=0)
    llm = base._LLMFalso(RespostaRedacao(ganchos=[base._base()]))

    redacao = redacao_mod.redigir(llm, conn, base._pedido(), resultado, contato, usuario, base.AGORA)

    assert redacao.aviso is not None
    assert "mensagem a partir do perfil" in redacao.aviso
    assert "Tente outro assunto" not in redacao.aviso


def test_o_prompt_diz_que_a_noticia_e_opcional_e_a_base_vem_primeiro(conn: sqlite3.Connection) -> None:
    usuario, contato, resultado = base._montar(conn, n_assuntos=0)
    llm = base._LLMFalso(RespostaRedacao(ganchos=[base._base()]))

    redacao_mod.redigir(llm, conn, base._pedido(), resultado, contato, usuario, base.AGORA)

    prompt = llm.prompts[0]
    assert "a notícia é opcional" in prompt
    assert "(nenhum — escreva só a mensagem base)" in prompt
    assert '"assunto_id": null' in prompt
