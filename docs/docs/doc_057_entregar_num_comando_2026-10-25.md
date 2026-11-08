# DOC 057 — entregar num comando (relatório do brief 057)

## RELATÓRIO FINAL
- Brief executado: 057 — entregar num comando só. Gate de dependência: `main` em `acb2a67` (conferido com `git log`).
- Arquivos criados: `scripts/agente_entregar.sh`, `.claude/settings.json`, `.claude/hooks/guarda_comando.py`, `tests/test_guarda_comando.py`, `tests/test_agente_entregar.py`, este relatório, `logs/commit_057.txt`, `logs/arquivos_057.txt`.
- Arquivos alterados (uma linha cada):
  - `scripts/verificar.sh`: saída completa em `logs/verificar_ultimo.txt`; na tela "ok"/"falhou" por etapa; numa falha, só o útil; mesmo código de saída; ainda para na primeira etapa que falha.
  - `scripts/commitar.sh`: `SEM_PERGUNTA=1` pula o "Commitar? [S/n]"; sem a variável, nada muda.
  - `.gitignore`: `/.claude/` virou `/.claude/settings.local.json` e `/.claude/estado/`.
  - `pyproject.toml`: marcador `llm_real`; `addopts = "-m 'not rede_real and not llm_real'"`.
  - `tests/test_extrator.py`: marcador `llm_real` no teste que chama o Ollama real.
  - `tests/test_llm_fumaca.py`: **fora da lista do brief**, mas o item 3.5 manda marcar todo teste que chame o Ollama real; os 3 testes do módulo chamam (`ClienteOllama` com `httpx.Client` real, `skipif` por `/api/tags`). Marcado no `pytestmark` do módulo.
  - `AGENTS.md`: §5 (entrega por `!scripts/agente_entregar.sh`, manifesto, trava), §6 (teste direcionado permitido, marcador `llm_real`), §8 (terceira linha da resposta final literal; as linhas do bloco do relatório que falavam em "comando pronto para colar" e em "git add" passaram a citar o gate e o manifesto).
  - `docs/ARQUITETURA.md` §2: `agente_entregar.sh` e `.claude/` na árvore (fora do git).
  - `docs/PLAN.md`: Resumo e Doing com o 057 (fora do git).
- Arquivos preservados literalmente na área afetada: `config/`, todo `agente_nw/`, os outros testes, `scripts/instalar_macos.sh`, `scripts/migracoes/`, o restante do `AGENTS.md`.
- Script de verificação: `scripts/verificar.sh`. Sidarta roda pela entrega: `!scripts/agente_entregar.sh`.
- Comandos executados: leitura (`ls`, `grep`, `git status/diff/log`), `bash -n` nos dois scripts, `pytest tests/test_guarda_comando.py tests/test_agente_entregar.py` (direcionado, permitido pelo brief), `pytest tests/test_extrator.py tests/test_llm_fumaca.py` (só coleta: 4 desselecionados, nenhuma chamada ao Ollama), `git check-ignore`. Nenhum git de escrita, nem o gate.
- Manifesto do commit: `logs/arquivos_057.txt` (12 arquivos) e `logs/commit_057.txt`. A lista bate com o `git status --porcelain -uall` (comparada com `diff`, saída vazia).
- Pendências e decisões que ficaram abertas: ver "Lacunas".
- Resumo, Doing, Backlog e Done do `docs/PLAN.md` atualizados: sim (057 em Doing; o hash entra quando houver commit)

## Conferências da seção 7 (saída)

```
1. echo '{"tool_input":{"command":"git commit -m x"},...}' | python3 .claude/hooks/guarda_comando.py
   Bloqueado: git de escrita é de Sidarta (AGENTS §5): deixe o manifesto em logs/ e termine com !scripts/agente_entregar.sh
   exit=2
2. o mesmo com "git status"
   exit=0   (sem saída)
3. .venv/bin/pytest tests/test_guarda_comando.py tests/test_agente_entregar.py -q
   .....................................................                    [100%]
   53 passed in 3.14s
4. NÃO RODADO pelo executor: ver Lacuna 1.
5. git check-ignore -v .claude/settings.json            → sem saída, rc=1 (não ignorado)
   git check-ignore -v config/local.yaml dados/agente.db logs saidas docs/PLAN.md
   .gitignore:19:config/local.yaml  config/local.yaml
   .gitignore:9:/dados/             dados/agente.db
   .gitignore:12:/logs/             logs
   .gitignore:10:/saidas/           saidas
   .gitignore:22:docs/*             docs/PLAN.md
```

Prova de que a trava está viva nesta sessão: ao tentar `scripts/agente_entregar.sh --simular 057` pelo meu Bash, o hook bloqueou o comando ("a suíte e o gate são de Sidarta").

## Lacunas

1. **Contradição no brief, critério 4.** O 3.6 manda bloquear `scripts/agente_entregar.sh` sem exceção; o critério 4 manda o executor rodar `scripts/agente_entregar.sh --simular 057`. A trava barrou o comando e não a contornei. A simulação está coberta por `test_simular_nao_toca_no_git_nem_roda_o_gate` (passou). Para fechar o critério: Sidarta roda `!scripts/agente_entregar.sh --simular 057` e confere os 7 passos. **Decisão de Sidarta:** se quiser que o executor possa simular, é preciso liberar `--simular` no hook e tirar `Bash(scripts/agente_entregar.sh:*)` do `deny` do `settings.json` (um `deny` não aceita exceção). Não fiz.
2. **O gate novo nunca rodou de verdade.** Escrevi `verificar.sh` sem rodá-lo (só `bash -n`), e não rodei `ruff format --check` nos arquivos novos (`.claude/hooks/guarda_comando.py`, os dois testes), pois o ruff é do gate. O ruff passa a olhar `.claude/` agora que ele não está mais ignorado. Verifiquei só o limite de 110 colunas. Se o gate reclamar de formatação, o ajuste é de uma linha.
3. **`AGENTS.md` §8, exemplo antigo.** O texto ainda cita `agente_nw listas ver --rede instagram` como algo que o executor roda; a trava agora bloqueia `listas`, como o brief manda. Não mudei esse exemplo (fora do escopo do brief). Fica para Sidarta decidir.
4. **Desvio pequeno do passo 6.** Se o push falhar, o manifesto também é renomeado para `entregue_*` (o commit já existe). Sem isso, reexecutar daria "nenhum arquivo da lista tem alteração". A mensagem diz: `commit <hash> feito localmente; falhou só o envio. Rode: !git push`.
5. **Limites da trava** (por desenho, texto simples do comando): `python -c "sqlite3.connect('dados/agente.db')"` e comandos montados dinamicamente passam; `pytest -m llm_real` sem caminho de arquivo é bloqueado (só Sidarta roda); corpo de heredoc é ignorado. Falha de leitura do JSON do hook deixa passar, para não travar a sessão.
6. `git rm`, `git mv`, `git pull`, `git cherry-pick`, `git revert`, `git switch`, `git am` também são bloqueados (além da lista do brief); `git fetch`, `git branch` sem `-d/-D/-m/-M` e `git tag` passam.
7. O Bash do macOS é o 3.2: usei só construções compatíveis (arrays, `[[ ]]`, `< <(...)`). Os testes rodam com o `bash` do sistema.

## Lacunas

| # | Lacuna | Destino | Impacto |
|---|---|---|---|
| 1 | Contradição do brief entre bloquear `agente_entregar.sh` e rodá-lo com `--simular`: superada no 058, que liberou o script ao executor | nenhum | nice |
| 2 | O gate novo (`verificar.sh`) não tinha rodado de verdade: rodou verde na entrega do 057 | nenhum | nice |
| 3 | AGENTS §8 ainda cita `agente_nw listas ver --rede instagram` como algo que o executor roda, e a trava bloqueia `listas`; Sidarta decide se o executor pode rodar `listas ver` (só lê o cache local) ou se o exemplo sai do §8 | decisão | degrada |
| 4 | Se o push falhar, o manifesto também é renomeado para `entregue_*` (o commit já existe); a mensagem manda rodar `git push` | nenhum | nice |
| 5 | A trava lê só o texto do comando: `python -c "sqlite3.connect('dados/agente.db')"` e comandos montados dinamicamente passam; `pytest -m llm_real` sem arquivo é bloqueado; corpo de heredoc é ignorado | dívida | nice |
| 6 | A trava bloqueia também `git rm`, `mv`, `pull`, `cherry-pick`, `revert`, `switch` e `am`, além da lista do brief; `fetch`, `branch` sem `-d/-D/-m/-M` e `tag` passam | nenhum | nice |
| 7 | Os scripts usam só construções do Bash 3.2 do macOS | nenhum | nice |
