from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path

from agente_nw.nucleo.database import backup, conexao, migracoes

TABELAS = (
    "schema_version",
    "tema",
    "perfil",
    "perfil_tema",
    "fonte",
    "assunto",
    "item",
    "assunto_contato",
    "fato",
    "fila_extracao",
    "descarte_sensivel",
    "fila_revisao",
    "progresso",
)


def _contagens(conn: sqlite3.Connection) -> dict[str, int]:
    return {tabela: conn.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0] for tabela in TABELAS}


def test_backup_gerado_e_restaurado_com_mesmas_contagens(tmp_path: Path) -> None:
    conn = conexao.abrir(tmp_path / "origem.db")
    migracoes.aplicar(conn)
    conn.execute(
        "INSERT INTO tema (nome, descricao, criado_em) "
        "VALUES ('corrida', 'descrição de exemplo', '2026-01-01')"
    )
    conn.commit()

    pasta_backups = tmp_path / "backups"
    caminho_backup = backup.fazer_backup(conn, pasta_backups)

    assert caminho_backup.exists()

    backup.restaurar(caminho_backup, tmp_path / "restaurado.db")

    conn_verificacao = sqlite3.connect(tmp_path / "restaurado.db")
    conn_verificacao.row_factory = sqlite3.Row

    assert _contagens(conn_verificacao) == _contagens(conn)
    conn_verificacao.close()
    conn.close()


def test_retencao_apaga_backup_com_mais_de_sete_dias(tmp_path: Path) -> None:
    pasta_backups = tmp_path / "backups"
    pasta_backups.mkdir()

    antigo = pasta_backups / "agente_2020-01-01.db"
    antigo.write_bytes(b"conteudo")
    oito_dias_atras = time.time() - 8 * 86400
    os.utime(antigo, (oito_dias_atras, oito_dias_atras))

    recente = pasta_backups / "agente_2026-01-01.db"
    recente.write_bytes(b"conteudo")

    apagados = backup.apagar_antigos(pasta_backups)

    assert antigo in apagados
    assert not antigo.exists()
    assert recente.exists()


def test_backup_mais_recente(tmp_path: Path) -> None:
    pasta_backups = tmp_path / "backups"
    pasta_backups.mkdir()
    (pasta_backups / "agente_2026-01-01.db").write_bytes(b"a")
    (pasta_backups / "agente_2026-02-01.db").write_bytes(b"b")

    mais_recente = backup.backup_mais_recente(pasta_backups)

    assert mais_recente is not None
    assert mais_recente.name == "agente_2026-02-01.db"
