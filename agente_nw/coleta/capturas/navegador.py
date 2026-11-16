from __future__ import annotations

import random
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol

from agente_nw.coleta.capturas.imagens import ImagemCapturada

URL_LOGIN_SUBSTRINGS: tuple[str, ...] = (
    "/login",
    "/signin",
    "/sign-in",
    "/sign_in",
    "/accounts/login",
    "/session/new",
)
MIN_CHARS_AUTENTICADO = 500
_BLOCO_TAMANHO_MINIMO = 30  # abaixo disso é menu ou rótulo: descartado
_BLOCO_TAMANHO_MAXIMO = 5000  # acima disso o bloco é partido em pedaços, nunca descartado (brief 083)
_FIM_DE_FRASE = re.compile(r"[.!?…][\"')\]»”’]*\s+")
_MAX_ESPERAS_LOGIN = 0  # sem espera: o usuário já está logado no próprio Chrome (brief 044)
_ESPERA_LOGIN_S = 5.0
_MAX_ROLAGENS = 5
_INTERVALO_MIN_S = 4.0
_INTERVALO_MAX_S = 9.0


class Pagina(Protocol):
    """Superfície mínima da página de navegador que o algoritmo consome.

    O backend real (extensão do Chrome do usuário, em `extensao_backend.py`) implementa
    este protocolo; os testes injetam uma `Pagina` falsa para exercitar o algoritmo
    sem depender do navegador.
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
    imagens: list[ImagemCapturada] = field(default_factory=list)
    blocos_partidos: int = 0  # blocos acima de `_BLOCO_TAMANHO_MAXIMO` lidos em pedaços (brief 083)


def _chave_da_imagem(src: str) -> str:
    return src.split("?")[0]


def _capturar_imagens(
    pagina: Pagina, maximo: int, largura_minima: int, acumuladas: list[ImagemCapturada]
) -> None:
    """Pede à página (se ela lê imagens) as publicadas que ainda não vieram, até `maximo` no total."""
    leitura = getattr(pagina, "imagens", None)
    faltam = maximo - len(acumuladas)
    if leitura is None or faltam <= 0:
        return
    ignorar = [_chave_da_imagem(imagem.src) for imagem in acumuladas]
    try:
        novas = leitura(faltam, largura_minima, ignorar)
    except Exception:
        return
    vistas = set(ignorar)
    for imagem in novas:
        chave = _chave_da_imagem(imagem.src)
        if chave not in vistas and len(acumuladas) < maximo:
            vistas.add(chave)
            acumuladas.append(imagem)


def _parece_pagina_de_login(url: str, texto: str) -> bool:
    url_baixa = url.lower()
    if any(marca in url_baixa for marca in URL_LOGIN_SUBSTRINGS):
        return True
    return len(texto.strip()) < MIN_CHARS_AUTENTICADO


def _onde_cortar(trecho: str) -> int:
    """Fim do pedaço dentro de `trecho` (que tem o tamanho máximo do pedaço): depois do último fim de
    parágrafo; sem parágrafo, do último fim de frase; sem frase, do último espaço. Só um trecho sem
    espaço nenhum (uma "palavra" de 5.000 caracteres) é cortado no tamanho máximo."""
    posicao = trecho.rfind("\n")
    if posicao > 0:
        return posicao + 1
    frases = [fim.end() for fim in _FIM_DE_FRASE.finditer(trecho)]
    if frases:
        return frases[-1]
    espacos = [indice for indice, caractere in enumerate(trecho) if caractere.isspace()]
    if espacos and espacos[-1] > 0:
        return espacos[-1] + 1
    return len(trecho)


def partir_bloco(bloco: str, maximo: int = _BLOCO_TAMANHO_MAXIMO) -> list[str]:
    """Pedaços consecutivos de até `maximo` caracteres cuja concatenação é o `bloco`, cortados em fim de
    parágrafo, de frase ou de palavra (brief 083, P-014). Bloco que cabe volta inteiro, num pedaço só."""
    pedacos: list[str] = []
    inicio = 0
    while len(bloco) - inicio > maximo:
        fim = inicio + _onde_cortar(bloco[inicio : inicio + maximo])
        pedacos.append(bloco[inicio:fim])
        inicio = fim
    pedacos.append(bloco[inicio:])
    if "".join(pedacos) != bloco:
        raise ValueError("os pedaços não reproduzem o bloco")
    return pedacos


def _extrair_blocos(texto: str) -> list[list[str]]:
    """Blocos da página (separados por linha em branco), cada um como a lista dos seus pedaços: um
    pedaço só quando o bloco cabe em `_BLOCO_TAMANHO_MAXIMO`, vários quando foi partido. Só o bloco
    abaixo de `_BLOCO_TAMANHO_MINIMO` (menu, rótulo) é descartado."""
    partes = (parte.strip() for parte in re.split(r"\n\s*\n+", texto))
    return [partir_bloco(parte) for parte in partes if len(parte) >= _BLOCO_TAMANHO_MINIMO]


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
    maximo_imagens: int = 0,
    largura_minima_imagem: int = 250,
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
                motivo="sem sessão ativa — entre na rede no seu Chrome e repita",
                blocos=[],
            )

    blocos: list[str] = []
    vistos: set[str] = set()
    partidos = 0

    def _acumular(texto_pagina: str) -> None:
        nonlocal partidos
        for pedacos in _extrair_blocos(texto_pagina):
            novos = [pedaco for pedaco in pedacos if pedaco not in vistos]
            if len(pedacos) > 1 and novos:
                partidos += 1
            for pedaco in novos:
                vistos.add(pedaco)
                blocos.append(pedaco)

    imagens: list[ImagemCapturada] = []
    _acumular(texto)
    _capturar_imagens(pagina, maximo_imagens, largura_minima_imagem, imagens)

    for _ in range(max(0, max_rolagens - 1)):
        dorme(rnd.uniform(intervalo_min_s, intervalo_max_s))
        pagina.rolar()
        _url, texto = pagina.estado()
        _acumular(texto)
        _capturar_imagens(pagina, maximo_imagens, largura_minima_imagem, imagens)

    return CapturaBlocos(
        autenticado=True, motivo=None, blocos=blocos, imagens=imagens, blocos_partidos=partidos
    )
