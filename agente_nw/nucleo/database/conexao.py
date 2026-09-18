from __future__ import annotations

import sqlite3
from pathlib import Path

import sqlite_vec


def abrir(caminho: str | Path) -> sqlite3.Connection:
    caminho_str = str(caminho)
    if caminho_str != ":memory:":
        Path(caminho_str).parent.mkdir(parents=True, exist_ok=True)

    conexao = sqlite3.connect(caminho_str)
    conexao.row_factory = sqlite3.Row

    conexao.enable_load_extension(True)
    sqlite_vec.load(conexao)
    conexao.enable_load_extension(False)

    conexao.execute("PRAGMA journal_mode=WAL")
    conexao.execute("PRAGMA foreign_keys=ON")
    conexao.execute("PRAGMA busy_timeout=5000")
    conexao.execute("PRAGMA synchronous=NORMAL")

    return conexao
