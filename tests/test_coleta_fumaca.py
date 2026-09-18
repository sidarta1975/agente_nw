from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from agente_nw.coleta.rss import leitor
from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import perfis
from agente_nw.nucleo.database.queries import temas as queries_temas
from agente_nw.nucleo.modelos.configuracao import ColetaLimiares

RAIZ = Path(__file__).resolve().parent.parent


def _rede_disponivel() -> bool:
    try:
        httpx.get("https://g1.globo.com/rss/g1/", timeout=5.0).raise_for_status()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _rede_disponivel(), reason="rede indisponível (feed real não respondeu)")


@pytest.fixture
def limiares() -> ColetaLimiares:
    return ColetaLimiares(
        teaser_minimo_caracteres=400,
        dias_max_primeira_aparicao=7,
        retencao_texto_dias=90,
        intervalo_google_news_segundos=0,
        dias_alerta_feed_vazio=2,
    )


def test_leitor_completo_sobre_fontes_exemplo_nao_duplica_em_segunda_rodada(
    tmp_path: Path, limiares: ColetaLimiares
) -> None:
    conexao_bd = conexao.abrir(tmp_path / "fumaca.db")
    migracoes.aplicar(conexao_bd)

    agora = "2026-09-18T00:00:00+00:00"
    usuario = perfis.upsert_usuario(conexao_bd, "Usuário de teste", agora)
    assert usuario.id is not None
    tema = queries_temas.obter_ou_criar(
        conexao_bd, "direito tributário", "reforma tributária, IBS, CBS, split payment", [], agora
    )
    conexao_bd.commit()
    assert tema.id is not None

    cliente_http = httpx.Client(timeout=30.0)
    caminho_sentinela = tmp_path / "PARE"

    resumo1 = leitor.coletar(
        conexao_bd, cliente_http, RAIZ / "fontes.exemplo.yaml", limiares, caminho_sentinela
    )
    assert resumo1.fontes_processadas >= 3  # 3 feeds do exemplo + ao menos 1 consulta do Google News
    assert resumo1.itens_novos >= 1

    (n_itens_apos_primeira,) = conexao_bd.execute("SELECT COUNT(*) FROM item").fetchone()

    resumo2 = leitor.coletar(
        conexao_bd, cliente_http, RAIZ / "fontes.exemplo.yaml", limiares, caminho_sentinela
    )
    (n_itens_apos_segunda,) = conexao_bd.execute("SELECT COUNT(*) FROM item").fetchone()

    assert n_itens_apos_segunda == n_itens_apos_primeira
    assert resumo2.fontes_processadas == 0  # mesmo dia, já processadas — nada a repetir
