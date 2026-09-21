from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from flask import Flask
from flask.testing import FlaskClient

import agente_nw.console.app as console_app
from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import fatos as fatos_q
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
from agente_nw.nucleo.modelos.fato import Fato

AGORA = "2026-09-21T10:00:00+00:00"


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
    perfil = perfis.inserir_novo_contato(conn, nome, None, None, AGORA)
    conn.commit()
    assert perfil.id is not None
    return perfil.id


def test_post_apagar_sem_historico_e_sem_confirmar_mostra_tela_de_confirmacao(
    client: FlaskClient, conn: sqlite3.Connection
) -> None:
    perfil_id = _criar_contato(conn, "Ana")

    resposta = client.post(f"/contatos/{perfil_id}/apagar")

    assert resposta.status_code == 200
    texto = resposta.get_data(as_text=True)
    assert "Confirmar apagar" in texto
    assert perfis.obter_por_id(conn, perfil_id) is not None  # ainda não apagou


def test_post_apagar_com_confirmar_apaga_e_redireciona_para_listagem(
    client: FlaskClient, conn: sqlite3.Connection
) -> None:
    perfil_id = _criar_contato(conn, "Beto")
    redes_sociais.inserir(conn, perfil_id, "linkedin", "https://linkedin.com/in/beto", AGORA)
    conn.commit()

    resposta = client.post(f"/contatos/{perfil_id}/apagar", data={"confirmar": "sim"}, follow_redirects=False)

    assert resposta.status_code == 302
    assert resposta.location.endswith("/contatos")
    assert perfis.obter_por_id(conn, perfil_id) is None


def test_post_apagar_com_historico_sempre_mostra_bloqueio(
    client: FlaskClient, conn: sqlite3.Connection
) -> None:
    perfil_id = _criar_contato(conn, "Carla")
    fatos_q.inserir(conn, Fato(perfil_id=perfil_id, tipo="teste", conteudo="algo", registrado_em=AGORA))
    conn.commit()

    resposta = client.post(f"/contatos/{perfil_id}/apagar", data={"confirmar": "sim"}, follow_redirects=False)

    assert resposta.status_code == 200
    texto = resposta.get_data(as_text=True)
    assert "não pode ser apagado" in texto
    assert perfis.obter_por_id(conn, perfil_id) is not None


def test_post_unir_sem_confirmar_mostra_tela_de_confirmacao(
    client: FlaskClient, conn: sqlite3.Connection
) -> None:
    canonico_id = _criar_contato(conn, "Ana Canônica")
    duplicado_id = _criar_contato(conn, "Ana Duplicada")

    resposta = client.post(f"/contatos/{canonico_id}/unir", data={"outro_id": str(duplicado_id)})

    assert resposta.status_code == 200
    texto = resposta.get_data(as_text=True)
    assert "Confirmar união" in texto
    assert perfis.obter_por_id(conn, duplicado_id) is not None


def test_post_unir_com_confirmar_reatribui_e_apaga_duplicado(
    client: FlaskClient, conn: sqlite3.Connection
) -> None:
    canonico_id = _criar_contato(conn, "Ana Canônica")
    duplicado_id = _criar_contato(conn, "Ana Duplicada")
    redes_sociais.inserir(conn, duplicado_id, "linkedin", "https://linkedin.com/in/dup", AGORA)
    conn.commit()

    resposta = client.post(
        f"/contatos/{canonico_id}/unir",
        data={"outro_id": str(duplicado_id), "confirmar": "sim"},
        follow_redirects=False,
    )

    assert resposta.status_code == 302
    assert resposta.location.endswith(f"/contatos/{canonico_id}")
    assert perfis.obter_por_id(conn, duplicado_id) is None
    redes = redes_sociais.listar_por_perfil(conn, canonico_id)
    assert len(redes) == 1


def test_post_unir_mesmo_perfil_devolve_400(client: FlaskClient, conn: sqlite3.Connection) -> None:
    perfil_id = _criar_contato(conn, "Ana")

    resposta = client.post(
        f"/contatos/{perfil_id}/unir", data={"outro_id": str(perfil_id), "confirmar": "sim"}
    )

    assert resposta.status_code == 400


def test_ficha_mostra_botoes_de_apagar_e_unir(client: FlaskClient, conn: sqlite3.Connection) -> None:
    perfil_id = _criar_contato(conn, "Ana")
    _criar_contato(conn, "Outro")

    resposta = client.get(f"/contatos/{perfil_id}")

    assert resposta.status_code == 200
    texto = resposta.get_data(as_text=True)
    assert "Apagar contato" in texto
    assert "Unir outro contato" in texto
    assert 'name="outro_id"' in texto
