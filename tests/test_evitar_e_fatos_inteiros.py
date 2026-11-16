"""Brief 091: o que o usuário pede para evitar é procurado em todos os itens do assunto, e os fatos do
contato entram inteiros na redação e nos termos de busca."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pytest

from agente_nw.nucleo import termos_contato
from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import assuntos, fatos, fontes, itens
from agente_nw.nucleo.modelos.assunto import Assunto
from agente_nw.nucleo.modelos.fato import Fato
from agente_nw.nucleo.modelos.item import Item
from agente_nw.nucleo.modelos.pedido import PedidoExtraido
from agente_nw.nucleo.prompts import redigir_ganchos as prompt_mod
from agente_nw.nucleo.prompts.redigir_ganchos import EntradaRedacao
from agente_nw.nucleo.relevancia.candidatos import termo_evitado

AGORA = "2026-10-13T10:00:00"


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(aberta)
    return aberta


def _pedido() -> PedidoExtraido:
    return PedidoExtraido.model_validate(
        {
            "pessoa_nome": "Vera",
            "pessoa_pistas": {},
            "objetivo": "agradecer",
            "objetivo_texto": "agradecer a indicação",
            "meio": "whatsapp",
            "registro": "proximo",
            "assunto_principal": "aviação regional",
            "interessa": [],
            "evitar": [],
            "termos_busca": ["aviação regional"],
            "confianca": 0.9,
        }
    )


def _entrada(fatos_: list[str]) -> EntradaRedacao:
    return EntradaRedacao(
        usuario_nome="Davi",
        usuario_temas=[],
        contato_nome="Vera",
        contato_ficha=[],
        vinculo=None,
        tempo_sem_contato=None,
        fatos=fatos_,
        cabecalho_rede=None,
        pedido=_pedido(),
        frase="Agradecer a Vera",
        historico=[],
        assuntos=[],
    )


def _fato_datado(dia: int, corpo: str) -> str:
    return f"2026-09-{dia:02d} (instagram): {corpo}"


# 1. Fato longo chega inteiro ao prompt.
def test_fato_de_3000_caracteres_chega_inteiro_ao_prompt() -> None:
    corpo = "início " + "x" * 3000 + " fim-do-fato"
    prompt = prompt_mod.construir_prompt(_entrada([_fato_datado(20, corpo)]))

    assert corpo in prompt


# 2. Excesso de fatos: os 4 mais recentes entram, os demais são listados como não incluídos.
def test_excesso_de_fatos_mantem_os_4_mais_recentes_e_lista_o_resto() -> None:
    lista = [_fato_datado(30 - i, "texto " * 400 + f"marca-{i}") for i in range(10)]
    entrada = _entrada(lista)

    cortada = prompt_mod.cortar_por_tamanho(entrada, limite_tokens=1500)
    nao_incluidos = prompt_mod.fatos_nao_incluidos(entrada, limite_tokens=1500)

    assert cortada.fatos == lista[:4]
    assert nao_incluidos == lista[4:]
    prompt = prompt_mod.construir_prompt(entrada, limite_tokens=1500)
    assert "marca-3" in prompt and "marca-4" not in prompt


def test_fatos_mantidos_saem_em_ordem_de_data_da_mais_nova_para_a_mais_antiga() -> None:
    desordenados = [_fato_datado(d, "texto " * 400 + f"d{d}") for d in (5, 25, 15, 20, 10, 1, 2, 3)]

    cortada = prompt_mod.cortar_por_tamanho(_entrada(desordenados), limite_tokens=1500)

    assert [f[:10] for f in cortada.fatos] == ["2026-09-25", "2026-09-20", "2026-09-15", "2026-09-10"]


# 3. Termo evitado que só aparece na manchete do 9º item é encontrado.
def _assunto_com_itens(
    conn: sqlite3.Connection, titulos: list[str], resumos: dict[int, str] | None = None
) -> Assunto:
    fonte = fontes.obter_ou_criar(conn, "g1.globo.com", "https://g1.globo.com/rss", "g1.globo.com", "rss", 5)
    assert fonte.id is not None
    assunto_id = assuntos.inserir(
        conn,
        Assunto(
            titulo_gerado="Setor aéreo",
            resumo_cartao="O setor segue em movimento.",
            primeiro_visto=AGORA,
            ultimo_visto=AGORA,
            n_itens=len(titulos),
            status="novo",
        ),
    )
    for indice, titulo in enumerate(titulos, start=1):
        item_id = itens.inserir(
            conn,
            Item(
                fonte_id=fonte.id,
                url_canonica=f"https://exemplo.com/{assunto_id}/{indice}",
                titulo=titulo,
                texto="corpo",
                coletado_em=AGORA,
                hash_titulo=f"hash-{assunto_id}-{indice}",
                assunto_id=assunto_id,
            ),
        )
        if resumos and indice in resumos:
            itens.gravar_resumo(conn, item_id, resumos[indice], "v-teste", 0, None)
    conn.commit()
    atual = assuntos.obter_por_id(conn, assunto_id)
    assert atual is not None
    return atual


def test_termo_so_na_manchete_do_nono_item_e_encontrado(conn: sqlite3.Connection) -> None:
    titulos = [f"Manchete comum {i}" for i in range(1, 9)] + ["Greve de pilotos paralisa o aeroporto"]
    assunto = _assunto_com_itens(conn, titulos)

    assert termo_evitado(assunto, ["greve"], conn) is True
    assert termo_evitado(assunto, ["futebol"], conn) is False


def test_termo_so_no_resumo_de_um_item_e_encontrado(conn: sqlite3.Connection) -> None:
    assunto = _assunto_com_itens(conn, ["a", "b", "c"], resumos={3: "A empresa anunciou demissões em massa."})

    assert termo_evitado(assunto, ["Demissões"], conn) is True


def test_sem_conexao_a_regra_antiga_continua(conn: sqlite3.Connection) -> None:
    assunto = _assunto_com_itens(conn, ["Greve de pilotos"])

    assert termo_evitado(assunto, ["greve"]) is False
    assert termo_evitado(assunto, ["movimento"]) is True


# 4. termos_do_contato de 1.000 caracteres devolve os termos do texto inteiro.
class _Cliente:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def gerar_json(self, tarefa: str, prompt: str, esquema: Any) -> Any:
        self.prompts.append(prompt)
        return esquema(termos=["cerâmica artesanal"])


def _perfil(conn: sqlite3.Connection) -> int:
    cursor = conn.execute(
        "INSERT INTO perfil (tipo, nome, linguas, ativo, criado_em, atualizado_em) "
        "VALUES ('contato', 'Ana', '[]', 0, ?, ?)",
        (AGORA, AGORA),
    )
    assert cursor.lastrowid is not None
    return cursor.lastrowid


def test_fato_de_1000_caracteres_vai_inteiro_aos_termos_do_contato(conn: sqlite3.Connection) -> None:
    perfil_id = _perfil(conn)
    texto = "abertura " + "palavra " * 130 + "cerâmica-no-fim"
    assert len(texto) > 1000
    fatos.inserir(conn, Fato(perfil_id=perfil_id, tipo="post", conteudo=texto, registrado_em=AGORA))
    cliente = _Cliente()

    termos = termos_contato.termos_do_contato(cliente, conn, perfil_id)

    assert termos == ["cerâmica artesanal"]
    assert texto in cliente.prompts[0]


# 5. Entrada curta: o prompt é o de antes.
def test_entrada_curta_nao_muda_o_prompt() -> None:
    entrada = _entrada([_fato_datado(20, "curto"), _fato_datado(19, "outro")])

    assert prompt_mod.cortar_por_tamanho(entrada) is entrada
    assert prompt_mod.fatos_nao_incluidos(entrada) == []
    assert _fato_datado(20, "curto") in prompt_mod.construir_prompt(entrada)
