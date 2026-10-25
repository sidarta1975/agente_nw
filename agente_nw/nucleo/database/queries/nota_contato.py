from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class NotaContato:
    id: int
    perfil_id: int
    pedido_id: int | None
    texto: str
    criado_em: str


def inserir(
    conexao: sqlite3.Connection, perfil_id: int, texto: str, agora: str, pedido_id: int | None = None
) -> int:
    """Grava uma nota do usuário sobre o contato (`pedido_id` nulo) ou sobre um pedido dele."""
    cursor = conexao.execute(
        "INSERT INTO nota_contato (perfil_id, pedido_id, texto, criado_em) VALUES (?, ?, ?, ?)",
        (perfil_id, pedido_id, texto.strip(), agora),
    )
    assert cursor.lastrowid is not None
    return cursor.lastrowid


def _para_nota(linha: sqlite3.Row) -> NotaContato:
    return NotaContato(
        id=linha["id"],
        perfil_id=linha["perfil_id"],
        pedido_id=linha["pedido_id"],
        texto=linha["texto"],
        criado_em=linha["criado_em"],
    )


def listar_por_perfil(
    conexao: sqlite3.Connection, perfil_id: int, limite: int | None = None
) -> list[NotaContato]:
    """Mais recentes primeiro."""
    consulta = (
        "SELECT id, perfil_id, pedido_id, texto, criado_em FROM nota_contato "
        "WHERE perfil_id = ? ORDER BY criado_em DESC, id DESC"
    )
    if limite is None:
        linhas = conexao.execute(consulta, (perfil_id,)).fetchall()
    else:
        linhas = conexao.execute(consulta + " LIMIT ?", (perfil_id, limite)).fetchall()
    return [_para_nota(linha) for linha in linhas]


def listar_por_pedido(conexao: sqlite3.Connection, pedido_id: int) -> list[NotaContato]:
    linhas = conexao.execute(
        "SELECT id, perfil_id, pedido_id, texto, criado_em FROM nota_contato "
        "WHERE pedido_id = ? ORDER BY criado_em DESC, id DESC",
        (pedido_id,),
    ).fetchall()
    return [_para_nota(linha) for linha in linhas]
