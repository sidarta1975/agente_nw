"""O gate casa resposta e candidato pela ordem; tamanho errado cai para a fila de revisão e não
filtra nada — o pedido segue como antes do gate (brief 049)."""

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
from agente_nw.nucleo.modelos.cruzamento import (
    AvaliacaoRelacaoObjetivo,
    RespostaAvaliarRelacaoObjetivo,
    RespostaCruzarPorQue,
)
from agente_nw.nucleo.relevancia.cruzamento import cruzar_contato_por_consulta

AGORA = "2026-10-15T10:00:00+00:00"
DATA = "2026-10-15"


def _vetor(*valores: float) -> list[float]:
    return list(valores) + [0.0] * (1024 - len(valores))


CENTROIDE_CONSULTA = _vetor(1.0, 0.0)
CENTROIDE_ASSUNTO = _vetor(1.0, 0.0)


def _quantidade_candidatos(prompt: str) -> int:
    linhas = prompt.rsplit("Candidatos:\n", 1)[1].splitlines()
    return len([linha for linha in linhas if linha.strip()])


class _ClienteGatePosicional:
    """Devolve exatamente `respostas`, na ordem recebida — testa que o casamento é por posição."""

    def __init__(self, respostas: list[bool]) -> None:
        self._respostas = respostas

    def embeddar(self, textos: list[str]) -> list[list[float]]:
        return [CENTROIDE_CONSULTA for _ in textos]

    def gerar_json(self, tarefa_nome: str, prompt: str, esquema: type[Any]) -> Any:
        if tarefa_nome == "avaliar_relacao_objetivo":
            return RespostaAvaliarRelacaoObjetivo(
                avaliacoes=[AvaliacaoRelacaoObjetivo(relaciona=r, motivo="") for r in self._respostas]
            )
        quantidade = prompt.rsplit("Assuntos:\n", 1)[1].count('" — tipo:')
        return RespostaCruzarPorQue(por_que=[f"motivo {i}" for i in range(quantidade)])


class _ClienteGateTamanhoErrado:
    """O gate sempre devolve uma avaliação de menos — nunca bate com a quantidade esperada."""

    def __init__(self) -> None:
        self.chamadas_gate = 0

    def embeddar(self, textos: list[str]) -> list[list[float]]:
        return [CENTROIDE_CONSULTA for _ in textos]

    def gerar_json(self, tarefa_nome: str, prompt: str, esquema: type[Any]) -> Any:
        if tarefa_nome == "avaliar_relacao_objetivo":
            self.chamadas_gate += 1
            quantidade = _quantidade_candidatos(prompt)
            return RespostaAvaliarRelacaoObjetivo(
                avaliacoes=[AvaliacaoRelacaoObjetivo(relaciona=True, motivo="")] * (quantidade - 1)
            )
        quantidade = prompt.rsplit("Assuntos:\n", 1)[1].count('" — tipo:')
        return RespostaCruzarPorQue(por_que=[f"motivo {i}" for i in range(quantidade)])


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
        assunto="eleição da OAB-SP", meio="pessoalmente", objetivo="apoiar a chapa da OAB-SP", livre="pedido"
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


def test_resposta_do_gate_casa_candidato_a_candidato_na_ordem(tmp_path: Path, limiares: Limiares) -> None:
    conn = _abrir(tmp_path)
    perfil_id = _contato(conn)
    a = _assunto(conn, "Assunto A")
    b = _assunto(conn, "Assunto B")
    c = _assunto(conn, "Assunto C")

    resumo = cruzar_contato_por_consulta(
        _ClienteGatePosicional([True, False, True]),
        conn,
        perfil_id,
        _contexto(),
        CENTROIDE_CONSULTA,
        limiares,
        AGORA,
    )

    por_assunto = {r.assunto_id: r for r in assunto_contato.listar_do_dia(conn, perfil_id, DATA)}
    assert por_assunto[a].tipo == "conector" and por_assunto[a].status == "novo"
    assert por_assunto[b].tipo == "fora_do_dominio" and por_assunto[b].status == "descartado"
    assert por_assunto[c].tipo == "conector" and por_assunto[c].status == "novo"
    assert resumo.conectores == 2
    assert resumo.descartados == 1


def test_resposta_de_tamanho_errado_vai_para_fila_revisao_e_nao_filtra(
    tmp_path: Path, limiares: Limiares
) -> None:
    conn = _abrir(tmp_path)
    perfil_id = _contato(conn)
    a = _assunto(conn, "Assunto A")
    b = _assunto(conn, "Assunto B")
    cliente = _ClienteGateTamanhoErrado()

    resumo = cruzar_contato_por_consulta(
        cliente, conn, perfil_id, _contexto(), CENTROIDE_CONSULTA, limiares, AGORA
    )

    # cai para fila_revisao em toda tentativa (2), nunca bate o tamanho esperado
    assert cliente.chamadas_gate == 2
    (n_fila,) = conn.execute(
        "SELECT COUNT(*) FROM fila_revisao WHERE tarefa = 'avaliar_relacao_objetivo'"
    ).fetchone()
    assert n_fila == 1
    assert resumo.erros == 1

    # sem gate (como está hoje): os dois candidatos seguem como conector, nenhum descartado pelo gate
    por_assunto = {r.assunto_id: r for r in assunto_contato.listar_do_dia(conn, perfil_id, DATA)}
    assert por_assunto[a].tipo == "conector" and por_assunto[a].status == "novo"
    assert por_assunto[b].tipo == "conector" and por_assunto[b].status == "novo"
    assert resumo.conectores == 2
    assert resumo.descartados == 0
