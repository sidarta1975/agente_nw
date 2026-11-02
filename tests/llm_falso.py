"""Proveniência dos clientes de LLM simulados nos testes (brief 066): o modelo de embedding com que os
vetores são gravados e lidos, e o perfil/modelo/versão de prompt que os registros gerados guardam."""

from __future__ import annotations

import re

from agente_nw.nucleo.modelos.proveniencia import Proveniencia
from agente_nw.nucleo.prompts.seguranca import MARCADOR_FIM

MODELO_EMBEDDING = "bge-m3"


class ProvenienciaFalsa:
    modelo_embedding = MODELO_EMBEDDING

    def proveniencia(self, tarefa_nome: str, versao_prompt: str | None = None) -> Proveniencia:
        return Proveniencia(modelo=f"modelo-falso-{tarefa_nome}", perfil="teste", prompt_versao=versao_prompt)


def candidatos_do_prompt(prompt: str) -> list[str]:
    """Cada candidato numerado de `avaliar_relacao_objetivo` (um bloco por "N. ", que pode ter várias
    linhas desde que título e resumo entram cercados — brief 068)."""
    lista = prompt.rsplit("Candidatos:\n", 1)[1]
    return [bloco for bloco in re.split(r"(?m)^\d+\. ", lista) if bloco.strip()]


def quantidade_assuntos_do_prompt(prompt: str) -> int:
    """Quantos assuntos numerados o prompt de `cruzar_por_que` traz (título cercado, depois "— tipo:")."""
    return prompt.rsplit("Assuntos:\n", 1)[1].count(f"{MARCADOR_FIM} — tipo:")
