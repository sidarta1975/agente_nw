from __future__ import annotations

import sqlite3
import struct

from agente_nw.nucleo.modelos.configuracao import NivelTema
from agente_nw.nucleo.modelos.perfil_tema import OrigemTema, PerfilTema

_COLUNAS = "perfil_id, tema_id, peso, origem, confirmado, nivel, registrado_em, peso_decaido_em"


def _para_perfil_tema(linha: sqlite3.Row) -> PerfilTema:
    return PerfilTema(
        perfil_id=linha["perfil_id"],
        tema_id=linha["tema_id"],
        peso=linha["peso"],
        origem=linha["origem"],
        confirmado=bool(linha["confirmado"]),
        nivel=linha["nivel"],
        registrado_em=linha["registrado_em"],
        peso_decaido_em=linha["peso_decaido_em"],
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


def desvincular(conexao: sqlite3.Connection, perfil_id: int, tema_id: int) -> bool:
    cursor = conexao.execute(
        "DELETE FROM perfil_tema WHERE perfil_id = ? AND tema_id = ?", (perfil_id, tema_id)
    )
    return cursor.rowcount > 0


def listar_por_perfil(conexao: sqlite3.Connection, perfil_id: int) -> list[PerfilTema]:
    linhas = conexao.execute(
        f"SELECT {_COLUNAS} FROM perfil_tema WHERE perfil_id = ? ORDER BY tema_id",
        (perfil_id,),
    ).fetchall()
    return [_para_perfil_tema(linha) for linha in linhas]


def listar_nomes_do_contato(conexao: sqlite3.Connection, perfil_id: int) -> list[str]:
    """Nomes das tags do contato (contextos como família, amigos, trabalho), das mais pesadas."""
    linhas = conexao.execute(
        "SELECT t.nome AS nome FROM perfil_tema pt JOIN tema t ON t.id = pt.tema_id "
        "WHERE pt.perfil_id = ? ORDER BY pt.peso DESC, t.nome",
        (perfil_id,),
    ).fetchall()
    return [linha["nome"] for linha in linhas]


def _desserializar(blob: bytes) -> list[float]:
    quantidade = len(blob) // 4
    return list(struct.unpack(f"<{quantidade}f", blob))


def listar_confirmados_com_embedding(
    conexao: sqlite3.Connection, perfil_id: int, modelo_embedding: str
) -> list[tuple[str, str, list[float]]]:
    """Só os temas com vetor do `modelo_embedding` atual (brief 066)."""
    linhas = conexao.execute(
        "SELECT t.nome AS nome, pt.nivel AS nivel, vt.embedding AS embedding FROM perfil_tema pt "
        "JOIN tema t ON t.id = pt.tema_id "
        "JOIN vetor_tema vt ON vt.tema_id = pt.tema_id "
        "WHERE pt.perfil_id = ? AND pt.confirmado = 1 AND pt.nivel IS NOT NULL AND vt.modelo_embedding = ?",
        (perfil_id, modelo_embedding),
    ).fetchall()
    return [(linha["nome"], linha["nivel"], _desserializar(linha["embedding"])) for linha in linhas]


def registrar_uso(conexao: sqlite3.Connection, perfil_id: int, tema_id: int, agora: str) -> None:
    """Uma linha por reforço do tema (brief 040): base para o nível por frequência e a última menção."""
    conexao.execute(
        "INSERT INTO tema_uso (perfil_id, tema_id, usado_em) VALUES (?, ?, ?)", (perfil_id, tema_id, agora)
    )


def contar_usos_desde(conexao: sqlite3.Connection, perfil_id: int, tema_id: int, desde: str) -> int:
    (quantidade,) = conexao.execute(
        "SELECT COUNT(*) FROM tema_uso WHERE perfil_id = ? AND tema_id = ? AND usado_em >= ?",
        (perfil_id, tema_id, desde),
    ).fetchone()
    return int(quantidade)


def ultima_mencao(conexao: sqlite3.Connection, perfil_id: int, tema_id: int) -> str | None:
    linha = conexao.execute(
        "SELECT MAX(usado_em) AS ultima FROM tema_uso WHERE perfil_id = ? AND tema_id = ?",
        (perfil_id, tema_id),
    ).fetchone()
    return linha["ultima"] if linha is not None else None


def atualizar_peso_por_decaimento(
    conexao: sqlite3.Connection, perfil_id: int, tema_id: int, peso: int, mes: str
) -> None:
    """Decaimento por inatividade (brief 040): não toca `origem`/`nivel`, só `peso` e a marca do mês
    em que decaiu, para não decair duas vezes no mesmo mês."""
    conexao.execute(
        "UPDATE perfil_tema SET peso = ?, peso_decaido_em = ? WHERE perfil_id = ? AND tema_id = ?",
        (peso, mes, perfil_id, tema_id),
    )


def remover_por_origem(conexao: sqlite3.Connection, perfil_id: int, origem: OrigemTema) -> int:
    """'Esquecer tudo o que você inferiu sobre mim' (brief 040): zera só uma origem; `declarada`
    sobrevive quando chamado com `origem='conversa'`."""
    cursor = conexao.execute(
        "DELETE FROM perfil_tema WHERE perfil_id = ? AND origem = ?", (perfil_id, origem)
    )
    return cursor.rowcount


def listar_do_contato_com_embedding(
    conexao: sqlite3.Connection, perfil_id: int, modelo_embedding: str
) -> list[tuple[str, list[float], bool]]:
    """Tags do contato com embedding do `modelo_embedding` atual (brief 066): as confirmadas, ou, na
    ausência delas, as sugeridas.

    Devolve (nome, embedding, confirmado), das mais pesadas para as mais leves."""
    linhas = conexao.execute(
        "SELECT t.nome AS nome, pt.confirmado AS confirmado, vt.embedding AS embedding FROM perfil_tema pt "
        "JOIN tema t ON t.id = pt.tema_id "
        "JOIN vetor_tema vt ON vt.tema_id = pt.tema_id "
        "WHERE pt.perfil_id = ? AND vt.modelo_embedding = ? ORDER BY pt.peso DESC, t.nome",
        (perfil_id, modelo_embedding),
    ).fetchall()
    confirmadas = [linha for linha in linhas if linha["confirmado"] == 1]
    escolhidas = confirmadas if confirmadas else list(linhas)
    return [
        (linha["nome"], _desserializar(linha["embedding"]), linha["confirmado"] == 1) for linha in escolhidas
    ]
