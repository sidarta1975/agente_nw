from __future__ import annotations

import sqlite3

from agente_nw.nucleo.modelos.fila import FilaExtracao

_COLUNAS = "id, perfil_id, texto, origem, criado_em, processado, erro"


def _para_fila_extracao(linha: sqlite3.Row) -> FilaExtracao:
    return FilaExtracao(
        id=linha["id"],
        perfil_id=linha["perfil_id"],
        texto=linha["texto"],
        origem=linha["origem"],
        criado_em=linha["criado_em"],
        processado=bool(linha["processado"]),
        erro=linha["erro"],
    )


def inserir(conexao: sqlite3.Connection, perfil_id: int, texto: str, origem: str, agora: str) -> int:
    cursor = conexao.execute(
        "INSERT INTO fila_extracao (perfil_id, texto, origem, criado_em, processado) VALUES (?, ?, ?, ?, 0)",
        (perfil_id, texto, origem, agora),
    )
    assert cursor.lastrowid is not None
    return cursor.lastrowid


def listar_pendentes(conexao: sqlite3.Connection, limite: int) -> list[FilaExtracao]:
    linhas = conexao.execute(
        f"SELECT {_COLUNAS} FROM fila_extracao WHERE processado = 0 AND erro IS NULL ORDER BY id LIMIT ?",
        (limite,),
    ).fetchall()
    return [_para_fila_extracao(linha) for linha in linhas]


def marcar_processado(conexao: sqlite3.Connection, item_id: int) -> None:
    conexao.execute("UPDATE fila_extracao SET processado = 1, erro = NULL WHERE id = ?", (item_id,))


def marcar_erro(conexao: sqlite3.Connection, item_id: int, erro: str) -> None:
    conexao.execute("UPDATE fila_extracao SET erro = ? WHERE id = ?", (erro, item_id))
