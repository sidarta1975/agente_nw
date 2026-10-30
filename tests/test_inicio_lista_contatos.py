"""A tela inicial começa pela lista de contatos (brief 060)."""

from __future__ import annotations

from pathlib import Path

import pytest
from flask import Flask
from flask.testing import FlaskClient

import agente_nw.console.app as console_app
from agente_nw.nucleo.database.queries import pedidos, perfis
from tests.test_console_novo_contato import _limiares
from tests.test_fluxo import Cenario

ANTIGO = "2026-01-01T00:00:00+00:00"


def _app(cenario: Cenario) -> FlaskClient:
    app: Flask = console_app.criar_app(
        cenario.caminho,
        cenario.caminho.parent / "log.jsonl",
        object(),  # type: ignore[arg-type]
        _limiares(),
        "http://unused",
        dependencias=cenario.deps,
        executar=lambda tarefa: tarefa(),
    )
    return app.test_client()


@pytest.fixture
def cenario(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Cenario:
    return Cenario(tmp_path, monkeypatch)


def test_sem_busca_mostra_no_maximo_20_com_os_recentes_primeiro(cenario: Cenario) -> None:
    conn = cenario.conn
    ids = []
    for i in range(25):
        contato = perfis.inserir_novo_contato(conn, f"Contato {i:02d}", None, None, ANTIGO)
        assert contato.id is not None
        ids.append(contato.id)
    conn.commit()
    recente_id = ids[10]
    pedidos.inserir(conn, "oi", "2026-10-20T00:00:00+00:00", perfil_id=recente_id)
    conn.commit()

    lista = perfis.listar_para_inicio(conn, "", 20)

    assert len(lista) == 20
    assert lista[0].perfil_id == recente_id
    assert lista[0].ultimo_pedido_em == "2026-10-20T00:00:00+00:00"
    assert [c.nome for c in lista[1:]] == sorted(c.nome for c in lista[1:])  # completa em ordem alfabética


def test_busca_por_jose_encontra_jose_sem_acento(cenario: Cenario) -> None:
    conn = cenario.conn
    perfis.inserir_novo_contato(conn, "José Alves", None, None, ANTIGO)
    perfis.inserir_novo_contato(conn, "Maria Souza", None, None, ANTIGO)
    conn.commit()

    lista = perfis.listar_para_inicio(conn, "jose", 50)

    assert [c.nome for c in lista] == ["José Alves"]


def test_botao_nao_esta_na_lista_aparece_na_pagina(cenario: Cenario) -> None:
    client = _app(cenario)

    pagina = client.get("/").get_data(as_text=True)

    assert "Não está na lista" in pagina


def test_pedir_com_perfil_id_cria_pedido_com_o_contato_sem_perguntar_homonimos(cenario: Cenario) -> None:
    perfil_id = cenario.contato("Marta Quintela", curar=True)
    client = _app(cenario)

    resposta = client.post("/pedir", data={"texto": "Falar sobre vela", "perfil_id": str(perfil_id)})
    pagina = client.get(str(resposta.headers["Location"])).get_data(as_text=True)

    gravado = pedidos.obter_por_id(cenario.conn, 1)
    assert gravado is not None and gravado.perfil_id == perfil_id and gravado.status == "concluido"
    assert "mais de um contato com esse nome" not in pagina


def test_pedir_com_perfil_id_e_nome_divergente_pergunta_antes_de_seguir(cenario: Cenario) -> None:
    perfil_id = cenario.contato("Joaquim Bastos", curar=True)
    cenario.cliente.nome = "Marta Quintela"  # o que o LLM "extrai" da frase, diferente do contato escolhido
    client = _app(cenario)

    resposta = client.post(
        "/pedir", data={"texto": "Falar com a Marta sobre vela", "perfil_id": str(perfil_id)}
    )
    pagina = client.get(str(resposta.headers["Location"])).get_data(as_text=True)

    gravado = pedidos.obter_por_id(cenario.conn, 1)
    assert gravado is not None and gravado.status == "aguardando_pessoa"
    assert "mas o contato escolhido é" in pagina
    assert "Marta Quintela" in pagina and "Joaquim Bastos" in pagina
