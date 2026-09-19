from __future__ import annotations

import math
import sqlite3
from pathlib import Path

import pytest

from agente_nw.nucleo.agrupamento.agrupador import agrupar
from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import assuntos, fontes, itens
from agente_nw.nucleo.modelos.assunto import Assunto
from agente_nw.nucleo.modelos.configuracao import (
    AgrupamentoLimiares,
    CartaoLimiares,
    ColetaLimiares,
    ConectorLimiares,
    Limiares,
    QualificacaoLimiares,
)
from agente_nw.nucleo.modelos.item import Item
from agente_nw.nucleo.vetores import centroide


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
            divergencia_minima_fonte_independente=0.30,
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
        cartao=CartaoLimiares(teto_por_dia=40),
    )


class _ClienteFake:
    def __init__(self, vetores: dict[str, list[float]]) -> None:
        self._vetores = vetores

    def embeddar(self, textos: list[str]) -> list[list[float]]:
        return [self._vetores[texto] for texto in textos]


def _vetor(graus: float) -> list[float]:
    radianos = math.radians(graus)
    # padded a 1024 dimensões (o esquema real de vetor_item/vetor_assunto): o cosseno entre dois
    # vetores 2D não muda ao completar ambos com os mesmos zeros no resto das posições.
    return [math.cos(radianos), math.sin(radianos)] + [0.0] * 1022


def _criar_fonte(conn: sqlite3.Connection, dominio: str) -> int:
    fonte = fontes.obter_ou_criar(conn, dominio, f"https://{dominio}/rss", dominio, "rss", 5)
    assert fonte.id is not None
    return fonte.id


def _criar_item_pendente(conn: sqlite3.Connection, fonte_id: int, titulo: str, publicado_em: str) -> None:
    item = Item(
        fonte_id=fonte_id,
        url_canonica=f"https://exemplo.com/{titulo}",
        titulo=titulo,
        texto=None,
        publicado_em=publicado_em,
        coletado_em=publicado_em,
        hash_titulo=f"hash-{titulo}",
    )
    itens.inserir(conn, item)


def test_itens_quase_iguais_formam_um_so_e_item_diferente_abre_novo(
    conn: sqlite3.Connection, limiares: Limiares, tmp_path: Path
) -> None:
    fonte_id = _criar_fonte(conn, "g1.globo.com")
    data = "2026-09-18T00:00:00+00:00"
    _criar_item_pendente(conn, fonte_id, "item-a", data)
    _criar_item_pendente(conn, fonte_id, "item-b", data)
    _criar_item_pendente(conn, fonte_id, "item-c", data)
    conn.commit()

    vetores = {
        "item-a": _vetor(0),
        "item-b": _vetor(28.36),  # cosseno ~0.88 contra item-a: mesmo assunto, não republicação
        "item-c": _vetor(90),  # cosseno ~0 contra item-a: assunto novo
    }
    cliente = _ClienteFake(vetores)

    resumo = agrupar(cliente, conn, limiares, tmp_path / "PARE", data_referencia=data)

    assert resumo.itens_embeddados == 3
    assert resumo.assuntos_criados == 2
    assert resumo.itens_vinculados == 3

    (n_assuntos,) = conn.execute("SELECT COUNT(*) FROM assunto").fetchone()
    assert n_assuntos == 2

    assunto_ab = conn.execute(
        "SELECT a.id, a.n_itens, a.status FROM assunto a JOIN item i ON i.assunto_id = a.id "
        "WHERE i.titulo = 'item-a'"
    ).fetchone()
    assert assunto_ab["n_itens"] == 2
    assert assunto_ab["status"] == "em_curso"

    assunto_c = conn.execute(
        "SELECT a.id, a.n_itens FROM assunto a JOIN item i ON i.assunto_id = a.id WHERE i.titulo = 'item-c'"
    ).fetchone()
    assert assunto_c["n_itens"] == 1
    assert assunto_c["id"] != assunto_ab["id"]


def test_item_republicado_nao_incrementa_n_itens(
    conn: sqlite3.Connection, limiares: Limiares, tmp_path: Path
) -> None:
    fonte_id = _criar_fonte(conn, "g1.globo.com")
    data1 = "2026-09-15T00:00:00+00:00"
    data2 = "2026-09-18T00:00:00+00:00"
    _criar_item_pendente(conn, fonte_id, "original", data1)
    conn.commit()

    vetores = {"original": _vetor(0)}
    agrupar(_ClienteFake(vetores), conn, limiares, tmp_path / "PARE", data_referencia=data1)

    _criar_item_pendente(conn, fonte_id, "republicado", data2)
    conn.commit()

    vetores2 = {"republicado": _vetor(14.07)}  # cosseno ~0.97 contra o original: republicação
    resumo = agrupar(_ClienteFake(vetores2), conn, limiares, tmp_path / "PARE", data_referencia=data2)

    assert resumo.republicacoes == 1
    assert resumo.assuntos_criados == 0

    assunto = conn.execute("SELECT n_itens, ultimo_visto FROM assunto").fetchone()
    assert assunto["n_itens"] == 1
    assert assunto["ultimo_visto"] == data2

    (assunto_id_republicado,) = conn.execute(
        "SELECT assunto_id FROM item WHERE titulo = 'republicado'"
    ).fetchone()
    assert assunto_id_republicado is not None


def test_assunto_encerrado_reabre_com_item_compativel_dentro_do_prazo(
    conn: sqlite3.Connection, limiares: Limiares, tmp_path: Path
) -> None:
    fonte_id = _criar_fonte(conn, "g1.globo.com")
    assunto_antigo = Assunto(
        primeiro_visto="2026-08-01T00:00:00+00:00",
        ultimo_visto="2026-08-01T00:00:00+00:00",
        n_itens=1,
        n_fontes_independentes=1,
        status="encerrado",
        temas=[],
    )
    assunto_id = assuntos.inserir(conn, assunto_antigo)
    assuntos.gravar_centroide(conn, assunto_id, _vetor(0))
    item_original = Item(
        fonte_id=fonte_id,
        url_canonica="https://exemplo.com/item-original-encerrado",
        titulo="item-original-encerrado",
        texto=None,
        publicado_em="2026-08-01T00:00:00+00:00",
        coletado_em="2026-08-01T00:00:00+00:00",
        hash_titulo="hash-item-original-encerrado",
        assunto_id=assunto_id,
    )
    item_original_id = itens.inserir(conn, item_original)
    itens.gravar_embedding(conn, item_original_id, _vetor(0))
    conn.commit()

    data_novo_item = "2026-09-18T00:00:00+00:00"
    _criar_item_pendente(conn, fonte_id, "item-reabre", data_novo_item)
    conn.commit()

    vetores = {"item-reabre": _vetor(28.36)}  # cosseno ~0.88: mesmo assunto, não republicação
    resumo = agrupar(_ClienteFake(vetores), conn, limiares, tmp_path / "PARE", data_referencia=data_novo_item)

    assert resumo.assuntos_reabertos == 1
    assert resumo.assuntos_criados == 0

    resultado = assuntos.obter_por_id(conn, assunto_id)
    assert resultado is not None
    assert resultado.status == "em_curso"
    assert resultado.n_itens == 2
    assert resultado.ultimo_visto == data_novo_item


def test_assunto_disperso_com_mais_de_12_itens_divide_em_dois(
    conn: sqlite3.Connection, limiares: Limiares, tmp_path: Path
) -> None:
    fonte_id = _criar_fonte(conn, "g1.globo.com")
    data = "2026-09-18T00:00:00+00:00"

    vetores_bloco_a = [_vetor(0 + i) for i in range(7)]
    vetores_bloco_b = [_vetor(90 + i) for i in range(6)]
    todos_vetores = vetores_bloco_a + vetores_bloco_b

    assunto = Assunto(
        primeiro_visto=data,
        ultimo_visto=data,
        n_itens=13,
        n_fontes_independentes=2,
        status="em_curso",
        temas=[],
    )
    assunto_id = assuntos.inserir(conn, assunto)
    assuntos.gravar_centroide(conn, assunto_id, centroide(todos_vetores))

    for i, vetor in enumerate(todos_vetores):
        item = Item(
            fonte_id=fonte_id,
            url_canonica=f"https://exemplo.com/disperso-{i}",
            titulo=f"disperso-{i}",
            texto=None,
            publicado_em=data,
            coletado_em=data,
            hash_titulo=f"hash-disperso-{i}",
            assunto_id=assunto_id,
        )
        item_id = itens.inserir(conn, item)
        itens.gravar_embedding(conn, item_id, vetor)
    conn.commit()

    resumo = agrupar(_ClienteFake({}), conn, limiares, tmp_path / "PARE", data_referencia=data)

    assert resumo.assuntos_divididos == 1
    (n_assuntos,) = conn.execute("SELECT COUNT(*) FROM assunto").fetchone()
    assert n_assuntos == 2

    contagens = sorted(
        row["n_itens"] for row in conn.execute("SELECT n_itens FROM assunto ORDER BY id").fetchall()
    )
    assert contagens == [6, 7]
