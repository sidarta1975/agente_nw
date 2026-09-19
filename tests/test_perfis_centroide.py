from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import perfil_tema, perfis, temas

AGORA = "2026-01-01T00:00:00+00:00"
_PESO_NIVEL = {"dominio": 1.0, "interesse": 0.7, "curiosidade": 0.4}


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


def _vetor(*valores: float) -> list[float]:
    return list(valores) + [0.0] * (1024 - len(valores))


def test_calcular_centroide_com_dois_temas_confirmados_bate_a_conta(conn: sqlite3.Connection) -> None:
    contato = perfis.inserir_ou_atualizar_contato(
        conn, "Fulano", "+5511900000000", None, None, None, None, AGORA
    )
    assert contato.id is not None

    tema_dominio = temas.obter_ou_criar(conn, "tema-dominio", "descrição", [], AGORA)
    assert tema_dominio.id is not None
    temas.gravar_embedding(conn, tema_dominio.id, _vetor(1.0, 0.0))
    perfil_tema.vincular(conn, contato.id, tema_dominio.id, 5, "declarada", "dominio", True, AGORA)

    tema_sem_nivel = temas.obter_ou_criar(conn, "tema-sem-nivel", "descrição", [], AGORA)
    assert tema_sem_nivel.id is not None
    temas.gravar_embedding(conn, tema_sem_nivel.id, _vetor(0.0, 1.0))
    perfil_tema.vincular(conn, contato.id, tema_sem_nivel.id, 1, "declarada", None, True, AGORA)
    conn.commit()

    resultado = perfis.calcular_centroide(conn, contato.id, _PESO_NIVEL)

    assert resultado is not None
    # peso efetivo: tema_dominio = 5 * 1.0 = 5; tema_sem_nivel = 1 * 1.0 (sem nível) = 1
    # média ponderada de (1,0) peso 5 e (0,1) peso 1 = (5/6, 1/6)
    assert round(resultado[0], 6) == round(5 / 6, 6)
    assert round(resultado[1], 6) == round(1 / 6, 6)


def test_calcular_centroide_ignora_tema_nao_confirmado(conn: sqlite3.Connection) -> None:
    contato = perfis.inserir_ou_atualizar_contato(
        conn, "Fulano", "+5511900000000", None, None, None, None, AGORA
    )
    assert contato.id is not None

    tema_confirmado = temas.obter_ou_criar(conn, "tema-confirmado", "descrição", [], AGORA)
    assert tema_confirmado.id is not None
    temas.gravar_embedding(conn, tema_confirmado.id, _vetor(1.0, 0.0))
    perfil_tema.vincular(conn, contato.id, tema_confirmado.id, 3, "declarada", "dominio", True, AGORA)

    tema_nao_confirmado = temas.obter_ou_criar(conn, "tema-nao-confirmado", "descrição", [], AGORA)
    assert tema_nao_confirmado.id is not None
    temas.gravar_embedding(conn, tema_nao_confirmado.id, _vetor(0.0, 1.0))
    perfil_tema.vincular(conn, contato.id, tema_nao_confirmado.id, 5, "declarada", "dominio", False, AGORA)
    conn.commit()

    resultado = perfis.calcular_centroide(conn, contato.id, _PESO_NIVEL)

    assert resultado is not None
    assert round(resultado[0], 6) == 1.0
    assert round(resultado[1], 6) == 0.0


def test_calcular_centroide_sem_tema_confirmado_devolve_none(conn: sqlite3.Connection) -> None:
    contato = perfis.inserir_ou_atualizar_contato(
        conn, "Fulano", "+5511900000000", None, None, None, None, AGORA
    )
    assert contato.id is not None

    assert perfis.calcular_centroide(conn, contato.id, _PESO_NIVEL) is None


def test_gravar_e_obter_centroide_de_perfil_faz_ida_e_volta(conn: sqlite3.Connection) -> None:
    contato = perfis.inserir_ou_atualizar_contato(
        conn, "Fulano", "+5511900000000", None, None, None, None, AGORA
    )
    assert contato.id is not None

    centroide = _vetor(0.3, 0.4)
    perfis.gravar_centroide(conn, contato.id, centroide)
    conn.commit()

    resultado = perfis.obter_centroide(conn, contato.id)
    assert resultado is not None
    assert [round(v, 6) for v in resultado] == centroide


def test_obter_centroide_de_perfil_devolve_none_quando_nao_gravado(conn: sqlite3.Connection) -> None:
    contato = perfis.inserir_ou_atualizar_contato(
        conn, "Fulano", "+5511900000000", None, None, None, None, AGORA
    )
    assert contato.id is not None

    assert perfis.obter_centroide(conn, contato.id) is None
