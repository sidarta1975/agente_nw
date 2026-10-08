from __future__ import annotations

import sqlite3
from typing import Protocol

from agente_nw.nucleo.database.queries import perfil_tema
from agente_nw.nucleo.database.queries import perfis as queries_perfis
from agente_nw.nucleo.database.queries import temas as queries_temas
from agente_nw.nucleo.modelos.configuracao import TemaUsuario
from agente_nw.nucleo.modelos.perfil import Perfil


class ClienteEmbeddagem(Protocol):
    def embeddar(self, textos: list[str]) -> list[list[float]]: ...


def _gravar_tema_do_usuario(
    conexao: sqlite3.Connection,
    cliente_llm: ClienteEmbeddagem,
    usuario_id: int,
    tema: TemaUsuario,
    agora: str,
) -> None:
    tema_gravado = queries_temas.obter_ou_criar(conexao, tema.nome, tema.descricao, tema.sinonimos, agora)
    assert tema_gravado.id is not None
    vetor = cliente_llm.embeddar([f"{tema.nome}: {tema.descricao}"])[0]
    queries_temas.gravar_embedding(conexao, tema_gravado.id, vetor)
    perfil_tema.vincular(
        conexao, usuario_id, tema_gravado.id, tema.peso, "declarada", tema.nivel, True, agora
    )


def salvar_perfil_usuario(
    conexao: sqlite3.Connection,
    cliente_llm: ClienteEmbeddagem,
    nome: str,
    temas: list[TemaUsuario],
    agora: str,
) -> Perfil:
    """Cria ou atualiza o perfil de usuário e vincula os temas informados,
    todos confirmados e com origem `declarada`. Reaproveitado tanto pelo CLI
    `importar-temas` quanto pelo formulário do console."""
    usuario = queries_perfis.upsert_usuario(conexao, nome, agora)
    assert usuario.id is not None
    for tema in temas:
        _gravar_tema_do_usuario(conexao, cliente_llm, usuario.id, tema, agora)
    conexao.commit()
    return usuario


def adicionar_tema_do_usuario(
    conexao: sqlite3.Connection,
    cliente_llm: ClienteEmbeddagem,
    usuario_id: int,
    tema: TemaUsuario,
    agora: str,
) -> None:
    """Adiciona um único tema a um perfil de usuário já existente."""
    _gravar_tema_do_usuario(conexao, cliente_llm, usuario_id, tema, agora)
    conexao.commit()


def remover_tema_do_usuario(conexao: sqlite3.Connection, usuario_id: int, tema_id: int) -> bool:
    """Remove o vínculo entre um tema e o perfil de usuário. O tema em si
    (tabela `tema`) fica preservado — outros contatos podem ainda estar
    vinculados a ele."""
    removeu = perfil_tema.desvincular(conexao, usuario_id, tema_id)
    if removeu:
        conexao.commit()
    return removeu
