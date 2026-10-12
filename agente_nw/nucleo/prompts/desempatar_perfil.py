from __future__ import annotations

from agente_nw.nucleo.modelos.localizacao import RespostaDesempate

ESQUEMA = RespostaDesempate

# Cenário do exemplo deliberadamente distante de qualquer entrada real de teste (armadilha 24).
_EXEMPLO_NOME = "Ivo"
_EXEMPLO_PISTAS = {"profissao": "luthier", "cidade": "Cremona"}
_EXEMPLO_CABECALHOS = [
    "Gerente de contas · Banco do Vale",
    "Construtor de violinos e violas · Ateliê Cremona",
    "Estudante de arquitetura",
]
_EXEMPLO_SAIDA = (
    '{"indice_escolhido": 2, "confianca": 0.9, '
    '"motivo": "construtor de violinos é luthier e o ateliê fica em Cremona"}'
)


def _linhas(cabecalhos: list[str]) -> str:
    return "\n".join(f'{i}. "{c or "(sem cabeçalho)"}"' for i, c in enumerate(cabecalhos, start=1))


def _pistas(pistas: dict[str, str]) -> str:
    return "; ".join(f"{chave}: {valor}" for chave, valor in pistas.items()) or "(nenhuma)"


def construir_prompt(nome: str, pistas: dict[str, str], cabecalhos: list[str]) -> str:
    return f"""\
O usuário procura uma pessoa de nome "{nome}" nas próprias redes sociais e encontrou
várias com esse nome. Você recebe o que ele sabe sobre a pessoa (as pistas) e o
cabeçalho curto que a rede mostra de cada candidato, numerado. Escolha o candidato
que combina com as pistas. Se nenhum combina com segurança, devolva null.

Responda só com um objeto JSON, sem texto antes ou depois, no formato exato:
{{"indice_escolhido": número da linha (1, 2, ...) ou null, "confianca": 0 a 1, "motivo": "..."}}

Exemplo resolvido:
Nome: {_EXEMPLO_NOME}
Pistas: {_pistas(_EXEMPLO_PISTAS)}
Candidatos:
{_linhas(_EXEMPLO_CABECALHOS)}
JSON: {_EXEMPLO_SAIDA}

Nome: {nome}
Pistas: {_pistas(pistas)}
Candidatos:
{_linhas(cabecalhos)}
JSON:
"""
