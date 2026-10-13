from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pytest

from agente_nw.nucleo import pedido as pedido_mod
from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import pedidos, perfis
from agente_nw.nucleo.modelos.pedido import PedidoExtraido

AGORA = "2026-10-11T10:00:00+00:00"
DEPOIS = "2026-10-12T10:00:00+00:00"


def _pedido(**mudancas: Any) -> PedidoExtraido:
    dados: dict[str, Any] = {
        "pessoa_nome": "Renato",
        "pessoa_pistas": {},
        "objetivo": "retomar",
        "objetivo_texto": "retomar o contato",
        "meio": "whatsapp",
        "registro": "cordial",
        "assunto_principal": "construção naval",
        "termos_busca": ["estaleiros"],
        "confianca": 0.8,
    }
    dados.update(mudancas)
    return PedidoExtraido.model_validate(dados)


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


def test_nome_inexistente_cria_contato_com_as_pistas(conn: sqlite3.Connection) -> None:
    pedido = _pedido(
        pessoa_pistas={
            "profissao": "engenheiro naval",
            "empresa": "Estaleiro Atlântico",
            "cidade": "Recife",
            "vinculo": "cliente antigo",
            "tempo_sem_contato": "há dois anos",
        }
    )

    perfil, criado, ambiguo, candidatos = pedido_mod.resolver_contato(conn, pedido, AGORA)

    assert criado is True and ambiguo is False and candidatos == []
    assert perfil is not None
    assert perfil.tipo == "contato"
    assert perfil.empresa == "Estaleiro Atlântico"
    assert perfil.cargo == "engenheiro naval"
    assert perfil.cidade == "Recife"
    assert "cliente antigo" in (perfil.notas or "")
    assert perfil.telefone is None and perfil.email is None


def test_nome_existente_unico_reaproveita_e_preenche_so_lacunas(conn: sqlite3.Connection) -> None:
    existente = perfis.inserir_novo_contato(conn, "Renato Alves", None, None, AGORA)
    assert existente.id is not None
    perfis.preencher_lacunas(conn, existente.id, {"empresa": "Estaleiro Atlântico"}, AGORA)
    conn.commit()

    pedido = _pedido(pessoa_pistas={"empresa": "Outra Empresa", "cidade": "Recife"})
    perfil, criado, ambiguo, _ = pedido_mod.resolver_contato(conn, pedido, DEPOIS)

    assert criado is False and ambiguo is False
    assert perfil is not None and perfil.id == existente.id
    assert perfil.empresa == "Estaleiro Atlântico"  # nunca sobrescreve
    assert perfil.cidade == "Recife"  # lacuna preenchida


def test_homonimos_escolhe_pelas_pistas_e_marca_ambiguidade(conn: sqlite3.Connection) -> None:
    a = perfis.inserir_novo_contato(conn, "Renato Alves", None, None, AGORA)
    b = perfis.inserir_novo_contato(conn, "Renato Souza", None, None, AGORA)
    assert a.id is not None and b.id is not None
    perfis.preencher_lacunas(conn, a.id, {"empresa": "Banco Alfa"}, AGORA)
    perfis.preencher_lacunas(conn, b.id, {"empresa": "Estaleiro Atlântico"}, AGORA)
    conn.commit()

    pedido = _pedido(pessoa_pistas={"empresa": "Estaleiro Atlântico"})
    perfil, criado, ambiguo, candidatos = pedido_mod.resolver_contato(conn, pedido, DEPOIS)

    assert criado is False and ambiguo is True
    assert perfil is not None and perfil.id == b.id
    assert {c.id for c in candidatos} == {a.id, b.id}


def test_contato_id_forcado_prevalece(conn: sqlite3.Connection) -> None:
    a = perfis.inserir_novo_contato(conn, "Renato Alves", None, None, AGORA)
    b = perfis.inserir_novo_contato(conn, "Renato Souza", None, None, AGORA)
    assert a.id is not None and b.id is not None
    conn.commit()

    perfil, criado, ambiguo, _ = pedido_mod.resolver_contato(conn, _pedido(), DEPOIS, contato_id_forcado=a.id)

    assert perfil is not None and perfil.id == a.id
    assert criado is False and ambiguo is False


def test_sem_nome_nao_ha_perfil_e_nao_ha_erro(conn: sqlite3.Connection) -> None:
    perfil, criado, ambiguo, candidatos = pedido_mod.resolver_contato(conn, _pedido(pessoa_nome=""), AGORA)
    assert perfil is None and criado is False and ambiguo is False and candidatos == []


class _ClienteFalso:
    def gerar_json(self, tarefa_nome: str, prompt: str, esquema: type[Any]) -> Any:
        return _pedido()


def test_processar_grava_o_pedido_com_o_perfil_resolvido(conn: sqlite3.Connection) -> None:
    resultado = pedido_mod.processar(_ClienteFalso(), conn, "Café com o Renato", AGORA)

    gravado = pedidos.obter_por_id(conn, resultado.pedido_id)
    assert gravado is not None
    assert gravado.texto == "Café com o Renato"
    assert gravado.extraido_json is not None
    assert gravado.perfil_id == (resultado.perfil.id if resultado.perfil else None)
    assert gravado.contato_criado is True
    assert perfis.obter_usuario(conn) is not None


def test_contato_forcado_com_nome_diferente_do_pedido_pede_confirmacao(conn: sqlite3.Connection) -> None:
    from types import SimpleNamespace

    lisa = perfis.inserir_novo_contato(conn, "Lisa Queen", None, None, AGORA)
    conn.commit()
    pedido = _pedido(pessoa_nome="Djalma")
    perguntas: list[tuple[str, str]] = []

    def _recusa(pessoa: str, contato: str) -> bool:
        perguntas.append((pessoa, contato))
        return False

    def _processar(confirmar: Any) -> Any:
        return pedido_mod.processar(
            SimpleNamespace(gerar_json=lambda *_a, **_k: pedido),
            conn,
            "frase",
            AGORA,
            contato_id_forcado=lisa.id,
            confirmar_contato=confirmar,
        )

    recusado = _processar(_recusa)
    aceito = _processar(lambda _p, _c: True)

    assert perguntas == [("Djalma", "Lisa Queen")]
    assert recusado.contato_divergente is True
    assert aceito.contato_divergente is False
