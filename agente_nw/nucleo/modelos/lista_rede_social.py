from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class EntradaLista(BaseModel):
    """Uma pessoa da lista do próprio usuário numa rede (conexão, seguido, amigo)."""

    model_config = ConfigDict(frozen=True)

    rede: str
    nome: str
    cabecalho: str = ""
    link: str
    foto_url: str | None = None


class EntradaGravada(EntradaLista):
    id: int
    lido_em: str
    perfil_id: int | None = None
