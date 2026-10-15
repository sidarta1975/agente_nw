from __future__ import annotations

import sqlite3
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

import feedparser
import httpx
import trafilatura
import yaml

from agente_nw.coleta.rss import fonte_alternativa, google_news
from agente_nw.coleta.rss.canonicalizar import hash_titulo, url_canonica
from agente_nw.coleta.rss.google_news import gerar_consultas, normalizar_termo
from agente_nw.coleta.rss.ruido import e_ruido
from agente_nw.nucleo.database.queries import fontes as queries_fontes
from agente_nw.nucleo.database.queries import itens as queries_itens
from agente_nw.nucleo.database.queries import sistema
from agente_nw.nucleo.database.queries import temas as queries_temas
from agente_nw.nucleo.modelos.configuracao import ColetaLimiares, FeedFonte, FontesArquivo
from agente_nw.nucleo.modelos.fonte import Fonte
from agente_nw.nucleo.modelos.item import Item

ETAPA_PROGRESSO = "coleta"
_CODIGOS_DE_BLOQUEIO = (429, 503)
_HOST_GOOGLE_NEWS = "news.google.com"
_HOSTS_COM_INTERVALO = (_HOST_GOOGLE_NEWS, fonte_alternativa.HOST)
_ultimo_acesso_por_host: dict[str, float] = {}

FonteUsada = str  # "google" | "alternativa" | "reaproveitada" | "nenhuma"


def _respeitar_intervalo(url: str, intervalo_s: float) -> None:
    """Pedidos aos agregadores de notícia (feeds, redirecionamentos e páginas) guardam o intervalo
    configurado: rajadas de centenas de pedidos fazem o site bloquear o IP."""
    host = next((h for h in _HOSTS_COM_INTERVALO if h in url), None)
    if host is None:
        return
    espera = intervalo_s - (time.monotonic() - _ultimo_acesso_por_host.get(host, 0.0))
    if espera > 0:
        time.sleep(espera)
    _ultimo_acesso_por_host[host] = time.monotonic()


@dataclass
class ResumoColeta:
    fontes_processadas: int = 0
    itens_novos: int = 0
    duplicados: int = 0
    descartados_ruido: int = 0
    alertas_feed_vazio: list[str] = field(default_factory=list)
    feeds_com_erro: list[str] = field(default_factory=list)
    bloqueio: str | None = None  # o site recusou por excesso de pedidos (429/503) nesta coleta
    google_bloqueado_ate: str | None = None  # ISO: o Google está em cooldown (agora ou de antes)
    feeds_em_cooldown: int = 0  # feeds que nem foram pedidos porque o host está em cooldown
    termos_reaproveitados: int = 0  # buscas do pedido que a coleta de poucas horas atrás já cobre
    usou_google: bool = False
    usou_alternativa: bool = False
    fonte_usada: FonteUsada = "nenhuma"
    tempo_segundos: float = 0.0
    tempo_esgotado: bool = False


@dataclass
class _ResultadoFeed:
    itens_novos: int | None  # None = o feed não pôde ser lido
    bloqueio: int | None = None  # código 429/503 quando o site recusou


def _carregar_fontes_arquivo(caminho: Path) -> FontesArquivo:
    dados = yaml.safe_load(caminho.read_text(encoding="utf-8")) or {}
    return FontesArquivo.model_validate(dados)


def _dominio(url: str) -> str:
    return urlparse(url).netloc


def _data_feedparser_para_iso(entrada: feedparser.FeedParserDict) -> str | None:
    estrutura = entrada.get("published_parsed") or entrada.get("updated_parsed")
    if estrutura is None:
        return None
    ano, mes, dia, hora, minuto, segundo = estrutura[:6]
    return datetime(ano, mes, dia, hora, minuto, segundo, tzinfo=UTC).isoformat()


def _bloqueado_ate(conexao_bd: sqlite3.Connection, host: str, agora: datetime) -> datetime | None:
    texto = sistema.bloqueio_ate(conexao_bd, host)
    if not texto:
        return None
    ate = datetime.fromisoformat(texto)
    return ate if ate > agora else None


def _registrar_bloqueio(
    conexao_bd: sqlite3.Connection,
    host: str,
    codigo: int,
    limiares: ColetaLimiares,
    resumo: ResumoColeta,
    agora: datetime,
    bloqueados: set[str],
) -> None:
    """Guarda no banco até quando o host fica sem receber pedido: atravessa pedidos e reinícios."""
    ate = agora + timedelta(minutes=limiares.cooldown_bloqueio_minutos)
    sistema.gravar_bloqueio(conexao_bd, host, ate.isoformat(), agora.isoformat())
    conexao_bd.commit()
    bloqueados.add(host)
    resumo.bloqueio = f"{host} respondeu {codigo}"
    if host == _HOST_GOOGLE_NEWS:
        resumo.google_bloqueado_ate = ate.isoformat()


def _host_em_cooldown(
    conexao_bd: sqlite3.Connection, host: str, agora: datetime, bloqueados: set[str], resumo: ResumoColeta
) -> bool:
    ate = _bloqueado_ate(conexao_bd, host, agora)
    if ate is None and host not in bloqueados:
        return False
    if ate is not None and host == _HOST_GOOGLE_NEWS:
        resumo.google_bloqueado_ate = ate.isoformat()
    return True


def _termo_recente(
    conexao_bd: sqlite3.Connection, chave: str, limiares: ColetaLimiares, agora: datetime
) -> bool:
    quando = sistema.termo_buscado_em(conexao_bd, chave)
    if quando is None or limiares.horas_reuso_termo <= 0:
        return False
    return agora - datetime.fromisoformat(quando) < timedelta(hours=limiares.horas_reuso_termo)


def _buscar_termo(
    conexao_bd: sqlite3.Connection,
    cliente_http: httpx.Client,
    limiares: ColetaLimiares,
    resumo: ResumoColeta,
    termo: str,
    agora: datetime,
    bloqueados: set[str],
) -> None:
    """Uma busca do pedido: Google; se o Google está em cooldown ou recusa agora, a fonte alternativa."""
    feeds = [(False, google_news.feed_do_termo(termo))]
    if limiares.usar_fonte_alternativa:
        feeds.append((True, fonte_alternativa.feed_do_termo(termo)))
    for alternativa, feed in feeds:
        host = _dominio(feed.url)
        if _host_em_cooldown(conexao_bd, host, agora, bloqueados, resumo):
            continue
        fonte = queries_fontes.obter_ou_criar(
            conexao_bd, feed.nome, feed.url, host, feed.tipo, feed.confiabilidade
        )
        conexao_bd.commit()
        assert fonte.id is not None
        _respeitar_intervalo(feed.url, limiares.intervalo_google_news_segundos)
        duplicados_antes = resumo.duplicados
        resultado = _processar_fonte(conexao_bd, cliente_http, fonte, limiares, resumo)
        if resultado.itens_novos is None:
            if resultado.bloqueio is not None:
                codigo = resultado.bloqueio
                _registrar_bloqueio(conexao_bd, host, codigo, limiares, resumo, agora, bloqueados)
            continue
        dia = agora.date().isoformat()
        queries_fontes.registrar_execucao(conexao_bd, fonte.id, dia, resultado.itens_novos)
        sistema.gravar_termo_buscado(conexao_bd, normalizar_termo(termo), agora.isoformat())
        conexao_bd.commit()
        resumo.fontes_processadas += 1
        if resultado.itens_novos == 0 and resumo.duplicados == duplicados_antes:
            return  # a fonte respondeu e não tinha nada: não conta como fonte das notícias
        if alternativa:
            resumo.usou_alternativa = True
        else:
            resumo.usou_google = True
        return


def _rotular_fonte(resumo: ResumoColeta, havia_termos: bool) -> FonteUsada:
    if resumo.usou_alternativa and resumo.google_bloqueado_ate is not None:
        return "alternativa"
    if resumo.usou_google:
        return "google"
    if resumo.usou_alternativa:
        return "alternativa"
    if havia_termos and resumo.termos_reaproveitados > 0:
        return "reaproveitada"
    return "nenhuma"


def coletar(
    conexao_bd: sqlite3.Connection,
    cliente_http: httpx.Client,
    caminho_fontes_yaml: Path | None,
    limiares: ColetaLimiares,
    caminho_sentinela: Path,
    feeds_extras: list[FeedFonte] | None = None,
    termos: list[str] | None = None,
    agora: datetime | None = None,
    avancar: Callable[[str], None] | None = None,
) -> ResumoColeta:
    """Coleta os feeds do arquivo, as buscas dos temas do usuário e as buscas do pedido (`termos`).

    Host que recusou por excesso de pedidos (429/503) fica em cooldown no banco e não recebe mais
    pedido até passar `cooldown_bloqueio_minutos`, nem em outro pedido nem depois de reiniciar. As buscas
    do pedido reaproveitam termo buscado há menos de `horas_reuso_termo`, caem no Bing quando o
    Google está bloqueado e param quando já há `candidatos_suficientes` notícias novas."""
    inicio = time.monotonic()
    avisar = avancar or (lambda _mensagem: None)
    resumo = ResumoColeta()
    momento = agora or datetime.now(UTC)
    hoje = momento.date().isoformat()
    bloqueados: set[str] = set()

    feeds_arquivo = (
        _carregar_fontes_arquivo(caminho_fontes_yaml).feeds if caminho_fontes_yaml is not None else []
    )
    temas_usuario = queries_temas.listar(conexao_bd)
    feeds_google_news = gerar_consultas(temas_usuario)

    fontes_no_banco: list[Fonte] = []
    for feed in [*feeds_arquivo, *feeds_google_news, *(feeds_extras or [])]:
        fonte = queries_fontes.obter_ou_criar(
            conexao_bd, feed.nome, feed.url, _dominio(feed.url), feed.tipo, feed.confiabilidade
        )
        fontes_no_banco.append(fonte)
    conexao_bd.commit()

    progresso = sistema.progresso_obter(conexao_bd, ETAPA_PROGRESSO)
    ultimo_id_processado = 0
    if progresso is not None and progresso["data_ciclo"] == hoje and progresso["ultimo_id"] is not None:
        ultimo_id_processado = int(progresso["ultimo_id"])

    fontes_a_processar = sorted(
        (fonte for fonte in fontes_no_banco if fonte.id is not None and fonte.id > ultimo_id_processado),
        key=lambda fonte: fonte.id or 0,
    )

    limite = inicio + limiares.tempo_maximo_segundos
    for fonte in fontes_a_processar:
        if caminho_sentinela.exists():
            break
        if time.monotonic() > limite:
            resumo.tempo_esgotado = True
            break
        assert fonte.id is not None

        host = _dominio(fonte.url_feed)
        if _host_em_cooldown(conexao_bd, host, momento, bloqueados, resumo):
            resumo.feeds_em_cooldown += 1  # não conta como processado: a coleta depois do cooldown tenta
            continue
        _respeitar_intervalo(fonte.url_feed, limiares.intervalo_google_news_segundos)

        resultado = _processar_fonte(conexao_bd, cliente_http, fonte, limiares, resumo)
        avisar(f"  {fonte.nome}: {resultado.itens_novos or 0} nova(s) · {time.monotonic() - inicio:.0f}s")
        if resultado.itens_novos is None:
            # Feed que falhou não conta como processado: a próxima coleta do dia tenta de novo.
            if resultado.bloqueio is not None:
                codigo = resultado.bloqueio
                _registrar_bloqueio(conexao_bd, host, codigo, limiares, resumo, momento, bloqueados)
            continue

        queries_fontes.registrar_execucao(conexao_bd, fonte.id, hoje, resultado.itens_novos)
        if queries_fontes.dois_dias_vazios(conexao_bd, fonte.id, hoje):
            resumo.alertas_feed_vazio.append(fonte.nome)

        sistema.progresso_gravar(conexao_bd, ETAPA_PROGRESSO, fonte.id, hoje, datetime.now(UTC).isoformat())
        conexao_bd.commit()
        resumo.fontes_processadas += 1

    for termo in termos or []:
        if caminho_sentinela.exists() or resumo.itens_novos >= limiares.candidatos_suficientes:
            break
        if time.monotonic() > limite:
            resumo.tempo_esgotado = True
            break
        if _termo_recente(conexao_bd, normalizar_termo(termo), limiares, momento):
            resumo.termos_reaproveitados += 1
            continue
        _buscar_termo(conexao_bd, cliente_http, limiares, resumo, termo, momento, bloqueados)
        avisar(f"  busca '{termo}': {resumo.itens_novos} nova(s) no total · {time.monotonic() - inicio:.0f}s")

    resumo.fonte_usada = _rotular_fonte(resumo, bool(termos))
    resumo.tempo_segundos = time.monotonic() - inicio
    return resumo


def _processar_fonte(
    conexao_bd: sqlite3.Connection,
    cliente_http: httpx.Client,
    fonte: Fonte,
    limiares: ColetaLimiares,
    resumo: ResumoColeta,
) -> _ResultadoFeed:
    """Itens novos do feed; `itens_novos=None` se o feed não pôde ser lido (e o código, se foi bloqueio)."""
    assert fonte.id is not None
    n_itens_novos_da_fonte = 0

    try:
        resposta_feed = cliente_http.get(fonte.url_feed, timeout=15.0)
        resposta_feed.raise_for_status()
        analisado = feedparser.parse(resposta_feed.content)
    except httpx.HTTPStatusError as erro:
        resumo.feeds_com_erro.append(fonte.nome)
        codigo = erro.response.status_code
        return _ResultadoFeed(None, codigo if codigo in _CODIGOS_DE_BLOQUEIO else None)
    except Exception:
        resumo.feeds_com_erro.append(fonte.nome)
        return _ResultadoFeed(None)

    for entrada in analisado.entries:
        titulo = str(entrada.get("title", "")).strip()
        link = entrada.get("link")
        if not titulo or not link:
            continue

        hash_do_titulo = hash_titulo(titulo)
        # O mesmo título aparece em várias buscas: checa pelo título antes de qualquer pedido de rede.
        if queries_itens.existe(conexao_bd, "", hash_do_titulo):
            resumo.duplicados += 1
            continue

        link = fonte_alternativa.url_real(str(link))
        _respeitar_intervalo(link, limiares.intervalo_google_news_segundos)
        url_final = url_canonica(cliente_http, link)
        if queries_itens.existe(conexao_bd, url_final, hash_do_titulo):
            resumo.duplicados += 1
            continue

        corpo: str | None = None
        _respeitar_intervalo(url_final, limiares.intervalo_google_news_segundos)
        try:
            pagina = cliente_http.get(url_final, timeout=15.0)
            pagina.raise_for_status()
            corpo = trafilatura.extract(pagina.text)
        except Exception:
            corpo = None

        publicado_em = _data_feedparser_para_iso(entrada)
        agora_iso = datetime.now(UTC).isoformat()

        ruido, _motivo = e_ruido(titulo, corpo, publicado_em, agora_iso, limiares)
        if ruido:
            resumo.descartados_ruido += 1
            continue

        item = Item(
            fonte_id=fonte.id,
            url_canonica=url_final,
            titulo=titulo,
            texto=corpo,
            publicado_em=publicado_em,
            coletado_em=agora_iso,
            hash_titulo=hash_do_titulo,
        )
        queries_itens.inserir(conexao_bd, item)
        resumo.itens_novos += 1
        n_itens_novos_da_fonte += 1
        if n_itens_novos_da_fonte >= limiares.maximo_itens_novos_por_feed:
            break

    return _ResultadoFeed(n_itens_novos_da_fonte)
