from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from flask import Flask
from flask.testing import FlaskClient

import agente_nw.console.app as console_app
from agente_nw.nucleo.database.queries import (
    assunto_contato,
    gancho_uso,
    listas,
    pedidos,
    redes_sociais,
)
from agente_nw.nucleo.modelos.assunto_contato import AssuntoContato
from agente_nw.nucleo.modelos.lista_rede_social import EntradaLista
from agente_nw.nucleo.modelos.localizacao import Localizacao
from tests.test_console_novo_contato import _limiares
from tests.test_fluxo import AGORA, Cenario, _opcao

TEXTO = "Falar com a Marta sobre vela"


def _app(cenario: Cenario, executar: Callable[[Callable[[], None]], None] | None = None) -> FlaskClient:
    sincrono: Callable[[Callable[[], None]], None] = executar or (lambda tarefa: tarefa())
    app: Flask = console_app.criar_app(
        cenario.caminho,
        cenario.caminho.parent / "log.jsonl",
        object(),  # type: ignore[arg-type]
        _limiares(),
        "http://unused",
        dependencias=cenario.deps,
        executar=sincrono,
    )
    return app.test_client()


@pytest.fixture
def cenario(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Cenario:
    return Cenario(tmp_path, monkeypatch)


def _pedir(client: FlaskClient, texto: str = TEXTO) -> str:
    resposta = client.post("/pedir", data={"texto": texto})
    assert resposta.status_code == 302
    return str(resposta.headers["Location"])


def test_inicio_sem_pedido_mostra_a_caixa_e_os_exemplos(cenario: Cenario) -> None:
    resposta = _app(cenario).get("/")

    texto = resposta.get_data(as_text=True)
    assert resposta.status_code == 200
    assert "<textarea" in texto and "autofocus" in texto
    assert 'action="/pedir"' in texto
    assert "Exemplos:" in texto
    assert "Pessoas recentes" not in texto


def test_pedir_redireciona_para_o_pedido_e_a_pagina_mostra_os_ganchos(cenario: Cenario) -> None:
    cenario.contato(curar=True)
    client = _app(cenario)

    destino = _pedir(client)
    pagina = client.get(destino).get_data(as_text=True)

    assert destino == "/pedido/1"
    assert "Regata reúne veleiros" in pagina
    assert "Oi Marta, vi uma regata" in pagina
    assert "copiarMensagem" in pagina  # único JavaScript: copiar a mensagem
    assert ">Usei<" in pagina and ">Não serve<" in pagina
    assert "Corrigir" in pagina
    assert "Bastidores" in pagina


def test_pedido_em_andamento_mostra_a_etapa_e_se_atualiza_sozinho(cenario: Cenario) -> None:
    client = _app(cenario, executar=lambda _tarefa: None)  # o trabalho nem começa: fica na fila

    destino = _pedir(client)
    pagina = client.get(destino).get_data(as_text=True)

    assert "Na fila" in pagina
    assert '<meta http-equiv="refresh" content="5">' in pagina
    assert pedidos.obter_por_id(cenario.conn, 1).status == "na_fila"  # type: ignore[union-attr]


def test_texto_vazio_nao_cria_pedido(cenario: Cenario) -> None:
    client = _app(cenario)

    resposta = client.post("/pedir", data={"texto": "   "})

    assert resposta.status_code == 302
    assert pedidos.obter_ultimo(cenario.conn) is None


def test_confirmacao_da_pessoa_nos_desfechos_e_retomada(cenario: Cenario) -> None:
    perfil_id = cenario.contato()
    cenario.localizacao_por_rede = {
        "linkedin": Localizacao(
            status="claro", escolhido=_opcao("linkedin"), opcoes=[_opcao("linkedin")], rede="linkedin"
        ),
        "instagram": Localizacao(status="ambiguo", opcoes=[_opcao("instagram")], rede="instagram"),
    }
    client = _app(cenario)

    destino = _pedir(client)
    pagina = client.get(destino).get_data(as_text=True)

    assert "É esta pessoa?" in pagina
    assert "Mostrar a lista" in pagina
    assert "Cole o link do perfil certo" in pagina
    assert "Não tem perfil nesta rede" in pagina
    assert "Mais de uma pessoa combina" in pagina
    assert pedidos.obter_por_id(cenario.conn, 1).status == "aguardando_pessoa"  # type: ignore[union-attr]

    respostas = [
        {"rede": "linkedin", "acao": "sugerido"},
        {"rede": "instagram", "acao": "opcao", "indice": "0"},
        {"rede": "facebook", "acao": "sem_perfil"},
        {"rede": "x", "acao": "link", "link": "https://exemplo.com/nao-e-rede"},
    ]
    for dados in respostas:
        client.post("/pedido/1/pessoa", data=dados)

    assert pedidos.obter_por_id(cenario.conn, 1).status == "aguardando_pessoa"  # type: ignore[union-attr]
    invalido = {"rede": "x", "acao": "link", "link": "https://exemplo.com/x"}
    resposta = client.post("/pedido/1/pessoa", data=invalido)
    assert "erro=" in str(resposta.headers["Location"])  # a mensagem volta na URL do redirect

    client.post("/pedido/1/pessoa", data={"rede": "x", "acao": "pular"})

    gravado = pedidos.obter_por_id(cenario.conn, 1)
    assert gravado is not None and gravado.status == "concluido"
    gravadas = {r.rede for r in redes_sociais.listar_por_perfil(cenario.conn, perfil_id)}
    assert gravadas == {"linkedin", "instagram"}


def test_homonimos_mostram_os_contatos_e_a_escolha_retoma(cenario: Cenario) -> None:
    cenario.contato("Marta Quintela", curar=True)
    segundo = cenario.contato("Marta Quintela Neto", curar=True)
    client = _app(cenario)

    destino = _pedir(client)
    pagina = client.get(destino).get_data(as_text=True)

    assert "mais de um contato com esse nome" in pagina
    client.post("/pedido/1/pessoa", data={"tipo": "contato", "perfil_id": str(segundo)})
    gravado = pedidos.obter_por_id(cenario.conn, 1)
    assert gravado is not None and gravado.status == "concluido" and gravado.perfil_id == segundo


def test_lista_do_pedido_filtra_e_escolhe_por_botao(cenario: Cenario) -> None:
    cenario.contato()
    client = _app(cenario, executar=lambda _tarefa: None)
    _pedir(client)
    entradas = [
        EntradaLista(rede="linkedin", nome="Marta Quintela", cabecalho="Bancária", link="https://l.com/m"),
        EntradaLista(rede="linkedin", nome="Paulo Dias", cabecalho="Contador", link="https://l.com/paulo"),
    ]
    listas.substituir_lista(cenario.conn, "linkedin", entradas, AGORA)
    cenario.conn.commit()

    tudo = client.get("/pedido/1/lista?rede=linkedin").get_data(as_text=True)
    filtrada = client.get("/pedido/1/lista?rede=linkedin&filtro=contador").get_data(as_text=True)

    assert "Marta Quintela" in tudo and "Paulo Dias" in tudo
    assert "Paulo Dias" in filtrada and "Marta Quintela" not in filtrada
    assert 'name="link" value="https://l.com/paulo"' in filtrada


def test_marcar_usei_e_nao_serve_atualiza_o_gancho_e_o_motor(cenario: Cenario) -> None:
    perfil_id = cenario.contato(curar=True)
    client = _app(cenario)
    _pedir(client)
    consulta_id = pedidos.obter_por_id(cenario.conn, 1).consulta_id  # type: ignore[union-attr]
    assert consulta_id is not None
    assunto_contato.inserir(
        cenario.conn,
        AssuntoContato(
            assunto_id=cenario.assunto_id,
            perfil_id=perfil_id,
            gerado_em=AGORA[:10],
            tipo="conector",
            aderencia_contato=0.5,
            aderencia_usuario=0.0,
            conversavel=0.8,
            score=80.0,
            status="novo",
        ),
    )
    cenario.conn.commit()

    resposta = client.post(f"/pedido/1/gancho/{cenario.assunto_id}/usado")

    assert resposta.status_code == 302
    assert gancho_uso.listar_por_consulta(cenario.conn, consulta_id)[0][1] == "usado"
    assert cenario.assunto_id in assunto_contato.listar_assunto_ids_ja_vistos(cenario.conn, perfil_id)
    assert "usado" in client.get("/pedido/1").get_data(as_text=True)
    assert client.post(f"/pedido/1/gancho/{cenario.assunto_id}/qualquer").status_code == 400


def test_correcao_cria_outro_pedido_e_o_antigo_continua(cenario: Cenario) -> None:
    cenario.contato(curar=True)
    client = _app(cenario)
    _pedir(client)

    resposta = client.post("/pedido/1/corrigir", data={"correcao": "mais informal"})

    assert resposta.headers["Location"] == "/pedido/2"
    filho = pedidos.obter_por_id(cenario.conn, 2)
    assert filho is not None and filho.pedido_pai_id == 1 and filho.status == "concluido"
    assert pedidos.obter_por_id(cenario.conn, 1).status == "concluido"  # type: ignore[union-attr]
    assert client.post("/pedido/1/corrigir", data={"correcao": " "}).headers["Location"] == "/pedido/1"


def test_erro_aparece_como_pagina_com_tentar_de_novo(cenario: Cenario) -> None:
    cenario.cliente.falha = True
    client = _app(cenario)
    destino = _pedir(client)

    pagina = client.get(destino).get_data(as_text=True)

    assert "Deu errado" in pagina and "modelo fora do ar" in pagina
    assert "Tentar de novo" in pagina

    cenario.contato(curar=True)
    cenario.cliente.falha = False
    client.post("/pedido/1/tentar-de-novo")

    assert pedidos.obter_por_id(cenario.conn, 1).status == "concluido"  # type: ignore[union-attr]


def test_pagina_da_pessoa_mostra_o_que_a_ia_sabe_e_aceita_texto_e_troca_de_perfil(
    cenario: Cenario, monkeypatch: pytest.MonkeyPatch
) -> None:
    perfil_id = cenario.contato(curar=True)
    client = _app(cenario)
    _pedir(client)
    monkeypatch.setattr(console_app.extrator, "processar_fila", lambda *_a, **_k: None)
    monkeypatch.setattr(console_app, "ClienteOllama", lambda *_a, **_k: object())

    pagina = client.get(f"/pessoa/{perfil_id}").get_data(as_text=True)

    assert "Marta Quintela" in pagina
    assert "linkedin.com/in/marta" in pagina
    assert "x: você disse que não tem perfil" in pagina
    assert "Falar com a Marta sobre vela" in pagina  # pedidos anteriores

    client.post(f"/pessoa/{perfil_id}/contar", data={"texto": "Mudou para Curitiba."})
    fila = cenario.conn.execute("SELECT texto, origem FROM fila_extracao").fetchall()
    assert [(linha["texto"], linha["origem"]) for linha in fila] == [("Mudou para Curitiba.", "manual")]

    ruim = client.post(f"/pessoa/{perfil_id}/trocar-perfil", data={"link": "https://exemplo.com/x"})
    assert "erro=" in str(ruim.headers["Location"])
    client.post(f"/pessoa/{perfil_id}/trocar-perfil", data={"link": "https://www.linkedin.com/in/marta-nova"})
    links = {r.link for r in redes_sociais.listar_por_perfil(cenario.conn, perfil_id) if r.rede == "linkedin"}
    assert links == {"https://www.linkedin.com/in/marta-nova"}


def test_inicio_lista_as_pessoas_recentes_e_as_telas_antigas_seguem_no_ar(cenario: Cenario) -> None:
    cenario.contato(curar=True)
    client = _app(cenario)
    _pedir(client)

    inicio = client.get("/").get_data(as_text=True)

    assert "Pessoas recentes" in inicio and "Marta Quintela" in inicio
    assert "Exemplos:" not in inicio  # só na primeira visita
    for rota in ("/contatos", "/menu", "/temas"):
        assert client.get(rota).status_code == 200
