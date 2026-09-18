from __future__ import annotations

import sqlite3

from agente_nw.nucleo.modelos.fila import FilaRevisao


def inserir(conexao: sqlite3.Connection, tarefa: str, entrada: str, erro: str, agora: str) -> int:
    registro = FilaRevisao(tarefa=tarefa, entrada=entrada, erro=erro, criado_em=agora, resolvido=False)
    cursor = conexao.execute(
        "INSERT INTO fila_revisao (tarefa, entrada, erro, criado_em, resolvido) VALUES (?, ?, ?, ?, ?)",
        (registro.tarefa, registro.entrada, registro.erro, registro.criado_em, int(registro.resolvido)),
    )
    assert cursor.lastrowid is not None
    return cursor.lastrowid
