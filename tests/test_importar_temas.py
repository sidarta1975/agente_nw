from __future__ import annotations

import sqlite3
from pathlib import Path

from agente_nw.cli import importar_temas
from agente_nw.nucleo.database import conexao, migracoes

RAIZ = Path(__file__).resolve().parent.parent


def _banco_temporario(tmp_path: Path) -> sqlite3.Connection:
    conn = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conn)
    return conn


class _ClienteEmbeddagemFake:
    def embeddar(self, textos: list[str]) -> list[list[float]]:
        return [[0.1, 0.2] + [0.0] * 1022 for _ in textos]


def test_importar_temas_grava_perfil_e_temas(tmp_path: Path) -> None:
    conn = _banco_temporario(tmp_path)

    resultado = importar_temas(
        str(RAIZ / "temas.exemplo.yaml"), simular=False, conexao_bd=conn, cliente_llm=_ClienteEmbeddagemFake()
    )

    assert resultado == 0
    (n_perfis,) = conn.execute("SELECT COUNT(*) FROM perfil WHERE tipo = 'usuario'").fetchone()
    (n_temas,) = conn.execute("SELECT COUNT(*) FROM tema").fetchone()
    (n_perfil_tema,) = conn.execute("SELECT COUNT(*) FROM perfil_tema").fetchone()
    (n_com_nivel,) = conn.execute("SELECT COUNT(*) FROM perfil_tema WHERE nivel IS NOT NULL").fetchone()
    (n_com_embedding,) = conn.execute("SELECT COUNT(*) FROM vetor_tema").fetchone()

    assert n_perfis == 1
    assert n_temas == 2
    assert n_perfil_tema == 2
    assert n_com_nivel == 2
    assert n_com_embedding == 2

    conn.close()


def test_importar_temas_de_novo_nao_duplica(tmp_path: Path) -> None:
    conn = _banco_temporario(tmp_path)

    importar_temas(
        str(RAIZ / "temas.exemplo.yaml"), simular=False, conexao_bd=conn, cliente_llm=_ClienteEmbeddagemFake()
    )
    importar_temas(
        str(RAIZ / "temas.exemplo.yaml"), simular=False, conexao_bd=conn, cliente_llm=_ClienteEmbeddagemFake()
    )

    (n_perfis,) = conn.execute("SELECT COUNT(*) FROM perfil WHERE tipo = 'usuario'").fetchone()
    (n_temas,) = conn.execute("SELECT COUNT(*) FROM tema").fetchone()
    (n_perfil_tema,) = conn.execute("SELECT COUNT(*) FROM perfil_tema").fetchone()
    (n_com_embedding,) = conn.execute("SELECT COUNT(*) FROM vetor_tema").fetchone()

    assert n_perfis == 1
    assert n_temas == 2
    assert n_perfil_tema == 2
    assert n_com_embedding == 2  # substitui, não duplica

    conn.close()
