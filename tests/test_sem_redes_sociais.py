""" "Esta pessoa não tem redes sociais" na página da pessoa (brief 060)."""

from __future__ import annotations

from pathlib import Path

import pytest
from flask import Flask
from flask.testing import FlaskClient

import agente_nw.console.app as console_app
from agente_nw.nucleo.database.queries import pedidos, rede_sem_perfil, redes_sociais
from tests.test_console_novo_contato import _limiares
from tests.test_fluxo import Cenario


def _app(cenario: Cenario) -> FlaskClient:
    app: Flask = console_app.criar_app(
        cenario.caminho,
        cenario.caminho.parent / "log.jsonl",
        object(),  # type: ignore[arg-type]
        _limiares(),
        "http://unused",
        dependencias=cenario.deps,
        executar=lambda tarefa: tarefa(),
    )
    return app.test_client()


@pytest.fixture
def cenario(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Cenario:
    return Cenario(tmp_path, monkeypatch)


def test_botao_grava_sem_perfil_em_todas_as_redes(cenario: Cenario) -> None:
    perfil_id = cenario.contato("Marta Quintela")
    client = _app(cenario)

    resposta = client.post(f"/pessoa/{perfil_id}/sem-redes-sociais")

    assert resposta.status_code == 302
    assert rede_sem_perfil.listar_redes(cenario.conn, perfil_id) == {
        "linkedin",
        "instagram",
        "facebook",
        "x",
    }
    pagina = client.get(f"/pessoa/{perfil_id}").get_data(as_text=True)
    assert "Sem redes sociais" in pagina


def test_pedido_depois_de_marcar_nao_pergunta_rede(cenario: Cenario) -> None:
    perfil_id = cenario.contato("Marta Quintela")
    client = _app(cenario)
    client.post(f"/pessoa/{perfil_id}/sem-redes-sociais")

    resposta = client.post("/pedir", data={"texto": "Falar sobre vela", "perfil_id": str(perfil_id)})
    pagina = client.get(str(resposta.headers["Location"])).get_data(as_text=True)

    assert "É esta pessoa?" not in pagina
    assert "Não tem perfil nesta rede" not in pagina
    gravado = pedidos.obter_por_id(cenario.conn, 1)
    assert gravado is not None and gravado.status == "concluido"


def test_trocar_perfil_desfaz_a_marcacao_daquela_rede(cenario: Cenario) -> None:
    perfil_id = cenario.contato("Marta Quintela")
    client = _app(cenario)
    client.post(f"/pessoa/{perfil_id}/sem-redes-sociais")

    client.post(f"/pessoa/{perfil_id}/trocar-perfil", data={"link": "https://www.linkedin.com/in/marta"})

    assert "linkedin" not in rede_sem_perfil.listar_redes(cenario.conn, perfil_id)
    assert {r.rede for r in redes_sociais.listar_por_perfil(cenario.conn, perfil_id)} == {"linkedin"}
