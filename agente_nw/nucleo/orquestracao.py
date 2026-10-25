"""A sequência "pedido → ganchos", escrita uma vez só (brief 056).

O terminal (`cli.pedir_cmd`) e o console (`nucleo/fluxo.py`) entendem o pedido do mesmo jeito
(`nucleo/pedido.py: processar`) e, daí em diante, seguem os mesmos passos: resolver o contato, resolver a
rede social de cada pessoa, preparar a consulta e redigir os ganchos. Este módulo guarda a ordem desses
passos e a decisão de qual resultado (contato ambíguo, localização clara, ambígua ou sem ninguém) dispara o
quê. Cada canal continua dono de como pergunta e de como mostra o progresso: ele entra aqui como um `Canal`.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Protocol

import httpx

from agente_nw.nucleo import pedido as pedido_mod
from agente_nw.nucleo import redacao as redacao_mod
from agente_nw.nucleo.consulta import ResultadoConsulta
from agente_nw.nucleo.llm import FalhaJsonInvalido
from agente_nw.nucleo.modelos.configuracao import Limiares
from agente_nw.nucleo.modelos.localizacao import Localizacao
from agente_nw.nucleo.modelos.pedido import PedidoExtraido, ResultadoPedido
from agente_nw.nucleo.modelos.perfil import Perfil
from agente_nw.nucleo.modelos.redacao import Redacao


class Desfecho(Enum):
    SEGUIR = "seguir"  # nada a perguntar: o pedido continua
    ESPERAR = "esperar"  # o canal ficou com perguntas e o pedido só continua com a resposta
    PARAR = "parar"  # o pedido termina aqui, sem redação


class Encaminhamento(Enum):
    """O que fazer com a localização de uma pessoa numa rede."""

    GRAVAR_ESCOLHIDO = "gravar_escolhido"  # claro, e o usuário pediu para não perguntar
    CONFIRMAR_ESCOLHIDO = "confirmar_escolhido"  # claro: "É esta pessoa?"; a recusa abre os candidatos
    CONFIRMAR_UNICA = "confirmar_unica"  # uma só candidata (ambígua ou vinda da busca geral)
    ESCOLHER = "escolher"  # várias candidatas
    PEDIR_LINK = "pedir_link"  # ninguém apareceu: o usuário cola o perfil, declara "sem perfil" ou pula
    PULAR = "pular"  # sem perguntar e sem pessoa clara: segue sem rede social


class FalhaNaRedacao(Exception):
    """O modelo não devolveu um JSON válido ao redigir os ganchos."""


class Canal(Protocol):
    """Como cada canal (terminal, console) pergunta e mostra o andamento."""

    def avisar(self, texto: str) -> None: ...

    def pedido_entendido(self, resultado: ResultadoPedido) -> None: ...

    def localizacoes(self, resultado: ResultadoPedido) -> Desfecho: ...

    def contato_divergente(self, resultado: ResultadoPedido) -> Desfecho: ...

    def contato_ambiguo(self, resultado: ResultadoPedido) -> Desfecho: ...

    def sem_pessoa(self, resultado: ResultadoPedido) -> Desfecho: ...

    def consulta_pronta(self, consulta: ResultadoConsulta) -> bool: ...

    def redigindo(self) -> None: ...


@dataclass
class Entrega:
    consulta: ResultadoConsulta
    redacao: Redacao


def encaminhar_localizacao(localizacao: Localizacao, sem_perguntar: bool) -> Encaminhamento:
    """A decisão claro / ambíguo / nenhum de uma rede, para quem pergunta no terminal."""
    if localizacao.status == "claro" and localizacao.escolhido is not None:
        return Encaminhamento.GRAVAR_ESCOLHIDO if sem_perguntar else Encaminhamento.CONFIRMAR_ESCOLHIDO
    if sem_perguntar:
        return Encaminhamento.PULAR
    if len(localizacao.opcoes) == 1:
        return Encaminhamento.CONFIRMAR_UNICA
    if localizacao.status == "nenhum" and not localizacao.opcoes:
        return Encaminhamento.PEDIR_LINK
    return Encaminhamento.ESCOLHER


def encaminhar_pedido(resultado: ResultadoPedido, canal: Canal, seguir_para_redacao: bool = True) -> Desfecho:
    """Depois de entender o pedido e resolver o contato: o que perguntar e se o pedido segue.

    A ordem é a mesma nos dois canais: mostrar o pedido, perguntar as redes pendentes, conferir contato
    divergente, contato ambíguo e pedido sem pessoa. Com `seguir_para_redacao=False` o pedido termina
    depois das perguntas das redes."""
    canal.pedido_entendido(resultado)
    perfil = resultado.perfil
    if perfil is not None and perfil.id is not None and resultado.localizacoes:
        desfecho = canal.localizacoes(resultado)
        if desfecho is Desfecho.ESPERAR:
            return desfecho
    if not seguir_para_redacao:
        return Desfecho.PARAR
    if resultado.contato_divergente:
        desfecho = canal.contato_divergente(resultado)
        if desfecho is not Desfecho.SEGUIR:
            return desfecho
    if resultado.contato_ambiguo:
        desfecho = canal.contato_ambiguo(resultado)
        if desfecho is not Desfecho.SEGUIR:
            return desfecho
    if perfil is None or perfil.id is None:
        return canal.sem_pessoa(resultado)
    return Desfecho.SEGUIR


def preparar_e_redigir(
    canal: Canal,
    *,
    preparar: Callable[..., ResultadoConsulta],
    conexao: sqlite3.Connection,
    cliente_llm: Any,
    cliente_http: httpx.Client,
    perfil: Perfil,
    extraido: PedidoExtraido,
    texto: str,
    limiares: Limiares,
    caminho_fontes: Path,
    caminho_sentinela: Path,
    abrir_pagina: Callable[[Path], Any],
    pasta_navegador: Path,
    limite_tokens: int,
    rodar_coleta: bool,
    ler_redes_sociais: bool,
) -> Entrega | None:
    """Prepara a consulta e redige os ganchos. Devolve None quando o canal encerra depois da consulta
    (o terminal com `--menu`). `preparar` entra como argumento para o canal poder trocá-lo nos testes."""
    consulta = preparar(
        conexao=conexao,
        cliente_llm=cliente_llm,
        cliente_http=cliente_http,
        perfil_id=perfil.id or 0,
        contexto=pedido_mod.para_contexto(extraido, texto),
        limiares=limiares,
        caminho_fontes=caminho_fontes,
        caminho_sentinela=caminho_sentinela,
        abrir_pagina=abrir_pagina,
        pasta_navegador=pasta_navegador,
        agora=datetime.now(UTC).isoformat(),
        rodar_coleta=rodar_coleta,
        ler_redes_sociais=ler_redes_sociais,
        avisar=canal.avisar,
    )
    if not canal.consulta_pronta(consulta):
        return None

    canal.redigindo()
    agora_redacao = datetime.now(UTC).isoformat()
    try:
        redacao = redacao_mod.redigir(
            cliente_llm,
            conexao,
            extraido,
            consulta,
            perfil,
            pedido_mod.garantir_usuario(conexao, agora_redacao),
            agora_redacao,
            frase=texto,
            limite_tokens=limite_tokens,
            meses_fato_antigo=limiares.redacao.meses_fato_antigo,
        )
    except FalhaJsonInvalido as erro:
        raise FalhaNaRedacao(str(erro)) from erro
    redacao_mod.registrar(conexao, consulta.consulta_id, redacao, agora_redacao)
    return Entrega(consulta=consulta, redacao=redacao)
