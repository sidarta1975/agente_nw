from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

import agente_nw.cli as cli
from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import assunto_contato, assuntos, perfis
from agente_nw.nucleo.modelos.assunto import Assunto
from agente_nw.nucleo.modelos.assunto_contato import AssuntoContato

AGORA = "2026-01-01T00:00:00+00:00"
DIA = "2026-09-19"


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


def _preparar_ambiente(monkeypatch: pytest.MonkeyPatch, conn: sqlite3.Connection, tmp_path: Path) -> None:
    monkeypatch.setattr(cli, "banco", lambda: conn)
    monkeypatch.setattr(cli, "RAIZ", tmp_path)
    caminho_log_llm = tmp_path / "dados" / "logs" / "chamadas_llm.jsonl"
    monkeypatch.setattr(cli, "caminho_log_chamadas_llm", lambda: caminho_log_llm)


def _criar_assunto_contato(
    conn: sqlite3.Connection, perfil_id: int, tipo: str, status: str, gerado_em: str = DIA
) -> None:
    assunto_id = assuntos.inserir(conn, Assunto(primeiro_visto=AGORA, ultimo_visto=AGORA, status="novo"))
    registro = AssuntoContato(
        assunto_id=assunto_id,
        perfil_id=perfil_id,
        gerado_em=gerado_em,
        tipo=tipo,  # type: ignore[arg-type]
        aderencia_contato=0.7,
        aderencia_usuario=0.6,
        conversavel=0.5,
        score=70.0,
        status=status,  # type: ignore[arg-type]
    )
    assunto_contato.inserir(conn, registro)


def test_certificar_bate_com_os_numeros_fabricados(
    monkeypatch: pytest.MonkeyPatch,
    conn: sqlite3.Connection,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _preparar_ambiente(monkeypatch, conn, tmp_path)

    pasta_logs = tmp_path / "dados" / "logs"
    pasta_logs.mkdir(parents=True)
    registros_llm = [
        {"tarefa": "qualificar", "tentativas_usadas": 1, "sucesso": True, "quando": f"{DIA}T06:10:00+00:00"},
        {"tarefa": "qualificar", "tentativas_usadas": 2, "sucesso": True, "quando": f"{DIA}T06:11:00+00:00"},
        {"tarefa": "cruzar", "tentativas_usadas": 2, "sucesso": False, "quando": f"{DIA}T06:12:00+00:00"},
    ]
    with (pasta_logs / "chamadas_llm.jsonl").open("w", encoding="utf-8") as arquivo:
        for registro in registros_llm:
            arquivo.write(json.dumps(registro) + "\n")

    contato = perfis.inserir_ou_atualizar_contato(
        conn, "Fulano", "+5511900000000", None, None, None, None, AGORA
    )
    assert contato.id is not None
    _criar_assunto_contato(conn, contato.id, "conector", "usado")
    _criar_assunto_contato(conn, contato.id, "viavel_com_esforco", "nao_serve")
    _criar_assunto_contato(conn, contato.id, "fora_do_dominio", "descartado")
    conn.commit()

    resultado = cli.certificar_cmd(DIA, DIA)

    assert resultado == 0
    saida = capsys.readouterr().out
    assert "Contatos com sugestão: 1" in saida
    assert "Assuntos entregues: 2 (usado: 1, não serve: 1, novo/pendente: 0)" in saida
    assert "Aproveitamento geral: 1/2 (50.0%)" in saida
    assert "Chamadas de LLM no período: 3" in saida
    assert "Sucesso na primeira tentativa: 1/3 (33.3%)" in saida
    assert "órfãos (deveria ser sempre 0): 0" in saida


def test_certificar_sem_dados_nao_trava(
    monkeypatch: pytest.MonkeyPatch,
    conn: sqlite3.Connection,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _preparar_ambiente(monkeypatch, conn, tmp_path)

    resultado = cli.certificar_cmd(DIA, DIA)

    assert resultado == 0
    saida = capsys.readouterr().out
    assert "Nenhuma chamada de LLM registrada no período." in saida
