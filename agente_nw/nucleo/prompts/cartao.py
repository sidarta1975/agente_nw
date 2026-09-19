from __future__ import annotations

from agente_nw.nucleo.modelos.cartao import RespostaCartao

ESQUEMA = RespostaCartao

# Cenário do exemplo deliberadamente distante de qualquer entrada real de teste
# (armadilha 24, docs/PLAN.md). O exemplo tem um número em cada uma das três
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


def construir_prompt(titulo: str, itens: list[tuple[str, str, str]]) -> str:
    lista_itens = "\n".join(
        f'- "{item_titulo}" ({dominio}): "{trecho}"' for item_titulo, dominio, trecho in itens
    )
    lista_exemplo_itens = "\n".join(f'- "{t}" ({d}): "{trecho}"' for t, d, trecho in _EXEMPLO_ITENS)

    return f"""\
Você recebe um assunto (título e até cinco itens de notícia, cada um com um
trecho do texto) e escreve um cartão resumindo o que aconteceu — só o que
está nos itens, nunca invente. O cartão tem exatamente três linhas, cada uma
uma frase completa; separe as três com uma quebra de linha (\\n) dentro do
texto de "resumo".

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

Assunto a resumir:
Título: "{titulo}"
Itens:
{lista_itens}
"""
