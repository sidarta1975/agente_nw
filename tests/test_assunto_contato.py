from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import assunto_contato, assuntos, perfis
from agente_nw.nucleo.modelos.assunto import Assunto
from agente_nw.nucleo.modelos.assunto_contato import AssuntoContato

AGORA = "2026-01-01T00:00:00+00:00"


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


def _criar_assunto(conn: sqlite3.Connection) -> int:
    assunto = Assunto(primeiro_visto=AGORA, ultimo_visto=AGORA, n_itens=1, status="novo")
    return assuntos.inserir(conn, assunto)


def _criar_contato(conn: sqlite3.Connection, telefone: str) -> int:
    contato = perfis.inserir_ou_atualizar_contato(conn, "Fulano", telefone, None, None, None, None, AGORA)
    assert contato.id is not None
    return contato.id


def _assunto_contato(assunto_id: int, perfil_id: int, tipo: str = "conector") -> AssuntoContato:
    return AssuntoContato(
        assunto_id=assunto_id,
        perfil_id=perfil_id,
        gerado_em="2026-09-19",
        tipo=tipo,  # type: ignore[arg-type]
        aderencia_contato=0.7,
        aderencia_usuario=0.6,
        conversavel=0.5,
        score=65.0,
        status="novo",
    )


def test_inserir_duas_vezes_mesma_tripla_nao_duplica(conn: sqlite3.Connection) -> None:
    assunto_id = _criar_assunto(conn)
    perfil_id = _criar_contato(conn, "+5511900000000")
    conn.commit()

    primeira = assunto_contato.inserir(conn, _assunto_contato(assunto_id, perfil_id))
    segunda = assunto_contato.inserir(conn, _assunto_contato(assunto_id, perfil_id))
    conn.commit()

    assert primeira is True
    assert segunda is False
    (n,) = conn.execute("SELECT COUNT(*) FROM assunto_contato").fetchone()
    assert n == 1


def test_listar_do_dia_traz_so_o_dia_pedido(conn: sqlite3.Connection) -> None:
    assunto_id = _criar_assunto(conn)
    perfil_id = _criar_contato(conn, "+5511900000000")
    conn.commit()

    registro = _assunto_contato(assunto_id, perfil_id)
    assunto_contato.inserir(conn, registro)
    conn.commit()

    resultado = assunto_contato.listar_do_dia(conn, perfil_id, "2026-09-19")
    assert len(resultado) == 1
    assert resultado[0].assunto_id == assunto_id

    assert assunto_contato.listar_do_dia(conn, perfil_id, "2026-09-20") == []


def test_listar_assunto_ids_ja_vistos_pega_qualquer_status(conn: sqlite3.Connection) -> None:
    perfil_id = _criar_contato(conn, "+5511900000000")
    assunto_novo = _criar_assunto(conn)
    assunto_descartado = _criar_assunto(conn)
    assunto_usado = _criar_assunto(conn)
    conn.commit()

    assunto_contato.inserir(conn, _assunto_contato(assunto_novo, perfil_id))
    registro_descartado = AssuntoContato(
        assunto_id=assunto_descartado,
        perfil_id=perfil_id,
        gerado_em="2026-09-19",
        tipo="fora_do_dominio",
        aderencia_contato=0.1,
        aderencia_usuario=0.1,
        conversavel=0.1,
        score=5.0,
        status="descartado",
        motivo="fora do domínio",
    )
    assunto_contato.inserir(conn, registro_descartado)
    registro_usado = _assunto_contato(assunto_usado, perfil_id)
    assunto_contato.inserir(conn, registro_usado)
    conn.commit()
    conn.execute("UPDATE assunto_contato SET status = 'usado' WHERE assunto_id = ?", (assunto_usado,))
    conn.commit()

    vistos = assunto_contato.listar_assunto_ids_ja_vistos(conn, perfil_id)

    assert vistos == {assunto_novo, assunto_descartado, assunto_usado}


def test_listar_assunto_ids_ja_vistos_nao_pega_de_outro_contato(conn: sqlite3.Connection) -> None:
    perfil_a = _criar_contato(conn, "+5511900000000")
    perfil_b = _criar_contato(conn, "+5511911111111")
    assunto_id = _criar_assunto(conn)
    conn.commit()

    assunto_contato.inserir(conn, _assunto_contato(assunto_id, perfil_a))
    conn.commit()

    assert assunto_contato.listar_assunto_ids_ja_vistos(conn, perfil_a) == {assunto_id}
    assert assunto_contato.listar_assunto_ids_ja_vistos(conn, perfil_b) == set()
