from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class DescarteSensivel(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int | None = None
    perfil_id: int | None = None
    origem_texto: str
    categoria: str
    registrado_em: str
