from __future__ import annotations

import sqlite3
from typing import Protocol, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from agente_nw.nucleo import sensivel
from agente_nw.nucleo.database.queries import fatos
from agente_nw.nucleo.llm import FalhaJsonInvalido

_EsquemaT = TypeVar("_EsquemaT", bound=BaseModel)

MAXIMO_TERMOS = 3
_FATOS_LIDOS = 30
_FATOS_NO_PROMPT = 12
_CARACTERES_POR_FATO = 300
_MAXIMO_PALAVRAS_DO_TERMO = 5
_TIPO_LISTA = "lista_rede_social"


class RespostaTermos(BaseModel):
    """Tarefa `extrair_termos_contato`: assuntos que o contato publica, prontos para busca de notícia."""

    model_config = ConfigDict(frozen=True)

    termos: list[str] = Field(default_factory=list)


class ClienteTermos(Protocol):
    def gerar_json(self, tarefa: str, prompt: str, esquema: type[_EsquemaT]) -> _EsquemaT: ...


def construir_prompt(publicacoes: list[str]) -> str:
    itens = "\n".join(f"- {texto}" for texto in publicacoes)
    return f"""\
Abaixo estão publicações recentes de uma pessoa nas redes sociais dela (texto e descrições
de imagens). Diga sobre quais ASSUNTOS ela publica, para buscar notícias que lhe interessem.
Devolva de 1 a {MAXIMO_TERMOS} termos de busca de notícia, cada um com 2 a {_MAXIMO_PALAVRAS_DO_TERMO}
palavras, em português, sobre temas profissionais, esportes, hobbies, viagens e lugares,
tecnologia ou mercado.

Não use nomes de pessoas. Não use saúde, religião, posição política, sindicato, vida sexual,
origem racial nem menores de idade. Se nada servir, devolva a lista vazia.

Responda só com um objeto JSON, sem texto antes ou depois:
{{"termos": ["...", "..."]}}

Publicações:
{itens}
"""


def termos_do_contato(cliente_llm: ClienteTermos, conexao: sqlite3.Connection, perfil_id: int) -> list[str]:
    """Termos de busca de notícia tirados do que o contato publica (fatos já gravados), ou lista vazia
    se não há fatos ou o modelo falha. Nunca lança para o chamador."""
    registros = [
        f
        for f in fatos.listar_recentes(conexao, perfil_id, _FATOS_LIDOS)
        if f.tipo != _TIPO_LISTA and f.conteudo.strip()
    ]
    publicacoes = [f.conteudo.strip()[:_CARACTERES_POR_FATO] for f in registros[:_FATOS_NO_PROMPT]]
    if not publicacoes:
        return []
    try:
        prompt = construir_prompt(publicacoes)
        resposta = cliente_llm.gerar_json("extrair_termos_contato", prompt, RespostaTermos)
    except FalhaJsonInvalido:
        return []
    termos: list[str] = []
    for bruto in resposta.termos:
        termo = " ".join(bruto.split())
        if not termo or len(termo.split()) > _MAXIMO_PALAVRAS_DO_TERMO:
            continue
        if sensivel.verificar(termo) is not None or termo.lower() in (t.lower() for t in termos):
            continue
        termos.append(termo)
    return termos[:MAXIMO_TERMOS]
