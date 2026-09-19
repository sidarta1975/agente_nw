from __future__ import annotations

import sqlite3
import struct
from typing import NamedTuple

import sqlite_vec

from agente_nw.nucleo.modelos.item import Item

_COLUNAS = "id, fonte_id, url_canonica, titulo, texto, publicado_em, coletado_em, hash_titulo, assunto_id"


class ItemComDominio(NamedTuple):
    item: Item
    dominio: str


def _para_item(linha: sqlite3.Row) -> Item:
    return Item(
        id=linha["id"],
        fonte_id=linha["fonte_id"],
        url_canonica=linha["url_canonica"],
        titulo=linha["titulo"],
        texto=linha["texto"],
        publicado_em=linha["publicado_em"],
        coletado_em=linha["coletado_em"],
        hash_titulo=linha["hash_titulo"],
        assunto_id=linha["assunto_id"],
    )


def _desserializar(blob: bytes) -> list[float]:
    quantidade = len(blob) // 4
    return list(struct.unpack(f"<{quantidade}f", blob))


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


def listar_sem_assunto(conexao: sqlite3.Connection, limite: int) -> list[Item]:
    linhas = conexao.execute(
        f"SELECT {_COLUNAS} FROM item WHERE assunto_id IS NULL ORDER BY id LIMIT ?",
        (limite,),
    ).fetchall()
    return [_para_item(linha) for linha in linhas]


def gravar_embedding(conexao: sqlite3.Connection, item_id: int, embedding: list[float]) -> None:
    vetor = sqlite_vec.serialize_float32(embedding)
    conexao.execute("DELETE FROM vetor_item WHERE item_id = ?", (item_id,))
    conexao.execute("INSERT INTO vetor_item (item_id, embedding) VALUES (?, ?)", (item_id, vetor))


def obter_embedding(conexao: sqlite3.Connection, item_id: int) -> list[float] | None:
    linha = conexao.execute("SELECT embedding FROM vetor_item WHERE item_id = ?", (item_id,)).fetchone()
    return _desserializar(linha["embedding"]) if linha is not None else None


def vincular_assunto(conexao: sqlite3.Connection, item_id: int, assunto_id: int) -> None:
    conexao.execute("UPDATE item SET assunto_id = ? WHERE id = ?", (assunto_id, item_id))


def listar_por_assunto(conexao: sqlite3.Connection, assunto_id: int) -> list[ItemComDominio]:
    colunas_item = ", ".join(f"i.{coluna}" for coluna in _COLUNAS.split(", "))
    linhas = conexao.execute(
        f"SELECT {colunas_item}, f.dominio AS dominio FROM item i "
        "JOIN fonte f ON f.id = i.fonte_id WHERE i.assunto_id = ? ORDER BY i.id",
        (assunto_id,),
    ).fetchall()
    return [ItemComDominio(item=_para_item(linha), dominio=linha["dominio"]) for linha in linhas]


def listar_com_embedding(conexao: sqlite3.Connection) -> list[tuple[Item, list[float]]]:
    linhas = conexao.execute(
        f"SELECT {', '.join(f'i.{c}' for c in _COLUNAS.split(', '))}, v.embedding AS embedding "
        "FROM item i JOIN vetor_item v ON v.item_id = i.id ORDER BY i.id"
    ).fetchall()
    return [(_para_item(linha), _desserializar(linha["embedding"])) for linha in linhas]
