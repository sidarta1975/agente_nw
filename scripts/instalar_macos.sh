#!/usr/bin/env bash
# Preparação da máquina para o agente_nw — MacBook Air M3, 16 GB, macOS Sonoma.
# Idempotente: pode ser rodado de novo sem efeito colateral.
set -euo pipefail

cd "$(dirname "$0")/.."

# Python 3.12 do Homebrew (traz o próprio SQLite e aceita carregar extensões, que o sqlite-vec exige)
brew install python@3.12

# Máquina compartilhada: se já há um servidor Ollama na porta de destino, não instalar o LaunchAgent
# do projeto — apontar ollama_url (config/local.yaml) para a instância existente.
PORTA_OLLAMA=11434
PID_EXISTENTE=$(lsof -nP -iTCP:"$PORTA_OLLAMA" -sTCP:LISTEN -t 2>/dev/null | head -n1 || true)
if [ -n "$PID_EXISTENTE" ]; then
    COMANDO_EXISTENTE=$(ps -p "$PID_EXISTENTE" -o command= || true)
    echo "já existe um servidor Ollama em $PORTA_OLLAMA (PID $PID_EXISTENTE, comando $COMANDO_EXISTENTE)." >&2
    echo "Em máquina compartilhada, aponte ollama_url em config/local.yaml para a instância existente em vez de instalar o LaunchAgent do projeto." >&2
    exit 1
fi

# Ollama: a FÓRMULA do Homebrew instala só o binário. O instalador oficial (e o cask) instala o
# aplicativo, que se registra no login e ocupa a porta 11434 — o conflito que o LaunchAgent do
# brief 012 quer evitar. NÃO iniciar por `brew services start ollama`: isso cria um segundo
# LaunchAgent sem as variáveis OLLAMA_MAX_LOADED_MODELS / OLLAMA_KEEP_ALIVE.
brew install ollama

ollama pull qwen3:4b
ollama pull bge-m3
ollama pull qwen3:8b   # só para a calibração do brief 007

echo
echo "Até o brief 012 existir, suba o servidor manualmente, num terminal à parte:"
echo "  OLLAMA_MAX_LOADED_MODELS=2 OLLAMA_KEEP_ALIVE=30m ollama serve"
echo "Nunca use 'brew services start ollama' nem o aplicativo Ollama.app."
echo

python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

mkdir -p dados/backups saidas logs
