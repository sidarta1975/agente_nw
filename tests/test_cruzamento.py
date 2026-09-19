from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pytest

from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import assuntos, perfil_tema, perfis, temas
from agente_nw.nucleo.llm import FalhaJsonInvalido
from agente_nw.nucleo.modelos.assunto import Assunto
from agente_nw.nucleo.modelos.configuracao import (
    AgrupamentoLimiares,
    ColetaLimiares,
    ConectorLimiares,
    Limiares,
    QualificacaoLimiares,
)
from agente_nw.nucleo.modelos.cruzamento import RespostaCruzarPorQue
from agente_nw.nucleo.relevancia.cruzamento import cruzar_contato

AGORA = "2026-09-19T00:00:00+00:00"


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


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
        ),
        coleta=ColetaLimiares(
            teaser_minimo_caracteres=400,
            dias_max_primeira_aparicao=7,
            retencao_texto_dias=90,
            intervalo_google_news_segundos=0,
            dias_alerta_feed_vazio=2,
        ),
    )


def _vetor(*valores: float) -> list[float]:
    return list(valores) + [0.0] * (1024 - len(valores))


class _ClienteFake:
    def __init__(self, respostas: list[RespostaCruzarPorQue | Exception]) -> None:
        self._respostas = list(respostas)
        self.chamadas = 0

    def gerar_json(self, tarefa_nome: str, prompt: str, esquema: type[Any]) -> Any:
        self.chamadas += 1
        resposta = self._respostas.pop(0)
        if isinstance(resposta, Exception):
            raise resposta
        return resposta


def _preparar_usuario_com_tema(conn: sqlite3.Connection) -> None:
    usuario = perfis.upsert_usuario(conn, "Usuário Teste", AGORA)
    assert usuario.id is not None
    tema_usuario = temas.obter_ou_criar(conn, "tema-usuario", "descrição do tema", [], AGORA)
    assert tema_usuario.id is not None
    temas.gravar_embedding(conn, tema_usuario.id, _vetor(1.0, 0.0))
    perfil_tema.vincular(conn, usuario.id, tema_usuario.id, 5, "declarada", "dominio", True, AGORA)
    conn.commit()


def _criar_contato_com_tema(conn: sqlite3.Connection, telefone: str, vetor_tema: list[float]) -> int:
    contato = perfis.inserir_ou_atualizar_contato(conn, "Fulano", telefone, None, None, None, None, AGORA)
    assert contato.id is not None
    tema_contato = temas.obter_ou_criar(conn, f"tema-contato-{telefone}", "descrição do tema", [], AGORA)
    assert tema_contato.id is not None
    temas.gravar_embedding(conn, tema_contato.id, vetor_tema)
    perfil_tema.vincular(conn, contato.id, tema_contato.id, 3, "declarada", "dominio", True, AGORA)
    conn.commit()
    return contato.id


def _criar_assunto_qualificado(
    conn: sqlite3.Connection, centroide: list[float], conversavel: float = 0.8, titulo: str = "Título"
) -> int:
    assunto = Assunto(
        titulo_gerado=titulo,
        primeiro_visto=AGORA,
        ultimo_visto=AGORA,
        n_itens=1,
        status="novo",
        substancial=0.8,
        conversavel=conversavel,
    )
    assunto_id = assuntos.inserir(conn, assunto)
    assuntos.gravar_centroide(conn, assunto_id, centroide)
    return assunto_id


def test_contato_sem_tema_confirmado_da_sem_assunto_sem_chamar_o_modelo(
    conn: sqlite3.Connection, limiares: Limiares
) -> None:
    contato = perfis.inserir_ou_atualizar_contato(
        conn, "Fulano", "+5511900000000", None, None, None, None, AGORA
    )
    assert contato.id is not None
    conn.commit()

    cliente = _ClienteFake([])
    resumo = cruzar_contato(cliente, conn, contato.id, limiares, AGORA)

    assert resumo.sem_assunto is True
    assert resumo.motivo == "contato sem tema confirmado"
    assert cliente.chamadas == 0


def test_todos_candidatos_fora_do_dominio_da_sem_assunto_sem_chamar_o_modelo(
    conn: sqlite3.Connection, limiares: Limiares
) -> None:
    _preparar_usuario_com_tema(conn)
    perfil_id = _criar_contato_com_tema(conn, "+5511900000000", _vetor(1.0, 0.0))
    # centroide do assunto longe do tema do usuário (cosseno 0) e conversável entre os dois limiares
    # (>= 0,6 de qualificacao.conversavel_minimo, pra passar a candidatura; < 0,8 de
    # conector.conversavel_viavel, pra não virar viável só por conversabilidade) — fora_do_dominio
    _criar_assunto_qualificado(conn, _vetor(0.0, 1.0), conversavel=0.65)
    conn.commit()

    cliente = _ClienteFake([])
    resumo = cruzar_contato(cliente, conn, perfil_id, limiares, AGORA)

    assert resumo.sem_assunto is True
    assert resumo.motivo == "nenhum candidato passou do piso"
    assert resumo.descartados == 1
    assert cliente.chamadas == 0


def test_por_que_de_tamanho_errado_grava_sem_por_que_e_nao_trava(
    conn: sqlite3.Connection, limiares: Limiares
) -> None:
    _preparar_usuario_com_tema(conn)
    perfil_id = _criar_contato_com_tema(conn, "+5511900000000", _vetor(1.0, 0.0))
    assunto_id = _criar_assunto_qualificado(conn, _vetor(1.0, 0.0), conversavel=0.8)
    conn.commit()

    resposta_errada = RespostaCruzarPorQue(por_que=["um", "dois"])  # esperado: 1 item
    cliente = _ClienteFake([resposta_errada, resposta_errada])
    resumo = cruzar_contato(cliente, conn, perfil_id, limiares, AGORA)

    assert cliente.chamadas == 2
    assert resumo.erros == 1
    assert resumo.conectores == 1

    (por_que,) = conn.execute(
        "SELECT por_que FROM assunto_contato WHERE assunto_id = ?", (assunto_id,)
    ).fetchone()
    assert por_que is None

    linha_fila = conn.execute("SELECT tarefa, entrada FROM fila_revisao").fetchone()
    assert linha_fila is not None
    assert linha_fila["tarefa"] == "cruzar_por_que"
    assert linha_fila["entrada"] == str(perfil_id)


def test_por_que_com_falha_de_json_depois_sucesso_grava_normalmente(
    conn: sqlite3.Connection, limiares: Limiares
) -> None:
    _preparar_usuario_com_tema(conn)
    perfil_id = _criar_contato_com_tema(conn, "+5511900000000", _vetor(1.0, 0.0))
    _criar_assunto_qualificado(conn, _vetor(1.0, 0.0), conversavel=0.8)
    conn.commit()

    falha = FalhaJsonInvalido("cruzar_por_que", 1, "json inválido")
    sucesso = RespostaCruzarPorQue(por_que=["justificativa real"])
    cliente = _ClienteFake([falha, sucesso])
    resumo = cruzar_contato(cliente, conn, perfil_id, limiares, AGORA)

    assert cliente.chamadas == 2
    assert resumo.erros == 0
    (por_que,) = conn.execute("SELECT por_que FROM assunto_contato").fetchone()
    assert por_que == "justificativa real"


def test_assunto_contato_gravado_com_assunto_id_certo_em_cada_posicao(
    conn: sqlite3.Connection, limiares: Limiares
) -> None:
    _preparar_usuario_com_tema(conn)
    perfil_id = _criar_contato_com_tema(conn, "+5511900000000", _vetor(1.0, 0.0))
    assunto_a = _criar_assunto_qualificado(conn, _vetor(1.0, 0.0), conversavel=0.8, titulo="Assunto A")
    assunto_b = _criar_assunto_qualificado(conn, _vetor(0.99, 0.14), conversavel=0.8, titulo="Assunto B")
    conn.commit()

    resposta = RespostaCruzarPorQue(por_que=["por que A", "por que B"])
    cliente = _ClienteFake([resposta])
    resumo = cruzar_contato(cliente, conn, perfil_id, limiares, AGORA)

    assert resumo.conectores == 2

    linhas = {
        row["assunto_id"]: row["por_que"]
        for row in conn.execute("SELECT assunto_id, por_que FROM assunto_contato")
    }
    # assunto_a é o candidato mais próximo (cosseno 1.0 exato) e vem antes na ordem final
    assert linhas[assunto_a] == "por que A"
    assert linhas[assunto_b] == "por que B"
