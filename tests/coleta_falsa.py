"""Rede falsa para os testes da coleta de notícias (brief 045): nenhum teste toca a internet."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote

import httpx

from agente_nw.coleta.rss import leitor
from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.modelos.configuracao import ColetaLimiares

_TEXTO = "Texto relevante e substancial da notícia. " * 20
PAGINA = f"<html><body><article>{_TEXTO}</article></body></html>"
GOOGLE = "news.google.com"
BING = "www.bing.com"


def limiares(**campos: Any) -> ColetaLimiares:
    base: dict[str, Any] = {
        "teaser_minimo_caracteres": 400,
        "dias_max_primeira_aparicao": 7,
        "retencao_texto_dias": 90,
        "intervalo_google_news_segundos": 0,
        "dias_alerta_feed_vazio": 2,
    }
    return ColetaLimiares.model_validate({**base, **campos})


def banco(tmp_path: Path) -> sqlite3.Connection:
    aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(aberta)
    return aberta


def feed_xml(itens: list[tuple[str, str]], dias_atras: int = 1) -> bytes:
    publicado = format_datetime(datetime.now(UTC) - timedelta(days=dias_atras))
    corpo = "".join(
        f"<item><title>{titulo}</title><link>{link}</link><pubDate>{publicado}</pubDate></item>"
        for titulo, link in itens
    )
    xml = f'<?xml version="1.0"?><rss version="2.0"><channel><title>F</title>{corpo}</channel></rss>'
    return xml.encode()


class RedeFalsa:
    """Google News e Bing News falsos. Cada busca devolve `por_busca` notícias com título e link
    derivados do termo; o modo de cada host liga o 503 ou o feed vazio."""

    def __init__(self, por_busca: int = 3) -> None:
        self.por_busca = por_busca
        self.google = "ok"  # ok | 503 | vazio
        self.bing = "ok"
        self.pedidos: list[str] = []  # host + caminho de cada pedido
        self.dias_atras = 1

    def cliente(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self._atender))

    def hosts(self) -> list[str]:
        return [pedido.split("/")[0] for pedido in self.pedidos]

    def buscas(self, host: str) -> list[str]:
        return [p for p in self.pedidos if p.startswith(host) and ("/rss/search" in p or "/news/search" in p)]

    def _atender(self, requisicao: httpx.Request) -> httpx.Response:
        url = requisicao.url
        self.pedidos.append(f"{url.host}{url.path}")
        if url.host == GOOGLE and url.path == "/rss/search":
            return self._feed(self.google, parse_qs(url.query.decode())["q"][0], "g", False)
        if url.host == BING and url.path == "/news/search":
            return self._feed(self.bing, parse_qs(url.query.decode())["q"][0], "b", True)
        return httpx.Response(200, text=PAGINA)

    def _feed(self, modo: str, termo: str, prefixo: str, via_bing: bool) -> httpx.Response:
        if modo == "503":
            return httpx.Response(503, text="Sorry...")
        if modo == "vazio":
            return httpx.Response(200, content=feed_xml([]))
        slug = quote(termo.strip('"').replace(" ", "-").lower(), safe="-")
        itens = []
        for n in range(self.por_busca):
            real = f"https://noticias.exemplo.com/{prefixo}-{slug}-{n}"
            link = real
            if via_bing:
                link = f"http://www.bing.com/news/apiclick.aspx?ref=FexRss&url={quote(real, safe='')}"
            itens.append((f"Notícia {prefixo} {slug} número {n} sobre o assunto", link))
        return httpx.Response(200, content=feed_xml(itens, self.dias_atras))


def agora_mais(minutos: float) -> datetime:
    return datetime.now(UTC) + timedelta(minutes=minutos)


def coletar(
    rede: RedeFalsa,
    conn: sqlite3.Connection,
    pasta: Path,
    termos: list[str],
    minutos: float = 0,
    **campos: Any,
) -> leitor.ResumoColeta:
    """Uma coleta do pedido (só as buscas dos `termos`), `minutos` à frente do relógio."""
    return leitor.coletar(
        conn,
        rede.cliente(),
        None,
        limiares(**campos),
        pasta / "PARE",
        termos=termos,
        agora=agora_mais(minutos),
    )
