from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import assuntos, fontes, itens
from agente_nw.nucleo.modelos.assunto import Assunto
from agente_nw.nucleo.modelos.cartao import RespostaCartao
from agente_nw.nucleo.modelos.item import Item
from agente_nw.nucleo.relevancia.cartoes import gerar_cartao

AGORA = "2026-01-01T00:00:00+00:00"


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


class _ClienteFake:
    def __init__(self, respostas: list[RespostaCartao]) -> None:
        self._respostas = list(respostas)
        self.chamadas = 0

    def gerar_json(self, tarefa_nome: str, prompt: str, esquema: type[RespostaCartao]) -> RespostaCartao:
        self.chamadas += 1
        return self._respostas.pop(0)


def _criar_assunto_com_item(conn: sqlite3.Connection) -> int:
    fonte = fontes.obter_ou_criar(conn, "g1.globo.com", "https://g1.globo.com/rss", "g1.globo.com", "rss", 5)
    assert fonte.id is not None
    assunto = Assunto(
        titulo_gerado="Título do assunto",
        primeiro_visto=AGORA,
        ultimo_visto=AGORA,
        n_itens=1,
        status="novo",
    )
    assunto_id = assuntos.inserir(conn, assunto)
    item = Item(
        fonte_id=fonte.id,
        url_canonica=f"https://exemplo.com/{assunto_id}",
        titulo="Título do item",
        texto="Um texto de exemplo com trecho relevante.",
        coletado_em=AGORA,
        hash_titulo=f"hash-{assunto_id}",
        assunto_id=assunto_id,
    )
    itens.inserir(conn, item)
    conn.commit()
    return assunto_id


def test_cartao_com_numero_e_fonte_na_mesma_linha_aprova(conn: sqlite3.Connection) -> None:
    assunto_id = _criar_assunto_com_item(conn)
    resposta = RespostaCartao(resumo="A obra custou R$ 40 milhões (G1).\nOutra linha sem número.\nFim.")
    cliente = _ClienteFake([resposta])

    resultado = gerar_cartao(cliente, conn, assunto_id)

    assert resultado == resposta.resumo
    assert cliente.chamadas == 1
    gravado = assuntos.obter_por_id(conn, assunto_id)
    assert gravado is not None
    assert gravado.resumo_cartao == resposta.resumo


def test_cartao_reprova_e_aprova_na_segunda_tentativa(conn: sqlite3.Connection) -> None:
    assunto_id = _criar_assunto_com_item(conn)
    invalido = RespostaCartao(resumo="A obra custou R$ 40 milhões, sem fonte citada aqui.")
    valido = RespostaCartao(resumo="A obra custou R$ 40 milhões (G1).")
    cliente = _ClienteFake([invalido, valido])

    resultado = gerar_cartao(cliente, conn, assunto_id)

    assert resultado == valido.resumo
    assert cliente.chamadas == 2
    gravado = assuntos.obter_por_id(conn, assunto_id)
    assert gravado is not None
    assert gravado.resumo_cartao == valido.resumo


def test_cartao_reprova_duas_vezes_vai_para_fila_revisao_e_devolve_none(conn: sqlite3.Connection) -> None:
    assunto_id = _criar_assunto_com_item(conn)
    invalido = RespostaCartao(resumo="A obra custou R$ 40 milhões, sem fonte.")
    cliente = _ClienteFake([invalido, invalido])

    resultado = gerar_cartao(cliente, conn, assunto_id)

    assert resultado is None
    assert cliente.chamadas == 2
    gravado = assuntos.obter_por_id(conn, assunto_id)
    assert gravado is not None
    assert gravado.resumo_cartao is None

    linha = conn.execute("SELECT tarefa, entrada, erro FROM fila_revisao").fetchone()
    assert linha is not None
    assert linha["tarefa"] == "cartao"
    assert linha["entrada"] == str(assunto_id)


def test_cartao_sem_numero_aprova_direto(conn: sqlite3.Connection) -> None:
    assunto_id = _criar_assunto_com_item(conn)
    resposta = RespostaCartao(resumo="Nada de números nesta linha.\nNem nesta outra.\nFim do resumo.")
    cliente = _ClienteFake([resposta])

    resultado = gerar_cartao(cliente, conn, assunto_id)

    assert resultado == resposta.resumo
    assert cliente.chamadas == 1


def test_cartao_de_assunto_inexistente_da_erro_claro(conn: sqlite3.Connection) -> None:
    cliente = _ClienteFake([])
    with pytest.raises(ValueError):
        gerar_cartao(cliente, conn, 999)
