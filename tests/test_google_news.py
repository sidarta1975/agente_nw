from __future__ import annotations

from urllib.parse import unquote

from agente_nw.coleta.rss.google_news import gerar_consultas
from agente_nw.nucleo.modelos.tema import Tema


def test_url_codificada_com_aspas_e_espacos() -> None:
    tema = Tema(
        nome="direito tributário",
        descricao="x",
        sinonimos=["reforma tributária"],
        criado_em="2026-01-01",
    )
    (feed,) = gerar_consultas([tema])

    assert feed.url.startswith("https://news.google.com/rss/search?q=")
    assert "hl=pt-BR&gl=BR&ceid=BR:pt-419" in feed.url

    consulta_decodificada = unquote(feed.url.split("q=")[1].split("&hl=")[0])
    assert consulta_decodificada == '"direito tributário" OR "reforma tributária"'


def test_limite_de_quatro_termos_por_tema() -> None:
    tema = Tema(
        nome="tema",
        descricao="x",
        sinonimos=["s1", "s2", "s3", "s4", "s5"],
        criado_em="2026-01-01",
    )
    (feed,) = gerar_consultas([tema])

    consulta_decodificada = unquote(feed.url.split("q=")[1].split("&hl=")[0])
    termos = consulta_decodificada.split(" OR ")
    assert len(termos) == 4
    assert termos == ['"tema"', '"s1"', '"s2"', '"s3"']


def test_um_feed_por_tema() -> None:
    temas = [
        Tema(nome="a", descricao="x", criado_em="2026-01-01"),
        Tema(nome="b", descricao="x", criado_em="2026-01-01"),
    ]
    feeds = gerar_consultas(temas)
    assert len(feeds) == 2
    assert feeds[0].tipo == "agregador"
