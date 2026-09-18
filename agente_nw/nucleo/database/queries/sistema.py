from __future__ import annotations

import sqlite3


def versao_esquema(conexao: sqlite3.Connection) -> int:
    linha = conexao.execute("SELECT MAX(versao) AS versao FROM schema_version").fetchone()
    versao = linha["versao"] if linha is not None else None
    return int(versao) if versao is not None else 0


def vec_version(conexao: sqlite3.Connection) -> str:
    (versao,) = conexao.execute("SELECT vec_version()").fetchone()
    return str(versao)


def progresso_obter(conexao: sqlite3.Connection, etapa: str) -> sqlite3.Row | None:
    linha: sqlite3.Row | None = conexao.execute(
        "SELECT etapa, ultimo_id, data_ciclo, atualizado_em FROM progresso WHERE etapa = ?",
        (etapa,),
    ).fetchone()
    return linha


def progresso_gravar(
    conexao: sqlite3.Connection,
    etapa: str,
    ultimo_id: int | None,
    data_ciclo: str | None,
    agora: str,
) -> None:
    conexao.execute(
        "INSERT INTO progresso (etapa, ultimo_id, data_ciclo, atualizado_em) VALUES (?, ?, ?, ?) "
        "ON CONFLICT (etapa) DO UPDATE SET "
        "ultimo_id = excluded.ultimo_id, data_ciclo = excluded.data_ciclo, "
        "atualizado_em = excluded.atualizado_em",
        (etapa, ultimo_id, data_ciclo, agora),
    )
