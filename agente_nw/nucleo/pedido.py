from __future__ import annotations

import getpass
import sqlite3
from typing import Protocol, TypeVar

from pydantic import BaseModel

from agente_nw.nucleo import localizacao as localizacao_mod
from agente_nw.nucleo.database.queries import pedidos, perfis, redes_sociais
from agente_nw.nucleo.modelos.contexto_consulta import ContextoConsulta
from agente_nw.nucleo.modelos.pedido import PedidoExtraido, ResultadoPedido
from agente_nw.nucleo.modelos.perfil import Perfil
from agente_nw.nucleo.prompts import extrair_pedido
from agente_nw.nucleo.texto import sem_acento_e_caixa

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
) -> ResultadoPedido:
    pedido_id = registrar(conexao, frase, agora)

    pedido = extrair(cliente_llm, conexao, frase)
    pedidos.gravar_extracao(conexao, pedido_id, pedido.model_dump_json(), pedido.confianca)
    conexao.commit()

    garantir_usuario(conexao, agora)
    perfil, criado, ambiguo, candidatos = resolver_contato(conexao, pedido, agora, contato_id_forcado)
    pedidos.gravar_resolucao(conexao, pedido_id, perfil.id if perfil is not None else None, criado, ambiguo)
    conexao.commit()

    resultado = ResultadoPedido(
        pedido_id=pedido_id,
        pedido=pedido,
        perfil=perfil,
        contato_criado=criado,
        contato_ambiguo=ambiguo,
        candidatos=candidatos,
    )
    _localizar_na_rede(cliente_llm, conexao, resultado, agora, navegacao, trocar_perfil)
    return resultado


def _localizar_na_rede(
    cliente_llm: ClientePedido,
    conexao: sqlite3.Connection,
    resultado: ResultadoPedido,
    agora: str,
    navegacao: localizacao_mod.ContextoNavegacao | None,
    trocar_perfil: bool,
) -> None:
    """Brief 037: acha a pessoa nas redes do usuário. Link no pedido grava direto; contato que já tem
    rede gravada não é procurado de novo (a menos que o usuário peça para trocar)."""
    perfil = resultado.perfil
    pedido = resultado.pedido
    if perfil is None or perfil.id is None or not pedido.pessoa_nome:
        return

    link = pedido.pessoa_pistas.get("link_rede_social")
    if link:
        resultado.link_gravado = localizacao_mod.gravar_link_do_pedido(
            conexao, perfil.id, link, agora, substituir=trocar_perfil
        )
        if resultado.link_gravado is not None:
            return
    if navegacao is None:
        return
    if redes_sociais.listar_por_perfil(conexao, perfil.id) and not trocar_perfil:
        return
    resultado.localizacao = localizacao_mod.localizar(conexao, cliente_llm, pedido, navegacao, agora)
