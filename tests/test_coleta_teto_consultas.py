from __future__ import annotations

from pathlib import Path

from agente_nw.coleta.rss.google_news import selecionar_termos
from agente_nw.nucleo.modelos.contexto_consulta import ContextoConsulta
from tests.coleta_falsa import GOOGLE, RedeFalsa, banco, coletar, limiares


def test_pedido_com_muitos_termos_gera_no_maximo_o_teto_nos_termos_certos() -> None:
    contexto = ContextoConsulta(
        assunto="ensino de idiomas",
        meio="whatsapp",
        objetivo="retomar",
        interessa=["viagens", "esqui"],
        termos_busca=["metodologias ativas", "idiomas online", "cursos de inglês"],
    )
    teto = limiares().max_consultas_por_pedido

    escolhidos = selecionar_termos(contexto, ["inglês corporativo", "sotaque"], teto)
    termos = [termo for _rotulo, termo in escolhidos]

    assert teto == 4
    assert termos == ["ensino de idiomas", "inglês corporativo", "sotaque", "metodologias ativas"]


def test_a_coleta_para_de_abrir_buscas_quando_ja_ha_candidatos_suficientes(tmp_path: Path) -> None:
    rede = RedeFalsa(por_busca=6)
    conn = banco(tmp_path)

    resumo = coletar(rede, conn, tmp_path, ["a1", "b2", "c3", "d4"], candidatos_suficientes=10)

    assert resumo.itens_novos == 12  # as duas primeiras buscas (6 + 6) passam de 10
    assert len(rede.buscas(GOOGLE)) == 2


def test_com_poucos_candidatos_todas_as_buscas_do_pedido_rodam(tmp_path: Path) -> None:
    rede = RedeFalsa(por_busca=1)
    conn = banco(tmp_path)

    resumo = coletar(rede, conn, tmp_path, ["a1", "b2", "c3", "d4"], candidatos_suficientes=10)

    assert resumo.itens_novos == 4
    assert len(rede.buscas(GOOGLE)) == 4
