"""Cartão e qualificação leem o corpo de todos os itens do assunto (brief 090).

Cada item ganha um resumo guardado, feito com o texto inteiro (em partes, quando não cabe numa chamada);
o cartão e a qualificação recebem os resumos de **todos** os itens, sem o corte de 300 caracteres e sem o
teto de 5. Resumos que não cabem na janela são consolidados em dois níveis, nunca cortados. LLM falso.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

import pytest

from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import assuntos, fontes, itens, perfil_tema, perfis
from agente_nw.nucleo.database.queries import temas as queries_temas
from agente_nw.nucleo.estimativa_tokens import estimar_tokens_conservador
from agente_nw.nucleo.llm import FalhaJsonInvalido
from agente_nw.nucleo.modelos.assunto import Assunto
from agente_nw.nucleo.modelos.cartao import RespostaCartao
from agente_nw.nucleo.modelos.item import Item
from agente_nw.nucleo.modelos.qualificacao import RespostaQualificar
from agente_nw.nucleo.modelos.rotulo import RespostaRotulo
from agente_nw.nucleo.prompts import cartao as prompt_cartao
from agente_nw.nucleo.prompts import qualificar as prompt_qualificar
from agente_nw.nucleo.prompts import rotular as prompt_rotular
from agente_nw.nucleo.prompts.seguranca import cercar_dado_externo
from agente_nw.nucleo.relevancia import cartoes, qualificador
from tests.llm_falso import ProvenienciaFalsa

AGORA = "2026-01-01T00:00:00+00:00"
RAIZ = Path(__file__).resolve().parent.parent
_MARCA = re.compile(r"ITEM-\d{2}")
_CARTAO_SEM_NUMERO = "O assunto avançou.\nHouve reação.\nO desfecho segue aberto."


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


def _vetor(*valores: float) -> list[float]:
    return list(valores) + [0.0] * (1024 - len(valores))


def _corpo_longo(marca: str, palavras: int = 400) -> str:
    """Corpo acima do tamanho de um resumo (precisa de chamada ao modelo), com a marca no fim."""
    return " ".join(["notícia"] * palavras) + f" {marca}"


class _Cliente(ProvenienciaFalsa):
    """Resumo do item, consolidação e cartão saem da tarefa `cartao`, distinguidos pela versão do prompt.

    O resumo falso devolve as marcas `ITEM-NN` (e o `fim-do-sexto`) achadas no prompt, mais `enchimento`
    palavras; a consolidação devolve só as marcas. Assim dá para seguir cada item até o cartão."""

    def __init__(self, janelas: dict[str, int] | None = None, enchimento: int = 0) -> None:
        self.janelas = janelas or {}
        self.enchimento = enchimento
        self.chamadas: list[tuple[str, str | None, str]] = []
        self.falhar_resumo = False

    def num_ctx(self, tarefa_nome: str) -> int:
        return self.janelas.get(tarefa_nome, 4096)

    def prompts(self, versao: str) -> list[str]:
        return [prompt for _, v, prompt in self.chamadas if v == versao]

    def gerar_json(
        self, tarefa_nome: str, prompt: str, esquema: type[Any], *, versao_prompt: str | None = None
    ) -> Any:
        self.chamadas.append((tarefa_nome, versao_prompt, prompt))
        assert estimar_tokens_conservador(prompt) <= self.num_ctx(tarefa_nome), "prompt acima da janela"
        marcas = " ".join(dict.fromkeys(_MARCA.findall(prompt)))
        if tarefa_nome == "rotular":
            return RespostaRotulo(titulo="Título gerado")
        if tarefa_nome == "qualificar":
            return RespostaQualificar(substancial=0.8, conversavel=0.8, temas=[], justificativa="ok")
        assert tarefa_nome == "cartao"
        if versao_prompt == prompt_cartao.VERSAO_RESUMO_ITEM:
            if self.falhar_resumo:
                raise FalhaJsonInvalido(tarefa_nome, 1, "resposta inválida")
            fim = " fim-do-sexto" if "fim-do-sexto" in prompt else ""
            return RespostaCartao(resumo=f"resumo {marcas}{fim} " + "fato " * self.enchimento)
        if versao_prompt == prompt_cartao.VERSAO_CONSOLIDACAO:
            return RespostaCartao(resumo=f"consolidado {marcas}")
        if versao_prompt == prompt_cartao.VERSAO:
            return RespostaCartao(resumo=_CARTAO_SEM_NUMERO)
        raise AssertionError(f"chamada inesperada: {tarefa_nome} {versao_prompt}")


def _criar_assunto(
    conn: sqlite3.Connection, corpos: list[str], titulo: str | None = "Assunto", qualificado: bool = False
) -> int:
    fonte = fontes.obter_ou_criar(conn, "g1.globo.com", "https://g1.globo.com/rss", "g1.globo.com", "rss", 5)
    assert fonte.id is not None
    assunto_id = assuntos.inserir(
        conn,
        Assunto(
            titulo_gerado=titulo,
            primeiro_visto=AGORA,
            ultimo_visto=AGORA,
            n_itens=len(corpos),
            status="novo",
            substancial=0.9 if qualificado else None,
            conversavel=0.9 if qualificado else None,
        ),
    )
    assuntos.gravar_centroide(conn, assunto_id, _vetor(1.0), modelo_embedding="bge-m3")
    for indice, corpo in enumerate(corpos, start=1):
        itens.inserir(
            conn,
            Item(
                fonte_id=fonte.id,
                url_canonica=f"https://exemplo.com/{assunto_id}/{indice}",
                titulo=f"Manchete {indice}",
                texto=corpo,
                coletado_em=AGORA,
                hash_titulo=f"hash-{assunto_id}-{indice}",
                assunto_id=assunto_id,
            ),
        )
    conn.commit()
    return assunto_id


def _resumo_gravado(conn: sqlite3.Connection, assunto_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT resumo, resumo_versao, resumo_partes FROM item WHERE assunto_id = ? ORDER BY id",
        (assunto_id,),
    ).fetchall()


# --- 1. o fim do corpo do 6º item chega ao cartão -----------------------------------------------------


def test_marcador_no_ultimo_caractere_do_sexto_item_chega_ao_prompt_do_cartao(
    conn: sqlite3.Connection,
) -> None:
    corpos = [_corpo_longo(f"ITEM-{i:02d}") for i in range(1, 6)]
    sexto = ("Parágrafo comprido de uma notícia de verdade. " * 1200) + "fim-do-sexto"
    assert sexto.endswith("fim-do-sexto") and len(sexto) > 50_000
    assunto_id = _criar_assunto(conn, [*corpos, sexto])
    cliente = _Cliente()

    assert cartoes.gerar_cartao(cliente, conn, assunto_id) == _CARTAO_SEM_NUMERO

    resumos_do_sexto = [p for p in cliente.prompts(prompt_cartao.VERSAO_RESUMO_ITEM) if "Manchete 6" in p]
    assert len(resumos_do_sexto) > 1, "o sexto item não cabe numa chamada: é lido em partes"
    assert "fim-do-sexto" in resumos_do_sexto[-1]
    (prompt_final,) = cliente.prompts(prompt_cartao.VERSAO)
    assert "fim-do-sexto" in prompt_final
    assert _resumo_gravado(conn, assunto_id)[5]["resumo_partes"] == len(resumos_do_sexto)


# --- 2. os 40 itens aparecem, nenhum descartado -------------------------------------------------------


def test_assunto_com_40_itens_tem_os_40_representados_no_cartao(conn: sqlite3.Connection) -> None:
    assunto_id = _criar_assunto(conn, [_corpo_longo(f"ITEM-{i:02d}") for i in range(1, 41)])
    cliente = _Cliente(janelas={"cartao": 100_000})

    assert cartoes.gerar_cartao(cliente, conn, assunto_id) is not None

    (prompt_final,) = cliente.prompts(prompt_cartao.VERSAO)
    assert set(_MARCA.findall(prompt_final)) == {f"ITEM-{i:02d}" for i in range(1, 41)}
    assert cliente.prompts(prompt_cartao.VERSAO_CONSOLIDACAO) == []
    linha = conn.execute(
        "SELECT cartao_versao, cartao_itens, cartao_niveis FROM assunto WHERE id = ?", (assunto_id,)
    ).fetchone()
    assert tuple(linha) == (prompt_cartao.VERSAO, 40, 1)


# --- 3. resumos acima do orçamento: consolidação em dois níveis ---------------------------------------


def test_resumos_acima_do_orcamento_sao_consolidados_em_dois_niveis_sem_perder_item(
    conn: sqlite3.Connection,
) -> None:
    assunto_id = _criar_assunto(conn, [_corpo_longo(f"ITEM-{i:02d}") for i in range(1, 41)])
    cliente = _Cliente(janelas={"cartao": 4096}, enchimento=150)

    assert cartoes.gerar_cartao(cliente, conn, assunto_id) is not None

    resumos = [linha["resumo"] for linha in _resumo_gravado(conn, assunto_id)]
    entradas = [(f"Manchete {i}", "g1.globo.com", r) for i, r in enumerate(resumos, start=1)]
    assert estimar_tokens_conservador(prompt_cartao.construir_prompt("Assunto", entradas)) > 4096
    consolidacoes = cliente.prompts(prompt_cartao.VERSAO_CONSOLIDACAO)
    assert len(consolidacoes) > 1
    cobertos_na_consolidacao = {marca for prompt in consolidacoes for marca in _MARCA.findall(prompt)}
    assert cobertos_na_consolidacao == {f"ITEM-{i:02d}" for i in range(1, 41)}
    (prompt_final,) = cliente.prompts(prompt_cartao.VERSAO)
    assert set(_MARCA.findall(prompt_final)) == {f"ITEM-{i:02d}" for i in range(1, 41)}
    linha = conn.execute(
        "SELECT cartao_itens, cartao_niveis FROM assunto WHERE id = ?", (assunto_id,)
    ).fetchone()
    assert tuple(linha) == (40, 2)


# --- 4. texto curto: o resumo é o próprio texto -------------------------------------------------------


def test_texto_curto_entra_no_prompt_identico_ao_original(conn: sqlite3.Connection) -> None:
    curto = "Prefeitura anuncia obra na orla; moradores cobram prazo e detalhes do projeto."
    assunto_id = _criar_assunto(conn, [curto])
    cliente = _Cliente()

    assert cartoes.gerar_cartao(cliente, conn, assunto_id) is not None

    assert cliente.prompts(prompt_cartao.VERSAO_RESUMO_ITEM) == []
    (prompt_final,) = cliente.prompts(prompt_cartao.VERSAO)
    assert cercar_dado_externo(curto) in prompt_final
    assert tuple(_resumo_gravado(conn, assunto_id)[0]) == (curto, prompt_cartao.VERSAO_RESUMO_ITEM, 0)


def test_resumo_de_item_que_cabe_numa_chamada_leva_o_texto_inteiro_sem_aviso_de_parte(
    conn: sqlite3.Connection,
) -> None:
    corpo = _corpo_longo("ITEM-01")
    assunto_id = _criar_assunto(conn, [corpo])
    cliente = _Cliente()

    cartoes.gerar_cartao(cliente, conn, assunto_id)

    (prompt_resumo,) = cliente.prompts(prompt_cartao.VERSAO_RESUMO_ITEM)
    assert cercar_dado_externo(corpo) in prompt_resumo
    assert "[parte " not in prompt_resumo
    assert tuple(_resumo_gravado(conn, assunto_id)[0])[1:] == (prompt_cartao.VERSAO_RESUMO_ITEM, 1)


# --- 5. versões -------------------------------------------------------------------------------------


def test_cartao_antigo_nao_e_confundido_com_o_novo_e_nao_e_regravado(conn: sqlite3.Connection) -> None:
    antigo = _criar_assunto(conn, [_corpo_longo("ITEM-01")], qualificado=True)
    assuntos.gravar_cartao(conn, antigo, "Cartão antigo, de 300 caracteres.")
    conn.execute("UPDATE assunto SET cartao_versao = NULL, cartao_itens = NULL, cartao_niveis = NULL")
    novo = _criar_assunto(conn, [_corpo_longo("ITEM-02")], qualificado=True)
    conn.commit()

    resumo = cartoes.gerar_pendentes(_Cliente(), conn, 10)

    assert resumo.gerados == 1
    velho = assuntos.obter_por_id(conn, antigo)
    assert velho is not None and velho.resumo_cartao == "Cartão antigo, de 300 caracteres."
    assert assuntos.versao_do_cartao(conn, antigo) is None
    assert assuntos.versao_do_cartao(conn, novo) == prompt_cartao.VERSAO
    assert prompt_cartao.VERSAO != "2026-11-02-1"
    assert prompt_qualificar.VERSAO != "2026-11-02-1"
    assert prompt_rotular.VERSAO != "2026-11-02-1"


def test_resumo_de_versao_antiga_e_refeito_e_o_da_versao_atual_e_reaproveitado(
    conn: sqlite3.Connection,
) -> None:
    assunto_id = _criar_assunto(conn, [_corpo_longo("ITEM-01"), _corpo_longo("ITEM-02")])
    conn.execute(
        "UPDATE item SET resumo = 'resumo velho', resumo_versao = 'resumo-item-velho', resumo_partes = 1 "
        "WHERE titulo = 'Manchete 1'"
    )
    conn.execute(
        "UPDATE item SET resumo = 'resumo atual ITEM-02', resumo_versao = ?, resumo_partes = 1 "
        "WHERE titulo = 'Manchete 2'",
        (prompt_cartao.VERSAO_RESUMO_ITEM,),
    )
    conn.commit()
    cliente = _Cliente()

    cartoes.gerar_cartao(cliente, conn, assunto_id)

    (prompt_resumo,) = cliente.prompts(prompt_cartao.VERSAO_RESUMO_ITEM)
    assert "Manchete 1" in prompt_resumo
    (prompt_final,) = cliente.prompts(prompt_cartao.VERSAO)
    assert "resumo velho" not in prompt_final
    assert "resumo atual ITEM-02" in prompt_final


def test_falha_no_resumo_de_um_item_nao_grava_cartao_parcial(conn: sqlite3.Connection) -> None:
    assunto_id = _criar_assunto(conn, [_corpo_longo("ITEM-01")])
    cliente = _Cliente()
    cliente.falhar_resumo = True

    assert cartoes.gerar_cartao(cliente, conn, assunto_id) is None

    assert cliente.prompts(prompt_cartao.VERSAO) == []
    assunto = assuntos.obter_por_id(conn, assunto_id)
    assert assunto is not None and assunto.resumo_cartao is None
    assert _resumo_gravado(conn, assunto_id)[0]["resumo"] is None


# --- 6. qualificação recebe os resumos ----------------------------------------------------------------


def _preparar_tema_usuario(conn: sqlite3.Connection) -> None:
    usuario = perfis.upsert_usuario(conn, "Usuário Teste", AGORA)
    assert usuario.id is not None
    tema = queries_temas.obter_ou_criar(conn, "tema-usuario", "descrição", [], AGORA)
    assert tema.id is not None
    queries_temas.gravar_embedding(conn, tema.id, _vetor(1.0), modelo_embedding="bge-m3")
    perfil_tema.vincular(conn, usuario.id, tema.id, 3, "declarada", "dominio", True, AGORA)
    conn.commit()


def test_qualificador_recebe_os_resumos_de_todos_os_itens_e_nao_o_corte(conn: sqlite3.Connection) -> None:
    _preparar_tema_usuario(conn)
    corpos = [("CORPO-QUE-NAO-VAI " * 300) + f"ITEM-{i:02d}" for i in range(1, 8)]
    assunto_id = _criar_assunto(conn, corpos, titulo=None)
    cliente = _Cliente()

    resumo = qualificador.qualificar_pendentes(cliente, conn, 10)

    assert resumo.qualificados == 1
    esperadas = {f"ITEM-{i:02d}" for i in range(1, 8)}
    for tarefa in ("rotular", "qualificar"):
        (prompt,) = [p for t, _, p in cliente.chamadas if t == tarefa]
        assert set(_MARCA.findall(prompt)) == esperadas
        assert "CORPO-QUE-NAO-VAI" not in prompt
        for linha in _resumo_gravado(conn, assunto_id):
            assert cercar_dado_externo(linha["resumo"]) in prompt
    assert len(cliente.prompts(prompt_cartao.VERSAO_RESUMO_ITEM)) == 7


def test_qualificar_com_janela_pequena_consolida_os_resumos_em_vez_de_cortar(
    conn: sqlite3.Connection,
) -> None:
    _preparar_tema_usuario(conn)
    _criar_assunto(conn, [_corpo_longo(f"ITEM-{i:02d}") for i in range(1, 41)], titulo="Já tem título")
    cliente = _Cliente(janelas={"qualificar": 2048, "cartao": 4096}, enchimento=60)

    resumo = qualificador.qualificar_pendentes(cliente, conn, 10)

    assert resumo.qualificados == 1
    assert cliente.prompts(prompt_cartao.VERSAO_CONSOLIDACAO)
    (prompt,) = [p for t, _, p in cliente.chamadas if t == "qualificar"]
    assert set(_MARCA.findall(prompt)) == {f"ITEM-{i:02d}" for i in range(1, 41)}


def test_cartoes_e_qualificador_nao_tem_mais_corte_de_300_nem_teto_de_5() -> None:
    for caminho in ("agente_nw/nucleo/relevancia/cartoes.py", "agente_nw/nucleo/relevancia/qualificador.py"):
        fonte = (RAIZ / caminho).read_text(encoding="utf-8")
        assert "[:300]" not in fonte and "[:5]" not in fonte
        assert "_TRUNCAMENTO_TRECHO" not in fonte and "_MAX_ITENS" not in fonte
