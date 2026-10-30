"""O gate reprova tudo: o menu zera, e a entrega (brief 047) fica só na mensagem base (brief 049)."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pytest

from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import assunto_contato, assuntos, perfis
from agente_nw.nucleo.modelos.assunto import Assunto
from agente_nw.nucleo.modelos.configuracao import (
    AgrupamentoLimiares,
    CartaoLimiares,
    ColetaLimiares,
    ConectorLimiares,
    ConsultaLimiares,
    Limiares,
    ListasLimiares,
    QualificacaoLimiares,
)
from agente_nw.nucleo.modelos.contexto_consulta import ContextoConsulta
from agente_nw.nucleo.modelos.cruzamento import AvaliacaoRelacaoObjetivo, RespostaAvaliarRelacaoObjetivo
from agente_nw.nucleo.relevancia.cruzamento import cruzar_contato_por_consulta

AGORA = "2026-10-15T10:00:00+00:00"
DATA = "2026-10-15"


def _vetor(*valores: float) -> list[float]:
    return list(valores) + [0.0] * (1024 - len(valores))


CENTROIDE_CONSULTA = _vetor(1.0, 0.0)
CENTROIDE_ASSUNTO = _vetor(1.0, 0.0)


class _ClienteGateReprovaTudo:
    """O gate nunca encontra relação com o objetivo — `cruzar_por_que` nem deveria ser chamado."""

    def __init__(self) -> None:
        self.chamou_cruzar_por_que = False

    def embeddar(self, textos: list[str]) -> list[list[float]]:
        return [CENTROIDE_CONSULTA for _ in textos]

    def gerar_json(self, tarefa_nome: str, prompt: str, esquema: type[Any]) -> Any:
        if tarefa_nome == "avaliar_relacao_objetivo":
            linhas = prompt.rsplit("Candidatos:\n", 1)[1].splitlines()
            quantidade = len([linha for linha in linhas if linha.strip()])
            return RespostaAvaliarRelacaoObjetivo(
                avaliacoes=[AvaliacaoRelacaoObjetivo(relaciona=False, motivo="sem relação")] * quantidade
            )
        self.chamou_cruzar_por_que = True
        raise AssertionError("cruzar_por_que não deveria ser chamado com o menu zerado")


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
        listas=ListasLimiares(maximo_entradas=2000, pausa_rolagem_s=0, validade_dias=30),
    )


def _abrir(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


def _contexto() -> ContextoConsulta:
    return ContextoConsulta(
        assunto="eleição da OAB-SP",
        meio="pessoalmente",
        objetivo="apoiar a chapa da OAB-SP",
        livre="Queria pedir apoio pro Luiz na chapa da OAB-SP.",
    )


def _contato(conn: sqlite3.Connection) -> int:
    contato = perfis.inserir_ou_atualizar_contato(
        conn, "Luiz", "+5511900001111", None, None, None, None, AGORA
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
    assuntos.gravar_centroide(conn, assunto_id, CENTROIDE_ASSUNTO)
    conn.commit()
    return assunto_id


def test_gate_reprova_tudo_zera_o_menu(tmp_path: Path, limiares: Limiares) -> None:
    conn = _abrir(tmp_path)
    perfil_id = _contato(conn)
    lula = _assunto(conn, "Apoiadores de Lula ocupam Copacabana")
    bolsonaro = _assunto(conn, "Bolsonaro discursa em manifestação neste domingo")
    cliente = _ClienteGateReprovaTudo()

    resumo = cruzar_contato_por_consulta(
        cliente, conn, perfil_id, _contexto(), CENTROIDE_CONSULTA, limiares, AGORA
    )

    assert resumo.sem_assunto is True
    assert resumo.motivo == "nenhum candidato com relação ao objetivo (juízo do modelo)"
    assert resumo.conectores == 0
    assert resumo.descartados == 2
    assert cliente.chamou_cruzar_por_que is False  # nenhum gancho de notícia forçado (brief 047)

    por_assunto = {r.assunto_id: r for r in assunto_contato.listar_do_dia(conn, perfil_id, DATA)}
    assert por_assunto[lula].tipo == "fora_do_dominio" and por_assunto[lula].status == "descartado"
    assert por_assunto[bolsonaro].tipo == "fora_do_dominio"
