from __future__ import annotations

from agente_nw.nucleo.modelos.calibracao import RespostaComparacaoPar

ESQUEMA = RespostaComparacaoPar

# Dois exemplos, de propósito — um par que é o mesmo assunto e um que não é: um
# exemplo só (sempre "verdadeiro", por exemplo) ensinaria o modelo a responder sempre
# a mesma coisa. O segundo exemplo é deliberadamente do mesmo tema geral do primeiro
# (não um tema totalmente alheio) — é essa a distinção que o modelo precisa aprender:
# mesmo tema não é mesmo assunto. Os títulos e trechos dos exemplos são deliberadamente
# distantes de qualquer texto real de teste (armadilha 24, docs/PLAN.md) para não
# incentivar o modelo a copiar o rótulo do exemplo em vez de julgar o par de verdade.
_EXEMPLO_1_TITULO_A = "Prefeitura de Recife anuncia obras na orla"
_EXEMPLO_1_TRECHO_A = "A prefeitura do Recife anunciou nesta terça-feira um pacote de obras de contenção."
_EXEMPLO_1_TITULO_B = "Obras de contenção começam na orla do Recife"
_EXEMPLO_1_TRECHO_B = "Começaram hoje as obras de contenção anunciadas pela prefeitura na orla da capital."
_EXEMPLO_1_SAIDA = '{"mesmo_assunto": true}'

_EXEMPLO_2_TITULO_A = "Incêndio atinge galpão industrial em Contagem, ninguém ficou ferido"
_EXEMPLO_2_TRECHO_A = "Um incêndio atingiu um galpão industrial em Contagem nesta segunda-feira."
_EXEMPLO_2_TITULO_B = "Novo incêndio atinge galpão na Grande BH, uma semana depois do de Contagem"
_EXEMPLO_2_TRECHO_B = "Bombeiros controlaram um incêndio em outro galpão na Grande BH nesta segunda."
_EXEMPLO_2_SAIDA = '{"mesmo_assunto": false}'


def construir_prompt(titulo_a: str, trecho_a: str, titulo_b: str, trecho_b: str) -> str:
    return f"""\
Você recebe dois itens de notícia — título e um trecho de cada um — e decide se
os dois tratam do mesmo assunto ou de assuntos diferentes.

Mesmo assunto significa que os dois itens sairiam como uma matéria só, não duas:
o mesmo evento concreto (a mesma declaração, a mesma decisão, o mesmo fato pontual),
não apenas o mesmo tema geral. Dois itens sobre o mesmo tema, mas eventos concretos
diferentes, são assuntos diferentes.

Responda só com um objeto JSON, sem texto antes ou depois, no formato exato:
{{"mesmo_assunto": true ou false}}

Exemplo 1 — mesmo assunto (mesmo evento concreto, veículos diferentes):
Item A — título: "{_EXEMPLO_1_TITULO_A}"
Item A — trecho: "{_EXEMPLO_1_TRECHO_A}"
Item B — título: "{_EXEMPLO_1_TITULO_B}"
Item B — trecho: "{_EXEMPLO_1_TRECHO_B}"
JSON: {_EXEMPLO_1_SAIDA}

Exemplo 2 — assuntos diferentes (mesmo tema geral, eventos concretos diferentes):
Item A — título: "{_EXEMPLO_2_TITULO_A}"
Item A — trecho: "{_EXEMPLO_2_TRECHO_A}"
Item B — título: "{_EXEMPLO_2_TITULO_B}"
Item B — trecho: "{_EXEMPLO_2_TRECHO_B}"
JSON: {_EXEMPLO_2_SAIDA}

Par a avaliar:
Item A — título: "{titulo_a}"
Item A — trecho: "{trecho_a}"
Item B — título: "{titulo_b}"
Item B — trecho: "{trecho_b}"
"""
