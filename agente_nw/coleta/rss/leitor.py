from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import feedparser
import httpx
import trafilatura
import yaml

from agente_nw.coleta.rss.canonicalizar import hash_titulo, url_canonica
from agente_nw.coleta.rss.google_news import gerar_consultas
from agente_nw.coleta.rss.ruido import e_ruido
from agente_nw.nucleo.database.queries import fontes as queries_fontes
from agente_nw.nucleo.database.queries import itens as queries_itens
from agente_nw.nucleo.database.queries import sistema
from agente_nw.nucleo.database.queries import temas as queries_temas
from agente_nw.nucleo.modelos.configuracao import ColetaLimiares, FontesArquivo
from agente_nw.nucleo.modelos.fonte import Fonte
from agente_nw.nucleo.modelos.item import Item

ETAPA_PROGRESSO = "coleta"


@dataclass
class ResumoColeta:
    fontes_processadas: int = 0
    itens_novos: int = 0
    duplicados: int = 0
    descartados_ruido: int = 0
    alertas_feed_vazio: list[str] = field(default_factory=list)
    tempo_segundos: float = 0.0


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


def coletar(
    conexao_bd: sqlite3.Connection,
    cliente_http: httpx.Client,
    caminho_fontes_yaml: Path,
    limiares: ColetaLimiares,
    caminho_sentinela: Path,
) -> ResumoColeta:
    inicio = time.monotonic()
    resumo = ResumoColeta()
    hoje = datetime.now(UTC).date().isoformat()

    feeds_arquivo = _carregar_fontes_arquivo(caminho_fontes_yaml).feeds
    temas_usuario = queries_temas.listar(conexao_bd)
    feeds_google_news = gerar_consultas(temas_usuario)

    fontes_no_banco: list[Fonte] = []
    for feed in [*feeds_arquivo, *feeds_google_news]:
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

    ultima_consulta_google_news = 0.0

    for fonte in fontes_a_processar:
        if caminho_sentinela.exists():
            break
        assert fonte.id is not None

        if "news.google.com" in fonte.url_feed:
            espera = limiares.intervalo_google_news_segundos - (
                time.monotonic() - ultima_consulta_google_news
            )
            if espera > 0:
                time.sleep(espera)
            ultima_consulta_google_news = time.monotonic()

        n_itens_novos_da_fonte = _processar_fonte(conexao_bd, cliente_http, fonte, limiares, resumo)

        queries_fontes.registrar_execucao(conexao_bd, fonte.id, hoje, n_itens_novos_da_fonte)
        if queries_fontes.dois_dias_vazios(conexao_bd, fonte.id, hoje):
            resumo.alertas_feed_vazio.append(fonte.nome)

        sistema.progresso_gravar(conexao_bd, ETAPA_PROGRESSO, fonte.id, hoje, datetime.now(UTC).isoformat())
        conexao_bd.commit()
        resumo.fontes_processadas += 1

    resumo.tempo_segundos = time.monotonic() - inicio
    return resumo


def _processar_fonte(
    conexao_bd: sqlite3.Connection,
    cliente_http: httpx.Client,
    fonte: Fonte,
    limiares: ColetaLimiares,
    resumo: ResumoColeta,
) -> int:
    assert fonte.id is not None
    n_itens_novos_da_fonte = 0

    try:
        resposta_feed = cliente_http.get(fonte.url_feed, timeout=15.0)
        resposta_feed.raise_for_status()
        analisado = feedparser.parse(resposta_feed.content)
    except Exception:
        return 0

    for entrada in analisado.entries:
        titulo = str(entrada.get("title", "")).strip()
        link = entrada.get("link")
        if not titulo or not link:
            continue

        url_final = url_canonica(cliente_http, link)
        hash_do_titulo = hash_titulo(titulo)

        if queries_itens.existe(conexao_bd, url_final, hash_do_titulo):
            resumo.duplicados += 1
            continue

        corpo: str | None = None
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

    return n_itens_novos_da_fonte
