from __future__ import annotations

import sqlite3
import unicodedata

from agente_nw.nucleo.database.queries import assunto_contato, assuntos
from agente_nw.nucleo.modelos.assunto import Assunto
from agente_nw.nucleo.modelos.configuracao import ConsultaLimiares
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


def _sem_acento_e_caixa(texto: str) -> str:
    decomposto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in decomposto if not unicodedata.combining(c)).casefold()


def termo_evitado(assunto: Assunto, evitar: list[str]) -> bool:
    """Correspondência literal, sem acento e sem caixa, no título e no resumo do assunto."""
    texto = _sem_acento_e_caixa(f"{assunto.titulo_gerado or ''} {assunto.resumo_cartao or ''}")
    return any(
        termo_normalizado in texto
        for termo_normalizado in (_sem_acento_e_caixa(t.strip()) for t in evitar)
        if termo_normalizado
    )


def selecionar_por_consulta(
    conexao: sqlite3.Connection,
    perfil_id: int,
    centroide_consulta: list[float],
    centroide_contato: list[float] | None,
    substancial_minimo: float,
    conversavel_minimo: float,
    limite: int,
    evitar: list[str],
    limiares_consulta: ConsultaLimiares,
) -> tuple[list[Assunto], list[Assunto]]:
    """Devolve (selecionados, evitados).

    Os evitados saem antes do corte em `limite`, para não ocupar vaga. A ordenação é pelo cosseno
    à consulta; com centroide do contato, pesos `selecao_peso_*` de `limiares.conector.consulta`."""
    ids_vistos = assunto_contato.listar_assunto_ids_ja_vistos(conexao, perfil_id)
    candidatos_com_centroide = assuntos.listar_qualificados_nao_vistos(
        conexao, substancial_minimo, conversavel_minimo, ids_vistos
    )

    evitados = [assunto for assunto, _ in candidatos_com_centroide if termo_evitado(assunto, evitar)]
    ids_evitados = {assunto.id for assunto in evitados}
    restantes = [par for par in candidatos_com_centroide if par[0].id not in ids_evitados]

    def chave(par: tuple[Assunto, list[float]]) -> float:
        cos_consulta = cosseno(centroide_consulta, par[1])
        if centroide_contato is None:
            return cos_consulta
        return limiares_consulta.selecao_peso_consulta * cos_consulta + (
            limiares_consulta.selecao_peso_contato * cosseno(centroide_contato, par[1])
        )

    ranqueados = sorted(restantes, key=chave, reverse=True)
    return [assunto for assunto, _ in ranqueados[:limite]], evitados
