from __future__ import annotations

from collections.abc import Sequence

from agente_nw.nucleo.modelos.cartao import RespostaCartao
from agente_nw.nucleo.prompts.seguranca import INSTRUCAO_DADO_EXTERNO, cercar_dado_externo

VERSAO = "2026-11-16-1"
"""Cartão a partir dos resumos de todos os itens (brief 090); `2026-11-02-1` era o de 5 itens × 300
caracteres. Cartão gravado antes fica com `assunto.cartao_versao` nulo."""
ESQUEMA = RespostaCartao

VERSAO_RESUMO_ITEM = "resumo-item-2026-11-16-1"
"""Resumo de um item, feito com o texto inteiro (brief 090). Vai para `item.resumo_versao`: resumo de
outra versão é refeito antes de ser usado. Roda na tarefa `cartao` (mesmo modelo e janela)."""

VERSAO_CONSOLIDACAO = "consolidar-2026-11-16-1"
"""Consolidação de uma parte da lista de resumos que não cabe numa chamada (brief 090)."""

PALAVRAS_DO_RESUMO = 150
"""Tamanho pedido ao modelo para o resumo de um item e para a consolidação. Texto que já tem até este
número de palavras é o seu próprio resumo: vai inteiro, sem chamada ao modelo (brief 090, teste 4)."""

# Cenário do exemplo deliberadamente distante de qualquer entrada real de teste
# (armadilha 24, docs/PLAN_agente_nw.md). O exemplo tem um número em cada uma das três
# linhas, cada um com a fonte entre parênteses na mesma linha — é exatamente o
# que a checagem determinística de cartoes.py exige; um exemplo sem número
# não ensinaria o modelo a citar a fonte quando o texto de verdade tiver um.
_EXEMPLO_TITULO = "Prefeitura do Recife inicia obras de contenção na orla"
_EXEMPLO_ITENS = [
    (
        "Prefeitura do Recife detalha cronograma das obras de contenção na orla",
        "g1.globo.com",
        "A prefeitura anunciou um pacote de R$ 40 milhões para conter a erosão em 3 trechos da orla.",
    ),
    (
        "Obras de contenção começam na orla do Recife nesta semana",
        "jconline.ne10.uol.com.br",
        "As obras, com prazo de 8 meses, começaram nesta segunda-feira na praia de Boa Viagem.",
    ),
]
_EXEMPLO_SAIDA = (
    '{"resumo": "A prefeitura do Recife anunciou R$ 40 milhões para conter a erosão '
    "da orla em 3 trechos (G1).\\nAs obras começaram nesta semana em Boa Viagem (JC "
    'Online).\\nO prazo previsto é de 8 meses (JC Online)."}'
)


def construir_prompt(titulo: str, itens: Sequence[tuple[str, str, str]]) -> str:
    """`itens`: (título, domínio, resumo) de cada item do assunto, todos; ou, quando os resumos não cabem
    na janela, das partes consolidadas da lista de resumos (`relevancia/cartoes.py`)."""
    lista_itens = "\n".join(
        f"- {cercar_dado_externo(item_titulo)} ({dominio}): {cercar_dado_externo(resumo)}"
        for item_titulo, dominio, resumo in itens
    )
    lista_exemplo_itens = "\n".join(f'- "{t}" ({d}): "{resumo}"' for t, d, resumo in _EXEMPLO_ITENS)

    return f"""\
Você recebe um assunto (o título e todos os itens de notícia que o formam, cada
um com o resumo do texto inteiro) e escreve um cartão resumindo o que
aconteceu — só o que está nos itens, nunca invente. O cartão tem exatamente
três linhas, cada uma uma frase completa; separe as três com uma quebra de
linha (\\n) dentro do texto de "resumo".

Toda vez que uma linha mencionar um número (data, valor, percentual, contagem
— qualquer dígito), essa mesma linha precisa citar a fonte entre parênteses,
pelo nome do veículo (ex.: "(G1)"), logo depois do número. Linha sem número
não precisa de fonte.

Responda só com um objeto JSON, sem texto antes ou depois, no formato exato:
{{"resumo": "..."}}

Exemplo resolvido:
Título: "{_EXEMPLO_TITULO}"
Itens:
{lista_exemplo_itens}
JSON: {_EXEMPLO_SAIDA}

{INSTRUCAO_DADO_EXTERNO}

Assunto a resumir:
Título: {cercar_dado_externo(titulo)}
Itens:
{lista_itens}
"""


def construir_prompt_resumo_item(titulo: str, dominio: str, texto: str) -> str:
    """Resumo de um item de notícia. `texto` é o texto inteiro, ou uma parte dele com o aviso
    "[parte K de N de um documento maior]" (`texto_integral.texto_para_o_prompt`)."""
    return f"""\
Você recebe um item de notícia (título, domínio da fonte e o texto) e escreve
um resumo dele em até {PALAVRAS_DO_RESUMO} palavras: os fatos, as decisões, os
desdobramentos, quem fez o quê, onde e quando. Mantenha todo número (data,
valor, percentual, contagem) que estiver no texto, do jeito que está. Só o que
está no texto, nunca invente. Se o texto for uma parte de um documento maior,
resuma só essa parte, sem supor o resto.

Responda só com um objeto JSON, sem texto antes ou depois, no formato exato:
{{"resumo": "..."}}

{INSTRUCAO_DADO_EXTERNO}

Título: {cercar_dado_externo(titulo)}
Fonte: {dominio}
Texto:
{cercar_dado_externo(texto)}
"""


def construir_prompt_consolidacao(titulo: str, lista_de_resumos: str) -> str:
    """Consolidação de uma parte da lista de resumos dos itens de um assunto (cada item numa linha
    "título (domínio): resumo"), quando a lista inteira não cabe na janela do cartão."""
    return f"""\
Você recebe parte da lista de resumos dos itens de notícia de um mesmo assunto
(cada item com título, domínio da fonte e resumo) e escreve um resumo único
dessa parte, em até {PALAVRAS_DO_RESUMO} palavras, com todos os fatos que ela traz.
Toda vez que mencionar um número, cite logo depois, entre parênteses, a fonte
de onde ele veio (o domínio do item, ex.: "(g1.globo.com)"). Só o que está na
lista, nunca invente.

Responda só com um objeto JSON, sem texto antes ou depois, no formato exato:
{{"resumo": "..."}}

{INSTRUCAO_DADO_EXTERNO}

Assunto: {cercar_dado_externo(titulo)}
Resumos:
{cercar_dado_externo(lista_de_resumos)}
"""
