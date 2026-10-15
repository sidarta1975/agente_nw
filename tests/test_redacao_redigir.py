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
from agente_nw.nucleo.database.queries import fontes as fontes_q
from agente_nw.nucleo.database.queries import gancho_uso, perfis
from agente_nw.nucleo.database.queries import itens as itens_q
from agente_nw.nucleo.modelos.assunto import Assunto
from agente_nw.nucleo.modelos.fato import Fato
from agente_nw.nucleo.modelos.item import Item
from agente_nw.nucleo.modelos.pedido import PedidoExtraido
from agente_nw.nucleo.modelos.perfil import Perfil
from agente_nw.nucleo.modelos.redacao import Gancho, RespostaRedacao

AGORA = "2026-10-12T10:00:00+00:00"


def _base(
    mensagem: str = "Oi, Irene! Faz tempo. Vi seu trabalho com cooperativas e lembrei de você.",
) -> Gancho:
    return Gancho(
        peculiaridade="o trabalho com cooperativas de crédito",
        por_que_para_esta_pessoa="Retoma a conversa pelo trabalho dela.",
        mensagem=mensagem,
        abordagem_presencial="Comece perguntando como vai o trabalho.",
    )


def _com_base(resposta: RespostaRedacao) -> RespostaRedacao:
    if any(g.assunto_id is None for g in resposta.ganchos):
        return resposta
    return resposta.model_copy(update={"ganchos": [_base(), *resposta.ganchos]})


class _LLMFalso:
    """Devolve respostas prontas, uma por chamada, e guarda os prompts recebidos. Por padrão acrescenta a
    mensagem base às respostas que vieram só com ganchos de notícia."""

    def __init__(self, *respostas: RespostaRedacao, com_base: bool = True) -> None:
        self._respostas = [_com_base(r) if com_base else r for r in respostas]
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

    assert [g.assunto_id for g in redacao.ganchos] == [None, *ids]
    assert redacao.registro_usado == "cordial"
    assert redacao.aviso == "Pouca informação sobre a pessoa; mensagem mais geral."
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

    assert [g.assunto_id for g in redacao.ganchos] == [None, outro, terceiro]
    assert f"[assunto {usado}]" not in llm.prompts[0]
    assert f"[assunto {outro}]" in llm.prompts[0]


def test_todos_os_assuntos_ja_usados_ainda_gera_a_mensagem_base(conn: sqlite3.Connection) -> None:
    usuario, contato, resultado = _montar(conn, n_assuntos=1)
    assunto_id = resultado.itens_menu[0].assunto_id
    anterior = _consulta_anterior(conn, contato)
    gancho_uso.inserir_entregues(conn, anterior, [(assunto_id, "{}")], AGORA)
    gancho_uso.marcar(conn, anterior, assunto_id, "usado", AGORA)
    llm = _LLMFalso(RespostaRedacao(ganchos=[_base()]))

    redacao = redacao_mod.redigir(llm, conn, _pedido(), resultado, contato, usuario, AGORA)

    assert [g.assunto_id for g in redacao.ganchos] == [None]
    assert redacao.aviso is not None and "já foram usados" in redacao.aviso
    assert len(llm.prompts) == 1 and f"[assunto {assunto_id}]" not in llm.prompts[0]


def test_sem_assunto_o_modelo_e_chamado_e_a_base_sai_com_aviso_informativo(conn: sqlite3.Connection) -> None:
    usuario, contato, resultado = _montar(conn, n_assuntos=0)
    llm = _LLMFalso(RespostaRedacao(ganchos=[_base()]))

    redacao = redacao_mod.redigir(llm, conn, _pedido(), resultado, contato, usuario, AGORA)

    assert [g.assunto_id for g in redacao.ganchos] == [None]
    assert redacao.aviso is not None and "mensagem a partir do perfil" in redacao.aviso
    assert len(llm.prompts) == 1 and "escreva só a mensagem base" in llm.prompts[0]


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

    assert presencial.ganchos[1].abordagem_presencial
    assert zap.ganchos[1].abordagem_presencial is None


def test_mensagem_com_termo_de_evitar_cai_e_o_aviso_diz_por_que(conn: sqlite3.Connection) -> None:
    usuario, contato, resultado = _montar(conn, n_assuntos=2)
    primeiro, segundo = (item.assunto_id for item in resultado.itens_menu)
    llm = _LLMFalso(
        RespostaRedacao(ganchos=[_gancho(primeiro, "Oi! Que tal falar de Eleição?"), _gancho(segundo)])
    )

    redacao = redacao_mod.redigir(llm, conn, _pedido(evitar=["eleicao"]), resultado, contato, usuario, AGORA)

    assert [g.assunto_id for g in redacao.ganchos] == [None, segundo]
    assert redacao.aviso is not None and "eleicao" in redacao.aviso


def test_sem_mensagem_base_valida_o_modelo_tem_uma_segunda_chance(conn: sqlite3.Connection) -> None:
    usuario, contato, resultado = _montar(conn, n_assuntos=1)
    assunto_id = resultado.itens_menu[0].assunto_id
    longa = " ".join(["palavra"] * 200)
    llm = _LLMFalso(
        RespostaRedacao(ganchos=[_base(longa), _gancho(assunto_id)]),
        RespostaRedacao(ganchos=[_base(), _gancho(assunto_id)]),
        com_base=False,
    )

    redacao = redacao_mod.redigir(llm, conn, _pedido(), resultado, contato, usuario, AGORA)

    assert len(llm.prompts) == 2
    assert "foi recusada" in llm.prompts[1] and "limite 80" in llm.prompts[1]
    assert [g.assunto_id for g in redacao.ganchos] == [None, assunto_id]


def test_registrar_grava_na_tabela_e_o_historico_mostra_o_status(conn: sqlite3.Connection) -> None:
    from agente_nw.nucleo import historico

    usuario, contato, resultado = _montar(conn, n_assuntos=1)
    assunto_id = resultado.itens_menu[0].assunto_id
    llm = _LLMFalso(RespostaRedacao(ganchos=[_gancho(assunto_id)]))
    redacao = redacao_mod.redigir(llm, conn, _pedido(), resultado, contato, usuario, AGORA)

    redacao_mod.registrar(conn, resultado.consulta_id, redacao, AGORA)

    gravados = redacao_mod.ganchos_da_consulta(conn, resultado.consulta_id)
    assert [(g.assunto_id, status) for g, status in gravados] == [
        (None, "entregue"),
        (assunto_id, "entregue"),
    ]
    gancho_uso.marcar(conn, resultado.consulta_id, assunto_id, "usado", AGORA)
    texto = historico.historico_recente_para_prompt(conn, contato.id or 0)
    assert f"Gancho {assunto_id} (usado)" in texto


def test_links_das_noticias_vem_do_banco_e_nao_do_modelo(conn: sqlite3.Connection) -> None:
    usuario, contato, resultado = _montar(conn, n_assuntos=1)
    assunto_id = resultado.itens_menu[0].assunto_id
    fonte = fontes_q.obter_ou_criar(conn, "Jornal", "https://jornal.test/feed", "jornal.test", "rss", 5)
    assert fonte.id is not None
    itens_q.inserir(
        conn,
        Item(
            fonte_id=fonte.id,
            url_canonica="https://jornal.test/materia-1",
            titulo="Matéria sobre cooperativas",
            texto="Texto integral da matéria sobre cooperativas, com todos os parágrafos.",
            publicado_em="2026-10-12T08:00:00+00:00",
            coletado_em=AGORA,
            hash_titulo="h1",
            assunto_id=assunto_id,
        ),
    )
    conn.commit()
    inventado = _gancho(assunto_id).model_copy(
        update={"links": [{"veiculo": "x", "titulo": "y", "url": "https://inventado.test"}]}
    )
    llm = _LLMFalso(RespostaRedacao(ganchos=[inventado]))

    redacao = redacao_mod.redigir(llm, conn, _pedido(), resultado, contato, usuario, AGORA)

    assert [(link.veiculo, link.url) for link in redacao.ganchos[1].links] == [
        ("jornal.test", "https://jornal.test/materia-1")
    ]
    redacao_mod.registrar(conn, resultado.consulta_id, redacao, AGORA)
    gravado = redacao_mod.ganchos_da_consulta(conn, resultado.consulta_id)[1][0]
    assert gravado.links[0].titulo == "Matéria sobre cooperativas"
    assert gravado.links[0].texto == "Texto integral da matéria sobre cooperativas, com todos os parágrafos."


class _LLMComEmbeddings(_LLMFalso):
    """Embeddings controlados: texto com 'vela' fica perto da consulta (assunto 'vela')."""

    def embeddar(self, textos: list[str]) -> list[list[float]]:
        return [[1.0, 0.0] if "vela" in t else [0.0, 1.0] for t in textos]


def _fatos(n: int, com_vela: set[int]) -> list[Fato]:
    return [
        Fato(
            perfil_id=1,
            tipo="post",
            conteudo=f"fato {i} sobre {'vela' if i in com_vela else 'cozinha'}",
            registrado_em=f"2026-10-{30 - i:02d}T10:00:00+00:00",
        )
        for i in range(n)
    ]


def test_fatos_escolhidos_sao_os_recentes_mais_os_parecidos_com_a_consulta() -> None:
    candidatos = _fatos(30, com_vela={12, 20, 25})
    llm = _LLMComEmbeddings()

    escolhidos = redacao_mod._escolher_fatos(llm, candidatos, "vela")

    conteudos = [f.conteudo for f in escolhidos]
    assert len(escolhidos) == 10
    assert all(f"fato {i} " in " ".join(conteudos) for i in range(4))  # os 4 mais recentes
    assert all(f"fato {i} sobre vela" in conteudos for i in (12, 20, 25))  # e os que falam do assunto


def test_poucos_fatos_entram_todos_e_sem_embeddings_ficam_os_recentes() -> None:
    assert len(redacao_mod._escolher_fatos(_LLMFalso(), _fatos(8, set()), "vela")) == 8

    sem_embeddings = redacao_mod._escolher_fatos(_LLMFalso(), _fatos(30, {25}), "vela")

    assert [f.conteudo for f in sem_embeddings] == [f.conteudo for f in _fatos(30, {25})[:10]]


def test_as_tags_do_contato_viram_o_contexto_da_relacao_no_prompt(conn: sqlite3.Connection) -> None:
    from agente_nw.nucleo.database.queries import perfil_tema, temas

    usuario, contato, resultado = _montar(conn, n_assuntos=1)
    assert contato.id is not None
    for nome, peso in (("trabalho", 3), ("família", 5)):
        tema = temas.obter_ou_criar(conn, nome, "contexto fixo da relação com o contato", [], AGORA)
        assert tema.id is not None
        perfil_tema.vincular(conn, contato.id, tema.id, peso, "declarada", None, True, AGORA)
    conn.commit()
    llm = _LLMFalso(RespostaRedacao(ganchos=[_gancho(resultado.itens_menu[0].assunto_id)]))

    redacao_mod.redigir(llm, conn, _pedido(), resultado, contato, usuario, AGORA)

    assert "Contexto da relação: família, trabalho." in llm.prompts[0]
