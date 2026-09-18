from __future__ import annotations

import sqlite3

from agente_nw.nucleo.modelos.configuracao import NivelTema
from agente_nw.nucleo.modelos.perfil_tema import OrigemTema, PerfilTema

_COLUNAS = "perfil_id, tema_id, peso, origem, confirmado, nivel, registrado_em"


def _para_perfil_tema(linha: sqlite3.Row) -> PerfilTema:
    return PerfilTema(
        perfil_id=linha["perfil_id"],
        tema_id=linha["tema_id"],
        peso=linha["peso"],
        origem=linha["origem"],
        confirmado=bool(linha["confirmado"]),
        nivel=linha["nivel"],
        registrado_em=linha["registrado_em"],
    )


def vincular(
    conexao: sqlite3.Connection,
    perfil_id: int,
    tema_id: int,
    peso: int,
    origem: OrigemTema,
    nivel: NivelTema | None,
    confirmado: bool,
    agora: str,
) -> PerfilTema:
    conexao.execute(
        "INSERT INTO perfil_tema (perfil_id, tema_id, peso, origem, confirmado, nivel, registrado_em) "
        "VALUES (?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT (perfil_id, tema_id) DO UPDATE SET "
        "peso = excluded.peso, origem = excluded.origem, confirmado = excluded.confirmado, "
        "nivel = excluded.nivel",
        (perfil_id, tema_id, peso, origem, int(confirmado), nivel, agora),
    )
    linha = conexao.execute(
        f"SELECT {_COLUNAS} FROM perfil_tema WHERE perfil_id = ? AND tema_id = ?",
        (perfil_id, tema_id),
    ).fetchone()
    assert linha is not None
    return _para_perfil_tema(linha)


def confirmar(conexao: sqlite3.Connection, perfil_id: int, tema_id: int) -> None:
    conexao.execute(
        "UPDATE perfil_tema SET confirmado = 1 WHERE perfil_id = ? AND tema_id = ?",
        (perfil_id, tema_id),
    )


def listar_por_perfil(conexao: sqlite3.Connection, perfil_id: int) -> list[PerfilTema]:
    linhas = conexao.execute(
        f"SELECT {_COLUNAS} FROM perfil_tema WHERE perfil_id = ? ORDER BY tema_id",
        (perfil_id,),
    ).fetchall()
    return [_para_perfil_tema(linha) for linha in linhas]
