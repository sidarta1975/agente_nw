from __future__ import annotations

import random
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol

_URL_LOGIN_SUBSTRINGS: tuple[str, ...] = (
    "/login",
    "/signin",
    "/sign-in",
    "/sign_in",
    "/accounts/login",
    "/session/new",
)
_MIN_CHARS_AUTENTICADO = 500
_BLOCO_TAMANHO_MINIMO = 30
_BLOCO_TAMANHO_MAXIMO = 5000
_MAX_ESPERAS_LOGIN = 36  # 36 × 5s = 3 min
_ESPERA_LOGIN_S = 5.0
_MAX_ROLAGENS = 5
_INTERVALO_MIN_S = 4.0
_INTERVALO_MAX_S = 9.0


class Pagina(Protocol):
    """Superfície mínima da página de navegador que o algoritmo consome.

    O backend real (Playwright, em `playwright_backend.py`) implementa este
    protocolo; os testes injetam uma `Pagina` falsa para exercitar o algoritmo
    sem depender do Chromium.
    """

    def ir_para(self, url: str) -> None: ...
    def estado(self) -> tuple[str, str]: ...  # (url_atual, texto_visivel)
    def rolar(self) -> None: ...
    def fechar(self) -> None: ...


@dataclass
class CapturaBlocos:
    autenticado: bool
    motivo: str | None
    blocos: list[str] = field(default_factory=list)


def _parece_pagina_de_login(url: str, texto: str) -> bool:
    url_baixa = url.lower()
    if any(marca in url_baixa for marca in _URL_LOGIN_SUBSTRINGS):
        return True
    return len(texto.strip()) < _MIN_CHARS_AUTENTICADO


def _extrair_blocos(texto: str) -> list[str]:
    partes = re.split(r"\n\s*\n+", texto)
    return [
        parte.strip()
        for parte in partes
        if _BLOCO_TAMANHO_MINIMO <= len(parte.strip()) <= _BLOCO_TAMANHO_MAXIMO
    ]


def ler(
    pagina: Pagina,
    url: str,
    dorme: Callable[[float], None] = time.sleep,
    aleatorio: random.Random | None = None,
    max_esperas_login: int = _MAX_ESPERAS_LOGIN,
    espera_login_s: float = _ESPERA_LOGIN_S,
    max_rolagens: int = _MAX_ROLAGENS,
    intervalo_min_s: float = _INTERVALO_MIN_S,
    intervalo_max_s: float = _INTERVALO_MAX_S,
) -> CapturaBlocos:
    """Fluxo genérico de leitura: abre `url` no `pagina`, aguarda login se preciso,
    rola no máximo `max_rolagens` vezes com intervalo aleatório entre rolagens e
    devolve os blocos de texto capturados. Nunca lança para o chamador — em caso
    de bloqueio de login, devolve `autenticado=False` com motivo."""
    rnd = aleatorio or random.Random()
    pagina.ir_para(url)
    url_atual, texto = pagina.estado()

    if _parece_pagina_de_login(url_atual, texto):
        entrou = False
        for _ in range(max_esperas_login):
            dorme(espera_login_s)
            url_atual, texto = pagina.estado()
            if not _parece_pagina_de_login(url_atual, texto):
                entrou = True
                break
        if not entrou:
            return CapturaBlocos(
                autenticado=False,
                motivo="sem sessão ativa e prazo de login esgotou",
                blocos=[],
            )

    blocos: list[str] = []
    vistos: set[str] = set()

    def _acumular(texto_pagina: str) -> None:
        for bloco in _extrair_blocos(texto_pagina):
            if bloco not in vistos:
                vistos.add(bloco)
                blocos.append(bloco)

    _acumular(texto)

    for _ in range(max(0, max_rolagens - 1)):
        dorme(rnd.uniform(intervalo_min_s, intervalo_max_s))
        pagina.rolar()
        _url, texto = pagina.estado()
        _acumular(texto)

    return CapturaBlocos(autenticado=True, motivo=None, blocos=blocos)
