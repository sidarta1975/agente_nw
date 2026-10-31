from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Tema(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int | None = None
    nome: str
    descricao: str
    sinonimos: list[str] = Field(default_factory=list)
    criado_em: str


class RespostaDescreverTema(BaseModel):
    """O que o modelo devolve (tarefa `descrever_tema`, brief 040): uma descrição curta de um termo
    novo, para virar tema do usuário sem cadastro manual."""

    model_config = ConfigDict(frozen=True)

    descricao: str
    sinonimos: list[str] = Field(default_factory=list)
