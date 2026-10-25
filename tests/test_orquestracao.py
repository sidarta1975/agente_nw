from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

import agente_nw.cli as cli
from agente_nw.nucleo import fluxo as fluxo_mod
from agente_nw.nucleo import orquestracao
from agente_nw.nucleo import redacao as redacao_mod
from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import listas, pedidos, perfis, redes_sociais
from agente_nw.nucleo.llm import FalhaJsonInvalido
from agente_nw.nucleo.modelos.lista_rede_social import EntradaLista
from agente_nw.nucleo.modelos.localizacao import Localizacao, Opcao
from agente_nw.nucleo.modelos.pedido import PedidoExtraido, ResultadoPedido
from agente_nw.nucleo.modelos.redacao import Redacao
from agente_nw.nucleo.orquestracao import Desfecho, Encaminhamento
from tests.test_console_novo_contato import _limiares

AGORA = "2026-10-25T10:00:00+00:00"
LINK_A = "https://www.linkedin.com/in/marta-a"
LINK_B = "https://www.linkedin.com/in/marta-b"
LINK_COLADO = "https://www.linkedin.com/in/marta-colada"


def _opcao(link: str, nome: str = "Marta Quintela") -> Opcao:
    return Opcao(rede="linkedin", nome=nome, cabecalho="Bancária", link=link, fonte="lista")


def _extraido() -> PedidoExtraido:
    return PedidoExtraido(
        pessoa_nome="Marta Quintela",
        objetivo="retomar",
        objetivo_texto="retomar o contato",
        meio="whatsapp",
        registro="cordial",
        assunto_principal="vela",
        termos_busca=["vela"],
        confianca=0.9,
    )


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(aberta)
    return aberta


# ---- a decisão claro / ambíguo / nenhum, num lugar só ---------------------------------------------------


@pytest.mark.parametrize(
    ("localizacao", "sem_perguntar", "esperado"),
    [
        (Localizacao("claro", _opcao(LINK_A), [_opcao(LINK_A)]), False, Encaminhamento.CONFIRMAR_ESCOLHIDO),
        (Localizacao("claro", _opcao(LINK_A), [_opcao(LINK_A)]), True, Encaminhamento.GRAVAR_ESCOLHIDO),
        (Localizacao("ambiguo", None, [_opcao(LINK_A)]), False, Encaminhamento.CONFIRMAR_UNICA),
        (Localizacao("nenhum", None, [_opcao(LINK_A)], "busca_geral"), False, Encaminhamento.CONFIRMAR_UNICA),
        (
            Localizacao("ambiguo", None, [_opcao(LINK_A), _opcao(LINK_B)]),
            False,
            Encaminhamento.ESCOLHER,
        ),
        (Localizacao("nenhum", None, []), False, Encaminhamento.PEDIR_LINK),
        (Localizacao("ambiguo", None, [_opcao(LINK_A), _opcao(LINK_B)]), True, Encaminhamento.PULAR),
        (Localizacao("nenhum", None, []), True, Encaminhamento.PULAR),
        (Localizacao("claro", None, [_opcao(LINK_A), _opcao(LINK_B)]), False, Encaminhamento.ESCOLHER),
    ],
)
def test_encaminhamento_da_localizacao(
    localizacao: Localizacao, sem_perguntar: bool, esperado: Encaminhamento
) -> None:
    assert orquestracao.encaminhar_localizacao(localizacao, sem_perguntar) is esperado


# ---- a ordem das decisões depois de entender o pedido ---------------------------------------------------


class CanalFalso:
    """Registra o que o orquestrador pede ao canal, na ordem."""

    def __init__(self, respostas: dict[str, Desfecho] | None = None) -> None:
        self.chamadas: list[str] = []
        self.respostas = respostas or {}

    def _responder(self, nome: str) -> Desfecho:
        self.chamadas.append(nome)
        return self.respostas.get(nome, Desfecho.SEGUIR)

    def avisar(self, texto: str) -> None:
        self.chamadas.append(f"avisar:{texto}")

    def pedido_entendido(self, resultado: ResultadoPedido) -> None:
        self.chamadas.append("pedido_entendido")

    def localizacoes(self, resultado: ResultadoPedido) -> Desfecho:
        return self._responder("localizacoes")

    def contato_divergente(self, resultado: ResultadoPedido) -> Desfecho:
        return self._responder("contato_divergente")

    def contato_ambiguo(self, resultado: ResultadoPedido) -> Desfecho:
        return self._responder("contato_ambiguo")

    def sem_pessoa(self, resultado: ResultadoPedido) -> Desfecho:
        return self._responder("sem_pessoa")

    def consulta_pronta(self, consulta: Any) -> bool:
        self.chamadas.append("consulta_pronta")
        return "consulta_pronta" not in self.respostas

    def redigindo(self) -> None:
        self.chamadas.append("redigindo")


def _resultado(conn: sqlite3.Connection, **mudancas: Any) -> ResultadoPedido:
    contato = perfis.inserir_novo_contato(conn, "Marta Quintela", None, None, AGORA)
    base: dict[str, Any] = {"pedido_id": 1, "pedido": _extraido(), "perfil": contato}
    return ResultadoPedido(**{**base, **mudancas})


def test_pedido_limpo_segue_sem_perguntar_nada(conn: sqlite3.Connection) -> None:
    canal = CanalFalso()

    desfecho = orquestracao.encaminhar_pedido(_resultado(conn), canal)

    assert desfecho is Desfecho.SEGUIR
    assert canal.chamadas == ["pedido_entendido"]


def test_localizacao_pendente_chama_o_canal_e_espera_se_ele_mandar(conn: sqlite3.Connection) -> None:
    pendente = [Localizacao("ambiguo", None, [_opcao(LINK_A)], rede="linkedin")]
    canal = CanalFalso({"localizacoes": Desfecho.ESPERAR})

    desfecho = orquestracao.encaminhar_pedido(_resultado(conn, localizacoes=pendente), canal)

    assert desfecho is Desfecho.ESPERAR
    assert canal.chamadas == ["pedido_entendido", "localizacoes"]


def test_sem_preparar_o_orquestrador_para_depois_da_localizacao(conn: sqlite3.Connection) -> None:
    pendente = [Localizacao("nenhum", None, [], rede="linkedin")]
    canal = CanalFalso()

    desfecho = orquestracao.encaminhar_pedido(
        _resultado(conn, localizacoes=pendente, contato_ambiguo=True), canal, seguir_para_redacao=False
    )

    assert desfecho is Desfecho.PARAR
    assert canal.chamadas == ["pedido_entendido", "localizacoes"]


def test_divergente_vem_antes_do_ambiguo_e_pode_parar(conn: sqlite3.Connection) -> None:
    canal = CanalFalso({"contato_divergente": Desfecho.PARAR})

    desfecho = orquestracao.encaminhar_pedido(
        _resultado(conn, contato_divergente=True, contato_ambiguo=True), canal
    )

    assert desfecho is Desfecho.PARAR
    assert canal.chamadas == ["pedido_entendido", "contato_divergente"]


def test_ambiguo_pergunta_o_contato(conn: sqlite3.Connection) -> None:
    canal = CanalFalso({"contato_ambiguo": Desfecho.ESPERAR})

    desfecho = orquestracao.encaminhar_pedido(_resultado(conn, contato_ambiguo=True), canal)

    assert desfecho is Desfecho.ESPERAR
    assert canal.chamadas == ["pedido_entendido", "contato_ambiguo"]


def test_sem_pessoa_avisa_e_segue_o_que_o_canal_mandar(conn: sqlite3.Connection) -> None:
    sem_pessoa = ResultadoPedido(pedido_id=1, pedido=_extraido(), perfil=None)

    parou = CanalFalso({"sem_pessoa": Desfecho.PARAR})
    assert orquestracao.encaminhar_pedido(sem_pessoa, parou) is Desfecho.PARAR
    assert parou.chamadas == ["pedido_entendido", "sem_pessoa"]

    seguiu = CanalFalso()
    assert orquestracao.encaminhar_pedido(sem_pessoa, seguiu) is Desfecho.SEGUIR


# ---- preparar + redigir ---------------------------------------------------------------------------------


def _entregar(
    canal: CanalFalso, preparar: Callable[..., Any], conn: sqlite3.Connection, tmp_path: Path
) -> Any:
    resultado = _resultado(conn)
    assert resultado.perfil is not None
    with httpx.Client(transport=httpx.MockTransport(lambda _r: httpx.Response(200))) as cliente_http:
        return orquestracao.preparar_e_redigir(
            canal,
            preparar=preparar,
            conexao=conn,
            cliente_llm=object(),
            cliente_http=cliente_http,
            perfil=resultado.perfil,
            extraido=resultado.pedido,
            texto="Falar com a Marta sobre vela",
            limiares=_limiares(),
            caminho_fontes=tmp_path / "fontes.yaml",
            caminho_sentinela=tmp_path / "PARE",
            abrir_pagina=lambda _p: None,
            pasta_navegador=tmp_path / "navegador",
            limite_tokens=6000,
            rodar_coleta=False,
            ler_redes_sociais=False,
        )


def test_preparar_e_redigir_chama_na_ordem_e_registra(
    conn: sqlite3.Connection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    canal = CanalFalso()
    chamadas_preparar: list[dict[str, Any]] = []
    registrado: list[int] = []

    def preparar(**kwargs: Any) -> Any:
        chamadas_preparar.append(kwargs)
        kwargs["avisar"]("AVISO: teste")
        return SimpleNamespace(consulta_id=7)

    monkeypatch.setattr(redacao_mod, "redigir", lambda *_a, **_k: Redacao(registro_usado="cordial"))
    monkeypatch.setattr(redacao_mod, "registrar", lambda _c, consulta_id, *_a: registrado.append(consulta_id))

    entrega = _entregar(canal, preparar, conn, tmp_path)

    assert canal.chamadas == ["avisar:AVISO: teste", "consulta_pronta", "redigindo"]
    assert registrado == [7]
    assert entrega.consulta.consulta_id == 7
    assert entrega.redacao.registro_usado == "cordial"
    assert chamadas_preparar[0]["rodar_coleta"] is False
    assert chamadas_preparar[0]["ler_redes_sociais"] is False
    assert chamadas_preparar[0]["contexto"].assunto == "vela"


def test_canal_que_nao_quer_a_redacao_encerra_depois_da_consulta(
    conn: sqlite3.Connection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    canal = CanalFalso({"consulta_pronta": Desfecho.PARAR})
    chamou: list[bool] = []
    monkeypatch.setattr(redacao_mod, "redigir", lambda *_a, **_k: chamou.append(True))

    entrega = _entregar(canal, lambda **_k: SimpleNamespace(consulta_id=1), conn, tmp_path)

    assert entrega is None
    assert chamou == []
    assert canal.chamadas == ["consulta_pronta"]


def test_json_invalido_na_redacao_vira_falha_na_redacao(
    conn: sqlite3.Connection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def redigir(*_a: Any, **_k: Any) -> Redacao:
        raise FalhaJsonInvalido("redigir_ganchos", 1, "saída quebrada")

    monkeypatch.setattr(redacao_mod, "redigir", redigir)

    with pytest.raises(orquestracao.FalhaNaRedacao):
        _entregar(CanalFalso(), lambda **_k: SimpleNamespace(consulta_id=1), conn, tmp_path)


# ---- os dois canais chegam ao mesmo resultado nos três desfechos ----------------------------------------


def _terminal(conn: sqlite3.Connection, respostas: list[str]) -> cli.CanalTerminal:
    iterador = iter(respostas)
    return cli.CanalTerminal(conn, "frase", AGORA, entrada=lambda _p: next(iterador))


def _web(conn: sqlite3.Connection, pedido_id: int) -> fluxo_mod.CanalWeb:
    return fluxo_mod.CanalWeb(conn, pedido_id)


def _pedido_gravado(conn: sqlite3.Connection, perfil_id: int) -> int:
    pedido_id = pedidos.inserir(conn, "frase", AGORA, status="processando")
    pedidos.gravar_resolucao(conn, pedido_id, perfil_id, False, False)
    conn.commit()
    return pedido_id


def _redes(conn: sqlite3.Connection, perfil_id: int) -> list[tuple[str, str]]:
    return [(r.rede, r.link) for r in redes_sociais.listar_por_perfil(conn, perfil_id)]


@pytest.fixture
def com_lista(conn: sqlite3.Connection) -> None:
    entradas = [EntradaLista(rede="linkedin", nome="Marta Quintela", cabecalho="Bancária", link=LINK_A)]
    listas.substituir_lista(conn, "linkedin", entradas, AGORA)
    conn.commit()


def test_claro_pergunta_o_mesmo_e_grava_o_mesmo_nos_dois_canais(
    conn: sqlite3.Connection, com_lista: None
) -> None:
    claro = Localizacao("claro", _opcao(LINK_A), [_opcao(LINK_A)], rede="linkedin")

    contato_t = perfis.inserir_novo_contato(conn, "Marta T", None, None, AGORA)
    assert contato_t.id is not None
    resultado_t = ResultadoPedido(1, _extraido(), contato_t, localizacoes=[claro])
    assert orquestracao.encaminhar_pedido(resultado_t, _terminal(conn, ["S"])) is Desfecho.SEGUIR

    contato_w = perfis.inserir_novo_contato(conn, "Marta W", None, None, AGORA)
    assert contato_w.id is not None
    pedido_id = _pedido_gravado(conn, contato_w.id)
    resultado_w = ResultadoPedido(pedido_id, _extraido(), contato_w, localizacoes=[claro])
    assert orquestracao.encaminhar_pedido(resultado_w, _web(conn, pedido_id)) is Desfecho.ESPERAR
    pergunta = fluxo_mod.perguntas_pendentes(pedidos.obter_por_id(conn, pedido_id))  # type: ignore[arg-type]
    assert pergunta == [fluxo_mod.pergunta_de_rede(claro)]
    assert fluxo_mod.decidir_rede(conn, pedido_id, "linkedin", "sugerido", AGORA) is None

    assert _redes(conn, contato_t.id) == _redes(conn, contato_w.id) == [("linkedin", LINK_A)]


def test_ambiguo_pergunta_o_mesmo_e_grava_o_mesmo_nos_dois_canais(
    conn: sqlite3.Connection, com_lista: None
) -> None:
    ambiguo = Localizacao(
        "ambiguo", None, [_opcao(LINK_A), _opcao(LINK_B, "Marta Quintela Dias")], rede="linkedin"
    )

    contato_t = perfis.inserir_novo_contato(conn, "Marta T", None, None, AGORA)
    assert contato_t.id is not None
    resultado_t = ResultadoPedido(1, _extraido(), contato_t, localizacoes=[ambiguo])
    assert orquestracao.encaminhar_pedido(resultado_t, _terminal(conn, ["2"])) is Desfecho.SEGUIR

    contato_w = perfis.inserir_novo_contato(conn, "Marta W", None, None, AGORA)
    assert contato_w.id is not None
    pedido_id = _pedido_gravado(conn, contato_w.id)
    resultado_w = ResultadoPedido(pedido_id, _extraido(), contato_w, localizacoes=[ambiguo])
    assert orquestracao.encaminhar_pedido(resultado_w, _web(conn, pedido_id)) is Desfecho.ESPERAR
    pergunta = fluxo_mod.perguntas_pendentes(pedidos.obter_por_id(conn, pedido_id))  # type: ignore[arg-type]
    assert pergunta == [fluxo_mod.pergunta_de_rede(ambiguo)]
    assert fluxo_mod.decidir_rede(conn, pedido_id, "linkedin", "opcao", AGORA, indice=1) is None

    assert _redes(conn, contato_t.id) == _redes(conn, contato_w.id) == [("linkedin", LINK_B)]


def test_nenhum_aceita_link_colado_ou_pular_nos_dois_canais(conn: sqlite3.Connection) -> None:
    nenhum = Localizacao("nenhum", None, [], rede="linkedin")

    colado_t = perfis.inserir_novo_contato(conn, "Marta T", None, None, AGORA)
    colado_w = perfis.inserir_novo_contato(conn, "Marta W", None, None, AGORA)
    pulado_t = perfis.inserir_novo_contato(conn, "Marta PT", None, None, AGORA)
    pulado_w = perfis.inserir_novo_contato(conn, "Marta PW", None, None, AGORA)
    assert None not in (colado_t.id, colado_w.id, pulado_t.id, pulado_w.id)

    for contato, resposta in ((colado_t, LINK_COLADO), (pulado_t, "")):
        resultado = ResultadoPedido(1, _extraido(), contato, localizacoes=[nenhum])
        assert orquestracao.encaminhar_pedido(resultado, _terminal(conn, [resposta])) is Desfecho.SEGUIR

    for contato, acao, link in ((colado_w, "link", LINK_COLADO), (pulado_w, "pular", "")):
        assert contato.id is not None
        pedido_id = _pedido_gravado(conn, contato.id)
        resultado = ResultadoPedido(pedido_id, _extraido(), contato, localizacoes=[nenhum])
        assert orquestracao.encaminhar_pedido(resultado, _web(conn, pedido_id)) is Desfecho.ESPERAR
        assert fluxo_mod.decidir_rede(conn, pedido_id, "linkedin", acao, AGORA, link=link) is None

    assert colado_t.id and colado_w.id and pulado_t.id and pulado_w.id
    assert _redes(conn, colado_t.id) == _redes(conn, colado_w.id) == [("linkedin", LINK_COLADO)]
    assert _redes(conn, pulado_t.id) == _redes(conn, pulado_w.id) == []


# ---- o SQL que saiu de fluxo.py e localizacao.py continua devolvendo o mesmo ----------------------------


def test_marcar_interrompidos_continua_marcando_so_o_que_nao_terminou(conn: sqlite3.Connection) -> None:
    na_fila = pedidos.inserir(conn, "a", AGORA, status="na_fila")
    processando = pedidos.inserir(conn, "b", AGORA, status="processando")
    concluido = pedidos.inserir(conn, "c", AGORA, status="concluido")
    conn.commit()

    assert fluxo_mod.marcar_interrompidos(conn) == 2

    for pedido_id, status in ((na_fila, "erro"), (processando, "erro"), (concluido, "concluido")):
        gravado = pedidos.obter_por_id(conn, pedido_id)
        assert gravado is not None and gravado.status == status
    interrompido = pedidos.obter_por_id(conn, na_fila)
    assert interrompido is not None and interrompido.erro == "O console foi encerrado durante o pedido."


def test_opcao_do_link_usa_o_cabecalho_da_lista_quando_o_link_esta_nela(
    conn: sqlite3.Connection, com_lista: None
) -> None:
    from agente_nw.nucleo import localizacao as localizacao_mod

    na_lista = localizacao_mod.opcao_do_link(conn, LINK_A)
    assert na_lista == Opcao(
        rede="linkedin", nome="Marta Quintela", cabecalho="Bancária", link=LINK_A, fonte="link_colado"
    )
    fora = localizacao_mod.opcao_do_link(conn, LINK_COLADO)
    assert fora == Opcao(
        rede="linkedin", nome=LINK_COLADO, cabecalho="", link=LINK_COLADO, fonte="link_colado"
    )
    assert localizacao_mod.opcao_do_link(conn, "https://exemplo.test/x") is None


# ---- brief 059: homônimos no terminal, falha em preparar e texto único ----------------------------------


class _LLMDoTerminal:
    def __init__(self, nome: str = "Otávio") -> None:
        self.nome = nome

    def gerar_json(self, tarefa_nome: str, prompt: str, esquema: Any) -> Any:
        return PedidoExtraido(
            pessoa_nome=self.nome,
            objetivo="retomar",
            objetivo_texto="retomar o contato",
            meio="whatsapp",
            registro="cordial",
            assunto_principal="seguros",
            termos_busca=["seguros"],
            confianca=0.9,
        )


@pytest.fixture
def terminal(
    conn: sqlite3.Connection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> list[dict[str, Any]]:
    """O terminal com o LLM, a rede e a consulta simulados. Devolve as chamadas a `preparar`."""
    from agente_nw.nucleo import consulta as consulta_mod

    chamadas: list[dict[str, Any]] = []

    def preparar(**kwargs: Any) -> Any:
        chamadas.append(kwargs)
        return SimpleNamespace(
            consulta_id=1, fonte_noticias="google", google_bloqueado_ate=None, aviso=None, itens_menu=[]
        )

    monkeypatch.setattr(cli, "banco", lambda: conn)
    monkeypatch.setattr(cli, "llm", lambda: _LLMDoTerminal())
    monkeypatch.setattr(cli, "http", lambda: httpx.Client(transport=httpx.MockTransport(lambda _r: None)))
    monkeypatch.setattr(cli, "_contexto_de_navegacao", lambda *_a, **_k: None)
    monkeypatch.setattr(consulta_mod, "preparar", preparar)
    monkeypatch.setattr(redacao_mod, "redigir", lambda *_a, **_k: Redacao(registro_usado="cordial"))
    monkeypatch.setattr(redacao_mod, "registrar", lambda *_a, **_k: None)
    return chamadas


def _dois_otavios(conn: sqlite3.Connection) -> None:
    perfis.inserir_novo_contato(conn, "Otávio Alves", None, None, AGORA)
    perfis.inserir_novo_contato(conn, "Otávio Souza", None, None, AGORA)
    conn.commit()


def test_homonimos_no_terminal_interativo_listam_e_seguem_com_o_numero(
    conn: sqlite3.Connection, terminal: list[dict[str, Any]], capsys: pytest.CaptureFixture[str]
) -> None:
    import re

    _dois_otavios(conn)
    perguntas: list[str] = []

    def responder(pergunta: str) -> str:
        perguntas.append(pergunta)
        return "2"

    assert cli.pedir_cmd("Almoço com o Otávio", True, False, None, entrada=responder) == 0

    saida = capsys.readouterr().out
    assert "Há mais de um contato chamado Otávio. Qual deles?" in saida
    linha_2 = next(linha for linha in saida.splitlines() if linha.startswith("  2. "))
    escolhido = int(re.search(r"#(\d+)", linha_2).group(1))  # type: ignore[union-attr]
    assert len(perguntas) == 1
    assert [c["perfil_id"] for c in terminal] == [escolhido]
    assert "Ganchos para" in saida


def test_homonimos_com_sem_perguntar_ficam_como_hoje(
    conn: sqlite3.Connection, terminal: list[dict[str, Any]], capsys: pytest.CaptureFixture[str]
) -> None:
    _dois_otavios(conn)

    assert cli.pedir_cmd("Almoço com o Otávio", True, False, None, sem_perguntar=True) == 0

    saida = capsys.readouterr().out
    assert "AVISO: encontrei 2 contatos chamados Otávio" in saida
    assert "escolha um com --contato" in saida
    assert terminal == []


def test_homonimos_com_json_seguem_com_o_palpite(
    conn: sqlite3.Connection, terminal: list[dict[str, Any]], capsys: pytest.CaptureFixture[str]
) -> None:
    _dois_otavios(conn)

    assert cli.pedir_cmd("Almoço com o Otávio", True, True, None) == 0

    assert len(terminal) == 1
    assert "Qual deles?" not in capsys.readouterr().out


def test_falha_de_json_em_preparar_mostra_falha_e_sai_com_erro(
    conn: sqlite3.Connection,
    terminal: list[dict[str, Any]],
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agente_nw.nucleo import consulta as consulta_mod

    def quebra(**_kwargs: Any) -> Any:
        raise FalhaJsonInvalido("extrair_termos_contato", 3, "saída quebrada")

    monkeypatch.setattr(consulta_mod, "preparar", quebra)

    assert cli.pedir_cmd("Almoço com o Otávio", True, False, None) == 1

    saida = capsys.readouterr().out
    assert "FALHA: não consegui preparar a consulta" in saida
    assert "saída quebrada" in saida


def test_pedido_sem_pessoa_tem_o_mesmo_texto_nos_dois_canais(
    conn: sqlite3.Connection,
    terminal: list[dict[str, Any]],
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tests.test_fluxo import Cenario

    monkeypatch.setattr(cli, "llm", lambda: _LLMDoTerminal(nome=""))
    assert cli.pedir_cmd("Um assunto geral", True, False, None) == 0
    assert f"AVISO: {orquestracao.SEM_PESSOA}" in capsys.readouterr().out

    cenario = Cenario(tmp_path, monkeypatch)
    cenario.cliente.nome = ""
    pedido_id = cenario.pedido("Um assunto geral")
    fluxo_mod.executar_pedido(cenario.deps, pedido_id)
    gravado = cenario.ler(pedido_id)
    assert gravado.avisos_json is not None and orquestracao.SEM_PESSOA in gravado.avisos_json
