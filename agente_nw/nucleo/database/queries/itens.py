from __future__ import annotations

import sqlite3

from agente_nw.nucleo.modelos.item import Item


def existe(conexao: sqlite3.Connection, url_canonica: str, hash_titulo: str) -> bool:
    linha = conexao.execute(
        "SELECT 1 FROM item WHERE url_canonica = ? OR hash_titulo = ? LIMIT 1",
        (url_canonica, hash_titulo),
    ).fetchone()
    return linha is not None


def inserir(conexao: sqlite3.Connection, item: Item) -> int:
    cursor = conexao.execute(
        "INSERT INTO item "
        "(fonte_id, url_canonica, titulo, texto, publicado_em, coletado_em, hash_titulo, assunto_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            item.fonte_id,
            item.url_canonica,
            item.titulo,
            item.texto,
            item.publicado_em,
            item.coletado_em,
            item.hash_titulo,
            item.assunto_id,
        ),
    )
    assert cursor.lastrowid is not None
    return cursor.lastrowid
