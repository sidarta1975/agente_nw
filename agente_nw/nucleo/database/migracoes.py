from __future__ import annotations

import sqlite3
from pathlib import Path

PASTA_MIGRACOES_PADRAO = Path(__file__).resolve().parent.parent.parent.parent / "scripts" / "migracoes"


def _versao_atual(conexao: sqlite3.Connection) -> int:
    existe = conexao.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
    ).fetchone()
    if existe is None:
        return 0
    linha = conexao.execute("SELECT MAX(versao) AS versao FROM schema_version").fetchone()
    versao = linha["versao"] if linha is not None else None
    return int(versao) if versao is not None else 0


def _migracoes_disponiveis(pasta: Path) -> list[tuple[int, Path]]:
    migracoes = [(int(caminho.name.split("_", 1)[0]), caminho) for caminho in pasta.glob("*.sql")]
    return sorted(migracoes, key=lambda item: item[0])


def aplicar(conexao: sqlite3.Connection, pasta: Path = PASTA_MIGRACOES_PADRAO) -> int:
    disponiveis = _migracoes_disponiveis(pasta)
    atual = _versao_atual(conexao)
    aplicadas = 0

    for numero, caminho in disponiveis:
        if numero <= atual:
            continue
        sql = caminho.read_text(encoding="utf-8")
        try:
            conexao.executescript(f"BEGIN;\n{sql}\nCOMMIT;")
        except Exception:
            conexao.execute("ROLLBACK")
            raise
        aplicadas += 1

    versao_final = _versao_atual(conexao)
    maior_arquivo = max((numero for numero, _ in disponiveis), default=0)
    if versao_final != maior_arquivo:
        raise RuntimeError(
            f"schema_version ({versao_final}) não bate com a última migração disponível ({maior_arquivo})"
        )

    return aplicadas
