"""Temas do usuário inferidos dos pedidos (brief 040): termo novo cria tema, o nível sobe pela
frequência, termo que casa sinônimo reforça em vez de duplicar, decaimento por inatividade, e
`declarada` nunca decai nem é apagado por "esquecer"."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import perfil_tema, perfis, temas
from agente_nw.nucleo.modelos.configuracao import TemasUsuarioLimiares
from agente_nw.nucleo.modelos.pedido import PedidoExtraido
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


def _pedido(termo: str, objetivo: str = "manter") -> PedidoExtraido:
    return PedidoExtraido.model_validate(
        {
            "objetivo": objetivo,
            "objetivo_texto": "falar sobre o assunto",
            "assunto_principal": termo,
            "termos_busca": [termo],
            "confianca": 0.9,
        }
    )


def test_termo_novo_cria_tema_conversa_curiosidade(tmp_path: Path) -> None:
    conn = _abrir(tmp_path)
    perfis.upsert_usuario(conn, "Rafael", AGORA)

    inferencia.atualizar_temas_do_usuario(
        conn, _ClienteFalso(), _pedido("vela"), AGORA, TemasUsuarioLimiares()
    )

    usuario = perfis.obter_usuario(conn)
    assert usuario is not None and usuario.id is not None
    (vinculo,) = perfil_tema.listar_por_perfil(conn, usuario.id)
    assert vinculo.origem == "conversa"
    assert vinculo.nivel == "curiosidade"
    assert vinculo.peso == 1
    assert temas.obter_por_nome(conn, "vela") is not None


def test_nivel_sobe_pela_frequencia_interesse_depois_dominio(tmp_path: Path) -> None:
    conn = _abrir(tmp_path)
    perfis.upsert_usuario(conn, "Rafael", AGORA)
    cliente = _ClienteFalso()
    limiares = TemasUsuarioLimiares()
    base = datetime.fromisoformat(AGORA)

    def _tocar(dia: int) -> None:
        agora = (base + timedelta(days=dia)).isoformat()
        inferencia.atualizar_temas_do_usuario(conn, cliente, _pedido("vela"), agora, limiares)

    usuario = perfis.obter_usuario(conn)
    assert usuario is not None and usuario.id is not None

    for dia in range(3):  # 3 usos em 30 dias
        _tocar(dia)
    (vinculo,) = perfil_tema.listar_por_perfil(conn, usuario.id)
    assert vinculo.nivel == "interesse"

    for dia in range(3, 6):  # 6 usos em 90 dias
        _tocar(dia)
    (vinculo,) = perfil_tema.listar_por_perfil(conn, usuario.id)
    assert vinculo.nivel == "dominio"


def test_termo_que_casa_sinonimo_soma_peso_em_vez_de_criar(tmp_path: Path) -> None:
    conn = _abrir(tmp_path)
    perfis.upsert_usuario(conn, "Rafael", AGORA)
    tema = temas.obter_ou_criar(conn, "velejar", "praticar vela em barco a vela", ["vela"], AGORA)
    assert tema.id is not None
    temas.gravar_embedding(conn, tema.id, _vetor(1.0, 0.0))
    conn.commit()

    inferencia.atualizar_temas_do_usuario(
        conn, _ClienteFalso(), _pedido("vela"), AGORA, TemasUsuarioLimiares()
    )

    assert len(temas.listar(conn)) == 1  # não criou um "vela" separado
    usuario = perfis.obter_usuario(conn)
    assert usuario is not None and usuario.id is not None
    (vinculo,) = perfil_tema.listar_por_perfil(conn, usuario.id)
    assert vinculo.tema_id == tema.id
    assert vinculo.peso == 1


def test_decaimento_apos_180_dias_sem_uso_e_idempotente_no_mesmo_mes(tmp_path: Path) -> None:
    conn = _abrir(tmp_path)
    perfis.upsert_usuario(conn, "Rafael", AGORA)
    cliente = _ClienteFalso()
    limiares = TemasUsuarioLimiares()
    inferencia.atualizar_temas_do_usuario(conn, cliente, _pedido("vela"), AGORA, limiares)
    inferencia.atualizar_temas_do_usuario(conn, cliente, _pedido("vela"), AGORA, limiares)

    usuario = perfis.obter_usuario(conn)
    assert usuario is not None and usuario.id is not None
    (vinculo,) = perfil_tema.listar_por_perfil(conn, usuario.id)
    assert vinculo.peso == 2

    muito_depois = (datetime.fromisoformat(AGORA) + timedelta(days=200)).date()
    inferencia.decair(conn, muito_depois, limiares)
    (vinculo,) = perfil_tema.listar_por_perfil(conn, usuario.id)
    assert vinculo.peso == 1

    inferencia.decair(conn, muito_depois, limiares)  # mesmo mês: não decai de novo
    (vinculo,) = perfil_tema.listar_por_perfil(conn, usuario.id)
    assert vinculo.peso == 1


def test_declarada_nunca_decai_nem_e_apagada_por_esquecer(tmp_path: Path) -> None:
    conn = _abrir(tmp_path)
    usuario = perfis.upsert_usuario(conn, "Rafael", AGORA)
    assert usuario.id is not None
    tema = temas.obter_ou_criar(conn, "direito tributário", "ramo do direito sobre tributos", [], AGORA)
    assert tema.id is not None
    perfil_tema.vincular(conn, usuario.id, tema.id, 5, "declarada", "dominio", True, AGORA)
    conn.commit()

    muito_depois = (datetime.fromisoformat(AGORA) + timedelta(days=400)).date()
    inferencia.decair(conn, muito_depois, TemasUsuarioLimiares())
    (vinculo,) = perfil_tema.listar_por_perfil(conn, usuario.id)
    assert vinculo.peso == 5

    removidos = inferencia.esquecer_inferidos(conn, usuario.id)
    assert removidos == 0
    (vinculo,) = perfil_tema.listar_por_perfil(conn, usuario.id)
    assert vinculo.origem == "declarada"
