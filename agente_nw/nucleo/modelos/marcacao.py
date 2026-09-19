from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

ResultadoMarcacao = Literal["usado", "nao_serve"]


class Marcacao(BaseModel):
    model_config = ConfigDict(frozen=True)

    ac_id: int
    resultado: ResultadoMarcacao
    motivo: str | None = None
