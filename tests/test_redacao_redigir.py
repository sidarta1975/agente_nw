from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pytest

from agente_nw.nucleo import redacao as redacao_mod
from agente_nw.nucleo.consulta import ItemMenu, ResultadoConsulta, ResumoRedeSocial
from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import assuntos as assuntos_q
from agente_nw.nucleo.database.queries import consulta_contato as consulta_contato_q
from agente_nw.nucleo.database.queries import gancho_uso, perfis
from agente_nw.nucleo.modelos.assunto import Assunto
from agente_nw.nucleo.modelos.pedido import PedidoExtraido
from agente_nw.nucleo.modelos.perfil import Perfil
from agente_nw.nucleo.modelos.redacao import Gancho, RespostaRedacao

AGORA = "2026-10-12T10:00:00+00:00"


class _LLMFalso:
    """Devolve respostas prontas, uma por chamada, e guarda os prompts recebidos."""

    def __init__(self, *respostas: RespostaRedacao) -> None:
        self._respostas = list(respostas)
        self.prompts: list[str] = []

    def gerar_json(self, tarefa_nome: str, prompt: str, esquema: type[Any]) -> Any:
        assert tarefa_nome == "redigir_ganchos"
        self.prompts.append(prompt)
        return self._respostas.pop(0)


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


def _pedido(
    meio: str = "whatsapp", registro: str = "cordial", evitar: list[str] | None = None
) -> PedidoExtraido:
    return PedidoExtraido.model_validate(
        {
            "pessoa_nome": "Irene",
            "pessoa_pistas": {"vinculo": "colega de turma", "tempo_sem_contato": "cinco anos"},
            "objetivo": "retomar",
            "objetivo_texto": "voltar a conversar",
            "meio": meio,
            "registro": registro,
            "assunto_principal": "cooperativas de crédito",
            "evitar": evitar or [],
            "termos_busca": ["cooperativas de crédito"],
            "confianca": 0.9,
        }
    )


def _gancho(assunto_id: int, mensagem: str = "Oi, Irene! Vi uma notícia e lembrei de você.") -> Gancho:
    return Gancho(
        assunto_id=assunto_id,
        titulo=f"Gancho {assunto_id}",
        noticia="Primeira frase. Segunda frase.",
        por_que_para_esta_pessoa="Ela trabalha com isso.",
        mensagem=mensagem,
        abordagem_presencial="Comece perguntando como vai o trabalho.",
    )


def _montar(conn: sqlite3.Connection, n_assuntos: int = 3) -> tuple[Perfil, Perfil, ResultadoConsulta]:
    usuario = perfis.upsert_usuario(conn, "Davi Pires", AGORA)
    contato = perfis.inserir_novo_contato(conn, "Irene Duarte", None, None, AGORA)
    assert contato.id is not None
    itens: list[ItemMenu] = []
    for i in range(n_assuntos):
        assunto_id = assuntos_q.inserir(
            conn,
            Assunto(
                titulo_gerado=f"Assunto {i + 1}",
                primeiro_visto=AGORA,
                ultimo_visto=AGORA,
                status="novo",
                resumo_cartao=f"Resumo {i + 1}",
            ),
        )
        itens.append(ItemMenu(i + 1, assunto_id, "conector", f"Assunto {i + 1}", f"motivo {i + 1}", 70.0))
    consulta = consulta_contato_q.inserir(conn, contato.id, AGORA, "{}", None, "[]")
    conn.commit()
    assert consulta.id is not None
    resultado = ResultadoConsulta(contato.id, consulta.id, itens, ResumoRedeSocial(), "")
    return usuario, contato, resultado


def _consulta_anterior(conn: sqlite3.Connection, contato: Perfil) -> int:
    assert contato.id is not None
    anterior = consulta_contato_q.inserir(conn, contato.id, "2026-10-01T10:00:00+00:00", "{}", None, "[]")
    assert anterior.id is not None
    return anterior.id


def test_tres_assuntos_geram_tres_ganchos(conn: sqlite3.Connection) -> None:
    usuario, contato, resultado = _montar(conn)
    ids = [item.assunto_id for item in resultado.itens_menu]
    llm = _LLMFalso(RespostaRedacao(ganchos=[_gancho(i) for i in ids]))

    redacao = redacao_mod.redigir(llm, conn, _pedido(), resultado, contato, usuario, AGORA)

    assert [g.assunto_id for g in redacao.ganchos] == ids
    assert redacao.registro_usado == "cordial"
    assert redacao.aviso is None
    assert "Davi Pires" in llm.prompts[0] and "Irene Duarte" in llm.prompts[0]


def test_gancho_ja_usado_no_historico_nao_e_entregue(conn: sqlite3.Connection) -> None:
    usuario, contato, resultado = _montar(conn)
    usado, outro, terceiro = (item.assunto_id for item in resultado.itens_menu)
    anterior = _consulta_anterior(conn, contato)
    gancho_uso.inserir_entregues(conn, anterior, [(usado, "{}")], AGORA)
    gancho_uso.marcar(conn, anterior, usado, "usado", AGORA)
    # O modelo insiste no assunto usado: o validador também o recusa.
    llm = _LLMFalso(RespostaRedacao(ganchos=[_gancho(usado), _gancho(outro), _gancho(terceiro)]))

    redacao = redacao_mod.redigir(llm, conn, _pedido(), resultado, contato, usuario, AGORA)

    assert [g.assunto_id for g in redacao.ganchos] == [outro, terceiro]
    assert f"[assunto {usado}]" not in llm.prompts[0]
    assert f"[assunto {outro}]" in llm.prompts[0]


def test_todos_os_assuntos_ja_usados_nao_chama_o_modelo(conn: sqlite3.Connection) -> None:
    usuario, contato, resultado = _montar(conn, n_assuntos=1)
    assunto_id = resultado.itens_menu[0].assunto_id
    anterior = _consulta_anterior(conn, contato)
    gancho_uso.inserir_entregues(conn, anterior, [(assunto_id, "{}")], AGORA)
    gancho_uso.marcar(conn, anterior, assunto_id, "usado", AGORA)
    llm = _LLMFalso()

    redacao = redacao_mod.redigir(llm, conn, _pedido(), resultado, contato, usuario, AGORA)

    assert redacao.ganchos == []
    assert redacao.aviso is not None and "já foram usados" in redacao.aviso
    assert llm.prompts == []


def test_sem_assunto_devolve_lista_vazia_com_aviso_e_nao_chama_o_modelo(conn: sqlite3.Connection) -> None:
    usuario, contato, resultado = _montar(conn, n_assuntos=0)
    llm = _LLMFalso()

    redacao = redacao_mod.redigir(llm, conn, _pedido(), resultado, contato, usuario, AGORA)

    assert redacao.ganchos == []
    assert redacao.aviso
    assert llm.prompts == []


def test_meio_presencial_traz_a_abordagem_e_whatsapp_nao(conn: sqlite3.Connection) -> None:
    usuario, contato, resultado = _montar(conn, n_assuntos=1)
    assunto_id = resultado.itens_menu[0].assunto_id

    presencial = redacao_mod.redigir(
        _LLMFalso(RespostaRedacao(ganchos=[_gancho(assunto_id)])),
        conn,
        _pedido(meio="pessoalmente"),
        resultado,
        contato,
        usuario,
        AGORA,
    )
    zap = redacao_mod.redigir(
        _LLMFalso(RespostaRedacao(ganchos=[_gancho(assunto_id)])),
        conn,
        _pedido(meio="whatsapp"),
        resultado,
        contato,
        usuario,
        AGORA,
    )

    assert presencial.ganchos[0].abordagem_presencial
    assert zap.ganchos[0].abordagem_presencial is None


def test_mensagem_com_termo_de_evitar_cai_e_o_aviso_diz_por_que(conn: sqlite3.Connection) -> None:
    usuario, contato, resultado = _montar(conn, n_assuntos=2)
    primeiro, segundo = (item.assunto_id for item in resultado.itens_menu)
    llm = _LLMFalso(
        RespostaRedacao(ganchos=[_gancho(primeiro, "Oi! Que tal falar de Eleição?"), _gancho(segundo)])
    )

    redacao = redacao_mod.redigir(llm, conn, _pedido(evitar=["eleicao"]), resultado, contato, usuario, AGORA)

    assert [g.assunto_id for g in redacao.ganchos] == [segundo]
    assert redacao.aviso is not None and "eleicao" in redacao.aviso


def test_se_todas_as_mensagens_forem_recusadas_o_modelo_tem_uma_segunda_chance(
    conn: sqlite3.Connection,
) -> None:
    usuario, contato, resultado = _montar(conn, n_assuntos=1)
    assunto_id = resultado.itens_menu[0].assunto_id
    longa = " ".join(["palavra"] * 200)
    llm = _LLMFalso(
        RespostaRedacao(ganchos=[_gancho(assunto_id, longa)]),
        RespostaRedacao(ganchos=[_gancho(assunto_id)]),
    )

    redacao = redacao_mod.redigir(llm, conn, _pedido(), resultado, contato, usuario, AGORA)

    assert len(llm.prompts) == 2
    assert "foi recusada" in llm.prompts[1] and "limite 80" in llm.prompts[1]
    assert [g.assunto_id for g in redacao.ganchos] == [assunto_id]


def test_registrar_grava_na_tabela_e_o_historico_mostra_o_status(conn: sqlite3.Connection) -> None:
    from agente_nw.nucleo import historico

    usuario, contato, resultado = _montar(conn, n_assuntos=1)
    assunto_id = resultado.itens_menu[0].assunto_id
    llm = _LLMFalso(RespostaRedacao(ganchos=[_gancho(assunto_id)]))
    redacao = redacao_mod.redigir(llm, conn, _pedido(), resultado, contato, usuario, AGORA)

    redacao_mod.registrar(conn, resultado.consulta_id, redacao, AGORA)

    gravados = redacao_mod.ganchos_da_consulta(conn, resultado.consulta_id)
    assert [(g.assunto_id, status) for g, status in gravados] == [(assunto_id, "entregue")]
    gancho_uso.marcar(conn, resultado.consulta_id, assunto_id, "usado", AGORA)
    texto = historico.historico_recente_para_prompt(conn, contato.id or 0)
    assert f"Gancho {assunto_id} (usado)" in texto
