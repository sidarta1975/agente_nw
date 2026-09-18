from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

StatusAssunto = Literal["novo", "em_curso", "encerrado"]


class Assunto(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int | None = None
    titulo_gerado: str | None = None
    primeiro_visto: str
    ultimo_visto: str
    n_itens: int = 0
    n_fontes_independentes: int = 0
    status: StatusAssunto
    temas: list[int] = Field(default_factory=list)
    substancial: float | None = None
    conversavel: float | None = None
    justificativa: str | None = None
    resumo_cartao: str | None = None
