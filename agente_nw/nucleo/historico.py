from __future__ import annotations

import json
import sqlite3

from agente_nw.nucleo.database.queries import consulta_contato as queries
from agente_nw.nucleo.modelos.consulta_contato import ConsultaContato

LIMITE_PADRAO = 5


def _formatar_contexto(contexto_json: str) -> str:
    try:
        dados = json.loads(contexto_json)
    except json.JSONDecodeError:
        return contexto_json
    if not isinstance(dados, dict):
        return contexto_json
    partes = [f"{chave}: {valor}" for chave, valor in dados.items() if valor not in (None, "", [], {})]
    return "; ".join(partes) if partes else "(sem detalhes)"


def _formatar_assuntos(assuntos_entregues_json: str) -> str:
    try:
        dados = json.loads(assuntos_entregues_json)
    except json.JSONDecodeError:
        return "(menu ilegível)"
    if not isinstance(dados, list):
        return "(menu ilegível)"
    titulos: list[str] = []
    for item in dados:
        if isinstance(item, dict):
            titulo = item.get("titulo") or item.get("titulo_gerado")
            if isinstance(titulo, str) and titulo:
                titulos.append(titulo)
    if not titulos:
        return f"{len(dados)} assunto(s) entregue(s)"
    return " · ".join(titulos)


def _formatar_uma(consulta: ConsultaContato) -> str:
    data = consulta.criado_em[:10]
    linhas = [f"[{data}] contexto: {_formatar_contexto(consulta.contexto_json)}"]
    if consulta.resumo_redes_sociais:
        linhas.append(f"  leitura de rede social: {consulta.resumo_redes_sociais}")
    linhas.append(f"  entregues: {_formatar_assuntos(consulta.assuntos_entregues_json)}")
    return "\n".join(linhas)


def formatar(consultas: list[ConsultaContato]) -> str:
    if not consultas:
        return ""
    return "\n".join(_formatar_uma(c) for c in consultas)


def historico_recente_para_prompt(
    conexao: sqlite3.Connection, perfil_id: int, limite: int = LIMITE_PADRAO
) -> str:
    return formatar(queries.listar_por_perfil(conexao, perfil_id, limite))
