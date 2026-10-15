from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime

from agente_nw.nucleo.database.queries import fatos, fila_extracao
from agente_nw.nucleo.database.queries import perfil_tema as queries_perfil_tema
from agente_nw.nucleo.database.queries import perfis as queries_perfis
from agente_nw.nucleo.database.queries import temas as queries_temas
from agente_nw.nucleo.llm import ClienteOllama, FalhaJsonInvalido
from agente_nw.nucleo.modelos.extracao import RespostaExtracaoTexto, TagSugerida
from agente_nw.nucleo.modelos.fato import Fato
from agente_nw.nucleo.modelos.fila import FilaExtracao
from agente_nw.nucleo.prompts.extrair_de_texto import construir_prompt


@dataclass
class ResumoProcessamento:
    itens_processados: int = 0
    tags_gravadas: int = 0
    campos_gravados: int = 0
    fatos_gravados: int = 0
    erros: int = 0


def _gravar_tag(
    conexao: sqlite3.Connection,
    tag: TagSugerida,
    item: FilaExtracao,
    agora: str,
) -> None:
    # Tema novo herda o trecho como descrição (só na criação); tema já
    # existente não tem a descrição tocada — daí checar obter_por_nome antes
    # de decidir se chama obter_ou_criar (que sobrescreveria a descrição de
    # um tema pré-existente, comportamento da própria função, não alterado).
    tema_existente = queries_temas.obter_por_nome(conexao, tag.tag)
    tema = tema_existente or queries_temas.obter_ou_criar(conexao, tag.tag, tag.trecho, [], agora)
    assert tema.id is not None

    queries_perfil_tema.vincular(conexao, item.perfil_id, tema.id, tag.peso, "sugerida", None, False, agora)


def processar_fila(
    cliente_llm: ClienteOllama, conexao: sqlite3.Connection, limite: int = 20
) -> ResumoProcessamento:
    """Lê itens pendentes de `fila_extracao`, extrai campos/tags/fatos via o
    contrato `extrair_de_texto` e grava tudo. Marca cada item como processado
    ou com erro; um erro em um item não interrompe o lote.
    """
    resumo = ResumoProcessamento()

    for item in fila_extracao.listar_pendentes(conexao, limite):
        agora = datetime.now(UTC).isoformat()

        try:
            resposta = cliente_llm.gerar_json(
                "extrair_de_texto", construir_prompt(item.texto), RespostaExtracaoTexto
            )
        except FalhaJsonInvalido as erro:
            assert item.id is not None
            fila_extracao.marcar_erro(conexao, item.id, str(erro))
            conexao.commit()
            resumo.erros += 1
            continue

        campos = resposta.campos.model_dump(exclude_none=True)
        if campos:
            queries_perfis.atualizar_campos_guiados(conexao, item.perfil_id, campos, agora)
            resumo.campos_gravados += len(campos)

        for tag in resposta.tags_sugeridas:
            _gravar_tag(conexao, tag, item, agora)
            resumo.tags_gravadas += 1

        for fato_extraido in resposta.fatos_datados:
            fatos.inserir(
                conexao,
                Fato(
                    perfil_id=item.perfil_id,
                    data_do_fato=fato_extraido.data,
                    tipo=fato_extraido.tipo,
                    conteudo=fato_extraido.conteudo,
                    fonte=fato_extraido.fonte,
                    registrado_em=agora,
                ),
            )
            resumo.fatos_gravados += 1

        assert item.id is not None
        fila_extracao.marcar_processado(conexao, item.id)
        conexao.commit()
        resumo.itens_processados += 1

    return resumo
