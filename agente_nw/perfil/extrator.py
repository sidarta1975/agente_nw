from __future__ import annotations

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol, TypeVar

from pydantic import BaseModel

from agente_nw.nucleo import texto_integral
from agente_nw.nucleo.database.queries import fatos, fila_extracao, fila_revisao
from agente_nw.nucleo.database.queries import perfil_tema as queries_perfil_tema
from agente_nw.nucleo.database.queries import perfis as queries_perfis
from agente_nw.nucleo.database.queries import temas as queries_temas
from agente_nw.nucleo.llm import FalhaJsonInvalido, JanelaEstourada
from agente_nw.nucleo.modelos.extracao import CamposExtraidos, RespostaExtracaoTexto, TagSugerida
from agente_nw.nucleo.modelos.fato import Fato
from agente_nw.nucleo.modelos.fila import FilaExtracao
from agente_nw.nucleo.modelos.proveniencia import Proveniencia
from agente_nw.nucleo.prompts.extrair_de_texto import VERSAO, construir_prompt
from agente_nw.nucleo.texto_integral import Parte

_EsquemaT = TypeVar("_EsquemaT", bound=BaseModel)


class ClienteExtracaoPerfil(Protocol):
    """Só o que `processar_fila` usa do cliente de LLM — `Protocol` local, como nos outros módulos
    do produto, para o provedor de geração ser indiferente aqui (briefs 075/076)."""

    def gerar_json(
        self,
        tarefa_nome: str,
        prompt: str,
        esquema: type[_EsquemaT],
        imagens: list[str] | None = None,
        versao_prompt: str | None = None,
    ) -> _EsquemaT: ...

    def proveniencia(self, tarefa_nome: str, versao_prompt: str | None = None) -> Proveniencia: ...

    def num_ctx(self, tarefa_nome: str) -> int: ...


_TAREFA = "extrair_de_texto"
_MOTIVO_REFEITO = "estouro de janela refeito em partes menores (brief 088)"


class DivergenciaEntrePartes(FalhaJsonInvalido):
    """Item lido em partes cujas partes dão valores diferentes a um campo único (brief 088, 2.3): não se
    decide por voto. O item vai para a `fila_revisao` e fica com erro em `fila_extracao`, com o mesmo
    `(fila_revisao id=N)` de qualquer falha, para o reenvio do brief 087 achar a linha."""

    def __init__(self, tarefa: str, fila_revisao_id: int, erro: str) -> None:
        super().__init__(tarefa, fila_revisao_id, erro)
        RuntimeError.__init__(
            self, f"tarefa '{tarefa}' com partes divergentes (fila_revisao id={fila_revisao_id}): {erro}"
        )


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


def _consolidar(
    respostas: list[RespostaExtracaoTexto],
) -> RespostaExtracaoTexto | list[texto_integral.Divergencia]:
    """Regra de consolidação de `extrair_de_texto` lido em partes (brief 088, 2.3). Tags e fatos datados
    são listas de fatos: união ordenada, sem repetição exata (`texto_integral.consolidar_fatos`); `linguas`
    também. Os outros campos guiados são únicos: o valor igual em todas as partes que o deram é aceito;
    valores diferentes **não são decididos por voto** e devolvem as divergências, para a revisão humana."""
    unicos, divergencias = texto_integral.consolidar_unicos(
        [r.campos.model_dump(exclude={"linguas"}, exclude_none=True) for r in respostas]
    )
    if divergencias:
        return divergencias
    linguas = texto_integral.consolidar_fatos([r.campos.linguas for r in respostas])
    tags = texto_integral.consolidar_fatos([r.tags_sugeridas for r in respostas])
    fatos_datados = texto_integral.consolidar_fatos([r.fatos_datados for r in respostas])
    return RespostaExtracaoTexto(
        campos=CamposExtraidos.model_validate({**unicos, "linguas": [lingua.valor for lingua in linguas]}),
        tags_sugeridas=[tag.valor for tag in tags],
        fatos_datados=[fato.valor for fato in fatos_datados],
    )


def _divergencia_para_revisao(
    conexao: sqlite3.Connection, item: FilaExtracao, divergencias: list[texto_integral.Divergencia]
) -> DivergenciaEntrePartes:
    """Aviso na `fila_revisao`: o erro diz só os campos e as partes (a listagem o mostra); os valores e o
    texto inteiro ficam na `entrada`, que só `revisao ver --inteiro` abre."""
    aviso = "divergência entre partes, sem voto: " + "; ".join(d.descrever() for d in divergencias)
    valores = "\n".join(d.descrever_com_valores() for d in divergencias)
    entrada = f"Valores divergentes entre as partes:\n{valores}\n\nTexto do item:\n{item.texto}"
    fila_id = fila_revisao.inserir(conexao, _TAREFA, entrada, aviso, datetime.now(UTC).isoformat())
    return DivergenciaEntrePartes(_TAREFA, fila_id, aviso)


def processar_item(
    cliente_llm: ClienteExtracaoPerfil,
    conexao: sqlite3.Connection,
    item: FilaExtracao,
    resumo: ResumoProcessamento,
) -> FalhaJsonInvalido | None:
    """Extrai e grava um item de `fila_extracao`. Devolve `None` quando gravou, ou a falha que o
    deixou com erro (o item fica marcado e o lote segue).

    O texto vai inteiro: numa chamada, se cabe no `num_ctx` da tarefa (o prompt é o de antes do brief
    088), ou em partes que cobrem o texto todo (`nucleo/texto_integral.py`), consolidadas por
    `_consolidar`. Parte sem resposta válida invalida o item inteiro, que vai para a fila de revisão;
    nada dele é gravado. O número de partes fica em `fila_extracao.partes_lidas`."""
    agora = datetime.now(UTC).isoformat()
    orcamento = texto_integral.orcamento_do_texto(cliente_llm.num_ctx(_TAREFA), construir_prompt(""))

    def processar(partes: list[Parte]) -> list[RespostaExtracaoTexto]:
        return [
            cliente_llm.gerar_json(
                _TAREFA,
                construir_prompt(texto_integral.texto_para_o_prompt(parte)),
                RespostaExtracaoTexto,
                versao_prompt=VERSAO,
            )
            for parte in partes
        ]

    def refazer(erro: BaseException) -> None:
        if isinstance(erro, FalhaJsonInvalido):
            fila_revisao.descartar(conexao, erro.fila_revisao_id, _MOTIVO_REFEITO, agora)

    try:
        respostas, partes = texto_integral.processar_dividindo(
            item.texto, orcamento, processar, JanelaEstourada, refazer
        )
        consolidada = respostas[0] if len(respostas) == 1 else _consolidar(respostas)
        if isinstance(consolidada, list):
            raise _divergencia_para_revisao(conexao, item, consolidada)
    except FalhaJsonInvalido as erro:
        assert item.id is not None
        fila_extracao.marcar_erro(conexao, item.id, str(erro))
        conexao.commit()
        resumo.erros += 1
        return erro
    resposta = consolidada

    proveniencia = cliente_llm.proveniencia("extrair_de_texto", VERSAO)
    campos = resposta.campos.model_dump(exclude_none=True)
    if campos:
        queries_perfis.atualizar_campos_guiados(conexao, item.perfil_id, campos, agora)
        resumo.campos_gravados += len(campos)

    for tag in resposta.tags_sugeridas:
        _gravar_tag(conexao, tag, item, agora)
        resumo.tags_gravadas += 1

    for fato_extraido in resposta.fatos_datados:
        data = fato_extraido.data
        if item.origem.startswith("whatsapp:"):
            # Bloco é um mês inteiro de mensagens; a data do mês (não o palpite do modelo sobre o
            # dia) é o que faz a marca [antigo] (brief 046) valer sozinha (brief 061).
            data = f"{item.origem.removeprefix('whatsapp:')}-01"
        fatos.inserir(
            conexao,
            Fato(
                perfil_id=item.perfil_id,
                data_do_fato=data,
                tipo=fato_extraido.tipo,
                conteudo=fato_extraido.conteudo,
                fonte=fato_extraido.fonte,
                registrado_em=agora,
            ),
            proveniencia,
        )
        resumo.fatos_gravados += 1

    assert item.id is not None
    fila_extracao.marcar_processado(conexao, item.id, proveniencia)
    fila_extracao.registrar_partes(conexao, item.id, len(partes))
    conexao.commit()
    resumo.itens_processados += 1
    return None


def processar_fila(
    cliente_llm: ClienteExtracaoPerfil, conexao: sqlite3.Connection, limite: int = 20
) -> ResumoProcessamento:
    """Lê itens pendentes de `fila_extracao`, extrai campos/tags/fatos via o
    contrato `extrair_de_texto` e grava tudo. Marca cada item como processado
    ou com erro; um erro em um item não interrompe o lote.
    """
    resumo = ResumoProcessamento()
    for item in fila_extracao.listar_pendentes(conexao, limite):
        processar_item(cliente_llm, conexao, item, resumo)
    return resumo


def reprocessador_de_item(
    cliente_llm: ClienteExtracaoPerfil, conexao: sqlite3.Connection
) -> Callable[[int], int | None]:
    """Reprocessa uma linha de `fila_extracao` (reenvio da fila de revisão, brief 087): devolve
    `None` se gravou, ou o id que a nova falha abriu em `fila_revisao`."""

    def reprocessar(extracao_id: int) -> int | None:
        item = fila_extracao.obter(conexao, extracao_id)
        assert item is not None
        falha = processar_item(cliente_llm, conexao, item, ResumoProcessamento())
        return None if falha is None else falha.fila_revisao_id

    return reprocessar
