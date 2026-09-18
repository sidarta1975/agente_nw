from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Tema(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int | None = None
    nome: str
    descricao: str
    sinonimos: list[str] = Field(default_factory=list)
    criado_em: str
