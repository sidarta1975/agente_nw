# DOC 062 — as lacunas de cada relatório vão para o PLAN sozinhas (relatório do brief 062)

## RELATÓRIO FINAL
- Brief executado: 062. Dependência: nenhuma.
- Arquivos criados: `scripts/agente_lacunas.py`, `tests/test_agente_lacunas.py`, este relatório, `logs/commit_062.txt`, `logs/arquivos_062.txt`.
- Arquivos alterados (uma linha cada):
  - `scripts/agente_entregar.sh`: depois do push e do manifesto, roda `agente_lacunas.py <NNN>` e acrescenta a linha dele à saída (nunca derruba a entrega).
  - `.claude/skills/executar/SKILL.md`: o relatório termina com `## Lacunas` em tabela; o executor não copia lacunas à mão.
  - `AGENTS.md` §8: a mesma regra, em uma frase.
  - `tests/test_agente_entregar.py`: **fora da lista do brief**; o repositório de teste ganhou `agente_lacunas.py`, um PLAN e um relatório, e um caso confere a linha de lacunas e a linha no PLAN.
  - `docs/PLAN.md` (fora do git): lacunas dos relatórios 055 a 059 (abaixo); Doing; retirada da linha obsoleta "059 · não iniciado" do Backlog.
  - `docs/docs/doc_055` a `doc_059`: acrescentada a tabela `## Lacunas` ao fim; o texto antigo não foi tocado.
- Arquivos preservados literalmente na área afetada: o resto do `agente_entregar.sh`, `verificar.sh`, `commitar.sh`, o resto do PLAN.
- Script de verificação: `scripts/verificar.sh`, pelo `scripts/agente_entregar.sh`.
- Manifesto: `logs/arquivos_062.txt` (6 arquivos), `logs/commit_062.txt`.
- Resumo, Doing, Backlog e Done do `docs/PLAN.md` atualizados: sim.

## Como funciona

`python3 scripts/agente_lacunas.py <NNN> [--raiz pasta] [--data AAAA-MM-DD]` lê a última seção `## Lacunas` de `docs/docs/doc_<NNN>_*.md`. Cada linha com destino diferente de `nenhum` entra no fim da seção do PLAN (backlog, pendência → Pendências de Sidarta, dívida, decisão → Decisões em aberto) como `- [<NNN>-<#>] <lacuna> · <impacto> · <data>`. A marca `[<NNN>-<#>]` impede duplicar; rodar duas vezes dá o mesmo PLAN. Imprime uma linha: `lacunas do 062: …`, `sem lacunas` ou `relatório sem tabela de lacunas no formato`. Sai sempre com 0.

## O que entrou no PLAN dos relatórios 055 a 059 (3.5)

Antes de classificar conferi o PLAN: o que já estava resolvido ou registrado recebeu destino `nenhum`. Saída:

```
lacunas do 055: 0 no Backlog, 0 em Pendências, 2 em Dívidas, 1 em Decisões
lacunas do 056: 0 no Backlog, 0 em Pendências, 0 em Dívidas, 0 em Decisões
lacunas do 057: 0 no Backlog, 0 em Pendências, 1 em Dívidas, 1 em Decisões
lacunas do 058: 0 no Backlog, 0 em Pendências, 1 em Dívidas, 0 em Decisões
lacunas do 059: 0 no Backlog, 0 em Pendências, 1 em Dívidas, 2 em Decisões
```

- **Dívidas conhecidas:** [055-1] ARQUITETURA §1, §3, §4, §5 e §7 desatualizadas; [055-2] PLANO §1 a §5 desatualizado; [057-5] limites da trava (comandos montados dinamicamente passam); [058-3] `docs/briefs/_modelo.md` passo 6 diz que Sidarta roda; [059-2] a comparação de nomes da divergência continua em `pedido.processar`.
- **Decisões em aberto:** [055-6] revisão do que foi movido das Dívidas ao histórico; [057-3] AGENTS §8 cita `listas ver` e a trava bloqueia `listas`; [059-1] leitura de `--preparar` e a mudança do homônimo no terminal; [059-3] "Sim" à divergência no console não faz a curadoria das redes.
- **Pendências de Sidarta e Backlog:** nenhuma linha nova (o teste real do 059 já estava em Pendências).
- **Nenhum:** as demais; entre elas, as diferenças 1 a 8 do 056 (1, 2, 6 e 7 resolvidas no 059; 3, 4, 5 e 8 mantidas por decisão de Sidarta).

Decisões do executor: no 055 fundi os itens 1 a 4 do relatório (todos sobre a ARQUITETURA) numa só linha de dívida e deixei o PLANO em outra, porque um mesmo brief de revisão dos documentos resolve cada grupo. No 056 resumi as oito diferenças em três linhas `nenhum`.

## Conferências (saída)

```
$ pytest tests/test_agente_lacunas.py tests/test_agente_entregar.py -q
16 passed in 2.89s     (antes do ajuste de formatação do último teste: 10 passed no arquivo de lacunas)

$ ruff check / ruff format -> ok (rodados no gate da entrega)
```

## Lacunas

Sem lacunas.
