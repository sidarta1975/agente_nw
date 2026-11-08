# Proposta de skill para o agente_nw — menos token, menos terminal, mesma regra

**Data:** 2026-10-24 · **Tipo:** relatório com proposta, nada aplicado · **Repositório:** `/Users/sidarta48/github/agente_nw`
**Base:** medição feita hoje no repositório (tamanhos, scripts, numeração, `git log`), o `AGENTS.md` vigente lido inteiro, a avaliação de skills de 23/10 (doc 051) e a proposta de evolução de 24/10 (doc 052).

---

## 1. Resumo em cinco linhas

1. O trabalho no Claude Code vira **duas skills curtas** (`/iniciar` e `/fechar`), **quatro travas automáticas (hooks)** e **seis scripts**. A regra não muda: quem testa, commita na `main` e decide é você.
2. O maior ganho não é a skill. É **parar de ler cerca de 100 mil caracteres antes de cada brief**. Isso dá ~20 mil tokens a menos por brief.
3. O copia-e-cola some. Você digita **uma palavra na própria janela do Claude Code** (`entregar`, `testar`), e o script roda sem acordar o modelo.
4. A worktree passa a ser **uma por conjunto coerente** de briefs (ex.: tudo da redação da mensagem), nunca por arquivo ou ação.
5. Ficam três decisões suas (seção 9), cada uma com recomendação.

---

## 2. O que foi medido hoje

| Item | Medida | Consequência |
|---|---|---|
| Leitura obrigatória antes de cada brief (AGENTS → PLANO → ARQUITETURA → PLAN) | 13.627 + 11.902 + 17.316 + 57.951 = **100.796 caracteres** (~25 a 29 mil tokens) | Custo fixo de todo brief, antes de abrir o próprio brief |
| `docs/PLAN.md` | 57.951 caracteres; a **última entrada tem 677** | Lê-se o diário inteiro para usar o último parágrafo |
| `AGENTS.md` | §2 estrutura (2.712) + §3 stack (3.110) = 43% do arquivo | Material de consulta, não de procedimento |
| `CLAUDE.md` | não existe | O Claude Code carrega sozinho o `CLAUDE.md`, não o `AGENTS.md`; hoje a leitura do AGENTS depende de o brief mandar |
| `.claude/` | vazio; sem `settings.json` | Cada leitura pede permissão; nenhuma trava automática |
| `scripts/commitar.sh` | já existe: add arquivo por arquivo, pergunta S/n, commit, sem push | Metade do "entregar" já está pronta; falta ler a lista de um arquivo em vez da linha de comando |
| `scripts/verificar.sh` | ruff + format + mypy + pytest, saída inteira na tela | Quando falha, você cola milhares de tokens de erro |
| Numeração | **051 e 052 repetidos**: no disco, 051 = avaliação de skills; no Projeto, 051 = unificação do pedido. 052 = proposta (disco) e auditoria (só no Projeto) | Falta uma fonte única de número |
| Trabalho dos comentários do usuário | ainda sem commit na `main` (16 arquivos) | Precisa ser commitado antes de qualquer worktree |

---

## 3. Correções ao roteiro relatado para este projeto

O relato dos seis repositórios acerta o quadro geral. Para o agente_nw, corrigir:

- **Existe sessão de planejamento**: é o Projeto no Claude, onde os briefs nascem. O AGENTS só não a descreve.
- **A ordem de leitura inclui o `docs/PLAN.md`.** Ele é o equivalente do CONTEXT dos outros repositórios e precisa estar atualizado para o brief ser certificado.
- **"Trabalhar em cópia" é cópia do banco** (`copiar-banco`), não do código. O código vai direto na `main`, sem branch nem worktree. Não há isolamento de código.
- **Pendência** também é o que exige a sua máquina ou presença (login, pessoa real, limiar), não só decisão de produto.
- **Existe a separação "ferramenta × dado real"**: banco real só com autorização sua.
- **Teste direcionado também é proibido aqui.**
- Faltavam: o executor **deve** rodar o que estiver ao alcance fora da suíte e colar a saída; "isso funcionava antes?" antes de diagnosticar; migração numerada; `git status` antes de `add`.

---

## 4. As três peças, em linguagem simples

| Peça | O que é | Quanto custa | Para que serve aqui |
|---|---|---|---|
| **Skill** | Arquivo de instruções que só entra na conversa quando você chama (`/iniciar`, `/fechar`) | Uma linha de descrição sempre carregada; o corpo só quando chamado | O passo a passo de início e fim de brief |
| **Hook** | Trava automática que o Claude Code roda antes ou depois de cada ação, sem passar pelo modelo | Zero quando passa; só a recusa chega ao modelo | Regras que não podem falhar nunca. Numa skill elas falhariam, porque a skill pode não ser chamada |
| **Script** | Comando comum do terminal | O modelo não lê o código, só a saída (uma ou duas linhas) | Tudo que é mecânico: foto do `git status`, conferência de escopo, lista do commit, gate |

Regra de projeto: **regra vai para hook, roteiro vai para skill, trabalho mecânico vai para script, e o AGENTS fica com o que exige julgamento.**

---

## 5. As skills

Ficam em `.claude/skills/` deste repositório. As duas são de chamada manual (`disable-model-invocation: true`): só rodam quando a sessão ou você as chama, nunca por iniciativa do modelo.

### 5.1 `/iniciar <número do brief>` (~1,5 mil caracteres)

O corpo da skill começa rodando `scripts/agente/iniciar.sh <número>`. O script faz, sem o modelo:
1. Confere que o brief existe em `docs/briefs/` e lê o cabeçalho (`Conjunto`, `Arquivos-alvo`, `Seções a ler`).
2. Confirma que a sessão está na worktree do conjunto (seção 7) e avisa se não estiver.
3. Tira a **foto do `git status`** e grava em `.claude/estado/foto_<número>.txt`. É contra ela que o fechamento confere o escopo.
4. Imprime o próximo número de migração livre.
5. Imprime **só a última entrada do `PLAN.md`** e **só as seções do PLANO e da ARQUITETURA que o brief citar**.

Depois disso, a skill manda o modelo ler o brief e o código existente da área afetada. Mais nada.

### 5.2 `/fechar` (~1,5 mil caracteres)

Roda `scripts/agente/fechar.sh <número>`, que faz, sem o modelo:
1. Compara o estado atual com a foto. Arquivo alterado fora dos `Arquivos-alvo` do brief aparece como **falha de escopo** e o fechamento para.
2. Gera a **parte mecânica do relatório final** do AGENTS: criados, alterados, preservados, comandos rodados.
3. Grava o **manifesto do commit** (`.claude/estado/manifesto.txt`): a mensagem e a lista de arquivos, que o `entregar` vai ler.
4. Se a decisão 3 da seção 9 for "sim", commita no ramo da worktree. Esse commit nunca vai para a `main`.

O modelo escreve só o que exige julgamento: as **pendências** e a **entrada nova do `PLAN.md`** (3 a 5 linhas).

### 5.3 Modelo de brief (não é skill; é um arquivo `docs/briefs/_modelo.md`)

Para os scripts lerem o brief sem ajuda do modelo, o cabeçalho passa a ter campos fixos:

```
**Conjunto:** redacao_da_mensagem
**Arquivos-alvo:** agente_nw/nucleo/redacao.py, tests/test_x.py
**Seções a ler:** ARQUITETURA §4; PLANO §2
**Modelo:** Sonnet
```

O resto do brief segue como hoje (objetivo, decisões, escopo, testes, fora de escopo, passos, aceite). A sessão de planejamento pega o número com `scripts/agente/proximo_numero.sh` e grava o brief **também no disco**, em `docs/briefs/`. Isso acaba com a colisão de números, porque disco e Projeto passam a seguir uma sequência só.

---

## 6. Os hooks

Ficam em `.claude/settings.json`. Todos são comandos de terminal, nenhum chama o modelo. Todos ficam em silêncio quando passam.

| Quando dispara | O que faz |
|---|---|
| **Antes de cada comando do modelo** | Recusa: git de escrita (`add`, `commit`, `merge`, `push`, `rebase`, `reset`, `checkout .`, `restore`, `clean`, `stash`, `branch -D`, `worktree remove`); a suíte (`pytest`, `mypy`, `ruff format`, `verificar.sh`, `entregar.sh`); qualquer comando que cite o banco real (`dados/agente.db` da pasta principal). Exceção única: `scripts/agente/fechar.sh` pode commitar **no ramo da worktree**, se a decisão 3 for "sim". |
| **Depois de cada edição de `.py`** | Roda `ruff check` só no arquivo editado. Se a decisão 2 for "não", este hook não entra. |
| **Quando você digita `entregar`** | Roda `scripts/agente/entregar.sh` e não deixa a mensagem chegar ao modelo. Você vê o resultado, e o modelo não gasta nada. |
| **Quando você digita `testar`** | Roda `scripts/agente/testar.sh`, só os testes do brief ativo. Também não acorda o modelo. |

Não entra hook de fim de resposta (`Stop`): ele dispara a cada resposta, não só no fim do brief. A conferência de escopo fica no `/fechar`.

**Alternativa ao gatilho por palavra:** digitar `!scripts/agente/entregar.sh`. O `!` manda o comando direto para o terminal, sem o modelo. A diferença é que a saída entra na conversa. Com o script imprimindo uma linha só, o custo é desprezível.

---

## 7. Worktree por conjunto coerente

**Conjunto** é um grupo de briefs que mexe nas mesmas peças e só faz sentido testado junto. Por exemplo, "redação da mensagem" reúne a mensagem base, os comentários do usuário e o molde por contexto. O nome do conjunto vem do cabeçalho do brief, escrito pela sessão de planejamento. O modelo não decide.

**Ciclo:**
1. **Abrir o conjunto.** Você digita `abrir redacao_da_mensagem`, e o script cria `../agente_nw-redacao_da_mensagem` com um ramo próprio. Uma vez por conjunto, você abre a sessão do Claude Code nessa pasta. É o único passo manual que sobra, e acontece por conjunto, não por brief.
2. **Cada brief do conjunto:** `/iniciar` → trabalho → `/fechar`, sempre dentro dela.
3. **Fechar o conjunto.** `entregar` faz o gate, o merge na `main` e apaga a pasta.

**Quatro armadilhas deste repositório, que o script de abertura resolve.** Sem isso, a worktree engana em vez de isolar.
1. **Ambiente Python.** O `.venv` atual foi instalado em modo editável apontando para a pasta principal. Um teste rodado dentro da worktree com ele testaria o código da `main` e passaria sem provar nada. **Solução:** a worktree ganha um `.venv` próprio, criado com `uv`, o que leva segundos.
2. **`config/local.yaml` e `dados/` estão fora do git.** O script copia o `local.yaml` e roda `copiar-banco` para o `dados/` da worktree. Nunca um atalho para o banco real.
3. **Portas fixas** do console (8765) e da ponte (8766): o programa sobe de uma pasta por vez.
4. **O trabalho dos comentários do usuário precisa estar commitado** na `main` antes da primeira worktree. Senão ela nasce sem esse código.

O Claude Code tem um recurso próprio de worktree. Ele não resolve as armadilhas 1 e 2, então o script continua necessário.

---

## 8. Ganho estimado por brief

Estimativa: caracteres medidos divididos por 4. A confirmação vem do consumo real das cinco primeiras tarefas depois da mudança.

| O quê | Hoje | Com a proposta |
|---|---|---|
| Leitura antes do brief | ~25 a 29 mil tokens | ~5 a 8 mil (AGENTS inteiro, última entrada do PLAN, seções citadas) |
| Relatório final escrito pelo modelo | ~1 a 2 mil tokens de saída | ~300 a 500 (só pendências e PLAN) |
| Gate que falha | você cola a saída inteira (milhares) | o modelo lê o resumo (~200 a 500) |
| Commit, teste, merge | você copia e cola comandos longos | uma palavra digitada; zero token |
| Permissão por comando de leitura | um pedido por comando | lista aprovada uma vez |
| Custo fixo das skills e hooks | — | ~100 tokens de descrição; hooks, zero |

Total esperado: **algo perto de 20 mil tokens a menos por brief**, e **nenhum comando copiado do Claude Code para o terminal**.

---

## 9. Decisões que são suas

| # | Decisão | O que muda no AGENTS | Recomendação |
|---|---|---|---|
| 1 | **Leitura reduzida:** AGENTS inteiro, só a última entrada do PLAN.md, só as seções do PLANO e da ARQUITETURA citadas no brief | §1 (ordem de leitura) | **Sim.** É a maior economia de todas. O brief continua podendo mandar ler mais quando precisar. |
| 2 | **Lint automático só do arquivo editado**, logo após a edição, silencioso quando passa | §6 (hoje proíbe ruff na sessão) | **Sim.** Pega o erro na hora, não no seu gate. mypy e pytest continuam só com você. |
| 3 | **Commit de cada brief no ramo da worktree pelo `/fechar`**, sem você; o merge na `main` continua só seu | §5 passa de "o executor nunca commita" para "o executor nunca toca a `main`" | **Sim.** Esse commit é desfeito com facilidade e fica fora da `main`. Você digita `entregar` uma vez por conjunto, não uma vez por brief. |

Se a decisão 3 for "não", o fechamento de cada brief vira mais uma palavra sua (`fechar`), também com custo zero de token.

---

## 10. O que vem dos outros repositórios, e o que não vem

**Entra:**
- Conferência de escopo no fechamento (lex_hub, sergio, trf6, cervello), aqui contra a foto, não contra a `main`.
- Número de brief por script (lex_hub, sergio).
- Teste rápido rodado por você (trf6).
- "Sem saída colada não se escreve que passou" (trf6).
- Modelo indicado no brief (trf6).
- Brief curto para mudança pequena (lex_hub).
- Não abrir o banco sem ordem explícita (cervello), como hook.

**Não entra:**
- Worktree por frente: aqui é por conjunto.
- Branch por brief, trava do checkout, reserva de porta, leitura do contexto de várias frentes, versão do AGENTS declarada no início. Tudo isso resolve trabalho paralelo, e aqui há uma frente e um desenvolvedor.
- Plugin `hookify`: quatro hooks sempre ligados, ~176 KB, para o que um script de 30 linhas faz.

**Lição do sergio:** o `CLAUDE.md` novo deste repositório tem uma linha só (`@AGENTS.md`, que faz o Claude Code carregar o AGENTS sozinho). Ele nunca repete nem contradiz uma regra.

---

## 11. Ordem de implantação

O primeiro passo é seu: commitar o trabalho dos comentários do usuário que está na `main`.

Os três briefs a seguir formam **um conjunto só** ("ferramentas de trabalho") e são entregues de uma vez:

| Ordem | Brief | Arquivos-alvo prováveis | Ganho imediato |
|---|---|---|---|
| 1 | Travas e entrega | `.claude/settings.json` (hooks), `scripts/agente/entregar.sh`, `scripts/agente/testar.sh`, `scripts/verificar.sh` (resumo em `logs/`), `scripts/commitar.sh` (ler o manifesto) | Fim do copia-e-cola e da saída colada; regra de git vira trava |
| 2 | Skills e modelo de brief | `.claude/skills/iniciar/`, `.claude/skills/fechar/`, `scripts/agente/iniciar.sh`, `fechar.sh`, `proximo_numero.sh`, `docs/briefs/_modelo.md`, `CLAUDE.md`, `AGENTS.md` (§1, §5, §6, conforme as decisões) | Fim da leitura de 100 mil caracteres; relatório mecânico; numeração única |
| 3 | Worktree por conjunto | `scripts/agente/abrir.sh`, ajuste no `entregar.sh` (merge e remoção) | Isolamento de verdade, com as quatro armadilhas resolvidas |

O número desses briefs sai do script de numeração do brief 2. Até ele existir, o próximo número livre conferido hoje no disco e no Projeto é o **054** (este relatório usa o 053).

---

## 12. Lacunas

| Lacuna | Impacto | Esforço |
|---|---|---|
| O bloqueio de mensagem pelo hook de prompt (gatilho `entregar`) e a execução de comando dentro da skill precisam ser confirmados na versão do Claude Code instalada no Pro | degrada (se falhar, fica o `!scripts/...`, quase tão barato) | baixo: um teste |
| Tempo máximo do hook precisa caber a suíte inteira | degrada | baixo: um número na configuração |
| A extensão do Chrome (JavaScript) fica fora do lint e do teste | nice | médio, brief próprio |
| A sessão de planejamento (Claude App) não carrega as skills do repositório; usa só o script de numeração e o modelo de brief | nice | — |
| As colisões já ocorridas (051, 052) ficam como estão, sem renomear nada já entregue; a regra vale daqui para frente | nice | — |
