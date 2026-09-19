from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

import agente_nw.cli as cli
from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import sistema

HOJE = datetime.now(UTC).date().isoformat()


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


def _contador() -> dict[str, int]:
    return {
        "coleta": 0,
        "extracao": 0,
        "agrupamento": 0,
        "qualificacao": 0,
        "cruzamento": 0,
        "cartoes": 0,
        "exportacao": 0,
        "backup": 0,
        "ler_marcacoes": 0,
    }


def _instalar_fakes_padrao(
    monkeypatch: pytest.MonkeyPatch, chamadas: dict[str, int], falha_em: str | None = None
) -> None:
    def _fake(nome: str):
        def fn(*_args: object) -> int:
            chamadas[nome] += 1
            if nome == falha_em:
                raise RuntimeError(f"falha simulada em {nome}")
            return 0

        return fn

    monkeypatch.setattr(cli, "coletar", _fake("coleta"))
    monkeypatch.setattr(cli, "processar_fila_cmd", _fake("extracao"))
    monkeypatch.setattr(cli, "agrupar_cmd", _fake("agrupamento"))
    monkeypatch.setattr(cli, "qualificar_cmd", _fake("qualificacao"))
    monkeypatch.setattr(cli, "cruzar_cmd", _fake("cruzamento"))
    monkeypatch.setattr(cli, "_gerar_cartoes_cmd", _fake("cartoes"))
    monkeypatch.setattr(cli, "exportar_menu_cmd", _fake("exportacao"))
    monkeypatch.setattr(cli, "fazer_backup_cmd", _fake("backup"))
    monkeypatch.setattr(cli, "ler_marcacoes_cmd", _fake("ler_marcacoes"))


def _preparar_ambiente(monkeypatch: pytest.MonkeyPatch, conn: sqlite3.Connection, tmp_path: Path) -> None:
    monkeypatch.setattr(cli, "banco", lambda: conn)
    monkeypatch.setattr(cli, "caminho_sentinela", lambda: tmp_path / "PARE")
    monkeypatch.setattr(cli, "caminho_pasta_saida", lambda: tmp_path / "saidas")
    monkeypatch.setattr(cli, "RAIZ", tmp_path)


def test_etapa_ja_feita_hoje_e_pulada(
    monkeypatch: pytest.MonkeyPatch, conn: sqlite3.Connection, tmp_path: Path
) -> None:
    _preparar_ambiente(monkeypatch, conn, tmp_path)
    chamadas = _contador()
    _instalar_fakes_padrao(monkeypatch, chamadas)

    sistema.progresso_gravar(conn, "ciclo:coleta", None, HOJE, "2020-01-01T00:00:00+00:00")
    conn.commit()

    resultado = cli.ciclo_cmd()

    assert resultado == 0
    assert chamadas["coleta"] == 0
    assert chamadas["extracao"] == 1

    progresso = sistema.progresso_obter(conn, "ciclo:coleta")
    assert progresso is not None
    assert progresso["atualizado_em"] == "2020-01-01T00:00:00+00:00"


def test_etapa_com_excecao_nao_grava_progresso_e_sai_com_codigo_1(
    monkeypatch: pytest.MonkeyPatch, conn: sqlite3.Connection, tmp_path: Path
) -> None:
    _preparar_ambiente(monkeypatch, conn, tmp_path)
    chamadas = _contador()
    _instalar_fakes_padrao(monkeypatch, chamadas, falha_em="agrupamento")

    resultado = cli.ciclo_cmd()

    assert resultado == 1
    assert chamadas["coleta"] == 1
    assert chamadas["extracao"] == 1
    assert chamadas["agrupamento"] == 1
    assert chamadas["qualificacao"] == 0  # nunca chegou lá

    assert sistema.progresso_obter(conn, "ciclo:agrupamento") is None
    assert sistema.progresso_obter(conn, "ciclo:coleta") is not None  # etapas anteriores gravaram normal


def test_segunda_chamada_no_mesmo_dia_sai_imediato_sem_rodar_nada(
    monkeypatch: pytest.MonkeyPatch, conn: sqlite3.Connection, tmp_path: Path
) -> None:
    _preparar_ambiente(monkeypatch, conn, tmp_path)
    chamadas = _contador()
    _instalar_fakes_padrao(monkeypatch, chamadas)

    primeiro_resultado = cli.ciclo_cmd()
    assert primeiro_resultado == 0
    assert chamadas["backup"] == 1

    segundo_resultado = cli.ciclo_cmd()

    assert segundo_resultado == 0
    assert chamadas["backup"] == 1  # não rodou de novo
    assert chamadas["coleta"] == 1  # nenhuma etapa rodou de novo


def test_sentinela_presente_para_o_ciclo_antes_da_proxima_etapa_sem_erro(
    monkeypatch: pytest.MonkeyPatch, conn: sqlite3.Connection, tmp_path: Path
) -> None:
    _preparar_ambiente(monkeypatch, conn, tmp_path)
    chamadas = _contador()
    _instalar_fakes_padrao(monkeypatch, chamadas)

    caminho_sentinela = tmp_path / "PARE"
    caminho_sentinela.write_text("", encoding="utf-8")

    resultado = cli.ciclo_cmd()

    assert resultado == 0
    assert chamadas["coleta"] == 0
    assert chamadas["backup"] == 0
    assert sistema.progresso_obter(conn, "ciclo:coleta") is None
