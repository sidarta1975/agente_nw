from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class PedidoGravado:
    id: int
    perfil_id: int | None
    texto: str
    extraido_json: str | None
    confianca: float | None
    contato_criado: bool
    contato_ambiguo: bool
    criado_em: str


_COLUNAS = "id, perfil_id, texto, extraido_json, confianca, contato_criado, contato_ambiguo, criado_em"


def _para_pedido(linha: sqlite3.Row) -> PedidoGravado:
    return PedidoGravado(
        id=linha["id"],
        perfil_id=linha["perfil_id"],
        texto=linha["texto"],
        extraido_json=linha["extraido_json"],
        confianca=linha["confianca"],
        contato_criado=bool(linha["contato_criado"]),
        contato_ambiguo=bool(linha["contato_ambiguo"]),
        criado_em=linha["criado_em"],
    )


def inserir(conexao: sqlite3.Connection, texto: str, agora: str) -> int:
    cursor = conexao.execute("INSERT INTO pedido (texto, criado_em) VALUES (?, ?)", (texto, agora))
    assert cursor.lastrowid is not None
    return cursor.lastrowid


def gravar_extracao(
    conexao: sqlite3.Connection, pedido_id: int, extraido_json: str, confianca: float
) -> None:
    conexao.execute(
        "UPDATE pedido SET extraido_json = ?, confianca = ? WHERE id = ?",
        (extraido_json, confianca, pedido_id),
    )


def gravar_resolucao(
    conexao: sqlite3.Connection,
    pedido_id: int,
    perfil_id: int | None,
    contato_criado: bool,
    contato_ambiguo: bool,
) -> None:
    conexao.execute(
        "UPDATE pedido SET perfil_id = ?, contato_criado = ?, contato_ambiguo = ? WHERE id = ?",
        (perfil_id, int(contato_criado), int(contato_ambiguo), pedido_id),
    )


def obter_por_id(conexao: sqlite3.Connection, pedido_id: int) -> PedidoGravado | None:
    linha = conexao.execute(f"SELECT {_COLUNAS} FROM pedido WHERE id = ?", (pedido_id,)).fetchone()
    return _para_pedido(linha) if linha is not None else None


def listar_recentes(conexao: sqlite3.Connection, limite: int) -> list[PedidoGravado]:
    linhas = conexao.execute(
        f"SELECT {_COLUNAS} FROM pedido ORDER BY criado_em DESC, id DESC LIMIT ?", (limite,)
    ).fetchall()
    return [_para_pedido(linha) for linha in linhas]
