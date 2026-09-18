from __future__ import annotations

import hashlib
import re
import unicodedata
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import httpx

_PARAMETROS_RASTREIO = frozenset(
    {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "fbclid",
        "gclid",
        "igshid",
        "mc_cid",
        "mc_eid",
    }
)

_NAO_ALFANUMERICO = re.compile(r"[^a-z0-9]+")


def _remover_rastreio_e_ancora(url: str) -> str:
    partes = urlparse(url)
    query_filtrada = [
        (chave, valor)
        for chave, valor in parse_qsl(partes.query, keep_blank_values=True)
        if chave not in _PARAMETROS_RASTREIO
    ]
    nova_query = urlencode(query_filtrada)
    return urlunparse((partes.scheme, partes.netloc, partes.path, partes.params, nova_query, ""))


def url_canonica(cliente_http: httpx.Client, url: str) -> str:
    url_limpa = _remover_rastreio_e_ancora(url)

    try:
        resposta = cliente_http.get(url_limpa, follow_redirects=False, timeout=15.0)
    except httpx.HTTPError:
        return url_limpa

    if 300 <= resposta.status_code < 400 and "location" in resposta.headers:
        destino = httpx.URL(url_limpa).join(resposta.headers["location"])
        return _remover_rastreio_e_ancora(str(destino))

    return url_limpa


def hash_titulo(titulo: str) -> str:
    normalizado = unicodedata.normalize("NFKD", titulo.casefold())
    sem_acento = "".join(caractere for caractere in normalizado if not unicodedata.combining(caractere))
    apenas_alfanumerico = _NAO_ALFANUMERICO.sub(" ", sem_acento)
    compactado = " ".join(apenas_alfanumerico.split())
    return hashlib.sha256(compactado.encode("utf-8")).hexdigest()
