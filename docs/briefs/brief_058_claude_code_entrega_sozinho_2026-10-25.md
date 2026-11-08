# Brief 058 — O Claude Code entrega sozinho: código, testes, commit, push e relatório

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Conjunto:** nenhum (brief isolado, direto na `main`)
**Arquivos-alvo:** `.claude/hooks/guarda_comando.py`, `.claude/settings.json`, `.claude/hooks/lint_arquivo.py` (novo), `.claude/skills/executar/SKILL.md` (novo), `scripts/agente_entregar.sh`, `tests/test_guarda_comando.py`, `tests/test_lint_arquivo.py` (novo), `AGENTS.md` (§5, §6, §8, §10), `docs/docs/doc_058_claude_code_entrega_sozinho_2026-10-25.md`, `logs/commit_058.txt`, `logs/arquivos_058.txt`
**Seções a ler:** AGENTS §4 a §10; o relatório do brief 057 (`docs/docs/doc_057_entregar_num_comando_2026-10-25.md`)
**Modelo:** Sonnet
**Teste de aceite:** este brief e o 057 entregues pelo próprio executor, commit e push incluídos, sem nenhum comando de Sidarta
**Depende de:** o trabalho do 057, que está escrito e sem commit; o passo 2 o entrega
**Data:** 2026-10-25

---

## 1. Objetivo em uma frase

Ao executar um brief, o Claude Code escreve o código e os testes, roda o gate, commita, faz o push e escreve o relatório, sozinho. Sidarta só recebe o que exige a presença dele: teste com pessoa real, login em rede social, decisão de produto.

---

## 2. Decisão de Sidarta (25/10), que este brief aplica

> "Quero que o Claude Code gere os códigos, teste os códigos, faça git, merge de forma automática e gere um relatório. Eu só devo receber comandos que não podem ser executados de forma automática."

Isso **substitui** as regras antigas "Git nunca roda de forma autônoma" e "o executor não roda a suíte". O que garante a segurança deixa de ser a mão de Sidarta e passa a ser o mecanismo:
- **Commit só com gate verde.** O `agente_entregar.sh` para antes do commit se ruff, mypy ou pytest falharem.
- **Commit só dos arquivos do manifesto.** Arquivo fora da lista faz a entrega parar.
- **Git direto continua travado.** `git commit`, `git push`, `reset`, `rebase`, `--force`, `branch -D` e `stash` escritos à mão pelo modelo continuam bloqueados pela trava. O único caminho para commitar é o script.
- **Banco real e rede social continuam travados.** São regra de produto, não de processo, e não mudam.

**Merge:** não há ramo nem worktree hoje, então o commit vai direto na `main` e não há merge a fazer. Quando a worktree for adotada, o `agente_entregar.sh` ganha o merge, em brief próprio.

---

## 3. O que muda

**3.1. Trava (`guarda_comando.py`).**
- **Passa a liberar para o modelo:** `scripts/agente_entregar.sh` (com ou sem `--simular` e número), `scripts/verificar.sh` e `pytest` em qualquer forma.
- **Continua bloqueando:** git de escrita digitado direto; `sqlite3` com `agente.db`; os subcomandos de rede social (`ler-rede-social`, `listas`, `pedir`, `extensao`); `rm -rf` fora de `logs/` e de pastas temporárias.
- **Continua pedindo confirmação:** outros subcomandos de `agente_nw` na pasta principal, porque usam o banco real.

Atualizar `tests/test_guarda_comando.py`.

**3.2. `settings.json`.** Tirar do `deny` o que a trava passa a liberar. Acrescentar o hook `PostToolUse` (item 3.3). Se o Claude Code não recarregar a configuração sozinho, registrar no relatório que a próxima sessão já abre com ela.

**3.3. Lint automático por arquivo (`lint_arquivo.py`, hook `PostToolUse` em `Edit|Write|MultiEdit`).** Depois de cada edição de `.py`, roda `.venv/bin/ruff format <arquivo>` e `.venv/bin/ruff check --fix <arquivo>`.
- Em silêncio quando passa.
- Quando sobra erro, no máximo 3 linhas: o caminho e o código do erro.

Assim o gate quase nunca falha por formatação. Escrever `tests/test_lint_arquivo.py`.

**3.4. `agente_entregar.sh`.**
- Já não pergunta nada; conferir que continua assim.
- Na falha do gate, devolve código de saída diferente de zero e as poucas linhas de resumo, para o executor corrigir e rodar de novo.
- No sucesso, mantém a linha final: `✓ brief NNN: commit <hash>, enviado ao GitHub`.

**3.5. Skill `/executar <NNN>` (`.claude/skills/executar/SKILL.md`).** Manual (`disable-model-invocation: true`), até 40 linhas. O corpo é o roteiro, nesta ordem:
1. Abrir `docs/briefs/brief_<NNN>_*.md`. Se não existir no disco, parar.
2. Ler o que o AGENTS §1 manda e as seções citadas no cabeçalho do brief.
3. Escrever o teste de aceite e os testes do brief **antes** do código.
4. Implementar só nos arquivos-alvo.
5. Rodar os testes do brief (`pytest tests/test_x.py -q`) até passarem.
6. Gravar o relatório `docs/docs/doc_<NNN>_*.md` (bloco do AGENTS §8), o manifesto (`logs/commit_<NNN>.txt` e `logs/arquivos_<NNN>.txt`) e as linhas Resumo, Doing e Done do PLAN.
7. Rodar `scripts/agente_entregar.sh <NNN>`. Se falhar, corrigir e rodar de novo, **no máximo 3 vezes**. Na terceira falha, parar e descrever no relatório o que falhou.
8. Resposta final em três linhas:
   - o caminho do relatório;
   - o que foi feito, com o hash do commit;
   - **"Nada para você."**, ou só o que exige Sidarta: teste com pessoa real, login, decisão de produto.

Comandos para Sidarta digitar nunca entram na resposta, exceto quando a entrega parou na terceira falha.

**3.6. `AGENTS.md`.**
- **§5:** substituir "Git nunca roda de forma autônoma. O executor prepara a lista…" por:

  > O executor commita e faz push ao fim de cada brief, exclusivamente por `scripts/agente_entregar.sh`, que só commita com o gate verde e só os arquivos do manifesto. Git de escrita digitado direto continua bloqueado pela trava `.claude/hooks/guarda_comando.py`.

  O resto da §5 fica: nunca `git add -A`, add arquivo por arquivo (feito pelo `commitar.sh`), trunk-based em `main`.
- **§6:** "Nunca rodam sozinhos: git, …, a suíte de testes" passa a "Nunca rodam sozinhos: leitura de rede social, alteração de ficha de contato, operação no banco real." Acrescentar: "O gate roda dentro do `agente_entregar.sh`, pelo executor."
- **§8:** a terceira linha da resposta final é "Nada para você." ou a pendência que exige Sidarta.
- **§10:** "Todo brief é executado com `/executar <NNN>`."

---

## 4. Passos de execução

1. Atualizar `guarda_comando.py` (3.1) e o seu teste. A trava relê o arquivo a cada comando, então a mudança vale na hora.
2. **Entregar o 057** com `scripts/agente_entregar.sh 057`. Se o gate falhar, corrigir e repetir (até 3 vezes). É o primeiro teste real do script.
3. `settings.json`, `lint_arquivo.py` e o seu teste, a skill `/executar`, o `agente_entregar.sh` (3.4) e o `AGENTS.md`.
4. Rodar os testes deste brief.
5. Relatório, manifesto e PLAN.
6. **Entregar o 058** com `scripts/agente_entregar.sh 058`.
7. Resposta final em três linhas, conforme 3.5.

---

## 5. Critérios de aceite

1. `git log --oneline -3` mostra o commit do 057 e o do 058, feitos pelo executor; `git status` está limpo; `git rev-list --count origin/main..HEAD` dá `0` (tudo enviado).
2. A trava ainda bloqueia `git commit -m x`, `git push --force`, `sqlite3 dados/agente.db` e `agente_nw pedir "…"` (saída do teste colada no relatório).
3. Editar um `.py` com erro de formatação deixa o arquivo formatado sem nenhuma mensagem (teste do hook).
4. A resposta final não traz nenhum comando para Sidarta.

---

## 6. Fora de escopo

Worktree e merge de ramo, troca de pip por `uv`, resumo do PLAN gerado por script e qualquer mudança de produto.
