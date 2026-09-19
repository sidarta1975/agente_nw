from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import assuntos, perfil_tema, perfis, temas
from agente_nw.nucleo.modelos.assunto import Assunto

AGORA = "2026-01-01T00:00:00+00:00"


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


def _vetor(*valores: float) -> list[float]:
    return list(valores) + [0.0] * (1024 - len(valores))


def _criar_assunto(conn: sqlite3.Connection, centroide: list[float]) -> int:
    assunto = Assunto(primeiro_visto=AGORA, ultimo_visto=AGORA, n_itens=1, status="novo")
    assunto_id = assuntos.inserir(conn, assunto)
    assuntos.gravar_centroide(conn, assunto_id, centroide)
    return assunto_id


def test_listar_candidatos_qualificacao_ordena_por_proximidade(conn: sqlite3.Connection) -> None:
    usuario = perfis.upsert_usuario(conn, "Usuário Teste", AGORA)
    assert usuario.id is not None
    tema_usuario = temas.obter_ou_criar(conn, "tema-usuario", "descrição", [], AGORA)
    assert tema_usuario.id is not None
    temas.gravar_embedding(conn, tema_usuario.id, _vetor(1.0, 0.0))
    perfil_tema.vincular(conn, usuario.id, tema_usuario.id, 3, "declarada", "dominio", True, AGORA)
    conn.commit()

    perto = _criar_assunto(conn, _vetor(0.99, 0.14))
    longe = _criar_assunto(conn, _vetor(0.0, 1.0))
    conn.commit()

    resultado = assuntos.listar_candidatos_qualificacao(conn, 10)

    assert [a.id for a in resultado] == [perto, longe]


def test_listar_candidatos_qualificacao_inclui_assunto_proximo_so_de_tema_de_contato(
    conn: sqlite3.Connection,
) -> None:
    usuario = perfis.upsert_usuario(conn, "Usuário Teste", AGORA)
    assert usuario.id is not None
    tema_usuario = temas.obter_ou_criar(conn, "tema-usuario", "descrição", [], AGORA)
    assert tema_usuario.id is not None
    temas.gravar_embedding(conn, tema_usuario.id, _vetor(1.0, 0.0))
    perfil_tema.vincular(conn, usuario.id, tema_usuario.id, 3, "declarada", "dominio", True, AGORA)

    contato = perfis.inserir_ou_atualizar_contato(
        conn, "Contato Ativo", "+5511900000000", None, None, None, None, AGORA
    )
    assert contato.id is not None
    perfis.ativar(conn, contato.id)
    tema_contato = temas.obter_ou_criar(conn, "tema-contato", "descrição", [], AGORA)
    assert tema_contato.id is not None
    temas.gravar_embedding(conn, tema_contato.id, _vetor(0.0, 1.0))
    perfil_tema.vincular(conn, contato.id, tema_contato.id, 3, "declarada", "dominio", True, AGORA)
    conn.commit()

    # este assunto só é próximo do tema do contato, nenhum do usuário — ainda deve aparecer
    so_contato = _criar_assunto(conn, _vetor(0.0, 0.99))
    conn.commit()

    resultado = assuntos.listar_candidatos_qualificacao(conn, 10)

    assert so_contato in [a.id for a in resultado]


def test_listar_candidatos_qualificacao_ignora_perfil_inativo(conn: sqlite3.Connection) -> None:
    contato_inativo = perfis.inserir_ou_atualizar_contato(
        conn, "Contato Inativo", "+5511911111111", None, None, None, None, AGORA
    )
    assert contato_inativo.id is not None
    tema_inativo = temas.obter_ou_criar(conn, "tema-inativo", "descrição", [], AGORA)
    assert tema_inativo.id is not None
    temas.gravar_embedding(conn, tema_inativo.id, _vetor(1.0, 0.0))
    perfil_tema.vincular(conn, contato_inativo.id, tema_inativo.id, 3, "declarada", "dominio", True, AGORA)
    conn.commit()

    assert assuntos.listar_candidatos_qualificacao(conn, 10) == []


def test_listar_candidatos_qualificacao_respeita_limite(conn: sqlite3.Connection) -> None:
    usuario = perfis.upsert_usuario(conn, "Usuário Teste", AGORA)
    assert usuario.id is not None
    tema_usuario = temas.obter_ou_criar(conn, "tema-usuario", "descrição", [], AGORA)
    assert tema_usuario.id is not None
    temas.gravar_embedding(conn, tema_usuario.id, _vetor(1.0, 0.0))
    perfil_tema.vincular(conn, usuario.id, tema_usuario.id, 3, "declarada", "dominio", True, AGORA)
    conn.commit()

    for _ in range(3):
        _criar_assunto(conn, _vetor(1.0, 0.0))
    conn.commit()

    resultado = assuntos.listar_candidatos_qualificacao(conn, 2)
    assert len(resultado) == 2


def test_listar_candidatos_qualificacao_ignora_ja_qualificado(conn: sqlite3.Connection) -> None:
    usuario = perfis.upsert_usuario(conn, "Usuário Teste", AGORA)
    assert usuario.id is not None
    tema_usuario = temas.obter_ou_criar(conn, "tema-usuario", "descrição", [], AGORA)
    assert tema_usuario.id is not None
    temas.gravar_embedding(conn, tema_usuario.id, _vetor(1.0, 0.0))
    perfil_tema.vincular(conn, usuario.id, tema_usuario.id, 3, "declarada", "dominio", True, AGORA)
    conn.commit()

    ja_qualificado = _criar_assunto(conn, _vetor(1.0, 0.0))
    assuntos.gravar_qualificacao(conn, ja_qualificado, 0.8, 0.7, "justificativa", [])
    conn.commit()

    assert assuntos.listar_candidatos_qualificacao(conn, 10) == []


def test_gravar_titulo_faz_ida_e_volta(conn: sqlite3.Connection) -> None:
    assunto_id = _criar_assunto(conn, _vetor(1.0, 0.0))
    conn.commit()

    assuntos.gravar_titulo(conn, assunto_id, "Título gerado")
    conn.commit()

    resultado = assuntos.obter_por_id(conn, assunto_id)
    assert resultado is not None
    assert resultado.titulo_gerado == "Título gerado"


def test_gravar_qualificacao_faz_ida_e_volta(conn: sqlite3.Connection) -> None:
    tema = temas.obter_ou_criar(conn, "tema-x", "descrição", [], AGORA)
    assert tema.id is not None
    assunto_id = _criar_assunto(conn, _vetor(1.0, 0.0))
    conn.commit()

    assuntos.gravar_qualificacao(conn, assunto_id, 0.8, 0.65, "boa justificativa", [tema.id])
    conn.commit()

    resultado = assuntos.obter_por_id(conn, assunto_id)
    assert resultado is not None
    assert resultado.substancial == 0.8
    assert resultado.conversavel == 0.65
    assert resultado.justificativa == "boa justificativa"
    assert resultado.temas == [tema.id]


def test_gravar_cartao_faz_ida_e_volta(conn: sqlite3.Connection) -> None:
    assunto_id = _criar_assunto(conn, _vetor(1.0, 0.0))
    conn.commit()

    assuntos.gravar_cartao(conn, assunto_id, "linha 1\nlinha 2\nlinha 3")
    conn.commit()

    resultado = assuntos.obter_por_id(conn, assunto_id)
    assert resultado is not None
    assert resultado.resumo_cartao == "linha 1\nlinha 2\nlinha 3"
