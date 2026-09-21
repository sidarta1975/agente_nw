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

AGORA = "2026-09-21T00:00:00+00:00"


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


def test_editar_ficha_atualiza_campos_simples_e_persiste(
    conn: sqlite3.Connection, client: FlaskClient
) -> None:
    perfil_id = _criar_contato(conn, "Ana")

    resposta = client.post(
        f"/contatos/{perfil_id}/editar",
        data={
            "nome": "Ana Editada",
            "apelido": "aninha",
            "empresa": "Nova Empresa",
            "cargo": "Diretora",
            "cidade": "São Paulo",
        },
        follow_redirects=False,
    )

    assert resposta.status_code == 302
    assert resposta.location.endswith(f"/contatos/{perfil_id}")

    linha = conn.execute(
        "SELECT nome, apelido, empresa, cargo, cidade FROM perfil WHERE id = ?", (perfil_id,)
    ).fetchone()
    assert linha["nome"] == "Ana Editada"
    assert linha["apelido"] == "aninha"
    assert linha["empresa"] == "Nova Empresa"
    assert linha["cargo"] == "Diretora"
    assert linha["cidade"] == "São Paulo"


def test_editar_ficha_sobrescreve_valor_pre_existente(conn: sqlite3.Connection, client: FlaskClient) -> None:
    perfil_id = _criar_contato(conn, "Beto")
    perfis.atualizar_ficha_manual(
        conn, perfil_id, {"empresa": "Empresa Original", "cargo": "Analista"}, AGORA
    )
    conn.commit()

    client.post(
        f"/contatos/{perfil_id}/editar",
        data={"nome": "Beto", "empresa": "Empresa Nova", "cargo": ""},
        follow_redirects=False,
    )

    linha = conn.execute("SELECT empresa, cargo FROM perfil WHERE id = ?", (perfil_id,)).fetchone()
    assert linha["empresa"] == "Empresa Nova"
    assert linha["cargo"] is None


def test_editar_ficha_normaliza_telefone_para_e164(conn: sqlite3.Connection, client: FlaskClient) -> None:
    perfil_id = _criar_contato(conn, "Carla")

    client.post(
        f"/contatos/{perfil_id}/editar",
        data={"nome": "Carla", "telefone": "(11) 90000-4321"},
        follow_redirects=False,
    )

    (telefone,) = conn.execute("SELECT telefone FROM perfil WHERE id = ?", (perfil_id,)).fetchone()
    assert telefone == "+5511900004321"


def test_editar_ficha_com_nome_vazio_devolve_400(conn: sqlite3.Connection, client: FlaskClient) -> None:
    perfil_id = _criar_contato(conn, "Dora")

    resposta = client.post(
        f"/contatos/{perfil_id}/editar",
        data={"nome": "", "empresa": "X"},
        follow_redirects=False,
    )

    assert resposta.status_code == 400


def test_editar_ficha_persiste_linguas_como_lista(conn: sqlite3.Connection, client: FlaskClient) -> None:
    perfil_id = _criar_contato(conn, "Elza")

    client.post(
        f"/contatos/{perfil_id}/editar",
        data={"nome": "Elza", "linguas": "português, inglês, francês"},
        follow_redirects=False,
    )

    (linguas,) = conn.execute("SELECT linguas FROM perfil WHERE id = ?", (perfil_id,)).fetchone()
    assert linguas == '["português", "inglês", "francês"]'


def test_editar_ficha_persiste_tem_filhos_sim_nao_e_desconhecido(
    conn: sqlite3.Connection, client: FlaskClient
) -> None:
    perfil_id = _criar_contato(conn, "Fabio")

    client.post(f"/contatos/{perfil_id}/editar", data={"nome": "Fabio", "tem_filhos": "sim"})
    (tem,) = conn.execute("SELECT tem_filhos FROM perfil WHERE id = ?", (perfil_id,)).fetchone()
    assert tem == 1

    client.post(f"/contatos/{perfil_id}/editar", data={"nome": "Fabio", "tem_filhos": "nao"})
    (tem,) = conn.execute("SELECT tem_filhos FROM perfil WHERE id = ?", (perfil_id,)).fetchone()
    assert tem == 0

    client.post(f"/contatos/{perfil_id}/editar", data={"nome": "Fabio", "tem_filhos": ""})
    (tem,) = conn.execute("SELECT tem_filhos FROM perfil WHERE id = ?", (perfil_id,)).fetchone()
    assert tem is None


def test_get_ficha_apresenta_valores_atuais_no_formulario(
    conn: sqlite3.Connection, client: FlaskClient
) -> None:
    perfil_id = _criar_contato(conn, "Gil")
    perfis.atualizar_ficha_manual(conn, perfil_id, {"empresa": "Acme", "cidade": "Curitiba"}, AGORA)
    conn.commit()

    resposta = client.get(f"/contatos/{perfil_id}")

    assert resposta.status_code == 200
    texto = resposta.get_data(as_text=True)
    assert 'value="Acme"' in texto
    assert 'value="Curitiba"' in texto
