from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Proveniencia(BaseModel):
    """Quem gerou um registro (brief 066): o perfil de hardware ativo (`air16`/`pro48`), o modelo da
    tarefa e a versão do prompt (`VERSAO` do módulo em `nucleo/prompts/`; `None` quando a tarefa monta
    o prompt fora dali). Gravada nas colunas `gerado_por_*` das tabelas de resultado."""

    model_config = ConfigDict(frozen=True)

    modelo: str
    perfil: str
    prompt_versao: str | None = None


def colunas_gerado_por(proveniencia: Proveniencia | None) -> tuple[str | None, str | None, str | None]:
    """Valores de (`gerado_por_modelo`, `gerado_por_perfil`, `gerado_por_prompt_versao`); sem
    proveniência, as três ficam nulas."""
    if proveniencia is None:
        return (None, None, None)
    return (proveniencia.modelo, proveniencia.perfil, proveniencia.prompt_versao)
