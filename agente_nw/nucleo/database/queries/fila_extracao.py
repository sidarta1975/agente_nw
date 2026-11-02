from __future__ import annotations

import sqlite3

from agente_nw.nucleo.modelos.fila import FilaExtracao
from agente_nw.nucleo.modelos.proveniencia import Proveniencia, colunas_gerado_por

_COLUNAS = "id, perfil_id, texto, origem, criado_em, processado, erro"


def _para_fila_extracao(linha: sqlite3.Row) -> FilaExtracao:
    return FilaExtracao(
        id=linha["id"],
        perfil_id=linha["perfil_id"],
        texto=linha["texto"],
        origem=linha["origem"],
        criado_em=linha["criado_em"],
        processado=bool(linha["processado"]),
        erro=linha["erro"],
    )


def inserir(conexao: sqlite3.Connection, perfil_id: int, texto: str, origem: str, agora: str) -> int:
    cursor = conexao.execute(
        "INSERT INTO fila_extracao (perfil_id, texto, origem, criado_em, processado) VALUES (?, ?, ?, ?, 0)",
        (perfil_id, texto, origem, agora),
    )
    assert cursor.lastrowid is not None
    return cursor.lastrowid


def listar_pendentes(conexao: sqlite3.Connection, limite: int) -> list[FilaExtracao]:
    linhas = conexao.execute(
        f"SELECT {_COLUNAS} FROM fila_extracao WHERE processado = 0 AND erro IS NULL ORDER BY id LIMIT ?",
        (limite,),
    ).fetchall()
    return [_para_fila_extracao(linha) for linha in linhas]


def marcar_processado(
    conexao: sqlite3.Connection, item_id: int, proveniencia: Proveniencia | None = None
) -> None:
    """`proveniencia`: perfil, modelo e versão do prompt que extraíram o item (brief 066)."""
    conexao.execute(
        "UPDATE fila_extracao SET processado = 1, erro = NULL, "
        "gerado_por_modelo = ?, gerado_por_perfil = ?, gerado_por_prompt_versao = ? WHERE id = ?",
        (*colunas_gerado_por(proveniencia), item_id),
    )


def marcar_erro(conexao: sqlite3.Connection, item_id: int, erro: str) -> None:
    conexao.execute("UPDATE fila_extracao SET erro = ? WHERE id = ?", (erro, item_id))


def contar_whatsapp(conexao: sqlite3.Connection, perfil_id: int) -> tuple[int, int]:
    """(pendentes, total) dos blocos de conversa do WhatsApp (origem `whatsapp:*`) deste contato —
    "processando conversa… (x de y blocos)" na página da pessoa (brief 061)."""
    (pendentes,) = conexao.execute(
        "SELECT COUNT(*) FROM fila_extracao WHERE perfil_id = ? AND origem LIKE 'whatsapp:%' "
        "AND processado = 0 AND erro IS NULL",
        (perfil_id,),
    ).fetchone()
    (total,) = conexao.execute(
        "SELECT COUNT(*) FROM fila_extracao WHERE perfil_id = ? AND origem LIKE 'whatsapp:%'", (perfil_id,)
    ).fetchone()
    return int(pendentes), int(total)
