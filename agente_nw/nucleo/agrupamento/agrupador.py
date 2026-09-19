from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Protocol

from agente_nw.nucleo.agrupamento import divisao
from agente_nw.nucleo.database.queries import assuntos, fila_revisao, itens
from agente_nw.nucleo.database.queries.itens import ItemComDominio
from agente_nw.nucleo.modelos.assunto import Assunto, StatusAssunto
from agente_nw.nucleo.modelos.configuracao import Limiares
from agente_nw.nucleo.vetores import centroide, cosseno


class ClienteEmbeddagem(Protocol):
    def embeddar(self, textos: list[str]) -> list[list[float]]: ...


@dataclass
class ResumoAgrupamento:
    itens_embeddados: int = 0
    assuntos_criados: int = 0
    itens_vinculados: int = 0
    republicacoes: int = 0
    assuntos_reabertos: int = 0
    assuntos_encerrados: int = 0
    assuntos_divididos: int = 0


def _id(item_com_dominio: ItemComDominio) -> int:
    item_id = item_com_dominio.item.id
    assert item_id is not None
    return item_id


def _subtrai_dias(data_iso: str, dias: int) -> str:
    momento = datetime.fromisoformat(data_iso)
    return (momento - timedelta(days=dias)).isoformat()


def _representantes_independentes(
    itens_com_dominio: list[tuple[str, list[float]]], limiar_divergencia: float
) -> list[tuple[str, list[float]]]:
    representantes: list[tuple[str, list[float]]] = []
    for dominio, vetor in itens_com_dominio:
        dominios_ja_vistos = {d for d, _ in representantes}
        if dominio in dominios_ja_vistos:
            continue
        if all(cosseno(vetor, v_rep) < limiar_divergencia for _, v_rep in representantes):
            representantes.append((dominio, vetor))
    return representantes


def _embeddings_por_item(
    conexao: sqlite3.Connection, itens_com_dominio: list[ItemComDominio]
) -> dict[int, list[float]]:
    resultado: dict[int, list[float]] = {}
    for item_com_dominio in itens_com_dominio:
        item_id = _id(item_com_dominio)
        embedding = itens.obter_embedding(conexao, item_id)
        assert embedding is not None
        resultado[item_id] = embedding
    return resultado


def agrupar(
    cliente_llm: ClienteEmbeddagem,
    conexao: sqlite3.Connection,
    limiares: Limiares,
    caminho_sentinela: Path,
    data_referencia: str,
    limite: int = 100,
) -> ResumoAgrupamento:
    resumo = ResumoAgrupamento()
    agora = datetime.now(UTC).isoformat()
    limiar_divergencia = 1 - limiares.agrupamento.divergencia_minima_fonte_independente

    for item in itens.listar_sem_assunto(conexao, limite):
        if caminho_sentinela.exists():
            break
        assert item.id is not None

        texto_para_embeddar = item.titulo if item.texto is None else f"{item.titulo}\n\n{item.texto[:2000]}"
        vetor = cliente_llm.embeddar([texto_para_embeddar])[0]
        itens.gravar_embedding(conexao, item.id, vetor)
        resumo.itens_embeddados += 1

        data_item = item.publicado_em or item.coletado_em
        desde_janela = _subtrai_dias(data_item, limiares.agrupamento.janela_dias)
        desde_reabertura = _subtrai_dias(data_item, limiares.coleta.retencao_texto_dias)
        candidatos = assuntos.listar_candidatos(conexao, desde_janela, desde_reabertura)

        melhor_candidato: Assunto | None = None
        melhor_cosseno_centroide = -1.0
        for candidato in candidatos:
            assert candidato.id is not None
            centro = assuntos.obter_centroide(conexao, candidato.id)
            assert centro is not None
            c = cosseno(vetor, centro)
            if c > melhor_cosseno_centroide:
                melhor_cosseno_centroide = c
                melhor_candidato = candidato

        if melhor_candidato is None or melhor_cosseno_centroide < limiares.agrupamento.cosseno_mesmo_assunto:
            novo_assunto = Assunto(
                primeiro_visto=data_item,
                ultimo_visto=data_item,
                n_itens=1,
                n_fontes_independentes=1,
                status="novo",
                temas=[],
            )
            assunto_id = assuntos.inserir(conexao, novo_assunto)
            assuntos.gravar_centroide(conexao, assunto_id, vetor)
            itens.vincular_assunto(conexao, item.id, assunto_id)
            resumo.assuntos_criados += 1
            resumo.itens_vinculados += 1
            conexao.commit()
            continue

        assert melhor_candidato.id is not None
        itens_do_assunto = itens.listar_por_assunto(conexao, melhor_candidato.id)
        melhor_cosseno_item = max(
            cosseno(vetor, embedding)
            for embedding in _embeddings_por_item(conexao, itens_do_assunto).values()
        )

        if melhor_cosseno_item >= limiares.agrupamento.cosseno_republicacao:
            itens.vincular_assunto(conexao, item.id, melhor_candidato.id)
            novo_ultimo_visto = max(data_item, melhor_candidato.ultimo_visto)
            assuntos.atualizar_apos_item(
                conexao,
                melhor_candidato.id,
                ultimo_visto=novo_ultimo_visto,
                n_itens=melhor_candidato.n_itens,
                n_fontes_independentes=melhor_candidato.n_fontes_independentes,
                status=melhor_candidato.status,
                agora=agora,
            )
            resumo.republicacoes += 1
            resumo.itens_vinculados += 1
            conexao.commit()
            continue

        itens.vincular_assunto(conexao, item.id, melhor_candidato.id)
        itens_atualizados = itens.listar_por_assunto(conexao, melhor_candidato.id)
        embeddings_atualizados = _embeddings_por_item(conexao, itens_atualizados)
        vetores_atualizados = [embeddings_atualizados[_id(ic)] for ic in itens_atualizados]
        centroide_novo = centroide(vetores_atualizados)
        n_itens_novo = melhor_candidato.n_itens + 1
        representantes = _representantes_independentes(
            [(ic.dominio, embeddings_atualizados[_id(ic)]) for ic in itens_atualizados],
            limiar_divergencia,
        )
        n_fontes_independentes_novo = len(representantes)

        status_novo: StatusAssunto = melhor_candidato.status
        reaberto = False
        if melhor_candidato.status == "encerrado":
            status_novo = "em_curso"
            reaberto = True
        elif melhor_candidato.status == "novo" and n_itens_novo >= 2:
            status_novo = "em_curso"

        assuntos.gravar_centroide(conexao, melhor_candidato.id, centroide_novo)
        assuntos.atualizar_apos_item(
            conexao,
            melhor_candidato.id,
            ultimo_visto=data_item,
            n_itens=n_itens_novo,
            n_fontes_independentes=n_fontes_independentes_novo,
            status=status_novo,
            agora=agora,
        )
        resumo.itens_vinculados += 1
        if reaberto:
            resumo.assuntos_reabertos += 1
            print(f"assunto {melhor_candidato.id} reaberto — volta ao noticiário")
        conexao.commit()

    antes_de = _subtrai_dias(data_referencia, limiares.agrupamento.janela_dias)
    resumo.assuntos_encerrados = assuntos.fechar_inativos(conexao, antes_de, agora)
    conexao.commit()

    for assunto in assuntos.listar_maiores_que(conexao, limiares.agrupamento.itens_para_dividir):
        assert assunto.id is not None
        itens_do_assunto = itens.listar_por_assunto(conexao, assunto.id)
        embeddings_por_id = _embeddings_por_item(conexao, itens_do_assunto)
        centro_atual = assuntos.obter_centroide(conexao, assunto.id)
        assert centro_atual is not None
        media_similaridade = sum(cosseno(v, centro_atual) for v in embeddings_por_id.values()) / len(
            embeddings_por_id
        )
        if media_similaridade >= limiares.agrupamento.cosseno_mesmo_assunto:
            continue

        resultado = divisao.dividir(embeddings_por_id)
        if resultado is None:
            fila_revisao.inserir(
                conexao,
                tarefa="dividir_assunto",
                entrada=str(assunto.id),
                erro="dispersão alta mas sem separação em duas partes",
                agora=agora,
            )
            conexao.commit()
            continue

        itens_por_id = {_id(ic): ic for ic in itens_do_assunto}

        grupo_a, grupo_b = resultado
        estatisticas_a = _estatisticas_particao(grupo_a, itens_por_id, embeddings_por_id, limiar_divergencia)
        estatisticas_b = _estatisticas_particao(grupo_b, itens_por_id, embeddings_por_id, limiar_divergencia)

        assuntos.gravar_centroide(conexao, assunto.id, estatisticas_a.centroide)
        assuntos.atualizar_apos_item(
            conexao,
            assunto.id,
            ultimo_visto=estatisticas_a.ultimo_visto,
            n_itens=estatisticas_a.n_itens,
            n_fontes_independentes=estatisticas_a.n_fontes_independentes,
            status=estatisticas_a.status,
            agora=agora,
            primeiro_visto=estatisticas_a.primeiro_visto,
        )

        novo_assunto = Assunto(
            primeiro_visto=estatisticas_b.primeiro_visto,
            ultimo_visto=estatisticas_b.ultimo_visto,
            n_itens=estatisticas_b.n_itens,
            n_fontes_independentes=estatisticas_b.n_fontes_independentes,
            status=estatisticas_b.status,
            temas=[],
        )
        novo_assunto_id = assuntos.inserir(conexao, novo_assunto)
        assuntos.gravar_centroide(conexao, novo_assunto_id, estatisticas_b.centroide)
        for item_id in grupo_b:
            itens.vincular_assunto(conexao, item_id, novo_assunto_id)

        resumo.assuntos_divididos += 1
        conexao.commit()

    return resumo


@dataclass
class _EstatisticasParticao:
    primeiro_visto: str
    ultimo_visto: str
    n_itens: int
    n_fontes_independentes: int
    status: StatusAssunto
    centroide: list[float]


def _estatisticas_particao(
    ids_grupo: list[int],
    itens_por_id: dict[int, ItemComDominio],
    embeddings_por_id: dict[int, list[float]],
    limiar_divergencia: float,
) -> _EstatisticasParticao:
    itens_do_grupo = [itens_por_id[item_id] for item_id in ids_grupo]
    vetores_do_grupo = [embeddings_por_id[item_id] for item_id in ids_grupo]
    datas = [ic.item.publicado_em or ic.item.coletado_em for ic in itens_do_grupo]
    n_itens_grupo = len(itens_do_grupo)
    representantes = _representantes_independentes(
        [(ic.dominio, embeddings_por_id[_id(ic)]) for ic in itens_do_grupo],
        limiar_divergencia,
    )
    return _EstatisticasParticao(
        primeiro_visto=min(datas),
        ultimo_visto=max(datas),
        n_itens=n_itens_grupo,
        n_fontes_independentes=len(representantes),
        status="em_curso" if n_itens_grupo >= 2 else "novo",
        centroide=centroide(vetores_do_grupo),
    )
