from __future__ import annotations

import re
import urllib.parse
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Protocol

_MIN_CHARS_AUTENTICADO = 500
_URL_LOGIN_SUBSTRINGS: tuple[str, ...] = (
    "/login",
    "/signin",
    "/sign-in",
    "/sign_in",
    "/accounts/login",
    "/session/new",
)


@dataclass(frozen=True)
class _ConfigRede:
    url_busca: str
    padrao_link_perfil: re.Pattern[str]


_CONFIG_BUSCA: dict[str, _ConfigRede] = {
    "linkedin": _ConfigRede(
        url_busca="https://www.linkedin.com/search/results/people/?keywords={query}",
        padrao_link_perfil=re.compile(r"linkedin\.com/in/[A-Za-z0-9\-_%]+/?"),
    ),
    "instagram": _ConfigRede(
        url_busca="https://www.instagram.com/explore/search/keyword/?q={query}",
        padrao_link_perfil=re.compile(r"instagram\.com/[A-Za-z0-9_.]+/?$"),
    ),
    "facebook": _ConfigRede(
        url_busca="https://www.facebook.com/search/people/?q={query}",
        padrao_link_perfil=re.compile(r"facebook\.com/(?:profile\.php\?id=\d+|[A-Za-z0-9.]+)/?$"),
    ),
    "x": _ConfigRede(
        url_busca="https://x.com/search?q={query}&f=user",
        padrao_link_perfil=re.compile(r"^https?://(?:www\.)?x\.com/[A-Za-z0-9_]+/?$"),
    ),
}

REDES_SUPORTADAS: tuple[str, ...] = tuple(sorted(_CONFIG_BUSCA.keys()))


def redes_automaticas(so_por_link: Iterable[str] = ()) -> tuple[str, ...]:
    """Redes lidas e buscadas sozinhas: todas as suportadas, menos as que `listas.redes_so_por_link`
    (limiares.yaml) deixa só por link colado. Vazio por padrão."""
    excluidas = set(so_por_link)
    return tuple(r for r in REDES_SUPORTADAS if r not in excluidas)


class PaginaBusca(Protocol):
    """Superfície que o algoritmo de busca consome. O backend real (extensão do Chrome)
    implementa este protocolo com `coletar_links` além dos métodos que a leitura
    (brief 017) já usava; testes injetam um fake."""

    def ir_para(self, url: str) -> None: ...
    def estado(self) -> tuple[str, str]: ...
    def coletar_links(self) -> list[tuple[str, str]]: ...
    def fechar(self) -> None: ...


@dataclass
class Candidato:
    nome_exibido: str
    descricao: str
    link: str


@dataclass
class ResultadoBusca:
    autenticado: bool
    motivo: str | None
    candidatos: list[Candidato] = field(default_factory=list)


def _parece_pagina_de_login(url: str, texto: str) -> bool:
    url_baixa = url.lower()
    if any(marca in url_baixa for marca in _URL_LOGIN_SUBSTRINGS):
        return True
    return len(texto.strip()) < _MIN_CHARS_AUTENTICADO


def _construir_query(nome: str, empresa: str | None, refino: str | None = None) -> str:
    """Nome mais a empresa; sem empresa, mais o `refino` (profissão que o usuário informou)."""
    for complemento in (empresa, refino):
        if complemento and complemento.strip():
            return f"{nome} {complemento}".strip()
    return nome.strip()


def _filtrar_candidatos(rede: str, links: list[tuple[str, str]]) -> list[Candidato]:
    from agente_nw.coleta.capturas import listas  # import tardio: listas importa este módulo

    padrao = _CONFIG_BUSCA[rede].padrao_link_perfil
    vistos: set[str] = set()
    candidatos: list[Candidato] = []
    for href, texto_container in links:
        if not padrao.search(href) or not listas.eh_perfil(rede, href):
            continue
        chave = href.split("?")[0].rstrip("/")
        if chave in vistos:
            continue
        vistos.add(chave)
        linhas = [linha.strip() for linha in texto_container.split("\n") if linha.strip()]
        nome_exibido = linhas[0] if linhas else ""
        if not nome_exibido:
            continue  # link sem texto (ícone, menu): não é uma pessoa para o usuário escolher
        descricao = " · ".join(linhas[1:5]) if len(linhas) > 1 else ""
        candidatos.append(Candidato(nome_exibido=nome_exibido, descricao=descricao, link=href))
    return candidatos


def buscar(
    pagina: PaginaBusca, rede: str, nome: str, empresa: str | None = None, refino: str | None = None
) -> ResultadoBusca:
    """Abre a busca nativa da rede social pelo nome do contato (opcionalmente
    refinada por empresa ou, na falta dela, por `refino`) e devolve os candidatos que aparecem
    no resultado. Se a busca refinada não achar ninguém, repete só com o nome.

    Não decide por nenhum — a confirmação humana continua obrigatória. Se a
    sessão não estiver logada, devolve `autenticado=False` com motivo, sem
    tentar logar e sem lançar."""
    if rede not in _CONFIG_BUSCA:
        return ResultadoBusca(autenticado=False, motivo=f"rede '{rede}' sem template de busca")

    config = _CONFIG_BUSCA[rede]
    consultas = [_construir_query(nome, empresa, refino)]
    if consultas[0] != nome.strip():
        consultas.append(nome.strip())
    candidatos: list[Candidato] = []
    for query in consultas:
        url = config.url_busca.format(query=urllib.parse.quote_plus(query))
        pagina.ir_para(url)
        url_atual, texto = pagina.estado()
        if _parece_pagina_de_login(url_atual, texto):
            resumo = " ".join(texto.split())[:120]
            return ResultadoBusca(
                autenticado=False,
                motivo=(
                    f"sem sessão ativa em {rede} — entre na rede no seu Chrome e repita "
                    f'(a aba estava em {url_atual}: "{resumo}")'
                ),
            )
        candidatos = _filtrar_candidatos(rede, pagina.coletar_links())
        if candidatos:
            break
    return ResultadoBusca(autenticado=True, motivo=None, candidatos=candidatos)
