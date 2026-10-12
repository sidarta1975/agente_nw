from __future__ import annotations

import sqlite3
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, TypeVar
from urllib.parse import urlparse

from pydantic import BaseModel

from agente_nw.coleta.capturas import busca, listas
from agente_nw.coleta.capturas.busca import REDES_SUPORTADAS
from agente_nw.coleta.capturas.listas import PaginaLista, ResultadoAtualizacao
from agente_nw.nucleo.database.queries import fatos, perfis, redes_sociais
from agente_nw.nucleo.database.queries import listas as queries_listas
from agente_nw.nucleo.llm import FalhaJsonInvalido
from agente_nw.nucleo.modelos.configuracao import ListasLimiares
from agente_nw.nucleo.modelos.fato import Fato
from agente_nw.nucleo.modelos.lista_rede_social import EntradaGravada
from agente_nw.nucleo.modelos.localizacao import Localizacao, Opcao, RespostaDesempate
from agente_nw.nucleo.modelos.pedido import PedidoExtraido
from agente_nw.nucleo.prompts import desempatar_perfil
from agente_nw.nucleo.texto import sem_acento_e_caixa

_EsquemaT = TypeVar("_EsquemaT", bound=BaseModel)
_CONFIANCA_MINIMA = 0.7
TIPO_FATO_LISTA = "lista_rede_social"
_HOSTS_POR_REDE: dict[str, str] = {
    "linkedin.com": "linkedin",
    "instagram.com": "instagram",
    "facebook.com": "facebook",
    "x.com": "x",
    "twitter.com": "x",
}


class ClienteDesempate(Protocol):
    def gerar_json(self, tarefa_nome: str, prompt: str, esquema: type[_EsquemaT]) -> _EsquemaT: ...


@dataclass
class ContextoNavegacao:
    """Tudo de que a localização precisa para abrir o navegador do usuário e guardar o que aprende."""

    abrir_pagina: Callable[[Path], PaginaLista]
    pasta_navegador: Path
    limiares: ListasLimiares
    usuarios_rede: dict[str, str]
    gravar_usuario: Callable[[str, str], None] | None = None
    perguntar_usuario: Callable[[str], str | None] | None = None
    avisar: Callable[[str], None] | None = None
    dorme: Callable[[float], None] = time.sleep
    aguardar_login: bool = False
    """False: rede sem sessão é descartada na hora (a localização nunca prende o pedido esperando
    login). True: espera o login como na leitura de perfil (brief 017) — uso explícito do usuário."""

    @property
    def max_esperas_login(self) -> int:
        return listas.MAX_ESPERAS_LOGIN if self.aguardar_login else 0


def canonicalizar_link(link: str) -> str:
    """Sem parâmetros de rastreio nem barra final, para o mesmo perfil ter sempre o mesmo link."""
    bruto = link.strip()
    base = bruto if "profile.php" in bruto else bruto.split("?")[0]
    return base.rstrip("/")


def rede_do_link(link: str) -> str | None:
    host = (urlparse(link.strip()).hostname or "").lower().removeprefix("www.")
    return _HOSTS_POR_REDE.get(host)


def ordem_das_redes(registro: str, pistas: dict[str, str]) -> list[str]:
    """LinkedIn primeiro para registro cordial/formal ou pista de profissão/empresa; Instagram
    primeiro para registro próximo; as demais na ordem de REDES_SUPORTADAS."""
    profissional = registro in ("cordial", "formal") or "profissao" in pistas or "empresa" in pistas
    primeira = "linkedin" if profissional else ("instagram" if registro == "proximo" else None)
    restantes = [r for r in REDES_SUPORTADAS if r != primeira]
    return ([primeira] if primeira else []) + restantes


def opcao_da_entrada(entrada: EntradaGravada) -> Opcao:
    return Opcao(
        rede=entrada.rede,
        nome=entrada.nome,
        cabecalho=entrada.cabecalho,
        link=entrada.link,
        fonte="lista",
        foto_url=entrada.foto_url,
    )


def _pontuar(opcao: Opcao, pistas: dict[str, str]) -> int:
    cabecalho = sem_acento_e_caixa(opcao.cabecalho)
    return sum(
        1
        for chave in ("profissao", "empresa", "cidade")
        if chave in pistas and sem_acento_e_caixa(pistas[chave]) in cabecalho
    )


def _desempatar(
    cliente_llm: ClienteDesempate, nome: str, pistas: dict[str, str], empatadas: list[Opcao]
) -> Opcao | None:
    prompt = desempatar_perfil.construir_prompt(nome, pistas, [o.cabecalho for o in empatadas])
    try:
        resposta = cliente_llm.gerar_json("desempatar_perfil", prompt, RespostaDesempate)
    except FalhaJsonInvalido:
        return None
    indice = resposta.indice_escolhido
    if indice is None or not 1 <= indice <= len(empatadas) or resposta.confianca < _CONFIANCA_MINIMA:
        return None
    return empatadas[indice - 1]


def _avaliar(
    cliente_llm: ClienteDesempate, pedido: PedidoExtraido, candidatas: list[Opcao]
) -> tuple[Opcao | None, list[Opcao]]:
    """Devolve (escolhido claro ou None, candidatas ordenadas da mais para a menos provável)."""
    pistas = pedido.pessoa_pistas
    tem_pistas = any(chave in pistas for chave in ("profissao", "empresa", "cidade"))
    pontuadas = sorted(((_pontuar(o, pistas), o) for o in candidatas), key=lambda par: -par[0])
    ordenadas = [o for _, o in pontuadas]
    melhor = pontuadas[0][0]
    empatadas = [o for pontos, o in pontuadas if pontos == melhor]

    if len(empatadas) == 1:
        claro = not tem_pistas or melhor >= 1
        return (empatadas[0] if claro else None), ordenadas
    if tem_pistas:
        escolhida = _desempatar(cliente_llm, pedido.pessoa_nome, pistas, empatadas)
        if escolhida is not None:
            resto = [o for o in ordenadas if o != escolhida]
            return escolhida, [escolhida, *resto]
    return None, ordenadas


def atualizar_lista(
    conexao: sqlite3.Connection,
    rede: str,
    contexto: ContextoNavegacao,
    agora: str,
    forcar: bool = False,
) -> ResultadoAtualizacao:
    """Garante a lista de `rede` no cache: usa o cache válido, ou lê a lista do navegador do usuário."""
    if not forcar and queries_listas.cache_valido(conexao, rede, contexto.limiares.validade_dias, agora):
        return ResultadoAtualizacao(
            rede=rede, lida=False, usou_cache=True, total=queries_listas.contar_por_rede(conexao, rede)
        )

    usuario = listas.resolver_usuario(
        rede,
        contexto.usuarios_rede.get(rede),
        contexto.abrir_pagina,
        contexto.pasta_navegador,
        contexto.gravar_usuario,
        contexto.perguntar_usuario,
        dorme=contexto.dorme,
        max_esperas_login=contexto.max_esperas_login,
    )
    if contexto.avisar is not None:
        contexto.avisar(f"Lendo a lista de {rede} — vai demorar; deixe a janela do navegador aberta.")
    pagina = contexto.abrir_pagina(contexto.pasta_navegador / rede)
    try:
        resultado = listas.ler_lista(
            pagina,
            rede,
            usuario,
            contexto.limiares,
            dorme=contexto.dorme,
            max_esperas_login=contexto.max_esperas_login,
        )
    finally:
        pagina.fechar()

    if not resultado.autenticado:
        return ResultadoAtualizacao(rede=rede, lida=False, usou_cache=False, total=0, motivo=resultado.motivo)
    queries_listas.substituir_lista(conexao, rede, resultado.entradas, agora)
    conexao.commit()
    return ResultadoAtualizacao(rede=rede, lida=True, usou_cache=False, total=len(resultado.entradas))


def _busca_geral(
    rede: str, pedido: PedidoExtraido, contexto: ContextoNavegacao
) -> tuple[list[Opcao], str | None]:
    pagina = contexto.abrir_pagina(contexto.pasta_navegador / rede)
    try:
        resultado = busca.buscar(pagina, rede, pedido.pessoa_nome, pedido.pessoa_pistas.get("empresa"))
    finally:
        pagina.fechar()
    if not resultado.autenticado:
        return [], resultado.motivo
    opcoes = [
        Opcao(
            rede=rede,
            nome=c.nome_exibido,
            cabecalho=c.descricao,
            link=canonicalizar_link(c.link),
            fonte="busca_geral",
        )
        for c in resultado.candidatos
    ]
    return opcoes, None


def localizar(
    conexao: sqlite3.Connection,
    cliente_llm: ClienteDesempate,
    pedido: PedidoExtraido,
    contexto: ContextoNavegacao,
    agora: str,
) -> Localizacao:
    """Procura a pessoa do pedido nas listas do próprio usuário (cache local) e, não achando,
    na busca geral de cada rede com sessão. Nunca decide sozinho nem grava: devolve `Localizacao`."""
    avisos: list[str] = []
    sem_sessao: set[str] = set()
    acumuladas: list[Opcao] = []

    for rede in ordem_das_redes(pedido.registro, pedido.pessoa_pistas):
        atualizacao = atualizar_lista(conexao, rede, contexto, agora)
        if atualizacao.motivo:
            avisos.append(f"{rede}: {atualizacao.motivo}")
            sem_sessao.add(rede)
            continue
        candidatas = [
            opcao_da_entrada(e) for e in queries_listas.buscar_por_nome(conexao, rede, pedido.pessoa_nome)
        ]
        if not candidatas:
            candidatas = [
                opcao_da_entrada(e)
                for e in queries_listas.buscar_parecidos(
                    conexao,
                    rede,
                    pedido.pessoa_nome,
                    contexto.limiares.similaridade_minima,
                    contexto.limiares.maximo_parecidas,
                )
            ]
        if not candidatas:
            continue
        escolhido, ordenadas = _avaliar(cliente_llm, pedido, candidatas)
        if escolhido is not None:
            return Localizacao(
                status="claro", escolhido=escolhido, opcoes=ordenadas, fonte="lista", avisos=avisos
            )
        acumuladas.extend(ordenadas)

    if acumuladas:
        return Localizacao(status="ambiguo", opcoes=acumuladas, fonte="lista", avisos=avisos)

    opcoes_busca: list[Opcao] = []
    for rede in ordem_das_redes(pedido.registro, pedido.pessoa_pistas):
        if rede in sem_sessao:
            continue
        achadas, motivo = _busca_geral(rede, pedido, contexto)
        if motivo:
            avisos.append(f"{rede}: {motivo}")
        opcoes_busca.extend(achadas)
    return Localizacao(status="nenhum", opcoes=opcoes_busca, fonte="busca_geral", avisos=avisos)


def confirmar(
    conexao: sqlite3.Connection,
    perfil_id: int,
    opcao: Opcao,
    agora: str,
    substituir: bool = False,
) -> None:
    """Grava a escolha confirmada no contato: rede social, notas (se vazias), vínculo na lista e fato."""
    atuais = redes_sociais.listar_por_perfil(conexao, perfil_id)
    if substituir:
        for existente in atuais:
            if existente.rede == opcao.rede:
                if existente.id is not None:
                    redes_sociais.remover(conexao, existente.id)
        atuais = redes_sociais.listar_por_perfil(conexao, perfil_id)
    if not any(r.link == opcao.link for r in atuais):
        redes_sociais.inserir(conexao, perfil_id, opcao.rede, opcao.link, agora)

    if opcao.cabecalho:
        perfis.preencher_lacunas(conexao, perfil_id, {"notas": opcao.cabecalho}, agora)
        ja_tem = any(
            f.conteudo == opcao.cabecalho and f.tipo == TIPO_FATO_LISTA
            for f in fatos.listar_recentes(conexao, perfil_id, 200)
        )
        if not ja_tem:
            fatos.inserir(
                conexao,
                Fato(
                    perfil_id=perfil_id,
                    tipo=TIPO_FATO_LISTA,
                    conteudo=opcao.cabecalho,
                    fonte=opcao.link,
                    registrado_em=agora,
                ),
            )
    queries_listas.vincular(conexao, opcao.link, perfil_id)
    conexao.commit()


def opcao_do_link(conexao: sqlite3.Connection, link: str) -> Opcao | None:
    """Opção a partir de um link colado pelo usuário; usa o cabeçalho da lista se o link estiver nela."""
    bruto = link.strip()
    rede = rede_do_link(bruto)
    if rede is None:
        return None
    canonico = canonicalizar_link(bruto)
    linha = conexao.execute(
        "SELECT nome, cabecalho FROM lista_rede_social WHERE link = ?", (canonico,)
    ).fetchone()
    nome = linha["nome"] if linha is not None else canonico
    cabecalho = linha["cabecalho"] if linha is not None else ""
    return Opcao(rede=rede, nome=nome, cabecalho=cabecalho, link=canonico, fonte="link_colado")


def gravar_link_do_pedido(
    conexao: sqlite3.Connection, perfil_id: int, link: str, agora: str, substituir: bool = False
) -> Opcao | None:
    """O pedido trouxe o link da pessoa: grava direto, sem perguntar."""
    opcao = opcao_do_link(conexao, link)
    if opcao is None:
        return None
    confirmar(conexao, perfil_id, opcao, agora, substituir=substituir)
    return opcao
