from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel

from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.llm import ClienteOllama
from agente_nw.nucleo.modelos.extracao import FatoDatado, RespostaExtracaoTexto, TagSugerida
from agente_nw.perfil.extrator import processar_fila


class _ClienteOllamaFalso(ClienteOllama):
    """Substitui o cliente real por uma resposta fabricada — sem rede, sem Ollama."""

    def __init__(self, resposta: RespostaExtracaoTexto) -> None:
        self._resposta = resposta

    def gerar_json(self, tarefa_nome: str, prompt: str, esquema: type[BaseModel]) -> Any:
        return self._resposta


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


def _criar_contato_com_item_na_fila(conn: sqlite3.Connection) -> int:
    agora = "2026-01-01T00:00:00+00:00"
    conn.execute(
        "INSERT INTO perfil (tipo, nome, linguas, criado_em, atualizado_em) "
        "VALUES ('contato', 'Fulano', '[]', ?, ?)",
        (agora, agora),
    )
    (perfil_id,) = conn.execute("SELECT id FROM perfil WHERE nome = 'Fulano'").fetchone()
    conn.execute(
        "INSERT INTO fila_extracao (perfil_id, texto, origem, criado_em, processado) "
        "VALUES (?, 'texto qualquer', 'cadastro', ?, 0)",
        (perfil_id, agora),
    )
    conn.commit()
    return perfil_id


def test_tag_sensivel_e_descartada_fato_limpo_e_gravado(conn: sqlite3.Connection) -> None:
    perfil_id = _criar_contato_com_item_na_fila(conn)

    resposta = RespostaExtracaoTexto(
        tags_sugeridas=[
            TagSugerida(tag="cabotagem", peso=3, trecho="está em tratamento para depressão"),
        ],
        fatos_datados=[
            FatoDatado(
                data="2026-01-01", tipo="publicacao", conteudo="comentou sobre logística", fonte="LinkedIn"
            ),
        ],
    )
    cliente_falso = _ClienteOllamaFalso(resposta)

    resumo = processar_fila(cliente_falso, conn)

    assert resumo.itens_processados == 1
    assert resumo.tags_gravadas == 0
    assert resumo.fatos_gravados == 1
    assert resumo.descartes_por_categoria.get("saude") == 1

    (n_perfil_tema,) = conn.execute(
        "SELECT COUNT(*) FROM perfil_tema WHERE perfil_id = ?", (perfil_id,)
    ).fetchone()
    assert n_perfil_tema == 0

    (n_fatos,) = conn.execute("SELECT COUNT(*) FROM fato WHERE perfil_id = ?", (perfil_id,)).fetchone()
    assert n_fatos == 1

    descarte = conn.execute(
        "SELECT categoria, origem_texto FROM descarte_sensivel WHERE perfil_id = ?", (perfil_id,)
    ).fetchone()
    assert descarte is not None
    assert descarte["categoria"] == "saude"
    assert descarte["origem_texto"] == "cadastro"  # nunca o trecho — a coluna nem existe na tabela
