from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from agente_nw.nucleo.modelos.configuracao import NivelTema

OrigemTema = Literal["declarada", "sugerida", "importada", "captura", "imagem", "conversa"]


class PerfilTema(BaseModel):
    model_config = ConfigDict(frozen=True)

    perfil_id: int
    tema_id: int
    peso: int = Field(default=3, ge=1, le=5)
    origem: OrigemTema
    confirmado: bool = False
    nivel: NivelTema | None = None
    registrado_em: str
