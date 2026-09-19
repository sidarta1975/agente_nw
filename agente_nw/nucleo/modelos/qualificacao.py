from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class RespostaQualificar(BaseModel):
    model_config = ConfigDict(frozen=True)

    substancial: float = Field(ge=0, le=1)
    conversavel: float = Field(ge=0, le=1)
    temas: list[str] = Field(default_factory=list)
    justificativa: str
