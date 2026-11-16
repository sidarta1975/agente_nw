"""Comparação, em simulação, do vetor antigo e do vetor novo de cada item (brief 089, item 2.4).

Somente leitura: o banco é aberto em `mode=ro` e nada é gravado (nem vetor, nem assunto, nem limiar). O
vetor antigo é o que está gravado em `vetor_item` (o que decidiu o assunto atual do item); o novo é
`embeddar_em_partes` do texto inteiro (`agrupador.texto_do_item`). Os dois passam pela **mesma regra** do
agrupador, com os limiares de hoje, para que a diferença medida seja só a do critério:

- destino de um item: o assunto de centróide mais próximo, se o cosseno chegar a `cosseno_mesmo_assunto`;
  abaixo disso, um assunto novo só dele. Os centróides são os gravados, de qualquer versão (o vetor de
  versão antiga continua válido para leitura, brief 089 item 2.3);
- troca de assunto: destino com o vetor novo diferente do destino com o antigo;
- fusão: um assunto que, com o vetor novo, recebe itens que com o antigo iam para dois ou mais assuntos
  existentes;
- separação: um assunto cujos itens, que com o vetor antigo iam para ele, com o novo vão para dois ou mais
  destinos (cada assunto novo conta como um destino próprio);
- republicação: item com outro item da amostra, no mesmo assunto atual, de cosseno a partir de
  `cosseno_republicacao` (a regra do agrupador). Conta quem era e deixaria de ser, e quem passaria a ser.

A amostra são os `N` itens mais recentes que têm vetor gravado. A saída tem só contagens, nenhum texto."""

from __future__ import annotations

import sqlite3
import struct
from collections import defaultdict
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Protocol

import numpy as np
import sqlite_vec

from agente_nw.nucleo.agrupamento.agrupador import texto_do_item
from agente_nw.nucleo.llm import embeddar_em_partes
from agente_nw.nucleo.modelos.configuracao import Limiares
from agente_nw.nucleo.vetores import cosseno

_COSSENO_DE_VETOR_IGUAL = 0.9999
"""O vetor gravado é `float32` e o que volta do Ollama é `float64`: igualdade bit a bit não se confere aqui,
e um cosseno a partir deste valor é o mesmo vetor (o texto que cabia no corte antigo é o mesmo texto)."""

_TABELAS_DE_VETOR_COM_CRITERIO = ("vetor_tema", "vetor_assunto", "vetor_perfil")


class ClienteEmbeddagem(Protocol):
    def embeddar(self, textos: list[str]) -> list[list[float]]: ...

    @property
    def modelo_embedding(self) -> str: ...


@dataclass(frozen=True)
class Comparado:
    item_id: int
    assunto_id: int | None
    antigo: list[float]
    novo: list[float]


@dataclass(frozen=True)
class ResultadoComparacao:
    itens_na_amostra: int = 0
    itens_lidos_em_partes: int = 0
    itens_com_vetor_igual: int = 0
    itens_sem_vetor_novo: int = 0
    itens_que_trocariam_de_assunto: int = 0
    assuntos_que_se_fundiriam: int = 0
    assuntos_que_se_separariam: int = 0
    republicados_antes: int = 0
    republicacoes_que_mudariam: int = 0
    passariam_a_republicacao: int = 0
    menor_cosseno_antigo_novo: float | None = None
    mediana_cosseno_antigo_novo: float | None = None
    vetores_do_criterio_anterior: tuple[tuple[str, int, int], ...] = ()
    """(tabela, vetores de outro critério, total) — os que ficam ausentes até uma regravação autorizada."""


class _ContaChamadas:
    def __init__(self, cliente: ClienteEmbeddagem) -> None:
        self._cliente = cliente
        self.chamadas = 0

    def embeddar(self, textos: list[str]) -> list[list[float]]:
        self.chamadas += 1
        return self._cliente.embeddar(textos)


def abrir_somente_leitura(caminho: Path) -> sqlite3.Connection:
    """Abre o banco sem permissão de escrita (`mode=ro`), com o `sqlite-vec` para ler os vetores."""
    conn = sqlite3.connect(f"{caminho.resolve().as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    return conn


def _desserializar(blob: bytes) -> list[float]:
    return list(struct.unpack(f"<{len(blob) // 4}f", blob))


def _destino(vetor: list[float], ids: list[int], matriz: np.ndarray, limiar: float) -> int | None:
    if not ids:
        return None
    alvo = np.asarray(vetor, dtype=np.float64)
    norma = float(np.linalg.norm(alvo))
    if norma == 0.0:
        return None
    cossenos = matriz @ (alvo / norma)
    melhor = int(np.argmax(cossenos))
    return ids[melhor] if float(cossenos[melhor]) >= limiar else None


def _matriz(centroides: dict[int, list[float]]) -> tuple[list[int], np.ndarray]:
    ids = sorted(centroides)
    if not ids:
        return ids, np.zeros((0, 0))
    matriz = np.asarray([centroides[i] for i in ids], dtype=np.float64)
    normas = np.linalg.norm(matriz, axis=1, keepdims=True)
    normas[normas == 0.0] = 1.0
    return ids, matriz / normas


def _republicacao(grupo: list[list[float]], indice: int, limiar: float) -> bool:
    return any(cosseno(grupo[indice], outro) >= limiar for j, outro in enumerate(grupo) if j != indice)


def contar(
    amostra: list[Comparado], centroides: dict[int, list[float]], limiares: Limiares
) -> ResultadoComparacao:
    """As contagens de decisão (troca, fusão, separação, republicação) — regra no docstring do módulo."""
    ids, matriz = _matriz(centroides)
    limiar_assunto = limiares.agrupamento.cosseno_mesmo_assunto
    limiar_republicacao = limiares.agrupamento.cosseno_republicacao

    trocas = 0
    origens_por_destino_novo: dict[int, set[int]] = defaultdict(set)
    destinos_novos_por_origem: dict[int, set[tuple[str, int]]] = defaultdict(set)
    for comparado in amostra:
        antes = _destino(comparado.antigo, ids, matriz, limiar_assunto)
        depois = _destino(comparado.novo, ids, matriz, limiar_assunto)
        if antes != depois:
            trocas += 1
        if depois is not None and antes is not None:
            origens_por_destino_novo[depois].add(antes)
        if antes is not None:
            destino = ("assunto", depois) if depois is not None else ("novo", comparado.item_id)
            destinos_novos_por_origem[antes].add(destino)

    republicados_antes = deixariam = passariam = 0
    por_assunto: dict[int, list[Comparado]] = defaultdict(list)
    for comparado in amostra:
        if comparado.assunto_id is not None:
            por_assunto[comparado.assunto_id].append(comparado)
    for grupo in por_assunto.values():
        antigos = [c.antigo for c in grupo]
        novos = [c.novo for c in grupo]
        for indice in range(len(grupo)):
            antes_rep = _republicacao(antigos, indice, limiar_republicacao)
            depois_rep = _republicacao(novos, indice, limiar_republicacao)
            republicados_antes += antes_rep
            deixariam += antes_rep and not depois_rep
            passariam += depois_rep and not antes_rep

    return ResultadoComparacao(
        itens_na_amostra=len(amostra),
        itens_que_trocariam_de_assunto=trocas,
        assuntos_que_se_fundiriam=sum(
            1 for origens in origens_por_destino_novo.values() if len(origens) >= 2
        ),
        assuntos_que_se_separariam=sum(
            1 for destinos in destinos_novos_por_origem.values() if len(destinos) >= 2
        ),
        republicados_antes=republicados_antes,
        republicacoes_que_mudariam=deixariam,
        passariam_a_republicacao=passariam,
    )


def _vetores_do_criterio_anterior(
    conn: sqlite3.Connection, identificador_atual: str
) -> tuple[tuple[str, int, int], ...]:
    contagens: list[tuple[str, int, int]] = []
    for tabela in _TABELAS_DE_VETOR_COM_CRITERIO:
        (total,) = conn.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()  # noqa: S608 — nomes fixos
        (outros,) = conn.execute(
            f"SELECT COUNT(*) FROM {tabela} WHERE modelo_embedding IS NOT ?",  # noqa: S608 — nomes fixos
            (identificador_atual,),
        ).fetchone()
        contagens.append((tabela, int(outros), int(total)))
    return tuple(contagens)


def comparar(
    cliente_llm: ClienteEmbeddagem, conn: sqlite3.Connection, limiares: Limiares, amostra: int
) -> ResultadoComparacao:
    """Calcula o vetor novo dos `amostra` itens mais recentes com vetor gravado e conta o que mudaria.
    Não grava nada: `conn` deve vir de `abrir_somente_leitura`."""
    linhas = conn.execute(
        "SELECT i.id, i.titulo, i.texto, i.assunto_id, v.embedding AS embedding "
        "FROM item i JOIN vetor_item v ON v.item_id = i.id ORDER BY i.id DESC LIMIT ?",
        (amostra,),
    ).fetchall()
    centroides = {
        int(linha["assunto_id"]): _desserializar(linha["centroide"])
        for linha in conn.execute("SELECT assunto_id, centroide FROM vetor_assunto")
    }

    comparados: list[Comparado] = []
    lidos_em_partes = iguais = sem_vetor_novo = 0
    cossenos: list[float] = []
    for linha in linhas:
        contador = _ContaChamadas(cliente_llm)
        try:
            novo = embeddar_em_partes(contador, texto_do_item(linha["titulo"], linha["texto"]))
        except ValueError:  # falha numa parte: o item fica sem vetor novo, nunca com um parcial
            sem_vetor_novo += 1
            continue
        antigo = _desserializar(linha["embedding"])
        lidos_em_partes += contador.chamadas > 1
        cossenos.append(cosseno(antigo, novo))
        iguais += cossenos[-1] >= _COSSENO_DE_VETOR_IGUAL
        comparados.append(Comparado(int(linha["id"]), linha["assunto_id"], antigo, novo))

    return replace(
        contar(comparados, centroides, limiares),
        itens_na_amostra=len(linhas),
        itens_lidos_em_partes=lidos_em_partes,
        itens_com_vetor_igual=iguais,
        itens_sem_vetor_novo=sem_vetor_novo,
        menor_cosseno_antigo_novo=min(cossenos) if cossenos else None,
        mediana_cosseno_antigo_novo=float(np.median(cossenos)) if cossenos else None,
        vetores_do_criterio_anterior=_vetores_do_criterio_anterior(conn, cliente_llm.modelo_embedding),
    )
