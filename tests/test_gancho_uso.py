from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import assuntos as assuntos_q
from agente_nw.nucleo.database.queries import consulta_contato as consulta_contato_q
from agente_nw.nucleo.database.queries import gancho_uso, perfis
from agente_nw.nucleo.modelos.assunto import Assunto

AGORA = "2026-10-12T10:00:00+00:00"
DEPOIS = "2026-10-12T11:00:00+00:00"


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


def _assunto(conn: sqlite3.Connection, titulo: str) -> int:
    return assuntos_q.inserir(
        conn, Assunto(titulo_gerado=titulo, primeiro_visto=AGORA, ultimo_visto=AGORA, status="novo")
    )


def _consulta(conn: sqlite3.Connection, perfil_id: int, quando: str = AGORA) -> int:
    consulta = consulta_contato_q.inserir(conn, perfil_id, quando, "{}", None, "[]")
    assert consulta.id is not None
    return consulta.id


def _contato(conn: sqlite3.Connection, nome: str) -> int:
    perfil = perfis.inserir_novo_contato(conn, nome, None, None, AGORA)
    assert perfil.id is not None
    return perfil.id


def test_inserir_entregues_grava_com_status_entregue(conn: sqlite3.Connection) -> None:
    perfil_id = _contato(conn, "Irene Duarte")
    consulta_id = _consulta(conn, perfil_id)
    primeiro, segundo = _assunto(conn, "um"), _assunto(conn, "dois")

    gancho_uso.inserir_entregues(conn, consulta_id, [(primeiro, '{"titulo": "um"}'), (segundo, "{}")], AGORA)

    assert gancho_uso.listar_por_consulta(conn, consulta_id) == [
        (primeiro, "entregue", '{"titulo": "um"}'),
        (segundo, "entregue", "{}"),
    ]


def test_marcar_muda_o_status_e_devolve_se_achou(conn: sqlite3.Connection) -> None:
    perfil_id = _contato(conn, "Irene Duarte")
    consulta_id = _consulta(conn, perfil_id)
    assunto_id = _assunto(conn, "um")
    gancho_uso.inserir_entregues(conn, consulta_id, [(assunto_id, "{}")], AGORA)

    assert gancho_uso.marcar(conn, consulta_id, assunto_id, "usado", DEPOIS) is True
    assert gancho_uso.marcar(conn, consulta_id, 9999, "usado", DEPOIS) is False

    assert gancho_uso.listar_por_consulta(conn, consulta_id)[0][1] == "usado"


def test_assuntos_usados_do_perfil_lista_so_os_usados_daquele_contato(conn: sqlite3.Connection) -> None:
    irene, paulo = _contato(conn, "Irene Duarte"), _contato(conn, "Paulo Bastos")
    usado, entregue, nao_serve, de_outro = (_assunto(conn, n) for n in ("a", "b", "c", "d"))
    consulta_irene, consulta_paulo = _consulta(conn, irene), _consulta(conn, paulo)
    gancho_uso.inserir_entregues(
        conn, consulta_irene, [(usado, "{}"), (entregue, "{}"), (nao_serve, "{}")], AGORA
    )
    gancho_uso.inserir_entregues(conn, consulta_paulo, [(de_outro, "{}")], AGORA)
    gancho_uso.marcar(conn, consulta_irene, usado, "usado", DEPOIS)
    gancho_uso.marcar(conn, consulta_irene, nao_serve, "nao_serve", DEPOIS)
    gancho_uso.marcar(conn, consulta_paulo, de_outro, "usado", DEPOIS)

    assert gancho_uso.assuntos_usados_do_perfil(conn, irene) == {usado}
    assert gancho_uso.assuntos_usados_do_perfil(conn, paulo) == {de_outro}


def test_status_invalido_e_recusado_pelo_banco(conn: sqlite3.Connection) -> None:
    perfil_id = _contato(conn, "Irene Duarte")
    consulta_id = _consulta(conn, perfil_id)
    assunto_id = _assunto(conn, "um")
    gancho_uso.inserir_entregues(conn, consulta_id, [(assunto_id, "{}")], AGORA)

    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE gancho_uso SET status = 'qualquer'")
