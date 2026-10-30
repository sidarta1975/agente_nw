from __future__ import annotations

from agente_nw.nucleo.modelos.cruzamento import RespostaAvaliarRelacaoObjetivo

ESQUEMA = RespostaAvaliarRelacaoObjetivo

# Cenário do exemplo deliberadamente distante de qualquer entrada real de teste (armadilha 24,
# docs/PLAN.md). O gate julga relação com o objetivo, nunca se o tema é "adequado" — por isso o
# exemplo tem um candidato claramente fora do objetivo e outro claramente dentro, nenhum sensível.
_EXEMPLO_OBJETIVO = "conseguir apoio para a campanha de arrecadação do grêmio da escola"
_EXEMPLO_FRASE = "Queria pedir pro Heitor ajudar a divulgar a campanha do grêmio."
_EXEMPLO_FICHA = "cargo: coordenador de eventos, empresa: Prefeitura de Itu"
_EXEMPLO_CANDIDATOS = [
    (
        "Prefeitura de Itu abre inscrições para feira de adoção de animais",
        "A feira oferece castração grátis.",
    ),
    ("Câmara aprova verba extra para eventos escolares em todo o estado", "A verba cobre material e espaço."),
]
_EXEMPLO_SAIDA = (
    '{"avaliacoes": ['
    '{"relaciona": false, "motivo": "feira de adoção de animais não tem relação com a campanha do grêmio"}, '
    '{"relaciona": true, "motivo": "a verba para eventos escolares se liga direto à arrecadação do grêmio"}'
    "]}"
)


def construir_prompt(
    objetivo: str, frase: str, ficha_contato: str, candidatos: list[tuple[str, str | None]]
) -> str:
    lista_candidatos = "\n".join(
        f'{indice}. "{titulo}" — {resumo or "(sem resumo)"}'
        for indice, (titulo, resumo) in enumerate(candidatos, start=1)
    )
    lista_exemplo = "\n".join(
        f'{indice}. "{titulo}" — {resumo}'
        for indice, (titulo, resumo) in enumerate(_EXEMPLO_CANDIDATOS, start=1)
    )

    return f"""\
Você julga, notícia por notícia, se ela tem relação real com o objetivo de um pedido — não se o \
tema é adequado, sensível ou poderia ser discutido; só se ajuda a atingir esse objetivo com esta \
pessoa. Relevante para o contato não basta: a pergunta é se serve ao objetivo do pedido.

Responda só com um objeto JSON, sem texto antes ou depois, com exatamente uma avaliação por \
candidato recebido, na mesma ordem:
{{"avaliacoes": [{{"relaciona": true, "motivo": "uma frase curta"}}]}}

Exemplo resolvido:
Objetivo: {_EXEMPLO_OBJETIVO}
Frase do pedido: "{_EXEMPLO_FRASE}"
Ficha do contato: {_EXEMPLO_FICHA}
Candidatos:
{lista_exemplo}
JSON: {_EXEMPLO_SAIDA}

Objetivo: {objetivo}
Frase do pedido: "{frase}"
Ficha do contato: {ficha_contato or "(nada informado)"}
Candidatos:
{lista_candidatos}
"""
