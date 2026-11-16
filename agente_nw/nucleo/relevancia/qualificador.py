from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Protocol, TypeVar

from pydantic import BaseModel

from agente_nw.nucleo.database.queries import assuntos
from agente_nw.nucleo.database.queries import temas as queries_temas
from agente_nw.nucleo.llm import FalhaJsonInvalido
from agente_nw.nucleo.modelos.proveniencia import Proveniencia
from agente_nw.nucleo.modelos.qualificacao import RespostaQualificar
from agente_nw.nucleo.modelos.rotulo import RespostaRotulo
from agente_nw.nucleo.prompts import qualificar, rotular
from agente_nw.nucleo.relevancia import cartoes
from agente_nw.nucleo.relevancia.cartoes import EntradaDoAssunto

_EsquemaT = TypeVar("_EsquemaT", bound=BaseModel)


class ClienteQualificacao(Protocol):
    def gerar_json(
        self, tarefa_nome: str, prompt: str, esquema: type[_EsquemaT], *, versao_prompt: str | None = None
    ) -> _EsquemaT: ...

    def proveniencia(self, tarefa_nome: str, versao_prompt: str | None = None) -> Proveniencia: ...

    def num_ctx(self, tarefa_nome: str) -> int: ...

    @property
    def modelo_embedding(self) -> str: ...


@dataclass
class ResumoQualificacao:
    candidatos: int = 0
    titulos_gerados: int = 0
    qualificados: int = 0
    erros: int = 0
    sem_corpo: int = 0  # assunto só com itens sem corpo: não é julgado pela manchete (brief 083)


def _itens_recentes_resumidos(
    cliente_llm: ClienteQualificacao, conexao: sqlite3.Connection, assunto_id: int
) -> list[EntradaDoAssunto]:
    """Todos os itens com corpo do assunto (o sem corpo fica fora, brief 083), cada um com o resumo do texto
    inteiro: os mesmos resumos que o cartão lê (brief 090), feitos e gravados aqui se ainda não existem.
    Nada de corte do texto nem de teto de itens; o que não couber na janela é consolidado por
    `cartoes.caber_na_janela`."""
    return cartoes.resumos_do_assunto(cliente_llm, conexao, assunto_id)


def qualificar_pendentes(
    cliente_llm: ClienteQualificacao,
    conexao: sqlite3.Connection,
    limite: int,
    vetores_extras: list[list[float]] | None = None,
) -> ResumoQualificacao:
    resumo = ResumoQualificacao()
    candidatos = assuntos.listar_candidatos_qualificacao(
        conexao, limite, cliente_llm.modelo_embedding, vetores_extras
    )
    resumo.candidatos = len(candidatos)

    nomes_temas_conhecidos = [tema.nome for tema in queries_temas.listar(conexao)]

    for candidato in candidatos:
        assert candidato.id is not None
        try:
            itens_resumidos = _itens_recentes_resumidos(cliente_llm, conexao, candidato.id)
        except FalhaJsonInvalido:
            resumo.erros += 1
            continue
        if not itens_resumidos:
            resumo.sem_corpo += 1
            continue

        if candidato.titulo_gerado is None:
            try:
                para_rotulo, _ = cartoes.caber_na_janela(
                    cliente_llm,
                    "(sem título)",
                    itens_resumidos,
                    rotular.construir_prompt,
                    cliente_llm.num_ctx("rotular"),
                    conexao,
                )
                prompt_rotulo = rotular.construir_prompt(para_rotulo)
                resposta_rotulo = cliente_llm.gerar_json(
                    "rotular", prompt_rotulo, RespostaRotulo, versao_prompt=rotular.VERSAO
                )
            except FalhaJsonInvalido:
                resumo.erros += 1
                continue
            assuntos.gravar_titulo(conexao, candidato.id, resposta_rotulo.titulo)
            conexao.commit()
            resumo.titulos_gerados += 1
            titulo = resposta_rotulo.titulo
        else:
            titulo = candidato.titulo_gerado

        def montar(lista: list[EntradaDoAssunto], titulo: str = titulo) -> str:
            return qualificar.construir_prompt(titulo, lista, nomes_temas_conhecidos)

        try:
            para_qualificar, _ = cartoes.caber_na_janela(
                cliente_llm, titulo, itens_resumidos, montar, cliente_llm.num_ctx("qualificar"), conexao
            )
            prompt_qualificar = montar(para_qualificar)
            resposta = cliente_llm.gerar_json(
                "qualificar", prompt_qualificar, RespostaQualificar, versao_prompt=qualificar.VERSAO
            )
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
            cliente_llm.proveniencia("qualificar", qualificar.VERSAO),
        )
        conexao.commit()
        resumo.qualificados += 1

    return resumo
