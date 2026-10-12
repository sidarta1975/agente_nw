from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta

from agente_nw.nucleo.modelos.lista_rede_social import EntradaGravada, EntradaLista
from agente_nw.nucleo.texto import casa_nome, sem_acento_e_caixa

_COLUNAS = "id, rede, nome, cabecalho, link, foto_url, lido_em, perfil_id"


def _para_entrada(linha: sqlite3.Row) -> EntradaGravada:
    return EntradaGravada(
        id=linha["id"],
        rede=linha["rede"],
        nome=linha["nome"],
        cabecalho=linha["cabecalho"],
        link=linha["link"],
        foto_url=linha["foto_url"],
        lido_em=linha["lido_em"],
        perfil_id=linha["perfil_id"],
    )


def substituir_lista(conexao: sqlite3.Connection, rede: str, entradas: list[EntradaLista], agora: str) -> int:
    """Grava a leitura nova da lista de uma rede. Links já vinculados a um contato mantêm o `perfil_id`;
    entradas antigas que sumiram da lista e não estão vinculadas são removidas."""
    for entrada in entradas:
        conexao.execute(
            "INSERT INTO lista_rede_social "
            "(rede, nome, nome_normalizado, cabecalho, link, foto_url, lido_em) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT (link) DO UPDATE SET rede = excluded.rede, nome = excluded.nome, "
            "nome_normalizado = excluded.nome_normalizado, cabecalho = excluded.cabecalho, "
            "foto_url = excluded.foto_url, lido_em = excluded.lido_em",
            (
                rede,
                entrada.nome,
                sem_acento_e_caixa(entrada.nome),
                entrada.cabecalho,
                entrada.link,
                entrada.foto_url,
                agora,
            ),
        )
    conexao.execute(
        "DELETE FROM lista_rede_social WHERE rede = ? AND lido_em != ? AND perfil_id IS NULL",
        (rede, agora),
    )
    return len(entradas)


def listar_por_rede(conexao: sqlite3.Connection, rede: str) -> list[EntradaGravada]:
    linhas = conexao.execute(
        f"SELECT {_COLUNAS} FROM lista_rede_social WHERE rede = ? ORDER BY nome_normalizado, id", (rede,)
    ).fetchall()
    return [_para_entrada(linha) for linha in linhas]


def contar_por_rede(conexao: sqlite3.Connection, rede: str) -> int:
    (total,) = conexao.execute("SELECT COUNT(*) FROM lista_rede_social WHERE rede = ?", (rede,)).fetchone()
    return int(total)


def buscar_por_nome(conexao: sqlite3.Connection, rede: str | None, nome: str) -> list[EntradaGravada]:
    """Entradas cujo nome casa com `nome` (primeiro nome inteiro, sobrenome por prefixo), sem acento."""
    primeiro = sem_acento_e_caixa(nome).split()[:1]
    if not primeiro:
        return []
    padrao = primeiro[0]
    filtro_rede = "" if rede is None else " AND rede = ?"
    parametros: list[str] = [padrao, f"{padrao} %"] + ([] if rede is None else [rede])
    linhas = conexao.execute(
        f"SELECT {_COLUNAS} FROM lista_rede_social "
        f"WHERE (nome_normalizado = ? OR nome_normalizado LIKE ?){filtro_rede} "
        "ORDER BY nome_normalizado, id",
        parametros,
    ).fetchall()
    return [e for e in (_para_entrada(linha) for linha in linhas) if casa_nome(nome, e.nome)]


def filtrar_por_texto(conexao: sqlite3.Connection, rede: str, texto: str) -> list[EntradaGravada]:
    """Filtro livre da opção "mostrar a lista": o texto aparece no nome ou no cabeçalho."""
    alvo = sem_acento_e_caixa(texto)
    return [
        e
        for e in listar_por_rede(conexao, rede)
        if alvo in sem_acento_e_caixa(e.nome) or alvo in sem_acento_e_caixa(e.cabecalho)
    ]


def vincular(conexao: sqlite3.Connection, link: str, perfil_id: int) -> bool:
    cursor = conexao.execute("UPDATE lista_rede_social SET perfil_id = ? WHERE link = ?", (perfil_id, link))
    return cursor.rowcount > 0


def ultima_leitura(conexao: sqlite3.Connection, rede: str) -> str | None:
    (quando,) = conexao.execute(
        "SELECT MAX(lido_em) FROM lista_rede_social WHERE rede = ?", (rede,)
    ).fetchone()
    return str(quando) if quando is not None else None


def cache_valido(conexao: sqlite3.Connection, rede: str, validade_dias: int, agora: str) -> bool:
    quando = ultima_leitura(conexao, rede)
    if quando is None:
        return False
    return datetime.fromisoformat(agora) - datetime.fromisoformat(quando) < timedelta(days=validade_dias)
