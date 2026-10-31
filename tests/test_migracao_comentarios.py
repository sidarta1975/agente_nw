from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

import pytest

from agente_nw.nucleo.database import conexao, migracoes


def test_a_migracao_14_acrescenta_o_comentario_sem_perder_ganchos_antigos(tmp_path: Path) -> None:
    antigas = tmp_path / "antigas"
    antigas.mkdir()
    for caminho in migracoes.PASTA_MIGRACOES_PADRAO.glob("*.sql"):
        if int(caminho.name.split("_", 1)[0]) <= 13:
            shutil.copy(caminho, antigas / caminho.name)
    banco = conexao.abrir(tmp_path / "velho.db")
    migracoes.aplicar(banco, antigas)
    banco.execute(
        "INSERT INTO perfil (nome, tipo, criado_em, atualizado_em) "
        "VALUES ('Ana', 'contato', '2026-10-01', '2026-10-01')"
    )
    banco.execute(
        "INSERT INTO consulta_contato (perfil_id, criado_em, contexto_json, assuntos_entregues_json) "
        "VALUES (1, '2026-10-01', '{}', '[]')"
    )
    banco.execute(
        "INSERT INTO gancho_uso (consulta_id, assunto_id, status, gancho_json, atualizado_em) "
        "VALUES (1, NULL, 'usado', '{}', '2026-10-01')"
    )
    banco.commit()

    migracoes.aplicar(banco)

    linha = banco.execute("SELECT status, comentario FROM gancho_uso").fetchone()
    assert (linha["status"], linha["comentario"]) == ("usado", None)
    assert banco.execute("SELECT COUNT(*) FROM nota_contato").fetchone()[0] == 0
    assert banco.execute("SELECT MAX(versao) FROM schema_version").fetchone()[0] == 16


def test_nota_exige_perfil_existente(tmp_path: Path) -> None:
    banco = conexao.abrir(tmp_path / "novo.db")
    migracoes.aplicar(banco)

    with pytest.raises(sqlite3.IntegrityError):
        banco.execute(
            "INSERT INTO nota_contato (perfil_id, texto, criado_em) VALUES (999, 'x', '2026-10-01')"
        )
