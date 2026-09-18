from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TipoPerfil = Literal["usuario", "contato"]


class Perfil(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int | None = None
    tipo: TipoPerfil
    nome: str
    apelido: str | None = None
    email: str | None = None
    telefone: str | None = None
    empresa: str | None = None
    cargo: str | None = None
    setor: str | None = None
    cidade: str | None = None
    naturalidade: str | None = None
    linguas: list[str] = Field(default_factory=list)
    formacao: str | None = None
    tem_filhos: bool | None = None
    faixa_etaria: str | None = None
    notas: str | None = None
    ativo: bool = False
    gerar_agora: bool = False
    ultima_coleta: str | None = None
    criado_em: str
    atualizado_em: str
