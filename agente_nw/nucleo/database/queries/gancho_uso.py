from __future__ import annotations

import sqlite3
from typing import Literal

StatusGancho = Literal["entregue", "usado", "nao_serve"]


def inserir_entregues(
    conexao: sqlite3.Connection, consulta_id: int, ganchos: list[tuple[int, str]], agora: str
) -> None:
    """Grava os ganchos entregues numa consulta. `ganchos` = [(assunto_id, gancho_json)]. Repetir a
    gravação da mesma consulta e assunto substitui o texto e volta o status para `entregue`."""
    for assunto_id, gancho_json in ganchos:
        conexao.execute(
            "INSERT INTO gancho_uso (consulta_id, assunto_id, status, gancho_json, atualizado_em) "
            "VALUES (?, ?, 'entregue', ?, ?) "
            "ON CONFLICT(consulta_id, assunto_id) DO UPDATE SET "
            "status = 'entregue', gancho_json = excluded.gancho_json, atualizado_em = excluded.atualizado_em",
            (consulta_id, assunto_id, gancho_json, agora),
        )


def marcar(
    conexao: sqlite3.Connection, consulta_id: int, assunto_id: int, status: StatusGancho, agora: str
) -> bool:
    cursor = conexao.execute(
        "UPDATE gancho_uso SET status = ?, atualizado_em = ? WHERE consulta_id = ? AND assunto_id = ?",
        (status, agora, consulta_id, assunto_id),
    )
    return cursor.rowcount > 0


def listar_por_consulta(conexao: sqlite3.Connection, consulta_id: int) -> list[tuple[int, StatusGancho, str]]:
    """[(assunto_id, status, gancho_json)] na ordem em que foram entregues."""
    linhas = conexao.execute(
        "SELECT assunto_id, status, gancho_json FROM gancho_uso WHERE consulta_id = ? ORDER BY id",
        (consulta_id,),
    ).fetchall()
    return [(linha["assunto_id"], linha["status"], linha["gancho_json"]) for linha in linhas]


def assuntos_usados_do_perfil(conexao: sqlite3.Connection, perfil_id: int) -> set[int]:
    """Assuntos cujo gancho o usuário marcou como usado em qualquer consulta deste contato."""
    linhas = conexao.execute(
        "SELECT DISTINCT g.assunto_id AS assunto_id FROM gancho_uso g "
        "JOIN consulta_contato c ON c.id = g.consulta_id "
        "WHERE c.perfil_id = ? AND g.status = 'usado'",
        (perfil_id,),
    ).fetchall()
    return {linha["assunto_id"] for linha in linhas}
