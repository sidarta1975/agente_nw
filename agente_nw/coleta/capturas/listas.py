from __future__ import annotations

import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from agente_nw.coleta.capturas.busca import _parece_pagina_de_login
from agente_nw.nucleo.modelos.configuracao import ListasLimiares
from agente_nw.nucleo.modelos.lista_rede_social import EntradaLista

REDES_COM_USUARIO: tuple[str, ...] = ("instagram", "x")
_MAX_ESPERAS_LOGIN = 36  # 36 × 5s = 3 min, como na leitura de perfil (brief 017)
_ESPERA_LOGIN_S = 5.0
MAX_ESPERAS_LOGIN = _MAX_ESPERAS_LOGIN  # exposto para quem decide esperar ou não
_RODADAS_SEM_NOVIDADE = 3

_URL_LISTA: dict[str, str] = {
    "linkedin": "https://www.linkedin.com/mynetwork/invite-connect/connections/",
    "instagram": "https://www.instagram.com/{usuario}/following/",
    "x": "https://x.com/{usuario}/following",
    "facebook": "https://www.facebook.com/friends/list",
}
_URL_INICIAL: dict[str, str] = {
    "instagram": "https://www.instagram.com/",
    "x": "https://x.com/home",
}

# Caminhos de primeiro nível que não são perfis de pessoa.
_RESERVADOS_INSTAGRAM = frozenset(
    {
        "explore",
        "accounts",
        "p",
        "reel",
        "reels",
        "stories",
        "direct",
        "about",
        "legal",
        "web",
        "tv",
    }
)
_RESERVADOS_X = frozenset(
    {
        "home",
        "explore",
        "i",
        "notifications",
        "messages",
        "search",
        "settings",
        "compose",
        "login",
        "signup",
        "tos",
        "privacy",
        "hashtag",
        "intent",
        "share",
    }
)
_RESERVADOS_FACEBOOK = frozenset(
    {
        "friends",
        "watch",
        "marketplace",
        "groups",
        "events",
        "pages",
        "gaming",
        "stories",
        "reel",
        "login",
        "help",
        "policies",
        "privacy",
        "settings",
        "messages",
        "notifications",
        "bookmarks",
        "saved",
        "memories",
        "photo",
        "photos",
        "video",
        "videos",
        "public",
        "search",
        "reels",
    }
)

_PADRAO_LINKEDIN = re.compile(r"^https?://(?:[a-z]+\.)?linkedin\.com/in/[A-Za-z0-9\-_%]+/?$")
_PADRAO_FACEBOOK_ID = re.compile(r"^https?://(?:www\.)?facebook\.com/profile\.php\?id=\d+$")
_HANDLE_POR_REDE: dict[str, tuple[re.Pattern[str], frozenset[str]]] = {
    "instagram": (
        re.compile(r"^https?://(?:www\.)?instagram\.com/([A-Za-z0-9_.]+)/?$"),
        _RESERVADOS_INSTAGRAM,
    ),
    "x": (re.compile(r"^https?://(?:www\.)?(?:x|twitter)\.com/([A-Za-z0-9_]+)/?$"), _RESERVADOS_X),
    "facebook": (
        re.compile(r"^https?://(?:www\.)?facebook\.com/([A-Za-z0-9.]+)/?$"),
        _RESERVADOS_FACEBOOK,
    ),
}

# Linhas de botão/rótulo que a rede mostra junto do cartão e que não são nome nem cabeçalho.
_RUIDO = frozenset(
    {
        "message",
        "mensagem",
        "following",
        "seguindo",
        "follow",
        "seguir",
        "remove",
        "remover",
        "add friend",
        "adicionar",
        "friends",
        "amigos",
        "·",
        "•",
        "...",
        "mais",
    }
)
_RUIDO_PREFIXOS = (
    "connected on",
    "conectado",
    "conectada",
    "followed by",
    "seguido por",
    "mutual",
    "em comum",
)


class PaginaLista(Protocol):
    """Superfície que a leitura das listas consome (união do que `navegador.ler` e `busca.buscar` usam)."""

    def ir_para(self, url: str) -> None: ...
    def estado(self) -> tuple[str, str]: ...
    def rolar(self) -> None: ...
    def coletar_links(self) -> list[tuple[str, str]]: ...
    def fechar(self) -> None: ...


@dataclass
class ResultadoLista:
    autenticado: bool
    motivo: str | None
    entradas: list[EntradaLista] = field(default_factory=list)
    truncada: bool = False


def url_da_lista(rede: str, usuario: str | None) -> str | None:
    modelo = _URL_LISTA.get(rede)
    if modelo is None:
        return None
    if "{usuario}" in modelo:
        return modelo.format(usuario=usuario) if usuario else None
    return modelo


def _caminho_de_perfil(rede: str, href: str) -> bool:
    sem_ancora = href.split("#")[0]
    if rede == "facebook" and _PADRAO_FACEBOOK_ID.match(sem_ancora):
        return True
    sem_consulta = sem_ancora.split("?")[0]
    if rede == "linkedin":
        return bool(_PADRAO_LINKEDIN.match(sem_consulta))
    configuracao = _HANDLE_POR_REDE.get(rede)
    if configuracao is None:
        return False
    padrao, reservados = configuracao
    achado = padrao.match(sem_consulta)
    return achado is not None and achado.group(1).lower() not in reservados


def _chave_do_link(href: str) -> str:
    base = href if "profile.php" in href else href.split("?")[0]
    return base.rstrip("/")


def _linhas_uteis(texto: str) -> list[str]:
    linhas: list[str] = []
    for bruta in texto.split("\n"):
        linha = bruta.strip()
        baixa = linha.lower()
        if not linha or baixa in _RUIDO or baixa.startswith(_RUIDO_PREFIXOS):
            continue
        linhas.append(linha)
    return linhas


def parse_links(rede: str, links: list[tuple[str, str]]) -> list[EntradaLista]:
    """Função pura: de `[(href, texto do cartão)]` para as entradas da lista de uma rede.

    O mesmo link costuma aparecer mais de uma vez (foto e nome); vale o cartão de texto mais longo.
    A primeira linha útil é o nome; as seguintes (até 3) formam o cabeçalho. No Instagram o nome
    é o de exibição (segunda linha) e o @usuário vai para o cabeçalho."""
    melhores: dict[str, tuple[str, str]] = {}
    ordem: list[str] = []
    for href, texto in links:
        if not _caminho_de_perfil(rede, href):
            continue
        chave = _chave_do_link(href)
        if chave not in melhores:
            ordem.append(chave)
            melhores[chave] = (href, texto)
        elif len(texto) > len(melhores[chave][1]):
            melhores[chave] = (href, texto)

    entradas: list[EntradaLista] = []
    for chave in ordem:
        href, texto = melhores[chave]
        linhas = _linhas_uteis(texto)
        if not linhas:
            continue
        nome, cabecalho = linhas[0], linhas[1:4]
        if rede == "instagram" and len(linhas) > 1:
            # O Instagram mostra o @usuário primeiro e o nome de exibição em seguida.
            nome, cabecalho = linhas[1], [f"@{linhas[0].lstrip('@')}", *linhas[2:4]]
        entradas.append(EntradaLista(rede=rede, nome=nome, cabecalho=" · ".join(cabecalho), link=chave))
    return entradas


def parse_usuario_do_menu(rede: str, links: list[tuple[str, str]]) -> str | None:
    """Função pura: acha o usuário da conta logada no menu da página inicial (link rotulado "Perfil")."""
    for href, texto in links:
        if texto.strip().lower() in {"perfil", "profile"} and _caminho_de_perfil(rede, href):
            achado = re.search(r"\.com/([A-Za-z0-9_.]+)", href.split("?")[0])
            if achado:
                return achado.group(1)
    return None


def _esperar_login(
    pagina: PaginaLista, dorme: Callable[[float], None], max_esperas: int, espera_s: float
) -> bool:
    url, texto = pagina.estado()
    if not _parece_pagina_de_login(url, texto):
        return True
    for _ in range(max_esperas):
        dorme(espera_s)
        url, texto = pagina.estado()
        if not _parece_pagina_de_login(url, texto):
            return True
    return False


def _entrar_na_lista(
    pagina: PaginaLista,
    url: str,
    dorme: Callable[[float], None],
    max_esperas: int,
    espera_s: float,
) -> bool:
    """Abre a lista e espera o login, se preciso. Depois de um login a rede costuma mandar o usuário
    para o início; por isso, se houve espera, abre a lista de novo."""
    pagina.ir_para(url)
    url_atual, texto = pagina.estado()
    precisou_logar = _parece_pagina_de_login(url_atual, texto)
    if not _esperar_login(pagina, dorme, max_esperas, espera_s):
        return False
    if precisou_logar:
        pagina.ir_para(url)
    return True


def descobrir_usuario(
    pagina: PaginaLista,
    rede: str,
    dorme: Callable[[float], None] = time.sleep,
    max_esperas_login: int = _MAX_ESPERAS_LOGIN,
    espera_login_s: float = _ESPERA_LOGIN_S,
) -> str | None:
    inicial = _URL_INICIAL.get(rede)
    if inicial is None:
        return None
    pagina.ir_para(inicial)
    if not _esperar_login(pagina, dorme, max_esperas_login, espera_login_s):
        return None
    return parse_usuario_do_menu(rede, pagina.coletar_links())


def ler_lista(
    pagina: PaginaLista,
    rede: str,
    usuario: str | None,
    limiares: ListasLimiares,
    dorme: Callable[[float], None] = time.sleep,
    max_esperas_login: int = _MAX_ESPERAS_LOGIN,
    espera_login_s: float = _ESPERA_LOGIN_S,
) -> ResultadoLista:
    """Abre a lista do próprio usuário, espera o login se preciso e rola até o fim da lista, até
    `maximo_entradas` ou até três rodadas sem entrada nova. Nunca lança por falta de sessão."""
    url = url_da_lista(rede, usuario)
    if url is None:
        motivo = (
            f"usuário de {rede} desconhecido — informe em config/local.yaml (redes.{rede}.usuario)"
            if rede in REDES_COM_USUARIO
            else f"rede '{rede}' sem lista suportada"
        )
        return ResultadoLista(autenticado=False, motivo=motivo)

    sem_sessao = ResultadoLista(
        autenticado=False, motivo=f"sem sessão ativa em {rede} e prazo de login esgotou"
    )
    if not _entrar_na_lista(pagina, url, dorme, max_esperas_login, espera_login_s):
        return sem_sessao

    acumuladas: dict[str, EntradaLista] = {}
    sem_novidade = 0
    while len(acumuladas) < limiares.maximo_entradas and sem_novidade < _RODADAS_SEM_NOVIDADE:
        antes = len(acumuladas)
        try:
            links = pagina.coletar_links()
        except Exception:
            links = []
        for entrada in parse_links(rede, links):
            acumuladas.setdefault(entrada.link, entrada)
        sem_novidade = 0 if len(acumuladas) > antes else sem_novidade + 1
        if len(acumuladas) >= limiares.maximo_entradas:
            break
        dorme(limiares.pausa_rolagem_s)
        try:
            pagina.rolar()
        except Exception:
            # A página navegou no meio da rolagem (ex.: redirecionamento do login): confirma a
            # sessão e volta para a lista. O que já foi acumulado fica.
            if not _entrar_na_lista(pagina, url, dorme, max_esperas_login, espera_login_s):
                return sem_sessao

    entradas = list(acumuladas.values())
    truncada = len(entradas) > limiares.maximo_entradas
    return ResultadoLista(
        autenticado=True, motivo=None, entradas=entradas[: limiares.maximo_entradas], truncada=truncada
    )


@dataclass
class ResultadoAtualizacao:
    rede: str
    lida: bool
    usou_cache: bool
    total: int
    motivo: str | None = None


def resolver_usuario(
    rede: str,
    configurado: str | None,
    abrir_pagina: Callable[[Path], PaginaLista],
    pasta_navegador: Path,
    gravar_usuario: Callable[[str, str], None] | None,
    perguntar_usuario: Callable[[str], str | None] | None,
    dorme: Callable[[float], None] = time.sleep,
    max_esperas_login: int = _MAX_ESPERAS_LOGIN,
) -> str | None:
    """Usuário da conta do próprio usuário em `rede`: do local.yaml; senão lido da página inicial
    logada (e gravado no local.yaml); senão perguntado. Redes sem URL por usuário devolvem None."""
    if rede not in REDES_COM_USUARIO:
        return None
    if configurado:
        return configurado
    pagina = abrir_pagina(pasta_navegador / rede)
    try:
        achado = descobrir_usuario(pagina, rede, dorme=dorme, max_esperas_login=max_esperas_login)
    finally:
        pagina.fechar()
    if achado is None and perguntar_usuario is not None:
        resposta = perguntar_usuario(rede)
        achado = resposta.strip().lstrip("@") if resposta and resposta.strip() else None
    if achado is not None and gravar_usuario is not None:
        gravar_usuario(rede, achado)
    return achado
