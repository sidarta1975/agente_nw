from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class RespostaRotulo(BaseModel):
    model_config = ConfigDict(frozen=True)

    titulo: str
