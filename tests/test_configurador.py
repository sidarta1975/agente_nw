from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import perfil_tema, perfis
from agente_nw.nucleo.database.queries import temas as queries_temas
from agente_nw.nucleo.modelos.configuracao import TemaUsuario
from agente_nw.perfil import configurador

AGORA = "2026-09-21T10:00:00+00:00"


class _ClienteEmbeddagemFake:
    def __init__(self) -> None:
        self.chamadas: list[list[str]] = []

    def embeddar(self, textos: list[str]) -> list[list[float]]:
        self.chamadas.append(list(textos))
        return [[0.1] * 1024 for _ in textos]


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


def _tema(nome: str, nivel: str = "interesse") -> TemaUsuario:
    return TemaUsuario(
        nome=nome,
        descricao="descrição bem completa com mais de oito palavras para passar validação de embedding",
        sinonimos=[],
        nivel=nivel,  # type: ignore[arg-type]
        peso=3,
    )


def test_salvar_perfil_usuario_cria_usuario_com_temas_confirmados(conn: sqlite3.Connection) -> None:
    cliente = _ClienteEmbeddagemFake()

    usuario = configurador.salvar_perfil_usuario(
        conn,
        cliente,
        "Sidarta",
        [_tema("vela", "dominio"), _tema("leitura", "interesse")],
        AGORA,
    )

    assert usuario.id is not None
    assert usuario.nome == "Sidarta"
    tags = perfil_tema.listar_por_perfil(conn, usuario.id)
    assert len(tags) == 2
    assert all(tag.confirmado for tag in tags)
    assert {tag.nivel for tag in tags} == {"dominio", "interesse"}
    assert all(tag.origem == "declarada" for tag in tags)
    assert len(cliente.chamadas) == 2  # um embed por tema


def test_salvar_perfil_usuario_pode_ser_chamado_de_novo_para_atualizar_temas(
    conn: sqlite3.Connection,
) -> None:
    cliente = _ClienteEmbeddagemFake()
    configurador.salvar_perfil_usuario(conn, cliente, "Sidarta", [_tema("vela")], AGORA)

    usuario_novo = configurador.salvar_perfil_usuario(
        conn, cliente, "Sidarta Bado", [_tema("leitura")], AGORA
    )

    assert usuario_novo.nome == "Sidarta Bado"
    tags = perfil_tema.listar_por_perfil(conn, usuario_novo.id or -1)
    nomes = {queries_temas.obter_por_id(conn, tag.tema_id).nome for tag in tags if tag.tema_id}  # type: ignore[union-attr]
    assert "vela" in nomes and "leitura" in nomes


def test_adicionar_tema_do_usuario_grava_novo_vinculo(conn: sqlite3.Connection) -> None:
    cliente = _ClienteEmbeddagemFake()
    usuario = configurador.salvar_perfil_usuario(conn, cliente, "Sidarta", [_tema("vela")], AGORA)
    assert usuario.id is not None

    configurador.adicionar_tema_do_usuario(conn, cliente, usuario.id, _tema("regata"), AGORA)

    tags = perfil_tema.listar_por_perfil(conn, usuario.id)
    nomes = {queries_temas.obter_por_id(conn, tag.tema_id).nome for tag in tags if tag.tema_id}  # type: ignore[union-attr]
    assert nomes == {"vela", "regata"}


def test_remover_tema_do_usuario_apaga_vinculo_mas_preserva_tema(conn: sqlite3.Connection) -> None:
    cliente = _ClienteEmbeddagemFake()
    usuario = configurador.salvar_perfil_usuario(conn, cliente, "Sidarta", [_tema("vela")], AGORA)
    assert usuario.id is not None
    tags = perfil_tema.listar_por_perfil(conn, usuario.id)
    tema_id = tags[0].tema_id

    removeu = configurador.remover_tema_do_usuario(conn, usuario.id, tema_id)

    assert removeu is True
    assert perfil_tema.listar_por_perfil(conn, usuario.id) == []
    assert queries_temas.obter_por_id(conn, tema_id) is not None


def test_remover_tema_do_usuario_devolve_falso_para_vinculo_inexistente(conn: sqlite3.Connection) -> None:
    usuario = perfis.upsert_usuario(conn, "Sidarta", AGORA)
    conn.commit()
    assert usuario.id is not None

    removeu = configurador.remover_tema_do_usuario(conn, usuario.id, 9999)

    assert removeu is False
