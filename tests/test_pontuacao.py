from __future__ import annotations

import math

import pytest

from agente_nw.nucleo.modelos.configuracao import ConectorLimiares
from agente_nw.nucleo.relevancia.pontuacao import avaliar

_CENTROIDE_ASSUNTO = [1.0, 0.0]
_PESO_NIVEL = {"dominio": 1.0, "interesse": 0.7, "curiosidade": 0.4}


@pytest.fixture
def limiares() -> ConectorLimiares:
    return ConectorLimiares(
        adjacencia_minima=0.55,
        conversavel_viavel=0.8,
        peso_aderencia_contato=50,
        peso_aderencia_usuario=30,
        peso_conversavel=20,
        peso_nivel=_PESO_NIVEL,
        candidatos_por_contato=10,
        itens_no_menu=5,
    )


def _vetor(cosseno_alvo: float) -> list[float]:
    return [cosseno_alvo, math.sqrt(max(1 - cosseno_alvo**2, 0.0))]


_CASOS = [
    (0.70, [("dominio1", "dominio", 0.60)], 0.50, "conector"),
    (0.40, [("interesse1", "interesse", 0.90)], 0.20, "conector"),
    (0.55, [("dominio1", "dominio", 0.55)], 0.60, "conector"),
    (0.80, [("dominio1", "dominio", 0.70), ("curiosidade1", "curiosidade", 0.95)], 0.40, "conector"),
    (0.50, [("curiosidade1", "curiosidade", 0.60)], 0.30, "viavel_com_esforco"),
    (0.30, [("dominio1", "dominio", 0.40)], 0.85, "viavel_com_esforco"),
    (0.20, [], 0.90, "viavel_com_esforco"),
    (0.60, [("interesse1", "interesse", 0.54)], 0.79, "fora_do_dominio"),
    (0.10, [("dominio1", "dominio", 0.20)], 0.10, "fora_do_dominio"),
    (0.50, [("curiosidade1", "curiosidade", 0.45)], 0.50, "fora_do_dominio"),
    (0.90, [], 0.30, "fora_do_dominio"),
    (0.0, [("dominio1", "dominio", 0.0)], 0.0, "fora_do_dominio"),
]


@pytest.mark.parametrize("indice", range(1, 13))
def test_doze_casos_da_secao_6(indice: int, limiares: ConectorLimiares) -> None:
    aderencia_contato_alvo, temas_brutos, conversavel, tipo_esperado = _CASOS[indice - 1]

    centroide_contato = _vetor(aderencia_contato_alvo)
    temas_usuario = [(nome, nivel, _vetor(c)) for nome, nivel, c in temas_brutos]

    resultado = avaliar(_CENTROIDE_ASSUNTO, centroide_contato, temas_usuario, conversavel, limiares)

    assert resultado.tipo == tipo_esperado, f"caso {indice}: esperado {tipo_esperado}, veio {resultado.tipo}"


def test_caso_5_ponto_de_apoio_e_o_tema_de_curiosidade(limiares: ConectorLimiares) -> None:
    centroide_contato = _vetor(0.50)
    temas_usuario = [("curiosidade1", "curiosidade", _vetor(0.60))]

    resultado = avaliar(_CENTROIDE_ASSUNTO, centroide_contato, temas_usuario, 0.30, limiares)

    assert resultado.tipo == "viavel_com_esforco"
    assert resultado.ponto_de_apoio == "curiosidade1"


def test_caso_6_viavel_por_conversabilidade_nao_tem_ponto_de_apoio_de_tema(
    limiares: ConectorLimiares,
) -> None:
    centroide_contato = _vetor(0.30)
    temas_usuario = [("dominio1", "dominio", _vetor(0.40))]

    resultado = avaliar(_CENTROIDE_ASSUNTO, centroide_contato, temas_usuario, 0.85, limiares)

    assert resultado.tipo == "viavel_com_esforco"
    assert resultado.ponto_de_apoio is None
