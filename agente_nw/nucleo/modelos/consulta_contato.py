from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ConsultaContato(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int | None = None
    perfil_id: int
    criado_em: str
    contexto_json: str
    resumo_redes_sociais: str | None = None
    assuntos_entregues_json: str
