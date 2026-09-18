from __future__ import annotations

import sqlite3

from agente_nw.nucleo.modelos.fonte import Fonte

_COLUNAS = "id, nome, url_feed, dominio, tipo, confiabilidade, ativa"


def _para_fonte(linha: sqlite3.Row) -> Fonte:
    return Fonte(
        id=linha["id"],
        nome=linha["nome"],
        url_feed=linha["url_feed"],
        dominio=linha["dominio"],
        tipo=linha["tipo"],
        confiabilidade=linha["confiabilidade"],
        ativa=bool(linha["ativa"]),
    )


def obter_por_url(conexao: sqlite3.Connection, url_feed: str) -> Fonte | None:
    linha = conexao.execute(f"SELECT {_COLUNAS} FROM fonte WHERE url_feed = ?", (url_feed,)).fetchone()
    return _para_fonte(linha) if linha is not None else None


def obter_ou_criar(
    conexao: sqlite3.Connection,
    nome: str,
    url_feed: str,
    dominio: str,
    tipo: str,
    confiabilidade: int,
) -> Fonte:
    existente = obter_por_url(conexao, url_feed)
    if existente is not None:
        return existente

    cursor = conexao.execute(
        "INSERT INTO fonte (nome, url_feed, dominio, tipo, confiabilidade, ativa) VALUES (?, ?, ?, ?, ?, 1)",
        (nome, url_feed, dominio, tipo, confiabilidade),
    )
    return Fonte(
        id=cursor.lastrowid,
        nome=nome,
        url_feed=url_feed,
        dominio=dominio,
        tipo=tipo,
        confiabilidade=confiabilidade,
        ativa=True,
    )


def listar_ativas(conexao: sqlite3.Connection) -> list[Fonte]:
    linhas = conexao.execute(f"SELECT {_COLUNAS} FROM fonte WHERE ativa = 1 ORDER BY nome").fetchall()
    return [_para_fonte(linha) for linha in linhas]


def registrar_execucao(conexao: sqlite3.Connection, fonte_id: int, data: str, n_itens_novos: int) -> None:
    conexao.execute(
        "INSERT INTO fonte_execucao (fonte_id, data, n_itens_novos) VALUES (?, ?, ?) "
        "ON CONFLICT (fonte_id, data) DO UPDATE SET n_itens_novos = excluded.n_itens_novos",
        (fonte_id, data, n_itens_novos),
    )


def dois_dias_vazios(conexao: sqlite3.Connection, fonte_id: int, data_referencia: str) -> bool:
    linhas = conexao.execute(
        "SELECT n_itens_novos FROM fonte_execucao WHERE fonte_id = ? AND data <= ? "
        "ORDER BY data DESC LIMIT 2",
        (fonte_id, data_referencia),
    ).fetchall()
    if len(linhas) < 2:
        return False
    return all(linha["n_itens_novos"] == 0 for linha in linhas)
