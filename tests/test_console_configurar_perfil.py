from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from flask import Flask
from flask.testing import FlaskClient

import agente_nw.console.app as console_app
from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import perfil_tema, perfis
from agente_nw.nucleo.database.queries import temas as queries_temas
from agente_nw.nucleo.modelos.configuracao import (
    AgrupamentoLimiares,
    CartaoLimiares,
    ColetaLimiares,
    ConectorLimiares,
    Limiares,
    QualificacaoLimiares,
)

AGORA = "2026-09-21T10:00:00+00:00"

DESCRICAO_VALIDA = "descrição bem completa com mais de oito palavras para embedding"


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
        return [[0.1] * 1024 for _ in textos]


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


def test_get_eu_sem_usuario_apresenta_formulario_de_configuracao(client: FlaskClient) -> None:
    resposta = client.get("/eu")

    assert resposta.status_code == 200
    texto = resposta.get_data(as_text=True)
    assert "Configurar perfil do usuário" in texto
    assert 'name="nome"' in texto
    assert 'name="tema_0_nome"' in texto
    assert "dominio" in texto and "interesse" in texto and "curiosidade" in texto


def test_configurar_cria_usuario_e_temas_confirmados(client: FlaskClient, conn: sqlite3.Connection) -> None:
    resposta = client.post(
        "/eu/configurar",
        data={
            "nome": "Sidarta",
            "tema_0_nome": "vela",
            "tema_0_descricao": DESCRICAO_VALIDA,
            "tema_0_nivel": "dominio",
            "tema_0_peso": "5",
            "tema_1_nome": "leitura",
            "tema_1_descricao": DESCRICAO_VALIDA,
            "tema_1_nivel": "interesse",
            "tema_1_peso": "3",
            "tema_2_nome": "vinho",
            "tema_2_descricao": DESCRICAO_VALIDA,
            "tema_2_nivel": "curiosidade",
            "tema_2_peso": "2",
        },
        follow_redirects=False,
    )

    assert resposta.status_code == 302
    assert resposta.location.endswith("/eu")

    usuario = perfis.obter_usuario(conn)
    assert usuario is not None and usuario.nome == "Sidarta"
    tags = perfil_tema.listar_por_perfil(conn, usuario.id or -1)
    assert len(tags) == 3
    assert all(t.confirmado for t in tags)
    assert {t.nivel for t in tags} == {"dominio", "interesse", "curiosidade"}


def test_configurar_sem_nome_devolve_formulario_com_erro(client: FlaskClient) -> None:
    resposta = client.post(
        "/eu/configurar",
        data={"tema_0_nome": "vela", "tema_0_descricao": DESCRICAO_VALIDA, "tema_0_nivel": "dominio"},
    )

    assert resposta.status_code == 200
    texto = resposta.get_data(as_text=True)
    assert "obrigatório" in texto or "obrigatorio" in texto.lower()


def test_configurar_sem_tema_devolve_formulario_com_erro(client: FlaskClient) -> None:
    resposta = client.post("/eu/configurar", data={"nome": "Sidarta"})

    assert resposta.status_code == 200
    texto = resposta.get_data(as_text=True)
    assert "tema" in texto.lower()


def test_configurar_com_descricao_curta_devolve_formulario_com_erro(client: FlaskClient) -> None:
    resposta = client.post(
        "/eu/configurar",
        data={
            "nome": "Sidarta",
            "tema_0_nome": "vela",
            "tema_0_descricao": "curta demais",
            "tema_0_nivel": "dominio",
            "tema_0_peso": "3",
        },
    )

    assert resposta.status_code == 200
    texto = resposta.get_data(as_text=True)
    assert "descricao" in texto.lower() or "descrição" in texto.lower() or "8 palavras" in texto


def test_adicionar_tema_pelo_console_persiste_para_o_usuario(
    client: FlaskClient, conn: sqlite3.Connection
) -> None:
    usuario = perfis.upsert_usuario(conn, "Sidarta", AGORA)
    conn.commit()
    assert usuario.id is not None

    resposta = client.post(
        "/temas/novo",
        data={
            "tema_nome": "gastronomia",
            "tema_descricao": DESCRICAO_VALIDA,
            "tema_nivel": "interesse",
            "tema_peso": "4",
        },
        follow_redirects=False,
    )

    assert resposta.status_code == 302
    tags = perfil_tema.listar_por_perfil(conn, usuario.id)
    nomes = {queries_temas.obter_por_id(conn, t.tema_id).nome for t in tags if t.tema_id}  # type: ignore[union-attr]
    assert "gastronomia" in nomes


def test_adicionar_tema_sem_usuario_devolve_400(client: FlaskClient) -> None:
    resposta = client.post(
        "/temas/novo",
        data={
            "tema_nome": "x",
            "tema_descricao": DESCRICAO_VALIDA,
            "tema_nivel": "interesse",
            "tema_peso": "3",
        },
    )

    assert resposta.status_code == 400


def test_remover_tema_do_usuario_apaga_o_vinculo(client: FlaskClient, conn: sqlite3.Connection) -> None:
    usuario = perfis.upsert_usuario(conn, "Sidarta", AGORA)
    tema = queries_temas.obter_ou_criar(conn, "vela", DESCRICAO_VALIDA, [], AGORA)
    assert usuario.id is not None and tema.id is not None
    perfil_tema.vincular(conn, usuario.id, tema.id, 3, "declarada", "dominio", True, AGORA)
    conn.commit()

    resposta = client.post(f"/temas/{tema.id}/remover-do-usuario", follow_redirects=False)

    assert resposta.status_code == 302
    assert perfil_tema.listar_por_perfil(conn, usuario.id) == []
    assert queries_temas.obter_por_id(conn, tema.id) is not None
