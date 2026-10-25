#!/usr/bin/env bash
# agente_entregar.sh — gate, commit e push de um brief numa linha só.
#
# Uso (Sidarta, dentro do Claude Code):  !scripts/agente_entregar.sh [--simular] [NNN]
#
# Lê o manifesto que o executor deixa em logs/ (AGENTS §5):
#   logs/commit_<NNN>.txt     mensagem do commit
#   logs/arquivos_<NNN>.txt   um caminho por linha, só o que entra no commit
# Sem NNN, usa o maior número que tem os dois arquivos. Para no primeiro erro:
#   1. confere o manifesto; 2. confere que nada fora da lista foi alterado; 3. gate (scripts/verificar.sh);
#   4. commit (scripts/commitar.sh, sem pergunta); 5. git push; 6. renomeia o manifesto para entregue_*;
#   6b. copia as lacunas do relatório para o PLAN (scripts/agente_lacunas.py); 7. imprime uma linha final.
# --simular mostra os passos sem rodar o gate nem tocar no git. O detalhe vai para logs/entregar_ultimo.txt.
set -euo pipefail
cd "$(dirname "$0")/.."

LOG="logs/entregar_ultimo.txt"
mkdir -p logs
: > "$LOG"

SIMULAR=0
NUMERO=""
for argumento in "$@"; do
  case "$argumento" in
    --simular) SIMULAR=1 ;;
    *) NUMERO="$argumento" ;;
  esac
done

parar() {
  echo "✗ ${NUMERO:+brief $NUMERO: }$1"
  exit 1
}

# 1. Manifesto
if [[ -z "$NUMERO" ]]; then
  maior=-1
  for arquivo in logs/commit_*.txt; do
    [[ -e "$arquivo" ]] || continue
    candidato="${arquivo#logs/commit_}"
    candidato="${candidato%.txt}"
    [[ "$candidato" =~ ^[0-9]+$ ]] || continue
    [[ -s "logs/arquivos_${candidato}.txt" ]] || continue
    if (( 10#$candidato > maior )); then
      maior=$((10#$candidato))
      NUMERO="$candidato"
    fi
  done
  [[ -n "$NUMERO" ]] || parar "nenhum manifesto completo em logs/ (precisa de commit_<NNN>.txt e arquivos_<NNN>.txt)"
fi

MENSAGEM="logs/commit_${NUMERO}.txt"
LISTA="logs/arquivos_${NUMERO}.txt"
[[ -s "$MENSAGEM" ]] || parar "falta $MENSAGEM ou está vazio"
[[ -s "$LISTA" ]] || parar "falta $LISTA ou está vazio"

ARQUIVOS=()
while IFS= read -r linha || [[ -n "$linha" ]]; do
  linha="${linha%$'\r'}"
  [[ -n "${linha// /}" ]] || continue
  if [[ "$linha" == /* || "$linha" == *..* ]]; then
    parar "caminho fora do repositório em $LISTA: $linha"
  fi
  [[ -e "$linha" ]] || parar "caminho de $LISTA não existe: $linha"
  ARQUIVOS+=("$linha")
done < "$LISTA"
(( ${#ARQUIVOS[@]} > 0 )) || parar "$LISTA não lista nenhum arquivo"
echo "manifesto $NUMERO: ${#ARQUIVOS[@]} arquivo(s)" | tee -a "$LOG"

# 2. Nada fora da lista
FORA=()
DENTRO=0
while IFS= read -r linha; do
  caminho="${linha:3}"
  caminho="${caminho##* -> }"
  encontrado=0
  for arquivo in "${ARQUIVOS[@]}"; do
    if [[ "$caminho" == "$arquivo" ]]; then
      encontrado=1
      break
    fi
  done
  if (( encontrado )); then
    DENTRO=$((DENTRO + 1))
  else
    FORA+=("$caminho")
  fi
done < <(git -c core.quotePath=false status --porcelain -uall)
if (( ${#FORA[@]} > 0 )); then
  echo "arquivos alterados fora de $LISTA:" | tee -a "$LOG"
  printf '  %s\n' "${FORA[@]}" | tee -a "$LOG"
  parar "há arquivo fora da lista; inclua em $LISTA ou reverta (nada foi tocado no git)"
fi
(( DENTRO > 0 )) || parar "nenhum arquivo da lista tem alteração para commitar"

if (( SIMULAR )); then
  echo "[simulação] brief $NUMERO, nada será executado:"
  echo "  1. manifesto conferido: $MENSAGEM e $LISTA (${#ARQUIVOS[@]} arquivos)"
  echo "  2. nenhum arquivo alterado fora da lista"
  echo "  3. rodaria scripts/verificar.sh (o gate)"
  echo "  4. rodaria scripts/commitar.sh $MENSAGEM <${#ARQUIVOS[@]} arquivos> (sem pergunta)"
  echo "  5. rodaria git push"
  echo "  6. renomearia o manifesto para logs/entregue_${NUMERO}_commit.txt e entregue_${NUMERO}_arquivos.txt"
  echo "  7. imprimiria: ✓ brief $NUMERO: commit <hash>, enviado ao GitHub"
  exit 0
fi

# 3. Gate
if ! scripts/verificar.sh 2>&1 | tee -a "$LOG"; then
  parar "o gate falhou; nada foi commitado (detalhe: logs/verificar_ultimo.txt)"
fi

# 4. Commit
if ! SEM_PERGUNTA=1 scripts/commitar.sh "$MENSAGEM" "${ARQUIVOS[@]}" >> "$LOG" 2>&1; then
  tail -n 5 "$LOG"
  parar "o commit falhou (detalhe: $LOG)"
fi
HASH="$(git rev-parse --short HEAD)"

# 5 e 6. Push e manifesto. O manifesto é renomeado mesmo se o push falhar: o commit já existe.
PUSH_OK=1
git push >> "$LOG" 2>&1 || PUSH_OK=0
mv "$MENSAGEM" "logs/entregue_${NUMERO}_commit.txt"
mv "$LISTA" "logs/entregue_${NUMERO}_arquivos.txt"
# Lacunas do relatório vão para o PLAN (fora do git; não muda o commit). Nunca derruba a entrega.
if [[ -f scripts/agente_lacunas.py ]]; then
  python3 scripts/agente_lacunas.py "$NUMERO" 2>> "$LOG" | tee -a "$LOG" || true
fi
if (( ! PUSH_OK )); then
  tail -n 3 "$LOG"
  echo "✗ brief $NUMERO: commit $HASH feito localmente; falhou só o envio. Rode: !git push"
  exit 1
fi

# 7. Linha final
echo "✓ brief $NUMERO: commit $HASH, enviado ao GitHub"
