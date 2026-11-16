"""Estimativa de tokens de um texto, sem tokenizador (brief 082).

Uma só fonte para as duas pontas que estimam: o corte por tamanho do prompt de redação
(`prompts/redigir_ganchos.cortar_por_tamanho`, que usa `estimar_tokens` sem mudança de comportamento)
e a conferência de janela do cliente de LLM (`nucleo/llm.py`, que usa `estimar_tokens_conservador`
para recusar, antes da chamada, o prompt que já se sabe que não cabe). A medida autoritativa é sempre
a que o modelo devolve depois da chamada; a estimativa só serve para não gastar uma chamada perdida."""

from __future__ import annotations

_TOKENS_POR_PALAVRA = 1.4
_CARACTERES_POR_TOKEN = 3


def estimar_tokens(texto: str) -> int:
    """Contagem aproximada: palavras × 1,4."""
    return int(len(texto.split()) * _TOKENS_POR_PALAVRA)


def estimar_tokens_conservador(texto: str) -> int:
    """O maior entre palavras × 1,4 e caracteres ÷ 3 (decisão 2.2 do brief 082): o 1,4 nunca foi
    conferido contra o tokenizador real, e texto de palavras longas ou sem espaço (URL, base64,
    lista colada) foge dele."""
    return max(estimar_tokens(texto), len(texto) // _CARACTERES_POR_TOKEN)
