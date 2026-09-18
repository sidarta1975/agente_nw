from __future__ import annotations

from pathlib import Path

from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import sistema

# Deriva do que existe em scripts/migracoes/, não de um número fixo — cada brief que
# acrescenta uma migração nova não precisa lembrar de atualizar este teste.
_QUANTIDADE_MIGRACOES = len(list(migracoes.PASTA_MIGRACOES_PADRAO.glob("*.sql")))


def test_migracao_cria_esquema_do_zero(tmp_path: Path) -> None:
    conn = conexao.abrir(tmp_path / "teste.db")

    aplicadas = migracoes.aplicar(conn)

    assert aplicadas == _QUANTIDADE_MIGRACOES
    assert sistema.versao_esquema(conn) == _QUANTIDADE_MIGRACOES
    assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert sistema.vec_version(conn)

    for tabela in ("vetor_tema", "vetor_item", "vetor_assunto", "vetor_perfil"):
        existe = conn.execute("SELECT name FROM sqlite_master WHERE name = ?", (tabela,)).fetchone()
        assert existe is not None, f"tabela virtual {tabela} não foi criada"

    conn.close()


def test_segunda_chamada_de_aplicar_nao_faz_nada(tmp_path: Path) -> None:
    conn = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conn)

    aplicadas_segunda_vez = migracoes.aplicar(conn)

    assert aplicadas_segunda_vez == 0
    assert sistema.versao_esquema(conn) == _QUANTIDADE_MIGRACOES

    conn.close()
