"""Recuperação de mensagens-molde por contexto: mesmo objetivo (categoria), mesmo registro e cargo
parecido; preferência pelas marcadas "usado"; `nao_serve` nunca entra (brief 048)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import consulta_contato, gancho_uso, perfis

AGORA = "2026-10-30T10:00:00+00:00"


def _abrir(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


def _contato(conn: sqlite3.Connection, nome: str, cargo: str) -> int:
    perfil = perfis.inserir_novo_contato(conn, nome, None, None, AGORA)
    assert perfil.id is not None
    perfis.atualizar_ficha_manual(conn, perfil.id, {"cargo": cargo}, AGORA)
    conn.commit()
    return perfil.id


def _gravar_consulta_e_mensagem(
    conn: sqlite3.Connection,
    perfil_id: int,
    objetivo_categoria: str,
    registro: str,
    mensagem: str,
    status: str,
) -> None:
    contexto_json = json.dumps({"objetivo_categoria": objetivo_categoria, "registro": registro})
    consulta = consulta_contato.inserir(conn, perfil_id, AGORA, contexto_json, None, "[]")
    assert consulta.id is not None
    gancho_json = json.dumps({"assunto_id": None, "mensagem": mensagem})
    gancho_uso.inserir_entregues(conn, consulta.id, [(None, gancho_json)], AGORA)
    if status != "entregue":
        gancho_uso.marcar(conn, consulta.id, None, status, AGORA)
    conn.commit()


def test_mensagem_usei_do_primeiro_advogado_vira_molde_para_o_segundo(tmp_path: Path) -> None:
    conn = _abrir(tmp_path)
    luiz = _contato(conn, "Luiz", "advogado")
    joao = _contato(conn, "João", "advogado")
    _gravar_consulta_e_mensagem(conn, luiz, "pedir", "cordial", "Mensagem que funcionou com o Luiz.", "usado")

    moldes = consulta_contato.moldes_por_contexto(conn, joao, "pedir", "cordial", "advogado", 2)

    assert len(moldes) == 1
    assert moldes[0].mensagem == "Mensagem que funcionou com o Luiz."
    assert moldes[0].bom is True


def test_mensagem_nao_serve_nunca_entra_como_molde(tmp_path: Path) -> None:
    conn = _abrir(tmp_path)
    luiz = _contato(conn, "Luiz", "advogado")
    joao = _contato(conn, "João", "advogado")
    _gravar_consulta_e_mensagem(conn, luiz, "pedir", "cordial", "Mensagem que não serviu.", "nao_serve")

    moldes = consulta_contato.moldes_por_contexto(conn, joao, "pedir", "cordial", "advogado", 2)

    assert moldes == []


def test_registro_diferente_nao_casa(tmp_path: Path) -> None:
    conn = _abrir(tmp_path)
    luiz = _contato(conn, "Luiz", "advogado")
    joao = _contato(conn, "João", "advogado")
    _gravar_consulta_e_mensagem(conn, luiz, "pedir", "formal", "Mensagem formal.", "usado")

    moldes = consulta_contato.moldes_por_contexto(conn, joao, "pedir", "cordial", "advogado", 2)

    assert moldes == []


def test_cargo_diferente_nao_casa(tmp_path: Path) -> None:
    conn = _abrir(tmp_path)
    luiz = _contato(conn, "Luiz", "advogado")
    maria = _contato(conn, "Maria", "médica")
    _gravar_consulta_e_mensagem(conn, luiz, "pedir", "cordial", "Mensagem do advogado.", "usado")

    moldes = consulta_contato.moldes_por_contexto(conn, maria, "pedir", "cordial", "médica", 2)

    assert moldes == []


def test_usado_vem_antes_de_entregue_e_respeita_o_maximo(tmp_path: Path) -> None:
    conn = _abrir(tmp_path)
    joao = _contato(conn, "João", "advogado")
    luiz = _contato(conn, "Luiz", "advogado")
    ana = _contato(conn, "Ana", "advogado")
    carla = _contato(conn, "Carla", "advogado")
    _gravar_consulta_e_mensagem(conn, luiz, "pedir", "cordial", "Mensagem só entregue, do Luiz.", "entregue")
    _gravar_consulta_e_mensagem(conn, ana, "pedir", "cordial", "Mensagem usada, da Ana.", "usado")
    _gravar_consulta_e_mensagem(conn, carla, "pedir", "cordial", "Outra mensagem, da Carla.", "usado")

    moldes = consulta_contato.moldes_por_contexto(conn, joao, "pedir", "cordial", "advogado", 2)

    assert len(moldes) == 2
    assert all(molde.bom for molde in moldes)  # as duas "usado" vêm antes da "entregue"
