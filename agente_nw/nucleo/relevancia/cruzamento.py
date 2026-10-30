from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from typing import Protocol, TypeVar

from pydantic import BaseModel

from agente_nw.nucleo.database.queries import assunto_contato, assuntos, fila_revisao, perfil_tema, perfis
from agente_nw.nucleo.llm import FalhaJsonInvalido
from agente_nw.nucleo.modelos.assunto import Assunto
from agente_nw.nucleo.modelos.assunto_contato import AssuntoContato
from agente_nw.nucleo.modelos.configuracao import Limiares
from agente_nw.nucleo.modelos.contexto_consulta import ContextoConsulta
from agente_nw.nucleo.modelos.cruzamento import (
    AvaliacaoRelacaoObjetivo,
    RespostaAvaliarRelacaoObjetivo,
    RespostaCruzarPorQue,
)
from agente_nw.nucleo.modelos.perfil import Perfil
from agente_nw.nucleo.prompts import avaliar_relacao_objetivo, cruzar_por_que
from agente_nw.nucleo.relevancia import candidatos
from agente_nw.nucleo.relevancia.pontuacao import Avaliacao, avaliar, avaliar_por_consulta

_MOTIVO_GATE = "sem relação com o objetivo (juízo do modelo)"
_SEM_RELACAO_COM_O_OBJETIVO = "nenhum candidato com relação ao objetivo (juízo do modelo)"

_EsquemaT = TypeVar("_EsquemaT", bound=BaseModel)
_MAX_TENTATIVAS = 2


class ClienteCruzamento(Protocol):
    def gerar_json(self, tarefa_nome: str, prompt: str, esquema: type[_EsquemaT]) -> _EsquemaT: ...


class ClienteCruzamentoConsulta(ClienteCruzamento, Protocol):
    def embeddar(self, textos: list[str]) -> list[list[float]]: ...


_MAXIMO_INTERESSA_NO_APOIO = 5


# O "por quê" recebe só o título do assunto e os temas: qualquer posição do contato ("ele apoia X") é
# invenção do modelo. Frase assim é trocada por uma que liga o assunto ao objetivo do usuário.
_ATRIBUICAO = re.compile(
    r"\b(ele|ela)\s+(apoia|apoiam|defende|vota|votou|torce|simpatiza|milita|acredita|odeia|ama|critica"
    r"|é\s+(contra|a\s+favor|de\s+\w+|eleitor|apoiador|partidári))",
    re.IGNORECASE,
)


def sem_atribuicao(por_que: str, contexto: ContextoConsulta) -> str:
    if _ATRIBUICAO.search(por_que) is None:
        return por_que
    return f"o assunto se liga ao que você quer: {contexto.objetivo}"


@dataclass
class ResumoContato:
    perfil_id: int
    sem_assunto: bool = False
    motivo: str | None = None
    candidatos: int = 0
    conectores: int = 0
    viaveis: int = 0
    descartados: int = 0
    erros: int = 0


def _chamar_cruzar_por_que(
    cliente_llm: ClienteCruzamento,
    conexao: sqlite3.Connection,
    prompt: str,
    quantidade_esperada: int,
    perfil_id: int,
    agora: str,
) -> list[str] | None:
    ultimo_erro = ""
    for _tentativa in range(_MAX_TENTATIVAS):
        try:
            resposta = cliente_llm.gerar_json("cruzar_por_que", prompt, RespostaCruzarPorQue)
        except FalhaJsonInvalido as erro:
            ultimo_erro = str(erro)
            continue
        if len(resposta.por_que) == quantidade_esperada:
            return resposta.por_que
        ultimo_erro = f"esperado {quantidade_esperada} itens em por_que, veio {len(resposta.por_que)}"

    fila_revisao.inserir(
        conexao, tarefa="cruzar_por_que", entrada=str(perfil_id), erro=ultimo_erro, agora=agora
    )
    return None


def _ficha_para_gate(contato: Perfil) -> str:
    partes = (("cargo", contato.cargo), ("empresa", contato.empresa), ("cidade", contato.cidade))
    return ", ".join(f"{rotulo}: {valor}" for rotulo, valor in partes if valor)


def _chamar_gate_objetivo(
    cliente_llm: ClienteCruzamento,
    conexao: sqlite3.Connection,
    prompt: str,
    quantidade_esperada: int,
    perfil_id: int,
    agora: str,
) -> list[AvaliacaoRelacaoObjetivo] | None:
    ultimo_erro = ""
    for _tentativa in range(_MAX_TENTATIVAS):
        try:
            resposta = cliente_llm.gerar_json(
                "avaliar_relacao_objetivo", prompt, RespostaAvaliarRelacaoObjetivo
            )
        except FalhaJsonInvalido as erro:
            ultimo_erro = str(erro)
            continue
        if len(resposta.avaliacoes) == quantidade_esperada:
            return resposta.avaliacoes
        ultimo_erro = f"esperado {quantidade_esperada} itens em avaliacoes, veio {len(resposta.avaliacoes)}"

    fila_revisao.inserir(
        conexao, tarefa="avaliar_relacao_objetivo", entrada=str(perfil_id), erro=ultimo_erro, agora=agora
    )
    return None


def _aplicar_gate_objetivo(
    cliente_llm: ClienteCruzamento,
    conexao: sqlite3.Connection,
    perfil_id: int,
    contexto: ContextoConsulta,
    contato: Perfil,
    demais: list[tuple[Assunto, Avaliacao]],
    data: str,
    agora: str,
    resumo: ResumoContato,
) -> list[tuple[Assunto, Avaliacao]]:
    """Julgamento sim/não do modelo: só a notícia com relação real com o objetivo do pedido continua
    `conector` (brief 049). Resposta de tamanho errado cai para `fila_revisao` e não filtra nada — o
    pedido segue como hoje, sem o gate."""
    candidatos_gate = [(assunto.titulo_gerado or "", assunto.resumo_cartao) for assunto, _ in demais]
    prompt = avaliar_relacao_objetivo.construir_prompt(
        contexto.objetivo, contexto.livre, _ficha_para_gate(contato), candidatos_gate
    )
    avaliacoes_gate = _chamar_gate_objetivo(cliente_llm, conexao, prompt, len(demais), perfil_id, agora)
    if avaliacoes_gate is None:
        resumo.erros += 1
        return demais

    mantidos: list[tuple[Assunto, Avaliacao]] = []
    for (assunto, avaliacao), avaliacao_gate in zip(demais, avaliacoes_gate, strict=True):
        if avaliacao_gate.relaciona:
            mantidos.append((assunto, avaliacao))
            continue
        assert assunto.id is not None
        assunto_contato.inserir(
            conexao,
            AssuntoContato(
                assunto_id=assunto.id,
                perfil_id=perfil_id,
                gerado_em=data,
                tipo="fora_do_dominio",
                aderencia_contato=avaliacao.aderencia_contato,
                aderencia_usuario=avaliacao.aderencia_usuario,
                conversavel=avaliacao.conversavel,
                score=avaliacao.score,
                status="descartado",
                motivo=_MOTIVO_GATE,
                aderencia_consulta=avaliacao.aderencia_consulta,
            ),
        )
        resumo.descartados += 1
    conexao.commit()
    return mantidos


def cruzar_contato(
    cliente_llm: ClienteCruzamento,
    conexao: sqlite3.Connection,
    perfil_id: int,
    limiares: Limiares,
    agora: str,
) -> ResumoContato:
    resumo = ResumoContato(perfil_id=perfil_id)
    data = agora[:10]

    centroide_contato = perfis.calcular_centroide(conexao, perfil_id, limiares.conector.peso_nivel)
    if centroide_contato is None:
        resumo.sem_assunto = True
        resumo.motivo = "contato sem tema confirmado"
        return resumo
    perfis.gravar_centroide(conexao, perfil_id, centroide_contato)
    conexao.commit()

    selecionados = candidatos.selecionar(
        conexao,
        perfil_id,
        centroide_contato,
        limiares.qualificacao.substancial_minimo,
        limiares.qualificacao.conversavel_minimo,
        limiares.conector.candidatos_por_contato,
    )
    resumo.candidatos = len(selecionados)
    if not selecionados:
        resumo.sem_assunto = True
        resumo.motivo = "nenhum assunto qualificado disponível"
        return resumo

    usuario = perfis.obter_usuario(conexao)
    assert usuario is not None and usuario.id is not None
    temas_usuario = perfil_tema.listar_confirmados_com_embedding(conexao, usuario.id)

    avaliacoes: list[tuple[Assunto, Avaliacao]] = []
    for assunto in selecionados:
        assert assunto.id is not None
        centroide_assunto = assuntos.obter_centroide(conexao, assunto.id)
        assert centroide_assunto is not None
        assert assunto.conversavel is not None
        avaliacao = avaliar(
            centroide_assunto, centroide_contato, temas_usuario, assunto.conversavel, limiares.conector
        )
        avaliacoes.append((assunto, avaliacao))

    for assunto, avaliacao in avaliacoes:
        if avaliacao.tipo != "fora_do_dominio":
            continue
        assert assunto.id is not None
        registro = AssuntoContato(
            assunto_id=assunto.id,
            perfil_id=perfil_id,
            gerado_em=data,
            tipo="fora_do_dominio",
            aderencia_contato=avaliacao.aderencia_contato,
            aderencia_usuario=avaliacao.aderencia_usuario,
            conversavel=avaliacao.conversavel,
            score=avaliacao.score,
            status="descartado",
            motivo="fora do domínio",
        )
        assunto_contato.inserir(conexao, registro)
        resumo.descartados += 1
    conexao.commit()

    demais = [(a, av) for a, av in avaliacoes if av.tipo != "fora_do_dominio"]
    if not demais:
        resumo.sem_assunto = True
        resumo.motivo = "nenhum candidato passou do piso"
        return resumo

    ordem_tipo = {"conector": 0, "viavel_com_esforco": 1}
    demais.sort(key=lambda par: (ordem_tipo[par[1].tipo], -par[1].score))
    selecionados_para_menu = demais[: limiares.conector.itens_no_menu]

    contato = perfis.obter_por_id(conexao, perfil_id)
    assert contato is not None
    apelido_ou_nome = contato.apelido or contato.nome
    temas_contato = [nome for nome, _, _ in perfil_tema.listar_confirmados_com_embedding(conexao, perfil_id)]
    temas_usuario_com_nivel = [(nome, nivel) for nome, nivel, _ in temas_usuario]
    assuntos_para_prompt: list[tuple[str, str, str | None]] = [
        (assunto.titulo_gerado or "", avaliacao.tipo, avaliacao.ponto_de_apoio)
        for assunto, avaliacao in selecionados_para_menu
    ]

    prompt = cruzar_por_que.construir_prompt(
        apelido_ou_nome, temas_contato, temas_usuario_com_nivel, assuntos_para_prompt
    )
    por_ques = _chamar_cruzar_por_que(
        cliente_llm, conexao, prompt, len(selecionados_para_menu), perfil_id, agora
    )
    if por_ques is None:
        resumo.erros += 1

    for indice, (assunto, avaliacao) in enumerate(selecionados_para_menu):
        assert assunto.id is not None
        registro = AssuntoContato(
            assunto_id=assunto.id,
            perfil_id=perfil_id,
            gerado_em=data,
            tipo=avaliacao.tipo,
            aderencia_contato=avaliacao.aderencia_contato,
            aderencia_usuario=avaliacao.aderencia_usuario,
            conversavel=avaliacao.conversavel,
            score=avaliacao.score,
            por_que=por_ques[indice] if por_ques is not None else None,
            status="novo",
        )
        assunto_contato.inserir(conexao, registro)
        if avaliacao.tipo == "conector":
            resumo.conectores += 1
        else:
            resumo.viaveis += 1
    conexao.commit()

    return resumo


def cruzar_contato_por_consulta(
    cliente_llm: ClienteCruzamentoConsulta,
    conexao: sqlite3.Connection,
    perfil_id: int,
    contexto: ContextoConsulta,
    centroide_consulta: list[float],
    limiares: Limiares,
    agora: str,
) -> ResumoContato:
    """Cruzamento em que o contexto da consulta é o sinal principal (brief 034).

    Tags, fatos do contato e temas do usuário enriquecem quando existem e nunca bloqueiam."""
    resumo = ResumoContato(perfil_id=perfil_id)
    data = agora[:10]

    # Reconsulta no mesmo dia substitui o menu: só o que o usuário decidiu (usado, nao_serve) permanece.
    assunto_contato.apagar_nao_decididos_do_dia(conexao, perfil_id, data)
    conexao.commit()

    centroide_contato = perfis.calcular_centroide_do_contato(conexao, perfil_id, cliente_llm)
    if centroide_contato is not None:
        perfis.gravar_centroide(conexao, perfil_id, centroide_contato)
        conexao.commit()

    restantes, evitados = candidatos.selecionar_por_consulta(
        conexao,
        perfil_id,
        centroide_consulta,
        centroide_contato,
        limiares.qualificacao.substancial_minimo,
        limiares.qualificacao.conversavel_minimo,
        limiares.conector.candidatos_por_contato,
        contexto.evitar,
        limiares.conector.consulta,
    )
    for assunto in evitados:
        assert assunto.id is not None
        assunto_contato.inserir(
            conexao,
            AssuntoContato(
                assunto_id=assunto.id,
                perfil_id=perfil_id,
                gerado_em=data,
                tipo="fora_do_dominio",
                aderencia_contato=0.0,
                aderencia_usuario=0.0,
                conversavel=assunto.conversavel or 0.0,
                score=0.0,
                status="descartado",
                motivo="evitado pelo contexto",
            ),
        )
        resumo.descartados += 1
    conexao.commit()

    resumo.candidatos = len(restantes)
    if not restantes:
        resumo.sem_assunto = True
        resumo.motivo = (
            "todos os candidatos foram evitados pelo contexto"
            if evitados
            else "nenhum assunto qualificado disponível"
        )
        return resumo

    usuario = perfis.obter_usuario(conexao)
    temas_usuario = (
        perfil_tema.listar_confirmados_com_embedding(conexao, usuario.id)
        if usuario is not None and usuario.id is not None
        else []
    )

    nomes_termos = [
        t for t in [contexto.assunto, *contexto.interessa[:_MAXIMO_INTERESSA_NO_APOIO]] if t.strip()
    ]
    termos_consulta = (
        list(zip(nomes_termos, cliente_llm.embeddar(nomes_termos), strict=True)) if nomes_termos else []
    )
    avaliacoes: list[tuple[Assunto, Avaliacao]] = []
    for assunto in restantes:
        assert assunto.id is not None
        centroide_assunto = assuntos.obter_centroide(conexao, assunto.id)
        assert centroide_assunto is not None
        assert assunto.conversavel is not None
        avaliacoes.append(
            (
                assunto,
                avaliar_por_consulta(
                    centroide_assunto,
                    centroide_consulta,
                    centroide_contato,
                    temas_usuario,
                    assunto.conversavel,
                    limiares.conector,
                    termos_consulta,
                ),
            )
        )

    # Na consulta só entra o que tem relação com o pedido ("conector"): contato e temas do usuário não
    # bastam, e entregar assunto sem relação com o objetivo seria inventar gancho.
    for assunto, avaliacao in avaliacoes:
        if avaliacao.tipo == "conector":
            continue
        assert assunto.id is not None
        motivo = "pouca relação com o pedido"
        assunto_contato.inserir(
            conexao,
            AssuntoContato(
                assunto_id=assunto.id,
                perfil_id=perfil_id,
                gerado_em=data,
                tipo="fora_do_dominio",
                aderencia_contato=avaliacao.aderencia_contato,
                aderencia_usuario=avaliacao.aderencia_usuario,
                conversavel=avaliacao.conversavel,
                score=avaliacao.score,
                status="descartado",
                motivo=motivo,
                aderencia_consulta=avaliacao.aderencia_consulta,
            ),
        )
        resumo.descartados += 1
    conexao.commit()

    demais = [(a, av) for a, av in avaliacoes if av.tipo == "conector"]
    if not demais:
        resumo.sem_assunto = True
        resumo.motivo = "nenhum candidato passou do piso"
        return resumo

    contato = perfis.obter_por_id(conexao, perfil_id)
    assert contato is not None

    # Gate (brief 049): o piso por embedding já cortou o grosso; o modelo decide, candidato a
    # candidato, se a notícia tem relação real com o objetivo do pedido — o que o vetor não separa
    # ("eleição da OAB" de "política nacional", por exemplo).
    demais = _aplicar_gate_objetivo(
        cliente_llm, conexao, perfil_id, contexto, contato, demais, data, agora, resumo
    )
    if not demais:
        resumo.sem_assunto = True
        resumo.motivo = _SEM_RELACAO_COM_O_OBJETIVO
        return resumo

    ordem_tipo = {"conector": 0, "viavel_com_esforco": 1}
    demais.sort(key=lambda par: (ordem_tipo[par[1].tipo], -par[1].score))
    selecionados_para_menu = demais[: limiares.conector.itens_no_menu]

    apelido_ou_nome = contato.apelido or contato.nome
    # As tags são contextos fixos da relação (família, amigos, trabalho): vão para o texto, não para o
    # centroide, que vem do que o contato publicou.
    temas_contato = perfil_tema.listar_nomes_do_contato(conexao, perfil_id)
    temas_usuario_com_nivel = [(nome, nivel) for nome, nivel, _ in temas_usuario]
    assuntos_para_prompt: list[tuple[str, str, str | None]] = [
        (assunto.titulo_gerado or "", avaliacao.tipo, avaliacao.ponto_de_apoio)
        for assunto, avaliacao in selecionados_para_menu
    ]

    prompt = cruzar_por_que.construir_prompt(
        apelido_ou_nome, temas_contato, temas_usuario_com_nivel, assuntos_para_prompt, contexto
    )
    por_ques = _chamar_cruzar_por_que(
        cliente_llm, conexao, prompt, len(selecionados_para_menu), perfil_id, agora
    )
    if por_ques is None:
        resumo.erros += 1

    for indice, (assunto, avaliacao) in enumerate(selecionados_para_menu):
        assert assunto.id is not None
        assunto_contato.inserir(
            conexao,
            AssuntoContato(
                assunto_id=assunto.id,
                perfil_id=perfil_id,
                gerado_em=data,
                tipo=avaliacao.tipo,
                aderencia_contato=avaliacao.aderencia_contato,
                aderencia_usuario=avaliacao.aderencia_usuario,
                conversavel=avaliacao.conversavel,
                score=avaliacao.score,
                por_que=sem_atribuicao(por_ques[indice], contexto) if por_ques is not None else None,
                status="novo",
                aderencia_consulta=avaliacao.aderencia_consulta,
            ),
        )
        if avaliacao.tipo == "conector":
            resumo.conectores += 1
        else:
            resumo.viaveis += 1
    conexao.commit()

    return resumo
