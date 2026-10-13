from __future__ import annotations

import json
import sqlite3
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel

from agente_nw.nucleo import historico as historico_mod
from agente_nw.nucleo.consulta import ItemMenu, ResultadoConsulta
from agente_nw.nucleo.database.queries import assuntos as assuntos_q
from agente_nw.nucleo.database.queries import consulta_contato as consulta_contato_q
from agente_nw.nucleo.database.queries import fatos as fatos_q
from agente_nw.nucleo.database.queries import gancho_uso as gancho_uso_q
from agente_nw.nucleo.database.queries import itens as itens_q
from agente_nw.nucleo.database.queries import listas as listas_q
from agente_nw.nucleo.database.queries import perfil_tema as perfil_tema_q
from agente_nw.nucleo.modelos.pedido import PedidoExtraido
from agente_nw.nucleo.modelos.perfil import Perfil
from agente_nw.nucleo.modelos.redacao import (
    Gancho,
    Redacao,
    RespostaRedacao,
    validar_ganchos,
)
from agente_nw.nucleo.prompts import redigir_ganchos as prompt_mod
from agente_nw.nucleo.prompts.redigir_ganchos import AssuntoParaRedacao, EntradaRedacao

_EsquemaT = TypeVar("_EsquemaT", bound=BaseModel)

_FATOS_NO_PROMPT = 10
_CONSULTAS_NO_HISTORICO = 3
_MANCHETES_POR_ASSUNTO = 3


class ClienteRedacao(Protocol):
    def gerar_json(self, tarefa_nome: str, prompt: str, esquema: type[_EsquemaT]) -> _EsquemaT: ...


def _assunto_para_redacao(conexao: sqlite3.Connection, item: ItemMenu) -> AssuntoParaRedacao:
    assunto = assuntos_q.obter_por_id(conexao, item.assunto_id)
    manchetes: list[str] = []
    for com_dominio in itens_q.listar_por_assunto(conexao, item.assunto_id)[:_MANCHETES_POR_ASSUNTO]:
        data = (com_dominio.item.publicado_em or "")[:10]
        origem = f"{com_dominio.dominio}, {data}" if data else com_dominio.dominio
        manchetes.append(f"{origem}: {com_dominio.item.titulo}")
    return AssuntoParaRedacao(
        assunto_id=item.assunto_id,
        titulo=item.titulo,
        por_que=item.por_que,
        resumo=assunto.resumo_cartao if assunto is not None else None,
        manchetes=manchetes,
    )


def _ficha(contato: Perfil) -> list[str]:
    partes = (("cargo", contato.cargo), ("empresa", contato.empresa), ("cidade", contato.cidade))
    return [f"{rotulo}: {valor}" for rotulo, valor in partes if valor]


def _fatos(conexao: sqlite3.Connection, perfil_id: int) -> list[str]:
    linhas: list[str] = []
    for fato in fatos_q.listar_recentes(conexao, perfil_id, _FATOS_NO_PROMPT):
        data = fato.data_do_fato or fato.registrado_em[:10]
        linhas.append(f"{data[:10]} ({fato.tipo}): {fato.conteudo}")
    return linhas


def _historico(conexao: sqlite3.Connection, perfil_id: int, consulta_id: int) -> list[str]:
    anteriores = [
        c
        for c in consulta_contato_q.listar_por_perfil(conexao, perfil_id, _CONSULTAS_NO_HISTORICO + 1)
        if c.id != consulta_id
    ][:_CONSULTAS_NO_HISTORICO]
    return [historico_mod.formatar_uma(c, conexao) for c in anteriores]


def montar_entrada(
    conexao: sqlite3.Connection,
    pedido: PedidoExtraido,
    frase: str,
    resultado_consulta: ResultadoConsulta,
    contato: Perfil,
    usuario: Perfil,
    assuntos: list[ItemMenu],
) -> EntradaRedacao:
    assert contato.id is not None and usuario.id is not None
    temas_usuario = [
        (nome, nivel)
        for nome, nivel, _vetor in perfil_tema_q.listar_confirmados_com_embedding(conexao, usuario.id)
    ]
    cabecalhos = listas_q.cabecalhos_do_perfil(conexao, contato.id)
    return EntradaRedacao(
        usuario_nome=usuario.nome,
        usuario_temas=temas_usuario,
        contato_nome=contato.apelido or contato.nome,
        contato_ficha=_ficha(contato),
        vinculo=pedido.pessoa_pistas.get("vinculo"),
        tempo_sem_contato=pedido.pessoa_pistas.get("tempo_sem_contato"),
        fatos=_fatos(conexao, contato.id),
        cabecalho_rede=" · ".join(f"{rede}: {cabecalho}" for rede, cabecalho in cabecalhos) or None,
        pedido=pedido,
        frase=frase,
        historico=_historico(conexao, contato.id, resultado_consulta.consulta_id),
        assuntos=[_assunto_para_redacao(conexao, item) for item in assuntos],
    )


def _juntar_avisos(partes: list[str]) -> str | None:
    unicas = [p for p in dict.fromkeys(parte.strip() for parte in partes) if p]
    return " ".join(unicas) or None


def _validar(
    resposta: RespostaRedacao, pedido: PedidoExtraido, validos: set[int], usados: set[int]
) -> tuple[list[Gancho], list[str]]:
    return validar_ganchos(resposta.ganchos, pedido.registro, pedido.evitar, validos, pedido.meio, usados)


def redigir(
    cliente_llm: ClienteRedacao,
    conexao: sqlite3.Connection,
    pedido: PedidoExtraido,
    resultado_consulta: ResultadoConsulta,
    perfil: Perfil,
    usuario: Perfil,
    agora: str,
    frase: str = "",
    limite_tokens: int = prompt_mod.LIMITE_TOKENS_PADRAO,
) -> Redacao:
    """Uma chamada ao modelo com todos os assuntos selecionados pelo motor. Não grava nada: quem
    entrega chama `registrar`. Sem assunto disponível, devolve `ganchos=[]` com aviso e não chama o
    modelo; assuntos que o usuário já usou com esta pessoa saem antes do prompt."""
    del agora
    assert perfil.id is not None
    registro = pedido.registro
    usados = gancho_uso_q.assuntos_usados_do_perfil(conexao, perfil.id)
    disponiveis = [item for item in resultado_consulta.itens_menu if item.assunto_id not in usados]

    if not disponiveis:
        sem_assunto = (
            "Todos os assuntos selecionados já foram usados com esta pessoa."
            if resultado_consulta.itens_menu
            else resultado_consulta.aviso or "Nenhum assunto qualificado para esta pessoa agora."
        )
        return Redacao(ganchos=[], aviso=sem_assunto, registro_usado=registro)

    entrada = montar_entrada(conexao, pedido, frase, resultado_consulta, perfil, usuario, disponiveis)
    prompt = prompt_mod.construir_prompt(entrada, limite_tokens)
    validos = {item.assunto_id for item in disponiveis}
    resposta = cliente_llm.gerar_json("redigir_ganchos", prompt, RespostaRedacao)
    ganchos, motivos = _validar(resposta, pedido, validos, usados)
    if not ganchos and motivos:
        # Segunda tentativa dizendo ao modelo o que foi recusado: sem ela, um excesso de palavras na
        # mensagem deixaria a pessoa sem nenhum gancho.
        recusas = "\n".join(f"- {motivo}" for motivo in motivos)
        retorno = f"{prompt}\n\nA resposta anterior foi recusada. Refaça respeitando as regras:\n{recusas}\n"
        resposta = cliente_llm.gerar_json("redigir_ganchos", retorno, RespostaRedacao)
        ganchos, motivos = _validar(resposta, pedido, validos, usados)
    aviso = _juntar_avisos([resposta.aviso or "", *motivos])
    if not ganchos and aviso is None:
        aviso = "O modelo não devolveu nenhum gancho para estes assuntos."
    return Redacao(ganchos=ganchos, aviso=aviso, registro_usado=registro)


def registrar(conexao: sqlite3.Connection, consulta_id: int, redacao: Redacao, agora: str) -> None:
    """Grava os ganchos entregues em `gancho_uso` (status `entregue`)."""
    gancho_uso_q.inserir_entregues(
        conexao,
        consulta_id,
        [(g.assunto_id, g.model_dump_json()) for g in redacao.ganchos],
        agora,
    )
    conexao.commit()


def ganchos_da_consulta(conexao: sqlite3.Connection, consulta_id: int) -> list[tuple[Gancho, str]]:
    """[(gancho, status)] gravados para a consulta, na ordem da entrega."""
    resultado: list[tuple[Gancho, str]] = []
    for _assunto_id, status, gancho_json in gancho_uso_q.listar_por_consulta(conexao, consulta_id):
        dados: Any = json.loads(gancho_json)
        resultado.append((Gancho.model_validate(dados), status))
    return resultado
