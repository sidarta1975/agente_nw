from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class RedeSocial(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int | None = None
    perfil_id: int
    rede: str
    link: str
    criado_em: str
