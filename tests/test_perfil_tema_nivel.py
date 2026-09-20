from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import perfil_tema, perfis, temas

AGORA = "2026-01-02T00:00:00+00:00"


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


def test_atualizar_nivel_troca_o_nivel_sem_alterar_outros_campos(conn: sqlite3.Connection) -> None:
    usuario = perfis.upsert_usuario(conn, "Fulano", AGORA)
    tema = temas.obter_ou_criar(conn, "direito tributário", "reforma tributária e split payment", [], AGORA)
    assert usuario.id is not None and tema.id is not None
    perfil_tema.vincular(conn, usuario.id, tema.id, 5, "declarada", "interesse", True, AGORA)
    conn.commit()

    perfil_tema.atualizar_nivel(conn, usuario.id, tema.id, "dominio")
    conn.commit()

    (vinculo,) = perfil_tema.listar_por_perfil(conn, usuario.id)
    assert vinculo.nivel == "dominio"
    assert vinculo.peso == 5
    assert vinculo.confirmado is True
