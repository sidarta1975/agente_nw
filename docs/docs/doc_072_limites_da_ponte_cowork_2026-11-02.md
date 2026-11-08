# Doc 072 — Limites da ponte do Cowork com o computador, no AGENTS.md

**Brief:** `docs/briefs/brief_072_limites_da_ponte_cowork_2026-11-02.md`
**Data:** 2026-11-02

## O que foi feito

Acrescentada a seção **§11 "Cowork: o que a ponte com o computador pode e não pode fazer"** ao fim do
`AGENTS.md`, depois da §10. A numeração 11 está livre: as seções do arquivo iam de §1 a §10 e nenhuma
outra entrou entre a 10 e esta.

Os quatro motivos apurados foram preservados, cada um com o detalhe técnico que evita reabrir a
investigação: binários do `.venv` em Mach-O arm64 que a VM Linux não executa ("Exec format error");
dependência de `pyobjc-framework-Contacts`, que não existe para Linux, então recriar o ambiente na VM não
resolveria; ausência de credenciais do GitHub na ponte (sem chave SSH, sem `gh auth`, sem credential
helper); e o bloqueio de digitação em terminal/IDE do controle de tela, que é por categoria e não se
destrava com permissão.

## Conferência de coerência com as seções existentes (item 4 do brief)

- **§5 (Git)** — "O executor commita e faz push ao fim de cada brief, exclusivamente por
  `scripts/agente_entregar.sh`". A §11 diz que o Cowork não commita; não há conflito, porque o Cowork não
  é o executor. As duas seções apontam para o mesmo lugar: quem commita é o executor, pelo script.
- **§10 (Briefs e numeração)** — "Todo brief escrito no Projeto é gravado em `docs/briefs/` antes de ser
  executado" e "Todo brief é executado com `/executar <NNN>`". A §11 reforça exatamente essa divisão
  ("o Cowork prepara o brief; Sidarta executa"), sem alterá-la.
- **§8 (Relatório final obrigatório)** — "Sem saída de comando colada no relatório, não se escreve que
  algo passou". A §11 cita a §8 e a reforça para o caso do Cowork, que não tem como rodar o gate.

Nenhuma contradição encontrada.

## Arquivos alterados

- `AGENTS.md` — nova seção §11, ao fim do arquivo; nenhuma seção existente foi reescrita.

## Arquivos preservados literalmente

- Todo o resto do `AGENTS.md` (§1 a §10, incluindo o bloco `## RELATÓRIO FINAL`).
- Nenhum arquivo de código tocado — o gate roda só para confirmar isso.
- `.claude/hooks/guarda_comando.py` e qualquer mecanismo de execução, fora de escopo (item 5).

## RELATÓRIO FINAL

- **Brief executado:** 072 — documentar os limites da ponte do Cowork no `AGENTS.md`.
- **Arquivos criados:** `docs/docs/doc_072_limites_da_ponte_cowork_2026-11-02.md`,
  `logs/commit_072.txt`, `logs/arquivos_072.txt`.
- **Arquivos alterados (resumo em uma linha cada):**
  - `AGENTS.md` — nova §11 com o que a ponte do Cowork pode e não pode fazer, e por quê.
- **Arquivos preservados literalmente na área afetada:** §1 a §10 do `AGENTS.md`; nenhum código.
- **Script de verificação (o gate, rodado pelo `scripts/agente_entregar.sh`; saída colada):** ver
  "Saída do gate" abaixo.
- **Comandos executados:**
  - `scripts/agente_entregar.sh 072`
- **Manifesto do commit (`logs/arquivos_072.txt` e `logs/commit_072.txt`):** ver abaixo.
- **Pendências e decisões que ficaram abertas:** nenhuma.
- **Resumo, Doing, Backlog e Done do `docs/PLAN.md` atualizados:** sim.

## Saída do gate

```
$ scripts/agente_entregar.sh 072
manifesto 072: 1 arquivo(s)
ruff check: ok
ruff format: ok
mypy: ok
pytest: ok (911 passed, 5 deselected in 32.57s)
sem lacunas
✓ brief 072: commit f6ed443, enviado ao GitHub
```

## Manifesto

`logs/arquivos_072.txt`:

```
AGENTS.md
```

`logs/commit_072.txt`:

```
docs(agents): secao 11 com o que a ponte do Cowork pode e nao pode fazer (brief 072)
```

## Lacunas

Sem lacunas.
