"""Seleção do provedor de geração (brief 076): com chave cadastrada em `ia_api`
(`config/local.yaml`), a geração de texto vai para aquela API; sem nenhuma chave, segue no Ollama,
como sempre foi. Embeddings são sempre do `ClienteOllama` local, qualquer que seja o provedor."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import httpx
import pytest
import yaml

from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.llm import ClienteAnthropic, ClienteGemini, ClienteOllama, ClienteOpenAI
from agente_nw.nucleo.modelos.configuracao import Configuracao, ConfiguracaoIaApi, Roteamento
from config.container import selecionar_cliente_llm

RAIZ = Path(__file__).resolve().parent.parent


def _roteamento() -> Roteamento:
    dados = yaml.safe_load((RAIZ / "config" / "llm_routing.yaml").read_text(encoding="utf-8"))
    return Roteamento.model_validate(dados)


def _conexao(tmp_path: Path) -> sqlite3.Connection:
    conexao_bd = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_bd)
    return conexao_bd


def _selecionar(tmp_path: Path, ia_api: ConfiguracaoIaApi | None) -> object:
    return selecionar_cliente_llm(
        httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={}))),
        _conexao(tmp_path),
        _roteamento(),
        "http://ollama.invalido",
        tmp_path / "chamadas_llm.jsonl",
        ia_api,
    )


def _ia_api(**blocos: object) -> ConfiguracaoIaApi:
    return ConfiguracaoIaApi.model_validate(blocos)


# --------------------------------------------------------------------------------------
# Sem chave nenhuma: nada muda
# --------------------------------------------------------------------------------------


def test_sem_bloco_ia_api_devolve_cliente_ollama(tmp_path: Path) -> None:
    assert isinstance(_selecionar(tmp_path, None), ClienteOllama)


def test_bloco_ia_api_vazio_devolve_cliente_ollama(tmp_path: Path) -> None:
    assert isinstance(_selecionar(tmp_path, ConfiguracaoIaApi()), ClienteOllama)


def test_configuracao_sem_ia_api_no_yaml_vira_o_padrao_de_ollama() -> None:
    """`config/local.exemplo.yaml` (e o `local.yaml` de todo instalador existente) não tem o bloco:
    o campo novo não pode ser obrigatório."""
    cfg = Configuracao.model_validate(
        yaml.safe_load((RAIZ / "config" / "local.exemplo.yaml").read_text(encoding="utf-8"))
    )
    assert cfg.ia_api == ConfiguracaoIaApi()
    assert cfg.ia_api.provedor == "auto"
    assert cfg.ia_api.anthropic is None
    assert cfg.ia_api.gemini is None
    assert cfg.ia_api.openai is None


def test_provedor_ollama_explicito_ignora_chave_cadastrada(tmp_path: Path) -> None:
    ia_api = _ia_api(provedor="ollama", anthropic={"chave": "sk-ant-x", "modelo": "claude-x"})

    assert isinstance(_selecionar(tmp_path, ia_api), ClienteOllama)


# --------------------------------------------------------------------------------------
# provedor: auto — a primeira da ordem fixa Anthropic > Gemini > OpenAI
# --------------------------------------------------------------------------------------


def test_auto_com_so_anthropic_devolve_cliente_anthropic(tmp_path: Path) -> None:
    ia_api = _ia_api(anthropic={"chave": "sk-ant-x", "modelo": "claude-x"})

    assert isinstance(_selecionar(tmp_path, ia_api), ClienteAnthropic)


def test_auto_com_so_gemini_devolve_cliente_gemini(tmp_path: Path) -> None:
    ia_api = _ia_api(gemini={"chave": "g-x", "modelo": "gemini-x"})

    assert isinstance(_selecionar(tmp_path, ia_api), ClienteGemini)


def test_auto_com_so_openai_devolve_cliente_openai(tmp_path: Path) -> None:
    ia_api = _ia_api(openai={"chave": "o-x", "modelo": "gpt-x"})

    assert isinstance(_selecionar(tmp_path, ia_api), ClienteOpenAI)


def test_auto_com_anthropic_e_openai_prefere_anthropic(tmp_path: Path) -> None:
    ia_api = _ia_api(
        anthropic={"chave": "sk-ant-x", "modelo": "claude-x"},
        openai={"chave": "o-x", "modelo": "gpt-x"},
    )

    assert isinstance(_selecionar(tmp_path, ia_api), ClienteAnthropic)


def test_auto_com_gemini_e_openai_prefere_gemini(tmp_path: Path) -> None:
    ia_api = _ia_api(
        gemini={"chave": "g-x", "modelo": "gemini-x"},
        openai={"chave": "o-x", "modelo": "gpt-x"},
    )

    assert isinstance(_selecionar(tmp_path, ia_api), ClienteGemini)


def test_auto_com_chave_em_branco_nao_conta_como_cadastrada(tmp_path: Path) -> None:
    ia_api = _ia_api(
        anthropic={"chave": "   ", "modelo": "claude-x"},
        openai={"chave": "o-x", "modelo": "gpt-x"},
    )

    assert isinstance(_selecionar(tmp_path, ia_api), ClienteOpenAI)


# --------------------------------------------------------------------------------------
# provedor explícito vence a prioridade automática; sem o sub-bloco, erro na inicialização
# --------------------------------------------------------------------------------------


def test_provedor_openai_explicito_vence_a_prioridade_da_anthropic(tmp_path: Path) -> None:
    ia_api = _ia_api(
        provedor="openai",
        anthropic={"chave": "sk-ant-x", "modelo": "claude-x"},
        openai={"chave": "o-x", "modelo": "gpt-x"},
    )

    assert isinstance(_selecionar(tmp_path, ia_api), ClienteOpenAI)


@pytest.mark.parametrize("provedor", ["anthropic", "gemini", "openai"])
def test_provedor_explicito_sem_o_sub_bloco_falha_na_inicializacao(provedor: str, tmp_path: Path) -> None:
    """Erro claro ao montar o cliente, não uma falha silenciosa na primeira chamada."""
    with pytest.raises(ValueError, match=provedor):
        _selecionar(tmp_path, _ia_api(provedor=provedor))


def test_provedor_desconhecido_nao_passa_pela_validacao_do_modelo() -> None:
    with pytest.raises(ValueError):
        _ia_api(provedor="gpt4all")


# --------------------------------------------------------------------------------------
# O ClienteOllama interno existe sempre e é o cliente de embeddings do cliente de API
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("bloco", "classe"),
    [
        ({"anthropic": {"chave": "sk-ant-x", "modelo": "claude-x"}}, ClienteAnthropic),
        ({"gemini": {"chave": "g-x", "modelo": "gemini-x"}}, ClienteGemini),
        ({"openai": {"chave": "o-x", "modelo": "gpt-x"}}, ClienteOpenAI),
    ],
)
def test_cliente_de_api_recebe_um_cliente_ollama_como_cliente_de_embeddings(
    bloco: dict[str, object], classe: type, tmp_path: Path
) -> None:
    cliente = _selecionar(tmp_path, _ia_api(**bloco))

    assert isinstance(cliente, classe)
    embeddings = cliente._cliente_embeddings
    assert isinstance(embeddings, ClienteOllama)
    assert embeddings.modelo_embedding == cliente.modelo_embedding


@pytest.mark.parametrize(
    ("bloco", "modelo"),
    [
        ({"anthropic": {"chave": "sk-ant-x", "modelo": "claude-x"}}, "claude-x"),
        ({"gemini": {"chave": "g-x", "modelo": "gemini-x"}}, "gemini-x"),
        ({"openai": {"chave": "o-x", "modelo": "gpt-x"}}, "gpt-x"),
    ],
)
def test_proveniencia_do_cliente_escolhido_registra_o_modelo_da_api(
    bloco: dict[str, object], modelo: str, tmp_path: Path
) -> None:
    """É por este campo que se confere no `chamadas_llm.jsonl` qual provedor atendeu."""
    cliente = _selecionar(tmp_path, _ia_api(**bloco))

    assert cliente.proveniencia("qualificar").modelo == modelo


# --------------------------------------------------------------------------------------
# Não sobrou nenhum lugar decidindo o provedor de outro jeito (item 3.3 do brief)
# --------------------------------------------------------------------------------------


def test_nenhuma_construcao_direta_de_cliente_fora_da_selecao() -> None:
    """`container.llm()` e as três construções de `agente_nw/console/app.py` passam todas por
    `selecionar_cliente_llm`; só a própria função constrói um cliente direto."""
    container_py = (RAIZ / "config" / "container.py").read_text(encoding="utf-8")
    app_py = (RAIZ / "agente_nw" / "console" / "app.py").read_text(encoding="utf-8")

    corpo_selecao = container_py.split("def selecionar_cliente_llm", 1)[1]
    fora_da_selecao = container_py.split("def selecionar_cliente_llm", 1)[0]

    assert "ClienteOllama(" in corpo_selecao
    assert "ClienteOllama(" not in fora_da_selecao
    for classe in ("ClienteOllama(", "ClienteAnthropic(", "ClienteGemini(", "ClienteOpenAI("):
        assert classe not in app_py, f"{classe} construído direto em console/app.py"
    assert app_py.count("selecionar_cliente_llm(") == 3
