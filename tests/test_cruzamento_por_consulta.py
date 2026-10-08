from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pytest

from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import assunto_contato, assuntos, fatos, perfil_tema, perfis, temas
from agente_nw.nucleo.modelos.assunto import Assunto
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
from agente_nw.nucleo.modelos.fato import Fato
from agente_nw.nucleo.relevancia.cruzamento import cruzar_contato_por_consulta
from agente_nw.nucleo.relevancia.pontuacao import avaliar, avaliar_por_consulta

AGORA = "2026-10-08T10:00:00+00:00"
DATA = "2026-10-08"


def _vetor(*valores: float) -> list[float]:
    return list(valores) + [0.0] * (1024 - len(valores))


CENTROIDE_CONSULTA = _vetor(1.0, 0.0)
# cosseno 0,64 com a consulta e 0,77 com a tag (0, 1): a tag sustenta mais que a consulta.
CENTROIDE_ASSUNTO = _vetor(1.0, 1.2)


class _ClienteFalso:
    """Embeddings controlados: texto de fato vira (0, 1); o resto (termos da consulta) vira (1, 0)."""

    def __init__(self) -> None:
        self.prompts: list[str] = []

    def embeddar(self, textos: list[str]) -> list[list[float]]:
        return [_vetor(0.0, 1.0) if "fato" in texto else _vetor(1.0, 0.0) for texto in textos]

    def gerar_json(self, tarefa_nome: str, prompt: str, esquema: type[Any]) -> Any:
        self.prompts.append(prompt)
        quantidade = prompt.rsplit("Assuntos:\n", 1)[1].count('" — tipo:')
        return RespostaCruzarPorQue(por_que=[f"serve para a consulta #{i}" for i in range(quantidade)])


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


def _abrir(tmp_path: Path, nome: str) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / f"{nome}.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


def _contexto(evitar: list[str] | None = None) -> ContextoConsulta:
    return ContextoConsulta(
        assunto="mercado de vela",
        meio="pessoalmente",
        objetivo="retomar contato",
        interessa=["regata", "barcos"],
        evitar=evitar or [],
    )


def _contato(conn: sqlite3.Connection) -> int:
    contato = perfis.inserir_ou_atualizar_contato(
        conn, "Ana", "+5511900001111", None, None, None, None, AGORA
    )
    assert contato.id is not None
    conn.commit()
    return contato.id


def _assunto(conn: sqlite3.Connection, titulo: str, centroide: list[float] = CENTROIDE_ASSUNTO) -> int:
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
    conn.commit()
    return assunto_id


def _tag(conn: sqlite3.Connection, perfil_id: int, nome: str, confirmado: bool) -> None:
    tema = temas.obter_ou_criar(conn, nome, "descrição da tag do contato", [], AGORA)
    assert tema.id is not None
    temas.gravar_embedding(conn, tema.id, _vetor(0.0, 1.0))
    perfil_tema.vincular(conn, perfil_id, tema.id, 3, "declarada", None, confirmado, AGORA)
    conn.commit()


def test_contexto_sem_tag_e_sem_tema_gera_menu_com_conector(tmp_path: Path, limiares: Limiares) -> None:
    conn = _abrir(tmp_path, "caso1")
    perfil_id = _contato(conn)
    _assunto(conn, "Regata oceânica reúne veleiros")

    resumo = cruzar_contato_por_consulta(
        _ClienteFalso(), conn, perfil_id, _contexto(), CENTROIDE_CONSULTA, limiares, AGORA
    )

    registros = assunto_contato.listar_do_dia(conn, perfil_id, DATA)
    assert resumo.sem_assunto is False
    assert len(registros) == 1
    assert registros[0].tipo == "conector"
    assert registros[0].status == "novo"
    assert registros[0].aderencia_contato == 0.0
    assert registros[0].aderencia_consulta is not None and registros[0].aderencia_consulta > 0.45
    assert registros[0].por_que


def test_tag_confirmada_eleva_o_score_e_vira_ponto_de_apoio(tmp_path: Path, limiares: Limiares) -> None:
    sem_tag = _abrir(tmp_path, "caso2a")
    perfil_a = _contato(sem_tag)
    _assunto(sem_tag, "Regata oceânica reúne veleiros")
    cruzar_contato_por_consulta(
        _ClienteFalso(), sem_tag, perfil_a, _contexto(), CENTROIDE_CONSULTA, limiares, AGORA
    )
    score_sem_tag = assunto_contato.listar_do_dia(sem_tag, perfil_a, DATA)[0].score

    com_tag = _abrir(tmp_path, "caso2b")
    perfil_b = _contato(com_tag)
    _tag(com_tag, perfil_b, "navegação", confirmado=True)
    _assunto(com_tag, "Regata oceânica reúne veleiros")
    cliente = _ClienteFalso()
    cruzar_contato_por_consulta(cliente, com_tag, perfil_b, _contexto(), CENTROIDE_CONSULTA, limiares, AGORA)
    registro = assunto_contato.listar_do_dia(com_tag, perfil_b, DATA)[0]

    assert registro.score > score_sem_tag
    assert registro.aderencia_contato > 0
    assert "ponto de apoio do usuário: navegação" in cliente.prompts[0]
    assert "Contexto da consulta: assunto: mercado de vela" in cliente.prompts[0]


def test_avaliar_por_consulta_cita_a_tag_como_ponto_de_apoio(limiares: Limiares) -> None:
    avaliacao = avaliar_por_consulta(
        CENTROIDE_ASSUNTO,
        CENTROIDE_CONSULTA,
        _vetor(0.0, 1.0),
        [],
        0.8,
        limiares.conector,
        termos_consulta=[("mercado de vela", CENTROIDE_CONSULTA)],
        tags_contato=[("navegação", _vetor(0.0, 1.0))],
    )
    assert avaliacao.tipo == "conector"
    assert avaliacao.ponto_de_apoio == "navegação"


def test_fatos_sem_tag_formam_o_centroide_do_contato(tmp_path: Path, limiares: Limiares) -> None:
    conn = _abrir(tmp_path, "caso3")
    perfil_id = _contato(conn)
    for indice in range(3):
        fatos.inserir(
            conn,
            Fato(
                perfil_id=perfil_id,
                tipo="post",
                conteudo=f"fato {indice} sobre navegação",
                registrado_em=AGORA,
            ),
        )
    conn.commit()
    _assunto(conn, "Regata oceânica reúne veleiros")

    cruzar_contato_por_consulta(
        _ClienteFalso(), conn, perfil_id, _contexto(), CENTROIDE_CONSULTA, limiares, AGORA
    )

    assert perfis.obter_centroide(conn, perfil_id) is not None
    registro = assunto_contato.listar_do_dia(conn, perfil_id, DATA)[0]
    assert registro.aderencia_contato > 0


def test_termo_de_evitar_descarta_o_candidato(tmp_path: Path, limiares: Limiares) -> None:
    conn = _abrir(tmp_path, "caso4")
    perfil_id = _contato(conn)
    evitado = _assunto(conn, "Política fiscal domina o debate")
    mantido = _assunto(conn, "Regata oceânica reúne veleiros")

    resumo = cruzar_contato_por_consulta(
        _ClienteFalso(), conn, perfil_id, _contexto(evitar=["politica"]), CENTROIDE_CONSULTA, limiares, AGORA
    )

    por_assunto = {r.assunto_id: r for r in assunto_contato.listar_do_dia(conn, perfil_id, DATA)}
    assert por_assunto[evitado].status == "descartado"
    assert por_assunto[evitado].motivo == "evitado pelo contexto"
    assert por_assunto[mantido].status == "novo"
    assert resumo.descartados == 1


def test_avaliar_antigo_segue_identico() -> None:
    limiares_conector = ConectorLimiares(
        adjacencia_minima=0.55,
        conversavel_viavel=0.8,
        consulta=ConsultaLimiares(
            minima=0.45,
            peso_consulta=50,
            peso_contato=25,
            peso_usuario=10,
            peso_conversavel=15,
            selecao_peso_consulta=0.7,
            selecao_peso_contato=0.3,
        ),
        peso_aderencia_contato=50,
        peso_aderencia_usuario=30,
        peso_conversavel=20,
        peso_nivel={"dominio": 1.0, "interesse": 0.7, "curiosidade": 0.4},
        candidatos_por_contato=10,
        itens_no_menu=5,
    )
    avaliacao = avaliar(
        _vetor(1.0, 0.0), _vetor(1.0, 0.0), [("tema", "dominio", _vetor(1.0, 0.0))], 0.9, limiares_conector
    )
    assert avaliacao.tipo == "conector"
    assert avaliacao.ponto_de_apoio == "tema"
    assert avaliacao.aderencia_consulta is None
    assert avaliacao.score == pytest.approx(50 + 30 + 18)
