#!/usr/bin/env bash
# executar_serie.sh — roda vários briefs, um depois do outro, sem ninguém acompanhando (brief 086).
#
# Uso:  scripts/executar_serie.sh <NNN> [NNN ...]
#   Exemplo:  scripts/executar_serie.sh 080 081 087 082
#
# Cada brief roda numa sessão nova do Claude Code (`claude -p "/executar NNN"`), com o modelo e o
# esforço do próprio cabeçalho. O sucesso **não** é o código de saída do Claude Code: uma parada
# correta do `/executar` também sai com 0 (relatório 085, item 2.2). O que vale é a prova da
# entrega, conferida aqui em seis itens. Na primeira falha a série para e não tenta o brief
# seguinte (AGENTS §10).
#
# Este script nunca grava no git: o único caminho para commitar continua sendo o
# scripts/agente_entregar.sh, chamado dentro do /executar (AGENTS §5).
#
# Variáveis de ambiente: SERIE_MAX_TURNS, SERIE_MAX_BUDGET_USD.
set -euo pipefail

MAX_TURNS="${SERIE_MAX_TURNS:-250}"
MAX_ORCAMENTO="${SERIE_MAX_BUDGET_USD:-20}"
PALAVRA_ENVIO="push"  # o comando de envio só é citado no STATUS; este script não roda git de escrita

# Mantém o Mac acordado durante a série inteira; `exec` troca o processo, então a série roda dentro.
if [[ -z "${SERIE_DENTRO_DO_CAFFEINATE:-}" ]] && command -v caffeinate >/dev/null 2>&1; then
  export SERIE_DENTRO_DO_CAFFEINATE=1
  exec caffeinate -dimsu "$0" "$@"
fi

cd "$(dirname "$0")/.."

PASTA_SERIE="logs/serie"
TRAVA="$PASTA_SERIE/TRAVA"
PASTA="$PASTA_SERIE/$(date +%Y-%m-%d_%H%M%S)"
STATUS="$PASTA/STATUS.txt"
TODOS="$*"

avisar() {
  command -v osascript >/dev/null 2>&1 || return 0
  osascript -e "display notification \"$1\" with title \"agente_nw: série\"" >/dev/null 2>&1 || true
}

recusar() {  # falha de pré-voo: a série não começou, nada a registrar no STATUS
  echo "✗ $1"
  exit 2
}

if (( $# == 0 )); then
  echo "uso: scripts/executar_serie.sh <NNN> [NNN ...]"
  exit 2
fi

# 1. Trava de instância: uma série por vez (relatório 085, barreira A7).
mkdir -p "$PASTA_SERIE"
if [[ -e "$TRAVA" ]]; then
  echo "✗ já há uma série em andamento (TRAVA em $TRAVA, pid $(cat "$TRAVA" 2>/dev/null || true))."
  echo "  Se não for verdade, apague o arquivo e rode de novo."
  exit 2
fi
echo "$$" > "$TRAVA"
trap 'rm -f "$TRAVA"' EXIT

# 2. Energia na tomada: tampa fechada na bateria faz o Mac dormir no meio da série.
# Sem pipe para o grep de propósito: `grep -q` fecha o pipe antes da hora e o `pipefail` derrubaria
# a conferência mesmo quando ela encontra o que procura.
if command -v pmset >/dev/null 2>&1; then
  ENERGIA="$(pmset -g batt 2>/dev/null || true)"
  case "$ENERGIA" in
    *"AC Power"*) ;;
    *) recusar "o Mac está na bateria: ligue na tomada e deixe a tampa aberta antes de soltar a série" ;;
  esac
fi

# 3. Árvore limpa e nada pendente de envio: o agente_entregar.sh recusa arquivo fora do manifesto.
SUJO="$(git status --porcelain -uall)"
if [[ -n "$SUJO" ]]; then
  echo "$SUJO"
  recusar "a árvore de trabalho não está limpa; commite ou reverta antes da série"
fi
PENDENTE="$(git rev-list --count origin/main..HEAD)"
[[ "$PENDENTE" == "0" ]] ||
  recusar "há $PENDENTE commit(s) sem envio ao GitHub; envie antes da série"

# 4. Cabeçalho de cada brief (um arquivo por número, Modelo, Esforço, Ordem em série) e a ordem da
#    lista. Qualquer problema recusa a série inteira, antes de chamar o Claude Code uma só vez.
PREVOO="$(python3 - "$@" <<'FIM'
import glob
import re
import sys

ESFORCOS = {"baixo": "low", "médio": "medium", "medio": "medium", "alto": "high"}


def campo(texto: str, rotulo: str) -> str:
    achado = re.search(rf"^\*\*{rotulo}:\*\*\s*(.+)$", texto, re.MULTILINE)
    return achado.group(1).strip() if achado else ""


def citados(ordem: str, marca: str) -> list[str]:
    numeros: list[str] = []
    for parte in re.split(r"[;.]", ordem):
        achado = re.search(rf"{marca}\s+(.+)", parte)
        if achado:
            numeros += re.findall(r"\b(\d{3})\b", achado.group(1))
    return numeros


numeros = sys.argv[1:]
problemas: list[str] = []
avisos: list[str] = []
briefs: dict[str, tuple[str, str, str]] = {}

for numero in numeros:
    achados = sorted(glob.glob(f"docs/briefs/brief_{numero}_*.md"))
    if len(achados) != 1:
        problemas.append(
            f"brief {numero}: {len(achados)} arquivo(s) em docs/briefs/ (precisa de exatamente 1)"
        )
        continue
    with open(achados[0], encoding="utf-8") as arquivo:
        texto = arquivo.read()
    modelo = campo(texto, "Modelo").split()[0].lower() if campo(texto, "Modelo") else ""
    bruto = campo(texto, "Esforço")
    esforco = ESFORCOS.get(bruto.split()[0].lower(), "") if bruto else ""
    ordem = campo(texto, "Ordem em série")
    if not modelo:
        problemas.append(f"brief {numero}: falta o campo Modelo no cabeçalho")
    if not esforco:
        problemas.append(f"brief {numero}: falta o campo Esforço (baixo, médio ou alto) no cabeçalho")
    if not ordem:
        problemas.append(f"brief {numero}: falta o campo Ordem em série no cabeçalho")
    if ordem:
        briefs[numero] = (modelo, esforco, ordem)
        reconhecido = ordem.strip().lower().startswith("livre") or citados(ordem, "depois de") or citados(
            ordem, "antes de"
        )
        if not reconhecido:
            avisos.append(f"brief {numero}: ordem em série não reconhecida, não aplicada: {ordem!r}")

posicao = {numero: i for i, numero in enumerate(numeros)}
for numero, (_modelo, _esforco, ordem) in briefs.items():
    for outro in citados(ordem, "depois de"):
        if outro in posicao and posicao[outro] > posicao[numero]:
            problemas.append(
                f"ordem violada: o brief {numero} roda depois do {outro}, e na lista vem antes"
            )
    for outro in citados(ordem, "antes de"):
        if outro in posicao and posicao[outro] < posicao[numero]:
            problemas.append(
                f"ordem violada: o brief {numero} roda antes do {outro}, e na lista vem depois"
            )

for aviso in avisos:
    print(f"aviso: {aviso}", file=sys.stderr)
if problemas:
    for problema in problemas:
        print(f"✗ {problema}", file=sys.stderr)
    raise SystemExit(2)
for numero in numeros:
    modelo, esforco, _ordem = briefs[numero]
    print(f"{numero}|{modelo}|{esforco}")
FIM
)" || recusar "pré-voo recusou a lista (acima o motivo); nenhum brief foi executado"

mkdir -p "$PASTA"
{
  echo "série de $(date '+%Y-%m-%d %H:%M'): $TODOS"
  echo ""
} > "$STATUS"

AJUSTES=()
[[ -f .claude/serie.settings.json ]] && AJUSTES=(--settings .claude/serie.settings.json)

CUSTO_TOTAL=0
PENDENCIAS=""
ENTREGUES=0

parar_no_brief() {  # parar_no_brief <NNN> <motivo>
  {
    echo "$1 PAROU: $2"
    echo ""
    echo "custo somado até aqui: US\$ $CUSTO_TOTAL (preço de tabela)"
    echo "retomar com: scripts/executar_serie.sh $TODOS"
    echo "  (brief já entregue é pulado pelo manifesto entregue_*)"
  } >> "$STATUS"
  echo "✗ brief $1 PAROU: $2"
  echo "  detalhe em $STATUS"
  avisar "brief $1 PAROU: $2"
  exit 1
}

while IFS='|' read -r NUMERO MODELO ESFORCO; do
  [[ -n "$NUMERO" ]] || continue

  if [[ -f "logs/entregue_${NUMERO}_commit.txt" && -f "logs/entregue_${NUMERO}_arquivos.txt" ]]; then
    echo "$NUMERO pulado: já entregue (manifesto logs/entregue_${NUMERO}_*)" | tee -a "$STATUS"
    continue
  fi

  echo "→ brief $NUMERO ($MODELO, esforço $ESFORCO)"
  SAIDA="$PASTA/$NUMERO.json"
  claude -p "/executar $NUMERO" \
    --model "$MODELO" \
    --effort "$ESFORCO" \
    --permission-prompts none \
    --max-turns "$MAX_TURNS" \
    --max-budget-usd "$MAX_ORCAMENTO" \
    --output-format json \
    ${AJUSTES[@]+"${AJUSTES[@]}"} \
    > "$SAIDA" 2> "$PASTA/$NUMERO.erro.txt" || true

  # Conferência 1: o que o próprio Claude Code devolveu (is_error, subtype, linha PAROU, pendência).
  LEITURA="$(python3 - "$SAIDA" <<'FIM'
import json
import sys

try:
    with open(sys.argv[1], encoding="utf-8") as arquivo:
        dados = json.load(arquivo)
except (OSError, ValueError) as erro:
    print(f"falha|saída do Claude Code ilegível ({type(erro).__name__})|0|")
    raise SystemExit(0)

custo = dados.get("total_cost_usd") or 0
linhas = [linha.strip() for linha in str(dados.get("result") or "").splitlines() if linha.strip()]
parou = next((linha for linha in linhas if linha.startswith("PAROU:")), "")
pendencia = next((linha for linha in linhas if linha.startswith("Para você")), "")

if dados.get("is_error") or dados.get("subtype") != "success":
    motivo = f"is_error={dados.get('is_error')}, subtype={dados.get('subtype')}"
    print(f"falha|{motivo}|{custo}|{pendencia}")
elif parou:
    print(f"falha|{parou}|{custo}|{pendencia}")
else:
    print(f"ok||{custo}|{pendencia}")
FIM
)"
  IFS='|' read -r ESTADO MOTIVO CUSTO PENDENCIA <<< "$LEITURA"
  CUSTO_TOTAL="$(awk "BEGIN{printf \"%.4f\", $CUSTO_TOTAL + ${CUSTO:-0}}")"
  [[ "$ESTADO" == "ok" ]] || parar_no_brief "$NUMERO" "$MOTIVO"

  # Conferência 2: a prova da entrega, no disco e no git (relatório 085, item 4.2).
  if [[ ! -f "logs/entregue_${NUMERO}_commit.txt" || ! -f "logs/entregue_${NUMERO}_arquivos.txt" ]]; then
    parar_no_brief "$NUMERO" "o manifesto não virou logs/entregue_${NUMERO}_* — o brief não entregou"
  fi
  ASSUNTO_DO_COMMIT="$(git log -1 --format=%s)"
  case "$ASSUNTO_DO_COMMIT" in
    *"$NUMERO"*) ;;
    *) parar_no_brief "$NUMERO" "o commit mais novo não cita o brief: $ASSUNTO_DO_COMMIT" ;;
  esac
  if [[ "$(git rev-list --count origin/main..HEAD)" != "0" ]]; then
    parar_no_brief "$NUMERO" "o commit não foi enviado ao GitHub; rode: git $PALAVRA_ENVIO"
  fi
  RESTO="$(git status --porcelain -uall)"
  if [[ -n "$RESTO" ]]; then
    parar_no_brief "$NUMERO" "a árvore ficou suja depois da entrega: $(echo "$RESTO" | tr '\n' ' ')"
  fi

  HASH="$(git rev-parse --short HEAD)"
  echo "$NUMERO entregue $HASH" | tee -a "$STATUS"
  ENTREGUES=$((ENTREGUES + 1))
  if [[ -n "$PENDENCIA" ]]; then
    PENDENCIAS="$PENDENCIAS$NUMERO: $PENDENCIA"$'\n'
    echo "  pendência humana: $PENDENCIA"
  fi
done <<< "$PREVOO"

{
  echo ""
  echo "CONCLUÍDA: $ENTREGUES brief(s) entregue(s) de [$TODOS]"
  echo "custo somado: US\$ $CUSTO_TOTAL (preço de tabela)"
  if [[ -n "$PENDENCIAS" ]]; then
    echo ""
    echo "pendências humanas (não impediram o commit):"
    printf '%s' "$PENDENCIAS"
  fi
} >> "$STATUS"

echo "✓ série concluída: $ENTREGUES brief(s). Detalhe em $STATUS"
avisar "série concluída: $ENTREGUES brief(s)"
