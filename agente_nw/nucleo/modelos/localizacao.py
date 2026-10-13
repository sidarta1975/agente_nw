from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

FonteOpcao = Literal["lista", "busca_geral", "link_colado"]
StatusLocalizacao = Literal["claro", "ambiguo", "nenhum"]


@dataclass(frozen=True)
class Opcao:
    """Uma pessoa candidata a ser o contato, numa rede."""

    rede: str
    nome: str
    cabecalho: str
    link: str
    fonte: FonteOpcao
    foto_url: str | None = None


@dataclass
class Localizacao:
    status: StatusLocalizacao
    escolhido: Opcao | None = None
    opcoes: list[Opcao] = field(default_factory=list)  # todas, da mais para a menos provável
    fonte: str = "lista"  # "lista" ou "busca_geral"
    avisos: list[str] = field(default_factory=list)
    rede: str | None = None  # quando a localização é de uma rede só (curadoria por rede)


class RespostaDesempate(BaseModel):
    """Tarefa `desempatar_perfil`. `indice_escolhido` conta a partir de 1; null = nenhum serve."""

    model_config = ConfigDict(frozen=True)

    indice_escolhido: int | None = None
    confianca: float = Field(ge=0, le=1)
    motivo: str
