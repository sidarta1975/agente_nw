from __future__ import annotations

from pathlib import Path

from agente_nw.nucleo.database import conexao, migracoes


def test_coluna_aderencia_consulta_existe_apos_migrar(tmp_path: Path) -> None:
    conn = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conn)

    colunas = {linha["name"] for linha in conn.execute("PRAGMA table_info(assunto_contato)").fetchall()}

    assert "aderencia_consulta" in colunas
    conn.close()
