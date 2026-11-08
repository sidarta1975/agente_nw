# Doc 073 — Estado local do projeto não atravessa sessão nem worktree, no AGENTS.md

**Brief:** `docs/briefs/brief_073_estado_local_multiplas_sessoes_2026-11-02.md`
**Data:** 2026-11-02

## O que foi feito

Acrescentada a seção **§12 "Estado local: uma árvore de trabalho só"** ao `AGENTS.md`, logo depois da §11
que o brief 072 abriu nesta mesma sequência. A numeração foi conferida antes de escrever, como o brief
pediu (a linha "Depende de" avisava do acoplamento de lugar entre 072 e 073): o arquivo ia de §1 a §10,
o 072 acrescentou a §11, então §12 é o número livre.

## Os achados do brief, conferidos um a um no código

Nenhum foi aceito por suposição:

| Afirmação do brief | Conferência | Resultado |
|---|---|---|
| O banco é resolvido contra a raiz da árvore de trabalho | `config/container.py:16` `RAIZ = Path(__file__).resolve().parent.parent`; `:77-79` `caminho_banco()` devolve `RAIZ / caminho` quando o caminho é relativo | confirmado |
| `dados/agente.db` é caminho relativo | `config/local.yaml:1` `banco: dados/agente.db` | confirmado |
| `.gitignore` exclui `docs/` inteiro, só com `.gitkeep` de exceção | `.gitignore:22-23` `docs/*` e `!docs/.gitkeep` | confirmado |
| Nenhum arquivo de `docs/` jamais entrou num commit | `git ls-files docs/` devolve 0 arquivos | confirmado |
| Já existiu a worktree `agente_nw_040` | `.git/worktrees/` ainda lista `agente_nw_040`, com a pasta já apagada | confirmado |

Além disso, a §12 registra o ponto que veio do material sobre as quatro superfícies do Claude Code
(terminal, aplicativo Desktop, Remote Control, Dispatch): mesma engine e mesma configuração de projeto,
mas sem histórico de conversa compartilhado, e disco compartilhado só dentro da mesma árvore de trabalho.

## Conferência de coerência com as seções existentes (item 4 do brief)

- **§11 (Cowork, acrescentada pelo brief 072)** — fala de *onde o código pode ser executado*; a §12 fala de
  *onde o estado local vive*. Não se sobrepõem, e as duas chegam à mesma conclusão: o trabalho real
  acontece na sessão de terminal de Sidarta, na árvore principal.
- **§6 (Tarefas não assistidas)** — "SQLite nunca compartilhado entre processos" e "desenvolvimento sempre
  em cópia (`agente_nw copiar-banco`)". A §12 não contradiz: ela trata de *qual* banco uma árvore vê, não
  de quantos processos o abrem ao mesmo tempo.
- **§3 (Stack)** — "SQLite em modo WAL, arquivo único em `dados/agente.db`, nunca compartilhado entre
  processos". Coerente: a §12 explica que esse caminho único é único *por árvore de trabalho*.
- **§10 (Briefs e numeração)** — "O próximo número é o maior encontrado em `docs/briefs/` e `docs/docs/`,
  mais um". A §12 esclarece uma consequência disso que não estava escrita em lugar nenhum: como `docs/`
  não é versionada, a numeração dos briefs depende de arquivos locais daquela árvore.

Nenhuma contradição encontrada.

## Arquivos alterados

- `AGENTS.md` — nova seção §12, depois da §11; nenhuma seção existente foi reescrita.

## Arquivos preservados literalmente

- Todo o resto do `AGENTS.md`, incluindo a §11 recém-acrescentada pelo brief 072.
- `config/container.py` e a resolução do banco — lidos, não tocados (item 5 do brief).
- O registro da worktree `agente_nw_040` — deixado como está, por decisão do próprio brief (item 5).

## RELATÓRIO FINAL

- **Brief executado:** 073 — documentar no `AGENTS.md` que o estado local não atravessa sessão nem worktree.
- **Arquivos criados:** `docs/docs/doc_073_estado_local_multiplas_sessoes_2026-11-02.md`,
  `logs/commit_073.txt`, `logs/arquivos_073.txt`.
- **Arquivos alterados (resumo em uma linha cada):**
  - `AGENTS.md` — nova §12: banco e `docs/` são estado de uma árvore de trabalho só; todo trabalho na
    árvore principal, e Remote Control para continuar de outro aparelho.
- **Arquivos preservados literalmente na área afetada:** §1 a §11 do `AGENTS.md`;
  `config/container.py`; nenhum código tocado.
- **Script de verificação (o gate, rodado pelo `scripts/agente_entregar.sh`; saída colada):** ver
  "Saída do gate" abaixo.
- **Comandos executados:**
  - `grep` em `config/container.py`, `config/local.yaml` e `.gitignore` (conferência dos achados, acima)
  - `git ls-files docs/ | wc -l` → `0`
  - `ls .git/worktrees/` → `agente_nw_040`
  - `scripts/agente_entregar.sh 073`
- **Manifesto do commit (`logs/arquivos_073.txt` e `logs/commit_073.txt`):** ver abaixo.
- **Pendências e decisões que ficaram abertas:** se `docs/` deve passar a ser versionada — decisão de
  Sidarta, na tabela de lacunas abaixo.
- **Resumo, Doing, Backlog e Done do `docs/PLAN.md` atualizados:** sim.

## Saída do gate

```
$ scripts/agente_entregar.sh 073
manifesto 073: 1 arquivo(s)
ruff check: ok
ruff format: ok
mypy: ok
pytest: ok (911 passed, 5 deselected in 33.68s)
lacunas do 073: 0 no Backlog, 0 em Pendencias, 0 em Dividas, 1 em Decisoes
✓ brief 073: commit 33a4550, enviado ao GitHub
```

## Manifesto

`logs/arquivos_073.txt`:

```
AGENTS.md
```

`logs/commit_073.txt`:

```
docs(agents): secao 12, banco e docs sao estado de uma arvore de trabalho so (brief 073)
```

## Lacunas

| # | Lacuna | Destino | Impacto |
|---|--------|---------|---------|
| 1 | `docs/` nunca é versionado pelo git — todo o histórico de PLAN, briefs e relatórios existe só como arquivo local, sem backup pelo git. Sidarta decide se isso deve mudar (mudaria o que `scripts/commitar.sh` e `scripts/agente_entregar.sh` consideram parte do commit) | decisão | degrada |
