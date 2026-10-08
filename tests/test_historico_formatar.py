from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from agente_nw.nucleo import historico
from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import consulta_contato as queries
from agente_nw.nucleo.modelos.consulta_contato import ConsultaContato

AGORA = "2026-09-20T10:00:00+00:00"


def test_formatar_lista_vazia_devolve_string_vazia() -> None:
    assert historico.formatar([]) == ""


def test_formatar_uma_consulta_mostra_data_contexto_e_entregues() -> None:
    consulta = ConsultaContato(
        id=1,
        perfil_id=1,
        criado_em="2026-09-20T10:00:00+00:00",
        contexto_json='{"assunto": "reunião", "meio": "café"}',
        resumo_redes_sociais=None,
        assuntos_entregues_json='[{"titulo": "regata oficial"}, {"titulo": "campeonato local"}]',
    )

    texto = historico.formatar([consulta])

    assert "[2026-09-20]" in texto
    assert "assunto: reunião" in texto
    assert "meio: café" in texto
    assert "regata oficial · campeonato local" in texto
    assert "leitura de rede social" not in texto


def test_formatar_varias_consultas_mantem_ordem_recebida_e_inclui_rede_social() -> None:
    a = ConsultaContato(
        id=1,
        perfil_id=1,
        criado_em="2026-09-20T10:00:00+00:00",
        contexto_json='{"assunto": "retomada"}',
        resumo_redes_sociais="postou sobre livro novo",
        assuntos_entregues_json='[{"titulo": "livro X"}]',
    )
    b = ConsultaContato(
        id=2,
        perfil_id=1,
        criado_em="2026-09-15T10:00:00+00:00",
        contexto_json='{"assunto": "primeira conversa"}',
        resumo_redes_sociais=None,
        assuntos_entregues_json="[]",
    )

    texto = historico.formatar([a, b])

    linhas = texto.split("\n")
    assert linhas[0].startswith("[2026-09-20]")
    assert "leitura de rede social: postou sobre livro novo" in texto
    assert "0 assunto(s) entregue(s)" in texto
    posicao_a = texto.index("[2026-09-20]")
    posicao_b = texto.index("[2026-09-15]")
    assert posicao_a < posicao_b


def test_formatar_lida_com_json_ilegivel_sem_estourar() -> None:
    consulta = ConsultaContato(
        id=1,
        perfil_id=1,
        criado_em="2026-09-20T10:00:00+00:00",
        contexto_json="isto não é JSON",
        resumo_redes_sociais=None,
        assuntos_entregues_json="também não",
    )

    texto = historico.formatar([consulta])

    assert "isto não é JSON" in texto
    assert "(menu ilegível)" in texto


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


def _criar_contato(conn: sqlite3.Connection, nome: str) -> int:
    cursor = conn.execute(
        "INSERT INTO perfil (tipo, nome, linguas, ativo, criado_em, atualizado_em) "
        "VALUES ('contato', ?, '[]', 0, ?, ?)",
        (nome, AGORA, AGORA),
    )
    conn.commit()
    assert cursor.lastrowid is not None
    return cursor.lastrowid


def test_historico_recente_para_prompt_sem_registro_devolve_string_vazia(conn: sqlite3.Connection) -> None:
    perfil_id = _criar_contato(conn, "Ana")

    texto = historico.historico_recente_para_prompt(conn, perfil_id)

    assert texto == ""


def test_historico_recente_para_prompt_limita_no_padrao_de_cinco(conn: sqlite3.Connection) -> None:
    perfil_id = _criar_contato(conn, "Beto")
    dias = (
        "2026-09-14",
        "2026-09-15",
        "2026-09-16",
        "2026-09-17",
        "2026-09-18",
        "2026-09-19",
        "2026-09-20",
    )
    for dia in dias:
        queries.inserir(conn, perfil_id, f"{dia}T10:00:00+00:00", "{}", None, "[]")
    conn.commit()

    texto = historico.historico_recente_para_prompt(conn, perfil_id)

    assert "[2026-09-20]" in texto
    assert "[2026-09-16]" in texto
    assert "[2026-09-15]" not in texto
    assert "[2026-09-14]" not in texto
