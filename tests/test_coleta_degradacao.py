from __future__ import annotations

from pathlib import Path

import pytest

from agente_nw.nucleo.database.queries import gancho_uso, pedidos, sistema
from tests.coleta_falsa import BING, GOOGLE, RedeFalsa, banco, coletar
from tests.test_console_tela_unica import _app
from tests.test_fluxo import Cenario


def test_google_e_bing_bloqueados_a_coleta_termina_sem_erro_e_sem_noticia(tmp_path: Path) -> None:
    rede = RedeFalsa()
    rede.google = "503"
    rede.bing = "503"
    conn = banco(tmp_path)

    resumo = coletar(rede, conn, tmp_path, ["inglês corporativo"])

    assert resumo.fonte_usada == "nenhuma"
    assert resumo.itens_novos == 0
    assert resumo.bloqueio is not None
    assert sistema.bloqueio_ate(conn, GOOGLE) is not None
    assert sistema.bloqueio_ate(conn, BING) is not None


def test_google_em_cooldown_e_bing_vazio_nao_e_erro(tmp_path: Path) -> None:
    rede = RedeFalsa()
    rede.google = "503"
    rede.bing = "vazio"
    conn = banco(tmp_path)

    resumo = coletar(rede, conn, tmp_path, ["inglês corporativo"])

    assert resumo.fonte_usada == "nenhuma"
    assert resumo.usou_alternativa is False  # respondeu, mas não trouxe nada
    assert resumo.feeds_com_erro == ["Google News · pedido: inglês corporativo"]


def test_alternativa_desligada_e_google_bloqueado_nao_insiste_nas_outras_buscas(tmp_path: Path) -> None:
    rede = RedeFalsa()
    rede.google = "503"
    conn = banco(tmp_path)

    coletar(rede, conn, tmp_path, ["a", "b", "c"], usar_fonte_alternativa=False)

    assert len(rede.buscas(GOOGLE)) == 1  # o primeiro 503 já fecha o Google para as outras buscas


def test_pedido_sem_noticia_conclui_com_ganchos_dos_temas_e_a_linha_explica(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cenario = Cenario(tmp_path, monkeypatch)
    cenario.contato(curar=True)
    cenario.fonte_noticias = "nenhuma"
    client = _app(cenario)

    client.post("/pedir", data={"texto": "Falar com a Marta sobre vela"})

    gravado = pedidos.obter_por_id(cenario.conn, 1)
    assert gravado is not None and gravado.status == "concluido" and gravado.erro is None
    assert gravado.consulta_id is not None
    assert len(gancho_uso.listar_por_consulta(cenario.conn, gravado.consulta_id)) == 1
    pagina = client.get("/pedido/1").get_data(as_text=True)
    assert "Sem notícias agora" in pagina
    assert "Deu errado" not in pagina
