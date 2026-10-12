from __future__ import annotations

from agente_nw.nucleo.modelos.pedido import PedidoExtraido

ESQUEMA = PedidoExtraido

# Cenário do exemplo resolvido deliberadamente distante de qualquer entrada real de
# teste (armadilha 24, docs/PLAN.md) — evita que o modelo copie o exemplo em vez de ler a frase.
_EXEMPLO_FRASE = (
    "Jantar sábado com o Teodoro, dono de uma marcenaria em Joinville que conheço da faculdade. "
    "Não nos falamos desde a pandemia. Quero saber como andam os negócios dele, sem falar de política."
)
_EXEMPLO_CONTATOS = [("Olívia Prado", "Clínica Prado", "pediatra")]
_EXEMPLO_SAIDA = (
    '{"pessoa_nome": "Teodoro", '
    '"pessoa_pistas": {"profissao": "dono de marcenaria", "cidade": "Joinville", '
    '"vinculo": "colega de faculdade", "tempo_sem_contato": "desde a pandemia"}, '
    '"objetivo": "retomar", "objetivo_texto": "saber como andam os negócios dele", '
    '"meio": "pessoalmente", "registro": "proximo", '
    '"assunto_principal": "mercado de móveis e marcenaria no Sul", '
    '"interessa": ["negócios dele"], "evitar": ["política"], '
    '"termos_busca": ["indústria moveleira", "marcenaria Santa Catarina", "preço da madeira", '
    '"exportação de móveis"], '
    '"continuacao": false, "confianca": 0.9}'
)


def _linha_contato(nome: str, empresa: str | None, cargo: str | None) -> str:
    detalhes = ", ".join(parte for parte in (cargo, empresa) if parte)
    return f"- {nome}" + (f" ({detalhes})" if detalhes else "")


def construir_prompt(frase: str, contatos_conhecidos: list[tuple[str, str | None, str | None]]) -> str:
    lista_contatos = (
        "\n".join(_linha_contato(n, e, c) for n, e, c in contatos_conhecidos)
        if contatos_conhecidos
        else "(nenhum contato conhecido)"
    )
    lista_exemplo = "\n".join(_linha_contato(n, e, c) for n, e, c in _EXEMPLO_CONTATOS)

    return f"""\
Você lê um pedido que o usuário escreveu em texto livre, sobre uma pessoa (ou um
grupo) com quem vai conversar, e extrai o que ele quer. Responda só com um objeto
JSON, sem texto antes ou depois, sem raciocínio, com exatamente estes campos:

"pessoa_nome" — o nome da pessoa como o usuário escreveu, sem título (sem "Dr.",
"Sr."). Use "" se a frase não fala de uma pessoa (é um grupo ou um tema geral).
"pessoa_pistas" — objeto só com as chaves que aparecem na frase: "profissao",
"empresa", "cidade", "vinculo" (como o usuário conhece a pessoa),
"tempo_sem_contato", "link_rede_social". Nunca invente uma chave.
"objetivo" — um de: retomar, agradecer, pedir, manter, apresentar, responder, outro.
"objetivo_texto" — o objetivo nas palavras do usuário.
"meio" — um de: pessoalmente, telefone, whatsapp, carta, outro. Almoço, encontro e
reunião são "pessoalmente". Se a frase não diz, use "whatsapp".
"registro" — um de: proximo, cordial, formal, conforme o vínculo e o tom da frase.
Na dúvida, "cordial".
"assunto_principal" — sobre o que a conversa deve girar, em até dez palavras. Se o
usuário não disse, deduza da profissão ou do vínculo.
"interessa" — até 5 termos que o usuário quer na conversa.
"evitar" — termos que o usuário não quer.
"termos_busca" — de 3 a 6 termos para buscar notícia, que você mesmo deduz da
profissão, da empresa, do assunto e do que provavelmente está em pauta.
"continuacao" — true só se a frase indica que a conversa já começou ("ele
respondeu que...", "de novo"); senão false.
"confianca" — de 0 a 1, o quanto você tem certeza de ter entendido o pedido.

Se a pessoa do pedido for um dos contatos já conhecidos, escreva o nome como está
na lista.

Exemplo resolvido:
Contatos já conhecidos:
{lista_exemplo}
Pedido: <<<{_EXEMPLO_FRASE}>>>
JSON: {_EXEMPLO_SAIDA}

Contatos já conhecidos:
{lista_contatos}
Pedido: <<<{frase}>>>
JSON:
"""
