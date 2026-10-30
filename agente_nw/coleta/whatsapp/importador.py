"""Importa uma conversa já lida (`leitor.ConversaWhatsapp`) para o banco e enfileira os blocos do
contato para a extração de fatos (brief 061)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from agente_nw.coleta.whatsapp.leitor import ConversaWhatsapp
from agente_nw.nucleo.database.queries import conversa as conversa_q
from agente_nw.nucleo.database.queries import fila_extracao
from agente_nw.nucleo.modelos.configuracao import WhatsappLimiares

_ORIGEM_PREFIXO = "whatsapp:"


@dataclass(frozen=True)
class ResumoImportacao:
    novas: int
    repetidas: int


def importar(
    conexao: sqlite3.Connection,
    perfil_id: int,
    conversa: ConversaWhatsapp,
    nome_usuario: str,
    agora: str,
) -> ResumoImportacao:
    """Grava as mensagens; `nome_usuario` diz qual participante é "você" (o resto vira "contato").
    Mensagem já gravada (mesmo hash) não duplica — conta como "já estava"."""
    novas = repetidas = 0
    for mensagem in conversa.mensagens:
        autor = "usuario" if mensagem.autor == nome_usuario else "contato"
        gravou = conversa_q.inserir_mensagem(
            conexao, perfil_id, autor, mensagem.quando.isoformat(), mensagem.texto, agora
        )
        novas += gravou
        repetidas += not gravou
    conexao.commit()
    return ResumoImportacao(novas, repetidas)


def enfileirar_extracao(
    conexao: sqlite3.Connection, perfil_id: int, limiares: WhatsappLimiares, agora: str
) -> int:
    """Enfileira (`fila_extracao`, origem `whatsapp:AAAA-MM`) os blocos de meses ainda não extraídos.
    Devolve quantos blocos novos entraram na fila."""
    ja_extraidos = conversa_q.meses_ja_extraidos(conexao, perfil_id)
    enfileirados = 0
    for mes, blocos in conversa_q.blocos_por_mes(
        conexao, perfil_id, limiares.maximo_caracteres_bloco, limiares.meses_extraidos
    ):
        if mes in ja_extraidos:
            continue
        for bloco in blocos:
            fila_extracao.inserir(conexao, perfil_id, bloco, f"{_ORIGEM_PREFIXO}{mes}", agora)
            enfileirados += 1
    conexao.commit()
    return enfileirados
