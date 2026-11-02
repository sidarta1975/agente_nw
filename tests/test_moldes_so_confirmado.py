"""Interrompe a realimentação do molde (brief 065): havendo mensagem `usado` para a tríade de contexto,
só `usado` entra como molde; sem nenhuma `usado`, no máximo uma `entregue` (a mais recente, marcada como
não confirmada). A mensagem nova grava `molde_origem_id` apontando para o molde que a originou."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from agente_nw.nucleo import redacao as redacao_mod
from agente_nw.nucleo.consulta import ResultadoConsulta, ResumoRedeSocial
from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import consulta_contato, gancho_uso, perfis
from agente_nw.nucleo.modelos.pedido import PedidoExtraido
from agente_nw.nucleo.modelos.redacao import Gancho, RespostaRedacao
from tests.llm_falso import ProvenienciaFalsa

AGORA = "2026-11-02T10:00:00+00:00"


class _ClienteFalso(ProvenienciaFalsa):
    def gerar_json(
        self, tarefa_nome: str, prompt: str, esquema: type[Any], versao_prompt: str | None = None
    ) -> Any:
        assert tarefa_nome == "redigir_ganchos"
        return RespostaRedacao(ganchos=[Gancho(mensagem="Mensagem nova para o contato.")])


def _abrir(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


def _contato(conn: sqlite3.Connection, nome: str, cargo: str) -> int:
    perfil = perfis.inserir_novo_contato(conn, nome, None, None, AGORA)
    assert perfil.id is not None
    perfis.atualizar_ficha_manual(conn, perfil.id, {"cargo": cargo}, AGORA)
    conn.commit()
    return perfil.id


def _gravar_consulta_e_mensagem(
    conn: sqlite3.Connection,
    perfil_id: int,
    objetivo_categoria: str,
    registro: str,
    mensagem: str,
    status: str,
    quando: str,
) -> int:
    contexto_json = json.dumps({"objetivo_categoria": objetivo_categoria, "registro": registro})
    consulta = consulta_contato.inserir(conn, perfil_id, quando, contexto_json, None, "[]")
    assert consulta.id is not None
    gancho_json = json.dumps({"assunto_id": None, "mensagem": mensagem})
    gancho_uso.inserir_entregues(conn, consulta.id, [(None, gancho_json)], quando)
    if status != "entregue":
        gancho_uso.marcar(conn, consulta.id, None, status, quando)
    conn.commit()
    (gancho_id,) = conn.execute(
        "SELECT id FROM gancho_uso WHERE consulta_id = ? AND assunto_id IS NULL", (consulta.id,)
    ).fetchone()
    return int(gancho_id)


def _pedido() -> PedidoExtraido:
    return PedidoExtraido.model_validate(
        {
            "objetivo": "pedir",
            "objetivo_texto": "pedir apoio na chapa da OAB",
            "registro": "cordial",
            "assunto_principal": "eleição da OAB",
            "termos_busca": ["OAB"],
            "confianca": 0.9,
        }
    )


def test_havendo_usado_so_usado_entra_mesmo_com_entregue_mais_recente(tmp_path: Path) -> None:
    conn = _abrir(tmp_path)
    joao = _contato(conn, "João", "advogado")
    luiz = _contato(conn, "Luiz", "advogado")
    ana = _contato(conn, "Ana", "advogado")
    _gravar_consulta_e_mensagem(
        conn, luiz, "pedir", "cordial", "Mensagem usada, do Luiz.", "usado", "2026-11-01T10:00:00+00:00"
    )
    _gravar_consulta_e_mensagem(
        conn, ana, "pedir", "cordial", "Entregue 1, da Ana.", "entregue", "2026-11-02T09:00:00+00:00"
    )
    _gravar_consulta_e_mensagem(
        conn, ana, "pedir", "cordial", "Entregue 2, da Ana.", "entregue", "2026-11-02T09:30:00+00:00"
    )

    moldes = consulta_contato.moldes_por_contexto(conn, joao, "pedir", "cordial", "advogado", 2)

    assert len(moldes) == 1
    assert moldes[0].mensagem == "Mensagem usada, do Luiz."
    assert moldes[0].bom is True


def test_sem_usado_so_a_entregue_mais_recente_entra(tmp_path: Path) -> None:
    conn = _abrir(tmp_path)
    joao = _contato(conn, "João", "advogado")
    luiz = _contato(conn, "Luiz", "advogado")
    _gravar_consulta_e_mensagem(
        conn, luiz, "pedir", "cordial", "Entregue mais antiga.", "entregue", "2026-11-01T09:00:00+00:00"
    )
    _gravar_consulta_e_mensagem(
        conn, luiz, "pedir", "cordial", "Entregue mais recente.", "entregue", "2026-11-02T09:00:00+00:00"
    )

    moldes = consulta_contato.moldes_por_contexto(conn, joao, "pedir", "cordial", "advogado", 2)

    assert len(moldes) == 1
    assert moldes[0].mensagem == "Entregue mais recente."
    assert moldes[0].bom is False


def test_sem_nenhuma_mensagem_anterior_lista_vazia(tmp_path: Path) -> None:
    conn = _abrir(tmp_path)
    joao = _contato(conn, "João", "advogado")

    moldes = consulta_contato.moldes_por_contexto(conn, joao, "pedir", "cordial", "advogado", 2)

    assert moldes == []


def test_prompt_distingue_usei_de_entreguei_nao_confirmado(tmp_path: Path) -> None:
    conn = _abrir(tmp_path)
    joao_id = _contato(conn, "João", "advogado")
    luiz = _contato(conn, "Luiz", "advogado")
    _gravar_consulta_e_mensagem(
        conn, luiz, "pedir", "cordial", "Mensagem nunca confirmada.", "entregue", AGORA
    )
    joao = perfis.obter_por_id(conn, joao_id)
    assert joao is not None

    linhas, molde_origem_id = redacao_mod._moldes(conn, joao, _pedido(), 2)

    assert linhas == ['[entreguei, ainda não confirmado se funcionou] "Mensagem nunca confirmada."']
    assert molde_origem_id is not None


def test_mensagem_redigida_a_partir_de_molde_grava_molde_origem_id(tmp_path: Path) -> None:
    conn = _abrir(tmp_path)
    luiz = _contato(conn, "Luiz", "advogado")
    molde_id = _gravar_consulta_e_mensagem(
        conn, luiz, "pedir", "cordial", "Mensagem que funcionou com o Luiz.", "usado", AGORA
    )
    joao_id = _contato(conn, "João", "advogado")
    joao = perfis.obter_por_id(conn, joao_id)
    assert joao is not None
    usuario = perfis.upsert_usuario(conn, "Rafael", AGORA)
    consulta = consulta_contato.inserir(conn, joao_id, AGORA, "{}", None, "[]")
    assert consulta.id is not None
    conn.commit()
    resultado = ResultadoConsulta(joao_id, consulta.id, [], ResumoRedeSocial(), "")

    redacao = redacao_mod.redigir(
        _ClienteFalso(), conn, _pedido(), resultado, joao, usuario, AGORA, frase="pedir apoio"
    )
    assert redacao.molde_origem_id == molde_id
    redacao_mod.registrar(conn, consulta.id, redacao, AGORA)

    (gravado,) = conn.execute(
        "SELECT molde_origem_id FROM gancho_uso WHERE consulta_id = ? AND assunto_id IS NULL",
        (consulta.id,),
    ).fetchone()
    assert gravado == molde_id


def test_mensagem_redigida_sem_molde_grava_molde_origem_id_nulo(tmp_path: Path) -> None:
    conn = _abrir(tmp_path)
    joao_id = _contato(conn, "João", "advogado")
    joao = perfis.obter_por_id(conn, joao_id)
    assert joao is not None
    usuario = perfis.upsert_usuario(conn, "Rafael", AGORA)
    consulta = consulta_contato.inserir(conn, joao_id, AGORA, "{}", None, "[]")
    assert consulta.id is not None
    conn.commit()
    resultado = ResultadoConsulta(joao_id, consulta.id, [], ResumoRedeSocial(), "")

    redacao = redacao_mod.redigir(
        _ClienteFalso(), conn, _pedido(), resultado, joao, usuario, AGORA, frase="pedir apoio"
    )
    assert redacao.molde_origem_id is None
    redacao_mod.registrar(conn, consulta.id, redacao, AGORA)

    (gravado,) = conn.execute(
        "SELECT molde_origem_id FROM gancho_uso WHERE consulta_id = ? AND assunto_id IS NULL",
        (consulta.id,),
    ).fetchone()
    assert gravado is None
