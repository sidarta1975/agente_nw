from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class RespostaCartao(BaseModel):
    model_config = ConfigDict(frozen=True)

    resumo: str
