from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import assuntos, fontes, itens
from agente_nw.nucleo.modelos.assunto import Assunto
from agente_nw.nucleo.modelos.cartao import RespostaCartao
from agente_nw.nucleo.modelos.item import Item
from agente_nw.nucleo.relevancia.cartoes import gerar_pendentes

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


def _criar_assunto_qualificado_com_item(conn: sqlite3.Connection, titulo: str) -> int:
    fonte = fontes.obter_ou_criar(conn, "g1.globo.com", "https://g1.globo.com/rss", "g1.globo.com", "rss", 5)
    assert fonte.id is not None
    assunto = Assunto(
        titulo_gerado=titulo,
        primeiro_visto=AGORA,
        ultimo_visto=AGORA,
        n_itens=1,
        status="novo",
        substancial=0.8,
        conversavel=0.8,
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


def test_gera_cartao_para_cada_candidato(conn: sqlite3.Connection) -> None:
    id1 = _criar_assunto_qualificado_com_item(conn, "Assunto 1")
    id2 = _criar_assunto_qualificado_com_item(conn, "Assunto 2")
    respostas = [
        RespostaCartao(resumo="Sem número na linha um.\nSem número na linha dois.\nFim."),
        RespostaCartao(resumo="Sem número na linha um.\nSem número na linha dois.\nFim."),
    ]
    cliente = _ClienteFake(respostas)

    resumo = gerar_pendentes(cliente, conn, 10)

    assert resumo.candidatos == 2
    assert resumo.gerados == 2
    assert resumo.erros == 0
    for assunto_id in (id1, id2):
        gravado = assuntos.obter_por_id(conn, assunto_id)
        assert gravado is not None
        assert gravado.resumo_cartao is not None


def test_candidato_com_gerar_cartao_none_conta_como_erro_nao_trava_os_demais(
    conn: sqlite3.Connection,
) -> None:
    id_falha = _criar_assunto_qualificado_com_item(conn, "Assunto que falha")
    id_ok = _criar_assunto_qualificado_com_item(conn, "Assunto que funciona")

    invalido = RespostaCartao(resumo="Um número sem fonte, tipo 40%, aqui.")
    valido = RespostaCartao(resumo="Sem número na linha um.\nSem número na linha dois.\nFim.")
    cliente = _ClienteFake([invalido, invalido, valido])

    resumo = gerar_pendentes(cliente, conn, 10)

    assert resumo.candidatos == 2
    assert resumo.erros == 1
    assert resumo.gerados == 1

    falhou = assuntos.obter_por_id(conn, id_falha)
    assert falhou is not None
    assert falhou.resumo_cartao is None

    ok = assuntos.obter_por_id(conn, id_ok)
    assert ok is not None
    assert ok.resumo_cartao is not None


def test_respeita_limite(conn: sqlite3.Connection) -> None:
    for i in range(3):
        _criar_assunto_qualificado_com_item(conn, f"Assunto {i}")
    resposta = RespostaCartao(resumo="Sem número na linha um.\nSem número na linha dois.\nFim.")
    cliente = _ClienteFake([resposta, resposta])

    resumo = gerar_pendentes(cliente, conn, 2)

    assert resumo.candidatos == 2
