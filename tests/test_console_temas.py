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

    def embeddar(self, textos: list[str]) -> list[list[float]]:
        return [[0.1] + [0.0] * 1023 for _ in textos]


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


def _usuario_com_tema(conn: sqlite3.Connection, confirmado: bool) -> tuple[int, int]:
    usuario = perfis.upsert_usuario(conn, "Fulano", AGORA)
    tema = temas.obter_ou_criar(conn, "corrida de rua", "provas de rua, maratonas e treinos", [], AGORA)
    assert usuario.id is not None and tema.id is not None
    perfil_tema.vincular(conn, usuario.id, tema.id, 3, "declarada", "interesse", confirmado, AGORA)
    conn.commit()
    return usuario.id, tema.id


def test_temas_lista_separa_confirmados_e_pendentes(conn: sqlite3.Connection, client: FlaskClient) -> None:
    _usuario_com_tema(conn, confirmado=True)

    resposta = client.get("/temas")

    assert resposta.status_code == 200
    texto = resposta.get_data(as_text=True)
    assert "corrida de rua" in texto
    assert "Nenhuma pendente." in texto


def test_temas_lista_mostra_sugestao_pendente(conn: sqlite3.Connection, client: FlaskClient) -> None:
    _usuario_com_tema(conn, confirmado=False)

    resposta = client.get("/temas")

    assert resposta.status_code == 200
    texto = resposta.get_data(as_text=True)
    assert "Nenhum tema confirmado ainda." in texto
    assert "corrida de rua" in texto


def test_atualizar_tema_regrava_descricao_sinonimos_e_embedding(
    conn: sqlite3.Connection, client: FlaskClient
) -> None:
    _usuario_id, tema_id = _usuario_com_tema(conn, confirmado=True)

    resposta = client.post(
        f"/temas/{tema_id}/atualizar",
        data={"descricao": "nova descrição do tema", "sinonimos": "maratona, meia maratona"},
        follow_redirects=True,
    )

    assert resposta.status_code == 200
    tema = temas.obter_por_id(conn, tema_id)
    assert tema is not None
    assert tema.descricao == "nova descrição do tema"
    assert tema.sinonimos == ["maratona", "meia maratona"]
    (n_embeddings,) = conn.execute("SELECT COUNT(*) FROM vetor_tema WHERE tema_id = ?", (tema_id,)).fetchone()
    assert n_embeddings == 1


def test_atualizar_nivel_grava_novo_nivel(conn: sqlite3.Connection, client: FlaskClient) -> None:
    usuario_id, tema_id = _usuario_com_tema(conn, confirmado=True)

    resposta = client.post(f"/temas/{tema_id}/nivel", data={"nivel": "dominio"}, follow_redirects=True)

    assert resposta.status_code == 200
    (vinculo,) = [v for v in perfil_tema.listar_por_perfil(conn, usuario_id) if v.tema_id == tema_id]
    assert vinculo.nivel == "dominio"


def test_confirmar_tema_pendente_confirma_a_sugestao(conn: sqlite3.Connection, client: FlaskClient) -> None:
    usuario_id, tema_id = _usuario_com_tema(conn, confirmado=False)

    resposta = client.post(f"/temas/{tema_id}/confirmar", follow_redirects=True)

    assert resposta.status_code == 200
    (vinculo,) = [v for v in perfil_tema.listar_por_perfil(conn, usuario_id) if v.tema_id == tema_id]
    assert vinculo.confirmado is True
