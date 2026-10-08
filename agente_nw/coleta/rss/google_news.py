from __future__ import annotations

from urllib.parse import quote

from agente_nw.nucleo.modelos.configuracao import FeedFonte
from agente_nw.nucleo.modelos.contexto_consulta import ContextoConsulta
from agente_nw.nucleo.modelos.tema import Tema

_MAXIMO_TERMOS_POR_TEMA = 4
_MAXIMO_INTERESSA = 5
_MAXIMO_TERMOS_CONTATO = 3


def _url_google_news(consulta: str) -> str:
    return f"https://news.google.com/rss/search?q={quote(consulta)}&hl=pt-BR&gl=BR&ceid=BR:pt-419"


def gerar_consultas(temas: list[Tema]) -> list[FeedFonte]:
    feeds = []
    for tema in temas:
        termos = [tema.nome, *tema.sinonimos][:_MAXIMO_TERMOS_POR_TEMA]
        consulta = " OR ".join(f'"{termo}"' for termo in termos)
        feeds.append(
            FeedFonte(
                nome=f"Google News · {tema.nome}",
                url=_url_google_news(consulta),
                tipo="agregador",
                confiabilidade=5,
            )
        )
    return feeds


def _feed_de_termo(rotulo: str, termo: str) -> FeedFonte:
    return FeedFonte(
        nome=f"Google News · {rotulo}: {termo}",
        url=_url_google_news(f'"{termo}"'),
        tipo="agregador",
        confiabilidade=5,
    )


def gerar_consultas_da_consulta(contexto: ContextoConsulta, termos_contato: list[str]) -> list[FeedFonte]:
    """Uma consulta para o assunto, uma por item de `interessa` (até 5) e uma por termo do contato (até 3)."""
    feeds = [_feed_de_termo("consulta", contexto.assunto)]
    feeds.extend(_feed_de_termo("interessa", termo) for termo in contexto.interessa[:_MAXIMO_INTERESSA])
    feeds.extend(_feed_de_termo("contato", termo) for termo in termos_contato[:_MAXIMO_TERMOS_CONTATO])
    return feeds
