from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

import agente_nw.cli as cli
from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import perfil_tema, perfis, temas


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


def _criar_contato_com_tags(conn: sqlite3.Connection, telefone: str, n_tags: int) -> int:
    agora = "2026-01-01T00:00:00+00:00"
    perfil = perfis.inserir_ou_atualizar_contato(
        conn, "Fulano de Teste", telefone, None, None, None, None, agora
    )
    assert perfil.id is not None
    for i in range(n_tags):
        tema = temas.obter_ou_criar(conn, f"tema-teste-{i}", f"descrição do tema teste {i}", [], agora)
        assert tema.id is not None
        perfil_tema.vincular(conn, perfil.id, tema.id, 3, "importada", None, False, agora)
    conn.commit()
    return perfil.id


def test_ficha_de_telefone_inexistente_nao_da_traceback(
    monkeypatch: pytest.MonkeyPatch, conn: sqlite3.Connection
) -> None:
    monkeypatch.setattr(cli, "banco", lambda: conn)
    resultado = cli.ficha_cmd("+5511900000000")
    assert resultado == 1


def test_confirmar_tags_com_indice_valido_e_invalido(
    monkeypatch: pytest.MonkeyPatch, conn: sqlite3.Connection
) -> None:
    monkeypatch.setattr(cli, "banco", lambda: conn)
    perfil_id = _criar_contato_com_tags(conn, "+5511911111111", 2)

    resultado = cli.confirmar_tags_cmd("+5511911111111", todas=False, ids="1,99")
    assert resultado == 0

    tags = perfil_tema.listar_por_perfil(conn, perfil_id)
    confirmadas = [tag for tag in tags if tag.confirmado]
    assert len(confirmadas) == 1


def test_confirmar_tags_todas_confirma_todas_as_pendentes(
    monkeypatch: pytest.MonkeyPatch, conn: sqlite3.Connection
) -> None:
    monkeypatch.setattr(cli, "banco", lambda: conn)
    perfil_id = _criar_contato_com_tags(conn, "+5511922222222", 3)

    resultado = cli.confirmar_tags_cmd("+5511922222222", todas=True, ids=None)
    assert resultado == 0

    tags = perfil_tema.listar_por_perfil(conn, perfil_id)
    assert all(tag.confirmado for tag in tags)
