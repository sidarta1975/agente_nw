from __future__ import annotations

import json
import re
import sqlite3
from datetime import UTC, datetime, timedelta
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
from agente_nw.nucleo.modelos.fato import Fato
from agente_nw.nucleo.modelos.pedido import PedidoExtraido
from agente_nw.nucleo.modelos.perfil import Perfil
from agente_nw.nucleo.modelos.redacao import (
    Gancho,
    LinkNoticia,
    Redacao,
    RespostaRedacao,
    validar_ganchos,
)
from agente_nw.nucleo.prompts import redigir_ganchos as prompt_mod
from agente_nw.nucleo.prompts.redigir_ganchos import AssuntoParaRedacao, EntradaRedacao
from agente_nw.nucleo.vetores import cosseno

_EsquemaT = TypeVar("_EsquemaT", bound=BaseModel)

_FATOS_NO_PROMPT = 10
_FATOS_CANDIDATOS = 40
_TRECHO_DO_FATO_NO_PROMPT = 600  # o fato fica inteiro no banco; o prompt leva o começo
_FATOS_RECENTES_GARANTIDOS = 4
_CONSULTAS_NO_HISTORICO = 3
_MANCHETES_POR_ASSUNTO = 3
_DIAS_POR_MES = 30
_MARCA_ANTIGO = "[antigo]"
_MARCA_DE_IMAGEM = "[de imagem]"
# Lembrança do Facebook ("Há 4 anos", "Veja suas lembranças"): a data do fato é a da leitura.
_LEMBRANCA = re.compile(r"\bh[aá]\s+\d+\s+anos?\b|\blembran[cç]as\b", re.IGNORECASE)


class ClienteRedacao(Protocol):
    def gerar_json(self, tarefa_nome: str, prompt: str, esquema: type[_EsquemaT]) -> _EsquemaT: ...


def _assunto_para_redacao(conexao: sqlite3.Connection, item: ItemMenu) -> AssuntoParaRedacao:
    assunto = assuntos_q.obter_por_id(conexao, item.assunto_id)
    manchetes: list[str] = []
    links: list[LinkNoticia] = []
    for com_dominio in itens_q.listar_por_assunto(conexao, item.assunto_id)[:_MANCHETES_POR_ASSUNTO]:
        data = (com_dominio.item.publicado_em or "")[:10]
        origem = f"{com_dominio.dominio}, {data}" if data else com_dominio.dominio
        manchetes.append(f"{origem}: {com_dominio.item.titulo}")
        links.append(
            LinkNoticia(
                veiculo=com_dominio.dominio,
                titulo=com_dominio.item.titulo,
                url=com_dominio.item.url_canonica,
                texto=com_dominio.item.texto,
            )
        )
    return AssuntoParaRedacao(
        assunto_id=item.assunto_id,
        titulo=item.titulo,
        por_que=item.por_que,
        resumo=assunto.resumo_cartao if assunto is not None else None,
        manchetes=manchetes,
        links=links,
    )


def _ficha(contato: Perfil) -> list[str]:
    partes = (("cargo", contato.cargo), ("empresa", contato.empresa), ("cidade", contato.cidade))
    return [f"{rotulo}: {valor}" for rotulo, valor in partes if valor]


def _escolher_fatos(cliente_llm: ClienteRedacao, candidatos: list[Fato], consulta: str) -> list[Fato]:
    """Os 4 fatos mais recentes e, entre os demais, os que mais se parecem com a consulta e os assuntos.
    Sem como medir a semelhança (cliente sem embeddings ou falha), ficam os mais recentes."""
    if len(candidatos) <= _FATOS_NO_PROMPT:
        return candidatos
    garantidos = candidatos[:_FATOS_RECENTES_GARANTIDOS]
    resto = candidatos[_FATOS_RECENTES_GARANTIDOS:]
    vagas = _FATOS_NO_PROMPT - len(garantidos)
    embeddar = getattr(cliente_llm, "embeddar", None)
    if embeddar is None:
        return candidatos[:_FATOS_NO_PROMPT]
    try:
        vetores = embeddar([consulta, *(f.conteudo[:_TRECHO_DO_FATO_NO_PROMPT] for f in resto)])
    except Exception:
        return candidatos[:_FATOS_NO_PROMPT]
    alvo, vetores_resto = vetores[0], vetores[1:]
    ordem = sorted(range(len(resto)), key=lambda i: -cosseno(alvo, vetores_resto[i]))
    return [*garantidos, *(resto[i] for i in sorted(ordem[:vagas]))]


def _e_antigo(fato: Fato, data: str, meses_fato_antigo: int, hoje: datetime) -> bool:
    if _LEMBRANCA.search(fato.conteudo):
        return True
    try:
        publicado = datetime.fromisoformat(data[:10]).replace(tzinfo=UTC)
    except ValueError:
        return False
    return hoje - publicado > timedelta(days=meses_fato_antigo * _DIAS_POR_MES)


def _fatos(
    conexao: sqlite3.Connection,
    perfil_id: int,
    cliente_llm: ClienteRedacao,
    consulta: str,
    meses_fato_antigo: int,
    hoje: datetime,
) -> list[str]:
    """Os fatos do prompt, um por linha. Fato antigo e fato lido de imagem levam marca: a redação não os
    afirma como posição atual da pessoa."""
    candidatos = fatos_q.listar_recentes(conexao, perfil_id, _FATOS_CANDIDATOS)
    linhas: list[str] = []
    for fato in _escolher_fatos(cliente_llm, candidatos, consulta):
        data = fato.data_do_fato or fato.registrado_em[:10]
        marcas = []
        if _e_antigo(fato, data, meses_fato_antigo, hoje):
            marcas.append(_MARCA_ANTIGO)
        if fato.tipo.startswith("imagem"):
            marcas.append(_MARCA_DE_IMAGEM)
        sufixo = f" {' '.join(marcas)}" if marcas else ""
        linhas.append(f"{data[:10]} ({fato.tipo}){sufixo}: {fato.conteudo[:_TRECHO_DO_FATO_NO_PROMPT]}")
    return linhas


def _historico(conexao: sqlite3.Connection, perfil_id: int, consulta_id: int) -> list[str]:
    anteriores = [
        c
        for c in consulta_contato_q.listar_por_perfil(conexao, perfil_id, _CONSULTAS_NO_HISTORICO + 1)
        if c.id != consulta_id
    ][:_CONSULTAS_NO_HISTORICO]
    return [historico_mod.formatar_uma(c, conexao) for c in anteriores]


def _texto_da_consulta(pedido: PedidoExtraido, assuntos: list[ItemMenu]) -> str:
    return ". ".join([pedido.assunto_principal, *pedido.interessa, *(item.titulo for item in assuntos)])


def montar_entrada(
    conexao: sqlite3.Connection,
    cliente_llm: ClienteRedacao,
    pedido: PedidoExtraido,
    frase: str,
    resultado_consulta: ResultadoConsulta,
    contato: Perfil,
    usuario: Perfil,
    assuntos: list[ItemMenu],
    meses_fato_antigo: int = 12,
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
        fatos=_fatos(
            conexao,
            contato.id,
            cliente_llm,
            _texto_da_consulta(pedido, assuntos),
            meses_fato_antigo,
            datetime.now(UTC),
        ),
        cabecalho_rede=" · ".join(f"{rede}: {cabecalho}" for rede, cabecalho in cabecalhos) or None,
        pedido=pedido,
        frase=frase,
        historico=_historico(conexao, contato.id, resultado_consulta.consulta_id),
        assuntos=[_assunto_para_redacao(conexao, item) for item in assuntos],
        contexto_relacao=perfil_tema_q.listar_nomes_do_contato(conexao, contato.id),
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
    meses_fato_antigo: int = 12,
) -> Redacao:
    """Uma chamada ao modelo: sempre devolve a mensagem base (objetivo + pessoa + uma peculiaridade) e,
    havendo assunto ligado ao pedido, também os ganchos de notícia. Sem assunto o modelo é chamado do mesmo
    jeito (brief 047; reverte a regra do 038). Não grava nada: quem entrega chama `registrar`. Assuntos que
    o usuário já usou com esta pessoa saem antes do prompt."""
    del agora
    assert perfil.id is not None
    registro = pedido.registro
    usados = gancho_uso_q.assuntos_usados_do_perfil(conexao, perfil.id)
    disponiveis = [item for item in resultado_consulta.itens_menu if item.assunto_id not in usados]
    informativos: list[str] = []
    if not disponiveis:
        informativos.append(
            "Todos os assuntos selecionados já foram usados com esta pessoa; mensagem a partir do perfil."
            if resultado_consulta.itens_menu
            else "Sem notícia relevante agora; mensagem a partir do perfil."
        )

    entrada = montar_entrada(
        conexao,
        cliente_llm,
        pedido,
        frase,
        resultado_consulta,
        perfil,
        usuario,
        disponiveis,
        meses_fato_antigo,
    )
    if not entrada.fatos:
        informativos.append("Pouca informação sobre a pessoa; mensagem mais geral.")
    prompt = prompt_mod.construir_prompt(entrada, limite_tokens)
    validos = {item.assunto_id for item in disponiveis}
    resposta = cliente_llm.gerar_json("redigir_ganchos", prompt, RespostaRedacao)
    ganchos, motivos = _validar(resposta, pedido, validos, usados)
    if not any(g.e_base for g in ganchos):
        motivos.append('faltou a mensagem base ("assunto_id": null), que é obrigatória')
        # Segunda tentativa dizendo ao modelo o que foi recusado: sem ela, um excesso de palavras na
        # mensagem deixaria a pessoa sem a mensagem base.
        recusas = "\n".join(f"- {motivo}" for motivo in motivos)
        retorno = f"{prompt}\n\nA resposta anterior foi recusada. Refaça respeitando as regras:\n{recusas}\n"
        resposta = cliente_llm.gerar_json("redigir_ganchos", retorno, RespostaRedacao)
        ganchos, motivos = _validar(resposta, pedido, validos, usados)
        if not any(g.e_base for g in ganchos):
            motivos.append("o modelo não devolveu a mensagem base")
    links_por_assunto = {a.assunto_id: a.links for a in entrada.assuntos}
    ganchos = [
        g if g.assunto_id is None else g.model_copy(update={"links": links_por_assunto.get(g.assunto_id, [])})
        for g in ganchos
    ]
    aviso = _juntar_avisos([*informativos, resposta.aviso or "", *motivos])
    if not ganchos and aviso is None:
        aviso = "O modelo não devolveu nenhuma mensagem."
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
