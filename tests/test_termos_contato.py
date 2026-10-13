from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pytest

from agente_nw.nucleo import termos_contato
from agente_nw.nucleo.database import conexao as conexao_bd
from agente_nw.nucleo.database import migracoes
from agente_nw.nucleo.database.queries import fatos
from agente_nw.nucleo.llm import FalhaJsonInvalido
from agente_nw.nucleo.modelos.fato import Fato

AGORA = "2026-10-13T10:00:00"


@pytest.fixture
def conexao(tmp_path: Path) -> sqlite3.Connection:
    aberta = conexao_bd.abrir(tmp_path / "teste.db")
    migracoes.aplicar(aberta)
    return aberta


class _Cliente:
    def __init__(self, termos: list[str] | None = None, falha: bool = False) -> None:
        self.termos = termos or []
        self.falha = falha
        self.prompts: list[str] = []

    def gerar_json(self, tarefa: str, prompt: str, esquema: Any) -> Any:
        assert tarefa == "extrair_termos_contato"
        self.prompts.append(prompt)
        if self.falha:
            raise FalhaJsonInvalido("extrair_termos_contato", 1, "inválido")
        return esquema(termos=self.termos)


def _fato(conexao: sqlite3.Connection, perfil_id: int, tipo: str, conteudo: str) -> None:
    fatos.inserir(conexao, Fato(perfil_id=perfil_id, tipo=tipo, conteudo=conteudo, registrado_em=AGORA))


def _perfil(conexao: sqlite3.Connection) -> int:
    cursor = conexao.execute(
        "INSERT INTO perfil (tipo, nome, linguas, ativo, criado_em, atualizado_em) "
        "VALUES ('contato', 'Ana', '[]', 0, ?, ?)",
        (AGORA, AGORA),
    )
    assert cursor.lastrowid is not None
    return cursor.lastrowid


def test_sem_fatos_nao_chama_o_modelo(conexao: sqlite3.Connection) -> None:
    perfil_id = _perfil(conexao)
    _fato(conexao, perfil_id, "lista_rede_social", "@ana")
    cliente = _Cliente(["x y"])

    assert termos_contato.termos_do_contato(cliente, conexao, perfil_id) == []
    assert cliente.prompts == []


def test_termos_filtrados_e_limitados(conexao: sqlite3.Connection) -> None:
    perfil_id = _perfil(conexao)
    _fato(conexao, perfil_id, "rede_social:linkedin", "Sotaque não atrapalha trabalhar em inglês")
    cliente = _Cliente(
        [
            "sotaque inglês trabalho",
            "Sotaque Inglês Trabalho",
            "vacinação em massa",
            "um dois três quatro cinco seis",
            "esqui Geórgia",
            "viagem neve",
            "outro tema",
        ]
    )

    termos = termos_contato.termos_do_contato(cliente, conexao, perfil_id)

    assert termos == ["sotaque inglês trabalho", "esqui Geórgia", "viagem neve"]
    assert "Sotaque não atrapalha" in cliente.prompts[0]


def test_falha_do_modelo_devolve_lista_vazia(conexao: sqlite3.Connection) -> None:
    perfil_id = _perfil(conexao)
    _fato(conexao, perfil_id, "rede_social:linkedin", "algo")

    assert termos_contato.termos_do_contato(_Cliente(falha=True), conexao, perfil_id) == []
