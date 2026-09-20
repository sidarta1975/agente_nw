from __future__ import annotations

import sqlite3
import struct

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


def atualizar_nivel(conexao: sqlite3.Connection, perfil_id: int, tema_id: int, nivel: NivelTema) -> None:
    conexao.execute(
        "UPDATE perfil_tema SET nivel = ? WHERE perfil_id = ? AND tema_id = ?",
        (nivel, perfil_id, tema_id),
    )


def listar_por_perfil(conexao: sqlite3.Connection, perfil_id: int) -> list[PerfilTema]:
    linhas = conexao.execute(
        f"SELECT {_COLUNAS} FROM perfil_tema WHERE perfil_id = ? ORDER BY tema_id",
        (perfil_id,),
    ).fetchall()
    return [_para_perfil_tema(linha) for linha in linhas]


def _desserializar(blob: bytes) -> list[float]:
    quantidade = len(blob) // 4
    return list(struct.unpack(f"<{quantidade}f", blob))


def listar_confirmados_com_embedding(
    conexao: sqlite3.Connection, perfil_id: int
) -> list[tuple[str, str, list[float]]]:
    linhas = conexao.execute(
        "SELECT t.nome AS nome, pt.nivel AS nivel, vt.embedding AS embedding FROM perfil_tema pt "
        "JOIN tema t ON t.id = pt.tema_id "
        "JOIN vetor_tema vt ON vt.tema_id = pt.tema_id "
        "WHERE pt.perfil_id = ? AND pt.confirmado = 1 AND pt.nivel IS NOT NULL",
        (perfil_id,),
    ).fetchall()
    return [(linha["nome"], linha["nivel"], _desserializar(linha["embedding"])) for linha in linhas]
