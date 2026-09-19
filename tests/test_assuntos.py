from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import assuntos
from agente_nw.nucleo.modelos.assunto import Assunto


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


def _vetor(*valores: float) -> list[float]:
    return list(valores) + [0.0] * (1024 - len(valores))


def _criar_assunto(conn: sqlite3.Connection, ultimo_visto: str, status: str) -> int:
    assunto = Assunto(
        primeiro_visto=ultimo_visto,
        ultimo_visto=ultimo_visto,
        n_itens=1,
        n_fontes_independentes=1,
        status=status,  # type: ignore[arg-type]
    )
    return assuntos.inserir(conn, assunto)


def test_inserir_e_obter_por_id_fazem_ida_e_volta(conn: sqlite3.Connection) -> None:
    assunto_id = _criar_assunto(conn, "2026-09-10", "novo")
    conn.commit()

    resultado = assuntos.obter_por_id(conn, assunto_id)

    assert resultado is not None
    assert resultado.id == assunto_id
    assert resultado.status == "novo"
    assert resultado.temas == []


def test_obter_por_id_devolve_none_quando_nao_existe(conn: sqlite3.Connection) -> None:
    assert assuntos.obter_por_id(conn, 999) is None


def test_listar_candidatos_traz_so_os_dentro_da_janela_ou_do_prazo_de_reabertura(
    conn: sqlite3.Connection,
) -> None:
    dentro_janela = _criar_assunto(conn, "2026-09-15", "em_curso")
    fora_janela = _criar_assunto(conn, "2026-09-01", "novo")
    encerrado_dentro_reabertura = _criar_assunto(conn, "2026-08-20", "encerrado")
    encerrado_fora_reabertura = _criar_assunto(conn, "2026-01-01", "encerrado")
    conn.commit()

    candidatos = assuntos.listar_candidatos(conn, desde_janela="2026-09-11", desde_reabertura="2026-06-21")

    ids = {a.id for a in candidatos}
    assert ids == {dentro_janela, encerrado_dentro_reabertura}
    assert fora_janela not in ids
    assert encerrado_fora_reabertura not in ids


def test_atualizar_apos_item_altera_campos_esperados(conn: sqlite3.Connection) -> None:
    assunto_id = _criar_assunto(conn, "2026-09-10", "novo")
    conn.commit()

    assuntos.atualizar_apos_item(
        conn,
        assunto_id,
        ultimo_visto="2026-09-15",
        n_itens=3,
        n_fontes_independentes=2,
        status="em_curso",
        agora="2026-09-18T00:00:00+00:00",
    )
    conn.commit()

    resultado = assuntos.obter_por_id(conn, assunto_id)
    assert resultado is not None
    assert resultado.ultimo_visto == "2026-09-15"
    assert resultado.n_itens == 3
    assert resultado.n_fontes_independentes == 2
    assert resultado.status == "em_curso"


def test_fechar_inativos_muda_status_e_devolve_contagem(conn: sqlite3.Connection) -> None:
    ativo_velho = _criar_assunto(conn, "2026-09-01", "em_curso")
    ativo_recente = _criar_assunto(conn, "2026-09-17", "novo")
    ja_encerrado = _criar_assunto(conn, "2026-08-01", "encerrado")
    conn.commit()

    quantidade = assuntos.fechar_inativos(conn, antes_de="2026-09-10", agora="2026-09-18T00:00:00+00:00")
    conn.commit()

    assert quantidade == 1
    assert assuntos.obter_por_id(conn, ativo_velho).status == "encerrado"  # type: ignore[union-attr]
    assert assuntos.obter_por_id(conn, ativo_recente).status == "novo"  # type: ignore[union-attr]
    assert assuntos.obter_por_id(conn, ja_encerrado).status == "encerrado"  # type: ignore[union-attr]


def test_listar_maiores_que_filtra_por_n_itens(conn: sqlite3.Connection) -> None:
    pequeno = Assunto(primeiro_visto="2026-09-01", ultimo_visto="2026-09-01", n_itens=5, status="em_curso")
    grande = Assunto(primeiro_visto="2026-09-01", ultimo_visto="2026-09-01", n_itens=13, status="em_curso")
    id_pequeno = assuntos.inserir(conn, pequeno)
    id_grande = assuntos.inserir(conn, grande)
    conn.commit()

    resultado = assuntos.listar_maiores_que(conn, 12)

    ids = [a.id for a in resultado]
    assert id_grande in ids
    assert id_pequeno not in ids


def test_gravar_e_obter_centroide_faz_ida_e_volta(conn: sqlite3.Connection) -> None:
    assunto_id = _criar_assunto(conn, "2026-09-10", "novo")
    conn.commit()

    centroide = _vetor(0.1, 0.2, 0.3, 0.4)
    assuntos.gravar_centroide(conn, assunto_id, centroide)
    conn.commit()

    resultado = assuntos.obter_centroide(conn, assunto_id)

    assert resultado is not None
    assert [round(v, 6) for v in resultado] == centroide


def test_obter_centroide_devolve_none_quando_nao_gravado(conn: sqlite3.Connection) -> None:
    assunto_id = _criar_assunto(conn, "2026-09-10", "novo")
    conn.commit()

    assert assuntos.obter_centroide(conn, assunto_id) is None
