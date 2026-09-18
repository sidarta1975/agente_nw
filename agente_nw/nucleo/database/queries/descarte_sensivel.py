from __future__ import annotations

import sqlite3

from agente_nw.nucleo.modelos.descarte import DescarteSensivel


def registrar(
    conexao: sqlite3.Connection,
    perfil_id: int | None,
    origem_texto: str,
    categoria: str,
    agora: str,
) -> int:
    """Registra um descarte por categoria sensível.

    ``origem_texto`` é a origem do texto processado (mesmo vocabulário de
    ``fila_extracao.origem`` — ex.: "cadastro", "notas_agenda"), nunca o
    conteúdo do texto em si. Junto com ``categoria``, é só o que esta tabela
    grava: nunca o trecho, nunca o termo que disparou o filtro (comentário na
    migração 001, coluna `categoria`) — nem esta função nem quem a chama têm
    como reintroduzir dado sensível aqui.
    """
    registro = DescarteSensivel(
        perfil_id=perfil_id, origem_texto=origem_texto, categoria=categoria, registrado_em=agora
    )
    cursor = conexao.execute(
        "INSERT INTO descarte_sensivel (perfil_id, origem_texto, categoria, registrado_em) "
        "VALUES (?, ?, ?, ?)",
        (registro.perfil_id, registro.origem_texto, registro.categoria, registro.registrado_em),
    )
    assert cursor.lastrowid is not None
    return cursor.lastrowid
