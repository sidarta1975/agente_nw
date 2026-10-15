from __future__ import annotations

from datetime import UTC, datetime, timedelta
from email.utils import format_datetime
from pathlib import Path

import httpx
import pytest

from agente_nw.coleta.rss import leitor
from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.modelos.configuracao import ColetaLimiares

_PARAGRAFO = "Texto relevante e substancial da notícia. " * 20
_PAGINA_HTML = f"<html><body><article>{_PARAGRAFO}</article></body></html>"


def _feed_xml(nome: str, link: str) -> bytes:
    publicado = format_datetime(datetime.now(UTC) - timedelta(days=1))
    return f"""<?xml version="1.0"?>
<rss version="2.0"><channel><title>{nome}</title>
<item><title>Notícia da fonte {nome} sobre um assunto qualquer</title>
<link>{link}</link>
<pubDate>{publicado}</pubDate></item>
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


def _fontes(caminho: Path) -> Path:
    caminho.write_text(
        "feeds:\n"
        + "".join(
            f"  - nome: Fonte{n}\n    url: https://exemplo.com/feed{n}.xml\n    tipo: veiculo\n"
            "    confiabilidade: 7\n"
            for n in (1, 2, 3)
        ),
        encoding="utf-8",
    )
    return caminho


def test_bloqueio_do_site_para_a_coleta_avisa_e_a_proxima_tenta_o_feed_de_novo(
    tmp_path: Path, limiares: ColetaLimiares
) -> None:
    bloqueado = {"ligado": True}
    pedidos: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith(".xml"):
            pedidos.append(url)
        if url.endswith("/feed2.xml") and bloqueado["ligado"]:
            return httpx.Response(503, text="Sorry...")
        for numero in (1, 2, 3):
            if url.endswith(f"/feed{numero}.xml"):
                link = f"https://exemplo.com/n{numero}"
                return httpx.Response(200, content=_feed_xml(f"Fonte{numero}", link))
        return httpx.Response(200, text=_PAGINA_HTML)

    cliente = httpx.Client(transport=httpx.MockTransport(handler))
    banco = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(banco)
    fontes = _fontes(tmp_path / "fontes.yaml")

    primeira = leitor.coletar(banco, cliente, fontes, limiares, tmp_path / "PARE")

    assert primeira.fontes_processadas == 1
    assert primeira.bloqueio == "exemplo.com respondeu 503"
    assert primeira.feeds_com_erro == ["Fonte2"]
    assert not any(url.endswith("/feed3.xml") for url in pedidos)  # parou de insistir

    bloqueado["ligado"] = False
    depois_do_cooldown = datetime.now(UTC) + timedelta(minutes=limiares.cooldown_bloqueio_minutos + 1)
    segunda = leitor.coletar(banco, cliente, fontes, limiares, tmp_path / "PARE", agora=depois_do_cooldown)

    assert segunda.bloqueio is None
    assert segunda.fontes_processadas == 2  # o feed que falhou não foi dado como processado
    assert banco.execute("SELECT COUNT(*) FROM item").fetchone()[0] == 3


def test_erro_comum_de_um_feed_nao_bloqueia_os_demais(tmp_path: Path, limiares: ColetaLimiares) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/feed2.xml"):
            return httpx.Response(500)
        for numero in (1, 3):
            if url.endswith(f"/feed{numero}.xml"):
                link = f"https://exemplo.com/n{numero}"
                return httpx.Response(200, content=_feed_xml(f"Fonte{numero}", link))
        return httpx.Response(200, text=_PAGINA_HTML)

    cliente = httpx.Client(transport=httpx.MockTransport(handler))
    banco = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(banco)

    resumo = leitor.coletar(banco, cliente, _fontes(tmp_path / "fontes.yaml"), limiares, tmp_path / "PARE")

    assert resumo.bloqueio is None
    assert resumo.feeds_com_erro == ["Fonte2"]
    assert resumo.fontes_processadas == 2


def test_titulo_ja_conhecido_nao_gera_pedido_de_rede_e_o_limite_por_feed_vale(
    tmp_path: Path, limiares: ColetaLimiares
) -> None:
    pedidos: list[str] = []

    def feed_com(titulos: list[str]) -> bytes:
        publicado = format_datetime(datetime.now(UTC) - timedelta(days=1))
        itens = "".join(
            f"<item><title>{t}</title><link>https://exemplo.com/{n}</link>"
            f"<pubDate>{publicado}</pubDate></item>"
            for n, t in enumerate(titulos)
        )
        return f'<?xml version="1.0"?><rss version="2.0"><channel>{itens}</channel></rss>'.encode()

    titulos = [f"Notícia número {n} sobre um assunto" for n in range(6)]

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/feed1.xml"):
            return httpx.Response(200, content=feed_com(titulos))
        pedidos.append(url)
        return httpx.Response(200, text=_PAGINA_HTML)

    cliente = httpx.Client(transport=httpx.MockTransport(handler))
    banco = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(banco)
    fontes = tmp_path / "fontes.yaml"
    fontes.write_text(
        "feeds:\n  - nome: Fonte1\n    url: https://exemplo.com/feed1.xml\n"
        "    tipo: veiculo\n    confiabilidade: 7\n",
        encoding="utf-8",
    )
    limitado = limiares.model_copy(update={"maximo_itens_novos_por_feed": 4})

    primeira = leitor.coletar(banco, cliente, fontes, limitado, tmp_path / "PARE")

    assert primeira.itens_novos == 4  # parou no limite do feed
    assert len(pedidos) == 8  # 2 pedidos por notícia nova (redirecionamento + página)

    pedidos.clear()
    banco.execute("DELETE FROM progresso")  # simula outro dia: o feed é lido de novo
    segunda = leitor.coletar(banco, cliente, fontes, limitado, tmp_path / "PARE")

    assert segunda.duplicados == 4  # as 4 já conhecidas não geram nenhum pedido
    assert segunda.itens_novos == 2
    assert len(pedidos) == 4
