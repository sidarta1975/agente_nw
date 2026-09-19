from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import assunto_contato, assuntos, perfis
from agente_nw.nucleo.modelos.assunto import Assunto
from agente_nw.nucleo.modelos.assunto_contato import AssuntoContato
from agente_nw.nucleo.saidas import markdown

AGORA = "2026-09-19T00:00:00+00:00"
DATA = "2026-09-19"


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


def _criar_contato(conn: sqlite3.Connection, telefone: str):
    contato = perfis.inserir_ou_atualizar_contato(conn, "Fulano", telefone, None, None, None, None, AGORA)
    assert contato.id is not None
    perfis.ativar(conn, contato.id)
    conn.commit()
    return contato


def _criar_assunto(conn: sqlite3.Connection, titulo: str, resumo_cartao: str | None = None) -> int:
    assunto = Assunto(
        titulo_gerado=titulo,
        resumo_cartao=resumo_cartao,
        primeiro_visto=AGORA,
        ultimo_visto=AGORA,
        status="novo",
    )
    return assuntos.inserir(conn, assunto)


def _gravar_assunto_contato(
    conn: sqlite3.Connection,
    assunto_id: int,
    perfil_id: int,
    tipo: str,
    por_que: str | None,
    status: str = "novo",
) -> None:
    registro = AssuntoContato(
        assunto_id=assunto_id,
        perfil_id=perfil_id,
        gerado_em=DATA,
        tipo=tipo,  # type: ignore[arg-type]
        aderencia_contato=0.7,
        aderencia_usuario=0.6,
        conversavel=0.5,
        score=70.0,
        por_que=por_que,
        status=status,  # type: ignore[arg-type]
    )
    assunto_contato.inserir(conn, registro)
    conn.commit()


def test_contato_sem_sugestao_nao_gera_bloco(conn: sqlite3.Connection) -> None:
    contato = _criar_contato(conn, "+5511900000000")

    texto = markdown.gerar(conn, [contato], DATA)

    assert contato.nome not in texto
    assert texto == "<!-- nenhuma sugestão hoje -->\n"


def test_conector_nao_leva_cartao(conn: sqlite3.Connection) -> None:
    contato = _criar_contato(conn, "+5511900000000")
    assunto_id = _criar_assunto(conn, "Título do conector", resumo_cartao="não deveria aparecer")
    _gravar_assunto_contato(conn, assunto_id, contato.id, "conector", "justificativa")

    texto = markdown.gerar(conn, [contato], DATA)

    assert "### Conectores" in texto
    assert "Cartão:" not in texto
    assert "### Viáveis com esforço" not in texto


def test_viavel_leva_cartao(conn: sqlite3.Connection) -> None:
    contato = _criar_contato(conn, "+5511900000000")
    assunto_id = _criar_assunto(conn, "Título do viável", resumo_cartao="linha 1\nlinha 2\nlinha 3")
    _gravar_assunto_contato(conn, assunto_id, contato.id, "viavel_com_esforco", "justificativa")

    texto = markdown.gerar(conn, [contato], DATA)

    assert "### Viáveis com esforço" in texto
    assert "Cartão: linha 1" in texto
    assert "### Conectores" not in texto


def test_por_que_none_nao_quebra_vira_nao_gerado(conn: sqlite3.Connection) -> None:
    contato = _criar_contato(conn, "+5511900000000")
    assunto_id = _criar_assunto(conn, "Título sem por quê")
    _gravar_assunto_contato(conn, assunto_id, contato.id, "conector", None)

    texto = markdown.gerar(conn, [contato], DATA)

    assert "Por quê: (não gerado)" in texto


def test_nenhum_perfil_com_sugestao_ainda_assim_produz_arquivo_com_comentario(
    conn: sqlite3.Connection,
) -> None:
    contato1 = _criar_contato(conn, "+5511900000000")
    contato2 = _criar_contato(conn, "+5511911111111")

    texto = markdown.gerar(conn, [contato1, contato2], DATA)

    assert texto == "<!-- nenhuma sugestão hoje -->\n"


def test_status_diferente_de_novo_nao_aparece(conn: sqlite3.Connection) -> None:
    contato = _criar_contato(conn, "+5511900000000")
    assunto_id = _criar_assunto(conn, "Já usado")
    _gravar_assunto_contato(conn, assunto_id, contato.id, "conector", "justificativa", status="usado")

    texto = markdown.gerar(conn, [contato], DATA)

    assert texto == "<!-- nenhuma sugestão hoje -->\n"
