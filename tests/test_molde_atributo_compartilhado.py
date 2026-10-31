"""O bloco de moldes leva o texto da mensagem-fonte e a instrução de manter o que é compartilhado (a
profissão, por exemplo) e trocar ou tirar o que só cabia à pessoa de origem (brief 048)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from agente_nw.nucleo import redacao as redacao_mod
from agente_nw.nucleo.consulta import ResultadoConsulta, ResumoRedeSocial
from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import consulta_contato, gancho_uso, perfis
from agente_nw.nucleo.modelos.pedido import PedidoExtraido
from agente_nw.nucleo.prompts import redigir_ganchos as prompt_mod
from agente_nw.nucleo.prompts.redigir_ganchos import EntradaRedacao

AGORA = "2026-10-30T10:00:00+00:00"


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


def _entrada_com_molde(moldes: list[str]) -> EntradaRedacao:
    return EntradaRedacao(
        usuario_nome="Rafael",
        usuario_temas=[],
        contato_nome="Maria",
        contato_ficha=["cargo: advogado"],
        vinculo=None,
        tempo_sem_contato=None,
        fatos=[],
        cabecalho_rede=None,
        pedido=_pedido(),
        frase="pedir apoio",
        historico=[],
        assuntos=[],
        moldes=moldes,
    )


def test_a_mensagem_molde_entra_no_prompt_com_a_instrucao_de_manter_o_compartilhado() -> None:
    molde = '[usei] "Luiz, você também é advogado e esteve no conselho da OAB-SP em 2019."'

    prompt = prompt_mod.construir_prompt(_entrada_com_molde([molde]))

    assert "MENSAGENS QUE JÁ FUNCIONARAM NESTE TIPO DE CONTEXTO" in prompt
    assert molde in prompt
    assert "carregue o que serve" in prompt
    assert "troque ou tire o detalhe que só cabia à pessoa de origem" in prompt


def test_sem_molde_o_bloco_nao_aparece() -> None:
    prompt = prompt_mod.construir_prompt(_entrada_com_molde([]))

    assert "MENSAGENS QUE JÁ FUNCIONARAM" not in prompt


def _abrir(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


class _SemEmbeddings:
    pass


def test_o_atributo_compartilhado_a_profissao_e_o_que_faz_o_molde_ser_recuperado(tmp_path: Path) -> None:
    conn = _abrir(tmp_path)
    luiz = perfis.inserir_novo_contato(conn, "Luiz", None, None, AGORA)
    assert luiz.id is not None
    perfis.atualizar_ficha_manual(conn, luiz.id, {"cargo": "advogado"}, AGORA)
    contexto_json = json.dumps({"objetivo_categoria": "pedir", "registro": "cordial"})
    consulta = consulta_contato.inserir(conn, luiz.id, AGORA, contexto_json, None, "[]")
    assert consulta.id is not None
    gancho_json = json.dumps(
        {"assunto_id": None, "mensagem": "Luiz, você também é advogado e esteve no conselho da OAB-SP."}
    )
    gancho_uso.inserir_entregues(conn, consulta.id, [(None, gancho_json)], AGORA)
    gancho_uso.marcar(conn, consulta.id, None, "usado", AGORA)
    joao_criado = perfis.inserir_novo_contato(conn, "João", None, None, AGORA)
    assert joao_criado.id is not None
    perfis.atualizar_ficha_manual(conn, joao_criado.id, {"cargo": "advogado"}, AGORA)
    joao = perfis.obter_por_id(conn, joao_criado.id)
    assert joao is not None and joao.id is not None
    usuario = perfis.upsert_usuario(conn, "Rafael", AGORA)
    joao_consulta = consulta_contato.inserir(conn, joao.id, AGORA, "{}", None, "[]")
    assert joao_consulta.id is not None
    conn.commit()
    resultado = ResultadoConsulta(joao.id, joao_consulta.id, [], ResumoRedeSocial(), "")

    entrada = redacao_mod.montar_entrada(
        conn, _SemEmbeddings(), _pedido(), "pedir apoio", resultado, joao, usuario, []
    )

    assert len(entrada.moldes) == 1
    assert "advogado" in entrada.moldes[0]
