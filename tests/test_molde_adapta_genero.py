"""O molde entra no prompt com o gênero gramatical de quem recebe agora; o modelo (aqui, simulado,
lendo o prompt) concorda no gênero certo ao adaptar — masculino na fonte, feminino no destino, e
vice-versa (brief 048)."""

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

AGORA = "2026-10-30T10:00:00+00:00"


class _ClienteAdaptaGenero:
    """Lê o gênero gramatical escrito no prompt e concorda a mensagem — proxy do que o modelo real
    faz; a adaptação semântica de verdade é o critério de aceite 2 do brief, testado por Sidarta."""

    def gerar_json(self, tarefa_nome: str, prompt: str, esquema: type[Any]) -> Any:
        assert tarefa_nome == "redigir_ganchos"
        if "Gênero gramatical: feminino" in prompt:
            mensagem = "Oi, Maria, tudo bem? Que bom ter você, cara colega advogada, na nossa chapa."
        else:
            mensagem = "Oi, Luiz, tudo bem? Que bom ter você, caro colega advogado, na nossa chapa."
        return RespostaRedacao(
            ganchos=[Gancho(mensagem=mensagem, por_que_para_esta_pessoa="convite para a chapa")]
        )


def _abrir(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


def _contato(conn: sqlite3.Connection, nome: str, cargo: str, genero: str) -> int:
    perfil = perfis.inserir_novo_contato(conn, nome, None, None, AGORA)
    assert perfil.id is not None
    perfis.atualizar_ficha_manual(conn, perfil.id, {"cargo": cargo, "genero_gramatical": genero}, AGORA)
    conn.commit()
    return perfil.id


def _molde(conn: sqlite3.Connection, perfil_id: int, mensagem: str) -> None:
    contexto_json = json.dumps({"objetivo_categoria": "pedir", "registro": "cordial"})
    consulta = consulta_contato.inserir(conn, perfil_id, AGORA, contexto_json, None, "[]")
    assert consulta.id is not None
    gancho_json = json.dumps({"assunto_id": None, "mensagem": mensagem})
    gancho_uso.inserir_entregues(conn, consulta.id, [(None, gancho_json)], AGORA)
    gancho_uso.marcar(conn, consulta.id, None, "usado", AGORA)
    conn.commit()


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


def test_molde_masculino_vira_feminino_para_contato_mulher(tmp_path: Path) -> None:
    conn = _abrir(tmp_path)
    luiz = _contato(conn, "Luiz", "advogado", "masculino")
    _molde(conn, luiz, "Oi, Luiz, tudo bem? Que bom ter você, caro colega advogado, na nossa chapa.")
    maria_id = _contato(conn, "Maria", "advogado", "feminino")
    maria = perfis.obter_por_id(conn, maria_id)
    assert maria is not None
    usuario = perfis.upsert_usuario(conn, "Rafael", AGORA)
    consulta = consulta_contato.inserir(conn, maria_id, AGORA, "{}", None, "[]")
    assert consulta.id is not None
    conn.commit()
    resultado = ResultadoConsulta(maria_id, consulta.id, [], ResumoRedeSocial(), "")

    redacao = redacao_mod.redigir(
        _ClienteAdaptaGenero(), conn, _pedido(), resultado, maria, usuario, AGORA, frase="pedir apoio"
    )

    assert redacao.ganchos
    mensagem = redacao.ganchos[0].mensagem
    assert "advogada" in mensagem
    assert "advogado" not in mensagem


def test_molde_feminino_vira_masculino_para_contato_homem(tmp_path: Path) -> None:
    conn = _abrir(tmp_path)
    ana = _contato(conn, "Ana", "advogado", "feminino")
    _molde(conn, ana, "Oi, Ana, tudo bem? Que bom ter você, cara colega advogada, na nossa chapa.")
    joao_id = _contato(conn, "João", "advogado", "masculino")
    joao = perfis.obter_por_id(conn, joao_id)
    assert joao is not None
    usuario = perfis.upsert_usuario(conn, "Rafael", AGORA)
    consulta = consulta_contato.inserir(conn, joao_id, AGORA, "{}", None, "[]")
    assert consulta.id is not None
    conn.commit()
    resultado = ResultadoConsulta(joao_id, consulta.id, [], ResumoRedeSocial(), "")

    redacao = redacao_mod.redigir(
        _ClienteAdaptaGenero(), conn, _pedido(), resultado, joao, usuario, AGORA, frase="pedir apoio"
    )

    assert redacao.ganchos
    mensagem = redacao.ganchos[0].mensagem
    assert "advogado" in mensagem
    assert "advogada" not in mensagem
