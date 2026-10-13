from __future__ import annotations

import sqlite3


def declarar(conexao: sqlite3.Connection, perfil_id: int, rede: str, agora: str) -> None:
    """O usuário disse que o contato não tem conta nessa rede."""
    conexao.execute(
        "INSERT INTO rede_sem_perfil (perfil_id, rede, declarado_em) VALUES (?, ?, ?) "
        "ON CONFLICT(perfil_id, rede) DO UPDATE SET declarado_em = excluded.declarado_em",
        (perfil_id, rede, agora),
    )


def remover(conexao: sqlite3.Connection, perfil_id: int, rede: str) -> None:
    conexao.execute("DELETE FROM rede_sem_perfil WHERE perfil_id = ? AND rede = ?", (perfil_id, rede))


def listar_redes(conexao: sqlite3.Connection, perfil_id: int) -> set[str]:
    linhas = conexao.execute("SELECT rede FROM rede_sem_perfil WHERE perfil_id = ?", (perfil_id,)).fetchall()
    return {linha["rede"] for linha in linhas}
