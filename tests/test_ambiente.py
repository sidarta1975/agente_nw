from __future__ import annotations

import sqlite3


def test_sqlite_vec_carrega_em_memoria() -> None:
    conexao = sqlite3.connect(":memory:")
    conexao.enable_load_extension(True)
    import sqlite_vec

    sqlite_vec.load(conexao)
    conexao.enable_load_extension(False)

    (versao,) = conexao.execute("select vec_version()").fetchone()
    assert versao

    conexao.close()
