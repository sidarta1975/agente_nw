from __future__ import annotations

import json
import sqlite3

import sqlite_vec

from agente_nw.nucleo.modelos.tema import Tema

_COLUNAS = "id, nome, descricao, sinonimos, criado_em"


def _para_tema(linha: sqlite3.Row) -> Tema:
    return Tema(
        id=linha["id"],
        nome=linha["nome"],
        descricao=linha["descricao"],
        sinonimos=json.loads(linha["sinonimos"]),
        criado_em=linha["criado_em"],
    )


def obter_por_nome(conexao: sqlite3.Connection, nome: str) -> Tema | None:
    linha = conexao.execute(f"SELECT {_COLUNAS} FROM tema WHERE nome = ?", (nome,)).fetchone()
    return _para_tema(linha) if linha is not None else None


def obter_ou_criar(
    conexao: sqlite3.Connection,
    nome: str,
    descricao: str,
    sinonimos: list[str],
    agora: str,
) -> Tema:
    sinonimos_json = json.dumps(sinonimos, ensure_ascii=False)
    existente = obter_por_nome(conexao, nome)

    if existente is None:
        cursor = conexao.execute(
            "INSERT INTO tema (nome, descricao, sinonimos, criado_em) VALUES (?, ?, ?, ?)",
            (nome, descricao, sinonimos_json, agora),
        )
        return Tema(id=cursor.lastrowid, nome=nome, descricao=descricao, sinonimos=sinonimos, criado_em=agora)

    conexao.execute(
        "UPDATE tema SET descricao = ?, sinonimos = ? WHERE id = ?",
        (descricao, sinonimos_json, existente.id),
    )
    return Tema(
        id=existente.id,
        nome=nome,
        descricao=descricao,
        sinonimos=sinonimos,
        criado_em=existente.criado_em,
    )


def listar(conexao: sqlite3.Connection) -> list[Tema]:
    linhas = conexao.execute(f"SELECT {_COLUNAS} FROM tema ORDER BY nome").fetchall()
    return [_para_tema(linha) for linha in linhas]


def gravar_embedding(conexao: sqlite3.Connection, tema_id: int, embedding: list[float]) -> None:
    vetor = sqlite_vec.serialize_float32(embedding)
    conexao.execute("DELETE FROM vetor_tema WHERE tema_id = ?", (tema_id,))
    conexao.execute("INSERT INTO vetor_tema (tema_id, embedding) VALUES (?, ?)", (tema_id, vetor))
