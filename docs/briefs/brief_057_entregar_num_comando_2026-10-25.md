# Brief 057 — Entregar num comando só: Sidarta para de copiar comandos

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Conjunto:** nenhum (brief isolado, direto na `main`)
**Arquivos-alvo:** `scripts/agente_entregar.sh` (novo), `scripts/verificar.sh`, `scripts/commitar.sh`, `.claude/settings.json` (novo), `.claude/hooks/guarda_comando.py` (novo), `.gitignore`, `pyproject.toml` (só o marcador de teste), `tests/test_extrator.py` (só o marcador), `tests/test_guarda_comando.py` (novo), `tests/test_agente_entregar.py` (novo), `AGENTS.md` (§5, §6, §8), `docs/docs/doc_057_entregar_num_comando_2026-10-25.md`, `logs/commit_057.txt`, `logs/arquivos_057.txt`
**Seções a ler:** AGENTS §4 a §8; ARQUITETURA §2 (estrutura de `scripts/`)
**Modelo:** Sonnet
**Teste de aceite:** `tests/test_guarda_comando.py` e `tests/test_agente_entregar.py`, mais as conferências da seção 7 que o executor roda sozinho
**Depende de:** nada; `main` em `acb2a67` ou depois. **Vem antes do 056.**
**Data:** 2026-10-25

---

## 1. Objetivo em uma frase

Ao fim de qualquer brief, Sidarta digita **uma linha** dentro do Claude Code (`!scripts/agente_entregar.sh`) e ela faz o gate, o commit e o push. Sem copiar comando, sem lista de arquivos, sem pergunta S/n. O executor continua sem rodar git nem a suíte, agora por trava automática e não só por texto.

---

## 2. Por que

No brief 055, o próprio executor escreveu a regra "a resposta final termina com o comando que Sidarta roda" e, na mesma sessão, terminou dizendo "o push é só seu" sem dar o comando. Regra em texto falha. Hoje, para entregar um brief, Sidarta copia três comandos longos (`verificar.sh`, `commitar.sh` com 16 caminhos, `git push`), e o `commitar.sh` pergunta S/n. Por isso ele não funciona com `!` dentro do Claude Code: a pergunta não tem como ser respondida e o script aborta.

Além disso, o gate falhou em 25/10 por um motivo alheio ao código: `test_extrator.py::test_extracao_real_produz_tags_e_campos_esperados` chama o Ollama real e esgotou o tempo com o modelo frio. Um gate que depende de o Ollama estar quente obriga Sidarta a investigar falha que não é falha.

---

## 3. Decisões

**3.1. Manifesto do commit: o executor deixa pronto, sem rodar git.** Ao fechar cada brief, o executor grava dois arquivos:
- `logs/commit_<NNN>.txt` — a mensagem do commit (já é regra desde o 055);
- `logs/arquivos_<NNN>.txt` — um caminho por linha, só os arquivos rastreados ou novos que entram no commit.

**3.2. `scripts/agente_entregar.sh [NNN]`.** Sem argumento, usa o maior NNN que tiver os dois arquivos em `logs/`. Faz, em ordem, e **para no primeiro erro**:
1. Confere que os dois arquivos do manifesto existem e não estão vazios, e que cada caminho listado existe.
2. Confere o `git status --porcelain`. Arquivo alterado ou novo **fora** da lista é erro: imprime os caminhos e para, sem tocar no git.
3. Roda `scripts/verificar.sh` (item 3.3). Se falhar, imprime o resumo e para.
4. Roda `scripts/commitar.sh` em modo sem pergunta (item 3.4), com a mensagem e a lista do manifesto.
5. Roda `git push`. Se falhar (rede, credencial), imprime a mensagem do git e diz que o commit local já foi feito e falta só o envio.
6. Renomeia o manifesto para `logs/entregue_<NNN>_commit.txt` e `logs/entregue_<NNN>_arquivos.txt`, para não ser entregue duas vezes.
7. Imprime **uma linha** final: `✓ brief NNN: commit <hash curto>, enviado ao GitHub` (ou o motivo da parada).

Opção `--simular`: mostra o que faria em cada passo, sem rodar o gate nem tocar no git.

A saída inteira cabe em até 10 linhas quando tudo passa. O detalhe vai para `logs/entregar_ultimo.txt`.

**3.3. `scripts/verificar.sh` grava e resume.** A saída completa de ruff, format, mypy e pytest vai para `logs/verificar_ultimo.txt`. Na tela ficam, para cada etapa, "ok" ou "falhou". Se o pytest falhar, aparecem só a linha do resumo e os nomes dos testes que falharam. O código de saída continua o mesmo: diferente de zero em qualquer falha. Rodado sozinho no terminal, o comportamento visível muda só nisso.

**3.4. `scripts/commitar.sh` ganha o modo sem pergunta.** Com a variável `SEM_PERGUNTA=1`, pula o "Commitar? [S/n]". Sem ela, nada muda. Continua sem push, sem amend, sem `--no-verify`, com o add arquivo por arquivo.

**3.5. Teste que chama o Ollama real ganha marcador.** `test_extracao_real_produz_tags_e_campos_esperados` recebe o marcador `llm_real`, declarado no `pyproject.toml` ao lado do `rede_real`, e o `addopts` passa a ser `-m 'not rede_real and not llm_real'`. O teste continua existindo e roda com `pytest -m llm_real`. Nenhum outro teste muda. Se a busca encontrar outro teste que chame o Ollama real (procure `ClienteOllama(` com `httpx.Client(` real nos testes), marque-o também e liste-o no relatório.

**3.6. A trava: `.claude/hooks/guarda_comando.py`**, hook `PreToolUse` para a ferramenta `Bash`. Em Python, só biblioteca padrão: lê o JSON da entrada padrão e olha `tool_input.command` e `cwd`. Ela vale para os comandos **do modelo**. O que Sidarta digita com `!` não passa por ela, e por isso o `!scripts/agente_entregar.sh` funciona.
- **Bloqueia** (código de saída 2, motivo em uma linha):
  - git de escrita: `add`, `commit`, `push`, `merge`, `rebase`, `reset`, `checkout` de arquivos, `restore`, `clean`, `stash`, `branch -D`, `worktree`;
  - a suíte: `pytest` sem caminho de arquivo, `mypy`, `ruff format`, `scripts/verificar.sh`, `scripts/commitar.sh`, `scripts/agente_entregar.sh`;
  - `sqlite3` com `agente.db`;
  - os subcomandos do programa que leem rede social: `ler-rede-social`, `listas`, `pedir`, `extensao`.
- **Pede confirmação a Sidarta** (`permissionDecision: "ask"`): qualquer outro subcomando de `agente_nw` rodado na pasta principal, porque ali ele usa o banco real. Exceções que passam direto: `verificar-ambiente`, `copiar-banco` e `--help`.
- **Deixa passar** todo o resto, em silêncio.

Motivo de cada bloqueio, sempre com a regra do AGENTS: por exemplo, "git de escrita é de Sidarta (AGENTS §5): deixe o manifesto em logs/ e termine com !scripts/agente_entregar.sh".

**3.7. `.claude/settings.json`, versionado.**
- `permissions.allow` só para leitura: `ls`, `cat`, `head`, `tail`, `wc`, `grep`, `rg`, `find`, `git status`, `git diff`, `git log`, `git show`, e `pytest` com caminho de arquivo de teste. Este último é o teste direcionado: liberado, desde que nunca seja a suíte inteira.
- `permissions.deny` repete os bloqueios de git e de suíte como segunda barreira.
- `hooks.PreToolUse` aponta para `python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/guarda_comando.py"`.

**3.8. `.gitignore`.** A linha `/.claude/` vira duas: `/.claude/settings.local.json` e `/.claude/estado/`. Assim a trava e a configuração entram no git. Conferir com `git check-ignore -v` que `config/local.yaml`, `dados/`, `logs/`, `saidas/` e `docs/*` continuam fora.

**3.9. `AGENTS.md`, só três trechos:**
- **§5:** "Sidarta entrega com `!scripts/agente_entregar.sh` dentro do Claude Code: gate, commit e push numa linha. O executor deixa o manifesto (`logs/commit_<NNN>.txt` e `logs/arquivos_<NNN>.txt`) e nunca roda git; a trava `.claude/hooks/guarda_comando.py` impede."
- **§6:** "Teste direcionado (`pytest tests/test_x.py`) é permitido ao executor; a suíte inteira e o gate, não. Testes que chamam o Ollama real levam o marcador `llm_real` e ficam fora do gate."
- **§8:** a terceira linha da resposta final é **sempre, literalmente**: `Para entregar: !scripts/agente_entregar.sh`.

> **Decisão de Sidarta embutida neste brief:** o teste direcionado passa a ser permitido ao executor. Isso evita que Sidarta rode teste a teste. Se preferir manter a proibição, remova `pytest` com caminho do `allow` e a frase do §6 antes de executar.

---

## 4. Testes

- `tests/test_guarda_comando.py`: alimenta o hook com JSON de exemplo e confere o código de saída e a decisão para:
  - `git commit -m x` → bloqueado;
  - `git status` → passa;
  - `pytest` → bloqueado; `pytest tests/test_x.py -q` → passa;
  - `scripts/verificar.sh` → bloqueado;
  - `sqlite3 dados/agente.db` → bloqueado;
  - `agente_nw pedir "..."` → bloqueado;
  - `agente_nw ficha 3` com `cwd` na pasta principal → `ask`;
  - `agente_nw copiar-banco` → passa;
  - `ls docs` → passa.
- `tests/test_agente_entregar.py`: num repositório git temporário (`tmp_path`, `git init`), com `verificar.sh` e `git push` substituídos por executáveis falsos no `PATH`:
  - manifesto completo → commit feito, push chamado, manifesto renomeado, linha final com o hash;
  - arquivo fora da lista → para antes do gate, sem commit;
  - gate falhando → para, sem commit;
  - `--simular` → nenhum commit.

---

## 5. Fora de escopo

Skills `/iniciar` e `/encerrar`, worktree, troca de pip por `uv`, trava do banco no código, lint automático por arquivo, resumo do PLAN gerado por script. Cada um terá brief próprio.

---

## 6. Passos de execução

1. Ler as seções citadas e este brief.
2. Escrever os dois testes da seção 4.
3. `guarda_comando.py`, `settings.json`, `.gitignore`.
4. `verificar.sh`, `commitar.sh`, `agente_entregar.sh` (com `chmod +x`).
5. Marcador `llm_real` (item 3.5).
6. AGENTS §5, §6, §8.
7. Conferências da seção 7, com a saída colada no relatório.
8. Relatório `docs/docs/doc_057_entregar_num_comando_2026-10-25.md`, `logs/commit_057.txt`, `logs/arquivos_057.txt`, e as linhas Resumo, Doing e Done do PLAN.
9. Resposta final em três linhas; a terceira: `Para entregar: !scripts/agente_entregar.sh`.

---

## 7. Critérios de aceite

**Que o executor roda sozinho e cola no relatório** (nenhum é a suíte):
1. `echo '{"tool_input":{"command":"git commit -m x"},"cwd":"'$PWD'"}' | python3 .claude/hooks/guarda_comando.py; echo $?` → `2`.
2. O mesmo com `git status` → `0`, sem saída.
3. `pytest tests/test_guarda_comando.py tests/test_agente_entregar.py -q` → verdes. Este é o teste direcionado; se Sidarta vetar o item 3.9, ele passa a ser rodado por Sidarta.
4. `scripts/agente_entregar.sh --simular 057` → mostra os 7 passos sem tocar no git.
5. `git check-ignore -v .claude/settings.json` → não ignorado; `git check-ignore -v config/local.yaml dados/agente.db` → ignorados.

**De Sidarta, uma vez:**

6. Digitar `!scripts/agente_entregar.sh` no Claude Code. A entrega deste próprio brief é o teste real: gate verde (sem o teste do Ollama), commit do 057, push, uma linha final.
