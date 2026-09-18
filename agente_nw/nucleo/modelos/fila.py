from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class FilaExtracao(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int | None = None
    perfil_id: int
    texto: str
    origem: str
    criado_em: str
    processado: bool = False
    erro: str | None = None


class FilaRevisao(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int | None = None
    tarefa: str
    entrada: str
    erro: str
    criado_em: str
    resolvido: bool = False
