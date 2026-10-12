from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest

import agente_nw.cli as cli
from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import perfis
from agente_nw.nucleo.modelos.pedido import PedidoExtraido

AGORA = "2026-10-11T10:00:00+00:00"


def _dados(**mudancas: Any) -> dict[str, Any]:
    dados: dict[str, Any] = {
        "pessoa_nome": "Renato",
        "pessoa_pistas": {"profissao": "engenheiro naval", "vinculo": "cliente antigo"},
        "objetivo": "retomar",
        "objetivo_texto": "retomar sem pedir nada",
        "meio": "pessoalmente",
        "registro": "cordial",
        "assunto_principal": "construção naval",
        "termos_busca": ["estaleiros", "construção naval"],
        "confianca": 0.82,
    }
    dados.update(mudancas)
    return dados


class _ClienteFalso:
    def gerar_json(self, tarefa_nome: str, prompt: str, esquema: type[Any]) -> Any:
        return PedidoExtraido.model_validate(_dados())


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


@pytest.fixture(autouse=True)
def _ambiente(conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "banco", lambda: conn)
    monkeypatch.setattr(cli, "llm", lambda: _ClienteFalso())


def test_saida_traz_os_blocos_principais(capsys: pytest.CaptureFixture[str]) -> None:
    resultado = cli.pedir_cmd("Almoço com o Renato", False, False, None)

    saida = capsys.readouterr().out
    assert resultado == 0
    assert "Pessoa: Renato (contato novo)" in saida
    assert "Objetivo: retomar" in saida
    assert "Buscar notícia sobre: estaleiros; construção naval" in saida
    assert "Confiança: 0,82" in saida


def test_json_imprime_o_pedido_extraido(capsys: pytest.CaptureFixture[str]) -> None:
    resultado = cli.pedir_cmd("Almoço com o Renato", False, True, None)

    dados = json.loads(capsys.readouterr().out)
    assert resultado == 0
    assert dados["pessoa_nome"] == "Renato"
    assert dados["termos_busca"] == ["estaleiros", "construção naval"]


def test_homonimos_geram_aviso_de_ambiguidade(
    conn: sqlite3.Connection, capsys: pytest.CaptureFixture[str]
) -> None:
    perfis.inserir_novo_contato(conn, "Renato Alves", None, None, AGORA)
    perfis.inserir_novo_contato(conn, "Renato Souza", None, None, AGORA)
    conn.commit()

    cli.pedir_cmd("Almoço com o Renato", False, False, None)

    saida = capsys.readouterr().out
    assert "AVISO: encontrei 2 contatos chamados Renato" in saida
    assert "agente_nw pedir --contato <id>" in saida


def test_contato_inexistente_forcado_falha(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.pedir_cmd("Almoço com o Renato", False, False, 9999) == 1
    assert "FALHA" in capsys.readouterr().out
