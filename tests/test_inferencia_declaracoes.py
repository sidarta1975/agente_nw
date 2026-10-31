"""O que o usuário disse sobre si vale mais (brief 040): autodeclaração positiva vira tema
`declarada`/`dominio`; negativa vira `nao_me_interessa` (e remove o tema se ele já existia); e o nome
do usuário é atualizado quando ele se identifica."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import perfil_tema, perfis, temas
from agente_nw.nucleo.modelos.configuracao import TemasUsuarioLimiares
from agente_nw.nucleo.modelos.tema import RespostaDescreverTema
from agente_nw.perfil import inferencia

AGORA = "2026-10-31T10:00:00+00:00"


def _vetor(*valores: float) -> list[float]:
    return list(valores) + [0.0] * (1024 - len(valores))


class _ClienteFalso:
    def gerar_json(self, tarefa_nome: str, prompt: str, esquema: type[Any]) -> Any:
        assert tarefa_nome == "descrever_tema"
        return RespostaDescreverTema(descricao="descrição qualquer de teste", sinonimos=[])

    def embeddar(self, textos: list[str]) -> list[list[float]]:
        return [_vetor(1.0, 0.0) for _ in textos]


def _abrir(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


def test_declaracao_positiva_vira_tema_declarada_dominio(tmp_path: Path) -> None:
    conn = _abrir(tmp_path)
    usuario = perfis.upsert_usuario(conn, "Rafael", AGORA)
    assert usuario.id is not None

    inferencia.aplicar_declaracoes(
        conn, _ClienteFalso(), usuario.id, ["sou advogado tributarista"], AGORA, TemasUsuarioLimiares()
    )

    tema = temas.obter_por_nome(conn, "advogado tributarista")
    assert tema is not None and tema.id is not None
    (vinculo,) = perfil_tema.listar_por_perfil(conn, usuario.id)
    assert vinculo.tema_id == tema.id
    assert vinculo.origem == "declarada"
    assert vinculo.nivel == "dominio"


def test_declaracao_negativa_vira_nao_me_interessa(tmp_path: Path) -> None:
    conn = _abrir(tmp_path)
    usuario = perfis.upsert_usuario(conn, "Rafael", AGORA)
    assert usuario.id is not None

    inferencia.aplicar_declaracoes(
        conn, _ClienteFalso(), usuario.id, ["não me interessa futebol"], AGORA, TemasUsuarioLimiares()
    )

    assert perfis.listar_nao_me_interessa(conn, usuario.id) == ["futebol"]
    assert perfil_tema.listar_por_perfil(conn, usuario.id) == []


def test_nao_tenho_mais_interesse_remove_o_tema_existente(tmp_path: Path) -> None:
    conn = _abrir(tmp_path)
    usuario = perfis.upsert_usuario(conn, "Rafael", AGORA)
    assert usuario.id is not None
    tema = temas.obter_ou_criar(conn, "política partidária", "disputa entre partidos políticos", [], AGORA)
    assert tema.id is not None
    perfil_tema.vincular(conn, usuario.id, tema.id, 3, "conversa", "interesse", True, AGORA)
    conn.commit()

    inferencia.aplicar_declaracoes(
        conn,
        _ClienteFalso(),
        usuario.id,
        ["não tenho mais interesse em política partidária"],
        AGORA,
        TemasUsuarioLimiares(),
    )

    assert perfil_tema.listar_por_perfil(conn, usuario.id) == []
    assert perfis.listar_nao_me_interessa(conn, usuario.id) == ["política partidária"]


def test_me_chamo_atualiza_o_nome(tmp_path: Path) -> None:
    conn = _abrir(tmp_path)
    usuario = perfis.upsert_usuario(conn, "Usuário", AGORA)
    assert usuario.id is not None

    inferencia.aplicar_declaracoes(
        conn, _ClienteFalso(), usuario.id, ["me chamo Sidarta"], AGORA, TemasUsuarioLimiares()
    )

    atualizado = perfis.obter_usuario(conn)
    assert atualizado is not None and atualizado.nome == "Sidarta"


def test_frase_sem_padrao_reconhecido_e_ignorada(tmp_path: Path) -> None:
    conn = _abrir(tmp_path)
    usuario = perfis.upsert_usuario(conn, "Rafael", AGORA)
    assert usuario.id is not None

    inferencia.aplicar_declaracoes(
        conn,
        _ClienteFalso(),
        usuario.id,
        ["isso aqui não segue padrão nenhum de autodeclaração"],
        AGORA,
        TemasUsuarioLimiares(),
    )

    assert perfil_tema.listar_por_perfil(conn, usuario.id) == []
    assert perfis.listar_nao_me_interessa(conn, usuario.id) == []
