from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Protocol, TypeVar

from pydantic import BaseModel

from agente_nw.nucleo.database.queries import assuntos, itens
from agente_nw.nucleo.database.queries import temas as queries_temas
from agente_nw.nucleo.llm import FalhaJsonInvalido
from agente_nw.nucleo.modelos.qualificacao import RespostaQualificar
from agente_nw.nucleo.modelos.rotulo import RespostaRotulo
from agente_nw.nucleo.prompts import qualificar, rotular

_EsquemaT = TypeVar("_EsquemaT", bound=BaseModel)

_MAX_ITENS_RESUMO = 5


class ClienteQualificacao(Protocol):
    def gerar_json(self, tarefa_nome: str, prompt: str, esquema: type[_EsquemaT]) -> _EsquemaT: ...


@dataclass
class ResumoQualificacao:
    candidatos: int = 0
    titulos_gerados: int = 0
    qualificados: int = 0
    erros: int = 0


def _itens_recentes_resumidos(conexao: sqlite3.Connection, assunto_id: int) -> list[tuple[str, str]]:
    itens_do_assunto = itens.listar_por_assunto(conexao, assunto_id)
    recentes = itens_do_assunto[-_MAX_ITENS_RESUMO:]
    return [(ic.item.titulo, ic.dominio) for ic in recentes]


def qualificar_pendentes(
    cliente_llm: ClienteQualificacao, conexao: sqlite3.Connection, limite: int
) -> ResumoQualificacao:
    resumo = ResumoQualificacao()
    candidatos = assuntos.listar_candidatos_qualificacao(conexao, limite)
    resumo.candidatos = len(candidatos)

    nomes_temas_conhecidos = [tema.nome for tema in queries_temas.listar(conexao)]

    for candidato in candidatos:
        assert candidato.id is not None
        itens_resumidos = _itens_recentes_resumidos(conexao, candidato.id)

        if candidato.titulo_gerado is None:
            prompt_rotulo = rotular.construir_prompt(itens_resumidos)
            try:
                resposta_rotulo = cliente_llm.gerar_json("rotular", prompt_rotulo, RespostaRotulo)
            except FalhaJsonInvalido:
                resumo.erros += 1
                continue
            assuntos.gravar_titulo(conexao, candidato.id, resposta_rotulo.titulo)
            conexao.commit()
            resumo.titulos_gerados += 1
            titulo = resposta_rotulo.titulo
        else:
            titulo = candidato.titulo_gerado

        prompt_qualificar = qualificar.construir_prompt(titulo, itens_resumidos, nomes_temas_conhecidos)
        try:
            resposta = cliente_llm.gerar_json("qualificar", prompt_qualificar, RespostaQualificar)
        except FalhaJsonInvalido:
            resumo.erros += 1
            continue

        temas_ids: list[int] = []
        for nome_tema in resposta.temas:
            tema = queries_temas.obter_por_nome(conexao, nome_tema)
            if tema is not None:
                assert tema.id is not None
                temas_ids.append(tema.id)

        assuntos.gravar_qualificacao(
            conexao,
            candidato.id,
            resposta.substancial,
            resposta.conversavel,
            resposta.justificativa,
            temas_ids,
        )
        conexao.commit()
        resumo.qualificados += 1

    return resumo
