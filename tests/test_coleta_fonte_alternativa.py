from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from agente_nw.coleta.rss import fonte_alternativa
from tests.coleta_falsa import BING, GOOGLE, RedeFalsa, banco, coletar


def test_feed_do_bing_ordena_por_data_e_vai_sem_aspas() -> None:
    feed = fonte_alternativa.feed_do_termo("inglês corporativo")

    assert feed.url.startswith("https://www.bing.com/news/search?q=")
    assert quote("inglês corporativo") in feed.url
    assert quote('"') not in feed.url.split("&qft")[0]  # com aspas e sortbydate o Bing devolve vazio
    assert "format=rss" in feed.url
    assert "qft=sortbydate" in feed.url


def test_url_real_sai_do_parametro_url_do_redirecionador() -> None:
    real = "https://oglobo.globo.com/educacao/noticia.ghtml"
    link = f"http://www.bing.com/news/apiclick.aspx?ref=FexRss&aid=&url={quote(real, safe='')}&c=1&mkt=pt-br"

    assert fonte_alternativa.url_real(link) == real
    assert fonte_alternativa.url_real("https://exemplo.com/materia") == "https://exemplo.com/materia"
    sem_url = "http://www.bing.com/news/apiclick.aspx?ref=FexRss"
    assert fonte_alternativa.url_real(sem_url) == sem_url


def test_com_o_google_em_cooldown_le_o_bing_e_grava_a_url_real(tmp_path: Path) -> None:
    rede = RedeFalsa(por_busca=2)
    rede.google = "503"
    conn = banco(tmp_path)

    resumo = coletar(rede, conn, tmp_path, ["inglês corporativo"])

    assert resumo.fonte_usada == "alternativa"
    urls = [linha["url_canonica"] for linha in conn.execute("SELECT url_canonica FROM item")]
    assert len(urls) == 2
    assert all(url.startswith("https://noticias.exemplo.com/b-") for url in urls)  # não o redirecionador
    assert BING in rede.hosts() and "noticias.exemplo.com" in rede.hosts()


def test_a_alternativa_passa_pelo_mesmo_filtro_de_duplicado(tmp_path: Path) -> None:
    rede = RedeFalsa(por_busca=2)
    rede.google = "503"
    conn = banco(tmp_path)
    coletar(rede, conn, tmp_path, ["inglês corporativo"])

    resumo = coletar(rede, conn, tmp_path, ["inglês corporativo"], minutos=25 * 60 + 200)

    assert resumo.itens_novos == 0
    assert resumo.duplicados == 2


def test_a_alternativa_passa_pelo_mesmo_filtro_de_ruido(tmp_path: Path) -> None:
    rede = RedeFalsa(por_busca=2)
    rede.google = "503"
    rede.dias_atras = 30  # velha demais: o filtro de ruído descarta, como faria com o Google
    conn = banco(tmp_path)

    resumo = coletar(rede, conn, tmp_path, ["inglês corporativo"])

    assert resumo.itens_novos == 0
    assert resumo.descartados_ruido == 2


def test_alternativa_desligada_nao_chama_o_bing(tmp_path: Path) -> None:
    rede = RedeFalsa()
    rede.google = "503"
    conn = banco(tmp_path)

    resumo = coletar(rede, conn, tmp_path, ["inglês corporativo"], usar_fonte_alternativa=False)

    assert BING not in rede.hosts()
    assert resumo.fonte_usada == "nenhuma"
    assert GOOGLE in rede.hosts()
