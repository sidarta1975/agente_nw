from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

import agente_nw.cli as cli
from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.modelos.configuracao import (
    AgrupamentoLimiares,
    ColetaLimiares,
    ConectorLimiares,
    Limiares,
    QualificacaoLimiares,
)


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
            divergencia_minima_fonte_independente=0.30,
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


def test_agrupar_sem_itens_pendentes_nao_erra_e_relata_zero(
    monkeypatch: pytest.MonkeyPatch,
    conn: sqlite3.Connection,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli, "banco", lambda: conn)
    monkeypatch.setattr(cli, "configuracao", lambda: _ConfigFake(_limiares()))
    monkeypatch.setattr(cli, "caminho_sentinela", lambda: tmp_path / "PARE")
    monkeypatch.setattr(cli, "llm", lambda: object())

    resultado = cli.agrupar_cmd()

    assert resultado == 0
    saida = capsys.readouterr().out
    assert "Assuntos criados: 0" in saida
    assert "Itens vinculados: 0" in saida


def test_calibrar_agrupamento_sem_itens_com_embedding_nao_trava(
    monkeypatch: pytest.MonkeyPatch,
    conn: sqlite3.Connection,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    caminho_limiares = tmp_path / "limiares.yaml"
    caminho_limiares.write_text(
        "agrupamento:\n  cosseno_mesmo_assunto: 0.82  # calibrar no brief 007\n", encoding="utf-8"
    )
    caminho_adr_pasta = tmp_path / "adr"

    monkeypatch.setattr(cli, "banco", lambda: conn)
    monkeypatch.setattr(cli, "llm", lambda: object())
    monkeypatch.setattr(cli, "caminho_limiares_yaml", lambda: caminho_limiares)
    monkeypatch.setattr(cli, "caminho_pasta_adr", lambda: caminho_adr_pasta)

    resultado = cli.calibrar_agrupamento_cmd()

    assert resultado == 0
    saida = capsys.readouterr().out
    assert "Pares avaliados pelo qwen3:8b: 0" in saida
    assert (caminho_adr_pasta / "adr-0001-limiar-agrupamento.md").exists()
