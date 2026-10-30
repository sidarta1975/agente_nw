"""O gate (brief 049): só a notícia que o modelo julga ligada ao objetivo continua conector."""

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


# Mesmo centróide para todos os assuntos do teste: todos passam o piso por embedding (046) com a
# mesma aderência, exatamente o caso do brief ("eleição da OAB" e "política nacional" indistinguíveis
# para o vetor) — só o gate (049) separa.
CENTROIDE_CONSULTA = _vetor(1.0, 0.0)
CENTROIDE_ASSUNTO = _vetor(1.0, 0.0)


class _ClienteFalso:
    """O gate reprova tudo que não cita "OAB" no título."""

    def __init__(self) -> None:
        self.prompts_gate: list[str] = []

    def embeddar(self, textos: list[str]) -> list[list[float]]:
        return [CENTROIDE_CONSULTA for _ in textos]

    def gerar_json(self, tarefa_nome: str, prompt: str, esquema: type[Any]) -> Any:
        if tarefa_nome == "avaliar_relacao_objetivo":
            self.prompts_gate.append(prompt)
            linhas_candidatos = prompt.rsplit("Candidatos:\n", 1)[1].splitlines()
            avaliacoes = [
                AvaliacaoRelacaoObjetivo(relaciona="OAB" in linha, motivo="motivo do gate")
                for linha in linhas_candidatos
                if linha.strip()
            ]
            return RespostaAvaliarRelacaoObjetivo(avaliacoes=avaliacoes)
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


def test_candidatos_sem_relacao_com_o_objetivo_sao_descartados_e_o_relacionado_fica(
    tmp_path: Path, limiares: Limiares
) -> None:
    conn = _abrir(tmp_path)
    perfil_id = _contato(conn)
    lula = _assunto(conn, "Apoiadores de Lula ocupam Copacabana")
    bolsonaro = _assunto(conn, "Bolsonaro discursa em manifestação neste domingo")
    manifestacao = _assunto(conn, "Manifestação reúne multidão na Avenida Paulista")
    sicoob = _assunto(conn, "Sicoob anuncia nova linha de crédito para pequenas empresas")
    oab = _assunto(conn, "OAB-SP abre processo disciplinar contra startup de ensino jurídico")

    resumo = cruzar_contato_por_consulta(
        _ClienteFalso(), conn, perfil_id, _contexto(), CENTROIDE_CONSULTA, limiares, AGORA
    )

    por_assunto = {r.assunto_id: r for r in assunto_contato.listar_do_dia(conn, perfil_id, DATA)}
    for assunto_id in (lula, bolsonaro, manifestacao, sicoob):
        assert por_assunto[assunto_id].tipo == "fora_do_dominio"
        assert por_assunto[assunto_id].status == "descartado"
        assert por_assunto[assunto_id].motivo == "sem relação com o objetivo (juízo do modelo)"
    assert por_assunto[oab].tipo == "conector"
    assert por_assunto[oab].status == "novo"
    assert resumo.sem_assunto is False
    assert resumo.conectores == 1
    assert resumo.descartados == 4


def test_prompt_do_gate_leva_objetivo_frase_e_ficha(tmp_path: Path, limiares: Limiares) -> None:
    conn = _abrir(tmp_path)
    perfil_id = _contato(conn)
    perfis.atualizar_ficha_manual(conn, perfil_id, {"cargo": "advogado"}, AGORA)
    conn.commit()
    _assunto(conn, "OAB-SP abre processo disciplinar contra startup de ensino jurídico")
    cliente = _ClienteFalso()

    cruzar_contato_por_consulta(cliente, conn, perfil_id, _contexto(), CENTROIDE_CONSULTA, limiares, AGORA)

    prompt = cliente.prompts_gate[0]
    assert "Objetivo: apoiar a chapa da OAB-SP" in prompt
    assert "Frase do pedido:" in prompt and "Luiz na chapa da OAB-SP" in prompt
    assert "cargo: advogado" in prompt
    assert "tema é adequado" not in prompt or "não se o tema é adequado" in prompt
