from __future__ import annotations

import threading
import time
from pathlib import Path

from agente_nw.nucleo.database import conexao, migracoes


def test_leitura_nao_bloqueia_durante_escrita_em_andamento(tmp_path: Path) -> None:
    caminho = tmp_path / "concorrencia.db"
    conn_preparo = conexao.abrir(caminho)
    migracoes.aplicar(conn_preparo)
    conn_preparo.close()

    def escrever_devagar() -> None:
        conn = conexao.abrir(caminho)
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            "INSERT INTO tema (nome, descricao, criado_em) VALUES "
            "('t1', 'descrição de exemplo com palavras suficientes', '2026-01-01')"
        )
        time.sleep(2)
        conn.commit()
        conn.close()

    thread_escrita = threading.Thread(target=escrever_devagar)
    thread_escrita.start()
    time.sleep(0.3)  # garante que a transação de escrita já começou

    inicio = time.monotonic()
    conn_leitura = conexao.abrir(caminho)
    (contagem,) = conn_leitura.execute("SELECT COUNT(*) FROM tema").fetchone()
    duracao = time.monotonic() - inicio
    conn_leitura.close()

    thread_escrita.join()

    assert contagem == 0  # a inserção ainda não tinha sido commitada quando a leitura rodou
    assert duracao < 2.0
