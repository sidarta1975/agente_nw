from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from agente_nw.coleta.capturas import leitor as leitor_capturas
from agente_nw.coleta.capturas.navegador import Pagina
from agente_nw.coleta.rss import leitor as leitor_rss
from agente_nw.nucleo import historico as historico_mod
from agente_nw.nucleo.agrupamento import agrupador
from agente_nw.nucleo.database.queries import assunto_contato as assunto_contato_q
from agente_nw.nucleo.database.queries import assuntos as assuntos_q
from agente_nw.nucleo.database.queries import consulta_contato as consulta_contato_q
from agente_nw.nucleo.modelos.configuracao import Limiares
from agente_nw.nucleo.modelos.contexto_consulta import ContextoConsulta
from agente_nw.nucleo.relevancia import cruzamento, qualificador
from agente_nw.perfil import extrator as extrator_perfil


@dataclass
class ItemMenu:
    ac_id: int
    assunto_id: int
    tipo: str
    titulo: str
    por_que: str | None
    score: float


@dataclass
class ResumoRedeSocial:
    redes_lidas: int = 0
    redes_sem_sessao: int = 0
    blocos_capturados: int = 0
    fatos_gravados: int = 0
    motivos_sem_sessao: list[str] = field(default_factory=list)


@dataclass
class ResultadoConsulta:
    perfil_id: int
    consulta_id: int
    itens_menu: list[ItemMenu]
    resumo_rede_social: ResumoRedeSocial
    historico_texto: str
    aviso: str | None = None


def _resumo_rede_para_texto(resumo: ResumoRedeSocial) -> str | None:
    if resumo.redes_lidas == 0 and resumo.redes_sem_sessao == 0:
        return None
    partes = [f"redes lidas: {resumo.redes_lidas}"]
    if resumo.blocos_capturados:
        partes.append(f"blocos capturados: {resumo.blocos_capturados}")
    if resumo.fatos_gravados:
        partes.append(f"fatos gravados: {resumo.fatos_gravados}")
    if resumo.redes_sem_sessao:
        partes.append(f"sem sessão: {resumo.redes_sem_sessao}")
    for motivo in resumo.motivos_sem_sessao:
        partes.append(motivo)
    return " · ".join(partes)


def preparar(
    conexao: sqlite3.Connection,
    cliente_llm: Any,
    cliente_http: httpx.Client,
    perfil_id: int,
    contexto: ContextoConsulta,
    limiares: Limiares,
    caminho_fontes: Path,
    caminho_sentinela: Path,
    abrir_pagina: Callable[[Path], Pagina],
    pasta_navegador: Path,
    agora: str,
    rodar_coleta: bool = True,
    max_esperas_login_rede_social: int = 36,
    espera_login_s_rede_social: float = 5.0,
    max_rolagens_rede_social: int = 5,
) -> ResultadoConsulta:
    """Orquestra a consulta sob demanda sobre um contato.

    Ordem: coleta de notícia (se `rodar_coleta`) → extração da fila → agrupamento
    → qualificação → leitura de rede social → cruzamento por contato → montagem
    do menu → gravação em `consulta_contato`. Contato sem rede social cadastrada
    ou sem histórico anterior não interrompe o fluxo; o resultado devolve um
    `aviso` quando não há assunto qualificado.

    O motor de cruzamento e a pontuação são reaproveitados sem alteração.
    O `contexto` inteiro é serializado em `contexto_json`; hoje não é lido pelo
    motor — briefs futuros podem passar a usá-lo via `historico.formatar`.
    """
    if rodar_coleta and caminho_fontes.exists():
        leitor_rss.coletar(conexao, cliente_http, caminho_fontes, limiares.coleta, caminho_sentinela)

    extrator_perfil.processar_fila(cliente_llm, conexao)
    agrupador.agrupar(cliente_llm, conexao, limiares, caminho_sentinela, agora)
    qualificador.qualificar_pendentes(cliente_llm, conexao, limiares.qualificacao.teto_por_dia)

    resumo_leitor = leitor_capturas.ler_redes_sociais_do_contato(
        cliente_llm,
        conexao,
        perfil_id,
        abrir_pagina,
        pasta_navegador,
        agora,
        max_esperas_login=max_esperas_login_rede_social,
        espera_login_s=espera_login_s_rede_social,
        max_rolagens=max_rolagens_rede_social,
    )
    resumo_rede = ResumoRedeSocial(
        redes_lidas=resumo_leitor.redes_lidas,
        redes_sem_sessao=resumo_leitor.redes_sem_sessao,
        blocos_capturados=resumo_leitor.blocos_capturados,
        fatos_gravados=resumo_leitor.fatos_gravados,
        motivos_sem_sessao=list(resumo_leitor.motivos_sem_sessao),
    )

    cruzamento.cruzar_contato(cliente_llm, conexao, perfil_id, limiares, agora)

    data_hoje = agora[:10]
    registros = assunto_contato_q.listar_do_dia(conexao, perfil_id, data_hoje)
    ativos = [r for r in registros if r.status == "novo" and r.tipo != "fora_do_dominio"]

    itens_menu: list[ItemMenu] = []
    itens_serializaveis: list[dict[str, Any]] = []
    for registro in ativos:
        assert registro.id is not None
        assunto = assuntos_q.obter_por_id(conexao, registro.assunto_id)
        titulo = (
            assunto.titulo_gerado
            if assunto is not None and assunto.titulo_gerado
            else f"assunto #{registro.assunto_id}"
        )
        itens_menu.append(
            ItemMenu(
                ac_id=registro.id,
                assunto_id=registro.assunto_id,
                tipo=registro.tipo,
                titulo=titulo,
                por_que=registro.por_que,
                score=registro.score,
            )
        )
        itens_serializaveis.append(
            {"titulo": titulo, "tipo": registro.tipo, "score": registro.score, "por_que": registro.por_que}
        )

    aviso = None if itens_menu else "Nenhum assunto qualificado para este contato agora."
    historico_texto = historico_mod.historico_recente_para_prompt(conexao, perfil_id)

    consulta_gravada = consulta_contato_q.inserir(
        conexao,
        perfil_id,
        agora,
        contexto.model_dump_json(),
        _resumo_rede_para_texto(resumo_rede),
        json.dumps(itens_serializaveis, ensure_ascii=False),
    )
    conexao.commit()
    assert consulta_gravada.id is not None

    return ResultadoConsulta(
        perfil_id=perfil_id,
        consulta_id=consulta_gravada.id,
        itens_menu=itens_menu,
        resumo_rede_social=resumo_rede,
        historico_texto=historico_texto,
        aviso=aviso,
    )
