from __future__ import annotations

from pathlib import Path

import pytest

from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import pedidos


def test_pedido_ganha_andamento_e_pedidos_antigos_ficam_concluidos(tmp_path: Path) -> None:
    conn = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conn)

    colunas = {linha["name"] for linha in conn.execute("PRAGMA table_info(pedido)").fetchall()}
    novas = {"status", "etapa", "erro", "avisos_json", "pedido_pai_id", "consulta_id", "localizacao_json"}
    assert novas <= colunas
    cursor = conn.execute(  # como um pedido gravado antes da migração: sem informar o status
        "INSERT INTO pedido (texto, criado_em) VALUES ('pedido antigo', '2026-10-01T10:00:00+00:00')"
    )
    gravado = pedidos.obter_por_id(conn, int(cursor.lastrowid or 0))
    assert gravado is not None and gravado.status == "concluido"
    conn.close()


def test_status_fora_da_lista_e_recusado(tmp_path: Path) -> None:
    conn = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conn)
    pedido_id = pedidos.inserir(conn, "x", "2026-10-01T10:00:00+00:00")

    with pytest.raises(Exception, match="CHECK"):
        conn.execute("UPDATE pedido SET status = 'qualquer' WHERE id = ?", (pedido_id,))
    conn.close()
