"""O que o usuário escreve chega inteiro ao modelo e é conferido inteiro (brief 081): comentário no
histórico, nota do contato, comentário do molde e a lista `evitar`."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import replace
from pathlib import Path

import pytest

from agente_nw.nucleo import historico, redacao
from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import consulta_contato, gancho_uso, nota_contato, perfis
from agente_nw.nucleo.modelos.assunto import Assunto
from agente_nw.nucleo.modelos.pedido import PedidoExtraido
from agente_nw.nucleo.prompts import redigir_ganchos as prompt
from agente_nw.nucleo.relevancia.candidatos import termo_evitado
from tests.test_redacao_prompt import _entrada

AGORA = "2026-10-30T10:00:00+00:00"


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


def _contato(conn: sqlite3.Connection, nome: str, cargo: str | None = None) -> int:
    perfil = perfis.inserir_novo_contato(conn, nome, None, None, AGORA)
    assert perfil.id is not None
    if cargo:
        perfis.atualizar_ficha_manual(conn, perfil.id, {"cargo": cargo}, AGORA)
    conn.commit()
    return perfil.id


def _pedido(**campos: object) -> PedidoExtraido:
    base: dict[str, object] = {
        "pessoa_nome": "Vera",
        "objetivo": "pedir",
        "objetivo_texto": "pedir uma indicação",
        "meio": "whatsapp",
        "registro": "cordial",
        "assunto_principal": "aviação",
        "termos_busca": ["aviação"],
        "confianca": 0.9,
    }
    base.update(campos)
    return PedidoExtraido.model_validate(base)


def _termos(n: int) -> list[str]:
    return [f"termo{i}" for i in range(1, n + 1)]


def test_comentario_de_2000_caracteres_chega_inteiro_ao_prompt(conn: sqlite3.Connection) -> None:
    perfil_id = _contato(conn, "Vera")
    consulta = consulta_contato.inserir(conn, perfil_id, AGORA, "{}", None, "[]")
    assert consulta.id is not None
    gancho = json.dumps({"assunto_id": None, "mensagem": "Oi, Vera!"})
    gancho_uso.inserir_entregues(conn, consulta.id, [(None, gancho)], AGORA)
    comentario = "".join(str(i % 10) for i in range(1999)) + "Z"
    gancho_uso.comentar(conn, consulta.id, None, comentario, AGORA)
    conn.commit()

    texto = historico.historico_recente_para_prompt(conn, perfil_id)

    assert f'comentário do usuário: "{comentario}"' in texto
    assert historico.comentarios_da_consulta(consulta, conn).endswith(f'"{comentario}"')


def test_nota_de_1500_e_comentario_de_molde_de_1000_chegam_inteiros(conn: sqlite3.Connection) -> None:
    vera = _contato(conn, "Vera", "advogada")
    outra = _contato(conn, "Lia", "advogada")
    nota = "N" * 1499 + "!"
    nota_contato.inserir(conn, vera, nota, AGORA)
    contexto = json.dumps({"objetivo_categoria": "pedir", "registro": "cordial"})
    consulta = consulta_contato.inserir(conn, outra, AGORA, contexto, None, "[]")
    assert consulta.id is not None
    gancho_uso.inserir_entregues(
        conn, consulta.id, [(None, json.dumps({"assunto_id": None, "mensagem": "Molde."}))], AGORA
    )
    gancho_uso.marcar(conn, consulta.id, None, "usado", AGORA)
    comentario = "M" * 999 + "!"
    gancho_uso.comentar(conn, consulta.id, None, comentario, AGORA)
    conn.commit()
    contato = perfis.obter_por_id(conn, vera)
    assert contato is not None

    notas = redacao._notas(conn, vera)
    linhas, _origem = redacao._moldes(conn, contato, _pedido(), 2)

    assert notas == [f"[{AGORA[:10]}] {nota}"]
    assert linhas == [f'[usei] "Molde." — comentário do usuário: "{comentario}"']
    entrada = replace(_entrada(), notas=notas, moldes=linhas)
    texto = prompt.construir_prompt(entrada)
    assert nota in texto and comentario in texto


def _consulta_com_mensagem(conn: sqlite3.Connection, perfil_id: int, mensagem: str) -> int:
    consulta = consulta_contato.inserir(conn, perfil_id, AGORA, "{}", None, "[]")
    assert consulta.id is not None
    gancho = json.dumps({"assunto_id": None, "mensagem": mensagem})
    gancho_uso.inserir_entregues(conn, consulta.id, [(None, gancho)], AGORA)
    conn.commit()
    return consulta.id


def test_mensagem_entregue_de_500_caracteres_chega_inteira(conn: sqlite3.Connection) -> None:
    # Muda de intenção por decisão de Sidarta (brief 099): antes exigia só os 100 primeiros caracteres.
    perfil_id = _contato(conn, "Vera")
    mensagem = "a" * 100 + "b" * 399 + "!"
    _consulta_com_mensagem(conn, perfil_id, mensagem)

    texto = historico.historico_recente_para_prompt(conn, perfil_id)

    assert f'mensagem: "{mensagem}"' in texto


def test_mensagem_entregue_de_3000_caracteres_chega_inteira_com_o_ultimo_caractere(
    conn: sqlite3.Connection,
) -> None:
    perfil_id = _contato(conn, "Vera")
    mensagem = "".join(str(i % 10) for i in range(2999)) + "Z"
    _consulta_com_mensagem(conn, perfil_id, mensagem)

    texto = historico.historico_recente_para_prompt(conn, perfil_id)

    assert f'mensagem: "{mensagem}"' in texto
    assert len(mensagem) == 3000


def test_marcador_no_fim_da_mensagem_aparece_no_prompt_de_redigir_ganchos(conn: sqlite3.Connection) -> None:
    perfil_id = _contato(conn, "Vera")
    mensagem = "início " + "x" * 2900 + " MARCADOR-FINAL-099"
    _consulta_com_mensagem(conn, perfil_id, mensagem)
    linhas = [historico.historico_recente_para_prompt(conn, perfil_id)]
    entrada = replace(_entrada(), historico=linhas)

    texto = prompt.construir_prompt(entrada)

    assert "MARCADOR-FINAL-099" in texto
    assert mensagem in texto


def test_prompt_que_estoura_o_orcamento_nao_corta_a_mensagem_e_sacrifica_outros_blocos(
    conn: sqlite3.Connection,
) -> None:
    perfil_id = _contato(conn, "Vera")
    mensagem = "m" * 2999 + "Z"
    _consulta_com_mensagem(conn, perfil_id, mensagem)
    entregue = historico.historico_recente_para_prompt(conn, perfil_id)
    nota = "nota " + "N" * 300
    comentario = 'comentário do usuário: "' + "H" * 300 + '"'
    base = _entrada(fatos=30, historico=2, palavras_por_linha=60)
    entrada = replace(
        base,
        notas=[nota],
        historico=[entregue, "[2026-10-02] consulta dois sem mensagem"],
        historico_comentarios=["", f"[2026-10-02] {comentario}"],
        trocas_whatsapp=["troca " + "w" * 50] * 5,
    )

    for limite in (1500, 200, 1):
        texto = prompt.construir_prompt(entrada, limite)

        assert mensagem in texto
        assert nota in texto
        assert comentario in texto
        assert "fato 29:" not in texto
    assert prompt.cortar_por_tamanho(entrada, 1).trocas_whatsapp == []


def test_comentario_do_usuario_continua_inteiro_ao_lado_da_mensagem(conn: sqlite3.Connection) -> None:
    perfil_id = _contato(conn, "Vera")
    consulta_id = _consulta_com_mensagem(conn, perfil_id, "m" * 800)
    comentario = "c" * 1999 + "!"
    gancho_uso.comentar(conn, consulta_id, None, comentario, AGORA)
    conn.commit()

    texto = historico.historico_recente_para_prompt(conn, perfil_id)

    assert f'mensagem: "{"m" * 800}"' in texto
    assert f'comentário do usuário: "{comentario}"' in texto


def test_evitar_mantem_oito_termos_e_interessa_continua_em_cinco() -> None:
    pedido = _pedido(evitar=_termos(8), interessa=_termos(8))

    assert pedido.evitar == _termos(8)
    assert pedido.interessa == _termos(5)


def test_mensagem_que_cita_o_oitavo_termo_de_evitar_e_detectada() -> None:
    pedido = _pedido(evitar=_termos(8))
    assunto = Assunto(
        titulo_gerado="Novidades sobre Termo8 hoje",
        primeiro_visto=AGORA,
        ultimo_visto=AGORA,
        status="novo",
    )

    assert termo_evitado(assunto, pedido.evitar) is True


def test_corte_por_tamanho_sacrifica_outros_blocos_e_preserva_o_texto_do_usuario() -> None:
    nota = "nota " + "N" * 300
    comentario_historico = 'comentário do usuário: "' + "H" * 300 + '"'
    molde_com = '[usei] "Molde com." — comentário do usuário: "' + "M" * 300 + '"'
    molde_sem = '[usei] "Molde sem comentário."'
    base = _entrada(fatos=30, historico=3, palavras_por_linha=60)
    entrada = replace(
        base,
        notas=[nota],
        historico=[*base.historico[:1], "[2026-10-02] consulta dois", "[2026-10-01] consulta três"],
        historico_comentarios=["", f"[2026-10-02] {comentario_historico}", ""],
        moldes=[molde_com, molde_sem],
        moldes_comentados=[molde_com],
        molde_origem_id=7,
        trocas_whatsapp=["troca " + "w" * 50] * 5,
    )

    for limite in (1500, 200, 1):
        cortada = prompt.cortar_por_tamanho(entrada, limite)
        texto = prompt.construir_prompt(entrada, limite)

        assert nota in texto
        assert comentario_historico in texto
        assert molde_com in texto
        assert "Molde sem comentário" not in texto or limite == 1500 and cortada.moldes == entrada.moldes
        assert "fato 29:" not in texto
    assert prompt.cortar_por_tamanho(entrada, 1).molde_origem_id == 7
    assert prompt.cortar_por_tamanho(entrada, 1).trocas_whatsapp == []
