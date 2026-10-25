from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Literal

StatusPedido = Literal["na_fila", "processando", "aguardando_pessoa", "concluido", "erro"]


@dataclass(frozen=True)
class PedidoGravado:
    id: int
    perfil_id: int | None
    texto: str
    extraido_json: str | None
    confianca: float | None
    contato_criado: bool
    contato_ambiguo: bool
    criado_em: str
    status: StatusPedido = "concluido"
    etapa: str | None = None
    erro: str | None = None
    avisos_json: str | None = None
    pedido_pai_id: int | None = None
    consulta_id: int | None = None
    localizacao_json: str | None = None
    noticias_fonte: str | None = None
    noticias_bloqueado_ate: str | None = None


@dataclass(frozen=True)
class PessoaRecente:
    perfil_id: int
    nome: str
    ultimo_pedido_em: str
    ganchos_usados: int


_COLUNAS = (
    "id, perfil_id, texto, extraido_json, confianca, contato_criado, contato_ambiguo, criado_em, "
    "status, etapa, erro, avisos_json, pedido_pai_id, consulta_id, localizacao_json, "
    "noticias_fonte, noticias_bloqueado_ate"
)


def _para_pedido(linha: sqlite3.Row) -> PedidoGravado:
    return PedidoGravado(
        id=linha["id"],
        perfil_id=linha["perfil_id"],
        texto=linha["texto"],
        extraido_json=linha["extraido_json"],
        confianca=linha["confianca"],
        contato_criado=bool(linha["contato_criado"]),
        contato_ambiguo=bool(linha["contato_ambiguo"]),
        criado_em=linha["criado_em"],
        status=linha["status"],
        etapa=linha["etapa"],
        erro=linha["erro"],
        avisos_json=linha["avisos_json"],
        pedido_pai_id=linha["pedido_pai_id"],
        consulta_id=linha["consulta_id"],
        localizacao_json=linha["localizacao_json"],
        noticias_fonte=linha["noticias_fonte"],
        noticias_bloqueado_ate=linha["noticias_bloqueado_ate"],
    )


def inserir(
    conexao: sqlite3.Connection,
    texto: str,
    agora: str,
    pedido_pai_id: int | None = None,
    perfil_id: int | None = None,
    status: StatusPedido = "concluido",
) -> int:
    cursor = conexao.execute(
        "INSERT INTO pedido (texto, criado_em, pedido_pai_id, perfil_id, status) VALUES (?, ?, ?, ?, ?)",
        (texto, agora, pedido_pai_id, perfil_id, status),
    )
    assert cursor.lastrowid is not None
    return cursor.lastrowid


def gravar_extracao(
    conexao: sqlite3.Connection, pedido_id: int, extraido_json: str, confianca: float
) -> None:
    conexao.execute(
        "UPDATE pedido SET extraido_json = ?, confianca = ? WHERE id = ?",
        (extraido_json, confianca, pedido_id),
    )


def gravar_resolucao(
    conexao: sqlite3.Connection,
    pedido_id: int,
    perfil_id: int | None,
    contato_criado: bool,
    contato_ambiguo: bool,
) -> None:
    conexao.execute(
        "UPDATE pedido SET perfil_id = ?, contato_criado = ?, contato_ambiguo = ? WHERE id = ?",
        (perfil_id, int(contato_criado), int(contato_ambiguo), pedido_id),
    )


def atualizar_status(
    conexao: sqlite3.Connection, pedido_id: int, status: StatusPedido, erro: str | None = None
) -> None:
    conexao.execute("UPDATE pedido SET status = ?, erro = ? WHERE id = ?", (status, erro, pedido_id))


def marcar_interrompidos(conexao: sqlite3.Connection) -> int:
    """Pedido que ficou 'na_fila' ou 'processando' porque o console foi encerrado não vai terminar sozinho.
    Devolve quantos marcou; quem chama faz o commit."""
    cursor = conexao.execute(
        "UPDATE pedido SET status = 'erro', erro = 'O console foi encerrado durante o pedido.' "
        "WHERE status IN ('na_fila', 'processando')"
    )
    return cursor.rowcount


def atualizar_etapa(conexao: sqlite3.Connection, pedido_id: int, etapa: str) -> None:
    conexao.execute("UPDATE pedido SET etapa = ? WHERE id = ?", (etapa, pedido_id))


def gravar_consulta(conexao: sqlite3.Connection, pedido_id: int, consulta_id: int) -> None:
    conexao.execute("UPDATE pedido SET consulta_id = ? WHERE id = ?", (consulta_id, pedido_id))


def gravar_localizacoes(conexao: sqlite3.Connection, pedido_id: int, localizacao_json: str | None) -> None:
    conexao.execute("UPDATE pedido SET localizacao_json = ? WHERE id = ?", (localizacao_json, pedido_id))


def gravar_fonte_noticias(
    conexao: sqlite3.Connection, pedido_id: int, fonte: str, bloqueado_ate: str | None
) -> None:
    conexao.execute(
        "UPDATE pedido SET noticias_fonte = ?, noticias_bloqueado_ate = ? WHERE id = ?",
        (fonte, bloqueado_ate, pedido_id),
    )


def gravar_avisos(conexao: sqlite3.Connection, pedido_id: int, avisos_json: str | None) -> None:
    conexao.execute("UPDATE pedido SET avisos_json = ? WHERE id = ?", (avisos_json, pedido_id))


def obter_por_id(conexao: sqlite3.Connection, pedido_id: int) -> PedidoGravado | None:
    linha = conexao.execute(f"SELECT {_COLUNAS} FROM pedido WHERE id = ?", (pedido_id,)).fetchone()
    return _para_pedido(linha) if linha is not None else None


def obter_ultimo(conexao: sqlite3.Connection) -> PedidoGravado | None:
    linha = conexao.execute(f"SELECT {_COLUNAS} FROM pedido ORDER BY id DESC LIMIT 1").fetchone()
    return _para_pedido(linha) if linha is not None else None


def listar_recentes(conexao: sqlite3.Connection, limite: int) -> list[PedidoGravado]:
    linhas = conexao.execute(
        f"SELECT {_COLUNAS} FROM pedido ORDER BY criado_em DESC, id DESC LIMIT ?", (limite,)
    ).fetchall()
    return [_para_pedido(linha) for linha in linhas]


def listar_por_perfil(conexao: sqlite3.Connection, perfil_id: int) -> list[PedidoGravado]:
    linhas = conexao.execute(
        f"SELECT {_COLUNAS} FROM pedido WHERE perfil_id = ? ORDER BY criado_em DESC, id DESC",
        (perfil_id,),
    ).fetchall()
    return [_para_pedido(linha) for linha in linhas]


def pessoas_recentes(conexao: sqlite3.Connection, limite: int) -> list[PessoaRecente]:
    """As últimas pessoas de quem o usuário pediu algo, com a data do último pedido e quantos ganchos
    dela ele marcou como usados."""
    linhas = conexao.execute(
        "SELECT p.perfil_id AS perfil_id, f.nome AS nome, MAX(p.criado_em) AS ultimo, "
        "(SELECT COUNT(*) FROM gancho_uso g JOIN consulta_contato c ON c.id = g.consulta_id "
        " WHERE c.perfil_id = p.perfil_id AND g.status = 'usado') AS usados "
        "FROM pedido p JOIN perfil f ON f.id = p.perfil_id "
        "WHERE p.perfil_id IS NOT NULL GROUP BY p.perfil_id ORDER BY ultimo DESC LIMIT ?",
        (limite,),
    ).fetchall()
    return [
        PessoaRecente(
            perfil_id=linha["perfil_id"],
            nome=linha["nome"],
            ultimo_pedido_em=linha["ultimo"],
            ganchos_usados=linha["usados"],
        )
        for linha in linhas
    ]
