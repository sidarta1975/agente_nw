from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.perfil.agenda_google_csv import ler_contatos
from agente_nw.perfil.importador import importar

RAIZ = Path(__file__).resolve().parent.parent
FIXTURE = RAIZ / "tests" / "fixtures" / "contatos_exemplo.csv"


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


def test_importar_duas_vezes_nao_duplica_perfis(conn: sqlite3.Connection) -> None:
    contatos = ler_contatos(FIXTURE)

    resumo1 = importar(contatos, conn)
    (n_perfis_1,) = conn.execute("SELECT COUNT(*) FROM perfil WHERE tipo = 'contato'").fetchone()

    resumo2 = importar(contatos, conn)
    (n_perfis_2,) = conn.execute("SELECT COUNT(*) FROM perfil WHERE tipo = 'contato'").fetchone()

    assert resumo1.perfis_criados == 5  # todos os 5 contatos da fixture têm telefone ou e-mail
    assert n_perfis_1 == n_perfis_2
    assert resumo2.perfis_criados == 0
    assert resumo2.perfis_atualizados == 5


def test_contato_com_nota_enfileira_extracao(conn: sqlite3.Connection) -> None:
    contatos = ler_contatos(FIXTURE)
    importar(contatos, conn)

    linha = conn.execute("SELECT texto, origem FROM fila_extracao WHERE origem = 'notas_agenda'").fetchone()
    assert linha is not None
    assert linha["texto"] == "Gosta de futebol e viagens."
    assert linha["origem"] == "notas_agenda"


def test_contato_com_marcador_gera_perfil_tema_importada(conn: sqlite3.Connection) -> None:
    contatos = ler_contatos(FIXTURE)
    importar(contatos, conn)

    linhas = conn.execute(
        "SELECT t.nome, pt.origem FROM perfil_tema pt JOIN tema t ON t.id = pt.tema_id "
        "WHERE pt.origem = 'importada' ORDER BY t.nome"
    ).fetchall()
    nomes = [linha["nome"] for linha in linhas]
    assert nomes == ["Amigos", "Clientes", "Trabalho"]


def test_nenhum_contato_nasce_ativo(conn: sqlite3.Connection) -> None:
    contatos = ler_contatos(FIXTURE)
    importar(contatos, conn)

    (n_ativos,) = conn.execute("SELECT COUNT(*) FROM perfil WHERE tipo = 'contato' AND ativo = 1").fetchone()
    assert n_ativos == 0


def test_tag_confirmada_nao_e_desconfirmada_ao_reimportar(conn: sqlite3.Connection) -> None:
    contatos = ler_contatos(FIXTURE)
    importar(contatos, conn)

    (perfil_id, tema_id) = conn.execute(
        "SELECT pt.perfil_id, pt.tema_id FROM perfil_tema pt "
        "JOIN tema t ON t.id = pt.tema_id WHERE t.nome = 'Amigos'"
    ).fetchone()
    conn.execute(
        "UPDATE perfil_tema SET confirmado = 1 WHERE perfil_id = ? AND tema_id = ?", (perfil_id, tema_id)
    )
    conn.commit()

    importar(contatos, conn)

    (confirmado,) = conn.execute(
        "SELECT confirmado FROM perfil_tema WHERE perfil_id = ? AND tema_id = ?", (perfil_id, tema_id)
    ).fetchone()
    assert confirmado == 1
