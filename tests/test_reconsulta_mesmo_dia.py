from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pytest

from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import assunto_contato, assuntos, perfis
from agente_nw.nucleo.modelos.assunto import Assunto
from agente_nw.nucleo.modelos.assunto_contato import AssuntoContato
from agente_nw.nucleo.modelos.configuracao import (
    AgrupamentoLimiares,
    CartaoLimiares,
    ColetaLimiares,
    ConectorLimiares,
    ConsultaLimiares,
    Limiares,
    QualificacaoLimiares,
)
from agente_nw.nucleo.modelos.contexto_consulta import ContextoConsulta
from agente_nw.nucleo.modelos.cruzamento import RespostaCruzarPorQue
from agente_nw.nucleo.relevancia.cruzamento import cruzar_contato_por_consulta

AGORA = "2026-10-08T10:00:00+00:00"
DATA = "2026-10-08"
ONTEM = "2026-10-07"


def _vetor(*valores: float) -> list[float]:
    return list(valores) + [0.0] * (1024 - len(valores))


CENTROIDE_CONSULTA = _vetor(1.0, 0.0)


class _ClienteFalso:
    def embeddar(self, textos: list[str]) -> list[list[float]]:
        return [_vetor(1.0, 0.0) for _ in textos]

    def gerar_json(self, tarefa_nome: str, prompt: str, esquema: type[Any]) -> Any:
        quantidade = prompt.rsplit("Assuntos:\n", 1)[1].count('" — tipo:')
        return RespostaCruzarPorQue(por_que=["serve para a consulta"] * quantidade)


@pytest.fixture
def limiares() -> Limiares:
    return Limiares(
        agrupamento=AgrupamentoLimiares(
            cosseno_mesmo_assunto=0.82,
            cosseno_republicacao=0.94,
            divergencia_minima_fonte_independente=0.08,
            janela_dias=7,
            itens_para_dividir=12,
        ),
        qualificacao=QualificacaoLimiares(substancial_minimo=0.6, conversavel_minimo=0.6, teto_por_dia=40),
        conector=ConectorLimiares(
            adjacencia_minima=0.55,
            conversavel_viavel=0.8,
            peso_aderencia_contato=50,
            peso_aderencia_usuario=30,
            peso_conversavel=20,
            peso_nivel={"dominio": 1.0, "interesse": 0.7, "curiosidade": 0.4},
            candidatos_por_contato=10,
            itens_no_menu=5,
            consulta=ConsultaLimiares(
                minima=0.45,
                peso_consulta=50,
                peso_contato=25,
                peso_usuario=10,
                peso_conversavel=15,
                selecao_peso_consulta=0.7,
                selecao_peso_contato=0.3,
            ),
        ),
        coleta=ColetaLimiares(
            teaser_minimo_caracteres=400,
            dias_max_primeira_aparicao=7,
            retencao_texto_dias=90,
            intervalo_google_news_segundos=0,
            dias_alerta_feed_vazio=2,
        ),
        cartao=CartaoLimiares(teto_por_dia=40),
    )


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


def _contato(conn: sqlite3.Connection) -> int:
    contato = perfis.inserir_ou_atualizar_contato(
        conn, "Ana", "+5511900001111", None, None, None, None, AGORA
    )
    assert contato.id is not None
    conn.commit()
    return contato.id


def _assunto(conn: sqlite3.Connection, titulo: str) -> int:
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
    assuntos.gravar_centroide(conn, assunto_id, _vetor(1.0, 0.1))
    conn.commit()
    return assunto_id


def _contexto(assunto: str = "mercado de vela", evitar: list[str] | None = None) -> ContextoConsulta:
    return ContextoConsulta(assunto=assunto, meio="pessoalmente", objetivo="retomar", evitar=evitar or [])


def _consultar(
    conn: sqlite3.Connection, perfil_id: int, limiares: Limiares, contexto: ContextoConsulta
) -> None:
    cruzar_contato_por_consulta(
        _ClienteFalso(), conn, perfil_id, contexto, CENTROIDE_CONSULTA, limiares, AGORA
    )


def _por_assunto(conn: sqlite3.Connection, perfil_id: int) -> dict[int, AssuntoContato]:
    return {r.assunto_id: r for r in assunto_contato.listar_do_dia(conn, perfil_id, DATA)}


def test_segunda_consulta_substitui_o_menu_e_preserva_o_que_foi_usado(
    conn: sqlite3.Connection, limiares: Limiares
) -> None:
    perfil_id = _contato(conn)
    a = _assunto(conn, "Regata oceânica reúne veleiros")
    b = _assunto(conn, "Veleiros novos chegam ao mercado")

    _consultar(conn, perfil_id, limiares, _contexto("primeiro contexto"))
    registro_b = _por_assunto(conn, perfil_id)[b]
    assert registro_b.id is not None
    assunto_contato.marcar_usado(conn, registro_b.id)
    conn.commit()

    _consultar(conn, perfil_id, limiares, _contexto("segundo contexto"))

    linhas = _por_assunto(conn, perfil_id)
    assert linhas[a].status == "novo"
    assert linhas[b].status == "usado"
    assert len(linhas) == 2


def test_assunto_descartado_por_evitar_volta_quando_o_termo_sai(
    conn: sqlite3.Connection, limiares: Limiares
) -> None:
    perfil_id = _contato(conn)
    a = _assunto(conn, "Regata oceânica reúne veleiros")

    _consultar(conn, perfil_id, limiares, _contexto(evitar=["regata"]))
    assert _por_assunto(conn, perfil_id)[a].status == "descartado"
    assert _por_assunto(conn, perfil_id)[a].motivo == "evitado pelo contexto"

    _consultar(conn, perfil_id, limiares, _contexto())
    assert _por_assunto(conn, perfil_id)[a].status == "novo"


def test_assunto_nao_serve_de_ontem_nao_aparece_hoje(conn: sqlite3.Connection, limiares: Limiares) -> None:
    perfil_id = _contato(conn)
    recusado = _assunto(conn, "Regata oceânica reúne veleiros")
    outro = _assunto(conn, "Veleiros novos chegam ao mercado")
    assunto_contato.inserir(
        conn,
        AssuntoContato(
            assunto_id=recusado,
            perfil_id=perfil_id,
            gerado_em=ONTEM,
            tipo="conector",
            aderencia_contato=0.0,
            aderencia_usuario=0.0,
            conversavel=0.8,
            score=50.0,
            status="nao_serve",
            motivo="já falamos disso",
        ),
    )
    conn.commit()

    _consultar(conn, perfil_id, limiares, _contexto())

    linhas = _por_assunto(conn, perfil_id)
    assert recusado not in linhas
    assert linhas[outro].status == "novo"
