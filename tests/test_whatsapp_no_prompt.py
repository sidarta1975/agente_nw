"""Tom da relação na redação: as últimas trocas do WhatsApp no HISTÓRICO (brief 061)."""

from __future__ import annotations

import sqlite3
from dataclasses import replace
from datetime import datetime
from pathlib import Path

import pytest

from agente_nw.nucleo import redacao as redacao_mod
from agente_nw.nucleo.consulta import ItemMenu, ResultadoConsulta, ResumoRedeSocial
from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import conversa as conversa_q
from agente_nw.nucleo.database.queries import perfis
from agente_nw.nucleo.modelos.pedido import PedidoExtraido
from agente_nw.nucleo.prompts import redigir_ganchos as prompt_mod
from agente_nw.nucleo.prompts.redigir_ganchos import EntradaRedacao

AGORA = "2026-10-25T10:00:00+00:00"


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


def _pedido() -> PedidoExtraido:
    return PedidoExtraido.model_validate(
        {
            "pessoa_nome": "Joana",
            "objetivo": "retomar",
            "objetivo_texto": "voltar a falar com ela",
            "meio": "whatsapp",
            "registro": "cordial",
            "assunto_principal": "café",
            "termos_busca": ["café"],
            "confianca": 0.9,
        }
    )


class _SemEmbeddings:
    pass


def test_as_ultimas_trocas_aparecem_no_historico(conn: sqlite3.Connection) -> None:
    usuario = perfis.upsert_usuario(conn, "Davi Pires", AGORA)
    contato = perfis.inserir_novo_contato(conn, "Joana Prado", None, None, AGORA)
    assert contato.id is not None
    conn.commit()
    for i in range(15):
        conversa_q.inserir_mensagem(
            conn,
            contato.id,
            "usuario" if i % 2 == 0 else "contato",
            datetime(2026, 9, 1, 10, i).isoformat(),
            f"mensagem {i}",
            AGORA,
        )
    conn.commit()
    resultado = ResultadoConsulta(contato.id, 1, [], ResumoRedeSocial(), "")

    entrada = redacao_mod.montar_entrada(
        conn, _SemEmbeddings(), _pedido(), "frase", resultado, contato, usuario, [], 12, 10
    )

    assert len(entrada.trocas_whatsapp) == 10
    assert entrada.trocas_whatsapp[0] == "Joana Prado: mensagem 5"
    assert entrada.trocas_whatsapp[-1] == "você: mensagem 14"
    prompt = prompt_mod.construir_prompt(entrada)
    assert "Conversa recente no WhatsApp (para o tom; não é fato atual):" in prompt
    assert "- Joana Prado: mensagem 5" in prompt


def _entrada_minima(assunto: ItemMenu | None = None) -> EntradaRedacao:
    return EntradaRedacao(
        usuario_nome="Davi Pires",
        usuario_temas=[],
        contato_nome="Joana Prado",
        contato_ficha=[],
        vinculo=None,
        tempo_sem_contato=None,
        fatos=[],
        cabecalho_rede=None,
        pedido=_pedido(),
        frase="frase",
        historico=[],
        assuntos=[],
    )


def test_conversa_sai_do_prompt_antes_das_notas_perto_do_limite() -> None:
    linha_longa = " ".join(["oi"] * 6000)
    entrada = replace(
        _entrada_minima(),
        notas=["nota curta do usuário"],
        trocas_whatsapp=[f"você: {linha_longa}"],
    )
    assert prompt_mod.estimar_tokens(prompt_mod.construir_prompt(entrada, limite_tokens=10**9)) > 6000

    texto = prompt_mod.construir_prompt(entrada, limite_tokens=6000)

    assert "nota curta do usuário" in texto
    assert "Conversa recente no WhatsApp" not in texto
    assert linha_longa not in texto
