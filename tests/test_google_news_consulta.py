from __future__ import annotations

from urllib.parse import quote

from agente_nw.coleta.rss.google_news import gerar_consultas_da_consulta
from agente_nw.nucleo.modelos.contexto_consulta import ContextoConsulta


def test_gera_uma_consulta_para_assunto_interessa_e_contato() -> None:
    contexto = ContextoConsulta(
        assunto="mercado de vela",
        meio="whatsapp",
        objetivo="retomar contato",
        interessa=["regata", "barcos"],
    )

    feeds = gerar_consultas_da_consulta(contexto, ["navegação", "imóveis"])

    assert len(feeds) == 1 + 2 + 2
    assert len({feed.nome for feed in feeds}) == len(feeds)
    assert quote('"mercado de vela"') in feeds[0].url
    assert quote('"regata"') in feeds[1].url
    assert quote('"navegação"') in feeds[3].url


def test_limita_interessa_a_cinco_e_termos_do_contato_a_tres() -> None:
    contexto = ContextoConsulta(
        assunto="a",
        meio="whatsapp",
        objetivo="b",
        interessa=[f"i{n}" for n in range(8)],
    )

    feeds = gerar_consultas_da_consulta(contexto, [f"c{n}" for n in range(6)])

    assert len(feeds) == 1 + 5 + 3


def test_sem_termos_do_contato_so_o_contexto() -> None:
    contexto = ContextoConsulta(assunto="a", meio="whatsapp", objetivo="b")
    assert len(gerar_consultas_da_consulta(contexto, [])) == 1
