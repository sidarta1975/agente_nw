from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import assuntos, perfis
from agente_nw.nucleo.modelos.assunto import Assunto
from agente_nw.nucleo.modelos.configuracao import ConsultaLimiares
from agente_nw.nucleo.relevancia.candidatos import selecionar_por_consulta

AGORA = "2026-10-08T10:00:00+00:00"
_LIMIARES = ConsultaLimiares(
    minima=0.45,
    peso_consulta=50,
    peso_contato=25,
    peso_usuario=10,
    peso_conversavel=15,
    selecao_peso_consulta=0.7,
    selecao_peso_contato=0.3,
)


def _vetor(*valores: float) -> list[float]:
    return list(valores) + [0.0] * (1024 - len(valores))


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


def _assunto(conn: sqlite3.Connection, titulo: str, centroide: list[float]) -> int:
    assunto_id = assuntos.inserir(
        conn,
        Assunto(
            titulo_gerado=titulo,
            primeiro_visto=AGORA,
            ultimo_visto=AGORA,
            n_itens=1,
            status="novo",
            substancial=0.8,
            conversavel=0.8,
        ),
    )
    assuntos.gravar_centroide(conn, assunto_id, centroide)
    return assunto_id


def test_ordenacao_usa_so_a_consulta_sem_centroide_do_contato(conn: sqlite3.Connection) -> None:
    contato = perfis.inserir_ou_atualizar_contato(
        conn, "Ana", "+5511900001111", None, None, None, None, AGORA
    )
    assert contato.id is not None
    a = _assunto(conn, "A", _vetor(1.0, 0.0))
    b = _assunto(conn, "B", _vetor(0.8, 0.6))
    conn.commit()

    ordem, _ = selecionar_por_consulta(conn, contato.id, _vetor(1.0, 0.0), None, 0.6, 0.6, 10, [], _LIMIARES)

    assert [x.id for x in ordem] == [a, b]


def test_centroide_do_contato_entra_com_peso_03(conn: sqlite3.Connection) -> None:
    contato = perfis.inserir_ou_atualizar_contato(
        conn, "Ana", "+5511900001111", None, None, None, None, AGORA
    )
    assert contato.id is not None
    a = _assunto(conn, "A", _vetor(1.0, 0.0))  # 0,7 × 1,0 + 0,3 × 0,0 = 0,70
    b = _assunto(conn, "B", _vetor(0.8, 0.6))  # 0,7 × 0,8 + 0,3 × 0,6 = 0,74
    conn.commit()

    ordem, _ = selecionar_por_consulta(conn, contato.id, _vetor(1.0, 0.0), _vetor(0.0, 1.0), 0.6, 0.6, 10, [], _LIMIARES)

    assert [x.id for x in ordem] == [b, a]


def test_evitados_saem_antes_do_corte_e_nao_ocupam_vaga(conn: sqlite3.Connection) -> None:
    contato = perfis.inserir_ou_atualizar_contato(conn, "Ana", "+5511900001111", None, None, None, None, AGORA)
    assert contato.id is not None
    evitados = [_assunto(conn, f"Política tema {n}", _vetor(1.0, 0.0)) for n in range(3)]
    mantidos = [_assunto(conn, f"Vela tema {n}", _vetor(0.9, 0.1)) for n in range(12)]
    conn.commit()

    selecionados, descartados = selecionar_por_consulta(
        conn, contato.id, _vetor(1.0, 0.0), None, 0.6, 0.6, 10, ["politica"], _LIMIARES
    )

    assert len(selecionados) == 10  # 12 não evitados, corte em 10; nenhum evitado tomou vaga
    assert {a.id for a in selecionados} <= set(mantidos)
    assert {a.id for a in descartados} == set(evitados)
