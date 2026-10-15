from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, TypeVar

from pydantic import BaseModel, ConfigDict

from agente_nw.nucleo.llm import FalhaJsonInvalido

_EsquemaT = TypeVar("_EsquemaT", bound=BaseModel)


@dataclass(frozen=True)
class ImagemCapturada:
    """Imagem publicada na página, lida pela extensão. Só existe até ser descrita: nunca é gravada."""

    src: str
    alt: str
    link: str  # a publicação a que a imagem pertence (ou "")
    mime: str
    dados_base64: str


class RespostaDescricaoImagem(BaseModel):
    """Tarefa `descrever_imagem`. `descartar` = imagem sem nada que descrever."""

    model_config = ConfigDict(frozen=True)

    descartar: bool = False
    descricao: str = ""


class ClienteVisao(Protocol):
    def gerar_json(
        self, tarefa: str, prompt: str, esquema: type[_EsquemaT], imagens: list[str] | None = None
    ) -> _EsquemaT: ...


def construir_prompt(rede: str, alt: str) -> str:
    dica = f'\nO texto alternativo da imagem na rede é: "{alt}".' if alt.strip() else ""
    return f"""\
Esta é uma imagem publicada por uma pessoa numa rede social ({rede}). Descreva-a em português do Brasil,
de forma objetiva e detalhada, em 2 a 5 frases: o que aparece (lugar, objetos, atividade, clima da cena),
quantas pessoas há e o que fazem, e qualquer texto legível na imagem, transcrito. Não identifique
ninguém pelo rosto e não invente o que não se vê.{dica}

Se não houver nada que descrever (imagem em branco, ilegível ou só interface), devolva descartar=true e
descricao vazia.

Responda só com um objeto JSON, sem texto antes ou depois:
{{"descartar": bool, "descricao": "..."}}
"""


def descrever(cliente_llm: ClienteVisao, imagem: ImagemCapturada, rede: str) -> str | None:
    """Descrição da imagem em texto, ou `None` se o modelo descartou ou falhou. Nunca lança para o
    chamador."""
    prompt = construir_prompt(rede, imagem.alt)
    try:
        resposta = cliente_llm.gerar_json(
            "descrever_imagem", prompt, RespostaDescricaoImagem, imagens=[imagem.dados_base64]
        )
    except FalhaJsonInvalido:
        return None
    descricao = resposta.descricao.strip()
    if resposta.descartar or not descricao:
        return None
    return descricao
