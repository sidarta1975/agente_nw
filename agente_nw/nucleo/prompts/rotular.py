from __future__ import annotations

from collections.abc import Sequence

from agente_nw.nucleo.modelos.rotulo import RespostaRotulo
from agente_nw.nucleo.prompts.seguranca import INSTRUCAO_DADO_EXTERNO, cercar_dado_externo

VERSAO = "2026-11-16-1"
"""Itens com o resumo do texto inteiro, todos os do assunto (brief 090); `2026-11-02-1` via título e
domínio de 5 itens."""
ESQUEMA = RespostaRotulo

# Cenário do exemplo deliberadamente distante de qualquer entrada real de teste
# (armadilha 24, docs/PLAN_agente_nw.md) — evita que o modelo copie conteúdo do exemplo em
# vez de resumir os itens de verdade.
_EXEMPLO_ITENS = [
    (
        "Prefeitura do Recife detalha cronograma das obras de contenção na orla",
        "g1.globo.com",
        "A prefeitura anunciou o pacote para conter a erosão em três trechos da orla.",
    ),
    (
        "Obras de contenção começam na orla do Recife nesta semana",
        "jconline.ne10.uol.com.br",
        "As obras começaram nesta segunda-feira na praia de Boa Viagem, com prazo de oito meses.",
    ),
]
_EXEMPLO_SAIDA = '{"titulo": "Prefeitura do Recife inicia obras de contenção na orla"}'


def construir_prompt(itens: Sequence[tuple[str, str, str]]) -> str:
    """`itens`: (título, domínio, resumo) de todos os itens do assunto, ou das partes consolidadas da
    lista de resumos quando ela não cabe na janela (`relevancia/cartoes.py`, brief 090)."""
    lista_itens = "\n".join(
        f"- {cercar_dado_externo(titulo)} ({dominio}): {cercar_dado_externo(resumo)}"
        for titulo, dominio, resumo in itens
    )
    lista_exemplo = "\n".join(
        f'- "{titulo}" ({dominio}): "{resumo}"' for titulo, dominio, resumo in _EXEMPLO_ITENS
    )

    return f"""\
Você recebe os itens de notícia (título, domínio da fonte e o resumo do texto
inteiro) que formam um mesmo assunto, e escreve um título curto para esse
assunto — como uma manchete, de 6 a 10 palavras, resumindo o fato em si, não a
lista de itens.

Responda só com um objeto JSON, sem texto antes ou depois, no formato exato:
{{"titulo": "..."}}

Exemplo resolvido:
Itens:
{lista_exemplo}
JSON: {_EXEMPLO_SAIDA}

{INSTRUCAO_DADO_EXTERNO}

Itens a resumir:
{lista_itens}
"""
