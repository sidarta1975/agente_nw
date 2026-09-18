from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from agente_nw.coleta.rss import leitor
from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.modelos.configuracao import ColetaLimiares

_PARAGRAFO = "Texto relevante e substancial da notícia. " * 20
PAGINA_HTML = f"<html><body><article>{_PARAGRAFO}</article></body></html>"


def _feed_xml(nome: str, link: str) -> bytes:
    return f"""<?xml version="1.0"?>
<rss version="2.0"><channel><title>{nome}</title>
<item><title>Notícia da fonte {nome} sobre um assunto qualquer</title>
<link>{link}</link>
<pubDate>Fri, 18 Sep 2026 10:00:00 GMT</pubDate></item>
</channel></rss>""".encode()


@pytest.fixture
def limiares() -> ColetaLimiares:
    return ColetaLimiares(
        teaser_minimo_caracteres=400,
        dias_max_primeira_aparicao=7,
        retencao_texto_dias=90,
        intervalo_google_news_segundos=0,
        dias_alerta_feed_vazio=2,
    )


def _escrever_fontes_yaml(caminho: Path) -> None:
    caminho.write_text(
        "feeds:\n"
        "  - nome: Fonte1\n"
        "    url: https://exemplo.com/feed1.xml\n"
        "    tipo: veiculo\n"
        "    confiabilidade: 7\n"
        "  - nome: Fonte2\n"
        "    url: https://exemplo.com/feed2.xml\n"
        "    tipo: veiculo\n"
        "    confiabilidade: 7\n"
        "  - nome: Fonte3\n"
        "    url: https://exemplo.com/feed3.xml\n"
        "    tipo: veiculo\n"
        "    confiabilidade: 7\n",
        encoding="utf-8",
    )


def test_interrupcao_no_meio_e_retomada_nao_duplica_nem_pula(
    tmp_path: Path, limiares: ColetaLimiares
) -> None:
    caminho_sentinela = tmp_path / "PARE"

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/feed1.xml"):
            # simula uma interrupção que acontece NO MEIO do processamento da fonte 1
            caminho_sentinela.touch()
            return httpx.Response(200, content=_feed_xml("Fonte1", "https://exemplo.com/n1"))
        if url.endswith("/feed2.xml"):
            return httpx.Response(200, content=_feed_xml("Fonte2", "https://exemplo.com/n2"))
        if url.endswith("/feed3.xml"):
            return httpx.Response(200, content=_feed_xml("Fonte3", "https://exemplo.com/n3"))
        return httpx.Response(200, text=PAGINA_HTML)

    cliente = httpx.Client(transport=httpx.MockTransport(handler))

    conexao_bd = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_bd)

    caminho_fontes = tmp_path / "fontes.yaml"
    _escrever_fontes_yaml(caminho_fontes)

    resumo1 = leitor.coletar(conexao_bd, cliente, caminho_fontes, limiares, caminho_sentinela)
    assert resumo1.fontes_processadas == 1
    assert resumo1.itens_novos == 1
    assert caminho_sentinela.exists()

    titulos_apos_primeira = [row[0] for row in conexao_bd.execute("SELECT titulo FROM item")]
    assert len(titulos_apos_primeira) == 1

    caminho_sentinela.unlink()
    resumo2 = leitor.coletar(conexao_bd, cliente, caminho_fontes, limiares, caminho_sentinela)
    assert resumo2.fontes_processadas == 2
    assert resumo2.itens_novos == 2

    titulos_finais = [row[0] for row in conexao_bd.execute("SELECT titulo FROM item ORDER BY id")]
    assert len(titulos_finais) == 3
    assert len(set(titulos_finais)) == 3  # nenhum duplicado
