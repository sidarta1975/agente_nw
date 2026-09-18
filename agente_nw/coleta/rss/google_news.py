from __future__ import annotations

from urllib.parse import quote

from agente_nw.nucleo.modelos.configuracao import FeedFonte
from agente_nw.nucleo.modelos.tema import Tema

_MAXIMO_TERMOS_POR_TEMA = 4


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
