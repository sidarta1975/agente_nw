from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pytest
from flask import Flask
from flask.testing import FlaskClient

import agente_nw.console.app as console_app
from agente_nw.coleta.capturas.busca import Candidato, ResultadoBusca
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


class _PaginaPlaywrightFake:
    ultima_pasta: Path | None = None
    fechada: bool = False

    def __init__(self, pasta_perfil: Path, headless: bool = False) -> None:
        _PaginaPlaywrightFake.ultima_pasta = pasta_perfil

    def ir_para(self, url: str) -> None:
        pass

    def estado(self) -> tuple[str, str]:
        return ("https://example.com", "x" * 1000)

    def coletar_links(self) -> list[tuple[str, str]]:
        return []

    def fechar(self) -> None:
        _PaginaPlaywrightFake.fechada = True


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


def _criar_contato(conn: sqlite3.Connection, nome: str, empresa: str | None = None) -> int:
    perfil = perfis.inserir_novo_contato(conn, nome, None, None, AGORA)
    conn.commit()
    assert perfil.id is not None
    if empresa is not None:
        perfis.atualizar_ficha_manual(conn, perfil.id, {"empresa": empresa}, AGORA)
        conn.commit()
    return perfil.id


def _monkey_playwright(monkeypatch: pytest.MonkeyPatch) -> None:
    from agente_nw.coleta.capturas import playwright_backend

    monkeypatch.setattr(playwright_backend, "PaginaPlaywright", _PaginaPlaywrightFake)


def _monkey_buscar(monkeypatch: pytest.MonkeyPatch, resultado: ResultadoBusca) -> dict[str, Any]:
    from agente_nw.coleta.capturas import busca as busca_mod

    chamadas: dict[str, Any] = {}

    def _fake(pagina: Any, rede: str, nome: str, empresa: str | None) -> ResultadoBusca:
        chamadas["rede"] = rede
        chamadas["nome"] = nome
        chamadas["empresa"] = empresa
        return resultado

    monkeypatch.setattr(busca_mod, "buscar", _fake)
    return chamadas


def test_busca_rede_desconhecida_devolve_400(client: FlaskClient, conn: sqlite3.Connection) -> None:
    perfil_id = _criar_contato(conn, "Ana")

    resposta = client.post(f"/contatos/{perfil_id}/redes-sociais/buscar", data={"rede": "orkut"})

    assert resposta.status_code == 400


def test_busca_com_sessao_ativa_lista_candidatos_e_passa_empresa(
    client: FlaskClient, conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    perfil_id = _criar_contato(conn, "Joaquim Millan", empresa="Bienal")
    _monkey_playwright(monkeypatch)
    resultado = ResultadoBusca(
        autenticado=True,
        motivo=None,
        candidatos=[
            Candidato(
                nome_exibido="Joaquim Millan",
                descricao="Curador · Bienal",
                link="https://www.linkedin.com/in/joaquim-millan/",
            )
        ],
    )
    chamadas = _monkey_buscar(monkeypatch, resultado)

    resposta = client.post(f"/contatos/{perfil_id}/redes-sociais/buscar", data={"rede": "linkedin"})

    assert resposta.status_code == 200
    texto = resposta.get_data(as_text=True)
    assert "Candidatos em linkedin" in texto
    assert "Joaquim Millan" in texto
    assert "Curador" in texto
    assert "linkedin.com/in/joaquim-millan" in texto
    assert "Confirmar" in texto
    assert "Descartar" in texto
    assert chamadas["nome"] == "Joaquim Millan"
    assert chamadas["empresa"] == "Bienal"


def test_busca_sem_sessao_mostra_aviso_sem_estourar(
    client: FlaskClient, conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    perfil_id = _criar_contato(conn, "Ana")
    _monkey_playwright(monkeypatch)
    _monkey_buscar(
        monkeypatch,
        ResultadoBusca(autenticado=False, motivo="sem sessão ativa em linkedin", candidatos=[]),
    )

    resposta = client.post(f"/contatos/{perfil_id}/redes-sociais/buscar", data={"rede": "linkedin"})

    assert resposta.status_code == 200
    texto = resposta.get_data(as_text=True)
    assert "sem sessão" in texto


def test_confirmar_candidato_via_form_de_adicao_persiste_em_rede_social(
    client: FlaskClient, conn: sqlite3.Connection
) -> None:
    perfil_id = _criar_contato(conn, "Beto")

    resposta = client.post(
        f"/contatos/{perfil_id}/redes-sociais/adicionar",
        data={"rede": "linkedin", "link": "https://www.linkedin.com/in/beto/"},
        follow_redirects=False,
    )

    assert resposta.status_code == 302
    linhas = redes_sociais.listar_por_perfil(conn, perfil_id)
    assert [(r.rede, r.link) for r in linhas] == [("linkedin", "https://www.linkedin.com/in/beto/")]


def test_ficha_sem_busca_mostra_botoes_de_busca_por_rede(
    client: FlaskClient, conn: sqlite3.Connection
) -> None:
    perfil_id = _criar_contato(conn, "Carla")

    resposta = client.get(f"/contatos/{perfil_id}")

    assert resposta.status_code == 200
    texto = resposta.get_data(as_text=True)
    assert "Buscar candidatos na rede" in texto
    assert "Buscar em linkedin" in texto
    assert "Buscar em instagram" in texto
    assert "Buscar em facebook" in texto
    assert "Buscar em x" in texto
