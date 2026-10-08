from __future__ import annotations

import sqlite3

from agente_nw.nucleo.modelos.rede_social import RedeSocial

_COLUNAS = "id, perfil_id, rede, link, criado_em"


def _para_rede_social(linha: sqlite3.Row) -> RedeSocial:
    return RedeSocial(
        id=linha["id"],
        perfil_id=linha["perfil_id"],
        rede=linha["rede"],
        link=linha["link"],
        criado_em=linha["criado_em"],
    )


def inserir(conexao: sqlite3.Connection, perfil_id: int, rede: str, link: str, agora: str) -> RedeSocial:
    cursor = conexao.execute(
        "INSERT INTO rede_social (perfil_id, rede, link, criado_em) VALUES (?, ?, ?, ?)",
        (perfil_id, rede, link, agora),
    )
    linha = conexao.execute(
        f"SELECT {_COLUNAS} FROM rede_social WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    assert linha is not None
    return _para_rede_social(linha)


def listar_por_perfil(conexao: sqlite3.Connection, perfil_id: int) -> list[RedeSocial]:
    linhas = conexao.execute(
        f"SELECT {_COLUNAS} FROM rede_social WHERE perfil_id = ? ORDER BY id",
        (perfil_id,),
    ).fetchall()
    return [_para_rede_social(linha) for linha in linhas]


def remover(conexao: sqlite3.Connection, rede_social_id: int) -> bool:
    cursor = conexao.execute("DELETE FROM rede_social WHERE id = ?", (rede_social_id,))
    return cursor.rowcount > 0
