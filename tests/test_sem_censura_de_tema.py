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
    """Resposta fabricada: sem rede, sem Ollama."""

    def __init__(self, resposta: RespostaExtracaoTexto) -> None:
        self._resposta = resposta

    def gerar_json(self, tarefa_nome: str, prompt: str, esquema: type[BaseModel]) -> Any:
        self._prompt = prompt
        return self._resposta


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


def _contato_com_item_na_fila(conn: sqlite3.Connection) -> int:
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


def test_tag_e_fato_politicos_ou_de_saude_sao_gravados(conn: sqlite3.Connection) -> None:
    perfil_id = _contato_com_item_na_fila(conn)
    tag = TagSugerida(tag="direito eleitoral", peso=4, trecho="atua em campanhas eleitorais")
    politico = FatoDatado(data="2026-01-01", tipo="publicacao", conteudo="Foi ao ato do PT", fonte="X")
    saude = FatoDatado(data="2026-01-02", tipo="publicacao", conteudo="Está em tratamento", fonte="X")
    resposta = RespostaExtracaoTexto(tags_sugeridas=[tag], fatos_datados=[politico, saude])

    resumo = processar_fila(_ClienteOllamaFalso(resposta), conn)

    assert resumo.tags_gravadas == 1
    assert resumo.fatos_gravados == 2
    (n_fatos,) = conn.execute("SELECT COUNT(*) FROM fato WHERE perfil_id = ?", (perfil_id,)).fetchone()
    assert n_fatos == 2


def test_prompt_de_extracao_nao_manda_ignorar_tema() -> None:
    from agente_nw.coleta.capturas.extrator import construir_prompt as prompt_do_bloco
    from agente_nw.nucleo.prompts.extrair_de_texto import construir_prompt as prompt_do_texto

    for prompt in (prompt_do_bloco("bloco", "linkedin"), prompt_do_texto("texto")):
        assert "sensíve" not in prompt
        assert "posição política" not in prompt
