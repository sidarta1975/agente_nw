"""Consulta ao `porteiro` (admin do Ollama compartilhado da máquina) antes de carregar um modelo
no Ollama local (brief 077). Uma consulta por modelo, por cliente; no modo `lote`, espera até 15 min
quando o código é `1`; no modo `interativo`, nunca espera. Falha ou ausência do `porteiro` degrada
para o comportamento de antes deste brief. Nenhum teste chama o `porteiro` real nem a rede."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import httpx
import pytest
import yaml
from pydantic import BaseModel

from agente_nw.nucleo import llm as llm_mod
from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.llm import ClienteAnthropic, ClienteOllama, _consultar_porteiro
from agente_nw.nucleo.modelos.configuracao import Roteamento
from config.container import selecionar_cliente_llm

RAIZ = Path(__file__).resolve().parent.parent

OLLAMA_URL = "http://127.0.0.1:11435"
PORTA = 11435


class _EsquemaTeste(BaseModel):
    ok: bool


class _ProcessoFake:
    """O que `_consultar_porteiro` lê de `subprocess.run`: só o `stdout`."""

    def __init__(self, stdout: str) -> None:
        self.stdout = stdout
        self.returncode = 0


def _roteamento() -> Roteamento:
    dados = yaml.safe_load((RAIZ / "config" / "llm_routing.yaml").read_text(encoding="utf-8"))
    return Roteamento.model_validate(dados)


def _resposta_json(**campos: object) -> httpx.Response:
    return httpx.Response(200, json={"response": json.dumps({"ok": True}), **campos})


def _handler_ok(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/api/embed":
        return httpx.Response(200, json={"embeddings": [[0.0] * 1024]})
    return _resposta_json()


def _cliente(
    tmp_path: Path,
    caminho_log: Path,
    modo_porteiro: Any = "lote",
    handler: Any = _handler_ok,
    ollama_url: str = OLLAMA_URL,
) -> ClienteOllama:
    conexao_bd = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_bd)
    cliente_http = httpx.Client(transport=httpx.MockTransport(handler))
    return ClienteOllama(
        cliente_http,
        conexao_bd,
        _roteamento(),
        ollama_url,
        caminho_log,
        modo_porteiro=modo_porteiro,
    )


def _avisos(caminho: Path) -> list[dict[str, object]]:
    """Só as linhas do `porteiro` no `chamadas_llm.jsonl` — as de `_registrar_log_chamada`
    continuam lá, uma por chamada, e não são aviso nenhum."""
    if not caminho.exists():
        return []
    linhas = [json.loads(linha) for linha in caminho.read_text(encoding="utf-8").splitlines()]
    return [linha for linha in linhas if linha.get("porteiro")]


def _linhas_de_chamada(caminho: Path) -> list[dict[str, object]]:
    if not caminho.exists():
        return []
    linhas = [json.loads(linha) for linha in caminho.read_text(encoding="utf-8").splitlines()]
    return [linha for linha in linhas if not linha.get("porteiro")]


@pytest.fixture(autouse=True)
def _sem_sono(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """A espera de 60 s é só registrada: nenhum teste dorme de verdade (igual ao
    `tests/test_llm_resiliente.py`)."""
    esperas: list[float] = []
    monkeypatch.setattr(llm_mod.time, "sleep", lambda segundos: esperas.append(segundos))
    return esperas


def _porteiro_fake(
    monkeypatch: pytest.MonkeyPatch, codigos: list[int] | None = None, erro: BaseException | None = None
) -> list[list[str]]:
    """Substitui `subprocess.run`: devolve, em ordem, um JSON por código de `codigos` (repetindo o
    último quando acabam), ou levanta `erro`. Guarda cada linha de comando pedida."""
    chamadas: list[list[str]] = []

    def run(comando: list[str], **kwargs: object) -> _ProcessoFake:
        chamadas.append(comando)
        if erro is not None:
            raise erro
        assert codigos is not None
        codigo = codigos[min(len(chamadas) - 1, len(codigos) - 1)]
        return _ProcessoFake(
            json.dumps(
                {"modelo": comando[3], "cabe": codigo == 0, "razao": "cabe", "codigo_de_saida": codigo}
            )
        )

    monkeypatch.setattr(llm_mod.subprocess, "run", run)
    return chamadas


# --------------------------------------------------------------------------------------
# `_consultar_porteiro`: a forma do comando e as quatro degradações para None
# --------------------------------------------------------------------------------------


def test_consultar_porteiro_devolve_o_json_do_porteiro(monkeypatch: pytest.MonkeyPatch) -> None:
    chamadas = _porteiro_fake(monkeypatch, [0])

    resposta = _consultar_porteiro("qwen3:4b", PORTA)

    assert resposta is not None
    assert resposta["codigo_de_saida"] == 0
    assert chamadas == [
        [
            "/opt/homebrew/bin/python3",
            "/Users/sidarta48/github/porteiro_local/bin/porteiro",
            "cabe",
            "qwen3:4b",
            "--porta",
            "11435",
            "--json",
        ]
    ]


def test_consultar_porteiro_usa_caminho_completo_com_o_python_na_frente(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`INTEGRACAO.md §4.1`: nunca o `porteiro` do PATH, nunca `sys.executable`."""
    chamadas = _porteiro_fake(monkeypatch, [0])

    _consultar_porteiro("qwen3:4b", PORTA)

    assert chamadas[0][0].startswith("/")
    assert chamadas[0][1].endswith("/porteiro_local/bin/porteiro")
    assert "--json" in chamadas[0]


@pytest.mark.parametrize(
    "preparar",
    [
        pytest.param(lambda m: _porteiro_fake(m, erro=FileNotFoundError("porteiro")), id="ausente"),
        pytest.param(
            lambda m: _porteiro_fake(m, erro=subprocess.TimeoutExpired("porteiro", 30.0)), id="travou"
        ),
        pytest.param(
            lambda m: m.setattr(llm_mod.subprocess, "run", lambda *a, **k: _ProcessoFake("não é json")),
            id="json_ilegivel",
        ),
        pytest.param(
            lambda m: m.setattr(
                llm_mod.subprocess, "run", lambda *a, **k: _ProcessoFake(json.dumps({"cabe": False}))
            ),
            id="sem_codigo_de_saida",
        ),
        pytest.param(
            lambda m: m.setattr(
                llm_mod.subprocess, "run", lambda *a, **k: _ProcessoFake(json.dumps([1, 2, 3]))
            ),
            id="json_que_nao_e_dict",
        ),
    ],
)
def test_consultar_porteiro_degrada_para_none(preparar: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    preparar(monkeypatch)

    assert _consultar_porteiro("qwen3:4b", PORTA) is None


# --------------------------------------------------------------------------------------
# Modo lote
# --------------------------------------------------------------------------------------


def test_lote_codigo_0_chama_o_ollama_sem_esperar_e_sem_aviso(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, _sem_sono: list[float]
) -> None:
    chamadas = _porteiro_fake(monkeypatch, [0])
    caminho_log = tmp_path / "chamadas_llm.jsonl"
    cliente = _cliente(tmp_path, caminho_log)

    resultado = cliente.gerar_json("qualificar", "prompt", _EsquemaTeste)

    assert resultado.ok is True
    assert len(chamadas) == 1
    assert _sem_sono == []
    assert _avisos(caminho_log) == []
    assert len(_linhas_de_chamada(caminho_log)) == 1


def test_lote_codigo_1_nas_dezesseis_consultas_espera_quinze_vezes_e_roda_assim_mesmo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, _sem_sono: list[float]
) -> None:
    """`INTEGRACAO.md §9`: 16 consultas, 15 esperas de 60 s — e o lote roda ao final, sempre."""
    chamadas = _porteiro_fake(monkeypatch, [1])
    caminho_log = tmp_path / "chamadas_llm.jsonl"
    cliente = _cliente(tmp_path, caminho_log)

    resultado = cliente.gerar_json("qualificar", "prompt", _EsquemaTeste)

    assert resultado.ok is True
    assert len(chamadas) == 16
    assert _sem_sono == [60.0] * 15

    avisos = _avisos(caminho_log)
    assert len(avisos) == 1
    assert avisos[0]["codigo_de_saida"] == 1
    assert avisos[0]["modelo"] == "qwen3:4b"
    assert avisos[0]["porta"] == PORTA
    assert "memória cheia" in str(avisos[0]["aviso"])


def test_lote_que_libera_na_terceira_consulta_espera_duas_vezes_e_nao_avisa(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, _sem_sono: list[float]
) -> None:
    chamadas = _porteiro_fake(monkeypatch, [1, 1, 0])
    caminho_log = tmp_path / "chamadas_llm.jsonl"
    cliente = _cliente(tmp_path, caminho_log)

    cliente.gerar_json("qualificar", "prompt", _EsquemaTeste)

    assert len(chamadas) == 3
    assert _sem_sono == [60.0, 60.0]
    assert _avisos(caminho_log) == []


def test_lote_sem_o_porteiro_instalado_nao_espera_e_registra_o_aviso(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, _sem_sono: list[float]
) -> None:
    """Código `3`, JSON ilegível, programa ausente: seguir como se o `porteiro` não existisse."""
    _porteiro_fake(monkeypatch, erro=FileNotFoundError("porteiro"))
    caminho_log = tmp_path / "chamadas_llm.jsonl"
    cliente = _cliente(tmp_path, caminho_log)

    resultado = cliente.gerar_json("qualificar", "prompt", _EsquemaTeste)

    assert resultado.ok is True
    assert _sem_sono == []

    avisos = _avisos(caminho_log)
    assert len(avisos) == 1
    assert avisos[0]["codigo_de_saida"] is None
    assert "indisponível" in str(avisos[0]["aviso"])


@pytest.mark.parametrize(("codigo", "trecho"), [(2, "não respondeu"), (3, "indisponível")])
def test_lote_codigos_2_e_3_rodam_na_hora_com_aviso(
    codigo: int, trecho: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, _sem_sono: list[float]
) -> None:
    """Só o `1` manda esperar (`INTEGRACAO.md §4.2`)."""
    chamadas = _porteiro_fake(monkeypatch, [codigo])
    caminho_log = tmp_path / "chamadas_llm.jsonl"
    cliente = _cliente(tmp_path, caminho_log)

    cliente.gerar_json("qualificar", "prompt", _EsquemaTeste)

    assert len(chamadas) == 1
    assert _sem_sono == []
    avisos = _avisos(caminho_log)
    assert len(avisos) == 1
    assert avisos[0]["codigo_de_saida"] == codigo
    assert trecho in str(avisos[0]["aviso"])


# --------------------------------------------------------------------------------------
# Modo interativo
# --------------------------------------------------------------------------------------


def test_interativo_nunca_espera_consulta_uma_vez_e_so_avisa(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, _sem_sono: list[float]
) -> None:
    """`INTEGRACAO.md §3`: com uma pessoa esperando, a resposta serve só para avisar."""
    chamadas = _porteiro_fake(monkeypatch, [1])
    caminho_log = tmp_path / "chamadas_llm.jsonl"
    cliente = _cliente(tmp_path, caminho_log, modo_porteiro="interativo")

    resultado = cliente.gerar_json("qualificar", "prompt", _EsquemaTeste)

    assert resultado.ok is True
    assert len(chamadas) == 1
    assert _sem_sono == []
    assert len(_avisos(caminho_log)) == 1


# --------------------------------------------------------------------------------------
# Uma consulta por modelo, nunca por item
# --------------------------------------------------------------------------------------


def test_duas_chamadas_da_mesma_tarefa_consultam_o_porteiro_uma_vez(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    chamadas = _porteiro_fake(monkeypatch, [0])
    cliente = _cliente(tmp_path, tmp_path / "chamadas_llm.jsonl")

    cliente.gerar_json("qualificar", "prompt", _EsquemaTeste)
    cliente.gerar_json("qualificar", "outro prompt", _EsquemaTeste)

    assert len(chamadas) == 1


def test_duas_tarefas_de_modelos_diferentes_consultam_uma_vez_cada_modelo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    chamadas = _porteiro_fake(monkeypatch, [0])
    cliente = _cliente(tmp_path, tmp_path / "chamadas_llm.jsonl")

    cliente.gerar_json("qualificar", "prompt", _EsquemaTeste)  # qwen3:4b
    cliente.gerar_json("descrever_imagem", "prompt", _EsquemaTeste)  # gemma3:4b

    assert [comando[3] for comando in chamadas] == ["qwen3:4b", "gemma3:4b"]


def test_a_nova_tentativa_por_transporte_nao_reconsulta_o_porteiro(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, _sem_sono: list[float]
) -> None:
    """O backoff do brief 064 chama `_chamar` cinco vezes; o `porteiro` é consultado uma só."""
    chamadas = _porteiro_fake(monkeypatch, [0])
    tentativas = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        tentativas["n"] += 1
        if tentativas["n"] == 1:
            return httpx.Response(503)
        return _resposta_json()

    cliente = _cliente(tmp_path, tmp_path / "chamadas_llm.jsonl", handler=handler)

    cliente.gerar_json("qualificar", "prompt", _EsquemaTeste)

    assert tentativas["n"] == 2
    assert len(chamadas) == 1


# --------------------------------------------------------------------------------------
# Embeddings: sempre no Ollama local, então sempre pelo porteiro
# --------------------------------------------------------------------------------------


def test_embeddar_consulta_o_porteiro_pelo_modelo_de_embedding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    chamadas = _porteiro_fake(monkeypatch, [0])
    cliente = _cliente(tmp_path, tmp_path / "chamadas_llm.jsonl")

    cliente.embeddar(["um texto"])
    cliente.embeddar(["outro texto"])

    assert [comando[3] for comando in chamadas] == ["bge-m3"]


def test_cliente_de_api_com_ollama_injetado_consulta_o_porteiro_ao_embeddar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A composição do brief 075 (embedding sempre local) leva o `porteiro` de graça: o cliente de
    API não consulta para gerar texto — não toca o Ollama — e consulta ao repassar `embeddar`."""
    chamadas = _porteiro_fake(monkeypatch, [0])
    caminho_log = tmp_path / "chamadas_llm.jsonl"
    cliente_ollama = _cliente(tmp_path, caminho_log)
    conexao_bd = conexao.abrir(tmp_path / "api.db")
    migracoes.aplicar(conexao_bd)
    cliente_api = ClienteAnthropic(
        httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={}))),
        conexao_bd,
        _roteamento(),
        "chave-de-teste-nao-serve-para-nada",
        "modelo-de-teste",
        caminho_log,
        cliente_ollama,
    )

    cliente_api.embeddar(["um texto"])

    assert [comando[3] for comando in chamadas] == ["bge-m3"]


# --------------------------------------------------------------------------------------
# Porta: vem da `ollama_url`, nunca de uma constante nova
# --------------------------------------------------------------------------------------


def test_a_porta_consultada_e_a_da_ollama_url(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    chamadas = _porteiro_fake(monkeypatch, [0])
    cliente = _cliente(tmp_path, tmp_path / "chamadas_llm.jsonl", ollama_url="http://127.0.0.1:11434")

    cliente.gerar_json("qualificar", "prompt", _EsquemaTeste)

    assert chamadas[0][5] == "11434"


def test_url_sem_porta_explicita_nao_consulta_o_porteiro(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sem porta na `ollama_url`, degrada como se o `porteiro` não existisse — nunca inventa
    uma porta (brief 077, item 3.6)."""
    chamadas = _porteiro_fake(monkeypatch, [0])
    caminho_log = tmp_path / "chamadas_llm.jsonl"
    cliente = _cliente(tmp_path, caminho_log, ollama_url="http://ollama.invalido")

    cliente.gerar_json("qualificar", "prompt", _EsquemaTeste)

    assert chamadas == []
    assert _avisos(caminho_log) == []


# --------------------------------------------------------------------------------------
# Quem escolhe o modo
# --------------------------------------------------------------------------------------


def test_selecionar_cliente_llm_repassa_o_modo_porteiro(tmp_path: Path) -> None:
    conexao_bd = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_bd)
    cliente_http = httpx.Client(transport=httpx.MockTransport(_handler_ok))

    lote = selecionar_cliente_llm(cliente_http, conexao_bd, _roteamento(), OLLAMA_URL, tmp_path / "log.jsonl")
    interativo = selecionar_cliente_llm(
        cliente_http,
        conexao_bd,
        _roteamento(),
        OLLAMA_URL,
        tmp_path / "log.jsonl",
        modo_porteiro="interativo",
    )

    assert isinstance(lote, ClienteOllama)
    assert isinstance(interativo, ClienteOllama)
    assert lote._modo_porteiro == "lote"
    assert interativo._modo_porteiro == "interativo"


def test_o_console_e_interativo_e_a_cli_e_lote() -> None:
    """As três construções do console passam `modo_porteiro="interativo"`; `container.llm()`, que
    atende todo comando de lote da CLI, fica no padrão `"lote"`."""
    app_py = (RAIZ / "agente_nw" / "console" / "app.py").read_text(encoding="utf-8")
    container_py = (RAIZ / "config" / "container.py").read_text(encoding="utf-8")

    assert app_py.count("selecionar_cliente_llm(") == 3
    assert app_py.count('modo_porteiro="interativo"') == 3

    corpo_llm = container_py.split("def llm()", 1)[1]
    assert "modo_porteiro" not in corpo_llm
