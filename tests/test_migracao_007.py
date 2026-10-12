from __future__ import annotations

from pathlib import Path

from agente_nw.nucleo.database import conexao, migracoes


def test_tabela_pedido_existe_apos_migrar(tmp_path: Path) -> None:
    conn = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conn)

    colunas = {linha["name"] for linha in conn.execute("PRAGMA table_info(pedido)").fetchall()}

    assert {"id", "perfil_id", "texto", "extraido_json", "confianca"} <= colunas
    assert {"contato_criado", "contato_ambiguo", "criado_em"} <= colunas
    conn.close()
