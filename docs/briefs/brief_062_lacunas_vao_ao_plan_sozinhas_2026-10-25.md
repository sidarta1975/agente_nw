# Brief 062 — As lacunas de cada relatório vão para o PLAN sozinhas

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Conjunto:** nenhum (brief isolado, direto na `main`)
**Arquivos-alvo:** `scripts/agente_lacunas.py` (novo), `scripts/agente_entregar.sh`, `.claude/skills/executar/SKILL.md`, `AGENTS.md` (§8), `tests/test_agente_lacunas.py` (novo), `docs/PLAN.md`, `docs/docs/doc_062_lacunas_vao_ao_plan_2026-10-25.md`, `logs/commit_062.txt`, `logs/arquivos_062.txt`
**Seções a ler:** AGENTS §8 e §10; `scripts/agente_entregar.sh` inteiro; `docs/PLAN.md` até `## Dívidas conhecidas`; as seções de lacunas, limites e pendências dos relatórios 055 a 059 em `docs/docs/`
**Modelo:** Sonnet
**Teste de aceite:** `tests/test_agente_lacunas.py`
**Depende de:** nada
**Data:** 2026-10-25

---

## 1. Objetivo em uma frase

Ao entregar um brief, o `agente_entregar.sh` copia sozinho as lacunas e pendências do relatório para o lugar certo do `docs/PLAN.md`. Nada que o executor deixou para Sidarta fica perdido dentro de um relatório.

---

## 2. Por quê

Os relatórios 055 a 059 registram lacunas e decisões em seções com nomes diferentes: "Lacunas", "Fora da letra do brief", "Interpretações e limites", "Pendência de Sidarta", "Diferenças de comportamento". Quem passa isso para o PLAN é o executor, à mão, quando lembra. O 059 deixou decisões só no relatório. O pandora já resolveu isso com um script no fechamento (pandora_006).

---

## 3. Decisões

**3.1. Formato fixo no relatório.** Todo relatório de brief termina com uma única seção:

```
## Lacunas

| # | Lacuna | Destino | Impacto |
|---|---|---|---|
| 1 | <uma frase> | backlog / pendência / dívida / decisão / nenhum | bloqueia / degrada / nice |
```

Destino:
- **backlog**: trabalho a fazer depois; vira linha em `## Backlog`.
- **pendência**: exige a máquina ou a presença de Sidarta (teste real, login, aprovação); vira linha em `## Pendências de Sidarta`.
- **dívida**: defeito conhecido, sem brief; vira item em `## Dívidas conhecidas`.
- **decisão**: escolha de produto que o executor não podia tomar, ou interpretação que tomou e Sidarta precisa conhecer; vira linha em `## Decisões em aberto`.
- **nenhum**: registro só no relatório.

Sem lacuna nenhuma, a seção diz "Sem lacunas." Seções soltas como "Fora da letra do brief" deixam de existir: o conteúdo entra como linha da tabela.

**3.2. `scripts/agente_lacunas.py <NNN>`.** Python, só biblioteca padrão:
- Lê `docs/docs/doc_<NNN>_*.md`, acha a tabela de `## Lacunas` e acrescenta cada linha com destino diferente de `nenhum` ao fim da seção certa do PLAN.
- Formato da linha no PLAN: `- [<NNN>-<#>] <lacuna> · <impacto> · <data>`.
- **Não duplica:** se `[<NNN>-<#>]` já existe no PLAN, pula. Rodar duas vezes dá o mesmo PLAN.
- Não altera nenhuma outra linha do PLAN.
- Imprime uma linha só: `lacunas do 062: 2 no Backlog, 1 em Pendências, 0 em Dívidas, 0 em Decisões`, ou `sem lacunas`.
- Relatório sem a seção, ou com a tabela fora do formato, também resulta numa linha só, `relatório sem tabela de lacunas no formato`. Não para a entrega, porque o commit e o push já aconteceram.

**3.3. `agente_entregar.sh`.** Depois do push e antes da linha final, roda `scripts/agente_lacunas.py <NNN>` e acrescenta a linha dele à saída. O PLAN está fora do git, então isso não muda o commit.

**3.4. Skill `/executar` e AGENTS §8.** As duas passam a dizer que o relatório termina com a tabela da 3.1 e que o executor não copia lacunas para o PLAN à mão.

**3.5. Uma vez, agora: os relatórios 055 a 059.** O executor lê as seções de lacunas, limites, pendências e diferenças desses cinco relatórios e reescreve cada uma no formato 3.1, acrescentando a tabela ao fim do relatório. O texto antigo fica onde está, e é a única alteração permitida nesses arquivos. Antes de classificar, o executor confere o PLAN atual: o que já estiver lá recebe destino `nenhum`. Depois roda `agente_lacunas.py` para cada um. No relatório deste brief, lista o que entrou em cada seção do PLAN.

---

## 4. Testes (antes do código)

`tests/test_agente_lacunas.py`, com um PLAN e um relatório temporários (`tmp_path`):
- uma lacuna de cada destino → cada uma na seção certa;
- rodar duas vezes → PLAN idêntico;
- destino `nenhum` → nada muda;
- relatório sem tabela → uma linha de aviso e PLAN intacto;
- as outras linhas do PLAN não mudam (comparação byte a byte fora das linhas acrescentadas).

---

## 5. Fora de escopo

Mover lacunas antigas, anteriores ao 055; remover do PLAN lacunas resolvidas, que continua sendo feito por quem fecha o brief que as resolve.

---

## 6. Passos e aceite

Executar com `/executar 062`. Aceite: testes verdes, gate verde, commit e push pelo executor. A entrega deste próprio brief já termina com a linha do `agente_lacunas.py`.

Resposta final: "Nada para você.", a não ser que alguma lacuna dos relatórios 055 a 059 tenha ido para Pendências ou Decisões. Nesse caso, listá-las em uma linha cada.
