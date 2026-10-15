from __future__ import annotations

from urllib.parse import quote

from agente_nw.coleta.rss.google_news import (
    gerar_consultas_da_consulta,
    normalizar_termo,
    selecionar_termos,
)
from agente_nw.nucleo.modelos.contexto_consulta import ContextoConsulta


def _contexto(**campos: object) -> ContextoConsulta:
    base: dict[str, object] = {"assunto": "mercado de vela", "meio": "whatsapp", "objetivo": "retomar"}
    return ContextoConsulta.model_validate({**base, **campos})


def test_prioridade_assunto_contato_termos_de_busca_e_interessa() -> None:
    contexto = _contexto(interessa=["regata"], termos_busca=["barcos"])

    termos = selecionar_termos(contexto, ["navegação"], maximo=10)

    assert termos == [
        ("consulta", "mercado de vela"),
        ("contato", "navegação"),
        ("busca", "barcos"),
        ("interessa", "regata"),
    ]


def test_o_teto_corta_do_fim_da_lista_de_prioridade() -> None:
    contexto = _contexto(interessa=["regata", "barcos"], termos_busca=["imóveis"])

    termos = selecionar_termos(contexto, ["navegação", "porto"], maximo=4)

    assert [termo for _rotulo, termo in termos] == ["mercado de vela", "navegação", "porto", "imóveis"]


def test_termos_repetidos_entre_as_origens_viram_um_so() -> None:
    contexto = _contexto(
        assunto="Mercado de Vela", termos_busca=["mercado  de vela", "veleiros"], interessa=["Veleiros"]
    )

    termos = selecionar_termos(contexto, ["MERCADO DE VELA"], maximo=10)

    assert termos == [("consulta", "Mercado de Vela"), ("busca", "veleiros")]


def test_normalizar_termo_ignora_acento_caixa_e_espacos() -> None:
    assert normalizar_termo("  Inglês   Corporativo ") == normalizar_termo("ingles corporativo")


def test_termo_vazio_e_ignorado_e_o_teto_padrao_e_quatro() -> None:
    contexto = _contexto(assunto="a", interessa=["", "  ", "i1", "i2", "i3", "i4"])

    assert len(selecionar_termos(contexto, [], maximo=4)) == 4
    assert all(termo.strip() for _rotulo, termo in selecionar_termos(contexto, [], maximo=10))


def test_cada_termo_escolhido_vira_uma_busca_do_google_por_frase_exata() -> None:
    contexto = _contexto(interessa=["regata"])

    feeds = gerar_consultas_da_consulta(contexto, ["navegação"])

    assert len(feeds) == 3
    assert len({feed.nome for feed in feeds}) == len(feeds)
    assert quote('"mercado de vela"') in feeds[0].url
    assert quote('"navegação"') in feeds[1].url
    assert quote('"regata"') in feeds[2].url


def test_sem_termos_do_contato_so_o_contexto() -> None:
    contexto = ContextoConsulta(assunto="a", meio="whatsapp", objetivo="b")

    assert len(gerar_consultas_da_consulta(contexto, [])) == 1
