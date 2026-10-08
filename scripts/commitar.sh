#!/usr/bin/env bash
# commitar.sh — commita uma leva de arquivos com mensagem lida de um arquivo.
#
# Sidarta roda; o executor não roda git. Existe para evitar o problema do
# terminal quebrar linhas longas de "git add ..." e "git commit -m ...".
#
# Uso:
#   scripts/commitar.sh <arquivo_de_mensagem> <arquivo1> [arquivo2 ...]
#
# Faz, em ordem:
#   1. Confere que o arquivo de mensagem existe e não está vazio.
#   2. Confere que cada arquivo listado existe (rastreado ou não).
#   3. git status antes do add.
#   4. git add em cada arquivo, um por um (§5 do AGENTS.md: nunca -A).
#   5. git status para mostrar o staged.
#   6. Pede confirmação (S/n).
#   7. git commit -F <arquivo_de_mensagem>.
#   8. git log --oneline -3.
#
# Não faz push. Não amenda commit. Não passa --no-verify. Se algum arquivo
# não existir, aborta antes de tocar no git.

set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "uso: $0 <arquivo_de_mensagem> <arquivo1> [arquivo2 ...]" >&2
  exit 2
fi

MSG="$1"
shift
ARQUIVOS=("$@")

if [[ ! -f "$MSG" ]]; then
  echo "FALHA: arquivo de mensagem '$MSG' não existe" >&2
  exit 1
fi

if [[ ! -s "$MSG" ]]; then
  echo "FALHA: arquivo de mensagem '$MSG' está vazio" >&2
  exit 1
fi

for arquivo in "${ARQUIVOS[@]}"; do
  if [[ ! -e "$arquivo" ]]; then
    echo "FALHA: '$arquivo' não existe no working tree" >&2
    exit 1
  fi
done

echo "=== git status antes ==="
git status

echo
echo "=== git add (um por um) ==="
for arquivo in "${ARQUIVOS[@]}"; do
  echo "  + $arquivo"
  git add -- "$arquivo"
done

echo
echo "=== git status depois do add ==="
git status

echo
echo "=== mensagem do commit ==="
cat "$MSG"

echo
read -r -p "Commitar? [S/n] " resposta
resposta="${resposta:-S}"
if [[ ! "$resposta" =~ ^[SsYy]$ ]]; then
  echo "abortado — o staged fica como está."
  exit 0
fi

git commit -F "$MSG"

echo
echo "=== git log --oneline -3 ==="
git log --oneline -3
