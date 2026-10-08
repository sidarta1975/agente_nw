from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MeioContato = Literal["pessoalmente", "telefone", "whatsapp", "carta", "outro"]


class ContextoConsulta(BaseModel):
    """Contexto que o usuário informa ao pedir uma consulta sobre um contato.

    Serializado em `consulta_contato.contexto_json` (brief 015), inspecionável
    depois via `historico_recente_para_prompt` e usado para dar tom ao motor de
    cruzamento em briefs futuros — hoje é gravado mas o motor ainda não o lê.
    """

    model_config = ConfigDict(frozen=True)

    assunto: str
    meio: MeioContato
    objetivo: str
    interessa: list[str] = Field(default_factory=list)
    evitar: list[str] = Field(default_factory=list)
    livre: str = ""
