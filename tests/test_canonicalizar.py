from __future__ import annotations

import httpx
import pytest

from agente_nw.coleta.rss.canonicalizar import hash_titulo, url_canonica

PARAMETROS_RASTREIO = (
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
    "igshid",
    "mc_cid",
    "mc_eid",
)


@pytest.fixture
def cliente_sem_redirecionamento() -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200)

    return httpx.Client(transport=httpx.MockTransport(handler))


@pytest.mark.parametrize("parametro", PARAMETROS_RASTREIO)
def test_remove_cada_parametro_de_rastreio(
    cliente_sem_redirecionamento: httpx.Client, parametro: str
) -> None:
    url = f"https://exemplo.com/noticia?id=42&{parametro}=xyz"
    resultado = url_canonica(cliente_sem_redirecionamento, url)
    assert parametro not in resultado
    assert "id=42" in resultado


def test_remove_ancora(cliente_sem_redirecionamento: httpx.Client) -> None:
    resultado = url_canonica(cliente_sem_redirecionamento, "https://exemplo.com/noticia?id=1#secao-2")
    assert "#" not in resultado


def test_segue_exatamente_um_redirecionamento() -> None:
    chamadas: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        chamadas.append(str(request.url))
        if "encurtador.com" in str(request.url):
            return httpx.Response(301, headers={"location": "https://destino.com/pagina-final?fbclid=abc"})
        return httpx.Response(200)

    cliente = httpx.Client(transport=httpx.MockTransport(handler))
    resultado = url_canonica(cliente, "https://encurtador.com/abc")

    assert resultado == "https://destino.com/pagina-final"
    assert len(chamadas) == 1  # não perseguiu um segundo redirecionamento a partir do destino


def test_hash_igual_para_variacoes_de_acentuacao_caixa_pontuacao() -> None:
    h1 = hash_titulo("Reforma tributária: o que muda?")
    h2 = hash_titulo("reforma tributária - o que muda")
    h3 = hash_titulo("REFORMA TRIBUTÁRIA, O QUE MUDA")
    assert h1 == h2 == h3


def test_hash_diferente_para_titulos_diferentes() -> None:
    h1 = hash_titulo("Reforma tributária avança no Congresso")
    h2 = hash_titulo("Corrida de rua bate recorde de inscritos")
    assert h1 != h2
