from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from typing import Protocol

from agente_nw.nucleo.database.queries import assuntos, fila_revisao, itens
from agente_nw.nucleo.llm import FalhaJsonInvalido
from agente_nw.nucleo.modelos.cartao import RespostaCartao
from agente_nw.nucleo.prompts import cartao as prompt_cartao

_MAX_ITENS_CARTAO = 5
_MAX_TENTATIVAS = 2
_TRUNCAMENTO_TRECHO = 300


class ClienteCartao(Protocol):
    def gerar_json(self, tarefa_nome: str, prompt: str, esquema: type[RespostaCartao]) -> RespostaCartao: ...


def _linha_tem_numero_sem_fonte(linha: str) -> bool:
    tem_digito = any(caractere.isdigit() for caractere in linha)
    if not tem_digito:
        return False
    return "(" not in linha or ")" not in linha


def _cartao_valido(resumo: str) -> bool:
    return not any(_linha_tem_numero_sem_fonte(linha) for linha in resumo.split("\n"))


def gerar_cartao(cliente_llm: ClienteCartao, conexao: sqlite3.Connection, assunto_id: int) -> str | None:
    assunto = assuntos.obter_por_id(conexao, assunto_id)
    if assunto is None:
        raise ValueError(f"assunto {assunto_id} não existe")

    itens_do_assunto = itens.listar_por_assunto(conexao, assunto_id)
    recentes = itens_do_assunto[-_MAX_ITENS_CARTAO:]
    itens_resumidos = [
        (ic.item.titulo, ic.dominio, (ic.item.texto or "")[:_TRUNCAMENTO_TRECHO]) for ic in recentes
    ]
    titulo = assunto.titulo_gerado or "(sem título)"
    prompt = prompt_cartao.construir_prompt(titulo, itens_resumidos)

    for _tentativa in range(_MAX_TENTATIVAS):
        try:
            resposta = cliente_llm.gerar_json("cartao", prompt, RespostaCartao)
        except FalhaJsonInvalido:
            continue
        if _cartao_valido(resposta.resumo):
            assuntos.gravar_cartao(conexao, assunto_id, resposta.resumo)
            conexao.commit()
            return resposta.resumo

    agora = datetime.now(UTC).isoformat()
    fila_revisao.inserir(
        conexao,
        tarefa="cartao",
        entrada=str(assunto_id),
        erro="número sem fonte entre parênteses",
        agora=agora,
    )
    conexao.commit()
    return None
