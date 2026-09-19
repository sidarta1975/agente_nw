from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import assunto_contato, assuntos, perfis
from agente_nw.nucleo.modelos.assunto import Assunto
from agente_nw.nucleo.modelos.assunto_contato import AssuntoContato
from agente_nw.nucleo.relevancia.candidatos import selecionar

AGORA = "2026-01-01T00:00:00+00:00"


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


def _vetor(*valores: float) -> list[float]:
    return list(valores) + [0.0] * (1024 - len(valores))


def _criar_assunto_qualificado(
    conn: sqlite3.Connection, centroide: list[float], substancial: float = 0.8, conversavel: float = 0.8
) -> int:
    assunto = Assunto(
        primeiro_visto=AGORA,
        ultimo_visto=AGORA,
        n_itens=1,
        status="novo",
        substancial=substancial,
        conversavel=conversavel,
    )
    assunto_id = assuntos.inserir(conn, assunto)
    assuntos.gravar_centroide(conn, assunto_id, centroide)
    return assunto_id


def _criar_contato(conn: sqlite3.Connection, telefone: str) -> int:
    contato = perfis.inserir_ou_atualizar_contato(conn, "Fulano", telefone, None, None, None, None, AGORA)
    assert contato.id is not None
    return contato.id


def test_assunto_ja_visto_nao_volta_a_ser_candidato(conn: sqlite3.Connection) -> None:
    perfil_id = _criar_contato(conn, "+5511900000000")
    ja_visto = _criar_assunto_qualificado(conn, _vetor(1.0, 0.0))
    novo = _criar_assunto_qualificado(conn, _vetor(1.0, 0.0))
    conn.commit()

    registro = AssuntoContato(
        assunto_id=ja_visto,
        perfil_id=perfil_id,
        gerado_em="2026-09-19",
        tipo="conector",
        aderencia_contato=0.7,
        aderencia_usuario=0.6,
        conversavel=0.5,
        score=65.0,
        status="novo",
    )
    assunto_contato.inserir(conn, registro)
    conn.commit()

    resultado = selecionar(conn, perfil_id, _vetor(1.0, 0.0), 0.6, 0.6, 10)

    ids = [a.id for a in resultado]
    assert novo in ids
    assert ja_visto not in ids


def test_corte_de_qualificacao_e_respeitado(conn: sqlite3.Connection) -> None:
    perfil_id = _criar_contato(conn, "+5511900000000")
    abaixo_substancial = _criar_assunto_qualificado(conn, _vetor(1.0, 0.0), substancial=0.3, conversavel=0.8)
    abaixo_conversavel = _criar_assunto_qualificado(conn, _vetor(1.0, 0.0), substancial=0.8, conversavel=0.3)
    passa = _criar_assunto_qualificado(conn, _vetor(1.0, 0.0), substancial=0.8, conversavel=0.8)
    conn.commit()

    resultado = selecionar(conn, perfil_id, _vetor(1.0, 0.0), 0.6, 0.6, 10)

    ids = [a.id for a in resultado]
    assert ids == [passa]
    assert abaixo_substancial not in ids
    assert abaixo_conversavel not in ids


def test_ordenacao_por_aderencia_ao_contato(conn: sqlite3.Connection) -> None:
    perfil_id = _criar_contato(conn, "+5511900000000")
    longe = _criar_assunto_qualificado(conn, _vetor(0.0, 1.0))
    perto = _criar_assunto_qualificado(conn, _vetor(0.99, 0.14))
    conn.commit()

    resultado = selecionar(conn, perfil_id, _vetor(1.0, 0.0), 0.6, 0.6, 10)

    assert [a.id for a in resultado] == [perto, longe]


def test_respeita_limite(conn: sqlite3.Connection) -> None:
    perfil_id = _criar_contato(conn, "+5511900000000")
    for _ in range(5):
        _criar_assunto_qualificado(conn, _vetor(1.0, 0.0))
    conn.commit()

    resultado = selecionar(conn, perfil_id, _vetor(1.0, 0.0), 0.6, 0.6, 3)

    assert len(resultado) == 3
