from __future__ import annotations

from agente_nw.nucleo.modelos.rotulo import RespostaRotulo

ESQUEMA = RespostaRotulo

# Cenário do exemplo deliberadamente distante de qualquer entrada real de teste
# (armadilha 24, docs/PLAN.md) — evita que o modelo copie conteúdo do exemplo em
# vez de resumir os itens de verdade.
_EXEMPLO_ITENS = [
    ("Prefeitura do Recife detalha cronograma das obras de contenção na orla", "g1.globo.com"),
    ("Obras de contenção começam na orla do Recife nesta semana", "jconline.ne10.uol.com.br"),
]
_EXEMPLO_SAIDA = '{"titulo": "Prefeitura do Recife inicia obras de contenção na orla"}'


def construir_prompt(itens: list[tuple[str, str]]) -> str:
    lista_itens = "\n".join(f'- "{titulo}" ({dominio})' for titulo, dominio in itens)
    lista_exemplo = "\n".join(f'- "{titulo}" ({dominio})' for titulo, dominio in _EXEMPLO_ITENS)

    return f"""\
Você recebe até cinco itens de notícia (título e domínio da fonte) que formam
um mesmo assunto, e escreve um título curto para esse assunto — como uma
manchete, de 6 a 10 palavras, resumindo o fato em si, não a lista de itens.

Responda só com um objeto JSON, sem texto antes ou depois, no formato exato:
{{"titulo": "..."}}

Exemplo resolvido:
Itens:
{lista_exemplo}
JSON: {_EXEMPLO_SAIDA}

Itens a resumir:
{lista_itens}
"""
