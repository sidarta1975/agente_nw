from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pytest

import agente_nw.cli as cli
from agente_nw.nucleo import fluxo as fluxo_mod
from agente_nw.nucleo import orquestracao
from agente_nw.nucleo.database.queries import pedidos, perfis
from agente_nw.nucleo.modelos.pedido import PedidoExtraido
from tests.llm_falso import ProvenienciaFalsa
from tests.test_fluxo import AGORA, Cenario


@pytest.fixture
def cenario(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Cenario:
    return Cenario(tmp_path, monkeypatch)


def _pedido_com_contato_forcado(cenario: Cenario, nome_do_contato: str) -> int:
    """Pedido sobre "Marta Quintela" (o que o LLM falso devolve) com um contato já escolhido."""
    perfil_id = cenario.contato(nome_do_contato, curar=True)
    pedido_id = cenario.pedido()
    pedidos.gravar_resolucao(cenario.conn, pedido_id, perfil_id, False, False)
    cenario.conn.commit()
    return pedido_id


def _perguntas(cenario: Cenario, pedido_id: int) -> list[dict[str, Any]]:
    return fluxo_mod.perguntas_pendentes(cenario.ler(pedido_id))


# ---- console -------------------------------------------------------------------------------------------


def test_console_contato_forcado_com_nome_que_nao_bate_pergunta_antes_de_seguir(cenario: Cenario) -> None:
    pedido_id = _pedido_com_contato_forcado(cenario, "Joaquim Bastos")

    fluxo_mod.executar_pedido(cenario.deps, pedido_id)

    gravado = cenario.ler(pedido_id)
    assert gravado.status == "aguardando_pessoa"
    assert cenario.chamadas_preparar == []
    (pergunta,) = _perguntas(cenario, pedido_id)
    assert pergunta["tipo"] == "divergencia"
    assert pergunta["nome_pedido"] == "Marta Quintela"
    assert pergunta["contato"]["nome"] == "Joaquim Bastos"


def test_console_sim_segue_o_pedido_ate_a_redacao(cenario: Cenario) -> None:
    pedido_id = _pedido_com_contato_forcado(cenario, "Joaquim Bastos")
    fluxo_mod.executar_pedido(cenario.deps, pedido_id)

    assert fluxo_mod.decidir_divergencia(cenario.conn, pedido_id, True) is None
    assert fluxo_mod.sem_perguntas(cenario.conn, pedido_id)
    fluxo_mod.retomar_apos_divergencia(cenario.deps, pedido_id)

    assert cenario.ler(pedido_id).status == "concluido"
    assert len(cenario.chamadas_preparar) == 1
    # A leitura de rede social relevante acontece (não é correção) e a curadoria já feita em pedidos
    # anteriores não é refeita: a retomada por `_entender` não repergunta o que já está curado.
    assert cenario.chamadas_preparar[0]["ler_redes_sociais"] is True
    assert cenario.redes_localizadas == []


# ---- curadoria de rede social depois do "Sim" (brief 071) ----------------------------------------------


def test_sim_na_divergencia_volta_a_curar_as_redes_sociais(cenario: Cenario) -> None:
    """O contato está certo depois do "Sim", mas as redes dele nunca foram curadas neste pedido: a
    retomada passa de novo por `_entender`, então a pergunta de rede aparece em vez de o pedido ir
    direto para a redação (decisão [059-3])."""
    perfil_id = cenario.contato("Joaquim Bastos")  # sem curar: toda rede está pendente
    pedido_id = cenario.pedido()
    pedidos.gravar_resolucao(cenario.conn, pedido_id, perfil_id, False, False)
    cenario.conn.commit()
    fluxo_mod.executar_pedido(cenario.deps, pedido_id)
    assert cenario.redes_localizadas == []  # divergência pausa antes de procurar rede nenhuma

    assert fluxo_mod.decidir_divergencia(cenario.conn, pedido_id, True) is None
    fluxo_mod.retomar_apos_divergencia(cenario.deps, pedido_id)

    gravado = cenario.ler(pedido_id)
    assert gravado.status == "aguardando_pessoa"
    assert cenario.redes_localizadas != []  # prova de que `_entender` rodou de novo
    assert {p["tipo"] for p in _perguntas(cenario, pedido_id)} == {"rede"}
    assert cenario.chamadas_preparar == []  # não foi para a redação sem perguntar


def test_sim_na_divergencia_nao_repete_a_pergunta_de_divergencia(cenario: Cenario) -> None:
    """Na segunda passada o contato já está confirmado pelo usuário: a divergência de nome continua
    existindo (o pedido fala de outra pessoa), mas não pode virar pergunta de novo."""
    perfil_id = cenario.contato("Joaquim Bastos", curar=True)
    pedido_id = cenario.pedido()
    pedidos.gravar_resolucao(cenario.conn, pedido_id, perfil_id, False, False)
    perfis.inserir_novo_contato(cenario.conn, "Marta Quintela Dias", None, None, AGORA)
    cenario.conn.commit()
    fluxo_mod.executar_pedido(cenario.deps, pedido_id)

    assert fluxo_mod.decidir_divergencia(cenario.conn, pedido_id, True) is None
    fluxo_mod.retomar_apos_divergencia(cenario.deps, pedido_id)

    tipos = {p["tipo"] for p in _perguntas(cenario, pedido_id)}
    assert "divergencia" not in tipos
    assert cenario.ler(pedido_id).perfil_id == perfil_id


def test_rota_do_console_apos_o_sim_despacha_a_curadoria_de_rede(cenario: Cenario) -> None:
    """A escolha do despacho é da rota: era ela que mandava `continuar=True` e pulava a curadoria."""
    from tests.test_console_tela_unica import _app

    perfil_id = cenario.contato("Joaquim Bastos")  # sem curar
    pedido_id = cenario.pedido()
    pedidos.gravar_resolucao(cenario.conn, pedido_id, perfil_id, False, False)
    cenario.conn.commit()
    client = _app(cenario)
    fluxo_mod.executar_pedido(cenario.deps, pedido_id)
    assert cenario.redes_localizadas == []

    client.post(f"/pedido/{pedido_id}/pessoa", data={"tipo": "divergencia", "resposta": "sim"})

    assert cenario.redes_localizadas != []  # a rota retomou por `_entender`, não por `_escrever`
    assert cenario.chamadas_preparar == []
    assert {p["tipo"] for p in _perguntas(cenario, pedido_id)} == {"rede"}


def test_resposta_de_rede_continua_indo_direto_para_a_redacao(cenario: Cenario) -> None:
    """Não regressão do caminho correto que já existia: quando a pergunta pendente era de rede, a
    localização já foi resolvida, então a retomada é `continuar_pedido` e não repassa por `_entender`."""
    cenario.contato()  # nome que bate com o do pedido: sem divergência
    pedido_id = cenario.pedido()
    fluxo_mod.executar_pedido(cenario.deps, pedido_id)
    assert cenario.ler(pedido_id).status == "aguardando_pessoa"
    passadas_de_entender = len(cenario.cliente.frases)

    for pergunta in _perguntas(cenario, pedido_id):
        assert fluxo_mod.decidir_rede(cenario.conn, pedido_id, pergunta["rede"], "pular", AGORA) is None
    assert fluxo_mod.sem_perguntas(cenario.conn, pedido_id)
    fluxo_mod.continuar_pedido(cenario.deps, pedido_id)

    assert cenario.ler(pedido_id).status == "concluido"
    assert len(cenario.cliente.frases) == passadas_de_entender  # `_entender` não rodou de novo


def test_console_nao_mostra_os_contatos_parecidos(cenario: Cenario) -> None:
    pedido_id = _pedido_com_contato_forcado(cenario, "Joaquim Bastos")
    primeira = perfis.inserir_novo_contato(cenario.conn, "Marta Quintela Dias", None, None, AGORA)
    segunda = perfis.inserir_novo_contato(cenario.conn, "Marta Quintela Souza", None, None, AGORA)
    cenario.conn.commit()
    fluxo_mod.executar_pedido(cenario.deps, pedido_id)

    assert fluxo_mod.decidir_divergencia(cenario.conn, pedido_id, False) is None

    gravado = cenario.ler(pedido_id)
    assert gravado.status == "aguardando_pessoa"
    (pergunta,) = _perguntas(cenario, pedido_id)
    assert pergunta["tipo"] == "contato"
    assert {c["perfil_id"] for c in pergunta["candidatos"]} == {primeira.id, segunda.id}
    assert cenario.chamadas_preparar == []

    assert fluxo_mod.decidir_contato(cenario.conn, pedido_id, segunda.id or 0) is None
    assert cenario.ler(pedido_id).perfil_id == segunda.id


def test_console_nao_sem_contatos_parecidos_recomeca_sem_o_contato_forcado(cenario: Cenario) -> None:
    pedido_id = _pedido_com_contato_forcado(cenario, "Joaquim Bastos")
    fluxo_mod.executar_pedido(cenario.deps, pedido_id)

    assert fluxo_mod.decidir_divergencia(cenario.conn, pedido_id, False) is None

    gravado = cenario.ler(pedido_id)
    assert gravado.status == "na_fila"
    assert gravado.perfil_id is None
    assert _perguntas(cenario, pedido_id) == []


def test_console_nome_que_bate_nao_pergunta_nada(cenario: Cenario) -> None:
    pedido_id = _pedido_com_contato_forcado(cenario, "Marta Quintela")

    fluxo_mod.executar_pedido(cenario.deps, pedido_id)

    assert cenario.ler(pedido_id).status == "concluido"
    assert _perguntas(cenario, pedido_id) == []


def test_resposta_repetida_a_divergencia_e_ignorada(cenario: Cenario) -> None:
    pedido_id = _pedido_com_contato_forcado(cenario, "Joaquim Bastos")
    fluxo_mod.executar_pedido(cenario.deps, pedido_id)
    assert fluxo_mod.decidir_divergencia(cenario.conn, pedido_id, True) is None

    assert fluxo_mod.decidir_divergencia(cenario.conn, pedido_id, False) is None

    assert cenario.ler(pedido_id).status == "aguardando_pessoa"
    assert _perguntas(cenario, pedido_id) == []


# ---- terminal ------------------------------------------------------------------------------------------


class _LLM(ProvenienciaFalsa):
    def gerar_json(
        self, tarefa_nome: str, prompt: str, esquema: Any, versao_prompt: str | None = None
    ) -> Any:
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
def terminal(cenario: Cenario, monkeypatch: pytest.MonkeyPatch) -> sqlite3.Connection:
    monkeypatch.setattr(cli, "banco", lambda: cenario.conn)
    monkeypatch.setattr(cli, "llm", lambda: _LLM())
    monkeypatch.setattr(cli, "_contexto_de_navegacao", lambda *_a, **_k: None)
    return cenario.conn


def test_terminal_mantem_a_confirmacao_s_n(
    terminal: sqlite3.Connection, cenario: Cenario, capsys: pytest.CaptureFixture[str]
) -> None:
    perfil_id = cenario.contato("Joaquim Bastos", curar=True)
    perguntas: list[str] = []

    def recusa(pergunta: str) -> str:
        perguntas.append(pergunta)
        return "n"

    assert cli.pedir_cmd("Falar com a Marta", True, False, perfil_id, entrada=recusa) == 1

    saida = capsys.readouterr().out
    assert "ATENÇÃO: o pedido fala de 'Marta Quintela', mas o contato é 'Joaquim Bastos'." in saida
    assert "Contato não confirmado" in saida
    assert perguntas == ["Continuar com este contato mesmo assim? [s/N] "]


def test_terminal_com_s_continua_com_o_contato(
    terminal: sqlite3.Connection, cenario: Cenario, capsys: pytest.CaptureFixture[str]
) -> None:
    perfil_id = cenario.contato("Joaquim Bastos", curar=True)

    assert cli.pedir_cmd("Falar com a Marta", False, False, perfil_id, entrada=lambda _p: "s") == 0

    saida = capsys.readouterr().out
    assert "Contato não confirmado" not in saida
    assert "Pessoa: Joaquim Bastos" in saida


def test_a_regra_de_divergencia_vem_do_orquestrador(cenario: Cenario) -> None:
    perfil_id = cenario.contato("Joaquim Bastos", curar=True)

    resultado = orquestracao.entender_pedido(
        _LLM(),
        cenario.conn,
        "Falar com a Marta",
        AGORA,
        limiares_listas=cenario.deps.limiares.listas,
        contato_id_forcado=perfil_id,
    )

    assert resultado.contato_divergente is True
