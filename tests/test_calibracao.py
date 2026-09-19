from __future__ import annotations

import math
import random
import sqlite3
from pathlib import Path

import pytest

from agente_nw.nucleo.agrupamento import calibracao
from agente_nw.nucleo.agrupamento.calibracao import _Par, calibrar
from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import fontes, itens
from agente_nw.nucleo.modelos.calibracao import RespostaComparacaoPar
from agente_nw.nucleo.modelos.item import Item
from agente_nw.nucleo.vetores import cosseno

_ITEM_DUMMY = Item(
    id=1,
    fonte_id=1,
    url_canonica="https://exemplo.com/dummy",
    titulo="dummy",
    coletado_em="2026-01-01T00:00:00+00:00",
    hash_titulo="hash-dummy",
)


def _par(cosseno_valor: float, rotulo_llm: bool | None = None, rotulo_final: bool | None = None) -> _Par:
    return _Par(
        item_a=_ITEM_DUMMY,
        item_b=_ITEM_DUMMY,
        cosseno=cosseno_valor,
        rotulo_llm=rotulo_llm,
        rotulo_final=rotulo_final,
    )


def _vetor(graus: float) -> list[float]:
    radianos = math.radians(graus)
    # padded a 1024 dimensões (o esquema real de vetor_item): o cosseno entre dois vetores 2D
    # não muda ao completar ambos com os mesmos zeros no resto das posições.
    return [math.cos(radianos), math.sin(radianos)] + [0.0] * 1022


def test_amostragem_controle_respeita_proporcao_e_grupo_pequeno_nao_trava() -> None:
    controle_iguais = [_par(0.95) for _ in range(20)]
    controle_distintos = [_par(0.10) for _ in range(3)]

    amostra, n_iguais, n_distintos = calibracao._amostrar_controle(
        random.Random(42), controle_iguais, controle_distintos
    )

    assert n_distintos == 3  # só existem 3, não trava pedindo mais
    assert n_iguais == 12  # redistribui o restante do alvo de 15 para o grupo que tem sobra
    assert len(amostra) == 15


def test_amostragem_banda_respeita_teto_de_35() -> None:
    dentro_da_banda = [_par(0.85) for _ in range(50)]

    amostra = calibracao._amostrar_banda(random.Random(1), dentro_da_banda)

    assert len(amostra) == 35


def test_amostragem_banda_com_menos_pares_que_o_teto_nao_trava() -> None:
    dentro_da_banda = [_par(0.85) for _ in range(5)]

    amostra = calibracao._amostrar_banda(random.Random(1), dentro_da_banda)

    assert len(amostra) == 5


def test_rotular_pares_define_rotulo_final_direto_do_qwen_sem_revisao() -> None:
    par_mesmo_assunto = _par(0.90)
    par_diferentes = _par(0.20)

    class _ClienteAlternado:
        def __init__(self) -> None:
            self._respostas = iter([True, False])

        def gerar_json(
            self, tarefa_nome: str, prompt: str, esquema: type[RespostaComparacaoPar]
        ) -> RespostaComparacaoPar:
            return RespostaComparacaoPar(mesmo_assunto=next(self._respostas))

    avaliados = calibracao._rotular_pares(_ClienteAlternado(), [par_mesmo_assunto, par_diferentes])

    assert len(avaliados) == 2
    assert par_mesmo_assunto.rotulo_llm is True
    assert par_mesmo_assunto.rotulo_final is True
    assert par_diferentes.rotulo_llm is False
    assert par_diferentes.rotulo_final is False


def test_escolher_limiar_acha_o_melhor_corte_conhecido() -> None:
    pares = [
        _par(0.60, rotulo_final=False),
        _par(0.75, rotulo_final=False),
        _par(0.80, rotulo_final=True),
        _par(0.85, rotulo_final=True),
        _par(0.90, rotulo_final=True),
    ]

    assert calibracao._escolher_limiar(pares, limiar_atual=0.82) == 0.80


def test_escolher_limiar_desempata_pelo_mais_proximo_do_limiar_atual() -> None:
    pares = [
        _par(0.70, rotulo_final=True),
        _par(0.75, rotulo_final=False),
        _par(0.85, rotulo_final=True),
    ]

    assert calibracao._escolher_limiar(pares, limiar_atual=0.72) == 0.70
    assert calibracao._escolher_limiar(pares, limiar_atual=0.80) == 0.85


def test_gravar_novo_limiar_muda_so_a_linha_esperada(tmp_path: Path) -> None:
    original = (
        "agrupamento:\n"
        "  cosseno_mesmo_assunto: 0.82     # calibrar no brief 007\n"
        "  cosseno_republicacao: 0.94\n"
        "conector:\n"
        "  adjacencia_minima: 0.55         # calibrar no brief 009\n"
    )
    caminho = tmp_path / "limiares.yaml"
    caminho.write_text(original, encoding="utf-8")

    calibracao._gravar_novo_limiar(caminho, 0.75)

    resultado = caminho.read_text(encoding="utf-8")
    linhas_originais = original.splitlines()
    linhas_resultado = resultado.splitlines()

    assert linhas_resultado[0] == linhas_originais[0]
    assert linhas_resultado[1] == "  cosseno_mesmo_assunto: 0.75     # calibrar no brief 007"
    assert linhas_resultado[2:] == linhas_originais[2:]


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


class _ClienteFakeSempreMesmoAssunto:
    def gerar_json(
        self, tarefa_nome: str, prompt: str, esquema: type[RespostaComparacaoPar]
    ) -> RespostaComparacaoPar:
        return RespostaComparacaoPar(mesmo_assunto=True)


def test_calibrar_de_ponta_a_ponta_escolhe_o_menor_cosseno_quando_llm_sempre_diz_mesmo_assunto(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    fonte = fontes.obter_ou_criar(conn, "g1.globo.com", "https://g1.globo.com/rss", "g1.globo.com", "rss", 5)
    assert fonte.id is not None

    angulos = [0, 10, 40, 75, 100]
    vetores = [_vetor(g) for g in angulos]
    menor_cosseno = min(
        cosseno(vetores[i], vetores[j]) for i in range(len(vetores)) for j in range(i + 1, len(vetores))
    )

    for i, vetor in enumerate(vetores):
        item = Item(
            fonte_id=fonte.id,
            url_canonica=f"https://exemplo.com/calib-{i}",
            titulo=f"calib-{i}",
            coletado_em="2026-09-18T00:00:00+00:00",
            hash_titulo=f"hash-calib-{i}",
        )
        item_id = itens.inserir(conn, item)
        itens.gravar_embedding(conn, item_id, vetor)
    conn.commit()

    caminho_limiares = tmp_path / "limiares.yaml"
    caminho_limiares.write_text(
        "agrupamento:\n"
        "  cosseno_mesmo_assunto: 0.82     # calibrar no brief 007\n"
        "  cosseno_republicacao: 0.94\n"
        "  divergencia_minima_fonte_independente: 0.30\n"
        "  janela_dias: 7\n"
        "  itens_para_dividir: 12\n",
        encoding="utf-8",
    )
    caminho_adr = tmp_path / "adr" / "adr-0001-limiar-agrupamento.md"

    resumo = calibrar(
        _ClienteFakeSempreMesmoAssunto(),
        conn,
        caminho_limiares,
        caminho_adr,
        gerador=random.Random(7),
    )

    assert resumo.limiar_anterior == 0.82
    assert resumo.limiar_novo == round(menor_cosseno, 2)
    assert resumo.pares_avaliados == 10  # C(5,2)
    assert caminho_adr.exists()
    assert f"cosseno_mesmo_assunto: {resumo.limiar_novo}" in caminho_limiares.read_text(encoding="utf-8")
