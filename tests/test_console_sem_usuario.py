from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from flask import Flask
from flask.testing import FlaskClient

import agente_nw.console.app as console_app
from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import perfis
from agente_nw.nucleo.modelos.configuracao import (
    AgrupamentoLimiares,
    CartaoLimiares,
    ColetaLimiares,
    ConectorLimiares,
    Limiares,
    QualificacaoLimiares,
)
from agente_nw.nucleo.modelos.extracao import RespostaExtracaoTexto

AGORA = "2026-09-20T00:00:00+00:00"


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


def test_temas_sem_usuario_devolve_200_com_aviso(conn: sqlite3.Connection, client: FlaskClient) -> None:
    resposta = client.get("/temas")

    assert resposta.status_code == 200
    texto = resposta.get_data(as_text=True)
    assert "usuário" in texto.lower()
    assert "importar-temas" in texto


def test_eu_sem_usuario_devolve_200_com_aviso(conn: sqlite3.Connection, client: FlaskClient) -> None:
    resposta = client.get("/eu")

    assert resposta.status_code == 200
    texto = resposta.get_data(as_text=True)
    assert "usuário" in texto.lower()
    assert "importar-temas" in texto


def test_temas_com_usuario_renderiza_normalmente(conn: sqlite3.Connection, client: FlaskClient) -> None:
    perfis.upsert_usuario(conn, "Sidarta", AGORA)
    conn.commit()

    resposta = client.get("/temas")

    assert resposta.status_code == 200
    texto = resposta.get_data(as_text=True)
    assert "Temas" in texto


def test_eu_com_usuario_renderiza_normalmente(conn: sqlite3.Connection, client: FlaskClient) -> None:
    perfis.upsert_usuario(conn, "Sidarta", AGORA)
    conn.commit()

    resposta = client.get("/eu")

    assert resposta.status_code == 200
    texto = resposta.get_data(as_text=True)
    assert "Sidarta" in texto
