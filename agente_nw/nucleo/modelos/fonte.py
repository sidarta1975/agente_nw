from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Fonte(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int | None = None
    nome: str
    url_feed: str
    dominio: str
    tipo: str
    confiabilidade: int = Field(default=5, ge=0, le=10)
    ativa: bool = True
