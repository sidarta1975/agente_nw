from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Fato(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int | None = None
    perfil_id: int
    data_do_fato: str | None = None
    tipo: str
    conteudo: str
    fonte: str | None = None
    registrado_em: str
