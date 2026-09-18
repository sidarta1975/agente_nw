from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Item(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int | None = None
    fonte_id: int
    url_canonica: str
    titulo: str
    texto: str | None = None
    publicado_em: str | None = None
    coletado_em: str
    hash_titulo: str
    assunto_id: int | None = None
