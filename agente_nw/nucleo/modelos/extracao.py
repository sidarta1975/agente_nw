from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CamposExtraidos(BaseModel):
    """Campos guiados da ficha que o modelo pode ter encontrado no texto livre.

    Mesmos nove campos guiados de ``perfil`` (`ARQUITETURA.md` seção 3) — nenhum
    campo fora deste conjunto é aceito pelo contrato.
    """

    model_config = ConfigDict(frozen=True)

    cidade: str | None = None
    naturalidade: str | None = None
    linguas: list[str] = Field(default_factory=list)
    formacao: str | None = None
    cargo: str | None = None
    setor: str | None = None
    empresa: str | None = None
    tem_filhos: bool | None = None
    faixa_etaria: str | None = None


class TagSugerida(BaseModel):
    model_config = ConfigDict(frozen=True)

    tag: str
    peso: int = Field(ge=1, le=5)
    trecho: str


class FatoDatado(BaseModel):
    model_config = ConfigDict(frozen=True)

    data: str | None = None
    tipo: str
    conteudo: str
    fonte: str | None = None


class RespostaExtracaoTexto(BaseModel):
    """Esquema do contrato ``extrair_de_texto`` (`ARQUITETURA.md` seção 4)."""

    model_config = ConfigDict(frozen=True)

    campos: CamposExtraidos = Field(default_factory=CamposExtraidos)
    tags_sugeridas: list[TagSugerida] = Field(default_factory=list)
    fatos_datados: list[FatoDatado] = Field(default_factory=list)
