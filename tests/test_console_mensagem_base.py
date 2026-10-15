from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from agente_nw.nucleo.database.queries import gancho_uso, pedidos
from agente_nw.nucleo.modelos.redacao import Gancho, Redacao
from tests.test_console_tela_unica import TEXTO, _app, _pedir
from tests.test_fluxo import Cenario


@pytest.fixture
def cenario(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Cenario:
    cenario = Cenario(tmp_path, monkeypatch)

    def so_a_base(*_a: Any, **_kw: Any) -> Redacao:
        base = Gancho(
            peculiaridade="as fotos da regata",
            por_que_para_esta_pessoa="Ela publicou a regata.",
            mensagem="Oi Marta, vi as fotos da regata e queria te convidar para um jantar.",
        )
        aviso = "Sem notícia relevante agora; mensagem a partir do perfil."
        return Redacao(ganchos=[base], aviso=aviso, registro_usado="cordial")

    monkeypatch.setattr("agente_nw.nucleo.fluxo.redacao_mod.redigir", so_a_base)
    return cenario


def test_a_tela_mostra_a_mensagem_base_primeiro_sem_noticia_e_o_aviso_informativo(cenario: Cenario) -> None:
    cenario.contato(curar=True)
    client = _app(cenario)

    pagina = client.get(_pedir(client, TEXTO)).get_data(as_text=True)

    assert "1. Mensagem base" in pagina
    assert "Peculiaridade da pessoa:" in pagina and "as fotos da regata" in pagina
    assert "Notícia:" not in pagina
    assert "Sem notícia relevante agora; mensagem a partir do perfil." in pagina
    assert "/pedido/1/gancho/base/usado" in pagina


def test_marcar_usei_na_mensagem_base(cenario: Cenario) -> None:
    cenario.contato(curar=True)
    client = _app(cenario)
    _pedir(client, TEXTO)
    consulta_id = pedidos.obter_por_id(cenario.conn, 1).consulta_id  # type: ignore[union-attr]
    assert consulta_id is not None

    resposta = client.post("/pedido/1/gancho/base/usado")

    assert resposta.status_code == 302
    assert gancho_uso.listar_por_consulta(cenario.conn, consulta_id)[0][:2] == (None, "usado")
    assert client.post("/pedido/1/gancho/base/qualquer").status_code == 400
