from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

import agente_nw.cli as cli
from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import assunto_contato, assuntos, perfis
from agente_nw.nucleo.modelos.assunto import Assunto
from agente_nw.nucleo.modelos.assunto_contato import AssuntoContato

AGORA = "2026-09-19T00:00:00+00:00"


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


def test_exportar_menu_sem_data_usa_a_data_de_hoje(
    monkeypatch: pytest.MonkeyPatch,
    conn: sqlite3.Connection,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    contato = perfis.inserir_ou_atualizar_contato(
        conn, "Fulano", "+5511900000000", None, None, None, None, AGORA
    )
    assert contato.id is not None
    perfis.ativar(conn, contato.id)
    assunto_id = assuntos.inserir(
        conn, Assunto(titulo_gerado="Título", primeiro_visto=AGORA, ultimo_visto=AGORA, status="novo")
    )
    hoje = datetime.now(UTC).date().isoformat()
    assunto_contato.inserir(
        conn,
        AssuntoContato(
            assunto_id=assunto_id,
            perfil_id=contato.id,
            gerado_em=hoje,
            tipo="conector",
            aderencia_contato=0.7,
            aderencia_usuario=0.6,
            conversavel=0.5,
            score=70.0,
            por_que="justificativa",
            status="novo",
        ),
    )
    conn.commit()

    pasta_saida = tmp_path / "saidas"
    monkeypatch.setattr(cli, "banco", lambda: conn)
    monkeypatch.setattr(cli, "caminho_pasta_saida", lambda: pasta_saida)

    resultado = cli.exportar_menu_cmd(None)

    assert resultado == 0
    caminho_esperado = pasta_saida / f"menu_{hoje}.md"
    assert caminho_esperado.exists()
    texto = caminho_esperado.read_text(encoding="utf-8")
    assert "Título" in texto
    assert "### Conectores" in texto

    saida = capsys.readouterr().out
    assert str(caminho_esperado) in saida


def test_exportar_menu_e_ler_marcacoes_de_ponta_a_ponta(
    monkeypatch: pytest.MonkeyPatch,
    conn: sqlite3.Connection,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    contato = perfis.inserir_ou_atualizar_contato(
        conn, "Fulano", "+5511900000000", None, None, None, None, AGORA
    )
    assert contato.id is not None
    perfis.ativar(conn, contato.id)
    assunto_id = assuntos.inserir(
        conn, Assunto(titulo_gerado="Título", primeiro_visto=AGORA, ultimo_visto=AGORA, status="novo")
    )
    assunto_contato.inserir(
        conn,
        AssuntoContato(
            assunto_id=assunto_id,
            perfil_id=contato.id,
            gerado_em="2026-09-19",
            tipo="conector",
            aderencia_contato=0.7,
            aderencia_usuario=0.6,
            conversavel=0.5,
            score=70.0,
            por_que="justificativa",
            status="novo",
        ),
    )
    conn.commit()
    (ac_id,) = conn.execute("SELECT id FROM assunto_contato").fetchone()

    pasta_saida = tmp_path / "saidas"
    monkeypatch.setattr(cli, "banco", lambda: conn)
    monkeypatch.setattr(cli, "caminho_pasta_saida", lambda: pasta_saida)

    assert cli.exportar_menu_cmd("2026-09-19") == 0

    caminho_arquivo = pasta_saida / "menu_2026-09-19.md"
    texto = caminho_arquivo.read_text(encoding="utf-8")
    texto_marcado = texto.replace("- [ ] usei", "- [x] usei", 1)
    caminho_arquivo.write_text(texto_marcado, encoding="utf-8")

    resultado = cli.ler_marcacoes_cmd("2026-09-19")

    assert resultado == 0
    (status,) = conn.execute("SELECT status FROM assunto_contato WHERE id = ?", (ac_id,)).fetchone()
    assert status == "usado"

    saida = capsys.readouterr().out
    assert "Marcações aplicadas: 1" in saida


def test_ler_marcacoes_arquivo_inexistente_da_erro_claro(
    monkeypatch: pytest.MonkeyPatch,
    conn: sqlite3.Connection,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli, "banco", lambda: conn)
    monkeypatch.setattr(cli, "caminho_pasta_saida", lambda: tmp_path / "saidas")

    resultado = cli.ler_marcacoes_cmd("2026-01-01")

    assert resultado == 1
    saida = capsys.readouterr().out
    assert "FALHA" in saida
