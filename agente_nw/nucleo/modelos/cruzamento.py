from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class RespostaCruzarPorQue(BaseModel):
    model_config = ConfigDict(frozen=True)

    por_que: list[str]
