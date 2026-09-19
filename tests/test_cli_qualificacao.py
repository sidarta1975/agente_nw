from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

import agente_nw.cli as cli
from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import assuntos, fontes, itens
from agente_nw.nucleo.modelos.assunto import Assunto
from agente_nw.nucleo.modelos.cartao import RespostaCartao
from agente_nw.nucleo.modelos.configuracao import (
    AgrupamentoLimiares,
    CartaoLimiares,
    ColetaLimiares,
    ConectorLimiares,
    Limiares,
    QualificacaoLimiares,
)
from agente_nw.nucleo.modelos.item import Item

AGORA = "2026-01-01T00:00:00+00:00"


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


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


class _ConfigFake:
    def __init__(self, limiares: Limiares) -> None:
        self.limiares = limiares


class _ClienteCartaoFake:
    def __init__(self, resposta: RespostaCartao) -> None:
        self._resposta = resposta

    def gerar_json(self, tarefa_nome: str, prompt: str, esquema: type[RespostaCartao]) -> RespostaCartao:
        return self._resposta


def test_qualificar_sem_candidatos_nao_erra(
    monkeypatch: pytest.MonkeyPatch, conn: sqlite3.Connection, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli, "banco", lambda: conn)
    monkeypatch.setattr(cli, "configuracao", lambda: _ConfigFake(_limiares()))
    monkeypatch.setattr(cli, "llm", lambda: object())

    resultado = cli.qualificar_cmd(None)

    assert resultado == 0
    saida = capsys.readouterr().out
    assert "Candidatos: 0" in saida
    assert "Qualificados: 0" in saida


def test_cartao_de_assunto_sem_qualificacao_ainda_funciona(
    monkeypatch: pytest.MonkeyPatch, conn: sqlite3.Connection, capsys: pytest.CaptureFixture[str]
) -> None:
    fonte = fontes.obter_ou_criar(conn, "g1.globo.com", "https://g1.globo.com/rss", "g1.globo.com", "rss", 5)
    assert fonte.id is not None
    assunto = Assunto(
        titulo_gerado="Título já gerado",
        primeiro_visto=AGORA,
        ultimo_visto=AGORA,
        n_itens=1,
        status="novo",
    )
    assunto_id = assuntos.inserir(conn, assunto)
    item = Item(
        fonte_id=fonte.id,
        url_canonica="https://exemplo.com/1",
        titulo="Título do item",
        texto="Texto de exemplo.",
        coletado_em=AGORA,
        hash_titulo="hash-1",
        assunto_id=assunto_id,
    )
    itens.inserir(conn, item)
    conn.commit()

    resposta = RespostaCartao(resumo="Nada de números aqui.\nSó texto corrido.\nFim.")
    monkeypatch.setattr(cli, "banco", lambda: conn)
    monkeypatch.setattr(cli, "llm", lambda: _ClienteCartaoFake(resposta))

    resultado = cli.cartao_cmd(assunto_id)

    assert resultado == 0
    saida = capsys.readouterr().out
    assert resposta.resumo in saida

    gravado = assuntos.obter_por_id(conn, assunto_id)
    assert gravado is not None
    assert gravado.substancial is None  # não qualificado, e mesmo assim o cartão funcionou


def test_cartao_de_assunto_inexistente_da_erro_claro(
    monkeypatch: pytest.MonkeyPatch, conn: sqlite3.Connection, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli, "banco", lambda: conn)
    monkeypatch.setattr(cli, "llm", lambda: object())

    resultado = cli.cartao_cmd(999)

    assert resultado == 1
    saida = capsys.readouterr().out
    assert "FALHA" in saida
