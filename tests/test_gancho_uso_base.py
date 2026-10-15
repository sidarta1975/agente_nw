from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

import tests.test_redacao_redigir as base
from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import gancho_uso

conn = base.conn


def _consulta(conn: sqlite3.Connection) -> int:
    _usuario, _contato, resultado = base._montar(conn, n_assuntos=1)
    return resultado.consulta_id


def test_a_mensagem_base_tem_usei_e_nao_serve_como_os_demais(conn: sqlite3.Connection) -> None:
    consulta_id = _consulta(conn)
    gancho_uso.inserir_entregues(conn, consulta_id, [(None, '{"mensagem": "base"}')], base.AGORA)

    assert gancho_uso.marcar(conn, consulta_id, None, "usado", base.AGORA) is True

    assert gancho_uso.listar_por_consulta(conn, consulta_id) == [(None, "usado", '{"mensagem": "base"}')]
    assert gancho_uso.marcar(conn, consulta_id, None, "nao_serve", base.AGORA) is True
    assert gancho_uso.listar_por_consulta(conn, consulta_id)[0][1] == "nao_serve"


def test_regravar_a_base_da_mesma_consulta_substitui_e_nao_duplica(conn: sqlite3.Connection) -> None:
    consulta_id = _consulta(conn)
    gancho_uso.inserir_entregues(conn, consulta_id, [(None, '{"mensagem": "a"}')], base.AGORA)
    gancho_uso.marcar(conn, consulta_id, None, "usado", base.AGORA)

    gancho_uso.inserir_entregues(conn, consulta_id, [(None, '{"mensagem": "b"}')], base.AGORA)

    assert gancho_uso.listar_por_consulta(conn, consulta_id) == [(None, "entregue", '{"mensagem": "b"}')]


def test_assuntos_usados_do_perfil_ignora_a_base(conn: sqlite3.Connection) -> None:
    usuario, contato, resultado = base._montar(conn, n_assuntos=1)
    assunto_id = resultado.itens_menu[0].assunto_id
    gancho_uso.inserir_entregues(conn, resultado.consulta_id, [(None, "{}"), (assunto_id, "{}")], base.AGORA)
    gancho_uso.marcar(conn, resultado.consulta_id, None, "usado", base.AGORA)
    gancho_uso.marcar(conn, resultado.consulta_id, assunto_id, "usado", base.AGORA)

    assert gancho_uso.assuntos_usados_do_perfil(conn, contato.id or 0) == {assunto_id}


def test_a_migracao_preserva_os_ganchos_que_ja_existiam(tmp_path: Path) -> None:
    antigas = tmp_path / "antigas"
    antigas.mkdir()
    for caminho in migracoes.PASTA_MIGRACOES_PADRAO.glob("*.sql"):
        if int(caminho.name.split("_", 1)[0]) <= 12:
            shutil.copy(caminho, antigas / caminho.name)
    banco = conexao.abrir(tmp_path / "velho.db")
    migracoes.aplicar(banco, antigas)
    banco.execute(
        "INSERT INTO assunto (titulo_gerado, primeiro_visto, ultimo_visto, status) "
        "VALUES ('A', '2026-10-01', '2026-10-01', 'novo')"
    )
    banco.execute(
        "INSERT INTO perfil (nome, tipo, criado_em, atualizado_em) "
        "VALUES ('Irene', 'contato', '2026-10-01', '2026-10-01')"
    )
    banco.execute(
        "INSERT INTO consulta_contato (perfil_id, criado_em, contexto_json, assuntos_entregues_json) "
        "VALUES (1, '2026-10-01', '{}', '[]')"
    )
    banco.execute(
        "INSERT INTO gancho_uso (consulta_id, assunto_id, status, gancho_json, atualizado_em) "
        "VALUES (1, 1, 'usado', '{}', '2026-10-01')"
    )
    banco.commit()

    migracoes.aplicar(banco)

    assert gancho_uso.listar_por_consulta(banco, 1) == [(1, "usado", "{}")]
    gancho_uso.inserir_entregues(banco, 1, [(None, "{}")], "2026-10-02")
    assert [a for a, _s, _j in gancho_uso.listar_por_consulta(banco, 1)] == [1, None]
