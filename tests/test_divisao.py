from __future__ import annotations

from agente_nw.nucleo.agrupamento.divisao import dividir


def test_dois_blocos_bem_separados_dividem_corretamente() -> None:
    vetores_itens = {
        1: [1.0, 0.0],
        2: [0.95, 0.05],
        3: [0.9, 0.1],
        4: [0.0, 1.0],
        5: [0.05, 0.95],
        6: [0.1, 0.9],
    }

    resultado = dividir(vetores_itens)

    assert resultado is not None
    grupo_a, grupo_b = resultado
    partes = {frozenset(grupo_a), frozenset(grupo_b)}
    assert partes == {frozenset({1, 2, 3}), frozenset({4, 5, 6})}


def test_todos_os_pontos_identicos_nao_separa() -> None:
    vetores_itens = {
        1: [0.5, 0.5],
        2: [0.5, 0.5],
        3: [0.5, 0.5],
        4: [0.5, 0.5],
    }

    assert dividir(vetores_itens) is None


def test_menos_de_dois_itens_nao_separa() -> None:
    assert dividir({1: [1.0, 0.0]}) is None
    assert dividir({}) is None
