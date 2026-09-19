from __future__ import annotations

import json
import sqlite3
import struct

import sqlite_vec

from agente_nw.nucleo.modelos.perfil import Perfil
from agente_nw.nucleo.vetores import centroide as calcular_media_ponderada

_COLUNAS = (
    "id, tipo, nome, apelido, email, telefone, empresa, cargo, setor, cidade, naturalidade, "
    "linguas, formacao, tem_filhos, faixa_etaria, notas, ativo, gerar_agora, ultima_coleta, "
    "criado_em, atualizado_em"
)


def _para_perfil(linha: sqlite3.Row) -> Perfil:
    return Perfil(
        id=linha["id"],
        tipo=linha["tipo"],
        nome=linha["nome"],
        apelido=linha["apelido"],
        email=linha["email"],
        telefone=linha["telefone"],
        empresa=linha["empresa"],
        cargo=linha["cargo"],
        setor=linha["setor"],
        cidade=linha["cidade"],
        naturalidade=linha["naturalidade"],
        linguas=json.loads(linha["linguas"]),
        formacao=linha["formacao"],
        tem_filhos=bool(linha["tem_filhos"]) if linha["tem_filhos"] is not None else None,
        faixa_etaria=linha["faixa_etaria"],
        notas=linha["notas"],
        ativo=bool(linha["ativo"]),
        gerar_agora=bool(linha["gerar_agora"]),
        ultima_coleta=linha["ultima_coleta"],
        criado_em=linha["criado_em"],
        atualizado_em=linha["atualizado_em"],
    )


def obter_usuario(conexao: sqlite3.Connection) -> Perfil | None:
    linha = conexao.execute(f"SELECT {_COLUNAS} FROM perfil WHERE tipo = 'usuario'").fetchone()
    return _para_perfil(linha) if linha is not None else None


def obter_por_id(conexao: sqlite3.Connection, perfil_id: int) -> Perfil | None:
    linha = conexao.execute(f"SELECT {_COLUNAS} FROM perfil WHERE id = ?", (perfil_id,)).fetchone()
    return _para_perfil(linha) if linha is not None else None


def obter_por_telefone_ou_email(
    conexao: sqlite3.Connection, telefone: str | None, email: str | None
) -> Perfil | None:
    if telefone is None and email is None:
        return None
    linha = conexao.execute(
        f"SELECT {_COLUNAS} FROM perfil WHERE (telefone IS NOT NULL AND telefone = ?) "
        "OR (email IS NOT NULL AND email = ?)",
        (telefone, email),
    ).fetchone()
    return _para_perfil(linha) if linha is not None else None


def upsert_usuario(conexao: sqlite3.Connection, nome: str, agora: str) -> Perfil:
    existente = obter_usuario(conexao)
    if existente is None:
        conexao.execute(
            "INSERT INTO perfil (tipo, nome, linguas, ativo, gerar_agora, criado_em, atualizado_em) "
            "VALUES ('usuario', ?, '[]', 1, 0, ?, ?)",
            (nome, agora, agora),
        )
        usuario = obter_usuario(conexao)
        assert usuario is not None
        return usuario

    conexao.execute("UPDATE perfil SET nome = ?, atualizado_em = ? WHERE id = ?", (nome, agora, existente.id))
    usuario = obter_usuario(conexao)
    assert usuario is not None
    return usuario


def inserir_ou_atualizar_contato(
    conexao: sqlite3.Connection,
    nome: str,
    telefone: str | None,
    email: str | None,
    empresa: str | None,
    cargo: str | None,
    notas: str | None,
    agora: str,
) -> Perfil:
    existente = obter_por_telefone_ou_email(conexao, telefone, email)
    if existente is None:
        conexao.execute(
            "INSERT INTO perfil (tipo, nome, telefone, email, empresa, cargo, notas, linguas, "
            "ativo, gerar_agora, criado_em, atualizado_em) "
            "VALUES ('contato', ?, ?, ?, ?, ?, ?, '[]', 0, 0, ?, ?)",
            (nome, telefone, email, empresa, cargo, notas, agora, agora),
        )
        novo = obter_por_telefone_ou_email(conexao, telefone, email)
        assert novo is not None
        return novo

    conexao.execute(
        "UPDATE perfil SET nome = ?, empresa = ?, cargo = ?, notas = ?, atualizado_em = ? WHERE id = ?",
        (nome, empresa, cargo, notas, agora, existente.id),
    )
    atualizado = obter_por_telefone_ou_email(conexao, telefone, email)
    assert atualizado is not None
    return atualizado


def ativar(conexao: sqlite3.Connection, perfil_id: int) -> None:
    conexao.execute("UPDATE perfil SET ativo = 1 WHERE id = ?", (perfil_id,))


def listar_ativos(conexao: sqlite3.Connection) -> list[Perfil]:
    linhas = conexao.execute(
        f"SELECT {_COLUNAS} FROM perfil WHERE ativo = 1 AND tipo = 'contato' ORDER BY nome"
    ).fetchall()
    return [_para_perfil(linha) for linha in linhas]


_CAMPOS_GUIADOS = (
    "cidade",
    "naturalidade",
    "linguas",
    "formacao",
    "cargo",
    "setor",
    "empresa",
    "tem_filhos",
    "faixa_etaria",
)


def atualizar_campos_guiados(
    conexao: sqlite3.Connection, perfil_id: int, campos: dict[str, object], agora: str
) -> None:
    """Grava, um de cada vez, só os campos guiados presentes em ``campos`` —
    e só se estiverem vazios hoje. Nunca sobrescreve um valor já preenchido
    (o dado que a pessoa digitou é sempre mais confiável do que o inferido).

    ``linguas`` é tratado separado dos demais: a coluna nunca é NULL (default
    '[]' na migração), então "vazio" para ela é `linguas = '[]'`, não
    `IS NULL` como para as colunas escalares.
    """
    for campo, valor in campos.items():
        if campo not in _CAMPOS_GUIADOS or valor is None:
            continue

        if campo == "linguas":
            assert isinstance(valor, list)
            conexao.execute(
                "UPDATE perfil SET linguas = CASE WHEN linguas = '[]' THEN ? ELSE linguas END, "
                "atualizado_em = CASE WHEN linguas = '[]' THEN ? ELSE atualizado_em END "
                "WHERE id = ?",
                (json.dumps(valor, ensure_ascii=False), agora, perfil_id),
            )
            continue

        valor_coluna = int(valor) if campo == "tem_filhos" and isinstance(valor, bool) else valor
        conexao.execute(
            f"UPDATE perfil SET {campo} = COALESCE({campo}, ?), "  # noqa: S608 — campo vem de _CAMPOS_GUIADOS, allowlist fechada acima
            f"atualizado_em = CASE WHEN {campo} IS NULL THEN ? ELSE atualizado_em END "
            "WHERE id = ?",
            (valor_coluna, agora, perfil_id),
        )


def _desserializar(blob: bytes) -> list[float]:
    quantidade = len(blob) // 4
    return list(struct.unpack(f"<{quantidade}f", blob))


def calcular_centroide(
    conexao: sqlite3.Connection, perfil_id: int, peso_nivel: dict[str, float]
) -> list[float] | None:
    linhas = conexao.execute(
        "SELECT pt.peso, pt.nivel, vt.embedding AS embedding FROM perfil_tema pt "
        "JOIN vetor_tema vt ON vt.tema_id = pt.tema_id "
        "WHERE pt.perfil_id = ? AND pt.confirmado = 1",
        (perfil_id,),
    ).fetchall()
    if not linhas:
        return None

    vetores: list[list[float]] = []
    pesos: list[float] = []
    for linha in linhas:
        peso_do_nivel = peso_nivel[linha["nivel"]] if linha["nivel"] is not None else 1.0
        vetores.append(_desserializar(linha["embedding"]))
        pesos.append(linha["peso"] * peso_do_nivel)

    return calcular_media_ponderada(vetores, pesos)


def gravar_centroide(conexao: sqlite3.Connection, perfil_id: int, centroide: list[float]) -> None:
    vetor = sqlite_vec.serialize_float32(centroide)
    conexao.execute("DELETE FROM vetor_perfil WHERE perfil_id = ?", (perfil_id,))
    conexao.execute("INSERT INTO vetor_perfil (perfil_id, centroide) VALUES (?, ?)", (perfil_id, vetor))


def obter_centroide(conexao: sqlite3.Connection, perfil_id: int) -> list[float] | None:
    linha = conexao.execute("SELECT centroide FROM vetor_perfil WHERE perfil_id = ?", (perfil_id,)).fetchone()
    return _desserializar(linha["centroide"]) if linha is not None else None
