"""Migração 016: `perfil.genero_gramatical`, para a redação concordar certo ao adaptar um molde de
outro contato (brief 048)."""

from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

import pytest

from agente_nw.nucleo.database import conexao, migracoes


def test_a_migracao_16_acrescenta_genero_gramatical_com_padrao_desconhecido(tmp_path: Path) -> None:
    antigas = tmp_path / "antigas"
    antigas.mkdir()
    for caminho in migracoes.PASTA_MIGRACOES_PADRAO.glob("*.sql"):
        if int(caminho.name.split("_", 1)[0]) <= 15:
            shutil.copy(caminho, antigas / caminho.name)
    banco = conexao.abrir(tmp_path / "velho.db")
    migracoes.aplicar(banco, antigas)
    banco.execute(
        "INSERT INTO perfil (nome, tipo, criado_em, atualizado_em) "
        "VALUES ('Ana', 'contato', '2026-10-30', '2026-10-30')"
    )
    banco.commit()

    migracoes.aplicar(banco)

    (genero,) = banco.execute("SELECT genero_gramatical FROM perfil WHERE nome = 'Ana'").fetchone()
    assert genero == "desconhecido"
    assert banco.execute("SELECT MAX(versao) FROM schema_version").fetchone()[0] == 16


def test_genero_gramatical_so_aceita_os_tres_valores(tmp_path: Path) -> None:
    banco = conexao.abrir(tmp_path / "novo.db")
    migracoes.aplicar(banco)
    banco.execute(
        "INSERT INTO perfil (nome, tipo, genero_gramatical, criado_em, atualizado_em) "
        "VALUES ('Luiz', 'contato', 'masculino', '2026-10-30', '2026-10-30')"
    )
    banco.commit()

    with pytest.raises(sqlite3.IntegrityError):
        banco.execute(
            "INSERT INTO perfil (nome, tipo, genero_gramatical, criado_em, atualizado_em) "
            "VALUES ('X', 'contato', 'outro', '2026-10-30', '2026-10-30')"
        )
