# Proposta de evolução — agente_nw (agente de relacionamento)

**Data:** 2026-10-24 · **Tipo:** proposta para crítica neste repositório · **Origem:** leitura direta do repositório em 22–24/10/2026, mais o resultado do brief de avaliação de skills (`docs/docs/doc_051_avaliar_skills_claude_2026-10-23.md`, com leitura do repositório real) e dos DOCs anteriores citados no texto. Nada aqui está aplicado; nenhum arquivo deste repositório foi alterado por esta proposta além da gravação deste documento.

## 1. Para que serve este documento

Reunir, num lugar só, o que se propõe mudar neste repositório em três planos — processo de desenvolvimento com Claude, tecnologia e skills — com a justificativa e o efeito esperado em token e em velocidade, para que a crítica aconteça aqui, com o contexto deste projeto, e não em conversa. Cada afirmação sobre o estado atual cita o arquivo; cada número de token diz como foi estimado. O que não está decidido está marcado como tal na seção 8.

## 2. Estado lido

241 arquivos `.py`, 125–127 de teste. `AGENTS.md` com 138 linhas (13.627 caracteres) — o mais curto dos sete. Python 3.12, Flask, `httpx`, Pydantic v2 (`frozen=True` nos contratos), SQLite com `sqlite-vec`, Ollama local, extensão Chrome manifest v3; `ruff`/`mypy --strict`/`pytest` dentro do `.venv` gerido por `uv`, sempre pelo usuário via `scripts/verificar.sh`. **Sem `uv.lock` nem lockfile algum** (`pyproject.toml` com `setuptools`, versões soltas). `.claude/` vazio e no `.gitignore`; sem `settings.json` — cada leitura pede permissão. Frente E1 (ciclo diário via launchd) com numeração própria e briefs sem prefixo até 050; os três últimos (048–050) são decisões de produto. Busca de notícias por `feedparser`+`trafilatura`, sem chave, por decisão do brief 045; navegador automatizado abandonado no brief 044. `agente_nw/perfil/normalizacao.py` existe. Token da ponte (`agente_nw/ponte/servidor.py:54`) não está em campo Pydantic nem em log. Dado real: perfis de pessoas.

## 3. O processo proposto (igual nos sete repositórios; aqui, o que vale para este)

**Arquivos de regra.** Três arquivos comuns ficam em `~/github/`, fora de qualquer repositório, escritos uma vez:
`~/github/CLAUDE.md` (13 regras que valem para as duas sessões, mais a linha `@CODE.md`), `~/github/CODE.md` (procedimento da sessão no Claude Code) e `~/github/APP.md` (procedimento da sessão no Claude App). O Claude Code carrega `CLAUDE.md` de todas as pastas acima da pasta de trabalho, então o arquivo entra sozinho em qualquer repositório e em qualquer worktree abaixo de `~/github`; a sessão no App lê o mesmo arquivo pela pasta conectada. Neste repositório fica só um `CLAUDE.md` curto com o que é específico daqui (seção 3.1) e um arquivo de configuração lido por scripts e hooks, nunca pelo modelo (seção 3.2). O `AGENTS.md` atual é **arquivado** em `docs/_archive/` quando a migração acontecer — não é apagado, e nada disso acontece antes de o piloto no pandora_96 completar cinco tarefas.

**As 13 regras comuns** (já estão em uso no pandora_96): papel dado pela ferramenta; modelo nomeado pelo brief; brief com Objetivo, Arquivos-alvo, Aceite, Passos e Recomendação de execução; DOC com Achado, Decisão, Lacunas e Gate; divergência → parar e registrar; só tocar arquivos-alvo; documentos nunca commitados; todo `.md` entregue na aba Saídas com caminho próprio; ler antes e reler depois de escrever; dado real só sob ordem explícita; resposta primeiro, comando em bloco, código de tarefa com descrição; sem resultado colado não se escreve que passou; o arquivo do repositório prevalece sobre o comum.

**Mecanismos no lugar de texto.** Três hooks de comando no `.claude/settings.json` (idênticos em todos os repos): `PreToolUse` em `Bash` bloqueia `git commit|merge|push|rebase|reset|stash|branch -D|worktree remove` e, conforme a configuração, `ruff`/`mypy`/`pytest` completos; `PostToolUse` em `Edit|Write` roda lint no arquivo editado quando a configuração permite; `Stop` roda a trava de escopo (arquivo fora dos Arquivos-alvo impede o encerramento) e gera o relatório mecânico no DOC. Nenhum hook de prompt ou de agente: esses chamam o modelo e gastam token. Todo hook é silencioso quando passa — só a falha chega ao modelo.

**Scripts.** Sete scripts com o nome do projeto (`<projeto>_doing.sh`, `_scope_gate.sh`, `_gate.sh`, `_fechar.sh`, `_entregar.sh`, `_relatorio_mecanico.sh`, `_lacunas.sh`), invólucros de uma linha sobre um código único em `~/github/_comum/bin/`, parametrizado pela configuração. Um bug corrigido corrige nos sete.

**Worktree e entrega.** Worktree por frente (repositório com várias frentes) ou por serviço (frente única). Um serviço é o conjunto de briefs que entrega algo que funciona. `fechar` por brief faz só DOC e linha no CONTEXT, sem merge. `entregar` por serviço faz numa chamada, pelo usuário: gate completo, um commit, merge em `main`, push, remoção da worktree, ✅ nas linhas de todos os briefs do serviço. Burocracia de git uma vez por serviço, nunca por brief. `<projeto>_doing.sh start <brief>` descobre a frente pelo prefixo do nome do brief, cria ou entra na worktree da frente e registra a tarefa ativa — o modelo não decide frente, branch nem worktree.

**Quem roda o quê.** Sessão no Claude Code: executa o brief dentro da worktree, escreve código só nos arquivos-alvo, roda teste direcionado onde a configuração permite, escreve o DOC. Usuário: gate completo e `entregar`. Sessão no Claude App: brief, lacunas para o backlog, fechamento. O modelo nunca roda gate completo (saída longa e quem é avaliado não se avalia) nem git de escrita (irreversível, e o momento do merge é decisão de produto).

### 3.1 O que fica no `CLAUDE.md` deste repositório (delta, até 15 linhas)

- Dado real: o banco de perfis e qualquer exportação; nenhuma skill ou subagente lê perfis, só código.
- Frente única; `E1` aceito como prefixo de brief.
- `git add -A` e `git commit` nunca pelo executor (AGENTS §5–6), garantidos por hook.

### 3.2 Configuração deste repositório (`.claude/projeto.env`, lida por scripts e hooks)

```
PROJETO=agente_nw
FRENTES=unica E1
WORKTREE=1
WORKTREE_DIR=../agente_nw-<servico>
LINT_POR_ARQUIVO=1
TESTE_DIRECIONADO=1
GATE=scripts/verificar.sh
DADO_REAL=<banco de perfis>.db
```

`FRENTES="unica E1"` faz o `doing.sh` aceitar `brief_E1_NNN` e `brief_NNN` sem criar duas worktrees permanentes.

## 4. Tecnologias a adotar, com justificativa

1. **`uv lock`** — não há lockfile; sem ele não há build reprodutível nem auditoria de dependência (`supply-chain-risk-auditor` foi descartada por isso). Um comando, nenhuma mudança de código.
2. **`.claude/settings.json` com `permissions.allow`** gerado por `claude-settings-audit` — o atrito mais citado no DOC 051: cada leitura pede confirmação.
3. **Hook `PreToolUse` de git** escrito à mão, com `git add -A`, `git add .`, `git commit`, `merge`, `push` bloqueados — o DOC 051 propôs adaptar `git-guardrails-claude-code`; escrever direto é menor.
4. **`hypothesis`** em `agente_nw/perfil/normalizacao.py` e `agente_nw/coleta/rss/canonicalizar.py` — normalização de nome e data é função pura, o caso de teste por propriedade.
5. **Auditoria preventiva de serialização** nos modelos Pydantic congelados (`nucleo/modelos/*.py`) com `secret-serialization` — nenhum vazamento ativo hoje; vale antes de um campo de token entrar num contrato.
6. **Continuar sem chave e sem navegador** na busca de notícias — `firecrawl` e `agent-browser` contrariam os briefs 044/045.

## 5. Skills

**Comuns a todos os repositórios** — `grilling` e `to-questionnaire` (mattpocock/skills, 2–3 KB cada, invocação manual) instaladas uma vez em `~/.claude/skills/`, para a sessão no App; `claude-settings-audit` (getsentry/skills) rodada uma vez por repositório para gerar a lista `permissions.allow` de comandos somente-leitura, revisada item a item antes de colar; `skill-scanner` (getsentry/skills) antes de copiar qualquer `SKILL.md` de terceiro; `claude-code-setup` (marketplace oficial) só como contraprova desta lista, descartando na hora qualquer sugestão de hook de lint/teste automático ou de liberar `git commit`. **Fora em todos**: `hookify` (quatro hooks sempre ligados, ~176 KB), `security-guidance` (revisão por LLM a cada edição), `commit`/`commit-commands` (commitam sozinhos), `modern-python` (troca mypy por `ty`), `superpowers` inteiro (`finishing-a-development-branch` faz merge por conta própria), `turso-db`, `firecrawl`/`agent-browser` (Node e serviço pago).

**Adotar neste repositório**
- `grilling` — o DOC 051 adotou: os briefs 048–050 são decisões de produto, o caso de uso exato; 2 KB, sem dependência.
- `to-questionnaire` — adotado pelo DOC 051.
- `claude-settings-audit` — adotado; reconhece `pyproject.toml` e só propõe leitura.

**Testar em um brief antes de adotar**
- `property-based-testing` — depende de `hypothesis` (dependência de dev).
- `secret-serialization` — `nucleo/modelos/*.py` e `ponte/`.
- `claude-code-setup` — contraprova, filtrando sugestões de hook de lint/teste e de liberar `git commit` (o DOC 051 leu as referências dela e são enviesadas para stack web/JS).
- `audit-context-building`, `differential-review` (trailofbits) — só leitura; úteis numa base de 241 arquivos antes de auditoria pontual.
- `semgrep` (parte do `static-analysis`) — só a parte Semgrep, local; CodeQL é pesado demais para repo solo.
- `webapp-testing` — só se o console Flask ganhar teste de navegador (dependência `playwright` de dev); não serve para a extensão Chrome.
- `serena`, `context7` — brief próprio de MCP cada.

**Não adotar, com o motivo**
- `firecrawl`, `agent-browser` — Node + serviço pago; contrariam 044/045.
- `supply-chain-risk-auditor` — até existir lockfile (item 1 da seção 4 resolve).
- `hookify` — ~176 KB e quatro hooks permanentes; o exemplo oficial (gate no `Stop`) contraria o AGENTS §6.
- `commit`/`commit-commands`, `pr-review-toolkit`, `code-review` oficial, `modern-python`, `mcp-builder`.
- `agents-md` — o AGENTS já tem 138 linhas; nada a encolher.

## 6. Efeito estimado em token e velocidade

Base da estimativa: tamanho real dos arquivos em caracteres, dividido por 4 (≈1 token por 4 caracteres em português). Não é medição de sessão; a medição vem de `/cost` ao fim de cada tarefa do piloto, comparada com tarefas anteriores do mesmo repositório.

| O que | Hoje | Com a proposta | Base |
|---|---|---|---|
| Regras carregadas por sessão no Code | ~3,4 mil (AGENTS.md) | ~2,3 mil | 13.627 caracteres |
| CONTEXT | não existe arquivo de CONTEXT neste repositório | `doing.sh` sobre o arquivo que a configuração apontar | — |
| Relatório mecânico no DOC | ~1–2 mil | 0 (hook `Stop`) | tamanho típico |
| Prompts de permissão | um por comando de leitura | lista `permissions.allow` | `.claude/` vazio hoje |

**Velocidade.** Aqui o ganho é atrito, não token: permissões por comando e ausência de lockfile. O AGENTS já é curto; a migração para o processo comum muda pouco o custo fixo e muito a fluidez.

## 7. O que muda de comportamento

- Nada muda em quem roda `scripts/verificar.sh` (você).
- Git de escrita passa de regra de texto (§5–6) para hook.
- Worktree por serviço; `E1` continua como prefixo.
- `docs/docs/` passa a existir (criado pela avaliação de skills).

## 8. Riscos e pontos abertos para crítica

- `uv lock` pode travar versões diferentes das que estão instaladas no `.venv` hoje; rodar `scripts/verificar.sh` logo depois.
- A extensão Chrome (JS) fica fora de todo lint e teste do processo; nenhuma skill avaliada cobre manifest v3.
- A ponte com o Mac é uma VM Linux: o DOC 051 mediu `gh` ausente e `jq` presente na VM, não no seu terminal.

## 9. Sequência proposta

1. `uv lock` + `scripts/verificar.sh`.
2. Instalar `grilling` e `to-questionnaire` em `~/.claude/skills/`; rodar `claude-settings-audit` e aprovar a lista em `.claude/settings.json`.
3. Hook `PreToolUse` de git no `settings.json`.
4. Brief de código: `hypothesis` em `normalizacao.py` e `canonicalizar.py`.
5. Migração para o processo comum (quarto da fila).

## 10. O que este documento não decide

A ordem entre repositórios (proposta: pandora_96 → trf6 → cervello → agente_nw → sergio → lex_hub → advogada_parceira_free, cinco tarefas em cada antes do próximo); se o commit dentro da worktree é um por brief ou um por serviço; preço por token dos modelos (não verificado nesta rodada — conferir a tabela atual antes de contar com uma razão Sonnet/Opus); e qualquer mudança no produto que não esteja na seção 4 — essas continuam saindo de brief próprio.
