from __future__ import annotations

import json
import sqlite3
import struct

import sqlite_vec

from agente_nw.nucleo.modelos.assunto import Assunto, StatusAssunto
from agente_nw.nucleo.vetores import cosseno

_COLUNAS = (
    "id, titulo_gerado, primeiro_visto, ultimo_visto, n_itens, n_fontes_independentes, "
    "status, temas, substancial, conversavel, justificativa, resumo_cartao"
)


def _para_assunto(linha: sqlite3.Row) -> Assunto:
    return Assunto(
        id=linha["id"],
        titulo_gerado=linha["titulo_gerado"],
        primeiro_visto=linha["primeiro_visto"],
        ultimo_visto=linha["ultimo_visto"],
        n_itens=linha["n_itens"],
        n_fontes_independentes=linha["n_fontes_independentes"],
        status=linha["status"],
        temas=json.loads(linha["temas"]),
        substancial=linha["substancial"],
        conversavel=linha["conversavel"],
        justificativa=linha["justificativa"],
        resumo_cartao=linha["resumo_cartao"],
    )


def _desserializar(blob: bytes) -> list[float]:
    quantidade = len(blob) // 4
    return list(struct.unpack(f"<{quantidade}f", blob))


def inserir(conexao: sqlite3.Connection, assunto: Assunto) -> int:
    cursor = conexao.execute(
        "INSERT INTO assunto "
        "(titulo_gerado, primeiro_visto, ultimo_visto, n_itens, n_fontes_independentes, "
        "status, temas, substancial, conversavel, justificativa, resumo_cartao) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            assunto.titulo_gerado,
            assunto.primeiro_visto,
            assunto.ultimo_visto,
            assunto.n_itens,
            assunto.n_fontes_independentes,
            assunto.status,
            json.dumps(assunto.temas),
            assunto.substancial,
            assunto.conversavel,
            assunto.justificativa,
            assunto.resumo_cartao,
        ),
    )
    assert cursor.lastrowid is not None
    return cursor.lastrowid


def obter_por_id(conexao: sqlite3.Connection, assunto_id: int) -> Assunto | None:
    linha = conexao.execute(f"SELECT {_COLUNAS} FROM assunto WHERE id = ?", (assunto_id,)).fetchone()
    return _para_assunto(linha) if linha is not None else None


def listar_candidatos(conexao: sqlite3.Connection, desde_janela: str, desde_reabertura: str) -> list[Assunto]:
    linhas = conexao.execute(
        f"SELECT {_COLUNAS} FROM assunto WHERE status IN ('novo', 'em_curso') AND ultimo_visto >= ? "
        f"UNION "
        f"SELECT {_COLUNAS} FROM assunto WHERE status = 'encerrado' AND ultimo_visto >= ?",
        (desde_janela, desde_reabertura),
    ).fetchall()
    return [_para_assunto(linha) for linha in linhas]


def atualizar_apos_item(
    conexao: sqlite3.Connection,
    assunto_id: int,
    ultimo_visto: str,
    n_itens: int,
    n_fontes_independentes: int,
    status: StatusAssunto,
    agora: str,
    primeiro_visto: str | None = None,
) -> None:
    # `agora` não é persistido: a tabela `assunto` não tem coluna de atualização — mantido no
    # parâmetro para uniformidade com o restante das funções de escrita deste pacote.
    # `primeiro_visto` só é passado pelo recálculo de divisão (fase 3 do agrupador); no fluxo
    # normal de chegada de item (fase 1) ele nunca muda e o padrão None deixa a coluna intocada.
    del agora
    if primeiro_visto is None:
        conexao.execute(
            "UPDATE assunto SET ultimo_visto = ?, n_itens = ?, n_fontes_independentes = ?, status = ? "
            "WHERE id = ?",
            (ultimo_visto, n_itens, n_fontes_independentes, status, assunto_id),
        )
    else:
        conexao.execute(
            "UPDATE assunto SET primeiro_visto = ?, ultimo_visto = ?, n_itens = ?, "
            "n_fontes_independentes = ?, status = ? WHERE id = ?",
            (primeiro_visto, ultimo_visto, n_itens, n_fontes_independentes, status, assunto_id),
        )


def fechar_inativos(conexao: sqlite3.Connection, antes_de: str, agora: str) -> int:
    del agora
    cursor = conexao.execute(
        "UPDATE assunto SET status = 'encerrado' WHERE status IN ('novo', 'em_curso') AND ultimo_visto < ?",
        (antes_de,),
    )
    return cursor.rowcount


def listar_maiores_que(conexao: sqlite3.Connection, n: int) -> list[Assunto]:
    linhas = conexao.execute(f"SELECT {_COLUNAS} FROM assunto WHERE n_itens > ? ORDER BY id", (n,)).fetchall()
    return [_para_assunto(linha) for linha in linhas]


def gravar_centroide(conexao: sqlite3.Connection, assunto_id: int, centroide: list[float]) -> None:
    vetor = sqlite_vec.serialize_float32(centroide)
    conexao.execute("DELETE FROM vetor_assunto WHERE assunto_id = ?", (assunto_id,))
    conexao.execute("INSERT INTO vetor_assunto (assunto_id, centroide) VALUES (?, ?)", (assunto_id, vetor))


def obter_centroide(conexao: sqlite3.Connection, assunto_id: int) -> list[float] | None:
    linha = conexao.execute(
        "SELECT centroide FROM vetor_assunto WHERE assunto_id = ?", (assunto_id,)
    ).fetchone()
    return _desserializar(linha["centroide"]) if linha is not None else None


def listar_candidatos_qualificacao(conexao: sqlite3.Connection, limite: int) -> list[Assunto]:
    linhas_temas = conexao.execute(
        "SELECT DISTINCT vt.embedding FROM perfil_tema pt "
        "JOIN perfil p ON p.id = pt.perfil_id "
        "JOIN vetor_tema vt ON vt.tema_id = pt.tema_id "
        "WHERE p.tipo = 'usuario' OR p.ativo = 1"
    ).fetchall()
    embeddings_temas = [_desserializar(linha["embedding"]) for linha in linhas_temas]
    if not embeddings_temas:
        return []

    colunas_assunto = ", ".join(f"a.{coluna}" for coluna in _COLUNAS.split(", "))
    linhas_assuntos = conexao.execute(
        f"SELECT {colunas_assunto}, va.centroide AS centroide FROM assunto a "
        "JOIN vetor_assunto va ON va.assunto_id = a.id "
        "WHERE a.substancial IS NULL ORDER BY a.id"
    ).fetchall()

    candidatos: list[tuple[float, Assunto]] = []
    for linha in linhas_assuntos:
        centro = _desserializar(linha["centroide"])
        melhor = max(cosseno(centro, embedding_tema) for embedding_tema in embeddings_temas)
        candidatos.append((melhor, _para_assunto(linha)))

    candidatos.sort(key=lambda par: par[0], reverse=True)
    return [assunto for _, assunto in candidatos[:limite]]


def gravar_titulo(conexao: sqlite3.Connection, assunto_id: int, titulo: str) -> None:
    conexao.execute("UPDATE assunto SET titulo_gerado = ? WHERE id = ?", (titulo, assunto_id))


def gravar_qualificacao(
    conexao: sqlite3.Connection,
    assunto_id: int,
    substancial: float,
    conversavel: float,
    justificativa: str,
    temas_ids: list[int],
) -> None:
    conexao.execute(
        "UPDATE assunto SET substancial = ?, conversavel = ?, justificativa = ?, temas = ? WHERE id = ?",
        (substancial, conversavel, justificativa, json.dumps(temas_ids), assunto_id),
    )


def gravar_cartao(conexao: sqlite3.Connection, assunto_id: int, resumo_cartao: str) -> None:
    conexao.execute("UPDATE assunto SET resumo_cartao = ? WHERE id = ?", (resumo_cartao, assunto_id))


def listar_qualificados_nao_vistos(
    conexao: sqlite3.Connection,
    substancial_minimo: float,
    conversavel_minimo: float,
    ids_vistos: set[int],
) -> list[tuple[Assunto, list[float]]]:
    colunas_assunto = ", ".join(f"a.{coluna}" for coluna in _COLUNAS.split(", "))
    linhas = conexao.execute(
        f"SELECT {colunas_assunto}, va.centroide AS centroide FROM assunto a "
        "JOIN vetor_assunto va ON va.assunto_id = a.id "
        "WHERE a.substancial >= ? AND a.conversavel >= ? ORDER BY a.id",
        (substancial_minimo, conversavel_minimo),
    ).fetchall()

    resultado: list[tuple[Assunto, list[float]]] = []
    for linha in linhas:
        assunto = _para_assunto(linha)
        if assunto.id in ids_vistos:
            continue
        resultado.append((assunto, _desserializar(linha["centroide"])))
    return resultado


def listar_qualificados_sem_cartao(conexao: sqlite3.Connection, limite: int) -> list[Assunto]:
    linhas = conexao.execute(
        f"SELECT {_COLUNAS} FROM assunto "
        "WHERE substancial IS NOT NULL AND conversavel IS NOT NULL AND resumo_cartao IS NULL "
        "ORDER BY id LIMIT ?",
        (limite,),
    ).fetchall()
    return [_para_assunto(linha) for linha in linhas]
