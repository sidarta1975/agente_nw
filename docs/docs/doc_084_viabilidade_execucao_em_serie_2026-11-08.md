# Relatório 084 — Viabilidade de executar briefs em série, sem acompanhamento

**Veredito: VIÁVEL COM AJUSTES.** O Claude Code roda `/executar` sozinho (testado), a trava vale nesse modo e a entrega é confiável. Mas três coisas precisam de ajuste antes da série 080–083: a árvore de trabalho já está suja para o `agente_entregar.sh`, o código de saída do Claude Code é 0 mesmo quando o brief para sem entregar, e o Mac está com 13% de bateria.

Só investigação. Nenhum brief executado, nenhum código alterado, nenhum git de escrita, nenhum acesso ao banco real nem a rede social. Único gasto: dois chamados curtos do Claude Code (US$ 0,006 cada, modelo Haiku).

Convenção: "não conferido" = não consegui provar sem executar um brief de verdade.

---

## 1. Modo sem acompanhamento

| Item | Prova |
|---|---|
| Versão | `claude --version` → `2.1.318 (Claude Code)` |
| Opções que importam | `claude --help`: `-p/--print`, `--permission-mode` (acceptEdits, auto, bypassPermissions, manual, dontAsk, plan), `--permission-prompts none` ("nobody: anything that would prompt is denied automatically"), `--allowedTools`, `--disallowedTools`, `--model` (alias `opus`, `sonnet`), `--effort` (low, medium, high, xhigh, max), `--max-turns`, `--max-budget-usd` (só com `-p`), `--output-format json` / `stream-json`, `--no-session-persistence`, `--settings <arquivo>`, `--debug-file` |
| Permissões de hoje | `.claude/settings.json`: `allow` só de leitura, `pytest`, `ruff`, `mypy`, `scripts/verificar.sh`, `scripts/agente_entregar.sh`; `deny` de git de escrita, `commitar.sh` e `sqlite3 dados/agente.db`. **Não há `Edit`, `Write`, `python3` nem `mkdir` no `allow`.** |
| Modo padrão do usuário | `~/.claude/settings.json`: `"defaultMode": "auto"`, modelo `claude-opus-5`. `~/.claude/settings.local.json` (global, fora do projeto) tem `allow` para `git add *`, `git commit *`, `git push *`. O `deny` do projeto vence, e a trava (hook) também bloqueia. |
| A trava | `.claude/hooks/guarda_comando.py`, ligada em `.claude/settings.json` (PreToolUse, matcher `Bash`). Bloqueia com código 2. |

### Teste inofensivo no modo headless (cole)

Comando: `claude -p "Use a ferramenta Bash para rodar exatamente: head -n 3 docs/briefs/brief_080_... Depois imprima só a primeira linha..." --model haiku --effort low --permission-mode dontAsk --permission-prompts none --allowedTools "Bash(head:*)" --max-turns 4 --output-format json --no-session-persistence --debug-file <scratchpad>/headless_debug.txt`

```
EXIT=0
"is_error":false,"subtype":"success","terminal_reason":"completed","num_turns":2,
"permission_denials":[],"total_cost_usd":0.00614603,"duration_ms":3104,
"result":"# Brief 080 — Registrar as exceções ao \"texto por inteiro\" aprovadas por Sidarta"
```

A trava rodou no modo headless (linha do arquivo de depuração):
```
Hooks: PreToolUse:Bash [python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/guarda_comando.py"] finished with status 0 (43ms)
```

### Segundo teste (extra, inofensivo): a skill `/executar` carrega em headless

`claude -p "/executar 999" ... --output-format json` → `is_error False, subtype success`, resposta: "O brief 999 não existe no disco ... Não executei nada." Isto prova que a skill (`disable-model-invocation: true`) é chamada por `-p` e que o passo 1 funciona. **E prova a barreira 2 abaixo: uma parada do `/executar` sai com `success`.**

### O que a trava faz quando manda bloquear

- Fora do headless, em teste direto da trava: `echo '{"tool_name":"Bash","tool_input":{"command":"git add x"}}' | python3 .claude/hooks/guarda_comando.py` → `Bloqueado: git de escrita é de Sidarta ...`, `exit=2`.
- Bloqueio **dentro** do headless: não conferido (o teste exigiria pedir um `git add` ao Claude Code de verdade). A execução da trava no headless está provada (acima); o código 2 do PreToolUse é o mesmo mecanismo.
- `--permission-mode bypassPermissions` com a trava: não conferido; **não recomendo** usá-lo (a ajuda do Claude Code o limita a "sandboxes sem internet").
- Efeito colateral achado: a trava bloqueia `git worktree list` (leitura), porque `worktree` está inteiro em `GIT_ESCRITA` (`guarda_comando.py:31`). Comprovado: meu próprio comando com `git worktree list` foi recusado nesta sessão. Para o executor, basta `ls .git/worktrees`.

**Conclusão do item 1:** o modo funciona neste repositório. Falta uma lista de permissões própria para a série (ver Barreira B3).

---

## 2. Encadeamento

### O `agente_entregar.sh` devolve código de saída confiável?

Sim, por leitura do script (`scripts/agente_entregar.sh`); não rodei (rodar commita):
- `set -euo pipefail` (linha 15); `parar()` imprime `✗ ...` e faz `exit 1`.
- Gate: `if ! scripts/verificar.sh 2>&1 | tee -a "$LOG"; then parar` — com `pipefail`, falha do gate vira falha do `if`.
- Commit: `if ! SEM_PERGUNTA=1 scripts/commitar.sh ...; then ... parar`.
- Push: `git push >> "$LOG" 2>&1 || PUSH_OK=0`; se falhar, imprime "falhou só o envio" e `exit 1`, **depois de renomear o manifesto para `entregue_*`** (o commit local existe).
- `scripts/agente_lacunas.py ... || true`: nunca derruba a entrega.
- Única saída 0 com sucesso: a linha `✓ brief NNN: commit <hash>, enviado ao GitHub`, depois do push.

`verificar.sh` sai com 1 em qualquer etapa que falha (cada `if ! etapa ...; then ... exit 1`). Gate atual: `1031 passed, 5 deselected in 26.62s` (`logs/verificar_ultimo.txt`).

### A regra das 3 tentativas termina em código diferente de zero?

**Não.** A skill diz "na terceira falha, pare e descreva no relatório" (`SKILL.md` passo 7). Parar assim é uma resposta normal: o Claude Code sai com 0. Prova: o teste `/executar 999` saiu com `success` e `is_error False` mesmo sem executar nada. O código de saída do `claude -p` só vira diferente de zero em erro de uso (`--permission-mode bogus` → `exit 1`, medido) e, pela documentação da ajuda, em falha de execução/limite de turnos (`--max-turns`, não medido).

### Desenho do executor em série (descrição, não código)

`scripts/executar_serie.sh 080 081 082 083`, Bash compatível com macOS 3.2:

1. **Antes de tudo:** confere árvore limpa (ver B1), `origin/main..HEAD` = 0, o Ollama não é exigido, energia na tomada e o brief de cada número existe em `docs/briefs/` (e que o número casa com um só arquivo).
2. **Por brief, contexto novo:** `claude -p "/executar NNN" --model <do cabeçalho> --effort <do cabeçalho> --permission-mode dontAsk --permission-prompts none --settings .claude/serie.settings.json --max-turns <N> --max-budget-usd <teto> --output-format json --no-session-persistence`, saída em `logs/serie/<data>/NNN.json` e texto em `NNN.txt`.
3. **Critério de sucesso do brief (o código de saída não basta):** todos verdadeiros — saída 0; `logs/entregue_NNN_commit.txt` existe; `git log -1 --format=%s` contém `(brief NNN)`; `git rev-list --count origin/main..HEAD` = 0; `git status --porcelain` vazio ou só o PLAN; `logs/entregar_ultimo.txt` termina em `✓ brief NNN: commit`.
4. **Parada:** qualquer critério falso → escreve `logs/serie/<data>/STATUS.txt` (`PAROU no brief NNN: <motivo>`; quais já foram entregues; o comando para retomar), notifica (item 6) e sai com 1. Não tenta o brief seguinte.
5. **Ordem e dependência:** a ordem é a da linha de comando; o script confere o campo novo `Ordem` (item B3 da seção "Atualização dos documentos") e recusa uma lista que fira "antes de".
6. **Fim:** `STATUS.txt` com `CONCLUÍDA`, hashes, minutos e custo por brief (do JSON), pendências humanas coletadas das três linhas finais ("Para você"). Notificação.
7. **Repetível:** recebe qualquer lista; os modelos vêm do cabeçalho de cada brief.

O que o script precisa (lista): (a) ler `**Modelo:**` e `**Esforço:**` do brief; (b) arquivo `.claude/serie.settings.json` com as permissões da série; (c) `caffeinate -dimsu` em volta; (d) checagem de tomada (`pmset -g batt`); (e) trava de instância única (arquivo `logs/serie/TRAVA`); (f) verificação de sucesso do item 3; (g) STATUS e notificação; (h) tempo máximo por brief (`timeout` não existe no macOS; usar `--max-turns` e `--max-budget-usd`, ou `perl -e 'alarm'`).

---

## 3. Modelo e esforço por brief

Respeitar é possível, e o script faz sozinho. Provas: `--model` aceita alias `opus`/`sonnet` e `--effort` aceita `low|medium|high|xhigh|max` (`claude --help`); o teste usou `--model haiku --effort low` e o JSON devolveu `modelUsage: claude-haiku-5-5`. Cabeçalhos: 080 Sonnet/baixo, 081 Sonnet/médio, 082 Opus/alto, 083 Opus/médio.
- Mapeamento a fixar: baixo→`low`, médio→`medium`, alto→`high`.
- A skill `executar` não tem `model:` no cabeçalho (`SKILL.md`); o modelo vem da linha de comando.
- Sem isso, valeria o `claude-opus-5` do `~/.claude/settings.json` para todos: perde-se economia no 080/081 e a ordem de grandeza de uso.
- Não conferido: se `--effort` é aceito igual a bordo de `-p` com a skill (o teste usou `--effort low` com sucesso, sem erro).

---

## 4. Barreiras de ambiente (veredito uma a uma)

| Item | Veredito | Prova |
|---|---|---|
| Credencial do push sem terminal | **ok** | `git remote -v` → HTTPS; `credential.helper = osxkeychain`; `gh auth status` → logado como `sidarta1975`. `GIT_TERMINAL_PROMPT=0 git ls-remote origin HEAD < /dev/null` → `e45c9dd5...	HEAD`, exit 0 (leitura; sem terminal). Push em si: não conferido (gravaria). Fica ok enquanto o Chaveiro estiver destravado (Mac reiniciado e ainda sem login deixa travado: nesse caso o push falha, ver B7). |
| Ollama 11435 ligado | **ok, e o gate não precisa dele** | `curl 127.0.0.1:11435/api/tags` responde; `porteiro status`: `qwen2.5:7b` carregado, usado por `sergio` e `sergio-S1`. `pyproject.toml:57` → `addopts = "-m 'not rede_real and not llm_real'"`; o gate rodou 1031 testes com 5 desmarcados. Testes de 080–083 usam cliente falso por convenção (`brief 083 §4`: "banco usa tmp_path"); `llm_real` aparece só em 3 arquivos de teste. Não conferido: teste de `llm.py` do 082 chamando o `porteiro` real. |
| Tempo e custo (Max) para 4 execuções | **não conferido o limite; risco moderado** | Medido: um chamado de Haiku custa US$ 0,006 em lista (`total_cost_usd`); `costBasis: "list"` (preço de tabela, não desconta a assinatura). Não há como ler o limite da janela da assinatura por linha de comando. Estimativa por tamanho: 080 pequeno (só documentos); 081 médio; 082 e 083 em Opus, os dois pesados. O JSON do `-p` traz `usage` e `modelUsage`: o script registra e pode parar por `--max-budget-usd`. Gate: 26,6 s por tentativa (3 tentativas por brief = 80 s no pior caso). |
| Mac dormir ou fechar a tampa | **BARREIRA agora** | `pmset -g batt` → `13%; discharging; 0:11 remaining`. `pmset -g assertions` → `PreventUserIdleSystemSleep` já mantido por Claude e `caffeinate`; ele impede dormir por **ociosidade**, **não** por tampa fechada na bateria. Remover: ligar na tomada; `caffeinate -dimsu` em volta do script; tampa aberta ou monitor externo. |
| Outro processo ou sessão na mesma árvore | **barreira branda** | `pgrep -fl claude` → 6 processos `claude` ativos agora (inclui esta sessão); não consegui dizer quais estão neste repositório. `.git/worktrees/agente_nw_040` é registro velho (AGENTS §12). O script precisa de trava de instância e de aviso "feche as outras sessões deste projeto". |
| Suíte demorada | **ok** | `1031 passed, 5 deselected in 26.62s`. |
| Árvore com arquivo sem commit | **BARREIRA já hoje** | `git status --short` → 4 linhas `??`, exatamente os briefs 080–083. `agente_entregar.sh:96-98` recusa qualquer arquivo alterado fora do manifesto ("há arquivo fora da lista"). Ver B1. |
| "Para você" do 083 (recarregar a extensão no Chrome) | **barreira humana, não bloqueia a série** | `brief_083 §6`: "Para você: recarregar a extensão no Chrome e abrir uma página longa". Pessoa necessária; a série registra a pendência no STATUS e segue (o brief 083 já está entregue ao commit; o recarregar é verificação posterior). |

---

## 5. Tabela de barreiras (resumo para decisão)

| # | Barreira | Prova | Gravidade | Como remover | Quem remove |
|---|---|---|---|---|---|
| B1 | A árvore já está suja para o `agente_entregar.sh`. Os 4 briefs estão sem commit e `docs/*.md` passou a ser versionado (`d8eda04`). O `PLAN.md` é rastreado e o `agente_lacunas.py` o altera **depois** do commit (`agente_lacunas.py:116-126`), então ele fica sujo e o brief seguinte só passa se o incluir no manifesto. A skill não manda pôr relatório, PLAN e o próprio brief no manifesto | `git status --short`; `git ls-files docs` → 134 arquivos; `agente_entregar.sh:96-98`; `logs/entregue_079_arquivos.txt` (inclui o relatório e o PLAN) | **Alta** (a série pararia no 080) | Commitar os 4 briefs antes (comando na entrega); ajustar a skill e o AGENTS para o manifesto sempre incluir relatório + PLAN (rascunho na seção "Atualização"); decidir o que fazer com o PLAN sujo ao fim do último brief (commit "docs(PLAN)" do próprio script de série) | Você (commit dos briefs) e eu num brief (skill/script) |
| B2 | Parada do `/executar` sai com código 0 | teste `/executar 999` → `success`; SKILL passo 7 ("pare e descreva") | **Alta** (sem isso a série seguiria sobre base quebrada) | O script confere o critério de sucesso do item 3 do desenho, não o código | Eu, num brief (`executar_serie.sh`) |
| B3 | Permissões do modo sem acompanhamento: o `allow` do projeto não cobre `Edit`/`Write`/`python3`/`mkdir`/`cp` que o brief usa. Em `dontAsk`, o que não está no `allow` é negado em silêncio e o brief gira até o `--max-turns` | `settings.json` (lista completa acima); `--permission-prompts none` | **Alta** | Arquivo `.claude/serie.settings.json` com `Edit`, `Write` (limitados a `agente_nw/**`, `tests/**`, `docs/**`, `scripts/**`, `config/**`, `extensao/**`, `logs/**`), `Bash(python3 scripts/*)`, `Bash(.venv/bin/*)`, `Bash(mkdir:*)`, e o `deny` atual; **teste de ensaio** com um brief sem efeito colateral antes da série | Eu (arquivo) e você (aprovar a lista) |
| B4 | Bateria 13% e tampa | `pmset -g batt` | **Alta hoje** | Tomada + `caffeinate -dimsu` no script + tampa aberta | Você (tomada) e eu (caffeinate) |
| B5 | O código de saída dos limites da assinatura (janela cheia) é desconhecido | não conferido | Média | O critério de sucesso do item 3 pega; o STATUS diz "PAROU, sem commit"; retomar depois com o mesmo comando | Eu |
| B6 | Outras 5 instâncias do Claude Code ativas; uma mexendo na mesma árvore quebraria o `status` | `pgrep -fl claude` | Média | Trava de instância no script; você fecha as outras sessões do projeto antes | Você e eu |
| B7 | Push falha se o Chaveiro travar; o script do `agente_entregar.sh` marca o manifesto como entregue e sai com 1; commit local já existe | `agente_entregar.sh:117-132` | Média | Critério de sucesso confere `origin/main..HEAD = 0`; STATUS dá o comando `git push` | Eu |
| B8 | Conflito de arquivos entre briefs: não achei nenhum. 080 toca só documentos; 081 `historico/redacao/pedido/candidatos`; 082 `llm.py` e `redigir_ganchos.py` (estimador); 083 `coleta/` e `extensao/` | `Arquivos-alvo` de cada brief | Baixa | Manter a ordem pedida 080→081→082→083; campo `Ordem` para listas futuras | Eu |
| B9 | Trava bloqueia `git worktree list` (leitura) | `guarda_comando.py:31`; bloqueio ao vivo nesta sessão | Baixa | Liberar `git worktree list` num brief da trava; hoje `ls .git/worktrees` serve | Eu, num brief |
| B10 | Dois briefs de número 074 e 075 duplicados no disco tornam `/executar 074` ambíguo (não afeta 080–083) | `docs/PLAN.md` Decisões em aberto `[074-1]` | Baixa | Série confere que `brief_NNN_*` casa com um só arquivo | Você (arquivar os antigos) |

---

## 6. Pontos de decisão humana (nunca automáticos) e como a série para

Nunca automático:
1. Aprovar exceção ao texto por inteiro, ou escrever em `docs/EXCECOES_TEXTO_INTEGRAL.md` além do que o brief 080 lista (tabela 2.2 do brief 080: 19 pontos). Um brief que precise de linha nova no registro **para**.
2. Qualquer uso do banco real (`dados/agente.db`) e qualquer `agente_nw` que não seja `--help`, `listas ver`, `copiar-banco` ou `verificar-ambiente` na pasta principal (a trava já manda perguntar; sem terminal, `ask` equivale a negar, pelo `--permission-prompts none`).
3. Leitura de rede social e login (a trava bloqueia `ler-rede-social`, `listas atualizar`, `pedir`, `extensao`).
4. Recarregar a extensão no Chrome e abrir página longa (083).
5. Ampliar o escopo do brief, tocar `AGENTS.md`, `settings`, skill ou trava fora de um brief que os tenha como alvo (AGENTS §10).
6. Subir qualquer limite de texto sem o 082 entregue.
7. Decisão de produto (qualquer "Decisões em aberto").
8. `git push --force`, reescrever histórico, desfazer commit.

Como parar e avisar: (a) o brief, ao chegar nisso, termina com "Para você: <o que>" e **não** entrega aquilo; (b) o script lê essa linha, grava no STATUS `PAROU PARA DECISÃO no brief NNN: ...` e notifica; (c) uma pendência humana que não impede o commit (como o Chrome do 083) vira "pendência" no STATUS e a série segue.

---

## 7. Notificação

Hoje não existe nada no projeto: `grep` de `"Stop"`, `"Notification"`, `"SessionEnd"` em `.claude/settings.json`, `~/.claude/settings.json` e `~/.claude/settings.local.json` → nenhum resultado. `~/.claude/settings.json` tem `inputNeededNotifEnabled` e `agentPushNotifEnabled` como `true`, que valem para sessões interativas, não para o `-p`. `/usr/bin/osascript` existe; `terminal-notifier` não.

Faltaria, no script de série: (1) arquivo `logs/serie/<data>/STATUS.txt` (sempre), (2) `osascript -e 'display notification "..." with title "agente_nw: série"'` no fim ou na parada, (3) opcional `say` para som. Não precisa de hook do Claude Code.

---

## 8. Riscos da automação em si

- **Brief que passa no gate e está errado.** O gate prova estilo, tipos e testes que o próprio brief escreveu; não prova que o teste do brief cobre o pedido. Mitigação: o relatório obrigatório cola a saída; a série não elimina a leitura do relatório pelo dono. Recomendo revisar o 082 (mais arriscado) logo que terminar, antes de qualquer brief novo.
- **Quatro commits sem revisão.** Os commits são pequenos e separados por brief. Todos ficam em `main` e já vão ao GitHub. Reverter só um: `git revert <hash>` (você digita; o executor não faz) cria um commit novo desfazendo aquele; isto só é limpo se os briefs seguintes não mexeram nas mesmas linhas. Arquivos-alvo diferentes mantêm isso verdadeiro para esta série (080: documentos; 081: `historico/redacao/pedido/candidatos`; 082: `llm.py` e o estimador de `redigir_ganchos.py`; 083: `coleta/` e `extensao/`). Ponto de atenção: 081 e 082 podem tocar `redacao.py`/`redigir_ganchos.py` por motivos diferentes; o 082 vem depois do 081 na ordem pedida.
- **O que a seção `## Lacunas` já cobre:** lacunas que o próprio executor viu, com destino no PLAN, automáticas (`agente_lacunas.py`).
- **O que ela não cobre:** o que o executor não viu (erro silencioso); uma decisão de produto que o executor tomou sem perceber; custo e tempo; `git diff` completo por brief. Proposta: o STATUS da série traz, por brief, `git show --stat <hash>` e a tabela de lacunas, para você ler em um lugar só.

---

## 9. O que você precisa fazer uma vez

1. Ligar o Mac na tomada e deixar a tampa aberta durante a série.
2. Commitar os 4 briefs (comando no fim) e fechar as outras sessões do Claude Code que usem este repositório.
3. Aprovar as mudanças da seção 10 (AGENTS, skill, modelo de brief, PLAN, ARQUITETURA) e mandar escrever o brief do executor em série.
4. Aprovar a lista de permissões da série (B3). Depois do ensaio, nada mais precisa de você durante a execução.
5. Depois da série: recarregar a extensão no Chrome e abrir uma página longa (083).

Credencial do GitHub: já está configurada (item 4); nada a fazer.

---

## 10. Atualização dos documentos canônicos (rascunhos; NADA foi aplicado)

### 10.1 `AGENTS.md` — §10 (execução em série)

Antes:
```
- Todo brief é executado com `/executar <NNN>`.
```
Depois:
```
- Todo brief é executado com `/executar <NNN>`.
- **Execução em série.** Vários briefs, um depois do outro, sem acompanhamento: `scripts/executar_serie.sh <NNN> <NNN> ...`. Cada brief roda em contexto novo (`claude -p "/executar NNN"`), com o modelo e o esforço do próprio cabeçalho. A série confere a cada brief, e não pelo código de saída do Claude Code (uma parada do `/executar` sai com 0): o manifesto `logs/entregue_<NNN>_commit.txt`, o commit com `(brief NNN)`, `origin/main..HEAD` igual a zero e a árvore limpa. **Qualquer falha para a série**, sem tentar o brief seguinte, grava `logs/serie/<data>/STATUS.txt` e avisa por notificação do macOS. Nunca automático na série: aprovar exceção ao texto por inteiro, banco real, leitura de rede social, decisão de produto, mudança de `AGENTS.md`, `settings` ou trava. A ordem dos briefs vem do campo `Ordem` do cabeçalho.
```

### 10.2 `AGENTS.md` — §4 (texto por inteiro)

Antes (última linha de §4):
```
- Quem decide que tema cabe numa mensagem é o usuário (brief 046): ...
```
Depois (acrescenta uma linha logo após):
```
- **Texto por inteiro (brief 079).** Quando o projeto analisa um texto (notícia, página, mensagem, comentário, histórico, fato, pedido), analisa o texto inteiro. O princípio é do dono do projeto: só Sidarta aprova exceção, e só ele (ou um brief escrito por ele) escreve em `docs/EXCECOES_TEXTO_INTEGRAL.md`. O executor não aprova exceção nem marca ponto como aprovado. Sem linha no registro, o corte é violação. O verificador é `scripts/verificar_auditoria_texto.py`. Todo brief que lê, monta ou envia texto a modelo, embedding ou filtro responde, no relatório: **"algum texto é analisado só em parte?"** (sim, onde e com que aprovação; ou não, e a prova).
```

### 10.3 `AGENTS.md` — §12 (frase desatualizada, achada nesta investigação)

Antes:
```
e a pasta `docs/` inteira (`docs/PLAN.md`, `docs/briefs/`, `docs/docs/`) — o `.gitignore` exclui `docs/*` de propósito, com exceção só de `docs/.gitkeep`; `git ls-files docs/` devolve vazio, isto é, nada dali jamais entrou num commit.
```
Depois:
```
e a pasta `docs/` (`docs/PLAN.md`, `docs/briefs/`, `docs/docs/`). Desde o commit `d8eda04` (2026-11-08) os `.md` de `docs/` são versionados (`.gitignore`: `!docs/*.md`, `!docs/*/*.md`); outros tipos de arquivo continuam ignorados. Mesmo assim, a pasta só se comporta como "o projeto" numa única árvore de trabalho: uma worktree separada tem o próprio banco e a própria cópia de `docs/`. Todo `.md` de `docs/` que um brief cria ou altera (relatório, PLAN, o próprio brief) entra no manifesto.
```
O resto do §12 (regra prática) fica.

### 10.4 `.claude/skills/executar/SKILL.md` — passo 6 (manifesto) e fim

Antes:
```
   - o manifesto: `logs/commit_$ARGUMENTS.txt` (mensagem do commit) e `logs/arquivos_$ARGUMENTS.txt` (um caminho por linha, só o que entra no commit);
   - as linhas Resumo, Doing e Done do `docs/PLAN.md`.
```
Depois:
```
   - as linhas Resumo, Doing e Done do `docs/PLAN.md`;
   - o manifesto: `logs/commit_$ARGUMENTS.txt` (mensagem do commit) e `logs/arquivos_$ARGUMENTS.txt` (um caminho por linha, só o que entra no commit). Entram sempre: o relatório, o `docs/PLAN.md` e o próprio brief se ainda não estiver no git (todos os `.md` de `docs/` são versionados).
```
Antes (passo 8, última linha dos três itens):
```
   - `Nada para você.` ou só o que exige Sidarta: teste com pessoa real, login em rede social, decisão de produto.
```
Depois:
```
   - `Nada para você.` ou só o que exige Sidarta: teste com pessoa real, login em rede social, decisão de produto.
   - Se parou sem entregar (brief ausente, "Depende de" não satisfeito, terceira falha do gate, ponto que só Sidarta decide), a primeira das três linhas começa com `PAROU:` e diz o motivo em uma frase. A série lê isso.
```
Acrescentar ao fim das regras:
```
- Em série, não há ninguém para responder: o que exigir resposta vira "Para você" e a série para, em vez de adivinhar.
```

### 10.5 `docs/briefs/_modelo.md` — campo novo e pergunta de texto

Antes:
```
**Teste de aceite:** arquivo ou comando que prova o critério; havendo teste, o executor o cria antes do código
**Depende de:** brief, commit ou ação de Sidarta que precisa existir antes; o executor confere literalmente e, se faltar, para
**Data:** AAAA-MM-DD
```
Depois:
```
**Teste de aceite:** arquivo ou comando que prova o critério; havendo teste, o executor o cria antes do código
**Depende de:** brief, commit ou ação de Sidarta que precisa existir antes; o executor confere literalmente e, se faltar, para
**Ordem em série:** "livre" | "depois de NNN" | "antes de NNN"; a série (`scripts/executar_serie.sh`) recusa lista que fira isto
**Data:** AAAA-MM-DD
```
E na seção 4 (Testes), acrescentar à frase final:
```
Todo brief que lê, monta ou envia texto a modelo, embedding ou filtro responde no relatório: "algum texto é analisado só em parte?" (AGENTS §4, brief 079).
```
Para a série atual: 080 `antes de 081, 082, 083`; 081 `livre`; 082 `antes de qualquer brief que suba limite de texto`; 083 `livre`.

### 10.6 `docs/PLAN.md` — Backlog e Resumo

Antes (Backlog, última linha):
```
- [079-2] Depois das decisões, cada correção aprovada precisa de um brief próprio ...
```
Depois (linhas acrescentadas):
```
- [084-1] `scripts/executar_serie.sh` + `.claude/serie.settings.json` (série sem acompanhamento: critério de sucesso fora do código de saída, STATUS, notificação, `caffeinate`, trava de instância) · degrada · 2026-11-08
- [084-2] Liberar `git worktree list` na trava (hoje bloqueado por estar inteiro em `GIT_ESCRITA`) · nice · 2026-11-08
- [084-3] Skill/AGENTS: o manifesto sempre inclui relatório, PLAN e brief (os `.md` de `docs/` são versionados desde `d8eda04`) · degrada · 2026-11-08
```
Resumo, "**Em execução:**" não muda. Acrescentar ao fim do parágrafo "Último brief concluído": `antes, 084 (relatório, sem código), viabilidade da execução em série: VIÁVEL COM AJUSTES.` (só se você quiser o 084 no Resumo; o `agente_lacunas.py` já leva as lacunas abaixo para o Backlog).

### 10.7 `docs/ARQUITETURA.md` — §11 e §13 novo

Antes (§11):
```
Tarefas não assistidas: nenhuma. **Nunca rodam sozinhos:** git, leitura de rede social, alteração de ficha de contato, a suíte de testes padrão.
```
Depois:
```
Tarefas não assistidas do produto: nenhuma. **Nunca rodam sozinhos:** leitura de rede social, alteração de ficha de contato, operação no banco real. O gate e o git de entrega rodam pelo executor (`scripts/agente_entregar.sh`, AGENTS §5–§6); a execução de vários briefs em série (AGENTS §10) é disparada por Sidarta, não é agendamento.
```
(a frase antiga "git ... a suíte de testes padrão" já diverge do AGENTS §6 desde o brief 058.)

Novo `## 13. Execução em série de briefs` ao fim (depois da §12), com: o script, o critério de sucesso por brief, o STATUS, a notificação e a lista "nunca automático" da seção 6 deste relatório.

### 10.8 Outros que acho necessários

- `.claude/settings.json`: não alterar; a lista da série vai em arquivo próprio (`.claude/serie.settings.json`), passado por `--settings`, para a sessão interativa não ganhar permissões de escrita automática.
- `.claude/hooks/guarda_comando.py`: ver [084-2].
- `docs/EXCECOES_TEXTO_INTEGRAL.md`: nenhuma mudança aqui; só o brief 080 escreve.

---

## RELATÓRIO FINAL
- Brief executado: pedido de investigação (sem número de brief); relatório 084.
- Arquivos criados: `docs/docs/doc_084_viabilidade_execucao_em_serie_2026-11-08.md`; `logs/commit_084.txt` (mensagem, fora do git).
- Arquivos alterados (com resumo da mudança em uma linha cada): nenhum.
- Arquivos preservados literalmente na área afetada: todos (nada foi aplicado das seções 10.1 a 10.8).
- Script de verificação (o gate): não rodado (nenhum código mudou). Último gate registrado: `1031 passed, 5 deselected in 26.62s` (`logs/verificar_ultimo.txt`).
- Comandos executados: `claude --version`, `claude --help`, `cat` das configurações, `pmset -g batt/assertions`, `curl` às portas 11434/11435, `porteiro status`, `git ls-remote` (leitura), `git status`, `git ls-files`, `pgrep`, e dois `claude -p` (Haiku, US$ 0,006 cada): leitura de arquivo com a trava ligada e `/executar 999`.
- Manifesto do commit: ver abaixo, "Comando para commitar".
- Pendências e decisões que ficaram abertas: aprovar as seções 10.1–10.7; aprovar a lista de permissões da série (B3); ligar na tomada; commitar os 4 briefs.
- Resumo, Doing, Backlog e Done do `docs/PLAN.md` atualizados: não (investigação; rascunho na seção 10.6).

Nenhuma saída de comando foi omitida nas provas acima; os itens marcados "não conferido" não foram afirmados.

## Lacunas

| # | Lacuna | Destino | Impacto |
|---|---|---|---|
| 1 | Bloqueio da trava dentro do `claude -p` (código 2) provado só fora do headless; a execução da trava no headless está provada | nenhum | nice |
| 2 | Código de saída do `claude -p` ao estourar `--max-turns`, `--max-budget-usd` ou o limite da assinatura: não medido | backlog | degrada |
| 3 | Uma execução completa de `/executar` em `dontAsk` com a lista própria da série: só dá para provar rodando um brief (ensaio) | backlog | degrada |
| 4 | Limite da janela da assinatura Max para quatro execuções seguidas (82 e 83 em Opus): não há comando que leia isso | decisão | degrada |
| 5 | `scripts/executar_serie.sh` e `.claude/serie.settings.json` ainda não existem | backlog | degrada |
| 6 | Manifesto sem relatório/PLAN/brief e `agente_lacunas.py` alterando o PLAN depois do commit deixam a árvore suja entre briefs | backlog | degrada |
| 7 | `git worktree list` (leitura) é bloqueado pela trava | backlog | nice |
| 8 | AGENTS §12 e ARQUITETURA §11 divergem do estado real (docs versionados; gate rodado pelo executor) | backlog | degrada |
