from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import UTC, datetime

from agente_nw.nucleo import sensivel
from agente_nw.nucleo.database.queries import descarte_sensivel, fatos, fila_extracao
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
    descartes_por_categoria: dict[str, int] = field(default_factory=dict)
    erros: int = 0


def _registrar_descarte(
    conexao: sqlite3.Connection,
    resumo: ResumoProcessamento,
    item: FilaExtracao,
    categoria: str,
    agora: str,
) -> None:
    descarte_sensivel.registrar(conexao, item.perfil_id, item.origem, categoria, agora)
    resumo.descartes_por_categoria[categoria] = resumo.descartes_por_categoria.get(categoria, 0) + 1


def _campos_limpos(
    resposta: RespostaExtracaoTexto,
    conexao: sqlite3.Connection,
    resumo: ResumoProcessamento,
    item: FilaExtracao,
    agora: str,
) -> dict[str, object]:
    limpos: dict[str, object] = {}
    for campo, valor in resposta.campos.model_dump(exclude_none=True).items():
        texto_verificado = ", ".join(valor) if isinstance(valor, list) else str(valor)
        categoria = sensivel.verificar(texto_verificado)
        if categoria is not None:
            _registrar_descarte(conexao, resumo, item, categoria, agora)
            continue
        limpos[campo] = valor
    return limpos


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
    contrato `extrair_de_texto`, filtra cada peça pelo filtro determinístico
    de categorias sensíveis, grava o que passar e descarta (registrando) o
    que não passar. Marca cada item como processado ou com erro; um erro em
    um item não interrompe o lote.
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

        campos_limpos = _campos_limpos(resposta, conexao, resumo, item, agora)
        if campos_limpos:
            queries_perfis.atualizar_campos_guiados(conexao, item.perfil_id, campos_limpos, agora)
            resumo.campos_gravados += len(campos_limpos)

        for tag in resposta.tags_sugeridas:
            categoria = sensivel.verificar(tag.tag) or sensivel.verificar(tag.trecho)
            if categoria is not None:
                _registrar_descarte(conexao, resumo, item, categoria, agora)
                continue
            _gravar_tag(conexao, tag, item, agora)
            resumo.tags_gravadas += 1

        for fato_extraido in resposta.fatos_datados:
            categoria = sensivel.verificar(fato_extraido.conteudo)
            if categoria is not None:
                _registrar_descarte(conexao, resumo, item, categoria, agora)
                continue
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
