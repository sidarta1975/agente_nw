from __future__ import annotations

from pathlib import Path

from agente_nw.nucleo.database.queries import sistema
from tests.coleta_falsa import GOOGLE, RedeFalsa, banco, coletar


def test_termo_buscado_ha_pouco_nao_vai_de_novo_a_rede(tmp_path: Path) -> None:
    rede = RedeFalsa()
    conn = banco(tmp_path)
    coletar(rede, conn, tmp_path, ["inglês corporativo"])
    rede.pedidos.clear()

    resumo = coletar(rede, conn, tmp_path, ["  Ingles   CORPORATIVO "], minutos=60)

    assert rede.pedidos == []  # nem a busca nem uma notícia: tudo já estava guardado
    assert resumo.termos_reaproveitados == 1
    assert resumo.fonte_usada == "reaproveitada"


def test_termo_mais_antigo_que_a_janela_e_buscado_de_novo(tmp_path: Path) -> None:
    rede = RedeFalsa()
    conn = banco(tmp_path)
    coletar(rede, conn, tmp_path, ["inglês corporativo"])
    rede.pedidos.clear()

    resumo = coletar(rede, conn, tmp_path, ["inglês corporativo"], minutos=25 * 60)

    assert len(rede.buscas(GOOGLE)) == 1
    assert resumo.termos_reaproveitados == 0
    assert resumo.fonte_usada == "google"


def test_a_janela_vem_do_limiar_e_zero_desliga_o_reuso(tmp_path: Path) -> None:
    rede = RedeFalsa()
    conn = banco(tmp_path)
    coletar(rede, conn, tmp_path, ["inglês corporativo"], horas_reuso_termo=0)
    rede.pedidos.clear()

    coletar(rede, conn, tmp_path, ["inglês corporativo"], horas_reuso_termo=0)

    assert len(rede.buscas(GOOGLE)) == 1


def test_busca_que_falhou_nao_conta_como_buscada(tmp_path: Path) -> None:
    rede = RedeFalsa()
    rede.google = "503"
    conn = banco(tmp_path)
    coletar(rede, conn, tmp_path, ["inglês corporativo"], usar_fonte_alternativa=False)

    assert sistema.termo_buscado_em(conn, "ingles corporativo") is None


def test_termo_misturado_com_novo_so_busca_o_novo(tmp_path: Path) -> None:
    rede = RedeFalsa()
    conn = banco(tmp_path)
    coletar(rede, conn, tmp_path, ["inglês corporativo"])
    rede.pedidos.clear()

    resumo = coletar(rede, conn, tmp_path, ["inglês corporativo", "sotaque profissional"], minutos=5)

    assert len(rede.buscas(GOOGLE)) == 1
    assert resumo.termos_reaproveitados == 1
    assert resumo.fonte_usada == "google"
