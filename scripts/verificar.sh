#!/usr/bin/env bash
# verificar.sh — o gate: ruff, formatação, mypy e pytest.
#
# A saída completa vai para logs/verificar_ultimo.txt. Na tela fica "ok" ou "falhou" por etapa; numa falha,
# só o que ajuda a achar o defeito. Para na primeira etapa que falhar. Código de saída diferente de zero em
# qualquer falha. Quem roda é Sidarta (AGENTS §6).
set -euo pipefail
cd "$(dirname "$0")/.."

VENV="$(pwd)/.venv"
LOG="logs/verificar_ultimo.txt"
PARCIAL="$(mktemp)"
trap 'rm -f "$PARCIAL"' EXIT

if [ ! -x "$VENV/bin/ruff" ]; then
  echo "Ambiente virtual não encontrado em $VENV (ou incompleto)." >&2
  echo "Rode uma vez: python3.12 -m venv .venv && .venv/bin/pip install -e \".[dev]\"" >&2
  exit 1
fi

mkdir -p logs
: > "$LOG"

# etapa <nome> <comando...>: roda, guarda a saída no log e deixa a saída da etapa em $PARCIAL.
etapa() {
  local nome="$1"
  shift
  local status=0
  "$@" > "$PARCIAL" 2>&1 || status=$?
  { echo "### $nome (código $status)"; cat "$PARCIAL"; echo; } >> "$LOG"
  return "$status"
}

falhou() {
  echo "$1: falhou (detalhe completo em $LOG)"
}

if ! etapa "ruff check" "$VENV/bin/ruff" check .; then
  falhou "ruff check"
  head -n 15 "$PARCIAL"
  exit 1
fi
echo "ruff check: ok"

if ! etapa "ruff format" "$VENV/bin/ruff" format --check .; then
  falhou "ruff format"
  head -n 15 "$PARCIAL"
  exit 1
fi
echo "ruff format: ok"

if ! etapa "mypy" "$VENV/bin/mypy" agente_nw; then
  falhou "mypy"
  head -n 15 "$PARCIAL"
  exit 1
fi
echo "mypy: ok"

if ! etapa "pytest" "$VENV/bin/pytest" -q; then
  falhou "pytest"
  grep -E '^(FAILED|ERROR) ' "$PARCIAL" || true
  tail -n 1 "$PARCIAL"
  exit 1
fi
echo "pytest: ok ($(tail -n 1 "$PARCIAL"))"
