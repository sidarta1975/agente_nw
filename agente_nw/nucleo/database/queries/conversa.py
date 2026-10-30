"""Conversas do WhatsApp importadas sobre um contato (brief 061)."""

from __future__ import annotations

import hashlib
import re
import sqlite3
from dataclasses import dataclass

_ESPACOS = re.compile(r"\s+")


@dataclass(frozen=True)
class MensagemGravada:
    id: int
    perfil_id: int
    autor: str  # "contato" ou "usuario"
    enviada_em: str
    texto: str


def calcular_hash(autor: str, enviada_em: str, texto: str) -> str:
    """autor + data/hora + texto sem espaços repetidos: reenviar a mesma exportação, ou uma mais nova
    que repete mensagens antigas, não duplica nada (migração 015)."""
    normalizado = _ESPACOS.sub(" ", texto).strip()
    return hashlib.sha256(f"{autor}|{enviada_em}|{normalizado}".encode()).hexdigest()


def inserir_mensagem(
    conexao: sqlite3.Connection, perfil_id: int, autor: str, enviada_em: str, texto: str, agora: str
) -> bool:
    """Grava a mensagem; devolve `False` sem gravar nada se já existia (mesmo hash)."""
    hash_ = calcular_hash(autor, enviada_em, texto)
    cursor = conexao.execute(
        "INSERT OR IGNORE INTO conversa_mensagem (perfil_id, autor, enviada_em, texto, hash, importada_em) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (perfil_id, autor, enviada_em, texto, hash_, agora),
    )
    return cursor.rowcount > 0


def ultimas_trocas(conexao: sqlite3.Connection, perfil_id: int, limite: int, nome_contato: str) -> list[str]:
    """As últimas `limite` mensagens trocadas, em ordem cronológica, formatadas "você: texto" / "Nome:
    texto" (brief 061: tom da relação na redação)."""
    linhas = conexao.execute(
        "SELECT autor, texto FROM conversa_mensagem WHERE perfil_id = ? ORDER BY enviada_em DESC LIMIT ?",
        (perfil_id, limite),
    ).fetchall()
    mensagens = list(reversed(linhas))
    return [
        f"{'você' if linha['autor'] == 'usuario' else nome_contato}: {linha['texto']}" for linha in mensagens
    ]


def meses_ja_extraidos(conexao: sqlite3.Connection, perfil_id: int) -> set[str]:
    """Meses (`AAAA-MM`) que já entraram na fila de extração para este contato."""
    linhas = conexao.execute(
        "SELECT DISTINCT origem FROM fila_extracao WHERE perfil_id = ? AND origem LIKE 'whatsapp:%'",
        (perfil_id,),
    ).fetchall()
    return {str(linha["origem"]).removeprefix("whatsapp:") for linha in linhas}


def _em_blocos(textos: list[str], maximo_caracteres: int) -> list[str]:
    blocos: list[str] = []
    atual: list[str] = []
    tamanho = 0
    for texto in textos:
        if atual and tamanho + len(texto) + 1 > maximo_caracteres:
            blocos.append("\n".join(atual))
            atual, tamanho = [], 0
        atual.append(texto)
        tamanho += len(texto) + 1
    if atual:
        blocos.append("\n".join(atual))
    return blocos


def blocos_por_mes(
    conexao: sqlite3.Connection, perfil_id: int, maximo_caracteres: int, meses_extraidos: int
) -> list[tuple[str, list[str]]]:
    """Mensagens **do contato** (nunca as do usuário), agrupadas por mês (`AAAA-MM`), do mais recente
    para o mais antigo, até `meses_extraidos` meses; cada mês em blocos de até `maximo_caracteres`
    caracteres (brief 061)."""
    linhas = conexao.execute(
        "SELECT enviada_em, texto FROM conversa_mensagem WHERE perfil_id = ? AND autor = 'contato' "
        "ORDER BY enviada_em",
        (perfil_id,),
    ).fetchall()
    por_mes: dict[str, list[str]] = {}
    for linha in linhas:
        mes = str(linha["enviada_em"])[:7]
        por_mes.setdefault(mes, []).append(str(linha["texto"]))

    return [
        (mes, _em_blocos(por_mes[mes], maximo_caracteres))
        for mes in sorted(por_mes, reverse=True)[:meses_extraidos]
    ]
