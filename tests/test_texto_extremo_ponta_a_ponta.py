"""Prova com textos extremos (brief 094, item 2.3): cada tarefa de `config/llm_routing.yaml` que recebe
texto de terceiros, com um texto de 34.195 caracteres e outro de 5.000.000, com um marcador único que
termina no **último** caractere. Para cada uma, o marcador chega a pelo menos uma chamada ao modelo (ou ao
embedding), ou a tarefa se recusa em voz alta: linha `"janela": true` no `chamadas_llm.jsonl` e o prompt
**inteiro**, marcador incluído, na `fila_revisao`. Passar em silêncio faz o teste falhar.

O cliente é o `ClienteOllama` de verdade (a conferência de janela é a do produto); só a ida ao servidor é
falsa: `_chamar` guarda o prompt e responde um JSON válido para o esquema, e o `/api/embed` é um
`MockTransport` que guarda cada texto. Sem Ollama e sem rede.

As 15 tarefas são as 14 de geração do perfil e o embedding (`embeddings.modelo`). Nenhuma fica fora:
todas recebem texto de terceiros ou do pedido. Onde a entrada pública exige banco e coleta inteiros, o
caso entra pelo montador do prompt mais `gerar_json`, que é onde o texto vira prompt; os cortes de
seleção que vêm antes (quantos fatos, quantas manchetes, quantos meses) são achados do relatório 094 e
não são provados aqui: dois deles (2.000 caracteres na calibração, P-008, e o sacrifício de blocos da
redação, P-033) são exceções aprovadas no registro."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest
import yaml
from pydantic import BaseModel

from agente_nw.coleta.capturas import extrator as extrator_captura
from agente_nw.coleta.capturas import imagens
from agente_nw.nucleo import llm as llm_mod
from agente_nw.nucleo import pedido as pedido_mod
from agente_nw.nucleo import termos_contato
from agente_nw.nucleo.database import conexao as conexao_mod
from agente_nw.nucleo.database import migracoes
from agente_nw.nucleo.database.queries import fila_extracao
from agente_nw.nucleo.llm import ClienteOllama, JanelaEstourada, embeddar_em_partes
from agente_nw.nucleo.modelos.configuracao import Roteamento
from agente_nw.nucleo.modelos.fila import FilaExtracao
from agente_nw.nucleo.modelos.pedido import PedidoExtraido
from agente_nw.nucleo.prompts import (
    avaliar_relacao_objetivo,
    cruzar_por_que,
    descrever_tema,
    desempatar_perfil,
    prerotular_calibracao,
    qualificar,
    redigir_ganchos,
    rotular,
)
from agente_nw.nucleo.relevancia import cartoes
from agente_nw.perfil import extrator as extrator_perfil

RAIZ = Path(__file__).resolve().parent.parent
MARCADOR = "MARCADOR-UNICO-094-FIM"
TAMANHOS = {"item_34195": 34_195, "sintetico_5M": 5_000_000}

_RESPOSTAS: dict[str, dict[str, Any]] = {
    "RespostaCartao": {"resumo": "resumo da parte"},
    "RespostaCapturaRedeSocial": {"descartar": False, "conteudo": "publicação"},
    "RespostaExtracaoTexto": {},
}


def texto_extremo(tamanho: int) -> str:
    """Texto com palavras e espaços (como uma notícia) e o marcador terminando no último caractere."""
    corpo = ("palavra de um texto de terceiros " * (tamanho // 33 + 1))[: tamanho - len(MARCADOR) - 1]
    texto = f"{corpo} {MARCADOR}"
    assert len(texto) == tamanho and texto.endswith(MARCADOR) and texto.count(MARCADOR) == 1
    return texto


class _Registrador(ClienteOllama):
    """`ClienteOllama` real; só `_chamar` (o servidor) é falso: guarda o prompt e responde o esquema."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.prompts: list[str] = []

    def _chamar(
        self,
        tarefa: Any,
        prompt: str,
        temperature: float,
        imagens: list[str] | None,
        esquema: type[BaseModel],
    ) -> Any:
        self.prompts.append(prompt)
        return llm_mod._RespostaBruta(
            texto=json.dumps(_RESPOSTAS.get(esquema.__name__, {})),
            tokens_prompt=None,
            parada="stop",
            cortada=False,
        )


class _Ambiente:
    def __init__(self, tmp_path: Path) -> None:
        self.conexao: sqlite3.Connection = conexao_mod.abrir(tmp_path / "teste.db")
        migracoes.aplicar(self.conexao)
        self.log = tmp_path / "chamadas_llm.jsonl"
        self.textos_embeddados: list[str] = []
        dados = yaml.safe_load((RAIZ / "config" / "llm_routing.yaml").read_text(encoding="utf-8"))
        http = httpx.Client(transport=httpx.MockTransport(self._embed))
        self.cliente = _Registrador(
            http, self.conexao, Roteamento.model_validate(dados), "http://127.0.0.1:11435", self.log
        )

    def _embed(self, request: httpx.Request) -> httpx.Response:
        corpo = json.loads(request.content)
        self.textos_embeddados.extend(corpo["input"])
        return httpx.Response(
            200, json={"embeddings": [[0.5] * 1024 for _ in corpo["input"]], "prompt_eval_count": 10}
        )

    def marcador_chegou(self) -> bool:
        return any(MARCADOR in texto for texto in [*self.cliente.prompts, *self.textos_embeddados])

    def recusou_em_voz_alta(self) -> bool:
        """Linha de janela no log e o prompt inteiro, com o marcador, guardado na `fila_revisao`."""
        linhas = self.log.read_text(encoding="utf-8").splitlines() if self.log.exists() else []
        janela = any(json.loads(linha).get("janela") is True for linha in linhas)
        guardado = any(
            MARCADOR in entrada for (entrada,) in self.conexao.execute("SELECT entrada FROM fila_revisao")
        )
        return janela and guardado


@pytest.fixture(autouse=True)
def _sem_porteiro(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(llm_mod, "_consultar_porteiro", lambda _modelo, _porta: {"codigo_de_saida": 0})
    monkeypatch.setattr("agente_nw.nucleo.llm.time.sleep", lambda _segundos: None)


def _gerar(amb: _Ambiente, tarefa: str, prompt: str, esquema: type[BaseModel]) -> None:
    try:
        amb.cliente.gerar_json(tarefa, prompt, esquema)
    except JanelaEstourada:
        pass  # a recusa é conferida pelo log e pela fila_revisao


def _pedido(**extra: Any) -> PedidoExtraido:
    base: dict[str, Any] = {
        "pessoa_nome": "Ana",
        "objetivo": "reaproximar",
        "objetivo_texto": "retomar contato",
        "assunto_principal": "notícia",
        "termos_busca": ["notícia"],
        "confianca": 0.9,
    }
    return PedidoExtraido.model_validate({**base, **extra})


# --- as 15 tarefas -------------------------------------------------------------------------------------


def _qualificar(amb: _Ambiente, texto: str) -> None:
    prompt = qualificar.construir_prompt("Título", [("Título", "exemplo.com", texto)], ["urbanismo"])
    _gerar(amb, "qualificar", prompt, qualificar.ESQUEMA)


def _rotular(amb: _Ambiente, texto: str) -> None:
    _gerar(amb, "rotular", rotular.construir_prompt([("Título", "exemplo.com", texto)]), rotular.ESQUEMA)


def _cartao(amb: _Ambiente, texto: str) -> None:
    """Entrada pública: o resumo do item lê o corpo inteiro, em partes se não couber (brief 090)."""
    cartoes.resumir_item(amb.cliente, "Título", "exemplo.com", texto, amb.conexao)


def _cruzar_por_que(amb: _Ambiente, texto: str) -> None:
    prompt = cruzar_por_que.construir_prompt(
        "Ana", ["vela"], [("corrida", "interesse")], [(texto, "conector", None)]
    )
    _gerar(amb, "cruzar_por_que", prompt, cruzar_por_que.ESQUEMA)


def _avaliar_relacao_objetivo(amb: _Ambiente, texto: str) -> None:
    prompt = avaliar_relacao_objetivo.construir_prompt(
        "reaproximar", texto, "cargo: advogada", [("Título", None)]
    )
    _gerar(amb, "avaliar_relacao_objetivo", prompt, avaliar_relacao_objetivo.ESQUEMA)


def _extrair_de_texto(amb: _Ambiente, texto: str) -> None:
    """Entrada pública: um item da `fila_extracao`, lido inteiro ou em partes (brief 088)."""
    amb.conexao.execute(
        "INSERT INTO perfil (id, tipo, nome, criado_em, atualizado_em) VALUES (1, 'contato', 'Ana', 'x', 'x')"
    )
    agora = "2026-11-16T00:00:00+00:00"
    item_id = fila_extracao.inserir(amb.conexao, 1, texto, "colado", agora)
    item = FilaExtracao(id=item_id, perfil_id=1, texto=texto, origem="colado", criado_em=agora)
    extrator_perfil.processar_item(amb.cliente, amb.conexao, item, extrator_perfil.ResumoProcessamento())


def _extrair_captura_rede_social(amb: _Ambiente, texto: str) -> None:
    """Entrada pública: um bloco capturado, lido inteiro ou em partes (brief 088)."""
    extrator_captura.extrair(amb.cliente, texto, "instagram", amb.conexao)


def _extrair_pedido(amb: _Ambiente, texto: str) -> None:
    """Entrada pública: a frase do usuário vai inteira ao prompt."""
    try:
        pedido_mod.extrair(amb.cliente, amb.conexao, texto)
    except JanelaEstourada:
        pass


def _desempatar_perfil(amb: _Ambiente, texto: str) -> None:
    prompt = desempatar_perfil.construir_prompt("Ana", {"profissao": "advogada"}, ["Ana — advogada", texto])
    _gerar(amb, "desempatar_perfil", prompt, desempatar_perfil.ESQUEMA)


def _redigir_ganchos(amb: _Ambiente, texto: str) -> None:
    """A frase do pedido (texto do usuário, protegida no corte por tamanho) e um fato, inteiros."""
    entrada = redigir_ganchos.EntradaRedacao(
        usuario_nome="Eu",
        usuario_temas=[],
        contato_nome="Ana",
        contato_ficha=[],
        vinculo=None,
        tempo_sem_contato=None,
        fatos=[],
        cabecalho_rede=None,
        pedido=_pedido(),
        frase=texto,
        historico=[],
        assuntos=[],
    )
    _gerar(amb, "redigir_ganchos", redigir_ganchos.construir_prompt(entrada), redigir_ganchos.ESQUEMA)


def _extrair_termos_contato(amb: _Ambiente, texto: str) -> None:
    _gerar(
        amb, "extrair_termos_contato", termos_contato.construir_prompt([texto]), termos_contato.RespostaTermos
    )


def _descrever_tema(amb: _Ambiente, texto: str) -> None:
    _gerar(amb, "descrever_tema", descrever_tema.construir_prompt(texto), descrever_tema.ESQUEMA)


def _descrever_imagem(amb: _Ambiente, texto: str) -> None:
    """Entrada pública: o `alt` da imagem publicada vai inteiro (a falha vira `None`, já registrada)."""
    imagem = imagens.ImagemCapturada(src="s", alt=texto, link="", mime="image/jpeg", dados_base64="AAAA")
    imagens.descrever(amb.cliente, imagem, "instagram")


def _prerotular_calibracao(amb: _Ambiente, texto: str) -> None:
    prompt = prerotular_calibracao.construir_prompt("Título A", texto, "Título B", "outro texto")
    _gerar(amb, "prerotular_calibracao", prompt, prerotular_calibracao.ESQUEMA)


def _embeddings(amb: _Ambiente, texto: str) -> None:
    """Entrada pública de todo vetor de texto de terceiros (item, fatos, tema): em partes (brief 089)."""
    embeddar_em_partes(amb.cliente, texto)


TAREFAS: dict[str, Callable[[_Ambiente, str], None]] = {
    "qualificar": _qualificar,
    "rotular": _rotular,
    "cartao": _cartao,
    "cruzar_por_que": _cruzar_por_que,
    "avaliar_relacao_objetivo": _avaliar_relacao_objetivo,
    "extrair_de_texto": _extrair_de_texto,
    "extrair_captura_rede_social": _extrair_captura_rede_social,
    "extrair_pedido": _extrair_pedido,
    "desempatar_perfil": _desempatar_perfil,
    "redigir_ganchos": _redigir_ganchos,
    "extrair_termos_contato": _extrair_termos_contato,
    "descrever_tema": _descrever_tema,
    "descrever_imagem": _descrever_imagem,
    "prerotular_calibracao": _prerotular_calibracao,
    "embeddings": _embeddings,
}

_DIVIDEM_EM_PARTES = {"cartao", "extrair_de_texto", "extrair_captura_rede_social", "embeddings"}


def test_as_15_tarefas_sao_as_do_roteamento() -> None:
    dados = yaml.safe_load((RAIZ / "config" / "llm_routing.yaml").read_text(encoding="utf-8"))
    for perfil in dados["perfis"].values():
        assert set(perfil["tarefas"]) | {"embeddings"} == set(TAREFAS)
    assert len(TAREFAS) == 15


@pytest.mark.parametrize("tamanho", TAMANHOS.values(), ids=list(TAMANHOS))
@pytest.mark.parametrize("tarefa", list(TAREFAS))
def test_marcador_chega_ou_a_tarefa_recusa_em_voz_alta(tmp_path: Path, tarefa: str, tamanho: int) -> None:
    amb = _Ambiente(tmp_path)

    TAREFAS[tarefa](amb, texto_extremo(tamanho))

    chegou, recusou = amb.marcador_chegou(), amb.recusou_em_voz_alta()
    assert chegou or recusou, f"{tarefa}: o marcador não chegou a nenhuma chamada e nada foi registrado"
    if tarefa in _DIVIDEM_EM_PARTES:
        assert chegou, f"{tarefa} lê em partes: o último caractere precisa chegar a uma chamada"
