from __future__ import annotations

import pytest

from agente_nw.nucleo.vetores import centroide, cosseno


def test_cosseno_vetores_iguais() -> None:
    assert cosseno([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == pytest.approx(1.0)


def test_cosseno_vetores_ortogonais() -> None:
    assert cosseno([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)


def test_cosseno_vetor_de_norma_zero_nao_quebra() -> None:
    assert cosseno([0.0, 0.0], [1.0, 2.0]) == 0.0
    assert cosseno([1.0, 2.0], [0.0, 0.0]) == 0.0


def test_centroide_com_pesos_iguais_bate_com_media_simples() -> None:
    resultado = centroide([[1.0, 1.0], [3.0, 3.0]], pesos=[1.0, 1.0])
    assert resultado == pytest.approx([2.0, 2.0])


def test_centroide_sem_pesos_usa_pesos_uniformes() -> None:
    resultado = centroide([[0.0, 0.0], [2.0, 4.0]])
    assert resultado == pytest.approx([1.0, 2.0])


def test_centroide_lista_vazia_levanta_erro() -> None:
    with pytest.raises(ValueError):
        centroide([])
