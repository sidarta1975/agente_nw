from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest

import agente_nw.cli as cli
import agente_nw.nucleo.consulta as consulta_mod
from agente_nw.nucleo.consulta import ItemMenu, ResultadoConsulta, ResumoRedeSocial
from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import assuntos as assuntos_q
from agente_nw.nucleo.database.queries import consulta_contato as consulta_contato_q
from agente_nw.nucleo.database.queries import fontes as fontes_q
from agente_nw.nucleo.database.queries import gancho_uso, perfis
from agente_nw.nucleo.database.queries import itens as itens_q
from agente_nw.nucleo.modelos.assunto import Assunto
from agente_nw.nucleo.modelos.item import Item
from agente_nw.nucleo.modelos.pedido import PedidoExtraido
from agente_nw.nucleo.modelos.redacao import Gancho, RespostaRedacao

AGORA = "2026-10-12T10:00:00+00:00"
ESTADO: dict[str, Any] = {}


def _pedido(meio: str) -> PedidoExtraido:
    return PedidoExtraido.model_validate(
        {
            "pessoa_nome": "Otávio",
            "pessoa_pistas": {"vinculo": "ex-sócio"},
            "objetivo": "retomar",
            "objetivo_texto": "voltar a conversar",
            "meio": meio,
            "registro": "cordial",
            "assunto_principal": "mercado de seguros",
            "termos_busca": ["seguros"],
            "confianca": 0.9,
        }
    )


class _LLMFalso:
    def gerar_json(self, tarefa_nome: str, prompt: str, esquema: type[Any]) -> Any:
        if tarefa_nome == "extrair_pedido":
            return _pedido(ESTADO["meio"])
        gancho = Gancho(
            assunto_id=ESTADO["assunto_id"],
            titulo="Seguradora muda regra de reajuste",
            noticia="A seguradora mudou a regra. A mudança vale em janeiro.",
            por_que_para_esta_pessoa="Ele atua no setor de seguros.",
            mensagem="Oi, Otávio! Li que o reajuste dos seguros vai mudar e lembrei de você.",
            abordagem_presencial="Pergunte como o setor reagiu à mudança.",
        )
        base = Gancho(
            peculiaridade="atua no setor de seguros",
            por_que_para_esta_pessoa="Retoma a conversa pelo setor dele.",
            mensagem="Oi, Otávio! Faz tempo que a gente não se fala. Como anda o setor de seguros?",
            abordagem_presencial="Comece perguntando do setor.",
        )
        return RespostaRedacao(ganchos=[base, gancho])


def _preparar_falso(**kwargs: Any) -> ResultadoConsulta:
    conn: sqlite3.Connection = kwargs["conexao"]
    assunto_id = assuntos_q.inserir(
        conn,
        Assunto(titulo_gerado="Regra de reajuste", primeiro_visto=AGORA, ultimo_visto=AGORA, status="novo"),
    )
    ESTADO["assunto_id"] = assunto_id
    fonte = fontes_q.obter_ou_criar(conn, "Gazeta", "https://gazeta.test/feed", "gazeta.test", "rss", 5)
    assert fonte.id is not None
    itens_q.inserir(
        conn,
        Item(
            fonte_id=fonte.id,
            url_canonica="https://gazeta.test/reajuste",
            titulo="Seguradora muda regra de reajuste",
            coletado_em=AGORA,
            hash_titulo="h-reajuste",
            assunto_id=assunto_id,
        ),
    )
    consulta = consulta_contato_q.inserir(conn, kwargs["perfil_id"], AGORA, "{}", None, "[]")
    conn.commit()
    assert consulta.id is not None
    item = ItemMenu(1, assunto_id, "conector", "Regra de reajuste", "ele atua no setor", 71.0)
    return ResultadoConsulta(kwargs["perfil_id"], consulta.id, [item], ResumoRedeSocial(), "")


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


@pytest.fixture(autouse=True)
def _ambiente(conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch) -> None:
    ESTADO.clear()
    ESTADO["meio"] = "pessoalmente"
    monkeypatch.setattr(cli, "banco", lambda: conn)
    monkeypatch.setattr(cli, "llm", lambda: _LLMFalso())
    monkeypatch.setattr(cli, "_contexto_de_navegacao", lambda *_a, **_k: None)
    monkeypatch.setattr(consulta_mod, "preparar", _preparar_falso)


def test_pedir_entrega_a_redacao_por_padrao(
    conn: sqlite3.Connection, capsys: pytest.CaptureFixture[str]
) -> None:
    assert cli.pedir_cmd("Almoço com o Otávio", True, False, None) == 0

    saida = capsys.readouterr().out
    assert "Ganchos para Otávio" in saida
    assert "1. Mensagem base" in saida
    assert "Peculiaridade: atua no setor de seguros" in saida
    assert "2. Seguradora muda regra de reajuste" in saida
    assert "Mensagem:" in saida
    assert "Abordagem presencial: Pergunte como o setor reagiu" in saida
    assert "Links:" in saida
    assert "- gazeta.test: Seguradora muda regra de reajuste" in saida
    assert "https://gazeta.test/reajuste" in saida
    linhas = conn.execute("SELECT status FROM gancho_uso").fetchall()
    assert [linha["status"] for linha in linhas] == ["entregue", "entregue"]


def test_pedido_por_whatsapp_traz_so_a_mensagem(capsys: pytest.CaptureFixture[str]) -> None:
    ESTADO["meio"] = "whatsapp"

    cli.pedir_cmd("Falar com o Otávio", True, False, None)

    saida = capsys.readouterr().out
    assert "Mensagem:" in saida
    assert "Abordagem presencial" not in saida


def test_menu_mantem_o_formato_anterior(conn: sqlite3.Connection, capsys: pytest.CaptureFixture[str]) -> None:
    cli.pedir_cmd("Almoço com o Otávio", True, False, None, menu=True)

    saida = capsys.readouterr().out
    assert "[conector] Regra de reajuste (score=71.0)" in saida
    assert "por quê: ele atua no setor" in saida
    assert "Mensagem:" not in saida
    assert gancho_uso.listar_por_consulta(conn, 1) == []


def test_json_imprime_a_redacao(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.pedir_cmd("Almoço com o Otávio", True, True, None) == 0

    dados = json.loads(capsys.readouterr().out)
    assert dados["registro_usado"] == "cordial"
    assert dados["ganchos"][1]["titulo"] == "Seguradora muda regra de reajuste"


def test_homonimos_nao_preparam_nem_gravam_rede_em_quem_pode_ser_outro(
    conn: sqlite3.Connection, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    perfis.inserir_novo_contato(conn, "Otávio Alves", None, None, AGORA)
    perfis.inserir_novo_contato(conn, "Otávio Souza", None, None, AGORA)
    conn.commit()

    def _nao_deveria_preparar(**_kwargs: Any) -> ResultadoConsulta:
        raise AssertionError("não prepara com contato ambíguo")

    monkeypatch.setattr(consulta_mod, "preparar", _nao_deveria_preparar)

    assert cli.pedir_cmd("Almoço com o Otávio", True, False, None) == 0

    saida = capsys.readouterr().out
    assert "escolha um com --contato" in saida
    assert "Ganchos para" not in saida
