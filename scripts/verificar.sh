#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

VENV="$(pwd)/.venv"

if [ ! -x "$VENV/bin/ruff" ]; then
  echo "Ambiente virtual não encontrado em $VENV (ou incompleto)." >&2
  echo "Rode uma vez: python3.12 -m venv .venv && .venv/bin/pip install -e \".[dev]\"" >&2
  exit 1
fi

"$VENV/bin/ruff" check .
"$VENV/bin/ruff" format --check .
"$VENV/bin/mypy" agente_nw
"$VENV/bin/pytest" -q
