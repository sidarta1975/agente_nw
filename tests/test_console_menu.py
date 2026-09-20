from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest
from flask import Flask
from flask.testing import FlaskClient

import agente_nw.console.app as console_app
from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import assunto_contato, assuntos, perfis
from agente_nw.nucleo.modelos.assunto import Assunto
from agente_nw.nucleo.modelos.assunto_contato import AssuntoContato
from agente_nw.nucleo.modelos.configuracao import (
    AgrupamentoLimiares,
    CartaoLimiares,
    ColetaLimiares,
    ConectorLimiares,
    Limiares,
    QualificacaoLimiares,
)

AGORA = "2026-09-19T00:00:00+00:00"
# gerado_em precisa ser a data real de "hoje": as rotas do console filtram
# assunto_contato por datetime.now(UTC).date(), não por AGORA.
HOJE = datetime.now(UTC).date().isoformat()


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


def _criar_contato_ativo(conn: sqlite3.Connection, nome: str) -> int:
    contato = perfis.inserir_ou_atualizar_contato(conn, nome, None, f"{nome}@x.com", None, None, None, AGORA)
    assert contato.id is not None
    perfis.ativar(conn, contato.id)
    conn.commit()
    return contato.id


def _criar_assunto_contato(
    conn: sqlite3.Connection, perfil_id: int, tipo: str, status: str, titulo: str
) -> int:
    assunto = Assunto(
        titulo_gerado=titulo,
        primeiro_visto=AGORA,
        ultimo_visto=AGORA,
        n_itens=1,
        status="novo",
        substancial=0.8,
        conversavel=0.8,
        resumo_cartao="Resumo do cartão em uma linha (fonte).",
    )
    assunto_id = assuntos.inserir(conn, assunto)
    registro = AssuntoContato(
        assunto_id=assunto_id,
        perfil_id=perfil_id,
        gerado_em=HOJE,
        tipo=tipo,  # type: ignore[arg-type]
        aderencia_contato=0.7,
        aderencia_usuario=0.7,
        conversavel=0.8,
        score=0.7,
        por_que="por causa do assunto X",
        status=status,  # type: ignore[arg-type]
    )
    assunto_contato.inserir(conn, registro)
    conn.commit()
    return assunto_id


def test_menu_lista_mostra_so_contatos_com_menu_hoje(conn: sqlite3.Connection, client: FlaskClient) -> None:
    com_menu = _criar_contato_ativo(conn, "Ana")
    _criar_contato_ativo(conn, "Beto")
    _criar_assunto_contato(conn, com_menu, "conector", "novo", "Assunto da Ana")

    resposta = client.get("/menu")

    assert resposta.status_code == 200
    texto = resposta.get_data(as_text=True)
    assert "Ana" in texto
    assert "Beto" not in texto


def test_menu_contato_separa_conectores_e_viaveis_e_mostra_cartao(
    conn: sqlite3.Connection, client: FlaskClient
) -> None:
    perfil_id = _criar_contato_ativo(conn, "Carla")
    _criar_assunto_contato(conn, perfil_id, "conector", "novo", "Assunto conector")
    _criar_assunto_contato(conn, perfil_id, "viavel_com_esforco", "novo", "Assunto viável")

    resposta = client.get(f"/menu/{perfil_id}")

    assert resposta.status_code == 200
    texto = resposta.get_data(as_text=True)
    assert "Assunto conector" in texto
    assert "Assunto viável" in texto
    assert "Resumo do cartão em uma linha" in texto


def test_marcar_usado_muda_status(conn: sqlite3.Connection, client: FlaskClient) -> None:
    perfil_id = _criar_contato_ativo(conn, "Dora")
    assunto_id = _criar_assunto_contato(conn, perfil_id, "conector", "novo", "Assunto")
    (ac_id,) = conn.execute("SELECT id FROM assunto_contato WHERE assunto_id = ?", (assunto_id,)).fetchone()

    resposta = client.post(f"/menu/{perfil_id}/usei/{ac_id}", follow_redirects=True)

    assert resposta.status_code == 200
    (status,) = conn.execute("SELECT status FROM assunto_contato WHERE id = ?", (ac_id,)).fetchone()
    assert status == "usado"


def test_marcar_nao_serve_grava_motivo(conn: sqlite3.Connection, client: FlaskClient) -> None:
    perfil_id = _criar_contato_ativo(conn, "Elza")
    assunto_id = _criar_assunto_contato(conn, perfil_id, "viavel_com_esforco", "novo", "Assunto")
    (ac_id,) = conn.execute("SELECT id FROM assunto_contato WHERE assunto_id = ?", (assunto_id,)).fetchone()

    resposta = client.post(
        f"/menu/{perfil_id}/nao-serve/{ac_id}", data={"motivo": "velho"}, follow_redirects=True
    )

    assert resposta.status_code == 200
    status, motivo = conn.execute(
        "SELECT status, motivo FROM assunto_contato WHERE id = ?", (ac_id,)
    ).fetchone()
    assert status == "nao_serve"
    assert motivo == "velho"


def test_fora_do_dominio_aparece_no_contador(conn: sqlite3.Connection, client: FlaskClient) -> None:
    perfil_id = _criar_contato_ativo(conn, "Fabio")
    _criar_assunto_contato(conn, perfil_id, "fora_do_dominio", "descartado", "Assunto irrelevante")

    resposta = client.get(f"/menu/{perfil_id}")

    assert resposta.status_code == 200
    texto = resposta.get_data(as_text=True)
    assert "Fora do domínio (1)" in texto
    assert "Assunto irrelevante" in texto
