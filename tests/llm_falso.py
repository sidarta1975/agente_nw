"""Proveniência dos clientes de LLM simulados nos testes (brief 066): o modelo de embedding com que os
vetores são gravados e lidos, e o perfil/modelo/versão de prompt que os registros gerados guardam."""

from __future__ import annotations

from agente_nw.nucleo.modelos.proveniencia import Proveniencia

MODELO_EMBEDDING = "bge-m3"


class ProvenienciaFalsa:
    modelo_embedding = MODELO_EMBEDDING

    def proveniencia(self, tarefa_nome: str, versao_prompt: str | None = None) -> Proveniencia:
        return Proveniencia(modelo=f"modelo-falso-{tarefa_nome}", perfil="teste", prompt_versao=versao_prompt)
