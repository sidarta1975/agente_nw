#!/usr/bin/env bash
set -euo pipefail

RAIZ="/Users/sidarta48/github/agente_nw"
LOG_WRAPPER="$RAIZ/dados/logs/rodar_ciclo.log"

cd "$RAIZ"
mkdir -p "$RAIZ/dados/logs"

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] rodar_ciclo.sh iniciado" >> "$LOG_WRAPPER"

sleep 300

"$RAIZ/.venv/bin/agente_nw" ciclo

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] rodar_ciclo.sh terminado" >> "$LOG_WRAPPER"
