from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class RespostaCruzarPorQue(BaseModel):
    model_config = ConfigDict(frozen=True)

    por_que: list[str]


class AvaliacaoRelacaoObjetivo(BaseModel):
    """Um candidato do gate (brief 049): o modelo julga se a notícia se liga ao objetivo do pedido."""

    model_config = ConfigDict(frozen=True)

    relaciona: bool
    motivo: str


class RespostaAvaliarRelacaoObjetivo(BaseModel):
    """Esquema do contrato `avaliar_relacao_objetivo` (brief 049)."""

    model_config = ConfigDict(frozen=True)

    avaliacoes: list[AvaliacaoRelacaoObjetivo]
