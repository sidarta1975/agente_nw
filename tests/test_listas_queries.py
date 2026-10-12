from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import listas, perfis
from agente_nw.nucleo.modelos.lista_rede_social import EntradaLista

AGORA = "2026-10-01T10:00:00+00:00"
DEPOIS = "2026-10-05T10:00:00+00:00"


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


def _entrada(nome: str, cabecalho: str = "", rede: str = "linkedin") -> EntradaLista:
    slug = nome.lower().replace(" ", "-")
    return EntradaLista(rede=rede, nome=nome, cabecalho=cabecalho, link=f"https://exemplo.test/{rede}/{slug}")


def test_substituir_preserva_o_vinculo_e_remove_o_que_sumiu(conn: sqlite3.Connection) -> None:
    contato = perfis.inserir_novo_contato(conn, "Maria Souza", None, None, AGORA)
    assert contato.id is not None
    maria, pedro = _entrada("Maria Souza", "Advogada"), _entrada("Pedro Alves", "Engenheiro")
    listas.substituir_lista(conn, "linkedin", [maria, pedro], AGORA)
    listas.vincular(conn, maria.link, contato.id)
    conn.commit()

    listas.substituir_lista(conn, "linkedin", [_entrada("Pedro Alves", "Engenheiro sênior")], DEPOIS)
    conn.commit()

    por_link = {e.link: e for e in listas.listar_por_rede(conn, "linkedin")}
    assert por_link[maria.link].perfil_id == contato.id  # vinculada: continua, mesmo fora da lista nova
    assert por_link[pedro.link].cabecalho == "Engenheiro sênior"
    assert por_link[pedro.link].lido_em == DEPOIS


def test_substituir_remove_entrada_antiga_nao_vinculada(conn: sqlite3.Connection) -> None:
    listas.substituir_lista(conn, "linkedin", [_entrada("Ana Lima"), _entrada("Beto Nunes")], AGORA)
    listas.substituir_lista(conn, "linkedin", [_entrada("Ana Lima")], DEPOIS)
    conn.commit()

    assert [e.nome for e in listas.listar_por_rede(conn, "linkedin")] == ["Ana Lima"]


def test_cache_valido_por_data(conn: sqlite3.Connection) -> None:
    assert listas.cache_valido(conn, "linkedin", 30, AGORA) is False
    listas.substituir_lista(conn, "linkedin", [_entrada("Ana Lima")], AGORA)
    conn.commit()

    assert listas.cache_valido(conn, "linkedin", 30, "2026-10-20T10:00:00+00:00") is True
    assert listas.cache_valido(conn, "linkedin", 30, "2026-11-05T10:00:00+00:00") is False
    assert listas.cache_valido(conn, "instagram", 30, AGORA) is False


def test_buscar_por_nome_ignora_acento_e_aceita_prefixo_de_sobrenome(conn: sqlite3.Connection) -> None:
    listas.substituir_lista(
        conn,
        "linkedin",
        [
            _entrada("Márcia Souza"),
            _entrada("Marcia Lopes"),
            _entrada("Marcelo Souza"),
            _entrada("Ana Marcia"),
        ],
        AGORA,
    )
    listas.substituir_lista(conn, "instagram", [_entrada("Marcia Dias", rede="instagram")], AGORA)

    nomes = {e.nome for e in listas.buscar_por_nome(conn, "linkedin", "marcia")}
    assert nomes == {"Márcia Souza", "Marcia Lopes"}
    assert [e.nome for e in listas.buscar_por_nome(conn, "linkedin", "Marcia Sou")] == ["Márcia Souza"]
    assert len(listas.buscar_por_nome(conn, None, "Marcia")) == 3
    assert listas.buscar_por_nome(conn, "linkedin", "Souza") == []


def test_filtrar_por_texto_olha_nome_e_cabecalho(conn: sqlite3.Connection) -> None:
    listas.substituir_lista(
        conn,
        "linkedin",
        [_entrada("Ana Lima", "Contadora"), _entrada("Beto Nunes", "Engenheiro")],
        AGORA,
    )

    assert [e.nome for e in listas.filtrar_por_texto(conn, "linkedin", "contadora")] == ["Ana Lima"]
    assert [e.nome for e in listas.filtrar_por_texto(conn, "linkedin", "nunes")] == ["Beto Nunes"]


def test_filtro_tolera_quebra_de_linha_e_ordem_das_palavras(conn: sqlite3.Connection) -> None:
    listas.substituir_lista(
        conn,
        "linkedin",
        [_entrada("Leonardo Vasques, CFA", "Portfolio Manager"), _entrada("Beto Nunes")],
        AGORA,
    )

    assert len(listas.filtrar_por_texto(conn, "linkedin", "leonardo \n  vasques")) == 1
    assert len(listas.filtrar_por_texto(conn, "linkedin", "vasques leonardo")) == 1


def test_nome_com_sufixo_e_pontuacao_ainda_casa(conn: sqlite3.Connection) -> None:
    listas.substituir_lista(
        conn,
        "linkedin",
        [_entrada("Leonardo Vasques, CFA"), _entrada("Samy Sanches de Almeida, JD, LL.M., MBA")],
        AGORA,
    )

    assert [e.nome for e in listas.buscar_por_nome(conn, "linkedin", "Leonardo Vasques")] == [
        "Leonardo Vasques, CFA"
    ]
    assert len(listas.buscar_por_nome(conn, "linkedin", "Samy Almeida")) == 1


def test_parecidos_acha_apelido_e_erro_de_digitacao_do_mais_para_o_menos_provavel(
    conn: sqlite3.Connection,
) -> None:
    listas.substituir_lista(
        conn,
        "linkedin",
        [
            _entrada("Leonardo Vasques, CFA"),
            _entrada("Leonardo Alves"),
            _entrada("Beto Nunes"),
        ],
        AGORA,
    )

    assert [e.nome for e in listas.buscar_parecidos(conn, "linkedin", "Leo Vasques", 0.8, 5)] == [
        "Leonardo Vasques, CFA"
    ]
    assert [e.nome for e in listas.buscar_parecidos(conn, "linkedin", "Leonardo Vasquez", 0.8, 5)] == [
        "Leonardo Vasques, CFA"
    ]
    assert listas.buscar_parecidos(conn, "linkedin", "Zeca Pagodinho", 0.8, 5) == []
