"""Cartão do assunto, feito com o que **todos** os itens dizem (brief 090).

1. **Resumo por item.** Cada item com corpo ganha um resumo guardado (`item.resumo`, migração 022), feito
   com o texto inteiro: numa chamada quando cabe, em partes que cobrem tudo quando não cabe
   (`nucleo/texto_integral.py`, brief 088). Texto que já tem até `PALAVRAS_DO_RESUMO` palavras é o seu
   próprio resumo, sem chamada ao modelo. Resumo de outra versão é refeito antes de ser usado.
2. **Cartão dos resumos.** O prompt do cartão recebe os resumos de todos os itens. Se não cabe na janela,
   a lista de resumos é dividida em partes que cobrem tudo (a mesma peça do brief 088) e cada parte vira
   um resumo consolidado; o cartão é feito com as consolidações (dois níveis). Nunca há corte.

A qualificação (`qualificador.py`) lê os mesmos resumos, pela mesma regra de caber na janela.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import NamedTuple, Protocol

from agente_nw.nucleo import texto_integral
from agente_nw.nucleo.database.queries import assuntos, fila_revisao, itens
from agente_nw.nucleo.estimativa_tokens import estimar_tokens_conservador
from agente_nw.nucleo.llm import FalhaJsonInvalido, JanelaEstourada
from agente_nw.nucleo.modelos.cartao import RespostaCartao
from agente_nw.nucleo.modelos.proveniencia import Proveniencia
from agente_nw.nucleo.prompts import cartao as prompt_cartao
from agente_nw.nucleo.texto_integral import Parte

TAREFA = "cartao"
"""Resumo do item, consolidação e cartão rodam na tarefa `cartao` (mesmo modelo e janela do perfil); a
versão do prompt (`prompt_cartao.VERSAO*`) distingue as três no `chamadas_llm.jsonl`."""

_MAX_TENTATIVAS = 2
_MOTIVO_REFEITO = "estouro de janela refeito em partes menores (brief 088)"
_TITULO_DA_CONSOLIDACAO = "Parte {indice} de {total} dos itens do assunto"
_DOMINIO_DA_CONSOLIDACAO = "várias fontes"


class ClienteCartao(Protocol):
    def gerar_json(
        self,
        tarefa_nome: str,
        prompt: str,
        esquema: type[RespostaCartao],
        *,
        versao_prompt: str | None = None,
    ) -> RespostaCartao: ...

    def proveniencia(self, tarefa_nome: str, versao_prompt: str | None = None) -> Proveniencia: ...

    def num_ctx(self, tarefa_nome: str) -> int: ...


class EntradaDoAssunto(NamedTuple):
    """O que o cartão, o título e a qualificação leem de um item: título, domínio e resumo. Depois de uma
    consolidação, a entrada é uma parte da lista de resumos ("Parte K de N dos itens do assunto")."""

    titulo: str
    dominio: str
    resumo: str


@dataclass(frozen=True)
class ResumoDoItem:
    resumo: str
    partes: int
    """0 = o texto é o próprio resumo (sem chamada); 1 = texto inteiro numa chamada; N = em N partes."""
    proveniencia: Proveniencia | None


def _linha_tem_numero_sem_fonte(linha: str) -> bool:
    tem_digito = any(caractere.isdigit() for caractere in linha)
    if not tem_digito:
        return False
    return "(" not in linha or ")" not in linha


def _cartao_valido(resumo: str) -> bool:
    return not any(_linha_tem_numero_sem_fonte(linha) for linha in resumo.split("\n"))


def _descartar_recusa_refeita(conexao: sqlite3.Connection | None) -> Callable[[BaseException], None]:
    """A recusa por tamanho superada por uma divisão menor sai da `fila_revisao`, como no brief 088. Sem
    conexão (simulação, que não grava), a recusa fica só na fila do próprio cliente."""

    def refazer(erro: BaseException) -> None:
        if conexao is not None and isinstance(erro, FalhaJsonInvalido):
            fila_revisao.descartar(
                conexao, erro.fila_revisao_id, _MOTIVO_REFEITO, datetime.now(UTC).isoformat()
            )

    return refazer


def texto_e_o_proprio_resumo(texto: str) -> bool:
    """Texto com até `PALAVRAS_DO_RESUMO` palavras não fica menor resumido: vai inteiro, como está."""
    return len(texto.split()) <= prompt_cartao.PALAVRAS_DO_RESUMO


def resumir_item(
    cliente: ClienteCartao, titulo: str, dominio: str, texto: str, conexao: sqlite3.Connection | None = None
) -> ResumoDoItem:
    """Resumo de um item com o texto inteiro. Texto que não cabe numa chamada é lido em partes que cobrem
    tudo; o resumo do item é então o resumo de cada parte, na ordem, uma por linha (união ordenada: nada de
    uma parte se perde por causa de outra). Falha em qualquer parte invalida o resumo inteiro."""
    if texto_e_o_proprio_resumo(texto):
        return ResumoDoItem(texto, 0, None)
    orcamento = texto_integral.orcamento_do_texto(
        cliente.num_ctx(TAREFA), prompt_cartao.construir_prompt_resumo_item(titulo, dominio, "")
    )

    def processar(partes: list[Parte]) -> list[str]:
        return [
            cliente.gerar_json(
                TAREFA,
                prompt_cartao.construir_prompt_resumo_item(
                    titulo, dominio, texto_integral.texto_para_o_prompt(p)
                ),
                RespostaCartao,
                versao_prompt=prompt_cartao.VERSAO_RESUMO_ITEM,
            ).resumo
            for p in partes
        ]

    resumos, partes = texto_integral.processar_dividindo(
        texto, orcamento, processar, JanelaEstourada, _descartar_recusa_refeita(conexao)
    )
    return ResumoDoItem(
        "\n".join(resumos), len(partes), cliente.proveniencia(TAREFA, prompt_cartao.VERSAO_RESUMO_ITEM)
    )


def resumos_do_assunto(
    cliente: ClienteCartao, conexao: sqlite3.Connection, assunto_id: int, gravar: bool = True
) -> list[EntradaDoAssunto]:
    """Todos os itens do assunto com corpo (o item sem corpo fica fora, brief 083), cada um com o resumo.
    O resumo guardado da versão atual é reaproveitado; o ausente ou de outra versão é feito agora e, com
    `gravar`, gravado no item. `gravar=False` não escreve nada no banco (comparação em simulação). Uma
    falha sobe (`FalhaJsonInvalido`): sem o resumo de um item, ninguém recebe a lista pela metade."""
    entradas: list[EntradaDoAssunto] = []
    for com_dominio in itens.listar_por_assunto(conexao, assunto_id, com_corpo=True):
        item = com_dominio.item
        assert item.id is not None and item.texto is not None
        gravado = itens.obter_resumo(conexao, item.id)
        if gravado is not None and gravado.versao == prompt_cartao.VERSAO_RESUMO_ITEM:
            resumo = gravado.resumo
        else:
            novo = resumir_item(
                cliente, item.titulo, com_dominio.dominio, item.texto, conexao if gravar else None
            )
            if gravar:
                itens.gravar_resumo(
                    conexao,
                    item.id,
                    novo.resumo,
                    prompt_cartao.VERSAO_RESUMO_ITEM,
                    novo.partes,
                    novo.proveniencia,
                )
                conexao.commit()
            resumo = novo.resumo
        entradas.append(EntradaDoAssunto(item.titulo, com_dominio.dominio, resumo))
    return entradas


def _lista_como_texto(entradas: list[EntradaDoAssunto]) -> str:
    """Um item por parágrafo: a divisão do brief 088 prefere cortar em fim de parágrafo."""
    return "\n\n".join(f"{e.titulo} ({e.dominio}): {e.resumo}" for e in entradas)


def _consolidar(
    cliente: ClienteCartao, titulo: str, entradas: list[EntradaDoAssunto], conexao: sqlite3.Connection | None
) -> list[EntradaDoAssunto]:
    """Um nível de consolidação: a lista de resumos, como texto, dividida em partes que cobrem tudo, e uma
    consolidação por parte, na ordem."""
    orcamento = texto_integral.orcamento_do_texto(
        cliente.num_ctx(TAREFA), prompt_cartao.construir_prompt_consolidacao(titulo, "")
    )

    def processar(partes: list[Parte]) -> list[str]:
        return [
            cliente.gerar_json(
                TAREFA,
                prompt_cartao.construir_prompt_consolidacao(titulo, texto_integral.texto_para_o_prompt(p)),
                RespostaCartao,
                versao_prompt=prompt_cartao.VERSAO_CONSOLIDACAO,
            ).resumo
            for p in partes
        ]

    resumos, _ = texto_integral.processar_dividindo(
        _lista_como_texto(entradas), orcamento, processar, JanelaEstourada, _descartar_recusa_refeita(conexao)
    )
    total = len(resumos)
    return [
        EntradaDoAssunto(_TITULO_DA_CONSOLIDACAO.format(indice=i, total=total), _DOMINIO_DA_CONSOLIDACAO, r)
        for i, r in enumerate(resumos, start=1)
    ]


def caber_na_janela(
    cliente: ClienteCartao,
    titulo: str,
    entradas: list[EntradaDoAssunto],
    montar: Callable[[list[EntradaDoAssunto]], str],
    janela: int,
    conexao: sqlite3.Connection | None = None,
) -> tuple[list[EntradaDoAssunto], int]:
    """As entradas que vão ao prompt montado por `montar` e o número de níveis (1 = os resumos de todos os
    itens, sem consolidação). Se o prompt passa da `janela` (o `num_ctx` da tarefa, pelo estimador do
    brief 082), a lista é consolidada (`_consolidar`) e conferida de novo — dois níveis no caso comum. Para
    quando uma rodada não diminui o número de entradas: o prompt vai como está e o cliente o recusa em voz
    alta (brief 082). Nenhuma entrada é descartada em nível nenhum."""
    niveis = 1
    while len(entradas) > 1 and estimar_tokens_conservador(montar(entradas)) > janela:
        consolidadas = _consolidar(cliente, titulo, entradas, conexao)
        if len(consolidadas) >= len(entradas):
            break
        entradas = consolidadas
        niveis += 1
    return entradas, niveis


def gerar_cartao(cliente_llm: ClienteCartao, conexao: sqlite3.Connection, assunto_id: int) -> str | None:
    assunto = assuntos.obter_por_id(conexao, assunto_id)
    if assunto is None:
        raise ValueError(f"assunto {assunto_id} não existe")

    titulo = assunto.titulo_gerado or "(sem título)"
    try:
        entradas = resumos_do_assunto(cliente_llm, conexao, assunto_id)
        cabem, niveis = caber_na_janela(
            cliente_llm,
            titulo,
            entradas,
            lambda lista: prompt_cartao.construir_prompt(titulo, lista),
            cliente_llm.num_ctx(TAREFA),
            conexao,
        )
    except FalhaJsonInvalido:
        return None  # o cliente já pôs o prompt na fila_revisao; nenhum cartão parcial
    prompt = prompt_cartao.construir_prompt(titulo, cabem)

    for _tentativa in range(_MAX_TENTATIVAS):
        try:
            resposta = cliente_llm.gerar_json(
                TAREFA, prompt, RespostaCartao, versao_prompt=prompt_cartao.VERSAO
            )
        except FalhaJsonInvalido:
            continue
        if _cartao_valido(resposta.resumo):
            assuntos.gravar_cartao(
                conexao,
                assunto_id,
                resposta.resumo,
                cliente_llm.proveniencia(TAREFA, prompt_cartao.VERSAO),
                itens_cobertos=len(entradas),
                niveis=niveis,
            )
            conexao.commit()
            return resposta.resumo

    agora = datetime.now(UTC).isoformat()
    fila_revisao.inserir(
        conexao,
        tarefa="cartao",
        entrada=str(assunto_id),
        erro="número sem fonte entre parênteses",
        agora=agora,
    )
    conexao.commit()
    return None


@dataclass
class ResumoCartoes:
    candidatos: int = 0
    gerados: int = 0
    erros: int = 0


def gerar_pendentes(cliente_llm: ClienteCartao, conexao: sqlite3.Connection, limite: int) -> ResumoCartoes:
    resumo = ResumoCartoes()
    candidatos = assuntos.listar_qualificados_sem_cartao(conexao, limite)
    resumo.candidatos = len(candidatos)

    for assunto in candidatos:
        assert assunto.id is not None
        resultado = gerar_cartao(cliente_llm, conexao, assunto.id)
        if resultado is None:
            resumo.erros += 1
        else:
            resumo.gerados += 1

    return resumo
