from __future__ import annotations

from agente_nw.nucleo.modelos.cruzamento import RespostaCruzarPorQue

ESQUEMA = RespostaCruzarPorQue

# Cenário do exemplo deliberadamente distante de qualquer entrada real de teste
# (armadilha 24, docs/PLAN.md). Dois assuntos no exemplo, de propósito — um só
# não ensinaria o modelo a fechar um item da lista e abrir o próximo. O "por quê"
# de cada exemplo cita literalmente o ponto de apoio dado, nunca inventa outro —
# é isso que o teste real (brief 009, critério de aceite 2) confirma contra saída
# real do modelo.
_EXEMPLO_APELIDO = "Marina"
_EXEMPLO_TEMAS_CONTATO = ["vela", "mercado imobiliário"]
_EXEMPLO_TEMAS_USUARIO = [("corrida de rua", "interesse"), ("direito tributário", "domínio")]
_EXEMPLO_ASSUNTOS = [
    ("Regata reúne 200 embarcações na Baía de Guanabara", "viavel_com_esforco", "corrida de rua"),
    ("Reforma tributária muda prazo de transição do ICMS", "conector", "direito tributário"),
]
_EXEMPLO_SAIDA = (
    '{"por_que": ['
    '"ela navega, e você também curte esporte de resistência como a corrida — dá pra puxar esse gancho", '
    '"é a área que você domina, e ela trabalha com imóveis — a transição do ICMS pode afetar o setor dela"'
    "]}"
)


def construir_prompt(
    apelido_ou_nome: str,
    temas_contato: list[str],
    temas_usuario_com_nivel: list[tuple[str, str]],
    assuntos: list[tuple[str, str, str | None]],
) -> str:
    lista_temas_contato = ", ".join(temas_contato) if temas_contato else "(nenhum)"
    lista_temas_usuario = (
        ", ".join(f"{nome} ({nivel})" for nome, nivel in temas_usuario_com_nivel)
        if temas_usuario_com_nivel
        else "(nenhum)"
    )
    lista_assuntos = "\n".join(
        f'{indice}. "{titulo}" — tipo: {tipo}, '
        f"ponto de apoio do usuário: {ponto_de_apoio or 'nenhum (só conversabilidade)'}"
        for indice, (titulo, tipo, ponto_de_apoio) in enumerate(assuntos, start=1)
    )

    lista_exemplo_temas_usuario = ", ".join(f"{nome} ({nivel})" for nome, nivel in _EXEMPLO_TEMAS_USUARIO)
    lista_exemplo_assuntos = "\n".join(
        f'{indice}. "{titulo}" — tipo: {tipo}, ponto de apoio do usuário: {ponto_de_apoio}'
        for indice, (titulo, tipo, ponto_de_apoio) in enumerate(_EXEMPLO_ASSUNTOS, start=1)
    )

    return f"""\
Você recebe o nome de um contato, os temas dele, os temas do usuário (com o
nível de cada um) e uma lista numerada de assuntos já escolhidos para esse
contato — cada um já com o tipo (conector ou viável com esforço) e o ponto de
apoio do usuário que justifica a escolha. Você escreve, para cada assunto
nessa ordem, uma frase curta de "por quê" esse assunto vale a pena puxar com
esse contato — citando o ponto de apoio dado, nunca inventando outro.

Responda só com um objeto JSON, sem texto antes ou depois, no formato exato,
com exatamente um "por_que" por assunto recebido, na mesma ordem:
{{"por_que": ["...", "..."]}}

Exemplo resolvido:
Contato: {_EXEMPLO_APELIDO}
Temas do contato: {", ".join(_EXEMPLO_TEMAS_CONTATO)}
Temas do usuário: {lista_exemplo_temas_usuario}
Assuntos:
{lista_exemplo_assuntos}
JSON: {_EXEMPLO_SAIDA}

Contato: {apelido_ou_nome}
Temas do contato: {lista_temas_contato}
Temas do usuário: {lista_temas_usuario}
Assuntos:
{lista_assuntos}
"""
