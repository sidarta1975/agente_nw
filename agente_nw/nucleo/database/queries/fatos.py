from __future__ import annotations

import sqlite3

from agente_nw.nucleo.modelos.fato import Fato
from agente_nw.nucleo.modelos.proveniencia import Proveniencia, colunas_gerado_por


def inserir(conexao: sqlite3.Connection, fato: Fato, proveniencia: Proveniencia | None = None) -> int:
    """Insere um fato. Só inserção — os gatilhos `fato_sem_update`/`fato_sem_delete`
    já bloqueiam o resto no banco; este módulo nem oferece outra função. `proveniencia`: quem extraiu
    o fato (brief 066), gravada no próprio INSERT."""
    cursor = conexao.execute(
        "INSERT INTO fato (perfil_id, data_do_fato, tipo, conteudo, fonte, registrado_em, "
        "gerado_por_modelo, gerado_por_perfil, gerado_por_prompt_versao) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            fato.perfil_id,
            fato.data_do_fato,
            fato.tipo,
            fato.conteudo,
            fato.fonte,
            fato.registrado_em,
            *colunas_gerado_por(proveniencia),
        ),
    )
    assert cursor.lastrowid is not None
    return cursor.lastrowid


def listar_recentes(conexao: sqlite3.Connection, perfil_id: int, limite: int) -> list[Fato]:
    linhas = conexao.execute(
        "SELECT id, perfil_id, data_do_fato, tipo, conteudo, fonte, registrado_em FROM fato "
        "WHERE perfil_id = ? ORDER BY COALESCE(data_do_fato, registrado_em) DESC, id DESC LIMIT ?",
        (perfil_id, limite),
    ).fetchall()
    return [
        Fato(
            id=linha["id"],
            perfil_id=linha["perfil_id"],
            data_do_fato=linha["data_do_fato"],
            tipo=linha["tipo"],
            conteudo=linha["conteudo"],
            fonte=linha["fonte"],
            registrado_em=linha["registrado_em"],
        )
        for linha in linhas
    ]


def existe(conexao: sqlite3.Connection, perfil_id: int, tipo: str, fonte: str) -> bool:
    """Já há fato deste tipo e desta fonte (por exemplo, a mesma publicação já descrita)?"""
    linha = conexao.execute(
        "SELECT 1 FROM fato WHERE perfil_id = ? AND tipo = ? AND fonte = ? LIMIT 1", (perfil_id, tipo, fonte)
    ).fetchone()
    return linha is not None
