from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from flask import Flask
from flask.testing import FlaskClient

import agente_nw.console.app as console_app
from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import perfis, redes_sociais
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


def _criar_contato(conn: sqlite3.Connection, nome: str) -> int:
    contato = perfis.inserir_ou_atualizar_contato(
        conn, nome, None, f"{nome.lower()}@x.com", None, None, None, AGORA
    )
    conn.commit()
    assert contato.id is not None
    return contato.id


def test_ficha_do_contato_mostra_vazio_quando_nao_ha_redes(
    conn: sqlite3.Connection, client: FlaskClient
) -> None:
    perfil_id = _criar_contato(conn, "Ana")

    resposta = client.get(f"/contatos/{perfil_id}")

    assert resposta.status_code == 200
    texto = resposta.get_data(as_text=True)
    assert "Redes sociais" in texto
    assert "Nenhuma cadastrada." in texto


def test_adicionar_rede_social_do_contato_persiste(conn: sqlite3.Connection, client: FlaskClient) -> None:
    perfil_id = _criar_contato(conn, "Beto")

    resposta = client.post(
        f"/contatos/{perfil_id}/redes-sociais/adicionar",
        data={"rede": "linkedin", "link": "https://linkedin.com/in/beto"},
        follow_redirects=True,
    )

    assert resposta.status_code == 200
    redes = redes_sociais.listar_por_perfil(conn, perfil_id)
    assert [(r.rede, r.link) for r in redes] == [("linkedin", "https://linkedin.com/in/beto")]


def test_adicionar_rede_social_do_contato_rejeita_link_sem_http(
    conn: sqlite3.Connection, client: FlaskClient
) -> None:
    perfil_id = _criar_contato(conn, "Carla")

    resposta = client.post(
        f"/contatos/{perfil_id}/redes-sociais/adicionar",
        data={"rede": "linkedin", "link": "linkedin.com/in/carla"},
        follow_redirects=True,
    )

    assert resposta.status_code == 200
    assert redes_sociais.listar_por_perfil(conn, perfil_id) == []


def test_remover_rede_social_do_contato_apaga_apenas_a_linha(
    conn: sqlite3.Connection, client: FlaskClient
) -> None:
    perfil_id = _criar_contato(conn, "Dora")
    primeira = redes_sociais.inserir(conn, perfil_id, "linkedin", "https://linkedin.com/in/dora", AGORA)
    segunda = redes_sociais.inserir(conn, perfil_id, "instagram", "https://instagram.com/dora", AGORA)
    conn.commit()
    assert primeira.id is not None and segunda.id is not None

    resposta = client.post(
        f"/contatos/{perfil_id}/redes-sociais/{primeira.id}/remover",
        follow_redirects=True,
    )

    assert resposta.status_code == 200
    restantes = redes_sociais.listar_por_perfil(conn, perfil_id)
    assert [r.id for r in restantes] == [segunda.id]


def test_eu_lista_redes_sociais_do_usuario(conn: sqlite3.Connection, client: FlaskClient) -> None:
    usuario = perfis.upsert_usuario(conn, "Sidarta", AGORA)
    assert usuario.id is not None
    redes_sociais.inserir(conn, usuario.id, "linkedin", "https://linkedin.com/in/sidarta", AGORA)
    conn.commit()

    resposta = client.get("/eu")

    assert resposta.status_code == 200
    texto = resposta.get_data(as_text=True)
    assert "Sidarta" in texto
    assert "linkedin" in texto
    assert "https://linkedin.com/in/sidarta" in texto


def test_adicionar_rede_social_do_usuario_persiste(conn: sqlite3.Connection, client: FlaskClient) -> None:
    usuario = perfis.upsert_usuario(conn, "Sidarta", AGORA)
    assert usuario.id is not None
    conn.commit()

    resposta = client.post(
        "/eu/redes-sociais/adicionar",
        data={"rede": "x", "link": "https://x.com/sidarta"},
        follow_redirects=True,
    )

    assert resposta.status_code == 200
    redes = redes_sociais.listar_por_perfil(conn, usuario.id)
    assert [(r.rede, r.link) for r in redes] == [("x", "https://x.com/sidarta")]


def test_remover_rede_social_do_usuario_apaga_apenas_a_linha(
    conn: sqlite3.Connection, client: FlaskClient
) -> None:
    usuario = perfis.upsert_usuario(conn, "Sidarta", AGORA)
    assert usuario.id is not None
    primeira = redes_sociais.inserir(conn, usuario.id, "x", "https://x.com/sidarta", AGORA)
    segunda = redes_sociais.inserir(conn, usuario.id, "linkedin", "https://linkedin.com/in/sidarta", AGORA)
    conn.commit()
    assert primeira.id is not None and segunda.id is not None

    resposta = client.post(
        f"/eu/redes-sociais/{primeira.id}/remover",
        follow_redirects=True,
    )

    assert resposta.status_code == 200
    restantes = redes_sociais.listar_por_perfil(conn, usuario.id)
    assert [r.id for r in restantes] == [segunda.id]
