from __future__ import annotations

import sqlite3
import unicodedata

from agente_nw.nucleo.database.queries import assunto_contato, assuntos, itens
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
    modelo_embedding: str,
) -> list[Assunto]:
    ids_vistos = assunto_contato.listar_assunto_ids_ja_vistos(conexao, perfil_id)
    candidatos_com_centroide = assuntos.listar_qualificados_nao_vistos(
        conexao, substancial_minimo, conversavel_minimo, ids_vistos, modelo_embedding
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


def _texto_do_assunto(assunto: Assunto, conexao: sqlite3.Connection | None) -> str:
    """Título e resumo do assunto e, com a conexão, o título (a manchete) e o resumo de **todos** os itens
    dele (brief 091). Sem a conexão, só o título e o resumo do assunto."""
    partes = [assunto.titulo_gerado or "", assunto.resumo_cartao or ""]
    if conexao is not None and assunto.id is not None:
        for com_dominio in itens.listar_por_assunto(conexao, assunto.id):
            partes.append(com_dominio.item.titulo)
            if com_dominio.item.id is not None:
                gravado = itens.obter_resumo(conexao, com_dominio.item.id)
                if gravado is not None:
                    partes.append(gravado.resumo)
    return _sem_acento_e_caixa(" ".join(partes))


def termo_evitado(assunto: Assunto, evitar: list[str], conexao: sqlite3.Connection | None = None) -> bool:
    """Correspondência literal, sem acento e sem caixa, no título e no resumo do assunto e, com a conexão,
    nas manchetes e nos resumos de todos os itens dele. Achou o termo, o assunto é evitado."""
    texto = _texto_do_assunto(assunto, conexao)
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
    modelo_embedding: str,
) -> tuple[list[Assunto], list[Assunto]]:
    """Devolve (selecionados, evitados).

    Os evitados saem antes do corte em `limite`, para não ocupar vaga. A ordenação é pelo cosseno
    à consulta; com centroide do contato, pesos `selecao_peso_*` de `limiares.conector.consulta`."""
    ids_vistos = assunto_contato.listar_assunto_ids_ja_vistos(conexao, perfil_id)
    candidatos_com_centroide = assuntos.listar_qualificados_nao_vistos(
        conexao, substancial_minimo, conversavel_minimo, ids_vistos, modelo_embedding
    )

    evitados = [assunto for assunto, _ in candidatos_com_centroide if termo_evitado(assunto, evitar, conexao)]
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
