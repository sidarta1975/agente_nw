"""Importação da conversa para o banco e fila de extração (brief 061)."""

from __future__ import annotations

import io
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from flask import Flask
from flask.testing import FlaskClient
from pydantic import BaseModel

import agente_nw.console.app as console_app
from agente_nw.coleta.whatsapp import importador
from agente_nw.coleta.whatsapp.leitor import ConversaWhatsapp, MensagemWhatsapp
from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import fila_extracao, perfis
from agente_nw.nucleo.llm import ClienteOllama
from agente_nw.nucleo.modelos.configuracao import WhatsappLimiares
from agente_nw.nucleo.modelos.extracao import FatoDatado, RespostaExtracaoTexto
from agente_nw.perfil.extrator import processar_fila
from tests.test_console_novo_contato import _limiares

AGORA = "2026-10-25T10:00:00+00:00"
DAVI = "Davi Pires"
JOANA = "Joana Prado"
_LIMIARES = WhatsappLimiares(meses_extraidos=24, maximo_caracteres_bloco=6000, trocas_no_prompt=10)


class _ClienteOllamaFalso(ClienteOllama):
    def __init__(self, resposta: RespostaExtracaoTexto) -> None:
        self._resposta = resposta

    def gerar_json(self, tarefa_nome: str, prompt: str, esquema: type[BaseModel]) -> Any:
        return self._resposta


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


def _contato(conn: sqlite3.Connection, nome: str = JOANA) -> int:
    contato = perfis.inserir_novo_contato(conn, nome, None, None, AGORA)
    conn.commit()
    assert contato.id is not None
    return contato.id


def _mensagem(autor: str, quando: datetime, texto: str) -> MensagemWhatsapp:
    return MensagemWhatsapp(autor, quando, texto)


def _n_mensagens(conn: sqlite3.Connection, perfil_id: int) -> int:
    (n,) = conn.execute("SELECT COUNT(*) FROM conversa_mensagem WHERE perfil_id = ?", (perfil_id,)).fetchone()
    return int(n)


def test_importar_grava_mensagens_com_autor_resolvido(conn: sqlite3.Connection) -> None:
    perfil_id = _contato(conn)
    conversa = ConversaWhatsapp(
        participantes=(DAVI, JOANA),
        mensagens=(
            _mensagem(DAVI, datetime(2026, 9, 1, 10, 0), "oi"),
            _mensagem(JOANA, datetime(2026, 9, 1, 10, 1), "tudo bem?"),
        ),
    )

    resumo = importador.importar(conn, perfil_id, conversa, DAVI, AGORA)

    assert resumo.novas == 2 and resumo.repetidas == 0
    autores = {
        linha["autor"]
        for linha in conn.execute(
            "SELECT autor FROM conversa_mensagem WHERE perfil_id = ?", (perfil_id,)
        ).fetchall()
    }
    assert autores == {"usuario", "contato"}


def test_importar_de_novo_nao_duplica(conn: sqlite3.Connection) -> None:
    perfil_id = _contato(conn)
    conversa = ConversaWhatsapp(
        participantes=(DAVI, JOANA),
        mensagens=(
            _mensagem(DAVI, datetime(2026, 9, 1, 10, 0), "oi"),
            _mensagem(JOANA, datetime(2026, 9, 1, 10, 1), "tudo bem?"),
        ),
    )
    importador.importar(conn, perfil_id, conversa, DAVI, AGORA)

    resumo = importador.importar(conn, perfil_id, conversa, DAVI, AGORA)

    assert resumo.novas == 0 and resumo.repetidas == 2
    assert _n_mensagens(conn, perfil_id) == 2


def test_importacao_sobreposta_so_grava_as_novas(conn: sqlite3.Connection) -> None:
    perfil_id = _contato(conn)
    primeira = ConversaWhatsapp(
        participantes=(DAVI, JOANA), mensagens=(_mensagem(DAVI, datetime(2026, 9, 1, 10, 0), "oi"),)
    )
    importador.importar(conn, perfil_id, primeira, DAVI, AGORA)

    segunda = ConversaWhatsapp(
        participantes=(DAVI, JOANA),
        mensagens=(
            _mensagem(DAVI, datetime(2026, 9, 1, 10, 0), "oi"),
            _mensagem(JOANA, datetime(2026, 9, 1, 10, 1), "tudo bem?"),
        ),
    )
    resumo = importador.importar(conn, perfil_id, segunda, DAVI, AGORA)

    assert resumo.novas == 1 and resumo.repetidas == 1
    assert _n_mensagens(conn, perfil_id) == 2


def test_so_mensagens_do_contato_vao_para_a_fila(conn: sqlite3.Connection) -> None:
    perfil_id = _contato(conn)
    conversa = ConversaWhatsapp(
        participantes=(DAVI, JOANA),
        mensagens=(
            _mensagem(DAVI, datetime(2026, 9, 5, 10, 0), "pergunta do davi"),
            _mensagem(JOANA, datetime(2026, 9, 5, 10, 1), "resposta da joana"),
        ),
    )
    importador.importar(conn, perfil_id, conversa, DAVI, AGORA)

    importador.enfileirar_extracao(conn, perfil_id, _LIMIARES, AGORA)

    pendentes = fila_extracao.listar_pendentes(conn, 10)
    assert len(pendentes) == 1
    assert pendentes[0].origem == "whatsapp:2026-09"
    assert "resposta da joana" in pendentes[0].texto
    assert "pergunta do davi" not in pendentes[0].texto


def test_agrupamento_por_mes_e_limite_de_meses(conn: sqlite3.Connection) -> None:
    perfil_id = _contato(conn)
    conversa = ConversaWhatsapp(
        participantes=(DAVI, JOANA),
        mensagens=(
            _mensagem(JOANA, datetime(2026, 7, 1, 10, 0), "mensagem de julho"),
            _mensagem(JOANA, datetime(2026, 8, 1, 10, 0), "mensagem de agosto"),
            _mensagem(JOANA, datetime(2026, 9, 1, 10, 0), "mensagem de setembro"),
        ),
    )
    importador.importar(conn, perfil_id, conversa, DAVI, AGORA)
    limiares = WhatsappLimiares(meses_extraidos=2, maximo_caracteres_bloco=6000, trocas_no_prompt=10)

    enfileirados = importador.enfileirar_extracao(conn, perfil_id, limiares, AGORA)

    assert enfileirados == 2
    origens = {item.origem for item in fila_extracao.listar_pendentes(conn, 10)}
    assert origens == {"whatsapp:2026-09", "whatsapp:2026-08"}  # os 2 mais recentes; julho fora


def test_enfileirar_de_novo_nao_repete_mes_ja_extraido(conn: sqlite3.Connection) -> None:
    perfil_id = _contato(conn)
    conversa = ConversaWhatsapp(
        participantes=(DAVI, JOANA),
        mensagens=(_mensagem(JOANA, datetime(2026, 9, 1, 10, 0), "oi"),),
    )
    importador.importar(conn, perfil_id, conversa, DAVI, AGORA)
    importador.enfileirar_extracao(conn, perfil_id, _LIMIARES, AGORA)

    enfileirados_de_novo = importador.enfileirar_extracao(conn, perfil_id, _LIMIARES, AGORA)

    assert enfileirados_de_novo == 0


def test_unir_contato_leva_as_mensagens(conn: sqlite3.Connection) -> None:
    canonico_id = _contato(conn, "Joana Prado")
    duplicado_id = _contato(conn, "Joana P.")
    conversa = ConversaWhatsapp(
        participantes=(DAVI, JOANA), mensagens=(_mensagem(JOANA, datetime(2026, 9, 1, 10, 0), "oi"),)
    )
    importador.importar(conn, duplicado_id, conversa, DAVI, AGORA)

    perfis.unir_contatos(conn, canonico_id, duplicado_id)

    assert _n_mensagens(conn, canonico_id) == 1
    assert _n_mensagens(conn, duplicado_id) == 0


def test_fato_extraido_de_bloco_whatsapp_fica_com_a_data_do_mes(conn: sqlite3.Connection) -> None:
    perfil_id = _contato(conn)
    fila_extracao.inserir(conn, perfil_id, "texto do mês", "whatsapp:2026-03", AGORA)
    conn.commit()
    resposta = RespostaExtracaoTexto(
        fatos_datados=[FatoDatado(data="2099-01-15", tipo="conversa", conteudo="algo dito", fonte=None)]
    )

    processar_fila(_ClienteOllamaFalso(resposta), conn)

    (data_do_fato,) = conn.execute(
        "SELECT data_do_fato FROM fato WHERE perfil_id = ?", (perfil_id,)
    ).fetchone()
    assert data_do_fato == "2026-03-01"


# ---- pelo console (envio, confirmação, "sem fotos e audios") -----------------------------------------


def _app(caminho_banco: Path) -> FlaskClient:
    app: Flask = console_app.criar_app(
        caminho_banco, caminho_banco.parent / "log.jsonl", object(), _limiares(), "http://unused"
    )
    return app.test_client()


@pytest.fixture
def banco(tmp_path: Path) -> Path:
    caminho = tmp_path / "teste.db"
    conexao_aberta = conexao.abrir(caminho)
    migracoes.aplicar(conexao_aberta)
    perfis.upsert_usuario(conexao_aberta, "Caio Serra", AGORA)
    perfis.inserir_novo_contato(conexao_aberta, "Joana Prado", None, None, AGORA)
    conexao_aberta.commit()
    conexao_aberta.close()
    return caminho


def test_enviar_mostra_confirmacao_com_voce_sugerido(banco: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _app(banco)
    dados = (Path(__file__).parent / "fixtures" / "whatsapp_ios.zip").read_bytes()

    resposta = client.post(
        "/pessoa/2/whatsapp/enviar",
        data={"arquivos": (io.BytesIO(dados), "whatsapp_ios.zip")},
        content_type="multipart/form-data",
    )
    pagina = resposta.get_data(as_text=True)

    assert "Joana Prado" in pagina and "Caio Serra" in pagina
    assert '<input type="radio" name="voce" value="Caio Serra" checked>' in pagina


def test_confirmar_importa_e_mostra_resumo(banco: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(console_app.extrator, "processar_fila", lambda *_a, **_k: None)
    monkeypatch.setattr(console_app, "ClienteOllama", lambda *_a, **_k: object())
    client = _app(banco)
    dados = (Path(__file__).parent / "fixtures" / "whatsapp_ios.zip").read_bytes()
    envio = client.post(
        "/pessoa/2/whatsapp/enviar",
        data={"arquivos": (io.BytesIO(dados), "whatsapp_ios.zip")},
        content_type="multipart/form-data",
    )
    pending_id = envio.get_data(as_text=True).split('name="pending_id" value="')[1].split('"')[0]

    resposta = client.post(
        "/pessoa/2/whatsapp/confirmar", data={"pending_id": pending_id, "voce": "Caio Serra"}
    )
    pagina = client.get(str(resposta.headers["Location"])).get_data(as_text=True)

    assert "3 mensagens novas, 0 já estavam" in pagina
    conexao_aberta = conexao.abrir(banco)
    autores = {
        linha["autor"] for linha in conexao_aberta.execute("SELECT autor FROM conversa_mensagem").fetchall()
    }
    assert autores == {"usuario", "contato"}


def test_grupo_e_recusado_na_pagina(banco: Path) -> None:
    client = _app(banco)
    texto_grupo = "\n".join(
        [
            "[01/02/2026, 08:00:00] Joana Prado: oi pessoal",
            "[01/02/2026, 08:01:00] Caio Serra: oi!",
            "[01/02/2026, 08:02:00] Renata Alves: e aí",
        ]
    )

    resposta = client.post(
        "/pessoa/2/whatsapp/enviar",
        data={"arquivos": (io.BytesIO(texto_grupo.encode("utf-8")), "grupo.txt")},
        content_type="multipart/form-data",
    )
    pagina = client.get(str(resposta.headers["Location"])).get_data(as_text=True)

    assert "Por enquanto só conversa individual" in pagina
