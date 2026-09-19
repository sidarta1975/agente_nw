from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class RespostaComparacaoPar(BaseModel):
    model_config = ConfigDict(frozen=True)

    mesmo_assunto: bool
