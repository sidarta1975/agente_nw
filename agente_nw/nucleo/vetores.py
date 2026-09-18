from __future__ import annotations

from collections.abc import Sequence

import numpy as np


def cosseno(a: Sequence[float], b: Sequence[float]) -> float:
    vetor_a = np.asarray(a, dtype=np.float64)
    vetor_b = np.asarray(b, dtype=np.float64)

    norma_a = float(np.linalg.norm(vetor_a))
    norma_b = float(np.linalg.norm(vetor_b))
    if norma_a == 0.0 or norma_b == 0.0:
        return 0.0

    return float(np.dot(vetor_a, vetor_b) / (norma_a * norma_b))


def centroide(vetores: Sequence[Sequence[float]], pesos: Sequence[float] | None = None) -> list[float]:
    if not vetores:
        raise ValueError("centroide de lista vazia é indefinido")

    matriz = np.asarray(vetores, dtype=np.float64)
    if pesos is None:
        pesos_array = np.ones(len(vetores), dtype=np.float64)
    else:
        pesos_array = np.asarray(pesos, dtype=np.float64)

    media_ponderada = np.average(matriz, axis=0, weights=pesos_array)
    return [float(valor) for valor in media_ponderada]
