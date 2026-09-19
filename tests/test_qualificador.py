from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pytest

from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import assuntos, fontes, itens, perfil_tema, perfis
from agente_nw.nucleo.database.queries import temas as queries_temas
from agente_nw.nucleo.llm import FalhaJsonInvalido
from agente_nw.nucleo.modelos.assunto import Assunto
from agente_nw.nucleo.modelos.item import Item
from agente_nw.nucleo.modelos.qualificacao import RespostaQualificar
from agente_nw.nucleo.modelos.rotulo import RespostaRotulo
from agente_nw.nucleo.relevancia.qualificador import qualificar_pendentes

AGORA = "2026-01-01T00:00:00+00:00"


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


def _vetor(*valores: float) -> list[float]:
    return list(valores) + [0.0] * (1024 - len(valores))


class _ClienteFake:
    def __init__(self) -> None:
        self.chamadas: list[str] = []
        self.respostas_rotular: list[RespostaRotulo | Exception] = []
        self.respostas_qualificar: list[RespostaQualificar | Exception] = []

    def gerar_json(self, tarefa_nome: str, prompt: str, esquema: type[Any]) -> Any:
        self.chamadas.append(tarefa_nome)
        if tarefa_nome == "rotular":
            resposta = self.respostas_rotular.pop(0)
        elif tarefa_nome == "qualificar":
            resposta = self.respostas_qualificar.pop(0)
        else:
            raise AssertionError(f"tarefa inesperada: {tarefa_nome}")
        if isinstance(resposta, Exception):
            raise resposta
        return resposta


def _preparar_tema_usuario(conn: sqlite3.Connection) -> None:
    usuario = perfis.upsert_usuario(conn, "Usuário Teste", AGORA)
    assert usuario.id is not None
    tema_usuario = queries_temas.obter_ou_criar(conn, "tema-usuario", "descrição", [], AGORA)
    assert tema_usuario.id is not None
    queries_temas.gravar_embedding(conn, tema_usuario.id, _vetor(1.0, 0.0))
    perfil_tema.vincular(conn, usuario.id, tema_usuario.id, 3, "declarada", "dominio", True, AGORA)
    conn.commit()


def _criar_assunto_com_item(conn: sqlite3.Connection, titulo_gerado: str | None) -> int:
    fonte = fontes.obter_ou_criar(conn, "g1.globo.com", "https://g1.globo.com/rss", "g1.globo.com", "rss", 5)
    assert fonte.id is not None
    assunto = Assunto(
        titulo_gerado=titulo_gerado, primeiro_visto=AGORA, ultimo_visto=AGORA, n_itens=1, status="novo"
    )
    assunto_id = assuntos.inserir(conn, assunto)
    assuntos.gravar_centroide(conn, assunto_id, _vetor(1.0, 0.0))
    item = Item(
        fonte_id=fonte.id,
        url_canonica=f"https://exemplo.com/{assunto_id}",
        titulo="Título do item",
        coletado_em=AGORA,
        hash_titulo=f"hash-{assunto_id}",
        assunto_id=assunto_id,
    )
    itens.inserir(conn, item)
    conn.commit()
    return assunto_id


def test_titulo_gerado_antes_de_qualificar_quando_assunto_sem_titulo(conn: sqlite3.Connection) -> None:
    _preparar_tema_usuario(conn)
    assunto_id = _criar_assunto_com_item(conn, titulo_gerado=None)

    cliente = _ClienteFake()
    cliente.respostas_rotular = [RespostaRotulo(titulo="Título gerado pelo modelo")]
    cliente.respostas_qualificar = [
        RespostaQualificar(substancial=0.8, conversavel=0.7, temas=[], justificativa="ok")
    ]

    resumo = qualificar_pendentes(cliente, conn, 10)

    assert cliente.chamadas == ["rotular", "qualificar"]
    assert resumo.titulos_gerados == 1
    assert resumo.qualificados == 1

    resultado = assuntos.obter_por_id(conn, assunto_id)
    assert resultado is not None
    assert resultado.titulo_gerado == "Título gerado pelo modelo"
    assert resultado.substancial == 0.8


def test_assunto_com_titulo_nao_chama_rotular_de_novo(conn: sqlite3.Connection) -> None:
    _preparar_tema_usuario(conn)
    _criar_assunto_com_item(conn, titulo_gerado="Já tem título")

    cliente = _ClienteFake()
    cliente.respostas_qualificar = [
        RespostaQualificar(substancial=0.5, conversavel=0.5, temas=[], justificativa="ok")
    ]

    resumo = qualificar_pendentes(cliente, conn, 10)

    assert cliente.chamadas == ["qualificar"]
    assert resumo.titulos_gerados == 0
    assert resumo.qualificados == 1


def test_tema_fora_da_lista_conhecida_e_descartado_sem_travar(conn: sqlite3.Connection) -> None:
    _preparar_tema_usuario(conn)
    assunto_id = _criar_assunto_com_item(conn, titulo_gerado="Já tem título")

    cliente = _ClienteFake()
    cliente.respostas_qualificar = [
        RespostaQualificar(substancial=0.6, conversavel=0.6, temas=["tema-inexistente"], justificativa="ok")
    ]

    resumo = qualificar_pendentes(cliente, conn, 10)

    assert resumo.qualificados == 1
    assert resumo.erros == 0
    resultado = assuntos.obter_por_id(conn, assunto_id)
    assert resultado is not None
    assert resultado.temas == []


def test_erro_de_json_num_candidato_nao_impede_os_demais(conn: sqlite3.Connection) -> None:
    _preparar_tema_usuario(conn)
    assunto_falha = _criar_assunto_com_item(conn, titulo_gerado=None)
    assunto_ok = _criar_assunto_com_item(conn, titulo_gerado="Já tem título")

    cliente = _ClienteFake()
    cliente.respostas_rotular = [FalhaJsonInvalido("rotular", 1, "json inválido")]
    cliente.respostas_qualificar = [
        RespostaQualificar(substancial=0.7, conversavel=0.7, temas=[], justificativa="ok")
    ]

    resumo = qualificar_pendentes(cliente, conn, 10)

    assert resumo.candidatos == 2
    assert resumo.erros == 1
    assert resumo.qualificados == 1

    falhou = assuntos.obter_por_id(conn, assunto_falha)
    assert falhou is not None
    assert falhou.substancial is None

    ok = assuntos.obter_por_id(conn, assunto_ok)
    assert ok is not None
    assert ok.substancial == 0.7
