from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest

from agente_nw.coleta.capturas.extensao_backend import PaginaExtensao, arquivar_navegador_antigo
from agente_nw.nucleo.modelos.configuracao import ExtensaoLimiares
from agente_nw.ponte import ErroDaExtensao, Ponte, PonteIndisponivel


class _PonteFalsa:
    """Registra as tarefas e responde com o que cada ação tem programado (exceção = falha)."""

    def __init__(self, respostas: dict[str, Any] | None = None) -> None:
        self.tarefas: list[dict[str, Any]] = []
        self.limites: list[float] = []
        self._respostas = respostas or {}

    def enviar(self, tarefa: dict[str, Any], tempo_limite_s: float) -> dict[str, Any]:
        self.tarefas.append(tarefa)
        self.limites.append(tempo_limite_s)
        resposta = self._respostas.get(tarefa["acao"], {})
        if isinstance(resposta, Exception):
            raise resposta
        return cast(dict[str, Any], resposta)


def _pagina(ponte: _PonteFalsa, **limiares: Any) -> PaginaExtensao:
    return PaginaExtensao(cast(Ponte, ponte), ExtensaoLimiares(**limiares))


def test_cada_metodo_vira_a_tarefa_certa() -> None:
    ponte = _PonteFalsa(
        {
            "abrir": {"aba_id": 7},
            "estado": {"url": "https://www.linkedin.com/feed/", "texto": "olá"},
            "links": {"links": [["https://www.linkedin.com/in/ana", "Ana Lima\nContadora"]]},
        }
    )
    pagina = _pagina(ponte, tempo_limite_tarefa_s=45, pausa_entre_paginas_s=3.0)

    pagina.ir_para("https://www.linkedin.com/feed/")
    estado = pagina.estado()
    pagina.rolar()
    links = pagina.coletar_links()
    pagina.fechar()

    assert estado == ("https://www.linkedin.com/feed/", "olá")
    assert links == [("https://www.linkedin.com/in/ana", "Ana Lima\nContadora")]
    acoes = [t["acao"] for t in ponte.tarefas]
    assert acoes == ["abrir", "estado", "rolar", "links", "fechar"]
    assert ponte.tarefas[0] == {
        "acao": "abrir",
        "url": "https://www.linkedin.com/feed/",
        "ativa": False,
        "pausa_s": 3.0,
    }
    assert all(t["aba_id"] == 7 for t in ponte.tarefas[1:])
    assert "mostrar mais" in ponte.tarefas[2]["rotulos"]
    assert ponte.tarefas[2]["maximo_entradas"] == 2000
    assert ponte.tarefas[2]["pausa_pagina_s"] == 3.0
    assert set(ponte.limites) == {45.0}


def test_aba_em_primeiro_plano_quando_a_configuracao_pede() -> None:
    ponte = _PonteFalsa({"abrir": {"aba_id": 1}})

    _pagina(ponte, aba_em_segundo_plano=False).ir_para("https://x.com/home")

    assert ponte.tarefas[0]["ativa"] is True


def test_estado_corta_o_texto_em_maximo_de_caracteres() -> None:
    ponte = _PonteFalsa({"abrir": {"aba_id": 1}, "estado": {"url": "u", "texto": "a" * 5000}})
    pagina = _pagina(ponte, maximo_caracteres_pagina=1000)
    pagina.ir_para("https://x.com/home")

    _url, texto = pagina.estado()

    assert len(texto) == 1000
    assert ponte.tarefas[1]["maximo"] == 1000


def test_fechar_e_idempotente() -> None:
    ponte = _PonteFalsa({"abrir": {"aba_id": 3}})
    pagina = _pagina(ponte)
    pagina.ir_para("https://www.facebook.com/friends/list")

    pagina.fechar()
    pagina.fechar()

    assert [t["acao"] for t in ponte.tarefas] == ["abrir", "fechar"]


def test_sem_aba_aberta_nada_e_enviado() -> None:
    ponte = _PonteFalsa()
    pagina = _pagina(ponte)

    assert pagina.coletar_links() == []
    pagina.rolar()
    pagina.fechar()

    assert ponte.tarefas == []


@pytest.mark.parametrize("falha", [PonteIndisponivel("sem resposta a tempo."), ErroDaExtensao("x")])
def test_ponte_indisponivel_vira_pagina_sem_sessao_e_nao_insiste(falha: Exception) -> None:
    ponte = _PonteFalsa({"abrir": falha})
    pagina = _pagina(ponte)

    pagina.ir_para("https://www.linkedin.com/feed/")
    url, texto = pagina.estado()
    pagina.rolar()
    links = pagina.coletar_links()

    assert url.startswith("ponte://")
    assert texto == ""
    assert links == []
    assert len(ponte.tarefas) == 1
    assert pagina.motivo_indisponivel is not None


def test_perfil_antigo_do_navegador_e_arquivado_uma_vez_sem_apagar(tmp_path: Path) -> None:
    navegador = tmp_path / "dados" / "navegador"
    (navegador / "linkedin").mkdir(parents=True)
    (navegador / "linkedin" / "Cookies").write_text("sessao")

    destino = arquivar_navegador_antigo(navegador)

    assert destino == tmp_path / "dados" / "_navegador_antigo"
    assert (destino / "linkedin" / "Cookies").read_text() == "sessao"
    assert not navegador.exists()
    assert arquivar_navegador_antigo(navegador) is None


def test_arquivar_ignora_pasta_vazia_ou_com_outro_nome(tmp_path: Path) -> None:
    (tmp_path / "navegador").mkdir()
    (tmp_path / "outro").mkdir()
    (tmp_path / "outro" / "x").write_text("1")

    assert arquivar_navegador_antigo(tmp_path / "navegador") is None
    assert arquivar_navegador_antigo(tmp_path / "outro") is None
    assert (tmp_path / "outro" / "x").exists()
