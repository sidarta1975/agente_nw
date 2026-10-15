from __future__ import annotations

import dataclasses
import sqlite3
from pathlib import Path
from typing import Any

import pytest

import agente_nw.cli as cli
import agente_nw.nucleo.consulta as consulta_mod
from agente_nw.nucleo.consulta import ResultadoConsulta, rotulo_da_fonte
from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import pedidos
from tests import test_cli_pedir_redacao as base
from tests.test_console_tela_unica import _app
from tests.test_fluxo import Cenario

BLOQUEADO_ATE = "2026-10-14T15:30:00+00:00"
CASOS = [
    ("google", None, "Notícias: Google"),
    ("alternativa", BLOQUEADO_ATE, "Notícias: fonte alternativa (Google bloqueado até"),
    ("reaproveitada", None, "Notícias reaproveitadas da coleta de hoje"),
    ("nenhuma", None, "Sem notícias agora — ganchos a partir das publicações e dos seus temas."),
]


@pytest.mark.parametrize(("fonte", "bloqueado_ate", "esperado"), CASOS)
def test_rotulo_dos_quatro_casos(fonte: str, bloqueado_ate: str | None, esperado: str) -> None:
    assert rotulo_da_fonte(fonte, bloqueado_ate).startswith(esperado)


def test_alternativa_sem_horario_nao_inventa_hora() -> None:
    assert rotulo_da_fonte("alternativa") == "Notícias: fonte alternativa"


@pytest.mark.parametrize(("fonte", "bloqueado_ate", "esperado"), CASOS)
def test_o_rotulo_chega_ao_pedido_e_a_pagina(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fonte: str, bloqueado_ate: str | None, esperado: str
) -> None:
    cenario = Cenario(tmp_path, monkeypatch)
    cenario.contato(curar=True)
    cenario.fonte_noticias = fonte
    cenario.google_bloqueado_ate = bloqueado_ate
    client = _app(cenario)

    client.post("/pedir", data={"texto": "Falar com a Marta sobre vela"})

    gravado = pedidos.obter_por_id(cenario.conn, 1)
    assert gravado is not None
    assert (gravado.noticias_fonte, gravado.noticias_bloqueado_ate) == (fonte, bloqueado_ate)
    pagina = client.get("/pedido/1").get_data(as_text=True)
    assert esperado in pagina


@pytest.fixture
def ambiente_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> sqlite3.Connection:
    conn = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conn)
    base.ESTADO.clear()
    base.ESTADO["meio"] = "whatsapp"
    monkeypatch.setattr(cli, "banco", lambda: conn)
    monkeypatch.setattr(cli, "llm", lambda: base._LLMFalso())
    monkeypatch.setattr(cli, "_contexto_de_navegacao", lambda *_a, **_k: None)
    return conn


@pytest.mark.parametrize(("fonte", "bloqueado_ate", "esperado"), CASOS)
def test_o_rotulo_chega_ao_terminal(
    ambiente_cli: sqlite3.Connection,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    fonte: str,
    bloqueado_ate: str | None,
    esperado: str,
) -> None:
    def preparar(**kwargs: Any) -> ResultadoConsulta:
        resultado = base._preparar_falso(**kwargs)
        return dataclasses.replace(resultado, fonte_noticias=fonte, google_bloqueado_ate=bloqueado_ate)

    monkeypatch.setattr(consulta_mod, "preparar", preparar)

    assert cli.pedir_cmd("Falar com o Otávio", True, False, None) == 0

    assert esperado in capsys.readouterr().out


def test_o_json_nao_leva_o_rotulo(
    ambiente_cli: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(consulta_mod, "preparar", base._preparar_falso)

    cli.pedir_cmd("Falar com o Otávio", True, True, None)

    assert "Notícias" not in capsys.readouterr().out
