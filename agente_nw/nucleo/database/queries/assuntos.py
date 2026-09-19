from __future__ import annotations

import json
import sqlite3
import struct

import sqlite_vec

from agente_nw.nucleo.modelos.assunto import Assunto, StatusAssunto

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
