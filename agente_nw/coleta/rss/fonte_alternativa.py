"""Fonte de notícia alternativa, sem chave, sem conta e sem nuvem: o RSS público do Bing News.

Entra quando o Google News está bloqueado (brief 045). Validada do IP do Pro em 14/10/2026: devolve
9 a 12 notícias por busca, com data, e ordenar por data (`qft=sortbydate`) traz as mais recentes. A busca
vai sem aspas: com aspas e `sortbydate` o Bing devolve a lista vazia. Os links passam pelo redirecionador
do Bing e levam a URL real no parâmetro `url`."""

from __future__ import annotations

from urllib.parse import parse_qs, quote, urlparse

from agente_nw.nucleo.modelos.configuracao import FeedFonte

HOST = "www.bing.com"
_CAMINHO_REDIRECIONADOR = "/news/apiclick.aspx"


def _url_bing(termo: str) -> str:
    return (
        f"https://{HOST}/news/search?q={quote(termo)}&format=rss&setlang=pt-BR&cc=BR&qft=sortbydate%3d%221%22"
    )


def feed_do_termo(termo: str) -> FeedFonte:
    return FeedFonte(
        nome=f"Bing News · pedido: {termo}",
        url=_url_bing(termo),
        tipo="agregador",
        confiabilidade=4,
    )


def url_real(link: str) -> str:
    """A URL da notícia dentro do link do redirecionador do Bing; qualquer outro link volta como veio."""
    partes = urlparse(link)
    if (partes.hostname or "").removeprefix("www.") != HOST.removeprefix("www."):
        return link
    if partes.path != _CAMINHO_REDIRECIONADOR:
        return link
    destino = parse_qs(partes.query).get("url")
    return destino[0] if destino else link
