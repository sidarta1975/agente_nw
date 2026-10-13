"""Fluxo do pedido para a tela única (brief 039).

O console grava o pedido e responde na hora; o trabalho roda numa thread do próprio processo
(`FilaDeTrabalho`, uma tarefa por vez) e vai atualizando `pedido.status` e `pedido.etapa`. Quando a IA
precisa que o usuário confirme uma pessoa, o pedido para em `aguardando_pessoa` com as perguntas em
`pedido.localizacao_json`; a resposta do usuário chama `decidir_*` e, sem mais perguntas, `continuar_pedido`.
"""

from __future__ import annotations

import json
import queue
import sqlite3
import threading
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from agente_nw.nucleo import localizacao as localizacao_mod
from agente_nw.nucleo import pedido as pedido_mod
from agente_nw.nucleo import redacao as redacao_mod
from agente_nw.nucleo.consulta import preparar
from agente_nw.nucleo.database import conexao as conexao_bd
from agente_nw.nucleo.database.queries import listas as queries_listas
from agente_nw.nucleo.database.queries import pedidos, perfis, rede_sem_perfil, sistema
from agente_nw.nucleo.modelos.configuracao import Limiares
from agente_nw.nucleo.modelos.localizacao import Localizacao, Opcao
from agente_nw.nucleo.modelos.pedido import PedidoExtraido

FRACAO_DO_CONTEXTO_NO_PROMPT = 0.73  # 8192 de contexto → ~6000 tokens estimados de prompt
ETAPA_DA_COLETA = "coleta"
_PREFIXO_AVISO = "AVISO"


@dataclass
class Dependencias:
    """Tudo de que o fluxo precisa fora do banco. Cada pedido abre a sua conexão (thread própria)."""

    caminho_banco: Path
    fabrica_llm: Callable[[sqlite3.Connection], Any]
    fabrica_http: Callable[[], httpx.Client]
    limiares: Limiares
    num_ctx_redacao: int
    caminho_fontes: Path
    caminho_sentinela: Path
    pasta_navegador: Path
    abrir_pagina: Callable[[Path], Any]  # extensão do Chrome: serve à localização e à leitura
    usuarios_rede: dict[str, str] = field(default_factory=dict)  # o usuário do próprio dono em cada rede
    gravar_usuario: Callable[[str, str], None] | None = None


class FilaDeTrabalho:
    """Uma tarefa por vez, numa thread só: o segundo pedido espera o primeiro terminar."""

    def __init__(self) -> None:
        self._fila: queue.Queue[Callable[[], None]] = queue.Queue()
        self._fio: threading.Thread | None = None
        self._trava = threading.Lock()

    def enfileirar(self, tarefa: Callable[[], None]) -> None:
        with self._trava:
            if self._fio is None:
                self._fio = threading.Thread(target=self._laco, name="fila-de-pedidos", daemon=True)
                self._fio.start()
        self._fila.put(tarefa)

    def _laco(self) -> None:
        while True:
            tarefa = self._fila.get()
            try:
                tarefa()
            except Exception:  # noqa: BLE001 — a tarefa grava o próprio erro; a fila não pode morrer
                continue


# ---- perguntas ao usuário (serialização) ------------------------------------------------------------


def _opcao_para_dict(opcao: Opcao) -> dict[str, Any]:
    return asdict(opcao)


def _opcao_de_dict(dados: dict[str, Any]) -> Opcao:
    return Opcao(**dados)


def pergunta_de_rede(localizacao: Localizacao) -> dict[str, Any]:
    return {
        "tipo": "rede",
        "rede": localizacao.rede,
        "status": localizacao.status,
        "escolhido": _opcao_para_dict(localizacao.escolhido) if localizacao.escolhido else None,
        "opcoes": [_opcao_para_dict(o) for o in localizacao.opcoes],
        "avisos": list(localizacao.avisos),
    }


def pergunta_de_contato(candidatos: list[Any]) -> dict[str, Any]:
    return {
        "tipo": "contato",
        "candidatos": [
            {
                "perfil_id": c.id,
                "nome": c.nome,
                "detalhe": ", ".join(p for p in (c.cargo, c.empresa, c.cidade) if p),
            }
            for c in candidatos
        ],
    }


def perguntas_pendentes(pedido: pedidos.PedidoGravado) -> list[dict[str, Any]]:
    if not pedido.localizacao_json:
        return []
    dados: list[dict[str, Any]] = json.loads(pedido.localizacao_json)
    return dados


def opcao_da_pergunta(dados: dict[str, Any] | None) -> Opcao | None:
    return _opcao_de_dict(dados) if dados else None


def _gravar_perguntas(conexao: sqlite3.Connection, pedido_id: int, perguntas: list[dict[str, Any]]) -> None:
    texto = json.dumps(perguntas, ensure_ascii=False) if perguntas else None
    pedidos.gravar_localizacoes(conexao, pedido_id, texto)
    conexao.commit()


# ---- criação do pedido -----------------------------------------------------------------------------


def criar_pedido(conexao: sqlite3.Connection, texto: str, agora: str) -> int:
    pedido_id = pedidos.inserir(conexao, texto, agora, status="na_fila")
    conexao.commit()
    return pedido_id


def criar_correcao(conexao: sqlite3.Connection, pedido_pai_id: int, correcao: str, agora: str) -> int | None:
    """Pedido novo que refaz o anterior com a correção do usuário; a pessoa já está confirmada."""
    pai = pedidos.obter_por_id(conexao, pedido_pai_id)
    if pai is None or pai.perfil_id is None or not correcao.strip():
        return None
    texto = f"{pai.texto}\nCorreção: {correcao.strip()}"
    pedido_id = pedidos.inserir(
        conexao, texto, agora, pedido_pai_id=pai.id, perfil_id=pai.perfil_id, status="na_fila"
    )
    conexao.commit()
    return pedido_id


def marcar_interrompidos(conexao: sqlite3.Connection) -> int:
    """Pedido que ficou 'processando' porque o console foi encerrado não vai terminar sozinho."""
    cursor = conexao.execute(
        "UPDATE pedido SET status = 'erro', erro = 'O console foi encerrado durante o pedido.' "
        "WHERE status IN ('na_fila', 'processando')"
    )
    conexao.commit()
    return cursor.rowcount


# ---- execução --------------------------------------------------------------------------------------


def _agora() -> str:
    return datetime.now(UTC).isoformat()


def executar_pedido(deps: Dependencias, pedido_id: int) -> None:
    """Entende o pedido, resolve o contato e, se não houver pergunta pendente, escreve os ganchos."""
    _com_conexao_propria(deps, pedido_id, lambda conexao: _entender(deps, conexao, pedido_id))


def continuar_pedido(deps: Dependencias, pedido_id: int) -> None:
    """Retoma depois das respostas do usuário (não há mais pergunta pendente)."""
    _com_conexao_propria(deps, pedido_id, lambda conexao: _escrever(deps, conexao, pedido_id))


def _com_conexao_propria(
    deps: Dependencias, pedido_id: int, trabalho: Callable[[sqlite3.Connection], None]
) -> None:
    conexao = conexao_bd.abrir(deps.caminho_banco)
    try:
        trabalho(conexao)
    except Exception as erro:  # noqa: BLE001 — qualquer falha vira "deu errado em <etapa>" na página
        conexao.rollback()
        pedidos.atualizar_status(conexao, pedido_id, "erro", f"{type(erro).__name__}: {erro}")
        conexao.commit()
    finally:
        conexao.close()


def _etapa(conexao: sqlite3.Connection, pedido_id: int, texto: str) -> None:
    pedidos.atualizar_etapa(conexao, pedido_id, texto)
    conexao.commit()


def _entender(deps: Dependencias, conexao: sqlite3.Connection, pedido_id: int) -> None:
    pedido = pedidos.obter_por_id(conexao, pedido_id)
    assert pedido is not None
    pedidos.atualizar_status(conexao, pedido_id, "processando")
    _gravar_perguntas(conexao, pedido_id, [])
    _etapa(conexao, pedido_id, "Entendendo o pedido")
    cliente_llm = deps.fabrica_llm(conexao)

    correcao = pedido.pedido_pai_id is not None
    navegacao: localizacao_mod.ContextoNavegacao | None = None
    if not correcao:
        navegacao = localizacao_mod.ContextoNavegacao(
            abrir_pagina=deps.abrir_pagina,
            pasta_navegador=deps.pasta_navegador,
            limiares=deps.limiares.listas,
            usuarios_rede=deps.usuarios_rede,
            gravar_usuario=deps.gravar_usuario,
            avisar=lambda texto: _etapa(conexao, pedido_id, texto),
        )
    resultado = pedido_mod.processar(
        cliente_llm,
        conexao,
        pedido.texto,
        _agora(),
        contato_id_forcado=pedido.perfil_id,  # correção, ou contato já escolhido pelo usuário
        navegacao=navegacao,
        pedido_id=pedido_id,
    )

    perguntas: list[dict[str, Any]] = []
    if resultado.contato_ambiguo:
        perguntas.append(pergunta_de_contato(resultado.candidatos))
    else:
        perguntas.extend(pergunta_de_rede(loc) for loc in resultado.localizacoes)
    if perguntas:
        _gravar_perguntas(conexao, pedido_id, perguntas)
        pedidos.atualizar_status(conexao, pedido_id, "aguardando_pessoa")
        conexao.commit()
        return
    _escrever(deps, conexao, pedido_id)


def _coleta_recente(conexao: sqlite3.Connection, minutos: int, agora: str) -> bool:
    progresso = sistema.progresso_obter(conexao, ETAPA_DA_COLETA)
    if progresso is None or not progresso["atualizado_em"] or minutos <= 0:
        return False
    ultima = datetime.fromisoformat(str(progresso["atualizado_em"]))
    return (datetime.fromisoformat(agora) - ultima).total_seconds() < minutos * 60


def _escrever(deps: Dependencias, conexao: sqlite3.Connection, pedido_id: int) -> None:
    pedido = pedidos.obter_por_id(conexao, pedido_id)
    assert pedido is not None
    avisos: list[str] = []
    if pedido.perfil_id is None or pedido.extraido_json is None:
        sem_pessoa = ["Pedido sem pessoa: não há contato para preparar."]
        pedidos.gravar_avisos(conexao, pedido_id, json.dumps(sem_pessoa, ensure_ascii=False))
        pedidos.atualizar_status(conexao, pedido_id, "concluido")
        conexao.commit()
        return
    perfil = perfis.obter_por_id(conexao, pedido.perfil_id)
    assert perfil is not None
    extraido = PedidoExtraido.model_validate_json(pedido.extraido_json)
    cliente_llm = deps.fabrica_llm(conexao)
    usuario = pedido_mod.garantir_usuario(conexao, _agora())
    correcao = pedido.pedido_pai_id is not None

    def avisar(texto: str) -> None:
        if texto.startswith(_PREFIXO_AVISO):
            avisos.append(texto)
        _etapa(conexao, pedido_id, texto)

    agora = _agora()
    reaproveita = correcao and _coleta_recente(conexao, deps.limiares.coleta.minutos_reaproveitamento, agora)
    with deps.fabrica_http() as cliente_http:
        consulta = preparar(
            conexao=conexao,
            cliente_llm=cliente_llm,
            cliente_http=cliente_http,
            perfil_id=perfil.id or 0,
            contexto=pedido_mod.para_contexto(extraido, pedido.texto),
            limiares=deps.limiares,
            caminho_fontes=deps.caminho_fontes,
            caminho_sentinela=deps.caminho_sentinela,
            abrir_pagina=deps.abrir_pagina,
            pasta_navegador=deps.pasta_navegador,
            agora=agora,
            rodar_coleta=not reaproveita,
            ler_redes_sociais=not correcao,
            avisar=avisar,
        )
    pedidos.gravar_consulta(conexao, pedido_id, consulta.consulta_id)
    conexao.commit()

    _etapa(conexao, pedido_id, "Escrevendo os ganchos e as mensagens")
    agora_redacao = _agora()
    redacao = redacao_mod.redigir(
        cliente_llm,
        conexao,
        extraido,
        consulta,
        perfil,
        usuario,
        agora_redacao,
        frase=pedido.texto,
        limite_tokens=int(deps.num_ctx_redacao * FRACAO_DO_CONTEXTO_NO_PROMPT),
    )
    redacao_mod.registrar(conexao, consulta.consulta_id, redacao, agora_redacao)
    if redacao.aviso:
        avisos.append(redacao.aviso)
    pedidos.gravar_avisos(conexao, pedido_id, json.dumps(avisos, ensure_ascii=False) if avisos else None)
    pedidos.atualizar_status(conexao, pedido_id, "concluido")
    _etapa(conexao, pedido_id, "Pronto")


# ---- respostas do usuário --------------------------------------------------------------------------


def decidir_rede(
    conexao: sqlite3.Connection,
    pedido_id: int,
    rede: str,
    acao: str,
    agora: str,
    indice: int | None = None,
    link: str = "",
) -> str | None:
    """Aplica a resposta do usuário a uma pergunta de rede. Devolve uma mensagem de erro, ou None.

    `acao`: `sugerido` (a pessoa que a IA achou), `opcao` (uma das candidatas, por `indice`), `link`
    (perfil colado), `sem_perfil` (a pessoa não tem conta nessa rede) ou `pular` (decidir depois)."""
    pedido = pedidos.obter_por_id(conexao, pedido_id)
    if pedido is None or pedido.perfil_id is None:
        return "Pedido sem contato."
    perguntas = perguntas_pendentes(pedido)
    pergunta = next((p for p in perguntas if p["tipo"] == "rede" and p["rede"] == rede), None)
    if pergunta is None:
        return None  # já respondida (clique repetido)

    escolhida: Opcao | None = None
    if acao == "sugerido":
        escolhida = opcao_da_pergunta(pergunta["escolhido"])
    elif acao == "opcao":
        opcoes = pergunta["opcoes"]
        if indice is None or not 0 <= indice < len(opcoes):
            return "Opção inválida."
        escolhida = _opcao_de_dict(opcoes[indice])
    elif acao == "link":
        escolhida = localizacao_mod.opcao_do_link(conexao, link)
        if escolhida is None:
            return "Link não reconhecido (aceito: linkedin, instagram, facebook, x)."
    elif acao == "sem_perfil":
        rede_sem_perfil.declarar(conexao, pedido.perfil_id, rede, agora)
    elif acao != "pular":
        return "Ação inválida."
    if escolhida is not None:
        localizacao_mod.confirmar(conexao, pedido.perfil_id, escolhida, agora)

    _gravar_perguntas(conexao, pedido_id, [p for p in perguntas if p is not pergunta])
    return None


def decidir_contato(conexao: sqlite3.Connection, pedido_id: int, perfil_id: int) -> str | None:
    """O usuário escolheu entre contatos homônimos: o pedido recomeça já com a pessoa certa."""
    pedido = pedidos.obter_por_id(conexao, pedido_id)
    if pedido is None:
        return "Pedido inexistente."
    candidatos = {
        c["perfil_id"]
        for pergunta in perguntas_pendentes(pedido)
        if pergunta["tipo"] == "contato"
        for c in pergunta["candidatos"]
    }
    if perfil_id not in candidatos:
        return "Contato inválido."
    pedidos.gravar_resolucao(conexao, pedido_id, perfil_id, False, False)
    _gravar_perguntas(conexao, pedido_id, [])
    pedidos.atualizar_status(conexao, pedido_id, "na_fila")
    conexao.commit()
    return None


def sem_perguntas(conexao: sqlite3.Connection, pedido_id: int) -> bool:
    pedido = pedidos.obter_por_id(conexao, pedido_id)
    return pedido is not None and not perguntas_pendentes(pedido)


def entradas_da_lista(conexao: sqlite3.Connection, rede: str, filtro: str) -> list[Opcao]:
    entradas = (
        queries_listas.filtrar_por_texto(conexao, rede, filtro)
        if filtro
        else queries_listas.listar_por_rede(conexao, rede)
    )
    return [localizacao_mod.opcao_da_entrada(entrada) for entrada in entradas]
