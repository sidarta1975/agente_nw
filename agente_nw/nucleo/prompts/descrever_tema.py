from __future__ import annotations

from agente_nw.nucleo.modelos.tema import RespostaDescreverTema

ESQUEMA = RespostaDescreverTema

# Cenário do exemplo deliberadamente distante de qualquer termo real de teste (armadilha 24,
# docs/PLAN.md) — evita que o modelo copie a descrição do exemplo em vez de descrever o termo de verdade.
_EXEMPLO_TERMO = "cerâmica"
_EXEMPLO_SAIDA = (
    '{"descricao": "Técnicas e tradições de moldar e queimar argila para fazer peças utilitárias '
    'ou decorativas.", "sinonimos": ["olaria", "cerâmica artesanal"]}'
)


def construir_prompt(termo: str) -> str:
    return f"""\
Você recebe um termo curto — um assunto que alguém mencionou ter interesse, domínio ou curiosidade —
e escreve uma descrição objetiva do que esse assunto é, de dez a vinte palavras, sem mencionar a
pessoa, e até três sinônimos ou termos próximos (lista vazia se não houver nenhum natural).

Responda só com um objeto JSON, sem texto antes ou depois, no formato exato:
{{"descricao": "...", "sinonimos": ["..."]}}

Exemplo resolvido:
Termo: {_EXEMPLO_TERMO}
JSON: {_EXEMPLO_SAIDA}

Termo: {termo}
JSON:
"""
