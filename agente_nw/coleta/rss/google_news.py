from __future__ import annotations

from urllib.parse import quote

from agente_nw.nucleo.modelos.configuracao import FeedFonte
from agente_nw.nucleo.modelos.contexto_consulta import ContextoConsulta
from agente_nw.nucleo.modelos.tema import Tema
from agente_nw.nucleo.texto import sem_acento_e_caixa

_MAXIMO_TERMOS_POR_TEMA = 4
_MAXIMO_INTERESSA = 5
_MAXIMO_TERMOS_CONTATO = 3
_MAXIMO_TERMOS_BUSCA = 6
_MAXIMO_CONSULTAS_PADRAO = 4


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


def normalizar_termo(termo: str) -> str:
    """Chave de um termo de busca: sem acento, sem caixa, sem espaços repetidos."""
    return " ".join(sem_acento_e_caixa(termo).split())


def selecionar_termos(
    contexto: ContextoConsulta, termos_contato: list[str], maximo: int
) -> list[tuple[str, str]]:
    """Os termos de busca do pedido como (rótulo, termo), sem repetição entre as origens e no máximo
    `maximo`. Prioridade: assunto, termos do contato (o produto vale pelo que ele publica),
    `termos_busca` do pedido e `interessa`."""
    origens = (
        ("consulta", [contexto.assunto]),
        ("contato", termos_contato[:_MAXIMO_TERMOS_CONTATO]),
        ("busca", contexto.termos_busca[:_MAXIMO_TERMOS_BUSCA]),
        ("interessa", contexto.interessa[:_MAXIMO_INTERESSA]),
    )
    escolhidos: list[tuple[str, str]] = []
    vistos: set[str] = set()
    for rotulo, termos in origens:
        for termo in termos:
            chave = normalizar_termo(termo)
            if not chave or chave in vistos:
                continue
            vistos.add(chave)
            escolhidos.append((rotulo, " ".join(termo.split())))
    return escolhidos[:maximo]


def feed_do_termo(termo: str) -> FeedFonte:
    """Busca do Google News por frase exata, para um termo já escolhido por `selecionar_termos`."""
    return _feed_de_termo("pedido", termo)


def gerar_consultas_da_consulta(
    contexto: ContextoConsulta, termos_contato: list[str], maximo: int = _MAXIMO_CONSULTAS_PADRAO
) -> list[FeedFonte]:
    """Uma busca por termo escolhido (assunto, contato, termos de busca e interessa, sem repetição e até
    `maximo`)."""
    termos = selecionar_termos(contexto, termos_contato, maximo)
    return [_feed_de_termo(rotulo, termo) for rotulo, termo in termos]
