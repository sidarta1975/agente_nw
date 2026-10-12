from __future__ import annotations

import functools
import sqlite3
from pathlib import Path
from typing import NamedTuple

import httpx
import yaml

from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.llm import ClienteOllama
from agente_nw.nucleo.modelos.configuracao import Configuracao, Limiares, Roteamento

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
    return httpx.Client(timeout=120.0)


@functools.lru_cache(maxsize=1)
def llm() -> ClienteOllama:
    cfg = configuracao()
    return ClienteOllama(http(), banco(), cfg.roteamento, cfg.local.ollama_url, caminho_log_chamadas_llm())


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
