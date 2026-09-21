from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel

from agente_nw.coleta.capturas import leitor
from agente_nw.coleta.capturas.extrator import RespostaCapturaRedeSocial
from agente_nw.coleta.capturas.navegador import Pagina
from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import perfis, redes_sociais

AGORA = "2026-09-20T10:00:00+00:00"


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


@dataclass
class _PaginaFake:
    estados: list[tuple[str, str]] = field(default_factory=list)
    _indice_estado: int = 0
    fechada: bool = False

    def ir_para(self, url: str) -> None:
        pass

    def estado(self) -> tuple[str, str]:
        indice = min(self._indice_estado, len(self.estados) - 1)
        self._indice_estado += 1
        return self.estados[indice]

    def rolar(self) -> None:
        pass

    def fechar(self) -> None:
        self.fechada = True


class _ClienteLLMFake:
    def __init__(self, respostas_por_bloco: dict[str, RespostaCapturaRedeSocial]) -> None:
        self._respostas = respostas_por_bloco
        self.chamadas: list[str] = []

    def gerar_json(self, tarefa: str, prompt: str, esquema: type[BaseModel]) -> Any:
        self.chamadas.append(tarefa)
        for chave, resposta in self._respostas.items():
            if chave in prompt:
                return resposta
        return RespostaCapturaRedeSocial(descartar=True)


def _texto_com_bloco(bloco: str) -> str:
    preenchimento = "conteúdo genérico o suficiente para passar do mínimo. " * 30
    return f"cabeçalho\n\n{bloco}\n\n{preenchimento}"


def _criar_contato(conn: sqlite3.Connection, nome: str, telefone: str) -> int:
    contato = perfis.inserir_ou_atualizar_contato(conn, nome, telefone, None, None, None, None, AGORA)
    conn.commit()
    assert contato.id is not None
    return contato.id


def test_contato_sem_redes_devolve_resumo_zerado(conn: sqlite3.Connection, tmp_path: Path) -> None:
    perfil_id = _criar_contato(conn, "Ana", "+5511900000001")

    def _abrir(_pasta: Path) -> Pagina:
        raise AssertionError("não deveria abrir navegador sem redes cadastradas")

    resumo = leitor.ler_redes_sociais_do_contato(
        _ClienteLLMFake({}),
        conn,
        perfil_id,
        _abrir,
        tmp_path / "navegador",
        AGORA,
        dorme=lambda _s: None,
        max_esperas_login=1,
        espera_login_s=0.0,
        max_rolagens=1,
    )

    assert resumo.redes_lidas == 0
    assert resumo.redes_sem_sessao == 0
    assert resumo.fatos_gravados == 0


def test_rede_autenticada_com_bloco_valido_grava_fato_com_tipo_e_fonte(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    perfil_id = _criar_contato(conn, "Beto", "+5511900000002")
    redes_sociais.inserir(conn, perfil_id, "linkedin", "https://linkedin.com/in/beto", AGORA)
    conn.commit()

    bloco = "Publicou artigo sobre gestão de projetos hoje pela manhã"
    texto = _texto_com_bloco(bloco)
    pagina = _PaginaFake(estados=[("https://linkedin.com/in/beto", texto)])

    resposta = RespostaCapturaRedeSocial(
        descartar=False,
        data_do_fato="2026-09-19",
        tipo="publicacao",
        conteudo=bloco,
    )
    cliente = _ClienteLLMFake({bloco: resposta})

    resumo = leitor.ler_redes_sociais_do_contato(
        cliente,
        conn,
        perfil_id,
        lambda _p: pagina,
        tmp_path / "navegador",
        AGORA,
        dorme=lambda _s: None,
        max_esperas_login=1,
        espera_login_s=0.0,
        max_rolagens=1,
    )

    assert resumo.redes_lidas == 1
    assert resumo.redes_sem_sessao == 0
    assert resumo.fatos_gravados == 1
    assert pagina.fechada is True

    linha = conn.execute(
        "SELECT perfil_id, data_do_fato, tipo, conteudo, fonte, registrado_em FROM fato WHERE perfil_id = ?",
        (perfil_id,),
    ).fetchone()
    assert linha is not None
    assert linha["perfil_id"] == perfil_id
    assert linha["data_do_fato"] == "2026-09-19"
    assert linha["tipo"] == "rede_social:linkedin"
    assert linha["conteudo"] == bloco
    assert linha["fonte"] == "https://linkedin.com/in/beto"
    assert linha["registrado_em"] == AGORA


def test_fato_gravado_e_imutavel(conn: sqlite3.Connection, tmp_path: Path) -> None:
    perfil_id = _criar_contato(conn, "Carla", "+5511900000003")
    redes_sociais.inserir(conn, perfil_id, "x", "https://x.com/carla", AGORA)
    conn.commit()

    bloco = "Compartilhou notícia sobre novos livros de ficção científica"
    texto = _texto_com_bloco(bloco)
    pagina = _PaginaFake(estados=[("https://x.com/carla", texto)])
    resposta = RespostaCapturaRedeSocial(descartar=False, data_do_fato=None, tipo="repost", conteudo=bloco)
    cliente = _ClienteLLMFake({bloco: resposta})

    leitor.ler_redes_sociais_do_contato(
        cliente,
        conn,
        perfil_id,
        lambda _p: pagina,
        tmp_path / "navegador",
        AGORA,
        dorme=lambda _s: None,
        max_esperas_login=1,
        espera_login_s=0.0,
        max_rolagens=1,
    )

    with pytest.raises(sqlite3.IntegrityError, match="fato é só inserção"):
        conn.execute("UPDATE fato SET conteudo = 'y' WHERE perfil_id = ?", (perfil_id,))
    with pytest.raises(sqlite3.IntegrityError, match="fato é só inserção"):
        conn.execute("DELETE FROM fato WHERE perfil_id = ?", (perfil_id,))


def test_rede_sem_sessao_nao_derruba_e_registra_motivo(conn: sqlite3.Connection, tmp_path: Path) -> None:
    perfil_id = _criar_contato(conn, "Dora", "+5511900000004")
    redes_sociais.inserir(conn, perfil_id, "instagram", "https://instagram.com/login?next=%2Fdora", AGORA)
    conn.commit()

    pagina = _PaginaFake(estados=[("https://instagram.com/login?next=%2Fdora", "faça login para continuar")])
    cliente = _ClienteLLMFake({})

    resumo = leitor.ler_redes_sociais_do_contato(
        cliente,
        conn,
        perfil_id,
        lambda _p: pagina,
        tmp_path / "navegador",
        AGORA,
        dorme=lambda _s: None,
        max_esperas_login=2,
        espera_login_s=0.0,
        max_rolagens=1,
    )

    assert resumo.redes_lidas == 0
    assert resumo.redes_sem_sessao == 1
    assert resumo.fatos_gravados == 0
    assert any("instagram" in motivo for motivo in resumo.motivos_sem_sessao)
    (n_fatos,) = conn.execute("SELECT COUNT(*) FROM fato WHERE perfil_id = ?", (perfil_id,)).fetchone()
    assert n_fatos == 0
