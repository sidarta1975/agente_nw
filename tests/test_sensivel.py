from __future__ import annotations

import pytest

from agente_nw.nucleo.sensivel import verificar

FRASES_QUE_DEVEM_PASSAR = (
    "Trabalha com logística de cabotagem",
    "Gosta de corrida de rua, já fez duas maratonas",
    "Formado em engenharia civil pela Poli",
    "Mora em Santos, litoral de São Paulo",
    "Fala inglês e espanhol fluentes",
    "Sócio de uma empresa de tecnologia",
    "Gosta de vinho e de cozinha italiana",
    "Torce para o Corinthians",
    "Viajou para Portugal em 2025",
    "Trabalha há cinco anos na mesma empresa",
    "Tem MBA em finanças pela FGV",
    "Gosta de fotografia de paisagem",
    "Pratica vela nos fins de semana",
    "Mudou de cargo recentemente, agora é diretor comercial",
    "Estudou na USP, no campus de São Carlos",
)

FRASES_QUE_DEVEM_SER_DESCARTADAS = (
    ("Tem diabetes tipo 2", "saude"),
    ("Está em tratamento para depressão", "saude"),
    ("Fez uma cirurgia de coluna recentemente", "saude"),
    ("É evangélico praticante", "religiao"),
    ("Frequenta um terreiro de umbanda", "religiao"),
    ("É filiado ao PT desde jovem", "politica"),
    ("Votou no Bolsonaro nas últimas eleições", "politica"),
    ("Milita pela causa de esquerda no trabalho", "politica"),
    ("É sindicalizado no sindicato da categoria", "sindicato"),
    ("Participou da greve geral do mês passado", "sindicato"),
    ("É homossexual assumido", "vida_sexual"),
    ("Comentou sobre a orientação sexual do primo", "vida_sexual"),
    ("É uma pessoa negra e fala sobre isso abertamente", "origem_racial"),
    ("Comentou sobre a própria etnia indígena", "origem_racial"),
    ("Tem uma filha de 9 anos que estuda perto do escritório", "menores"),
)


@pytest.mark.parametrize("frase", FRASES_QUE_DEVEM_PASSAR)
def test_frase_limpa_passa(frase: str) -> None:
    assert verificar(frase) is None


@pytest.mark.parametrize(("frase", "categoria_esperada"), FRASES_QUE_DEVEM_SER_DESCARTADAS)
def test_frase_sensivel_e_descartada_na_categoria_certa(frase: str, categoria_esperada: str) -> None:
    assert verificar(frase) == categoria_esperada
