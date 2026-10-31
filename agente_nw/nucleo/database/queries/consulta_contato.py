from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass

from agente_nw.nucleo.modelos.consulta_contato import ConsultaContato
from agente_nw.nucleo.texto import sem_acento_e_caixa

_COLUNAS = "id, perfil_id, criado_em, contexto_json, resumo_redes_sociais, assuntos_entregues_json"


def _para_consulta(linha: sqlite3.Row) -> ConsultaContato:
    return ConsultaContato(
        id=linha["id"],
        perfil_id=linha["perfil_id"],
        criado_em=linha["criado_em"],
        contexto_json=linha["contexto_json"],
        resumo_redes_sociais=linha["resumo_redes_sociais"],
        assuntos_entregues_json=linha["assuntos_entregues_json"],
    )


def inserir(
    conexao: sqlite3.Connection,
    perfil_id: int,
    criado_em: str,
    contexto_json: str,
    resumo_redes_sociais: str | None,
    assuntos_entregues_json: str,
) -> ConsultaContato:
    cursor = conexao.execute(
        "INSERT INTO consulta_contato "
        "(perfil_id, criado_em, contexto_json, resumo_redes_sociais, assuntos_entregues_json) "
        "VALUES (?, ?, ?, ?, ?)",
        (perfil_id, criado_em, contexto_json, resumo_redes_sociais, assuntos_entregues_json),
    )
    linha = conexao.execute(
        f"SELECT {_COLUNAS} FROM consulta_contato WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    assert linha is not None
    return _para_consulta(linha)


def listar_por_perfil(
    conexao: sqlite3.Connection, perfil_id: int, limite: int | None = None
) -> list[ConsultaContato]:
    if limite is None:
        linhas = conexao.execute(
            f"SELECT {_COLUNAS} FROM consulta_contato WHERE perfil_id = ? ORDER BY criado_em DESC, id DESC",
            (perfil_id,),
        ).fetchall()
    else:
        linhas = conexao.execute(
            f"SELECT {_COLUNAS} FROM consulta_contato WHERE perfil_id = ? "
            "ORDER BY criado_em DESC, id DESC LIMIT ?",
            (perfil_id, limite),
        ).fetchall()
    return [_para_consulta(linha) for linha in linhas]


@dataclass(frozen=True)
class MoldeParaRedacao:
    """Uma mensagem já redigida para outro contato, de contexto parecido (brief 048)."""

    mensagem: str
    bom: bool  # status 'usado': o usuário marcou que serviu
    comentario: str | None = None


def moldes_por_contexto(
    conexao: sqlite3.Connection,
    perfil_id_atual: int,
    objetivo_categoria: str,
    registro: str | None,
    cargo_atual: str | None,
    maximo: int,
) -> list[MoldeParaRedacao]:
    """Mensagens entregues a outro contato com o mesmo objetivo, o mesmo registro e cargo parecido —
    a tríade de contexto do brief 048. `nao_serve` nunca entra; `usado` vem primeiro, depois por
    recência. Sem cargo do contato atual não há "tipo de contato" para comparar: devolve vazio."""
    if not cargo_atual or not registro or maximo <= 0:
        return []
    cargo_normalizado = sem_acento_e_caixa(cargo_atual)
    linhas = conexao.execute(
        "SELECT g.gancho_json AS gancho_json, g.status AS status, g.comentario AS comentario, "
        "p.cargo AS cargo_fonte "
        "FROM gancho_uso g "
        "JOIN consulta_contato c ON c.id = g.consulta_id "
        "JOIN perfil p ON p.id = c.perfil_id "
        "WHERE c.perfil_id != ? AND g.status IN ('usado', 'entregue') "
        "AND json_extract(c.contexto_json, '$.objetivo_categoria') = ? "
        "AND json_extract(c.contexto_json, '$.registro') = ? "
        "ORDER BY (g.status = 'usado') DESC, c.criado_em DESC",
        (perfil_id_atual, objetivo_categoria, registro),
    ).fetchall()
    moldes: list[MoldeParaRedacao] = []
    for linha in linhas:
        if linha["cargo_fonte"] is None or sem_acento_e_caixa(linha["cargo_fonte"]) != cargo_normalizado:
            continue
        try:
            dados = json.loads(linha["gancho_json"])
        except json.JSONDecodeError:
            continue
        mensagem = dados.get("mensagem") if isinstance(dados, dict) else None
        if not isinstance(mensagem, str) or not mensagem.strip():
            continue
        moldes.append(
            MoldeParaRedacao(
                mensagem=mensagem, bom=linha["status"] == "usado", comentario=linha["comentario"]
            )
        )
        if len(moldes) >= maximo:
            break
    return moldes
