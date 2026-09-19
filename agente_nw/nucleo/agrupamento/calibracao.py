from __future__ import annotations

import random
import re
import sqlite3
import statistics
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

import yaml

from agente_nw.nucleo.database.queries import itens
from agente_nw.nucleo.llm import FalhaJsonInvalido
from agente_nw.nucleo.modelos.calibracao import RespostaComparacaoPar
from agente_nw.nucleo.modelos.item import Item
from agente_nw.nucleo.prompts import prerotular_calibracao
from agente_nw.nucleo.vetores import cosseno

_MAX_PARES_BANDA = 35
_MAX_PARES_CONTROLE = 15
_LIMIAR_BANDA_BAIXO = 0.70
_LIMIAR_BANDA_ALTO = 0.92
_TRUNCAMENTO_TRECHO = 2000


class ClientePrerrotulagem(Protocol):
    def gerar_json(
        self, tarefa_nome: str, prompt: str, esquema: type[RespostaComparacaoPar]
    ) -> RespostaComparacaoPar: ...


@dataclass
class ResumoCalibracao:
    pares_na_banda: int
    pares_controle: int
    pares_avaliados: int
    limiar_anterior: float
    limiar_novo: float
    caminho_adr: Path


@dataclass
class _Par:
    item_a: Item
    item_b: Item
    cosseno: float
    rotulo_llm: bool | None = None
    rotulo_final: bool | None = None


def _todos_os_pares(
    itens_com_embedding: list[tuple[Item, list[float]]],
) -> tuple[list[_Par], list[_Par], list[_Par]]:
    dentro_da_banda: list[_Par] = []
    controle_iguais: list[_Par] = []
    controle_distintos: list[_Par] = []

    for i in range(len(itens_com_embedding)):
        item_a, vetor_a = itens_com_embedding[i]
        for j in range(i + 1, len(itens_com_embedding)):
            item_b, vetor_b = itens_com_embedding[j]
            c = cosseno(vetor_a, vetor_b)
            par = _Par(item_a=item_a, item_b=item_b, cosseno=c)
            if c > _LIMIAR_BANDA_ALTO:
                controle_iguais.append(par)
            elif c < _LIMIAR_BANDA_BAIXO:
                controle_distintos.append(par)
            else:
                dentro_da_banda.append(par)

    return dentro_da_banda, controle_iguais, controle_distintos


def _amostrar_banda(gerador: random.Random, dentro_da_banda: list[_Par]) -> list[_Par]:
    return gerador.sample(dentro_da_banda, min(_MAX_PARES_BANDA, len(dentro_da_banda)))


def _amostrar_controle(
    gerador: random.Random, controle_iguais: list[_Par], controle_distintos: list[_Par]
) -> tuple[list[_Par], int, int]:
    alvo_iguais = _MAX_PARES_CONTROLE - _MAX_PARES_CONTROLE // 2
    alvo_distintos = _MAX_PARES_CONTROLE // 2

    n_iguais = min(alvo_iguais, len(controle_iguais))
    n_distintos = min(alvo_distintos, len(controle_distintos))
    restante = _MAX_PARES_CONTROLE - n_iguais - n_distintos

    if restante > 0:
        extra = min(restante, len(controle_iguais) - n_iguais)
        n_iguais += extra
        restante -= extra
    if restante > 0:
        extra = min(restante, len(controle_distintos) - n_distintos)
        n_distintos += extra

    amostra = gerador.sample(controle_iguais, n_iguais) + gerador.sample(controle_distintos, n_distintos)
    return amostra, n_iguais, n_distintos


def _trecho(item: Item) -> str:
    return (item.texto or "")[:_TRUNCAMENTO_TRECHO]


def _rotular_pares(cliente_llm: ClientePrerrotulagem, pares: list[_Par]) -> list[_Par]:
    avaliados: list[_Par] = []
    for par in pares:
        prompt = prerotular_calibracao.construir_prompt(
            par.item_a.titulo, _trecho(par.item_a), par.item_b.titulo, _trecho(par.item_b)
        )
        try:
            resposta = cliente_llm.gerar_json("prerotular_calibracao", prompt, RespostaComparacaoPar)
        except FalhaJsonInvalido:
            continue
        par.rotulo_llm = resposta.mesmo_assunto
        par.rotulo_final = resposta.mesmo_assunto
        avaliados.append(par)
    return avaliados


def _ler_limiar_atual(caminho_limiares_yaml: Path) -> float:
    dados = yaml.safe_load(caminho_limiares_yaml.read_text(encoding="utf-8"))
    return float(dados["agrupamento"]["cosseno_mesmo_assunto"])


def _escolher_limiar(pares_avaliados: list[_Par], limiar_atual: float) -> float | None:
    candidatos = sorted({par.cosseno for par in pares_avaliados})
    melhor_candidato: float | None = None
    melhor_acertos = -1

    for candidato in candidatos:
        acertos = sum(1 for par in pares_avaliados if (par.cosseno >= candidato) == par.rotulo_final)
        if acertos > melhor_acertos or (
            acertos == melhor_acertos
            and melhor_candidato is not None
            and abs(candidato - limiar_atual) < abs(melhor_candidato - limiar_atual)
        ):
            melhor_acertos = acertos
            melhor_candidato = candidato

    return melhor_candidato


def _gravar_novo_limiar(caminho_limiares_yaml: Path, novo_valor: float) -> None:
    texto = caminho_limiares_yaml.read_text(encoding="utf-8")
    novo_texto, n = re.subn(r"(cosseno_mesmo_assunto:\s*)[0-9.]+", rf"\g<1>{novo_valor}", texto, count=1)
    assert n == 1
    caminho_limiares_yaml.write_text(novo_texto, encoding="utf-8")


def _escrever_adr(
    caminho_adr: Path,
    limiar_anterior: float,
    limiar_novo: float,
    amostra_banda: list[_Par],
    n_controle_iguais: int,
    n_controle_distintos: int,
    pares_avaliados: list[_Par],
    erros_llm: int,
) -> None:
    caminho_adr.parent.mkdir(parents=True, exist_ok=True)

    cossenos_banda = [par.cosseno for par in amostra_banda]
    if cossenos_banda:
        distribuicao = (
            f"mínimo {min(cossenos_banda):.3f}, máximo {max(cossenos_banda):.3f}, "
            f"média {statistics.mean(cossenos_banda):.3f}, mediana {statistics.median(cossenos_banda):.3f}"
        )
    else:
        distribuicao = "sem pares na banda de dúvida"

    if pares_avaliados:
        acertos = sum(1 for par in pares_avaliados if (par.cosseno >= limiar_novo) == par.rotulo_final)
        acuracia = f"{acertos}/{len(pares_avaliados)} ({acertos / len(pares_avaliados):.1%})"
    else:
        acuracia = "sem pares avaliados"

    conteudo = f"""\
# ADR-0001 — Limiar de agrupamento (cosseno_mesmo_assunto)

Data: {datetime.now(UTC).date().isoformat()}

Valor anterior: {limiar_anterior}
Valor novo: {limiar_novo}

## Composição da amostra

- Pares na banda de dúvida (0.70–0.92) amostrados: {len(amostra_banda)}
- Pares de controle amostrados: {n_controle_iguais} de cosseno alto (>0.92), \
{n_controle_distintos} de cosseno baixo (<0.70)
- Pares avaliados com sucesso pelo qwen3:8b: {len(pares_avaliados)}
- Erros de JSON inválido (par descartado): {erros_llm}

## Distribuição dos cossenos da banda de dúvida

{distribuicao}

## Revisão humana

Calibração sem revisão humana, por decisão do Sidarta — curadoria real vem de uso real
(aceitar/recusar sugestão de verdade, já previsto em assunto_contato.status), não de rotulagem
sintética. Se a medição real do brief 013 mostrar limiar errado, recalibra com dado de uso real.

## Acurácia do limiar escolhido sobre a amostra

{acuracia}
"""
    caminho_adr.write_text(conteudo, encoding="utf-8")


def calibrar(
    cliente_llm: ClientePrerrotulagem,
    conexao: sqlite3.Connection,
    caminho_limiares_yaml: Path,
    caminho_adr: Path,
    gerador: random.Random | None = None,
) -> ResumoCalibracao:
    itens_com_embedding = itens.listar_com_embedding(conexao)
    dentro_da_banda, controle_iguais, controle_distintos = _todos_os_pares(itens_com_embedding)

    if gerador is None:
        gerador = random.Random()
    amostra_banda = _amostrar_banda(gerador, dentro_da_banda)
    amostra_controle, n_controle_iguais, n_controle_distintos = _amostrar_controle(
        gerador, controle_iguais, controle_distintos
    )

    pares_amostrados = amostra_banda + amostra_controle
    pares_avaliados = _rotular_pares(cliente_llm, pares_amostrados)
    erros_llm = len(pares_amostrados) - len(pares_avaliados)

    limiar_atual = _ler_limiar_atual(caminho_limiares_yaml)

    candidato_escolhido = _escolher_limiar(pares_avaliados, limiar_atual)
    limiar_novo = limiar_atual if candidato_escolhido is None else round(candidato_escolhido, 2)
    if candidato_escolhido is not None:
        _gravar_novo_limiar(caminho_limiares_yaml, limiar_novo)

    _escrever_adr(
        caminho_adr,
        limiar_atual,
        limiar_novo,
        amostra_banda,
        n_controle_iguais,
        n_controle_distintos,
        pares_avaliados,
        erros_llm,
    )

    return ResumoCalibracao(
        pares_na_banda=len(amostra_banda),
        pares_controle=len(amostra_controle),
        pares_avaliados=len(pares_avaliados),
        limiar_anterior=limiar_atual,
        limiar_novo=limiar_novo,
        caminho_adr=caminho_adr,
    )
