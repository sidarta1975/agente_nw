from __future__ import annotations

import functools
import sqlite3
from pathlib import Path
from typing import NamedTuple

import httpx
import yaml

from agente_nw.nucleo import prompts
from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.llm import (
    ClienteAnthropic,
    ClienteGemini,
    ClienteOllama,
    ClienteOpenAI,
)
from agente_nw.nucleo.modelos.configuracao import (
    Configuracao,
    ConfiguracaoIaApi,
    Limiares,
    ProvedorApi,
    Roteamento,
)

ClienteLLM = ClienteOllama | ClienteAnthropic | ClienteGemini | ClienteOpenAI
"""O que `selecionar_cliente_llm` devolve. Os módulos do produto não usam este nome: cada um declara
o `Protocol` local com os métodos de que precisa (`gerar_json`, `proveniencia`, `modelo_embedding`)."""

_ORDEM_PROVEDORES: tuple[str, ...] = ("anthropic", "gemini", "openai")
"""Prioridade do `provedor: auto` (brief 076, item 3.2): a primeira cadastrada nesta ordem. Não tem
critério técnico além de ser previsível e documentada — quem quiser outra põe o nome em `provedor`."""

_CLASSES_API: dict[str, type[ClienteAnthropic] | type[ClienteGemini] | type[ClienteOpenAI]] = {
    "anthropic": ClienteAnthropic,
    "gemini": ClienteGemini,
    "openai": ClienteOpenAI,
}

RAIZ = Path(__file__).resolve().parent.parent


class ConfiguracaoCarregada(NamedTuple):
    local: Configuracao
    roteamento: Roteamento
    limiares: Limiares


def _carregar_yaml(caminho: Path) -> dict[str, object]:
    dados = yaml.safe_load(caminho.read_text(encoding="utf-8"))
    return dados if isinstance(dados, dict) else {}


@functools.lru_cache(maxsize=1)
def configuracao() -> ConfiguracaoCarregada:
    caminho_local = RAIZ / "config" / "local.yaml"
    if not caminho_local.exists():
        caminho_local = RAIZ / "config" / "local.exemplo.yaml"

    local = Configuracao.model_validate(_carregar_yaml(caminho_local))
    dados_roteamento = _carregar_yaml(RAIZ / "config" / "llm_routing.yaml")
    if local.perfil_llm is not None:
        dados_roteamento["perfil_ativo"] = local.perfil_llm
    roteamento = Roteamento.model_validate(dados_roteamento)
    limiares = Limiares.model_validate(_carregar_yaml(RAIZ / "config" / "limiares.yaml"))
    prompts.verificar_versoes()
    return ConfiguracaoCarregada(local=local, roteamento=roteamento, limiares=limiares)


def gravar_usuario_rede(rede: str, usuario: str) -> None:
    """Grava `redes.<rede>.usuario` em config/local.yaml (criando o arquivo a partir do exemplo)."""
    caminho = RAIZ / "config" / "local.yaml"
    origem = caminho if caminho.exists() else RAIZ / "config" / "local.exemplo.yaml"
    texto = origem.read_text(encoding="utf-8")
    dados = yaml.safe_load(texto) or {}
    if not dados.get("redes"):
        # Anexa o bloco novo e preserva os comentários do arquivo.
        bloco = f"\nredes:\n  {rede}:\n    usuario: {usuario}\n"
        caminho.write_text(texto.rstrip("\n") + bloco, encoding="utf-8")
    else:
        dados["redes"].setdefault(rede, {})["usuario"] = usuario
        caminho.write_text(yaml.safe_dump(dados, allow_unicode=True, sort_keys=False), encoding="utf-8")
    configuracao.cache_clear()


def origem_perfil_llm() -> str:
    return "config/local.yaml" if configuracao().local.perfil_llm is not None else "config/llm_routing.yaml"


@functools.lru_cache(maxsize=1)
def http() -> httpx.Client:
    return httpx.Client(timeout=600.0)


def _provedor_escolhido(ia_api: ConfiguracaoIaApi) -> str:
    if ia_api.provedor != "auto":
        return ia_api.provedor
    for nome in _ORDEM_PROVEDORES:
        provedor: ProvedorApi | None = getattr(ia_api, nome)
        if provedor is not None and provedor.chave.strip() and provedor.modelo.strip():
            return nome
    return "ollama"


def selecionar_cliente_llm(
    http_client: httpx.Client,
    conexao_bd: sqlite3.Connection,
    roteamento: Roteamento,
    ollama_url: str,
    caminho_log: Path,
    ia_api: ConfiguracaoIaApi | None = None,
) -> ClienteLLM:
    """O único lugar que decide qual provedor gera texto (brief 076). Com chave cadastrada em
    `ia_api`, devolve o cliente daquela API; sem nenhuma, o `ClienteOllama` — o comportamento de
    sempre. O `ClienteOllama` é construído em qualquer caso, porque é ele que faz os embeddings,
    que nunca saem da máquina (brief 075, item 3.5)."""
    cliente_ollama = ClienteOllama(http_client, conexao_bd, roteamento, ollama_url, caminho_log)
    escolhido = _provedor_escolhido(ia_api or ConfiguracaoIaApi())
    if escolhido == "ollama":
        return cliente_ollama

    provedor: ProvedorApi | None = getattr(ia_api, escolhido, None)
    if provedor is None or not provedor.chave.strip() or not provedor.modelo.strip():
        raise ValueError(
            f"ia_api.provedor = '{escolhido}' em config/local.yaml, mas o bloco "
            f"ia_api.{escolhido} não tem 'chave' e 'modelo' preenchidos"
        )
    return _CLASSES_API[escolhido](
        http_client,
        conexao_bd,
        roteamento,
        provedor.chave,
        provedor.modelo,
        caminho_log,
        cliente_ollama,
    )


@functools.lru_cache(maxsize=1)
def llm() -> ClienteLLM:
    cfg = configuracao()
    return selecionar_cliente_llm(
        http(),
        banco(),
        cfg.roteamento,
        cfg.local.ollama_url,
        caminho_log_chamadas_llm(),
        cfg.local.ia_api,
    )


def caminho_banco() -> Path:
    caminho = Path(configuracao().local.banco)
    return caminho if caminho.is_absolute() else RAIZ / caminho


def caminho_pasta_backups() -> Path:
    caminho = Path(configuracao().local.pasta_backups)
    return caminho if caminho.is_absolute() else RAIZ / caminho


def caminho_pasta_saida() -> Path:
    caminho = Path(configuracao().local.pasta_saida)
    return caminho if caminho.is_absolute() else RAIZ / caminho


def caminho_sentinela() -> Path:
    return RAIZ / "dados" / "PARE"


def caminho_limiares_yaml() -> Path:
    return RAIZ / "config" / "limiares.yaml"


def caminho_pasta_adr() -> Path:
    return RAIZ / "docs" / "adr"


def caminho_log_chamadas_llm() -> Path:
    return RAIZ / "dados" / "logs" / "chamadas_llm.jsonl"


@functools.lru_cache(maxsize=1)
def banco() -> sqlite3.Connection:
    conn = conexao.abrir(caminho_banco())
    migracoes.aplicar(conn)
    return conn
