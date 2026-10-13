from __future__ import annotations

import getpass
import sqlite3
from collections.abc import Callable, Sequence
from typing import Protocol, TypeVar

from pydantic import BaseModel

from agente_nw.nucleo import localizacao as localizacao_mod
from agente_nw.nucleo.database.queries import pedidos, perfis, rede_sem_perfil, redes_sociais
from agente_nw.nucleo.modelos.contexto_consulta import ContextoConsulta
from agente_nw.nucleo.modelos.pedido import PedidoExtraido, ResultadoPedido
from agente_nw.nucleo.modelos.perfil import Perfil
from agente_nw.nucleo.prompts import extrair_pedido
from agente_nw.nucleo.texto import sem_acento_e_caixa, similaridade_nome

_EsquemaT = TypeVar("_EsquemaT", bound=BaseModel)
_MAXIMO_CONTATOS_NO_PROMPT = 50


class ClientePedido(Protocol):
    def gerar_json(self, tarefa_nome: str, prompt: str, esquema: type[_EsquemaT]) -> _EsquemaT: ...


def extrair(cliente_llm: ClientePedido, conexao: sqlite3.Connection, frase: str) -> PedidoExtraido:
    conhecidos = [
        (contato.nome, contato.empresa, contato.cargo)
        for contato in perfis.listar_contatos_recentes(conexao, _MAXIMO_CONTATOS_NO_PROMPT)
    ]
    prompt = extrair_pedido.construir_prompt(frase, conhecidos)
    return cliente_llm.gerar_json("extrair_pedido", prompt, PedidoExtraido)


def _casa(pista: str | None, valor: str | None) -> bool:
    if not pista or not valor:
        return False
    a, b = sem_acento_e_caixa(pista), sem_acento_e_caixa(valor)
    return a in b or b in a


def _pistas_casadas(contato: Perfil, pedido: PedidoExtraido) -> int:
    pistas = pedido.pessoa_pistas
    return sum(
        (
            _casa(pistas.get("empresa"), contato.empresa),
            _casa(pistas.get("cidade"), contato.cidade),
            _casa(pistas.get("profissao"), contato.cargo),
        )
    )


def _lacunas_das_pistas(pedido: PedidoExtraido) -> dict[str, str]:
    pistas = pedido.pessoa_pistas
    notas = "; ".join(
        f"{rotulo}: {pistas[chave]}"
        for chave, rotulo in (("vinculo", "vínculo"), ("tempo_sem_contato", "sem contato"))
        if chave in pistas
    )
    campos = {
        "empresa": pistas.get("empresa", ""),
        "cargo": pistas.get("profissao", ""),
        "cidade": pistas.get("cidade", ""),
        "notas": notas,
    }
    return {campo: valor for campo, valor in campos.items() if valor}


def resolver_contato(
    conexao: sqlite3.Connection,
    pedido: PedidoExtraido,
    agora: str,
    contato_id_forcado: int | None = None,
) -> tuple[Perfil | None, bool, bool, list[Perfil]]:
    """Devolve (perfil, contato_criado, contato_ambiguo, candidatos)."""
    if contato_id_forcado is not None:
        forcado = perfis.obter_por_id(conexao, contato_id_forcado)
        if forcado is None or forcado.tipo != "contato" or forcado.id is None:
            raise ValueError(f"contato #{contato_id_forcado} não existe")
        perfis.preencher_lacunas(conexao, forcado.id, _lacunas_das_pistas(pedido), agora)
        atual = perfis.obter_por_id(conexao, forcado.id)
        return atual, False, False, []

    if not pedido.pessoa_nome:
        return None, False, False, []

    candidatos = perfis.buscar_por_nome(conexao, pedido.pessoa_nome)
    if not candidatos:
        novo = perfis.inserir_novo_contato(conexao, pedido.pessoa_nome, None, None, agora)
        assert novo.id is not None
        perfis.preencher_lacunas(conexao, novo.id, _lacunas_das_pistas(pedido), agora)
        return perfis.obter_por_id(conexao, novo.id), True, False, []

    ordenados = sorted(
        candidatos,
        key=lambda c: (_pistas_casadas(c, pedido), c.atualizado_em, c.id or 0),
        reverse=True,
    )
    escolhido = ordenados[0]
    assert escolhido.id is not None
    perfis.preencher_lacunas(conexao, escolhido.id, _lacunas_das_pistas(pedido), agora)
    return perfis.obter_por_id(conexao, escolhido.id), False, len(ordenados) > 1, ordenados


def garantir_usuario(conexao: sqlite3.Connection, agora: str) -> Perfil:
    existente = perfis.obter_usuario(conexao)
    if existente is not None:
        return existente
    login = getpass.getuser()
    return perfis.upsert_usuario(conexao, login[:1].upper() + login[1:], agora)


def para_contexto(pedido: PedidoExtraido, frase: str = "") -> ContextoConsulta:
    return ContextoConsulta(
        assunto=pedido.assunto_principal,
        meio=pedido.meio,
        objetivo=pedido.objetivo_texto,
        interessa=list(pedido.interessa),
        evitar=list(pedido.evitar),
        livre=frase,
        registro=pedido.registro,
        termos_busca=list(pedido.termos_busca),
    )


def registrar(conexao: sqlite3.Connection, frase: str, agora: str) -> int:
    """Grava a frase bruta antes de qualquer outra etapa."""
    pedido_id = pedidos.inserir(conexao, frase, agora)
    conexao.commit()
    return pedido_id


def processar(
    cliente_llm: ClientePedido,
    conexao: sqlite3.Connection,
    frase: str,
    agora: str,
    contato_id_forcado: int | None = None,
    navegacao: localizacao_mod.ContextoNavegacao | None = None,
    trocar_perfil: bool = False,
    perfis_informados: Sequence[str] = (),
    confirmar_contato: Callable[[str, str], bool] | None = None,
    similaridade_minima_contato: float = 0.5,
    pedido_id: int | None = None,
) -> ResultadoPedido:
    """`pedido_id`: o console já gravou o pedido (e responde ao usuário antes de processar)."""
    if pedido_id is None:
        pedido_id = registrar(conexao, frase, agora)

    pedido = extrair(cliente_llm, conexao, frase)
    pedidos.gravar_extracao(conexao, pedido_id, pedido.model_dump_json(), pedido.confianca)
    conexao.commit()

    garantir_usuario(conexao, agora)
    perfil, criado, ambiguo, candidatos = resolver_contato(conexao, pedido, agora, contato_id_forcado)
    pedidos.gravar_resolucao(conexao, pedido_id, perfil.id if perfil is not None else None, criado, ambiguo)
    conexao.commit()

    divergente = (
        contato_id_forcado is not None
        and perfil is not None
        and bool(pedido.pessoa_nome)
        and similaridade_nome(pedido.pessoa_nome, perfil.nome) < similaridade_minima_contato
    )
    if divergente and perfil is not None and confirmar_contato is not None:
        divergente = not confirmar_contato(pedido.pessoa_nome, perfil.nome)

    resultado = ResultadoPedido(
        pedido_id=pedido_id,
        pedido=pedido,
        perfil=perfil,
        contato_criado=criado,
        contato_ambiguo=ambiguo,
        contato_divergente=divergente,
        candidatos=candidatos,
    )
    _localizar_na_rede(cliente_llm, conexao, resultado, agora, navegacao, trocar_perfil, perfis_informados)
    return resultado


def _localizar_na_rede(
    cliente_llm: ClientePedido,
    conexao: sqlite3.Connection,
    resultado: ResultadoPedido,
    agora: str,
    navegacao: localizacao_mod.ContextoNavegacao | None,
    trocar_perfil: bool,
    perfis_informados: Sequence[str] = (),
) -> None:
    """Curadoria dos perfis (briefs 037 e 038). Link no pedido ou em `perfis_informados` grava direto.
    Uma rede só é procurada enquanto estiver pendente: com perfil gravado ou declarada "sem perfil"
    pelo usuário ela está curada e o programa não volta a procurar (a menos que `trocar_perfil`)."""
    perfil = resultado.perfil
    pedido = resultado.pedido
    if perfil is None or perfil.id is None or not pedido.pessoa_nome:
        return
    if resultado.contato_divergente:
        return  # o contato dado em --contato não é a pessoa do pedido: não grava rede social nele
    if resultado.contato_ambiguo:
        return  # há homônimos e o contato é um palpite: não grava rede social em quem pode ser outro

    link = pedido.pessoa_pistas.get("link_rede_social")
    if link:
        resultado.link_gravado = localizacao_mod.gravar_link_do_pedido(
            conexao, perfil.id, link, agora, substituir=trocar_perfil
        )
        if resultado.link_gravado is not None:
            return
    for informado in perfis_informados:
        gravado = localizacao_mod.gravar_link_do_pedido(conexao, perfil.id, informado, agora, substituir=True)
        if gravado is None:
            resultado.links_nao_reconhecidos.append(informado)
    if navegacao is None:
        return
    curadas = {r.rede for r in redes_sociais.listar_por_perfil(conexao, perfil.id)}
    curadas |= rede_sem_perfil.listar_redes(conexao, perfil.id)
    so_por_link = navegacao.limiares.redes_so_por_link
    for rede in localizacao_mod.ordem_das_redes(pedido.registro, pedido.pessoa_pistas, so_por_link):
        if rede in curadas and not trocar_perfil:
            continue
        resultado.localizacoes.append(
            localizacao_mod.localizar_rede(
                conexao, cliente_llm, pedido, navegacao, agora, rede, nomes_extras=[perfil.nome]
            )
        )
