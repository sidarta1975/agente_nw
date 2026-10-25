from __future__ import annotations

import sqlite3

import tests.test_redacao_redigir as base
from agente_nw.nucleo import redacao as redacao_mod
from agente_nw.nucleo.database.queries import gancho_uso, nota_contato
from agente_nw.nucleo.modelos.redacao import RespostaRedacao

conn = base.conn


def test_comentario_de_mensagem_anterior_e_nota_do_contato_vao_no_historico_do_prompt(
    conn: sqlite3.Connection,
) -> None:
    usuario, contato, resultado = base._montar(conn, n_assuntos=0)
    assert contato.id is not None
    anterior = base._consulta_anterior(conn, contato)
    gancho_uso.inserir_entregues(conn, anterior, [(None, base._base().model_dump_json())], base.AGORA)
    gancho_uso.marcar(conn, anterior, None, "nao_serve", base.AGORA)
    gancho_uso.comentar(conn, anterior, None, "não serve porque ficou política nacional", base.AGORA)
    nota_contato.inserir(conn, contato.id, "trocou de escritório", "2026-10-10T10:00:00+00:00")
    llm = base._LLMFalso(RespostaRedacao(ganchos=[base._base()]))

    redacao_mod.redigir(llm, conn, base._pedido(), resultado, contato, usuario, base.AGORA)

    assert 'comentário do usuário: "não serve porque ficou política nacional"' in llm.prompts[0]
    assert "[2026-10-10] trocou de escritório" in llm.prompts[0]
    assert "Notas do usuário sobre esta pessoa" in llm.prompts[0]


def test_sem_comentario_e_sem_nota_o_prompt_nao_ganha_nada(conn: sqlite3.Connection) -> None:
    usuario, contato, resultado = base._montar(conn, n_assuntos=0)
    base._consulta_anterior(conn, contato)
    llm = base._LLMFalso(RespostaRedacao(ganchos=[base._base()]))

    redacao_mod.redigir(llm, conn, base._pedido(), resultado, contato, usuario, base.AGORA)

    assert "comentário do usuário:" not in llm.prompts[0]
    assert "Notas do usuário sobre esta pessoa" not in llm.prompts[0]


def test_so_as_notas_mais_recentes_entram(conn: sqlite3.Connection) -> None:
    usuario, contato, resultado = base._montar(conn, n_assuntos=0)
    assert contato.id is not None
    for i in range(7):
        nota_contato.inserir(conn, contato.id, f"nota {i}", f"2026-10-0{i + 1}T10:00:00+00:00")
    llm = base._LLMFalso(RespostaRedacao(ganchos=[base._base()]))

    redacao_mod.redigir(llm, conn, base._pedido(), resultado, contato, usuario, base.AGORA)

    assert "nota 6" in llm.prompts[0] and "nota 2" in llm.prompts[0]
    assert "nota 1" not in llm.prompts[0] and "nota 0" not in llm.prompts[0]
