"""Janela do modelo (brief 082): prompt que não cabe no `num_ctx`, texto de embedding acima do limite do
`bge-m3` e resposta cortada por `num_predict` nunca viram resultado bom. O projeto registra uma linha
`"janela": true` em `chamadas_llm.jsonl`, não usa a resposta e levanta um erro de janela que é
subclasse do erro que os chamadores já tratam (`FalhaJsonInvalido`), com o item na `fila_revisao`.

Sem Ollama e sem rede: `MockTransport` em tudo."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
import yaml
from pydantic import BaseModel

from agente_nw.nucleo import estimativa_tokens
from agente_nw.nucleo import llm as llm_mod
from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import fila_extracao, fila_revisao
from agente_nw.nucleo.llm import (
    ClienteAnthropic,
    ClienteGemini,
    ClienteOllama,
    ClienteOpenAI,
    FalhaJanela,
    FalhaJanelaEmbedding,
    FalhaJsonInvalido,
    JanelaEstourada,
)
from agente_nw.nucleo.modelos.configuracao import Roteamento
from agente_nw.nucleo.prompts import redigir_ganchos

RAIZ = Path(__file__).resolve().parent.parent
CHAVE = "chave-de-teste-nao-serve-para-nada"


class _EsquemaTeste(BaseModel):
    ok: bool


class _EsquemaLista(BaseModel):
    itens: list[str]


def _roteamento() -> Roteamento:
    dados = yaml.safe_load((RAIZ / "config" / "llm_routing.yaml").read_text(encoding="utf-8"))
    return Roteamento.model_validate(dados)


def _num_ctx(tarefa: str) -> int:
    roteamento = _roteamento()
    return roteamento.perfis[roteamento.perfil_ativo].tarefas[tarefa].num_ctx


def _ler_log(caminho: Path) -> list[dict[str, Any]]:
    if not caminho.exists():
        return []
    return [json.loads(linha) for linha in caminho.read_text(encoding="utf-8").splitlines()]


def _linhas_janela(caminho: Path) -> list[dict[str, Any]]:
    return [linha for linha in _ler_log(caminho) if linha.get("janela") is True]


@pytest.fixture(autouse=True)
def _sem_sono(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(llm_mod.time, "sleep", lambda _segundos: None)


@pytest.fixture(autouse=True)
def _sem_porteiro(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(llm_mod, "_consultar_porteiro", lambda _modelo, _porta: {"codigo_de_saida": 0})


class _Contador:
    def __init__(self, resposta: Any) -> None:
        self.chamadas = 0
        self._resposta = resposta

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.chamadas += 1
        corpo = self._resposta(request) if callable(self._resposta) else self._resposta
        return httpx.Response(200, json=corpo)


def _ollama(tmp_path: Path, handler: Any) -> tuple[ClienteOllama, Any, Path]:
    conexao_bd = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_bd)
    caminho_log = tmp_path / "chamadas_llm.jsonl"
    http = httpx.Client(transport=httpx.MockTransport(handler))
    cliente = ClienteOllama(http, conexao_bd, _roteamento(), "http://127.0.0.1:11435", caminho_log)
    return cliente, conexao_bd, caminho_log


# --- 1 e 2: a medida devolvida pelo Ollama -----------------------------------------------------------


def test_prompt_eval_count_igual_ao_num_ctx_e_erro_de_janela_com_log_e_sem_resultado(tmp_path: Path) -> None:
    num_ctx = _num_ctx("qualificar")
    servidor = _Contador(
        {"response": json.dumps({"ok": True}), "done_reason": "stop", "prompt_eval_count": num_ctx}
    )
    cliente, conexao_bd, caminho_log = _ollama(tmp_path, servidor)

    with pytest.raises(FalhaJanela) as erro:
        cliente.gerar_json("qualificar", "prompt curto", _EsquemaTeste)

    assert isinstance(erro.value, FalhaJsonInvalido)
    assert isinstance(erro.value, JanelaEstourada)
    assert erro.value.motivo == "prompt_cortado"
    assert erro.value.tokens_medidos == num_ctx
    assert servidor.chamadas == 1, "estouro de janela não ganha nova tentativa: o mesmo prompt corta de novo"
    [linha] = _linhas_janela(caminho_log)
    assert linha["tarefa"] == "qualificar"
    assert linha["modelo"] == "qwen3:4b"
    assert linha["tokens_medidos"] == num_ctx
    assert linha["num_ctx"] == num_ctx
    assert linha["motivo"] == "prompt_cortado"
    assert fila_revisao.obter(conexao_bd, erro.value.fila_revisao_id) is not None


def test_prompt_eval_count_menor_que_num_ctx_devolve_resultado_e_nao_registra_janela(tmp_path: Path) -> None:
    num_ctx = _num_ctx("qualificar")
    servidor = _Contador(
        {"response": json.dumps({"ok": True}), "done_reason": "stop", "prompt_eval_count": num_ctx - 1}
    )
    cliente, conexao_bd, caminho_log = _ollama(tmp_path, servidor)

    resultado = cliente.gerar_json("qualificar", "prompt curto", _EsquemaTeste)

    assert resultado.ok is True
    assert _linhas_janela(caminho_log) == []
    assert fila_revisao.listar(conexao_bd) == []


def test_resposta_sem_campos_de_medida_segue_como_antes(tmp_path: Path) -> None:
    """Resposta antiga do Ollama (ou falsa dos outros testes), sem `prompt_eval_count` nem `done_reason`."""
    cliente, _conexao, caminho_log = _ollama(tmp_path, _Contador({"response": json.dumps({"ok": True})}))

    assert cliente.gerar_json("qualificar", "prompt curto", _EsquemaTeste).ok is True
    assert _linhas_janela(caminho_log) == []


# --- 3: a estimativa antes da chamada ----------------------------------------------------------------


def test_prompt_estimado_acima_do_num_ctx_e_recusado_antes_de_chamar_o_servidor(tmp_path: Path) -> None:
    num_ctx = _num_ctx("qualificar")
    prompt = " ".join(["palavra"] * num_ctx)  # 8 caracteres por palavra: caracteres ÷ 3 ≈ 2,7 × num_ctx
    servidor = _Contador({"response": json.dumps({"ok": True})})
    cliente, conexao_bd, caminho_log = _ollama(tmp_path, servidor)

    with pytest.raises(FalhaJanela) as erro:
        cliente.gerar_json("qualificar", prompt, _EsquemaTeste)

    assert servidor.chamadas == 0
    assert erro.value.motivo == "prompt_estimado_acima_da_janela"
    assert erro.value.tokens_estimados == estimativa_tokens.estimar_tokens_conservador(prompt)
    [linha] = _linhas_janela(caminho_log)
    assert linha["tokens_medidos"] is None
    assert linha["tokens_estimados"] > num_ctx
    assert fila_revisao.obter(conexao_bd, erro.value.fila_revisao_id) is not None


def test_prompt_que_so_passa_do_num_ctx_com_2_0_e_recusado_em_voz_alta(tmp_path: Path) -> None:
    """Brief 098: 0,6 × num_ctx palavras curtas passava com 1,4 (0,84 × num_ctx) e agora, com 2,0
    tokens por palavra, estoura: o cliente recusa antes de chamar o servidor, em vez de o modelo cortar."""
    num_ctx = _num_ctx("qualificar")
    palavras = int(num_ctx * 0.6)
    prompt = " ".join(["a"] * palavras)
    assert palavras * 1.4 < num_ctx < palavras * 2.0
    servidor = _Contador({"response": json.dumps({"ok": True})})
    cliente, _conexao, caminho_log = _ollama(tmp_path, servidor)

    with pytest.raises(FalhaJanela) as erro:
        cliente.gerar_json("qualificar", prompt, _EsquemaTeste)

    assert servidor.chamadas == 0
    assert erro.value.motivo == "prompt_estimado_acima_da_janela"
    assert erro.value.tokens_estimados == palavras * 2
    assert len(_linhas_janela(caminho_log)) == 1


def test_estimativa_igual_ao_num_ctx_nao_bloqueia(tmp_path: Path) -> None:
    """Só bloqueia quando passa do `num_ctx` (2.2); a decisão final é a medida do servidor."""
    num_ctx = _num_ctx("qualificar")
    prompt = "a" * (num_ctx * 3)
    assert estimativa_tokens.estimar_tokens_conservador(prompt) == num_ctx
    servidor = _Contador({"response": json.dumps({"ok": True}), "prompt_eval_count": num_ctx - 10})
    cliente, _conexao, _log = _ollama(tmp_path, servidor)

    assert cliente.gerar_json("qualificar", prompt, _EsquemaTeste).ok is True
    assert servidor.chamadas == 1


def test_estimativa_e_o_maior_entre_palavras_e_caracteres() -> None:
    assert estimativa_tokens.estimar_tokens(" ".join(["a"] * 100)) == 200
    assert estimativa_tokens.estimar_tokens_conservador(" ".join(["a"] * 100)) == 200
    assert (
        estimativa_tokens.estimar_tokens_conservador("paralelepípedo " * 10)
        == len("paralelepípedo " * 10) // 3
    )


# --- 4 e 5: resposta cortada por tamanho, nos quatro clientes -----------------------------------------


def test_done_reason_length_com_json_valido_e_falha_e_nao_resultado(tmp_path: Path) -> None:
    servidor = _Contador(
        {"response": json.dumps({"itens": ["um", "dois"]}), "done_reason": "length", "prompt_eval_count": 50}
    )
    cliente, conexao_bd, caminho_log = _ollama(tmp_path, servidor)

    with pytest.raises(FalhaJanela) as erro:
        cliente.gerar_json("cartao", "prompt curto", _EsquemaLista)

    assert erro.value.motivo == "resposta_cortada"
    [linha] = _linhas_janela(caminho_log)
    assert linha["motivo"] == "resposta_cortada"
    assert linha["parada"] == "length"
    assert linha["num_predict"] == 1024
    assert fila_revisao.obter(conexao_bd, erro.value.fila_revisao_id) is not None


def _api(tmp_path: Path, classe: Any, handler: Any) -> tuple[Any, Path]:
    conexao_bd = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_bd)
    caminho_log = tmp_path / "chamadas_llm.jsonl"
    http = httpx.Client(transport=httpx.MockTransport(handler))
    embeddings = ClienteOllama(http, conexao_bd, _roteamento(), "http://127.0.0.1:11435", caminho_log)
    cliente = classe(http, conexao_bd, _roteamento(), CHAVE, "modelo-de-teste", caminho_log, embeddings)
    return cliente, caminho_log


def _anthropic(parada: str) -> dict[str, Any]:
    return {
        "content": [{"type": "tool_use", "name": "responder", "input": {"itens": ["um"]}}],
        "stop_reason": parada,
    }


def _gemini(parada: str) -> dict[str, Any]:
    return {
        "candidates": [
            {"content": {"parts": [{"text": json.dumps({"itens": ["um"]})}]}, "finishReason": parada}
        ]
    }


def _openai(parada: str) -> dict[str, Any]:
    return {"choices": [{"message": {"content": json.dumps({"itens": ["um"]})}, "finish_reason": parada}]}


CASOS_API = [
    (ClienteAnthropic, _anthropic, "max_tokens", "tool_use"),
    (ClienteGemini, _gemini, "MAX_TOKENS", "STOP"),
    (ClienteOpenAI, _openai, "length", "stop"),
]


@pytest.mark.parametrize(("classe", "corpo", "cortada", "normal"), CASOS_API)
def test_api_com_resposta_cortada_por_tamanho_e_falha(
    tmp_path: Path, classe: Any, corpo: Any, cortada: str, normal: str
) -> None:
    servidor = _Contador(corpo(cortada))
    cliente, caminho_log = _api(tmp_path, classe, servidor)

    with pytest.raises(FalhaJanela) as erro:
        cliente.gerar_json("cartao", "prompt curto", _EsquemaLista)

    assert erro.value.motivo == "resposta_cortada"
    assert servidor.chamadas == 1
    [linha] = _linhas_janela(caminho_log)
    assert linha["parada"] == cortada
    assert linha["modelo"] == "modelo-de-teste"


@pytest.mark.parametrize(("classe", "corpo", "cortada", "normal"), CASOS_API)
def test_api_com_parada_normal_devolve_resultado(
    tmp_path: Path, classe: Any, corpo: Any, cortada: str, normal: str
) -> None:
    cliente, caminho_log = _api(tmp_path, classe, _Contador(corpo(normal)))

    assert cliente.gerar_json("cartao", "prompt curto", _EsquemaLista).itens == ["um"]
    assert _linhas_janela(caminho_log) == []


def test_anthropic_janela_do_proprio_modelo_excedida_tambem_e_resposta_cortada(tmp_path: Path) -> None:
    cliente, _log = _api(tmp_path, ClienteAnthropic, _Contador(_anthropic("model_context_window_exceeded")))

    with pytest.raises(FalhaJanela):
        cliente.gerar_json("cartao", "prompt curto", _EsquemaLista)


@pytest.mark.parametrize(("classe", "corpo", "cortada", "normal"), CASOS_API)
def test_api_nao_bloqueia_pelo_num_ctx_do_ollama(
    tmp_path: Path, classe: Any, corpo: Any, cortada: str, normal: str
) -> None:
    """O `num_ctx` é a janela do modelo local; o provedor de API não corta o prompt em silêncio
    (recusa com erro HTTP), então a estimativa antes da chamada só vale para o Ollama."""
    prompt = " ".join(["palavra"] * _num_ctx("cartao"))
    servidor = _Contador(corpo(normal))
    cliente, _log = _api(tmp_path, classe, servidor)

    assert cliente.gerar_json("cartao", prompt, _EsquemaLista).itens == ["um"]
    assert servidor.chamadas == 1


# --- 6: embeddings ------------------------------------------------------------------------------------


def _vetores(request: httpx.Request) -> dict[str, Any]:
    textos = json.loads(request.content)["input"]
    return {"embeddings": [[0.5] * 1024 for _ in textos]}


def test_embedding_acima_do_limite_e_erro_de_janela_com_registro_sem_chamar(tmp_path: Path) -> None:
    servidor = _Contador(_vetores)
    cliente, _conexao, caminho_log = _ollama(tmp_path, servidor)
    longo = "a" * (3 * llm_mod.LIMITE_TOKENS_EMBEDDING + 3)

    with pytest.raises(FalhaJanelaEmbedding) as erro:
        cliente.embeddar(["curto", longo])

    assert isinstance(erro.value, JanelaEstourada)
    assert isinstance(erro.value, ValueError), "o mesmo tipo que `embeddar` já levantava para vetor inválido"
    assert servidor.chamadas == 0
    [linha] = _linhas_janela(caminho_log)
    assert linha["tarefa"] == "embeddings"
    assert linha["modelo"] == "bge-m3"
    assert linha["motivo"] == "embedding_acima_do_limite"
    assert linha["num_ctx"] == llm_mod.LIMITE_TOKENS_EMBEDDING


def test_embedding_abaixo_do_limite_devolve_vetor(tmp_path: Path) -> None:
    cliente, _conexao, caminho_log = _ollama(tmp_path, _Contador(_vetores))

    vetores = cliente.embeddar(["curto", "a" * (3 * llm_mod.LIMITE_TOKENS_EMBEDDING)])

    assert len(vetores) == 2 and len(vetores[0]) == 1024
    assert _linhas_janela(caminho_log) == []


def test_embedding_com_contagem_do_servidor_no_limite_e_erro_de_janela(tmp_path: Path) -> None:
    def resposta(request: httpx.Request) -> dict[str, Any]:
        return {**_vetores(request), "prompt_eval_count": llm_mod.LIMITE_TOKENS_EMBEDDING}

    cliente, _conexao, caminho_log = _ollama(tmp_path, _Contador(resposta))

    with pytest.raises(FalhaJanelaEmbedding) as erro:
        cliente.embeddar(["texto que o servidor contou no limite"])

    assert erro.value.tokens_medidos == llm_mod.LIMITE_TOKENS_EMBEDDING
    [linha] = _linhas_janela(caminho_log)
    assert linha["tokens_medidos"] == llm_mod.LIMITE_TOKENS_EMBEDDING


def test_embedding_de_varios_textos_nao_confunde_a_soma_com_um_texto_cortado(tmp_path: Path) -> None:
    """O `prompt_eval_count` do `/api/embed` soma todos os textos: com mais de um, só a estimativa decide."""

    def resposta(request: httpx.Request) -> dict[str, Any]:
        return {**_vetores(request), "prompt_eval_count": llm_mod.LIMITE_TOKENS_EMBEDDING * 2}

    cliente, _conexao, _log = _ollama(tmp_path, _Contador(resposta))

    assert len(cliente.embeddar(["um texto", "outro texto"])) == 2


def test_cliente_de_api_repassa_o_erro_de_janela_do_embedding(tmp_path: Path) -> None:
    cliente, _log = _api(tmp_path, ClienteAnthropic, _Contador(_vetores))

    with pytest.raises(FalhaJanelaEmbedding):
        cliente.embeddar(["a" * (3 * llm_mod.LIMITE_TOKENS_EMBEDDING + 3)])


# --- 7: tarefa com fila de revisão --------------------------------------------------------------------


def test_extrair_de_texto_com_janela_estourada_vai_para_a_fila_de_revisao(tmp_path: Path) -> None:
    from agente_nw.nucleo.database.queries import perfis
    from agente_nw.perfil import extrator

    num_ctx = _num_ctx("extrair_de_texto")
    servidor = _Contador({"response": "{}", "done_reason": "stop", "prompt_eval_count": num_ctx})
    cliente, conexao_bd, caminho_log = _ollama(tmp_path, servidor)
    contato = perfis.inserir_novo_contato(
        conexao_bd, "Pessoa de Teste", None, None, "2026-11-16T00:00:00+00:00"
    )
    assert contato.id is not None
    item_id = fila_extracao.inserir(conexao_bd, contato.id, "texto longo da conversa", "manual", "2026-11-16")
    conexao_bd.commit()
    item = fila_extracao.obter(conexao_bd, item_id)
    assert item is not None

    resumo = extrator.ResumoProcessamento()
    erro = extrator.processar_item(cliente, conexao_bd, item, resumo)

    assert isinstance(erro, FalhaJanela)
    assert resumo.erros == 1
    [na_fila] = fila_revisao.listar(conexao_bd)
    assert na_fila.tarefa == "extrair_de_texto"
    assert "janela" in na_fila.erro
    marcado = fila_extracao.obter(conexao_bd, item_id)
    assert marcado is not None and f"(fila_revisao id={na_fila.id})" in (marcado.erro or "")
    assert len(_linhas_janela(caminho_log)) == 1


# --- 8: o estimador compartilhado ---------------------------------------------------------------------


def test_redigir_ganchos_usa_o_estimador_compartilhado() -> None:
    assert redigir_ganchos.estimar_tokens is estimativa_tokens.estimar_tokens
