from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from agente_nw.nucleo import redacao as redacao_mod
from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import fatos as fatos_q
from agente_nw.nucleo.database.queries import perfis
from agente_nw.nucleo.modelos.fato import Fato
from agente_nw.nucleo.prompts import redigir_ganchos

HOJE = datetime(2026, 10, 14, tzinfo=UTC)
AGORA = "2026-10-14T10:00:00+00:00"


class _SemEmbeddings:
    pass


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


def _perfil(conn: sqlite3.Connection) -> int:
    contato = perfis.inserir_novo_contato(conn, "Luiz David", None, None, AGORA)
    assert contato.id is not None
    return contato.id


def _fato(conn: sqlite3.Connection, perfil_id: int, tipo: str, conteudo: str, data: str | None) -> None:
    fatos_q.inserir(
        conn,
        Fato(perfil_id=perfil_id, tipo=tipo, conteudo=conteudo, data_do_fato=data, registrado_em=AGORA),
    )
    conn.commit()


def _linhas(conn: sqlite3.Connection, perfil_id: int) -> list[str]:
    return redacao_mod._fatos(conn, perfil_id, _SemEmbeddings(), "eleição", 12, HOJE)


def test_fato_com_data_antiga_vai_marcado(conn: sqlite3.Connection) -> None:
    perfil_id = _perfil(conn)
    _fato(conn, perfil_id, "rede_social:linkedin", "Post de campanha de 2022", "2022-10-02")

    (linha,) = _linhas(conn, perfil_id)

    assert "[antigo]" in linha and "[de imagem]" not in linha


def test_lembranca_do_facebook_vai_marcada_mesmo_sem_data(conn: sqlite3.Connection) -> None:
    perfil_id = _perfil(conn)
    texto = "E seguimos! #BoraLula13\nHá 4 anos\nVeja suas lembranças"
    _fato(conn, perfil_id, "rede_social:facebook", texto, None)

    (linha,) = _linhas(conn, perfil_id)

    assert "[antigo]" in linha


def test_fato_de_imagem_vai_marcado(conn: sqlite3.Connection) -> None:
    perfil_id = _perfil(conn)
    _fato(conn, perfil_id, "imagem:linkedin", "Imagem publicada: grupo diante de uma bandeira", "2026-10-10")

    (linha,) = _linhas(conn, perfil_id)

    assert "[de imagem]" in linha and "[antigo]" not in linha


def test_post_recente_vai_sem_marca(conn: sqlite3.Connection) -> None:
    perfil_id = _perfil(conn)
    _fato(conn, perfil_id, "rede_social:linkedin", "Atuação da CDH-OABSP na Paulista", "2026-10-09")

    (linha,) = _linhas(conn, perfil_id)

    assert "[antigo]" not in linha and "[de imagem]" not in linha
    assert linha.startswith("2026-10-09 (rede_social:linkedin):")


def test_regra_do_prompt_manda_ressalvar_fato_marcado() -> None:
    regras = redigir_ganchos._regras()

    assert "[antigo] ou [de imagem]" in regras
    assert "Nunca infira opinião, posição ou adesão" in regras
