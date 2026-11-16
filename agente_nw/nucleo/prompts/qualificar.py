from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import yaml

from agente_nw.nucleo.modelos.qualificacao import RespostaQualificar
from agente_nw.nucleo.prompts.seguranca import INSTRUCAO_DADO_EXTERNO, cercar_dado_externo

VERSAO = "2026-11-16-1"
"""Itens com o resumo do texto inteiro, todos os do assunto (brief 090); `2026-11-02-1` via título e
domínio de 5 itens."""
ESQUEMA = RespostaQualificar

_CAMINHO_EXEMPLOS_CONVERSAVEL = Path(__file__).resolve().parent / "exemplos_conversavel.yaml"
_exemplos = yaml.safe_load(_CAMINHO_EXEMPLOS_CONVERSAVEL.read_text(encoding="utf-8"))
_EXEMPLOS_CONVERSAVEL: list[str] = _exemplos["conversavel"]
_EXEMPLOS_NAO_CONVERSAVEL: list[str] = _exemplos["nao_conversavel"]

# Cenário do exemplo resolvido deliberadamente distante de qualquer entrada real de
# teste (armadilha 24, docs/PLAN_agente_nw.md) — evita que o modelo copie conteúdo do exemplo
# em vez de julgar o assunto de verdade.
_EXEMPLO_TITULO = "Prefeitura do Recife inicia obras de contenção na orla"
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
_EXEMPLO_TEMAS_CONHECIDOS = ["urbanismo", "esportes", "culinária"]
_EXEMPLO_SAIDA = (
    '{"substancial": 0.7, "conversavel": 0.9, "temas": ["urbanismo"], '
    '"justificativa": "obra pública concreta, com cronograma e local definidos, '
    'fácil de comentar sem conhecimento técnico"}'
)


def construir_prompt(titulo: str, itens: Sequence[tuple[str, str, str]], temas_conhecidos: list[str]) -> str:
    """`itens`: (título, domínio, resumo) de todos os itens do assunto, ou das partes consolidadas da
    lista de resumos quando ela não cabe na janela (`relevancia/cartoes.py`, brief 090)."""
    lista_itens = "\n".join(
        f"- {cercar_dado_externo(item_titulo)} ({dominio}): {cercar_dado_externo(resumo)}"
        for item_titulo, dominio, resumo in itens
    )
    lista_exemplo_itens = "\n".join(f'- "{t}" ({d}): "{resumo}"' for t, d, resumo in _EXEMPLO_ITENS)
    lista_temas = ", ".join(temas_conhecidos) if temas_conhecidos else "(nenhum tema conhecido)"
    lista_exemplo_temas = ", ".join(_EXEMPLO_TEMAS_CONHECIDOS)
    lista_conversavel = "\n".join(f"- {frase}" for frase in _EXEMPLOS_CONVERSAVEL)
    lista_nao_conversavel = "\n".join(f"- {frase}" for frase in _EXEMPLOS_NAO_CONVERSAVEL)

    return f"""\
Você recebe um assunto (título e todos os itens de notícia que o formam, cada
um com o resumo do texto inteiro) e avalia três coisas sobre ele:

"substancial" (0 a 1) — o quanto o assunto tem substância de verdade: um fato
concreto, uma decisão, um desdobramento — não uma especulação vaga ou nota
passageira sem conteúdo.

"conversavel" (0 a 1) — o quanto dá para puxar assunto sobre isso com um
resumo curto na mão, sem ser especialista no tema. Exemplos de conversável:
{lista_conversavel}
Exemplos de não conversável (exigem bagagem técnica específica):
{lista_nao_conversavel}

"temas" — quais destes temas conhecidos este assunto toca (lista vazia se
nenhum, nunca invente um tema fora desta lista):
{lista_temas}

"justificativa" — uma frase curta explicando as notas acima.

Responda só com um objeto JSON, sem texto antes ou depois, no formato exato:
{{"substancial": 0 a 1, "conversavel": 0 a 1, "temas": [...], "justificativa": "..."}}

Exemplo resolvido:
Título: "{_EXEMPLO_TITULO}"
Itens:
{lista_exemplo_itens}
Temas conhecidos: {lista_exemplo_temas}
JSON: {_EXEMPLO_SAIDA}

{INSTRUCAO_DADO_EXTERNO}

Assunto a avaliar:
Título: {cercar_dado_externo(titulo)}
Itens:
{lista_itens}
Temas conhecidos: {lista_temas}
"""
