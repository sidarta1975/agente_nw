from __future__ import annotations

from pathlib import Path

from agente_nw.nucleo.database import conexao
from agente_nw.nucleo.database.queries import sistema
from tests.coleta_falsa import BING, GOOGLE, RedeFalsa, banco, coletar


def test_um_503_grava_o_cooldown_e_a_busca_cai_no_bing(tmp_path: Path) -> None:
    rede = RedeFalsa()
    rede.google = "503"
    conn = banco(tmp_path)

    resumo = coletar(rede, conn, tmp_path, ["inglês corporativo"])

    assert sistema.bloqueio_ate(conn, GOOGLE) is not None
    assert resumo.bloqueio == f"{GOOGLE} respondeu 503"
    assert resumo.fonte_usada == "alternativa"
    assert resumo.google_bloqueado_ate is not None
    assert resumo.itens_novos == 3
    assert len(rede.buscas(BING)) == 1


def test_o_pedido_seguinte_nao_chama_o_google_durante_o_cooldown(tmp_path: Path) -> None:
    rede = RedeFalsa()
    rede.google = "503"
    conn = banco(tmp_path)
    coletar(rede, conn, tmp_path, ["inglês corporativo"])
    rede.pedidos.clear()
    rede.google = "ok"  # mesmo que o Google já tenha voltado, o programa não insiste antes da hora

    resumo = coletar(rede, conn, tmp_path, ["sotaque profissional"], minutos=10)

    assert GOOGLE not in rede.hosts()
    assert resumo.fonte_usada == "alternativa"
    assert resumo.google_bloqueado_ate is not None


def test_dez_pedidos_seguidos_nao_renovam_o_bloqueio(tmp_path: Path) -> None:
    rede = RedeFalsa()
    rede.google = "503"
    conn = banco(tmp_path)
    coletar(rede, conn, tmp_path, ["tema 0"])
    chamadas_ao_google = len(rede.buscas(GOOGLE))

    for n in range(1, 11):
        coletar(rede, conn, tmp_path, [f"tema {n}"], minutos=n)

    assert len(rede.buscas(GOOGLE)) == chamadas_ao_google == 1


def test_passado_o_cooldown_volta_ao_google(tmp_path: Path) -> None:
    rede = RedeFalsa()
    rede.google = "503"
    conn = banco(tmp_path)
    coletar(rede, conn, tmp_path, ["inglês corporativo"])
    rede.google = "ok"

    resumo = coletar(rede, conn, tmp_path, ["sotaque profissional"], minutos=181)

    assert resumo.fonte_usada == "google"
    assert resumo.bloqueio is None
    assert len(rede.buscas(GOOGLE)) == 2


def test_o_cooldown_atravessa_o_reinicio_porque_vive_no_banco(tmp_path: Path) -> None:
    rede = RedeFalsa()
    rede.google = "503"
    conn = banco(tmp_path)
    coletar(rede, conn, tmp_path, ["inglês corporativo"])
    conn.close()
    rede.pedidos.clear()
    rede.google = "ok"

    reaberto = conexao.abrir(tmp_path / "teste.db")
    coletar(rede, reaberto, tmp_path, ["sotaque profissional"], minutos=5)

    assert GOOGLE not in rede.hosts()


def test_o_tempo_do_cooldown_vem_do_limiar(tmp_path: Path) -> None:
    rede = RedeFalsa()
    rede.google = "503"
    conn = banco(tmp_path)

    coletar(rede, conn, tmp_path, ["inglês corporativo"], cooldown_bloqueio_minutos=30)
    rede.google = "ok"

    dentro = coletar(rede, conn, tmp_path, ["a"], minutos=20, cooldown_bloqueio_minutos=30)
    fora = coletar(rede, conn, tmp_path, ["b"], minutos=31, cooldown_bloqueio_minutos=30)

    assert dentro.fonte_usada == "alternativa"
    assert fora.fonte_usada == "google"
