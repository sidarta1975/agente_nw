from __future__ import annotations

import pytest

from agente_nw.coleta.rss.ruido import e_ruido
from agente_nw.nucleo.modelos.configuracao import ColetaLimiares

HOJE = "2026-09-18T10:00:00+00:00"
CORPO_LONGO = "texto relevante e substancial sobre o assunto tratado na notícia. " * 10


@pytest.fixture
def limiares() -> ColetaLimiares:
    return ColetaLimiares(
        teaser_minimo_caracteres=400,
        dias_max_primeira_aparicao=7,
        retencao_texto_dias=90,
        intervalo_google_news_segundos=2,
        dias_alerta_feed_vazio=2,
    )


def test_corpo_abaixo_do_teaser_minimo_e_ruido(limiares: ColetaLimiares) -> None:
    ruido, motivo = e_ruido("Título normal", "corpo curto", HOJE, HOJE, limiares)
    assert ruido is True
    assert motivo == "corpo abaixo do teaser mínimo"


def test_titulo_de_lista_e_ruido(limiares: ColetaLimiares) -> None:
    ruido, motivo = e_ruido("10 dicas para economizar no fim do ano", CORPO_LONGO, HOJE, HOJE, limiares)
    assert ruido is True
    assert motivo == "título de lista"


def test_marcado_como_patrocinado_e_ruido(limiares: ColetaLimiares) -> None:
    ruido, motivo = e_ruido("Publicidade: conheça o novo produto", CORPO_LONGO, HOJE, HOJE, limiares)
    assert ruido is True
    assert motivo == "marcado como patrocinado"


def test_mais_de_sete_dias_ate_primeira_coleta_e_ruido(limiares: ColetaLimiares) -> None:
    publicado_ha_muito_tempo = "2026-09-01T10:00:00+00:00"
    ruido, motivo = e_ruido("Título normal", CORPO_LONGO, publicado_ha_muito_tempo, HOJE, limiares)
    assert ruido is True
    assert motivo == "mais dias que o permitido entre publicação e primeira coleta"


def test_item_normal_nao_e_ruido(limiares: ColetaLimiares) -> None:
    ruido, motivo = e_ruido("Reforma tributária avança no Congresso", CORPO_LONGO, HOJE, HOJE, limiares)
    assert ruido is False
    assert motivo is None
