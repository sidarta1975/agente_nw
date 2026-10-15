from __future__ import annotations

import sqlite3

import tests.test_redacao_redigir as base
from agente_nw.nucleo import redacao as redacao_mod
from agente_nw.nucleo.database.queries import fatos as fatos_q
from agente_nw.nucleo.modelos.fato import Fato
from agente_nw.nucleo.modelos.redacao import Gancho, RespostaRedacao

conn = base.conn


def test_os_fatos_da_pessoa_vao_no_prompt_para_a_base_citar_uma_peculiaridade(
    conn: sqlite3.Connection,
) -> None:
    usuario, contato, resultado = base._montar(conn, n_assuntos=0)
    assert contato.id is not None
    fatos_q.inserir(
        conn,
        Fato(
            perfil_id=contato.id,
            tipo="post",
            conteudo="Irene publicou fotos da regata de cooperativas em Santos.",
            registrado_em="2026-10-10T10:00:00+00:00",
        ),
    )
    conn.commit()
    peculiar = Gancho(
        peculiaridade="a regata de cooperativas em Santos",
        por_que_para_esta_pessoa="Ela publicou sobre a regata.",
        mensagem="Oi, Irene! Vi as fotos da regata de cooperativas em Santos. Vamos jantar na quinta?",
    )
    llm = base._LLMFalso(RespostaRedacao(ganchos=[peculiar]))

    redacao = redacao_mod.redigir(llm, conn, base._pedido(), resultado, contato, usuario, base.AGORA)

    assert "Irene publicou fotos da regata de cooperativas em Santos." in llm.prompts[0]
    assert 'cita uma "peculiaridade" concreta' in llm.prompts[0]
    assert redacao.ganchos[0].peculiaridade == "a regata de cooperativas em Santos"
    assert "Pouca informação" not in (redacao.aviso or "")


def test_sem_nenhum_fato_a_base_sai_pela_ficha_e_o_aviso_diz_que_e_mais_geral(
    conn: sqlite3.Connection,
) -> None:
    usuario, contato, resultado = base._montar(conn, n_assuntos=0)
    geral = Gancho(
        por_que_para_esta_pessoa="Pelo vínculo de turma.",
        mensagem="Oi, Irene! Faz tempo. Vamos marcar um jantar com a turma?",
    )
    llm = base._LLMFalso(RespostaRedacao(ganchos=[geral]))

    redacao = redacao_mod.redigir(llm, conn, base._pedido(), resultado, contato, usuario, base.AGORA)

    assert "Fatos recentes sobre a pessoa: (nenhum)" in llm.prompts[0]
    assert redacao.ganchos[0].peculiaridade is None
    assert redacao.aviso is not None
    assert "Pouca informação sobre a pessoa; mensagem mais geral." in redacao.aviso


def test_o_prompt_proibe_inventar_e_manda_usar_a_ficha_sem_fato(conn: sqlite3.Connection) -> None:
    usuario, contato, resultado = base._montar(conn, n_assuntos=0)
    llm = base._LLMFalso(RespostaRedacao(ganchos=[base._base()]))

    redacao_mod.redigir(llm, conn, base._pedido(), resultado, contato, usuario, base.AGORA)

    assert "não invente nada" in llm.prompts[0]
    assert "Nunca infira opinião, posição ou adesão" in llm.prompts[0]


def test_o_prompt_proibe_inventar_local_data_e_evento_do_convite(conn: sqlite3.Connection) -> None:
    usuario, contato, resultado = base._montar(conn, n_assuntos=0)
    llm = base._LLMFalso(RespostaRedacao(ganchos=[base._base()]))

    redacao_mod.redigir(llm, conn, base._pedido(), resultado, contato, usuario, base.AGORA)

    assert "Não invente local, data, horário, prazo" in llm.prompts[0]
    assert "Um lugar ou evento que aparece nos fatos é da pessoa, não do convite" in llm.prompts[0]


def test_o_prompt_pesa_a_forca_do_vinculo_e_manda_cumprir_a_forma_do_pedido(conn: sqlite3.Connection) -> None:
    usuario, contato, resultado = base._montar(conn, n_assuntos=0)
    llm = base._LLMFalso(RespostaRedacao(ganchos=[base._base()]))

    redacao_mod.redigir(llm, conn, base._pedido(), resultado, contato, usuario, base.AGORA)

    assert "Pese a força do vínculo" in llm.prompts[0]
    assert "Vínculo fraco" in llm.prompts[0]
    assert "mas só se a pessoa não o conhece bem" in llm.prompts[0]
    assert "número de parágrafos" in llm.prompts[0]
