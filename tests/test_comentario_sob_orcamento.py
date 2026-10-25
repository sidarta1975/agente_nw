from __future__ import annotations

from dataclasses import replace

from agente_nw.nucleo.prompts import redigir_ganchos as prompt
from tests.test_redacao_prompt import _entrada


def test_prompt_perto_do_limite_corta_o_historico_mas_mantem_a_nota_e_o_comentario() -> None:
    entrada = replace(
        _entrada(fatos=10, historico=3, palavras_por_linha=700),
        notas=["[2026-10-10] trocou de escritório"],
    )
    entrada = replace(
        entrada, historico=[*entrada.historico[:1], 'comentário do usuário: "só a primeira consulta fica"']
    )
    assert prompt.estimar_tokens(prompt.construir_prompt(entrada, limite_tokens=10**9)) > 6000

    texto = prompt.construir_prompt(entrada, limite_tokens=6000)

    assert "trocou de escritório" in texto
    assert "consulta 0:" in texto
    assert "só a primeira consulta fica" not in texto
    assert prompt.estimar_tokens(texto) < prompt.estimar_tokens(prompt.construir_prompt(entrada, 10**9))
