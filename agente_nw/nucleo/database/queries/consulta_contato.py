from __future__ import annotations

import sqlite3

from agente_nw.nucleo.modelos.consulta_contato import ConsultaContato

_COLUNAS = "id, perfil_id, criado_em, contexto_json, resumo_redes_sociais, assuntos_entregues_json"


def _para_consulta(linha: sqlite3.Row) -> ConsultaContato:
    return ConsultaContato(
        id=linha["id"],
        perfil_id=linha["perfil_id"],
        criado_em=linha["criado_em"],
        contexto_json=linha["contexto_json"],
        resumo_redes_sociais=linha["resumo_redes_sociais"],
        assuntos_entregues_json=linha["assuntos_entregues_json"],
    )


def inserir(
    conexao: sqlite3.Connection,
    perfil_id: int,
    criado_em: str,
    contexto_json: str,
    resumo_redes_sociais: str | None,
    assuntos_entregues_json: str,
) -> ConsultaContato:
    cursor = conexao.execute(
        "INSERT INTO consulta_contato "
        "(perfil_id, criado_em, contexto_json, resumo_redes_sociais, assuntos_entregues_json) "
        "VALUES (?, ?, ?, ?, ?)",
        (perfil_id, criado_em, contexto_json, resumo_redes_sociais, assuntos_entregues_json),
    )
    linha = conexao.execute(
        f"SELECT {_COLUNAS} FROM consulta_contato WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    assert linha is not None
    return _para_consulta(linha)


def listar_por_perfil(
    conexao: sqlite3.Connection, perfil_id: int, limite: int | None = None
) -> list[ConsultaContato]:
    if limite is None:
        linhas = conexao.execute(
            f"SELECT {_COLUNAS} FROM consulta_contato WHERE perfil_id = ? ORDER BY criado_em DESC, id DESC",
            (perfil_id,),
        ).fetchall()
    else:
        linhas = conexao.execute(
            f"SELECT {_COLUNAS} FROM consulta_contato WHERE perfil_id = ? "
            "ORDER BY criado_em DESC, id DESC LIMIT ?",
            (perfil_id, limite),
        ).fetchall()
    return [_para_consulta(linha) for linha in linhas]
