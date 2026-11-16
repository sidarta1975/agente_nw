"""Estimativa de tokens de um texto, sem tokenizador (brief 082).

Uma só fonte para as duas pontas que estimam: o corte por tamanho do prompt de redação
(`prompts/redigir_ganchos.cortar_por_tamanho`, que usa `estimar_tokens` sem mudança de comportamento)
e a conferência de janela do cliente de LLM (`nucleo/llm.py`, que usa `estimar_tokens_conservador`
para recusar, antes da chamada, o prompt que já se sabe que não cabe). A medida autoritativa é sempre
a que o modelo devolve depois da chamada; a estimativa só serve para não gastar uma chamada perdida."""

from __future__ import annotations

# 2,0 tokens por palavra: medido no `qwen2.5:14b` com um prompt real de redação (brief 082, seção 3 do
# doc_082; razão real 2,001) e adotado no brief 098. Conservador de propósito: superestimar faz o cliente
# recusar cedo (erro visível); subestimar deixa o prompt estourar a janela sem aviso.
# Não medido no `qwen3:4b`.
_TOKENS_POR_PALAVRA = 2.0
_CARACTERES_POR_TOKEN = 3


def estimar_tokens(texto: str) -> int:
    """Contagem aproximada: palavras × 2,0."""
    return int(len(texto.split()) * _TOKENS_POR_PALAVRA)


def estimar_tokens_conservador(texto: str) -> int:
    """O maior entre palavras × 2,0 e caracteres ÷ 3 (decisão 2.2 do brief 082): o fator por palavra é
    uma média, e texto de palavras longas ou sem espaço (URL, base64,
    lista colada) foge dele."""
    return max(estimar_tokens(texto), len(texto) // _CARACTERES_POR_TOKEN)
