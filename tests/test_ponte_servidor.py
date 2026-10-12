from __future__ import annotations

import json
import threading
from collections.abc import Callable, Iterator
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from agente_nw.ponte import ID_EXTENSAO, ErroDaExtensao, Ponte, PonteIndisponivel


@pytest.fixture
def avisos() -> list[str]:
    return []


@pytest.fixture
def ponte(avisos: list[str]) -> Iterator[Ponte]:
    aberta = Ponte(
        porta=0,
        abrir_navegador=lambda _url: None,
        espera_conexao_s=0.6,
        long_poll_s=0.4,
        sem_contato_s=0.6,
        avisar=avisos.append,
    )
    aberta.iniciar()
    yield aberta
    aberta.fechar()


def _pagina_falsa(
    ponte: Ponte, responder: Callable[[dict[str, Any]], dict[str, Any] | None], tarefas: int = 99
) -> threading.Thread:
    """Faz o papel da página-ponte: busca tarefas, 'repassa à extensão' e devolve o resultado.
    `responder` devolvendo None = nunca responde (extensão travada)."""

    def laco() -> None:
        base = f"http://127.0.0.1:{ponte.porta}"
        atendidas = 0
        while atendidas < tarefas:
            try:
                with urlopen(f"{base}/tarefa?token={ponte.token}", timeout=5) as resposta:
                    dados = json.load(resposta)
            except OSError:
                return
            if not dados:
                continue
            atendidas += 1
            resultado = responder(dados["tarefa"])
            if resultado is None:
                continue
            corpo = json.dumps({"id": dados["id"], **resultado}).encode()
            pedido = Request(
                f"{base}/resultado?token={ponte.token}",
                data=corpo,
                method="POST",
                headers={"Content-Type": "application/json"},
            )
            urlopen(pedido, timeout=5).close()

    fio = threading.Thread(target=laco, daemon=True)
    fio.start()
    return fio


def test_tarefa_chega_a_pagina_e_a_resposta_libera_o_envio(ponte: Ponte) -> None:
    recebidas: list[dict[str, Any]] = []

    def responder(tarefa: dict[str, Any]) -> dict[str, Any]:
        recebidas.append(tarefa)
        return {"ok": True, "dados": {"versao": "1.0.0"}}

    _pagina_falsa(ponte, responder)

    dados = ponte.enviar({"acao": "ola"}, tempo_limite_s=5)

    assert dados == {"versao": "1.0.0"}
    assert recebidas == [{"acao": "ola"}]


def test_erro_da_extensao_vira_excecao_com_a_mensagem(ponte: Ponte) -> None:
    _pagina_falsa(ponte, lambda _t: {"ok": False, "erro": "endereço fora das redes permitidas"})

    with pytest.raises(ErroDaExtensao, match="fora das redes permitidas"):
        ponte.enviar({"acao": "abrir", "url": "https://exemplo.com"}, tempo_limite_s=5)


def test_token_errado_e_recusado_em_todos_os_endpoints(ponte: Ponte) -> None:
    base = f"http://127.0.0.1:{ponte.porta}"

    for caminho in ("/ponte", "/tarefa"):
        with pytest.raises(HTTPError) as erro:
            urlopen(f"{base}{caminho}?token=errado", timeout=5)
        assert erro.value.code == 403

    pedido = Request(f"{base}/resultado?token=errado", data=b"{}", method="POST")
    with pytest.raises(HTTPError) as erro_post:
        urlopen(pedido, timeout=5)
    assert erro_post.value.code == 403


def test_pagina_da_ponte_leva_o_token_e_o_id_da_extensao(ponte: Ponte) -> None:
    with urlopen(ponte.url, timeout=5) as resposta:
        html = resposta.read().decode()

    assert ponte.token in html
    assert ID_EXTENSAO in html
    assert "agente_nw — ponte" in html
    assert "__TOKEN__" not in html


def test_extensao_travada_estoura_o_tempo_limite_e_as_chamadas_seguintes_falham_na_hora(
    ponte: Ponte, avisos: list[str]
) -> None:
    _pagina_falsa(ponte, lambda _t: None)

    with pytest.raises(PonteIndisponivel, match="a tempo"):
        ponte.enviar({"acao": "ola"}, tempo_limite_s=0.5)
    with pytest.raises(PonteIndisponivel, match="a tempo"):
        ponte.enviar({"acao": "ola"}, tempo_limite_s=30)

    assert len(avisos) == 1
    assert "agente_nw extensao testar" in avisos[0]


def test_pagina_que_nunca_conecta_e_declarada_ausente(ponte: Ponte) -> None:
    with pytest.raises(PonteIndisponivel, match="não conectou"):
        ponte.enviar({"acao": "ola"}, tempo_limite_s=30)


def test_aba_da_ponte_fechada_no_meio_e_detectada_sem_esperar_o_tempo_limite(ponte: Ponte) -> None:
    fio = _pagina_falsa(ponte, lambda _t: {"ok": True, "dados": {}}, tarefas=1)
    ponte.enviar({"acao": "ola"}, tempo_limite_s=5)
    fio.join(timeout=5)

    with pytest.raises(PonteIndisponivel, match="fechada"):
        ponte.enviar({"acao": "ola"}, tempo_limite_s=30)


def test_navegador_so_e_aberto_uma_vez_na_primeira_tarefa(avisos: list[str]) -> None:
    abertas: list[str] = []
    aberta = Ponte(porta=0, abrir_navegador=abertas.append, long_poll_s=0.3, avisar=avisos.append)
    aberta.iniciar()
    try:
        assert abertas == []
        _pagina_falsa(aberta, lambda _t: {"ok": True, "dados": {}})
        aberta.enviar({"acao": "ola"}, tempo_limite_s=5)
        aberta.enviar({"acao": "ola"}, tempo_limite_s=5)
        assert abertas == [aberta.url]
    finally:
        aberta.fechar()
