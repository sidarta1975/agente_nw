#!/usr/bin/env bash
# Preparação da máquina para o agente_nw — MacBook Air M3, 16 GB, macOS Sonoma.
# Idempotente: pode ser rodado de novo sem efeito colateral.
set -euo pipefail

cd "$(dirname "$0")/.."

# Python 3.12 do Homebrew (traz o próprio SQLite e aceita carregar extensões, que o sqlite-vec exige)
brew install python@3.12

# Ollama: a FÓRMULA do Homebrew instala só o binário. O instalador oficial (e o cask) instala o
# aplicativo, que se registra no login e ocupa a porta 11434 — o que queremos evitar. NÃO iniciar
# por `brew services start ollama`: isso registra um serviço sem as variáveis
# OLLAMA_MAX_LOADED_MODELS / OLLAMA_KEEP_ALIVE, e além disso a arquitetura sob demanda
# (decisão de 2026-09-20) dispensa qualquer agendador ou serviço do projeto.
brew install ollama

ollama pull qwen3:4b
ollama pull bge-m3
ollama pull qwen3:8b   # só para a calibração de agrupamento (comando manual)

echo
echo "Suba o servidor manualmente, num terminal à parte, quando for usar o agente:"
echo "  OLLAMA_MAX_LOADED_MODELS=2 OLLAMA_KEEP_ALIVE=30m ollama serve"
echo "Nunca use 'brew services start ollama' nem o aplicativo Ollama.app."
echo

python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Playwright: a lib Python é instalada pelo pip acima, mas o binário do Chromium
# precisa ser baixado à parte. É usado pela leitura de rede social sob demanda
# (brief 017) — sem ele o comando `agente_nw ler-rede-social` falha na verificação
# de ambiente.
playwright install chromium

mkdir -p dados/backups saidas logs
