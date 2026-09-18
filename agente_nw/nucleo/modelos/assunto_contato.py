from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

TipoConector = Literal["conector", "viavel_com_esforco", "fora_do_dominio"]
StatusAssuntoContato = Literal["novo", "usado", "nao_serve", "descartado"]


class AssuntoContato(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int | None = None
    assunto_id: int
    perfil_id: int
    gerado_em: str
    tipo: TipoConector
    aderencia_contato: float
    aderencia_usuario: float
    conversavel: float
    score: float
    por_que: str | None = None
    status: StatusAssuntoContato
    motivo: str | None = None
