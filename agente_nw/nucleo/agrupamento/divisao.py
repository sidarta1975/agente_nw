from __future__ import annotations

from agente_nw.nucleo.vetores import centroide, cosseno

_MAX_ITERACOES = 5


def dividir(vetores_itens: dict[int, list[float]]) -> tuple[list[int], list[int]] | None:
    ids = list(vetores_itens.keys())
    if len(ids) < 2:
        return None

    semente_a: int | None = None
    semente_b: int | None = None
    menor_cosseno: float | None = None
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            c = cosseno(vetores_itens[ids[i]], vetores_itens[ids[j]])
            if menor_cosseno is None or c < menor_cosseno:
                menor_cosseno = c
                semente_a, semente_b = ids[i], ids[j]
    assert semente_a is not None and semente_b is not None

    centro_a = vetores_itens[semente_a]
    centro_b = vetores_itens[semente_b]
    grupo_a: list[int] = []
    grupo_b: list[int] = []

    for _ in range(_MAX_ITERACOES):
        novo_a: list[int] = []
        novo_b: list[int] = []
        for item_id in ids:
            vetor = vetores_itens[item_id]
            if cosseno(vetor, centro_a) >= cosseno(vetor, centro_b):
                novo_a.append(item_id)
            else:
                novo_b.append(item_id)

        if not novo_a or not novo_b:
            return None

        convergiu = novo_a == grupo_a and novo_b == grupo_b
        grupo_a, grupo_b = novo_a, novo_b
        if convergiu:
            break

        centro_a = centroide([vetores_itens[i] for i in grupo_a])
        centro_b = centroide([vetores_itens[i] for i in grupo_b])

    return (grupo_a, grupo_b)
