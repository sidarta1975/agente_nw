from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from flask import Flask
from flask.testing import FlaskClient

import agente_nw.console.app as console_app
from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import perfil_tema, perfis, temas
from agente_nw.nucleo.modelos.configuracao import (
    AgrupamentoLimiares,
    CartaoLimiares,
    ColetaLimiares,
    ConectorLimiares,
    Limiares,
    QualificacaoLimiares,
)
from agente_nw.nucleo.modelos.extracao import RespostaExtracaoTexto

AGORA = "2026-09-19T00:00:00+00:00"


def _limiares() -> Limiares:
    return Limiares(
        agrupamento=AgrupamentoLimiares(
            cosseno_mesmo_assunto=0.82,
            cosseno_republicacao=0.94,
            divergencia_minima_fonte_independente=0.08,
            janela_dias=7,
            itens_para_dividir=12,
        ),
        qualificacao=QualificacaoLimiares(substancial_minimo=0.6, conversavel_minimo=0.6, teto_por_dia=40),
        conector=ConectorLimiares(
            adjacencia_minima=0.55,
            conversavel_viavel=0.8,
            peso_aderencia_contato=50,
            peso_aderencia_usuario=30,
            peso_conversavel=20,
            peso_nivel={"dominio": 1.0, "interesse": 0.7, "curiosidade": 0.4},
            candidatos_por_contato=10,
            itens_no_menu=5,
        ),
        coleta=ColetaLimiares(
            teaser_minimo_caracteres=400,
            dias_max_primeira_aparicao=7,
            retencao_texto_dias=90,
            intervalo_google_news_segundos=0,
            dias_alerta_feed_vazio=2,
        ),
        cartao=CartaoLimiares(teto_por_dia=40),
    )


class _ClienteLLMFake:
    def __init__(self, *args: object, **kwargs: object) -> None:
        pass

    def gerar_json(self, tarefa_nome: str, prompt: str, esquema: type[RespostaExtracaoTexto]) -> object:
        return esquema()


@pytest.fixture
def caminho_banco(tmp_path: Path) -> Path:
    return tmp_path / "teste.db"


@pytest.fixture
def conn(caminho_banco: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(caminho_banco)
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


@pytest.fixture
def app(
    caminho_banco: Path, tmp_path: Path, conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> Flask:
    monkeypatch.setattr(console_app, "ClienteOllama", _ClienteLLMFake)
    return console_app.criar_app(
        caminho_banco, tmp_path / "log.jsonl", object(), _limiares(), "http://unused"
    )


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    return app.test_client()


def test_contatos_lista_todos_com_lacunas_e_status(conn: sqlite3.Connection, client: FlaskClient) -> None:
    ativo = perfis.inserir_ou_atualizar_contato(conn, "Ana", None, "ana@x.com", None, None, None, AGORA)
    assert ativo.id is not None
    perfis.ativar(conn, ativo.id)
    perfis.inserir_ou_atualizar_contato(conn, "Beto", None, "beto@x.com", None, None, None, AGORA)
    conn.commit()

    resposta = client.get("/contatos")

    assert resposta.status_code == 200
    texto = resposta.get_data(as_text=True)
    assert "Ana" in texto
    assert "Beto" in texto
    assert "campo(s) faltando" in texto


def test_ficha_mostra_lacunas_e_tags_confirmadas_e_pendentes(
    conn: sqlite3.Connection, client: FlaskClient
) -> None:
    contato = perfis.inserir_ou_atualizar_contato(conn, "Carla", None, "carla@x.com", None, None, None, AGORA)
    assert contato.id is not None
    tema = temas.obter_ou_criar(conn, "vela", "descrição do tema de vela para embedding", [], AGORA)
    assert tema.id is not None
    perfil_tema.vincular(conn, contato.id, tema.id, 3, "sugerida", None, False, AGORA)
    conn.commit()

    resposta = client.get(f"/contatos/{contato.id}")

    assert resposta.status_code == 200
    texto = resposta.get_data(as_text=True)
    assert "(vazio)" in texto
    assert "vela" in texto


def test_ativar_marca_perfil_como_ativo(conn: sqlite3.Connection, client: FlaskClient) -> None:
    contato = perfis.inserir_ou_atualizar_contato(conn, "Dora", None, "dora@x.com", None, None, None, AGORA)
    assert contato.id is not None
    conn.commit()

    resposta = client.post(f"/contatos/{contato.id}/ativar", follow_redirects=True)

    assert resposta.status_code == 200
    (ativo,) = conn.execute("SELECT ativo FROM perfil WHERE id = ?", (contato.id,)).fetchone()
    assert ativo == 1


def test_confirmar_tags_em_lote_confirma_so_as_marcadas(
    conn: sqlite3.Connection, client: FlaskClient
) -> None:
    contato = perfis.inserir_ou_atualizar_contato(conn, "Elza", None, "elza@x.com", None, None, None, AGORA)
    assert contato.id is not None
    tema_a = temas.obter_ou_criar(conn, "tema-a", "descrição completa do tema a para embedding", [], AGORA)
    tema_b = temas.obter_ou_criar(conn, "tema-b", "descrição completa do tema b para embedding", [], AGORA)
    assert tema_a.id is not None and tema_b.id is not None
    perfil_tema.vincular(conn, contato.id, tema_a.id, 3, "sugerida", None, False, AGORA)
    perfil_tema.vincular(conn, contato.id, tema_b.id, 3, "sugerida", None, False, AGORA)
    conn.commit()

    resposta = client.post(
        f"/contatos/{contato.id}/confirmar-tags", data={"tema_id": str(tema_a.id)}, follow_redirects=True
    )

    assert resposta.status_code == 200
    vinculos = {v.tema_id: v.confirmado for v in perfil_tema.listar_por_perfil(conn, contato.id)}
    assert vinculos[tema_a.id] is True
    assert vinculos[tema_b.id] is False


def test_adicionar_texto_enfileira_e_processa_via_llm_fake(
    conn: sqlite3.Connection, client: FlaskClient
) -> None:
    contato = perfis.inserir_ou_atualizar_contato(conn, "Fabio", None, "fabio@x.com", None, None, None, AGORA)
    assert contato.id is not None
    conn.commit()

    resposta = client.post(
        f"/contatos/{contato.id}/adicionar-texto",
        data={"texto": "Fabio joga vôlei nos fins de semana."},
        follow_redirects=True,
    )

    assert resposta.status_code == 200
    (n_pendentes,) = conn.execute(
        "SELECT COUNT(*) FROM fila_extracao WHERE perfil_id = ? AND processado = 0", (contato.id,)
    ).fetchone()
    assert n_pendentes == 0
    (n_total,) = conn.execute(
        "SELECT COUNT(*) FROM fila_extracao WHERE perfil_id = ?", (contato.id,)
    ).fetchone()
    assert n_total == 1


def test_gerar_menu_sem_tema_confirmado_nao_quebra_e_mostra_menu_vazio(
    conn: sqlite3.Connection, client: FlaskClient
) -> None:
    contato = perfis.inserir_ou_atualizar_contato(conn, "Gil", None, "gil@x.com", None, None, None, AGORA)
    assert contato.id is not None
    conn.commit()

    resposta = client.post(f"/contatos/{contato.id}/gerar-menu", follow_redirects=True)

    assert resposta.status_code == 200
    texto = resposta.get_data(as_text=True)
    assert "Nenhum conector hoje" in texto
