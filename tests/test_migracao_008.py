from __future__ import annotations

from pathlib import Path

from agente_nw.nucleo.database import conexao, migracoes


def test_tabela_lista_rede_social_existe_apos_migrar(tmp_path: Path) -> None:
    conn = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conn)

    colunas = {linha["name"] for linha in conn.execute("PRAGMA table_info(lista_rede_social)").fetchall()}

    esperadas = {"rede", "nome", "nome_normalizado", "cabecalho", "link", "foto_url", "lido_em", "perfil_id"}
    assert esperadas <= colunas
    conn.close()
