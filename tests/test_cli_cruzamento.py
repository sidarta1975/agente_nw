from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

import agente_nw.cli as cli
from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import perfis
from agente_nw.nucleo.modelos.configuracao import (
    AgrupamentoLimiares,
    ColetaLimiares,
    ConectorLimiares,
    Limiares,
    QualificacaoLimiares,
)

AGORA = "2026-09-19T00:00:00+00:00"


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
    )


class _ConfigFake:
    def __init__(self, limiares: Limiares) -> None:
        self.limiares = limiares


def test_menu_sem_assunto_contato_hoje_avisa_claro(
    monkeypatch: pytest.MonkeyPatch, conn: sqlite3.Connection, capsys: pytest.CaptureFixture[str]
) -> None:
    contato = perfis.inserir_ou_atualizar_contato(
        conn, "Fulano", "+5511900000000", None, None, None, None, AGORA
    )
    assert contato.id is not None
    conn.commit()

    monkeypatch.setattr(cli, "banco", lambda: conn)

    resultado = cli.menu_cmd("+5511900000000")

    assert resultado == 0
    saida = capsys.readouterr().out
    assert "Nenhum assunto no menu de hoje" in saida


def test_menu_de_telefone_inexistente_da_erro_claro(
    monkeypatch: pytest.MonkeyPatch, conn: sqlite3.Connection, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli, "banco", lambda: conn)

    resultado = cli.menu_cmd("+5511999999999")

    assert resultado == 1
    saida = capsys.readouterr().out
    assert "FALHA" in saida


def test_cruzar_sem_nenhum_contato_ativo_nao_erra(
    monkeypatch: pytest.MonkeyPatch, conn: sqlite3.Connection, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli, "banco", lambda: conn)
    monkeypatch.setattr(cli, "configuracao", lambda: _ConfigFake(_limiares()))
    monkeypatch.setattr(cli, "llm", lambda: object())

    resultado = cli.cruzar_cmd()

    assert resultado == 0
    saida = capsys.readouterr().out
    assert "Nenhum contato ativo" in saida
