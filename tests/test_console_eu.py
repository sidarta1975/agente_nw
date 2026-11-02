"""Tela Eu sem formulário de temas (brief 040): mostra os temas inferidos por nível; "contar" aplica
uma declaração do usuário; "esquecer" zera só os temas `origem='conversa'`."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

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
    ConsultaLimiares,
    Limiares,
    ListasLimiares,
    QualificacaoLimiares,
)
from agente_nw.nucleo.modelos.pedido import PedidoExtraido
from agente_nw.nucleo.modelos.tema import RespostaDescreverTema
from tests.llm_falso import ProvenienciaFalsa

AGORA = "2026-10-31T00:00:00+00:00"


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
            consulta=ConsultaLimiares(
                minima=0.45,
                peso_consulta=50,
                peso_contato=25,
                peso_usuario=10,
                peso_conversavel=15,
                selecao_peso_consulta=0.7,
                selecao_peso_contato=0.3,
            ),
        ),
        coleta=ColetaLimiares(
            teaser_minimo_caracteres=400,
            dias_max_primeira_aparicao=7,
            retencao_texto_dias=90,
            intervalo_google_news_segundos=0,
            dias_alerta_feed_vazio=2,
        ),
        cartao=CartaoLimiares(teto_por_dia=40),
        listas=ListasLimiares(maximo_entradas=2000, pausa_rolagem_s=0, validade_dias=30),
    )


class _ClienteLLMFake(ProvenienciaFalsa):
    def __init__(self, *args: object, **kwargs: object) -> None:
        pass

    def gerar_json(
        self, tarefa_nome: str, prompt: str, esquema: type[Any], versao_prompt: str | None = None
    ) -> Any:
        if tarefa_nome == "extrair_pedido":
            return PedidoExtraido.model_validate(
                {
                    "objetivo": "outro",
                    "objetivo_texto": "",
                    "assunto_principal": "sobre o usuário",
                    "termos_busca": ["x"],
                    "confianca": 0.9,
                    "sobre_o_usuario": ["sou advogado tributarista"],
                }
            )
        if tarefa_nome == "descrever_tema":
            return RespostaDescreverTema(descricao="descrição qualquer de teste", sinonimos=[])
        return esquema()

    def embeddar(self, textos: list[str]) -> list[list[float]]:
        return [[1.0, 0.0] + [0.0] * 1022 for _ in textos]


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


def test_tela_mostra_os_temas_agrupados_por_nivel(conn: sqlite3.Connection, client: FlaskClient) -> None:
    usuario = perfis.upsert_usuario(conn, "Rafael", AGORA)
    assert usuario.id is not None
    dominante = temas.obter_ou_criar(conn, "direito tributário", "ramo do direito sobre tributos", [], AGORA)
    curioso = temas.obter_ou_criar(conn, "cerâmica", "moldar e queimar argila", [], AGORA)
    assert dominante.id is not None and curioso.id is not None
    perfil_tema.vincular(conn, usuario.id, dominante.id, 5, "declarada", "dominio", True, AGORA)
    perfil_tema.vincular(conn, usuario.id, curioso.id, 1, "conversa", "curiosidade", True, AGORA)
    conn.commit()

    resposta = client.get("/eu")

    assert resposta.status_code == 200
    texto = resposta.get_data(as_text=True)
    assert "direito tributário" in texto
    assert "cerâmica" in texto


def test_contar_aplica_a_declaracao(conn: sqlite3.Connection, client: FlaskClient) -> None:
    usuario = perfis.upsert_usuario(conn, "Rafael", AGORA)
    assert usuario.id is not None
    conn.commit()

    resposta = client.post("/eu/contar", data={"texto": "sou advogado tributarista"}, follow_redirects=False)

    assert resposta.status_code == 302
    tema = temas.obter_por_nome(conn, "advogado tributarista")
    assert tema is not None and tema.id is not None
    (vinculo,) = perfil_tema.listar_por_perfil(conn, usuario.id)
    assert vinculo.tema_id == tema.id
    assert vinculo.origem == "declarada"


def test_esquecer_zera_so_origem_conversa(conn: sqlite3.Connection, client: FlaskClient) -> None:
    usuario = perfis.upsert_usuario(conn, "Rafael", AGORA)
    assert usuario.id is not None
    declarado = temas.obter_ou_criar(conn, "direito tributário", "ramo do direito sobre tributos", [], AGORA)
    inferido = temas.obter_ou_criar(conn, "vela", "esporte de velejar", [], AGORA)
    assert declarado.id is not None and inferido.id is not None
    perfil_tema.vincular(conn, usuario.id, declarado.id, 5, "declarada", "dominio", True, AGORA)
    perfil_tema.vincular(conn, usuario.id, inferido.id, 1, "conversa", "curiosidade", True, AGORA)
    conn.commit()

    resposta = client.post("/eu/esquecer", follow_redirects=False)

    assert resposta.status_code == 302
    (vinculo,) = perfil_tema.listar_por_perfil(conn, usuario.id)
    assert vinculo.tema_id == declarado.id
    assert vinculo.origem == "declarada"
