from __future__ import annotations

from pathlib import Path

from agente_nw.nucleo.database import conexao, migracoes


def test_tabela_gancho_uso_existe_apos_migrar(tmp_path: Path) -> None:
    conn = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conn)

    colunas = {linha["name"] for linha in conn.execute("PRAGMA table_info(gancho_uso)").fetchall()}

    assert {"consulta_id", "assunto_id", "status", "gancho_json", "atualizado_em"} <= colunas
    versao = conn.execute("SELECT MAX(versao) AS versao FROM schema_version").fetchone()["versao"]
    assert versao >= 9
    conn.close()


def test_tabela_rede_sem_perfil_existe_apos_migrar(tmp_path: Path) -> None:
    conn = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conn)

    colunas = {linha["name"] for linha in conn.execute("PRAGMA table_info(rede_sem_perfil)").fetchall()}

    assert {"perfil_id", "rede", "declarado_em"} <= colunas
    conn.close()
