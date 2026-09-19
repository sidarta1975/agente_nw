from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Protocol, TypeVar

from pydantic import BaseModel

from agente_nw.nucleo.database.queries import assunto_contato, assuntos, fila_revisao, perfil_tema, perfis
from agente_nw.nucleo.llm import FalhaJsonInvalido
from agente_nw.nucleo.modelos.assunto import Assunto
from agente_nw.nucleo.modelos.assunto_contato import AssuntoContato
from agente_nw.nucleo.modelos.configuracao import Limiares
from agente_nw.nucleo.modelos.cruzamento import RespostaCruzarPorQue
from agente_nw.nucleo.prompts import cruzar_por_que
from agente_nw.nucleo.relevancia import candidatos
from agente_nw.nucleo.relevancia.pontuacao import Avaliacao, avaliar

_EsquemaT = TypeVar("_EsquemaT", bound=BaseModel)
_MAX_TENTATIVAS = 2


class ClienteCruzamento(Protocol):
    def gerar_json(self, tarefa_nome: str, prompt: str, esquema: type[_EsquemaT]) -> _EsquemaT: ...


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
