from __future__ import annotations

import sqlite3
from typing import Literal

StatusGancho = Literal["entregue", "usado", "nao_serve"]


def inserir_entregues(
    conexao: sqlite3.Connection, consulta_id: int, ganchos: list[tuple[int | None, str]], agora: str
) -> None:
    """Grava os ganchos entregues numa consulta. `ganchos` = [(assunto_id, gancho_json)]; assunto_id
    nulo é a mensagem base (brief 047). Repetir a gravação da mesma consulta e assunto substitui o
    texto e volta o status para `entregue`."""
    for assunto_id, gancho_json in ganchos:
        if assunto_id is None:
            atualizada = conexao.execute(
                "UPDATE gancho_uso SET status = 'entregue', gancho_json = ?, atualizado_em = ? "
                "WHERE consulta_id = ? AND assunto_id IS NULL",
                (gancho_json, agora, consulta_id),
            )
            if atualizada.rowcount == 0:
                conexao.execute(
                    "INSERT INTO gancho_uso (consulta_id, assunto_id, status, gancho_json, atualizado_em) "
                    "VALUES (?, NULL, 'entregue', ?, ?)",
                    (consulta_id, gancho_json, agora),
                )
            continue
        conexao.execute(
            "INSERT INTO gancho_uso (consulta_id, assunto_id, status, gancho_json, atualizado_em) "
            "VALUES (?, ?, 'entregue', ?, ?) "
            "ON CONFLICT(consulta_id, assunto_id) DO UPDATE SET "
            "status = 'entregue', gancho_json = excluded.gancho_json, atualizado_em = excluded.atualizado_em",
            (consulta_id, assunto_id, gancho_json, agora),
        )


def marcar(
    conexao: sqlite3.Connection, consulta_id: int, assunto_id: int | None, status: StatusGancho, agora: str
) -> bool:
    """`assunto_id` nulo marca a mensagem base da consulta."""
    cursor = conexao.execute(
        "UPDATE gancho_uso SET status = ?, atualizado_em = ? WHERE consulta_id = ? AND assunto_id IS ?",
        (status, agora, consulta_id, assunto_id),
    )
    return cursor.rowcount > 0


def comentar(
    conexao: sqlite3.Connection, consulta_id: int, assunto_id: int | None, texto: str, agora: str
) -> bool:
    """Grava o comentário livre do usuário sobre a mensagem (brief 050); texto vazio apaga o comentário.
    `assunto_id` nulo é a mensagem base."""
    cursor = conexao.execute(
        "UPDATE gancho_uso SET comentario = ?, atualizado_em = ? WHERE consulta_id = ? AND assunto_id IS ?",
        (texto.strip() or None, agora, consulta_id, assunto_id),
    )
    return cursor.rowcount > 0


def listar_por_consulta(
    conexao: sqlite3.Connection, consulta_id: int
) -> list[tuple[int | None, StatusGancho, str]]:
    """[(assunto_id, status, gancho_json)] na ordem em que foram entregues; assunto nulo é a base."""
    linhas = conexao.execute(
        "SELECT assunto_id, status, gancho_json FROM gancho_uso WHERE consulta_id = ? ORDER BY id",
        (consulta_id,),
    ).fetchall()
    return [(linha["assunto_id"], linha["status"], linha["gancho_json"]) for linha in linhas]


def comentarios_por_consulta(conexao: sqlite3.Connection, consulta_id: int) -> dict[int | None, str]:
    """{assunto_id: comentario} das mensagens da consulta que têm comentário; nulo é a base."""
    linhas = conexao.execute(
        "SELECT assunto_id, comentario FROM gancho_uso WHERE consulta_id = ? AND comentario IS NOT NULL",
        (consulta_id,),
    ).fetchall()
    return {linha["assunto_id"]: linha["comentario"] for linha in linhas}


def assuntos_usados_do_perfil(conexao: sqlite3.Connection, perfil_id: int) -> set[int]:
    """Assuntos cujo gancho o usuário marcou como usado em qualquer consulta deste contato."""
    linhas = conexao.execute(
        "SELECT DISTINCT g.assunto_id AS assunto_id FROM gancho_uso g "
        "JOIN consulta_contato c ON c.id = g.consulta_id "
        "WHERE c.perfil_id = ? AND g.status = 'usado' AND g.assunto_id IS NOT NULL",
        (perfil_id,),
    ).fetchall()
    return {linha["assunto_id"] for linha in linhas}
