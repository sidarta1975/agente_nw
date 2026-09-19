from __future__ import annotations

import sqlite3

from agente_nw.nucleo.database.queries import assunto_contato, assuntos
from agente_nw.nucleo.modelos.assunto import Assunto
from agente_nw.nucleo.vetores import cosseno


def selecionar(
    conexao: sqlite3.Connection,
    perfil_id: int,
    centroide_contato: list[float],
    substancial_minimo: float,
    conversavel_minimo: float,
    limite: int,
) -> list[Assunto]:
    ids_vistos = assunto_contato.listar_assunto_ids_ja_vistos(conexao, perfil_id)
    candidatos_com_centroide = assuntos.listar_qualificados_nao_vistos(
        conexao, substancial_minimo, conversavel_minimo, ids_vistos
    )

    ranqueados = sorted(
        candidatos_com_centroide,
        key=lambda par: cosseno(centroide_contato, par[1]),
        reverse=True,
    )
    return [assunto for assunto, _ in ranqueados[:limite]]
