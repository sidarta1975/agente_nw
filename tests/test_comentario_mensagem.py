from __future__ import annotations

import sqlite3

import tests.test_redacao_redigir as base
from agente_nw.nucleo.database.queries import gancho_uso

conn = base.conn


def _com_ganchos(conn: sqlite3.Connection) -> tuple[int, int]:
    _usuario, _contato, resultado = base._montar(conn, n_assuntos=1)
    assunto_id = resultado.itens_menu[0].assunto_id
    gancho_uso.inserir_entregues(conn, resultado.consulta_id, [(None, "{}"), (assunto_id, "{}")], base.AGORA)
    return resultado.consulta_id, assunto_id


def test_comentar_a_mensagem_base_e_a_de_noticia_persiste_em_cada_uma(conn: sqlite3.Connection) -> None:
    consulta_id, assunto_id = _com_ganchos(conn)

    assert gancho_uso.comentar(conn, consulta_id, None, "ótima peculiaridade", base.AGORA) is True
    assert gancho_uso.comentar(conn, consulta_id, assunto_id, "queria da OAB", base.AGORA) is True

    assert gancho_uso.comentarios_por_consulta(conn, consulta_id) == {
        None: "ótima peculiaridade",
        assunto_id: "queria da OAB",
    }


def test_sem_comentario_nada_aparece_e_o_status_nao_muda(conn: sqlite3.Connection) -> None:
    consulta_id, assunto_id = _com_ganchos(conn)
    gancho_uso.marcar(conn, consulta_id, assunto_id, "usado", base.AGORA)

    assert gancho_uso.comentarios_por_consulta(conn, consulta_id) == {}
    gancho_uso.comentar(conn, consulta_id, assunto_id, "serviu", base.AGORA)
    assert gancho_uso.listar_por_consulta(conn, consulta_id)[1][1] == "usado"


def test_comentario_vazio_apaga_e_texto_e_aparado(conn: sqlite3.Connection) -> None:
    consulta_id, _assunto_id = _com_ganchos(conn)
    gancho_uso.comentar(conn, consulta_id, None, "  serviu  ", base.AGORA)
    assert gancho_uso.comentarios_por_consulta(conn, consulta_id) == {None: "serviu"}

    gancho_uso.comentar(conn, consulta_id, None, "   ", base.AGORA)

    assert gancho_uso.comentarios_por_consulta(conn, consulta_id) == {}


def test_comentar_mensagem_que_nao_existe_devolve_falso(conn: sqlite3.Connection) -> None:
    consulta_id, _assunto_id = _com_ganchos(conn)

    assert gancho_uso.comentar(conn, consulta_id, 99999, "x", base.AGORA) is False
