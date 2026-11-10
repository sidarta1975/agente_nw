# Relatório 085 — Atestado de viabilidade da execução de briefs em série

**Veredito: VIÁVEL COM AJUSTES** — o método funciona e eu provei as três peças que importam (o Claude Code roda `/executar` sozinho, escreve arquivos sozinho e o `agente_entregar.sh` tem código de saída confiável), mas a série 080→083 **não pode rodar hoje**: falta o script que encadeia (`scripts/executar_serie.sh`, prometido no AGENTS §10 para o brief 086, que ainda não existe), a árvore de trabalho está suja de um jeito que o próprio gate recusa, e o sinal de sucesso **não pode** ser o código de saída do Claude Code.

Só investigação. Nenhum brief executado, nenhum arquivo de código alterado, nenhum git de escrita, nenhum acesso ao banco real nem a rede social. Gasto desta investigação: três chamadas curtas do Claude Code em Haiku, US$ 0,019 somadas (preço de tabela).

**Este relatório não repete o 084.** `docs/docs/doc_084_viabilidade_execucao_em_serie_2026-11-08.md` (hoje, 12:32) já fez a investigação completa; eu o reconferi, refiz as provas que importavam, **corrigi uma conclusão dele** e registrei o que mudou nas três horas seguintes. Onde este relatório não diz nada, o 084 vale.

Convenção: "não conferido" = não consegui provar sem executar um brief de verdade.

---

## 1. O que mudou desde o 084 (três horas atrás)

| O que | Estado no 084 (12:32) | Estado agora (15:30) | Prova |
|---|---|---|---|
| Documentos canônicos | 8 rascunhos de alteração, nada aplicado | **Aplicados**: AGENTS §4 (texto por inteiro) e §10 (execução em série, ordem em série), `SKILL.md` (manifesto com relatório + PLAN + brief, linha `PAROU:`, regra da série), `_modelo.md` (campo `Ordem em série`, pergunta do texto), `ARQUITETURA.md` (§11 corrigida, §13 nova), `PLAN.md` | `git diff --stat` → 5 arquivos, 26 inserções; `git diff AGENTS.md` mostra as duas regras novas |
| Bateria / tampa (B4, "Alta hoje") | 13%, descarregando | **resolvido**: `Now drawing from 'AC Power'`, 100% | `pmset -g batt` |
| Árvore de trabalho | 4 briefs sem commit | **pior**: 5 arquivos modificados (os canônicos acima) + 6 sem commit (4 briefs, `doc_084`, este `doc_085`) | `git status --short` |
| `scripts/executar_serie.sh`, `.claude/serie.settings.json`, `logs/serie/` | não existiam | **continuam não existindo**; e o brief 086, que o AGENTS §10 cita como quem os cria, não está escrito | `ls` dos três caminhos; `ls docs/briefs/ \| grep 08[4-9]` → nenhum |
| Permissão de escrita sem acompanhamento (B3, "Alta") | avaliada como barreira alta | **corrigida por teste**: a escrita funciona (ver 2.3) | teste 3 abaixo |

---

## 2. As provas que rodei agora

Versão: `claude --version` → `2.1.318 (Claude Code)`. As opções que a série usa existem nesta versão (`claude --help`): `-p/--print`, `--permission-mode`, `--permission-prompts <target>` (com o valor `none`: "anything that would prompt is denied automatically"), `--allowedTools`/`--disallowedTools`, `--model`, `--effort <level>`, `--max-turns`, `--max-budget-usd`, `--output-format json|stream-json`, `--settings <arquivo>`, `--fallback-model`.

A trava do projeto está ligada como `PreToolUse` com matcher `Bash` (`.claude/settings.json`, chave `hooks`), e o lint como `PostToolUse` em `Edit|Write|MultiEdit`. As três chamadas abaixo rodaram com esses dois hooks carregados.

### 2.1. Teste 1 — leitura, sem ninguém aprovando nada

```
$ claude -p --model haiku --max-turns 4 --permission-prompts none --output-format json \
  "Leia config/limiares.yaml e responda com uma linha só: o valor da chave
   extensao.maximo_caracteres_pagina. Não altere nada."

is_error: False
subtype: success
num_turns: 2
custo_usd: 0.00679094
resposta: `extensao.maximo_caracteres_pagina` = **200000**
```

O valor está certo (`config/limiares.yaml:59`). **O modo sem acompanhamento funciona neste repositório, com a trava e as permissões de hoje.**

### 2.2. Teste 2 — uma parada do `/executar` sai com código 0 (a descoberta que manda no desenho)

```
$ claude -p --model haiku --max-turns 6 --permission-prompts none --output-format json "/executar 999"
exit_code_do_claude=0
is_error: False | subtype: success | num_turns: 5 | custo: 0.0084
resposta: PAROU: o brief 999 não existe. Não há `docs/briefs/brief_999_*.md` no disco
nem no histórico git do repositório... Nenhum código foi alterado e nada foi commitado.
```

A skill se comportou exatamente como manda o `SKILL.md` (passo 1: "Se não existir no disco, pare e diga isso") — e o processo saiu com **0**, `is_error: false`, `subtype: success`. Para o sistema operacional, "parei sem fazer nada" é indistinguível de "entreguei". Confirma o B2 do 084, por teste independente.

**Consequência para a série:** o código de saída do `claude -p` é inútil como sinal de sucesso. O que vale é a prova da entrega (item 4.2).

### 2.3. Teste 3 — escrita sem ninguém aprovando: funciona (corrige o 084)

```
$ claude -p --model haiku --max-turns 6 --permission-prompts none --output-format json \
  "Crie o arquivo logs/teste_permissao_serie.txt com a palavra ok dentro..."
exit=0 | is_error: False | subtype: success | turns: 2 | custo: 0.0059
resposta: Sim, consegui. O arquivo logs/teste_permissao_serie.txt foi criado...

$ ls -la logs/teste_permissao_serie.txt
-rw-r--r--  1 sidarta48  staff  3  8 nov 15:29 logs/teste_permissao_serie.txt
$ cat logs/teste_permissao_serie.txt
ok
```

(Arquivo apagado em seguida; `logs/` é ignorado pelo git.)

O 084 concluiu, na barreira B3, que `Edit`/`Write` fora do `allow` do projeto seriam "negados em silêncio" e que a série giraria até o `--max-turns`. **Isso está errado**: a lista `permissions.allow` governa o que *pergunta*, e o modo padrão do usuário (`~/.claude/settings.json`: `"defaultMode": "auto"`) aprova a escrita sozinho; `--permission-prompts none` só nega o que **iria** perguntar. Logo, um brief consegue escrever código e teste sem ninguém por perto, com a configuração de hoje, sem arquivo de permissões novo.

O que sobra dessa barreira, menor e real: **comandos de terminal fora do `allow`**. O `allow` cobre `ls, cat, head, tail, wc, grep, rg, find, git status/diff/log/show, pytest, .venv/bin/{pytest,mypy,ruff}, scripts/verificar.sh, scripts/agente_entregar.sh`. Não cobre, por exemplo, `mkdir`, `cp`, `mv`, `printf`, `sed`, `python3` solto — um brief que precise de um deles numa execução `--permission-prompts none` leva uma negativa silenciosa. Remédio no item 9.

### 2.4. O `agente_entregar.sh` devolve código de saída confiável — sim

| Caminho | Linha | Código |
|---|---|---|
| `parar()` (manifesto ausente, caminho fora do repositório, arquivo fora da lista) | `scripts/agente_entregar.sh:30-32` | `exit 1` |
| Gate (`scripts/verificar.sh`) falhou | `:109` | `parar` → 1 |
| Commit falhou | `:114` | `parar` → 1 |
| Push falhou (commit local já existe) | `:122-132` | `exit 1`, com a frase `✗ ... falhou só o envio. Rode: !git push` |
| Tudo certo | `:136` | chega ao fim → 0, com `✓ brief NNN: commit <hash>, enviado ao GitHub` |
| `--simular` | `:102-105` | **`exit 0` sem fazer nada** |

Isto é: 0 só depois de gate verde, commit e push. **A série nunca pode passar `--simular`** — seria um sucesso falso.

### 2.5. Ambiente, agora

| Item | Veredito | Prova |
|---|---|---|
| Energia | **ok** | `pmset -g batt` → `AC Power`, 100% |
| Ollama na porta 11435 | **ok** | `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:11435/api/tags` → `200` |
| Gate precisa do Ollama? | **não** | `pyproject.toml` → `addopts = "-m 'not rede_real and not llm_real'"`; a entrega do 079 rodou `1031 passed, 5 deselected in 26.62s` |
| Suíte demorada | **ok** | 26,6 s por tentativa; 3 tentativas no pior caso = ~80 s por brief |
| Credencial do push | **ok até o Chaveiro travar** | o 084 provou (`gh auth status` logado, `credential.helper = osxkeychain`, `git ls-remote` com `GIT_TERMINAL_PROMPT=0` devolveu o HEAD). Não reconferido aqui; o push de verdade só se prova gravando |
| `origin/main..HEAD` | **0** (nada pendente de envio) | `git rev-list --count origin/main..HEAD` → `0` |
| Outras sessões na mesma árvore | **barreira branda** | `pgrep -fl claude \| wc -l` → **19** processos. Não dá para dizer quantos são deste repositório; o 084 viu 6 às 12:32 |
| Árvore limpa para o `agente_entregar.sh` | **BARREIRA** | `git status --short` → 5 `M` + 6 `??` |

### 2.6. Os quatro briefs

| Brief | Modelo | Esforço | Ordem em série | Depende de | Teste de aceite |
|---|---|---|---|---|---|
| 080 registro de exceções | Sonnet | baixo | antes de 081, 082, 083 | 079 executado (`700a43a`, `e45c9dd`) ✓ | `verificar_auditoria_texto.py` devolve 0 |
| 081 texto do usuário inteiro | Sonnet | médio | livre | 079 ✓ | `tests/test_texto_do_usuario_inteiro.py` |
| 082 medir a janela do modelo | Opus | alto | antes de qualquer brief que suba limite de texto | 079 ✓ | `tests/test_janela_modelo.py` |
| 083 fim da perda silenciosa | Opus | médio | livre | 079 ✓ | `tests/test_coleta_sem_perda_silenciosa.py` |

A ordem pedida (080 → 081 → 082 → 083) satisfaz os quatro campos `Ordem em série`. Os `Arquivos-alvo` não se cruzam: 080 só documentos; 081 `historico/redacao/pedido/candidatos`; 082 `llm.py` e o estimador; 083 `coleta/` e `extensao/`. O único toque comum é o par relatório/`PLAN.md`, que todo brief altera — e é exatamente de onde vem a barreira B1.

---

## 3. Modelo e esforço por brief: dá para respeitar

Cada chamada é um processo próprio, então `--model` e `--effort` vêm do cabeçalho do brief, lidos pelo script antes de chamar:

- `--model sonnet` para 080 e 081, `--model opus` para 082 e 083 (as duas são aliases válidos nesta versão).
- `--effort baixo|médio|alto` → `low|medium|high` (`--effort` aceita `low, medium, high, xhigh, max`).
- Como ler: as duas linhas `**Modelo:**` e `**Esforço:**` do cabeçalho; o campo `Modelo` às vezes traz uma justificativa depois do nome ("Opus — toca o cliente usado pelas 15 tarefas"), então o script pega a **primeira palavra** depois do rótulo.
- Se o cabeçalho não trouxer os campos, o script **para** em vez de escolher por conta própria.

O que se perde se não respeitar: 082 e 083 em Sonnet seriam mais baratos e mais rápidos, mas os dois briefs dizem no próprio cabeçalho por que pedem Opus ("um engano trava o produto inteiro", "um engano aqui perde dado ou quebra a leitura"). Rodar abaixo do pedido é decisão de produto, não de script.

---

## 4. Desenho do executor em série (descrição, não código)

O AGENTS §10 já fixou o procedimento. O que este atestado acrescenta é o detalhe do critério de sucesso e da ordem das conferências.

### 4.1. Antes de começar (uma vez por série, e para tudo se falhar)

1. **Árvore limpa**: `git status --porcelain` vazio. Senão, para e diz o que está sujo (é o estado de hoje).
2. **Nada pendente de envio**: `git rev-list --count origin/main..HEAD` = 0.
3. **Um arquivo por brief**: `docs/briefs/brief_<NNN>_*.md` casa com exatamente um arquivo (hoje `brief_074_*` e `brief_075_*` casam com dois cada — não afeta 080-083).
4. **Ordem**: lê `Ordem em série` de cada brief da lista e recusa lista que fira a regra.
5. **Depende de**: só confere que o campo existe; quem o avalia de verdade é o `/executar` (passo 2 da skill).
6. **Ambiente**: Ollama responde (se algum brief pedir), energia na tomada, `caffeinate -dimsu` em volta de toda a série, trava de instância (um só `executar_serie.sh` por vez) e aviso para fechar outras sessões do projeto.

### 4.2. Por brief, em contexto novo

Chama `claude -p "/executar <NNN>"` com `--model`/`--effort` do cabeçalho, `--permission-prompts none`, `--max-turns` generoso, `--max-budget-usd` por brief, `--output-format json`, e grava a saída crua em `logs/serie/<data>/<NNN>.json`.

Depois, **ignora o código de saída** e confere a entrega (teste 2):

1. `logs/entregue_<NNN>_commit.txt` e `logs/entregue_<NNN>_arquivos.txt` existem (o `agente_entregar.sh` só renomeia o manifesto depois do commit, `:123-124`);
2. o commit mais novo menciona `(brief <NNN>)` ou o número do brief;
3. `git rev-list --count origin/main..HEAD` = 0 (push feito);
4. `git status --porcelain` vazio (nada ficou sujo — ver B1);
5. a primeira das três linhas finais não começa com `PAROU:` (regra nova do `SKILL.md`);
6. `is_error` do JSON é falso **e** `subtype` é `success` (pega estouro de `--max-turns` e de orçamento).

Falhou qualquer uma: **para a série**, não tenta o brief seguinte, escreve `logs/serie/<data>/STATUS.txt` com o brief, o passo e a frase do `PAROU:`, e notifica (item 7).

### 4.3. Ao fim

`STATUS.txt` com uma linha por brief (`080 entregue <hash>`, `081 entregue <hash>`, `082 PAROU: ...`), o custo somado lido dos JSON, e a lista de "Para você" que os relatórios produziram (o 083 tem um: recarregar a extensão no Chrome).

### 4.4. O que o script precisa ter

Leitura do cabeçalho do brief (modelo, esforço, ordem); as seis conferências de pré-voo; o laço com a conferência de entrega de seis itens; `caffeinate`; trava de instância (um arquivo de bloqueio em `logs/serie/`); um log por brief e o `STATUS.txt`; notificação por `osascript`; e nenhuma palavra de git de escrita (o git continua só dentro do `agente_entregar.sh`, AGENTS §5).

---

## 5. Pontos de decisão humana: nunca automáticos

A série para e avisa, sem tentar adivinhar, quando aparecer qualquer um destes:

| O que | Por que | Onde está escrito |
|---|---|---|
| Aprovar exceção ao texto por inteiro (escrever em `docs/EXCECOES_TEXTO_INTEGRAL.md`) | o princípio é do dono; quem audita não absolve | AGENTS §4; brief 079 item 3.1 |
| Qualquer uso do banco real `dados/agente.db` | desenvolvimento é sempre em cópia | AGENTS §6; `deny` do settings; a trava |
| Leitura de rede social, `pedir`, `listas`, `extensao` | "nunca rodam sozinhos" | AGENTS §6 e §7; a trava |
| Decisão de produto que o brief não cobre | o executor não tem latitude criativa | AGENTS §1 |
| Alterar `AGENTS.md`, regra, skill, `settings` ou a trava | salvo se o brief tiver o arquivo como alvo | AGENTS §10 |
| Dois briefs com o mesmo número no disco | `/executar NNN` fica ambíguo | aconteceu com 074/075 |
| Terceira falha do gate | base quebrada não recebe o brief seguinte | AGENTS §8; `SKILL.md` passo 7 |
| Teste com pessoa real / recarregar a extensão no Chrome | exige pessoa | brief 083 §6 |

Como para: a skill já manda começar a primeira das três linhas com `PAROU:` (regra nova do `SKILL.md`); o script lê isso, escreve no `STATUS.txt` e notifica. Nenhum desses casos vira pergunta, porque não há ninguém para responder.

---

## 6. Notificação: o que existe e o que falta

| Peça | Estado | Prova |
|---|---|---|
| `terminal-notifier` | **não instalado** | `which terminal-notifier` → not found |
| `osascript` (notificação do macOS nativa) | **disponível** | `which osascript` → `/usr/bin/osascript` |
| Hook de fim de execução no projeto (`Stop`, `Notification`) | **não existe**: o `.claude/settings.json` só tem `PreToolUse` (trava) e `PostToolUse` (lint) | `settings.json`, chave `hooks` |
| Arquivo de status | **não existe** (`logs/serie/` não existe) | `ls -d logs/serie` → No such file or directory |

Falta, então: o `STATUS.txt` e uma linha de `osascript -e 'display notification ...'` no fim do script da série (sucesso e falha). Como extra barato, a mesma linha pode tocar um som; e, se você quiser aviso fora do Mac, aí sim precisa de algo novo (e-mail ou push), que não existe no projeto hoje.

---

## 7. Riscos da automação em si

1. **Brief que passa no gate e está errado.** O gate prova lint, tipo e testes — não prova que o teste mede a coisa certa. Em série, quatro briefs podem empilhar quatro commits assim. Mitigação parcial que já existe: o teste de aceite é escrito **antes** do código (`SKILL.md` passo 3) e o relatório obrigatório traz a saída colada (AGENTS §8). Mitigação que falta: leitura humana dos quatro relatórios antes de seguir para a série seguinte.
2. **Quatro commits sem revisão.** `main` é trunk-based e o push é imediato (AGENTS §5), então o GitHub recebe cada brief assim que o gate fecha. Reverter **um** commit do meio: `git revert <hash>` cria um commit novo que desfaz só aquele — e, porque cada brief commita apenas os arquivos do seu manifesto, os commits não se sobrepõem (confirmado nos `Arquivos-alvo` do item 2.6; a exceção é o par relatório/PLAN, em que o revert pode conflitar e pedir resolução à mão). `git reset` não serve depois do push.
3. **O que a seção `Lacunas` já cobre:** o que o executor **sabe** que ficou faltando, com destino (backlog, pendência, dívida, decisão) e impacto, e o `agente_lacunas.py` leva para o PLAN sozinho. **O que ela não cobre:** o erro que o executor não percebeu (lacuna só registra o conhecido), e nada nela obriga você a ler antes do brief seguinte — numa série, as lacunas do 080 entram no PLAN sem ninguém olhar antes de o 081 começar.
4. **Risco novo que a série cria:** o PLAN é alterado pelo `agente_lacunas.py` **depois** do commit (é o que vi na entrega do 079), então a árvore fica suja entre briefs e o brief seguinte bate na trava do AGENTS §5. Sem resolver isso, a série para no segundo brief. É a barreira B1.

---

## 8. Tabela de barreiras

| # | Barreira | Prova | Gravidade | Como remover | Quem remove |
|---|---|---|---|---|---|
| A1 | **O script da série não existe.** O AGENTS §10 já descreve o procedimento e diz que `scripts/executar_serie.sh` "nasce no brief 086" — e não há brief 084, 085 nem 086 escrito | `ls scripts/executar_serie.sh` → não existe; `ls docs/briefs/ \| grep 08[4-9]` → nenhum; AGENTS §10 | **Alta** (sem ele não há série; hoje é um `/executar` por vez) | Escrever o brief 086 com o desenho do item 4 e executá-lo como brief normal | Sidarta escreve o brief; o executor o implementa |
| A2 | **Árvore suja**: 5 documentos canônicos modificados e 6 arquivos sem commit (4 briefs, `doc_084`, este `doc_085`). O `agente_entregar.sh` recusa qualquer arquivo fora do manifesto | `git status --short`; `scripts/agente_entregar.sh:30-32` e a recusa que aconteceu na entrega do 079 | **Alta** (a série pararia antes do 080) | Commitar isto antes de começar (comando no fim desta resposta) | Sidarta |
| A3 | **O código de saída do `claude -p` é 0 mesmo quando o brief para sem entregar** | teste 2 (item 2.2): `/executar 999` → `PAROU`, exit 0, `subtype: success` | **Alta** (a série seguiria sobre base quebrada) | O script usa a conferência de entrega de seis itens (4.2), não o código de saída | o executor, no brief 086 |
| A4 | **PLAN sujo depois do commit**: o `agente_lacunas.py` altera o `docs/PLAN.md` depois de o commit já estar fechado, e o PLAN agora é versionado | observado na entrega do 079 (o gate imprimiu as lacunas depois do commit); `git ls-files docs \| wc -l` → 134 | **Alta** (pararia no brief seguinte) | Decidir uma de duas: o `agente_lacunas.py` roda antes do commit, ou a série fecha um commit `docs(plan)` próprio ao fim | Sidarta decide; o executor implementa no 086 |
| A5 | **Comandos de terminal fora do `allow`** (`mkdir`, `cp`, `mv`, `sed`, `python3` solto) são negados em silêncio com `--permission-prompts none`; a escrita de arquivo, essa, funciona | teste 3 (item 2.3) provou a escrita; a lista do `allow` está em `.claude/settings.json` | **Média** | Ensaio com um brief pequeno (o 080 é só documentos) antes dos pesados; se faltar algo, `.claude/serie.settings.json` com a lista extra, passado por `--settings`, sem tocar no settings da sessão interativa | Sidarta aprova a lista; o executor escreve |
| A6 | **Limite da assinatura (janela de uso)**: não há comando que leia quanto resta; quatro execuções seguidas, duas em Opus, podem bater no limite no meio | não conferido; é fato desta sessão que o limite foi atingido hoje, no meio do brief 079 | **Média** | `--max-budget-usd` por brief; a conferência de entrega pega a parada; retomar com a mesma lista depois (o 080 já entregue é reconhecido pelo manifesto `entregue_*`) | Sidarta (janela), executor (orçamento) |
| A7 | **Outras sessões na mesma árvore**: 19 processos `claude` ativos; duas sessões no mesmo repositório atropelariam o `git status` em que a série confia | `pgrep -fl claude \| wc -l` → 19; AGENTS §12 | **Média** | Trava de instância no script e fechar as outras sessões deste projeto antes de começar | Sidarta (fechar), executor (trava) |
| A8 | **Push depende do Chaveiro destravado**; se travar, o commit fica local e o `agente_entregar.sh` sai com 1 | `scripts/agente_entregar.sh:122-132` | Média | A conferência `origin/main..HEAD = 0` pega; o `STATUS.txt` dá o comando `git push` | Sidarta |
| A9 | **O "Para você" do 083** (recarregar a extensão no Chrome e abrir uma página longa) exige pessoa | `brief_083` §6 | Baixa (não bloqueia a série) | A série registra a pendência no `STATUS.txt` e segue; você faz depois | Sidarta |
| A10 | **`git worktree list` é bloqueado pela trava**, mesmo sendo leitura, então a série não consegue conferir worktrees pelo caminho natural | bloqueio visto nesta sessão; `ls .git/worktrees` serve de substituto | Baixa | Liberar a leitura num brief da trava | executor |
| A11 | **Mac dormir** por tampa fechada na bateria (resolvido hoje, mas volta se você desligar da tomada) | `pmset -g batt` → AC Power, 100% | Baixa agora | `caffeinate -dimsu` em volta da série e tampa aberta ou tomada | Sidarta |

---

## 9. O que Sidarta precisa fazer uma vez

1. **Commitar o que está na árvore** (os 5 documentos canônicos já atualizados, os 4 briefs, o `doc_084` e este `doc_085`) — comando no fim da resposta.
2. **Escrever o brief 086** com o desenho do item 4 (o script da série, o arquivo de permissões se o ensaio mostrar que falta, a notificação e o `STATUS.txt`) e executá-lo com `/executar 086`, como brief normal.
3. **Decidir a barreira A4**: o `agente_lacunas.py` passa a rodar antes do commit, ou a série fecha um commit `docs(plan)` próprio ao fim? (Sem essa decisão a série para no segundo brief.)
4. **Antes de cada série**: Mac na tomada, tampa aberta, outras sessões do projeto fechadas, `git status` vazio.
5. **Aprovar a lista de permissões da série**, se o ensaio com o 080 mostrar comando negado.
6. **Depois da série**: ler os quatro relatórios e as lacunas que entraram no PLAN — é a única revisão humana que sobra, e nenhuma automação a substitui.

---

## Atualização dos documentos canônicos

**Quase tudo já está aplicado.** Os oito rascunhos do 084 (§10.1 a §10.8) estão na árvore, sem commit: AGENTS §4 e §10, `SKILL.md`, `_modelo.md`, `ARQUITETURA.md` §11 e §13, `PLAN.md`. Conferi um por um no `git diff`. Então **não repito nada disso**; o que segue é só o que **ainda falta**, como trecho exato para você aprovar. Nada foi aplicado.

### U1. `AGENTS.md` §12 — o rascunho 10.3 do 084 ficou obsoleto

O 084 propôs corrigir a frase "o `.gitignore` exclui `docs/*` de propósito... nada dali jamais entrou num commit". Essa frase **já não existe**: você reescreveu o §12 no commit `d8eda04` e ele hoje diz que os `.md` de `docs/` são versionados. **Nada a fazer.** Registro aqui para você não aplicar o 10.3 do 084 por engano.

### U2. `AGENTS.md` §10 — o número do brief que cria o script

Antes:
```
- **Execução em série.** Vários briefs, um depois do outro, sem acompanhamento: `scripts/executar_serie.sh <NNN> <NNN> ...` (o script nasce no brief 086; até lá, um `/executar` por vez).
```
Depois (se você escrever o brief com outro número, troque aqui; e a frase fica verdadeira enquanto o brief não existir):
```
- **Execução em série.** Vários briefs, um depois do outro, sem acompanhamento: `scripts/executar_serie.sh <NNN> <NNN> ...` (o script e o arquivo de permissões da série são criados pelo brief 086, ainda não escrito; até ele ser executado, um `/executar` por vez, com a árvore limpa entre um e outro).
```

### U3. `AGENTS.md` §10 — o critério de sucesso, que é a parte que não pode ficar implícita

Antes:
```
A série confere a cada brief, e não pelo código de saída do Claude Code (uma parada do `/executar` sai com 0): o manifesto `logs/entregue_<NNN>_commit.txt`, o commit com `(brief NNN)`, `origin/main..HEAD` igual a zero e a árvore limpa.
```
Depois:
```
A série confere a cada brief, e não pelo código de saída do Claude Code (provado no relatório 085: uma parada correta do `/executar` sai com 0, `is_error: false`, `subtype: success`): o manifesto renomeado para `logs/entregue_<NNN>_commit.txt`, o commit mais novo citando o brief, `origin/main..HEAD` igual a zero, a árvore limpa, a primeira das três linhas finais sem `PAROU:`, e `is_error` falso com `subtype: success` no JSON do `-p`. A série nunca chama `scripts/agente_entregar.sh --simular` (ele sai com 0 sem entregar nada).
```

### U4. `.claude/skills/executar/SKILL.md` — a árvore limpa no fim de cada brief

Antes (fim do passo 7):
```
7. Rode `scripts/agente_entregar.sh $ARGUMENTS`. Ele roda o gate, commita só o manifesto e faz o push. Se falhar, corrija a causa e rode de novo, **no máximo 3 vezes**. Na terceira falha, pare e descreva no relatório o que falhou.
```
Depois:
```
7. Rode `scripts/agente_entregar.sh $ARGUMENTS`. Ele roda o gate, commita só o manifesto e faz o push. Se falhar, corrija a causa e rode de novo, **no máximo 3 vezes**. Na terceira falha, pare e descreva no relatório o que falhou. Entregue, confira `git status --porcelain`: a árvore tem de ficar vazia. Se o `agente_lacunas.py` deixou o `docs/PLAN.md` sujo, feche-o no mesmo brief (manifesto novo, mensagem `docs(NNN): lacunas no PLAN`) — em série, árvore suja faz o brief seguinte parar.
```

### U5. `docs/PLAN.md` — Backlog

Acrescentar ao Backlog (uma linha; o `agente_lacunas.py` não serve aqui porque este relatório não é de brief):
```
- 086 · `scripts/executar_serie.sh` e a execução de vários briefs sem acompanhamento (desenho no relatório 085, seção 4) · não iniciado · — · 2026-11-08
```

### U6. `docs/ARQUITETURA.md` §13 — o estado deixa de ser "decidido" e passa a ter o critério

Antes:
```
Estado: o procedimento está decidido; o script nasce no brief 086 (`scripts/executar_serie.sh` e `.claude/serie.settings.json`). Até lá, um `/executar` por vez.
```
Depois:
```
Estado: o procedimento está decidido e atestado (relatório 085: o modo sem acompanhamento funciona, a escrita de arquivo funciona, o `agente_entregar.sh` tem código de saída confiável e o do Claude Code não tem). O script nasce no brief 086 (`scripts/executar_serie.sh` e, se o ensaio mostrar comando negado, `.claude/serie.settings.json`). Até lá, um `/executar` por vez, com a árvore limpa entre um e outro.
```

### U7. Nada a mudar em

- `.claude/settings.json` — a lista da série, se for necessária, vai em arquivo próprio passado por `--settings`, para a sessão interativa não ganhar permissão de escrita automática.
- `docs/EXCECOES_TEXTO_INTEGRAL.md` — só o brief 080 escreve nele.
- `docs/briefs/_modelo.md` — o campo `Ordem em série` e a pergunta do texto por inteiro já estão lá.

---

## RELATÓRIO FINAL

- **Brief executado:** nenhum. Esta é uma investigação pedida por Sidarta, não um brief: não há `docs/briefs/brief_085_*.md`, e nada foi implementado.
- **Arquivos criados:** `docs/docs/doc_085_atestado_execucao_em_serie_2026-11-08.md` (este relatório).
- **Arquivos alterados:** nenhum. Os 5 documentos canônicos que aparecem modificados na árvore foram alterados **antes** desta investigação (rascunhos do relatório 084 aplicados); eu não toquei neles.
- **Arquivos preservados literalmente na área afetada:** todos. Nenhum arquivo de `agente_nw/`, `config/`, `extensao/`, `tests/` ou `scripts/` foi lido com escrita.
- **Script de verificação (o gate):** não rodado — não há mudança de código para verificar. A medida citada (`1031 passed, 5 deselected in 26.62s`) é da entrega do brief 079, hoje.
- **Comandos executados:** `claude --version`; `claude --help`; as três chamadas `claude -p` dos itens 2.1 a 2.3 (saídas coladas); `git status --short`; `git diff --stat`; `git diff` dos 5 documentos; `git rev-list --count origin/main..HEAD`; `pmset -g batt`; `pgrep -fl claude | wc -l`; `curl` no Ollama; `ls` dos caminhos da série; `grep` em `scripts/agente_entregar.sh`, `.claude/settings.json`, `pyproject.toml` e nos cabeçalhos dos briefs 080-083; `rm logs/teste_permissao_serie.txt` (o arquivo do teste 3).
- **Manifesto do commit:** não existe — este relatório não deve ser commitado pelo executor. O comando para você commitar está no fim da resposta do chat.
- **Pendências e decisões que ficaram abertas:** as 11 barreiras da seção 8 e os 6 itens da seção 9; em especial, a decisão A4 (quando o `agente_lacunas.py` roda) e a escrita do brief 086.
- **Resumo, Doing, Backlog e Done do `docs/PLAN.md` atualizados:** não — de propósito. A linha proposta para o Backlog está em U5, para você aprovar.

---

## Lacunas

| # | Lacuna | Destino | Impacto |
|---|---|---|---|
| 1 | O brief 086 (`scripts/executar_serie.sh`, notificação, `STATUS.txt`, trava de instância) ainda não está escrito, e o AGENTS §10 já o cita | backlog | degrada |
| 2 | Decisão A4: o `agente_lacunas.py` passa a rodar antes do commit ou a série fecha um commit `docs(plan)` próprio? Sem isso a série para no segundo brief | decisão | degrada |
| 3 | Uma execução completa de `/executar` sem acompanhamento, com um brief de verdade, não foi provada — só leitura (teste 1), parada (teste 2) e escrita de arquivo (teste 3). O ensaio natural é o 080, que só mexe em documentos | backlog | degrada |
| 4 | Limite da janela de uso da assinatura para quatro execuções seguidas: não há comando que leia isso, e o limite foi atingido hoje no meio do brief 079 | decisão | degrada |
| 5 | Quais dos 19 processos `claude` ativos estão nesta árvore de trabalho: não conferido (`git worktree list` é bloqueado pela trava) | dívida | nice |
| 6 | O push de verdade em processo sem terminal não foi provado (provar exige gravar); só a leitura remota foi, no relatório 084 | dívida | nice |
| 7 | Comandos de terminal fora do `allow` (`mkdir`, `cp`, `mv`, `sed`) numa execução `--permission-prompts none`: a negativa silenciosa é dedução da documentação do `--permission-prompts`, não teste | dívida | nice |
| 8 | A revisão humana dos relatórios entre briefs de uma série não tem mecanismo nenhum — depende de você lembrar | decisão | degrada |
