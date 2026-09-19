from __future__ import annotations

import sqlite3

from agente_nw.nucleo.modelos.assunto_contato import AssuntoContato

_COLUNAS = (
    "id, assunto_id, perfil_id, gerado_em, tipo, aderencia_contato, aderencia_usuario, "
    "conversavel, score, por_que, status, motivo"
)


def _para_assunto_contato(linha: sqlite3.Row) -> AssuntoContato:
    return AssuntoContato(
        id=linha["id"],
        assunto_id=linha["assunto_id"],
        perfil_id=linha["perfil_id"],
        gerado_em=linha["gerado_em"],
        tipo=linha["tipo"],
        aderencia_contato=linha["aderencia_contato"],
        aderencia_usuario=linha["aderencia_usuario"],
        conversavel=linha["conversavel"],
        score=linha["score"],
        por_que=linha["por_que"],
        status=linha["status"],
        motivo=linha["motivo"],
    )


def inserir(conexao: sqlite3.Connection, assunto_contato: AssuntoContato) -> bool:
    cursor = conexao.execute(
        "INSERT INTO assunto_contato "
        "(assunto_id, perfil_id, gerado_em, tipo, aderencia_contato, aderencia_usuario, "
        "conversavel, score, por_que, status, motivo) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT (assunto_id, perfil_id, gerado_em) DO NOTHING",
        (
            assunto_contato.assunto_id,
            assunto_contato.perfil_id,
            assunto_contato.gerado_em,
            assunto_contato.tipo,
            assunto_contato.aderencia_contato,
            assunto_contato.aderencia_usuario,
            assunto_contato.conversavel,
            assunto_contato.score,
            assunto_contato.por_que,
            assunto_contato.status,
            assunto_contato.motivo,
        ),
    )
    return cursor.rowcount > 0


def listar_do_dia(conexao: sqlite3.Connection, perfil_id: int, data: str) -> list[AssuntoContato]:
    linhas = conexao.execute(
        f"SELECT {_COLUNAS} FROM assunto_contato WHERE perfil_id = ? AND gerado_em = ? ORDER BY score DESC",
        (perfil_id, data),
    ).fetchall()
    return [_para_assunto_contato(linha) for linha in linhas]


def listar_assunto_ids_ja_vistos(conexao: sqlite3.Connection, perfil_id: int) -> set[int]:
    linhas = conexao.execute(
        "SELECT DISTINCT assunto_id FROM assunto_contato WHERE perfil_id = ?", (perfil_id,)
    ).fetchall()
    return {linha["assunto_id"] for linha in linhas}


def marcar_usado(conexao: sqlite3.Connection, ac_id: int) -> bool:
    cursor = conexao.execute(
        "UPDATE assunto_contato SET status = 'usado' WHERE id = ? AND status = 'novo'", (ac_id,)
    )
    return cursor.rowcount > 0


def marcar_nao_serve(conexao: sqlite3.Connection, ac_id: int, motivo: str) -> bool:
    cursor = conexao.execute(
        "UPDATE assunto_contato SET status = 'nao_serve', motivo = ? WHERE id = ? AND status = 'novo'",
        (motivo, ac_id),
    )
    return cursor.rowcount > 0


def contar_por_status(conexao: sqlite3.Connection, data: str) -> dict[str, int]:
    linhas = conexao.execute(
        "SELECT status, COUNT(*) AS quantidade FROM assunto_contato WHERE gerado_em = ? GROUP BY status",
        (data,),
    ).fetchall()
    return {linha["status"]: linha["quantidade"] for linha in linhas}


def contar_por_perfil_e_tipo(conexao: sqlite3.Connection, data: str) -> list[tuple[int, str, int]]:
    linhas = conexao.execute(
        "SELECT perfil_id, tipo, COUNT(*) AS quantidade FROM assunto_contato "
        "WHERE gerado_em = ? GROUP BY perfil_id, tipo",
        (data,),
    ).fetchall()
    return [(linha["perfil_id"], linha["tipo"], linha["quantidade"]) for linha in linhas]


def contar_orfaos(conexao: sqlite3.Connection) -> int:
    (contagem,) = conexao.execute(
        "SELECT COUNT(*) FROM assunto_contato ac LEFT JOIN assunto a ON a.id = ac.assunto_id "
        "WHERE a.id IS NULL"
    ).fetchone()
    return int(contagem)
