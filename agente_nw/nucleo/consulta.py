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
from agente_nw.coleta.rss import google_news
from agente_nw.coleta.rss import leitor as leitor_rss
from agente_nw.nucleo import historico as historico_mod
from agente_nw.nucleo import termos_contato as termos_contato_mod
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


def _texto_da_consulta(contexto: ContextoConsulta) -> str:
    partes = [contexto.assunto, contexto.objetivo, *contexto.interessa, contexto.livre]
    return "\n".join(parte for parte in partes if parte.strip())


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
    max_esperas_login_rede_social: int = 0,
    espera_login_s_rede_social: float = 5.0,
    max_rolagens_rede_social: int = 5,
    avisar: Callable[[str], None] | None = None,
) -> ResultadoConsulta:
    """Orquestra a consulta sob demanda sobre um contato.

    Ordem: leitura de rede social → coleta de notícia (se `rodar_coleta`; as buscas incluem termos
    tirados do que o contato publica) → extração da fila → agrupamento → qualificação → cruzamento
    por contato → montagem do menu → gravação em `consulta_contato`. Contato sem rede social cadastrada
    ou sem histórico anterior não interrompe o fluxo; o resultado devolve um
    `aviso` quando não há assunto qualificado.

    O contexto lido pelo motor desde o brief 034: vira o centroide da consulta
    (sinal principal), gera consultas ao Google News, filtra `evitar` e entra no
    "por quê". Tags e fatos do contato e temas do usuário enriquecem quando
    existem e nunca bloqueiam. O `contexto` inteiro também é serializado em
    `contexto_json`.
    """

    def etapa(texto: str) -> None:
        if avisar is not None:
            avisar(texto)

    etapa("Entendendo o pedido (vetor da consulta)...")
    centroide_consulta = cliente_llm.embeddar([_texto_da_consulta(contexto)])[0]

    etapa("Lendo as redes sociais do contato no seu Chrome...")
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
        maximo_blocos=limiares.coleta.maximo_blocos_por_rede,
        maximo_imagens=limiares.coleta.maximo_imagens_por_rede,
        largura_minima_imagem=limiares.coleta.largura_minima_imagem,
        avisar=avisar,
    )
    resumo_rede = ResumoRedeSocial(
        redes_lidas=resumo_leitor.redes_lidas,
        redes_sem_sessao=resumo_leitor.redes_sem_sessao,
        blocos_capturados=resumo_leitor.blocos_capturados,
        fatos_gravados=resumo_leitor.fatos_gravados,
        motivos_sem_sessao=list(resumo_leitor.motivos_sem_sessao),
    )

    if rodar_coleta:
        etapa("Escolhendo os termos de busca pelo que o contato publica...")
        termos_contato = termos_contato_mod.termos_do_contato(cliente_llm, conexao, perfil_id)
        etapa(f"Termos de busca do contato: {', '.join(termos_contato) or '(nenhum)'}")
        etapa("Coletando notícias (feeds e consultas ao Google News)...")
        resumo_coleta = leitor_rss.coletar(
            conexao,
            cliente_http,
            caminho_fontes if caminho_fontes.exists() else None,
            limiares.coleta,
            caminho_sentinela,
            feeds_extras=google_news.gerar_consultas_da_consulta(contexto, termos_contato),
        )
        if resumo_coleta is not None and resumo_coleta.bloqueio is not None:
            etapa(
                f"AVISO: {resumo_coleta.bloqueio}: excesso de buscas, o site bloqueou por um tempo. "
                "As notícias desta consulta não foram buscadas; só valem as já guardadas."
            )
        elif resumo_coleta is not None and resumo_coleta.feeds_com_erro:
            etapa(f"AVISO: {len(resumo_coleta.feeds_com_erro)} busca(s) de notícia falharam nesta consulta.")

    etapa("Extraindo texto das notícias novas...")
    extrator_perfil.processar_fila(cliente_llm, conexao)
    etapa("Agrupando as notícias em assuntos...")
    agrupador.agrupar(cliente_llm, conexao, limiares, caminho_sentinela, agora)
    etapa("Qualificando os assuntos novos...")
    qualificador.qualificar_pendentes(
        cliente_llm, conexao, limiares.qualificacao.teto_por_dia, vetores_extras=[centroide_consulta]
    )

    etapa("Escolhendo os assuntos para esta pessoa...")
    cruzamento.cruzar_contato_por_consulta(
        cliente_llm, conexao, perfil_id, contexto, centroide_consulta, limiares, agora
    )

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

    aviso = (
        None
        if itens_menu
        else "Não achei notícia com relação com o pedido ou com o que esta pessoa publica. "
        "Tente outro assunto, ou espere notícias novas."
    )
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
