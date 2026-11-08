# Brief 033 — Integração dos commits de hoje (briefs 031 e 032) com a versão atual do repositório

**Repositório:** `/Users/sidarta48/github/agente_nw` (MacBook Pro)
**Estado atual:** rebase interrompido com conflito em `AGENTS.md` (`git status` mostra `UU AGENTS.md`). O `main` local tinha 3 commits (`24848f2`, `fcb696d`, `0668a79`) feitos sobre uma base de 19/09 (`2b93ec8`, brief 010); o `origin/main` está 12 commits à frente (briefs 013 a 025, até `e9c0a39`).
**Data:** 2026-10-08

---

## 1. Objetivo em uma frase

Deixar o `main` do Pro igual ao `origin/main` mais o trabalho de hoje (perfil `pro48`, seleção de perfil por máquina, checagem de servidor Ollama por porta), com a suíte passando, sem reinstaurar nada que a arquitetura sob demanda (brief 016) removeu.

---

## 2. O que mudou no `origin/main` e invalida parte do trabalho de hoje

Lido em `git diff 2b93ec8 origin/main`:

- **Não existe mais LaunchAgent nenhum.** `scripts/launchd/` (plists do Ollama e do ciclo) e `scripts/rodar_ciclo.sh` foram apagados. `AGENTS.md` diz: "Ollama [...] subido pelo próprio usuário fora do aplicativo do Ollama" e "Agendamento: não existe". O `instalar_macos.sh` atual só faz `brew install ollama`, `ollama pull` e imprime a instrução para subir `ollama serve` à mão.
- **Tarefa de LLM nova:** `extrair_captura_rede_social` (brief 017), declarada no perfil `air16` de `config/llm_routing.yaml`. O validador criado no brief 031 exige as mesmas tarefas em todos os perfis — por isso `pro48` precisa dela.
- **`cli.py` ganhou** `preparar_cmd`, `ler_rede_social_cmd`, `_verificar_playwright_chromium`; `ciclo_cmd` e `_gerar_cartoes_cmd` saíram.
- **`AGENTS.md` foi reescrito** para a arquitetura sob demanda (seções 2, 3, 6 e 7).

Consequência: do brief 032, **cai** tudo que fala em "LaunchAgent do projeto" (comentário no plist, checagem de porta ocupada antes de instalar o plist, categoria "LaunchAgent do projeto" na classificação do servidor, parágrafo do `AGENTS.md` sobre máquina dedicada com LaunchAgent). **Fica** o que não depende disso: perfil por máquina, `ollama_url` por máquina, checagem por porta distinguindo Ollama.app de outra instância, e o item "Ollama responde" nomeando a instância.

---

## 3. Decisões

1. **Merge, não rebase.** `git rebase --abort` e depois `git merge origin/main`. Um único ponto de resolução, um commit de merge. Os três commits de hoje ficam intactos no histórico.
2. **`origin/main` é a base de verdade para tudo que é arquitetura.** Em qualquer dúvida de texto ou estrutura, prevalece a versão do `origin/main`; o trabalho de hoje entra como acréscimo, nunca reintroduzindo ciclo, agendamento ou LaunchAgent.
3. **`scripts/launchd/` continua apagado.** Conflito modify/delete do plist: resolver com `git rm`. O comentário XML do brief 032 morre com o arquivo.
4. **`instalar_macos.sh`: versão do `origin/main`**, sem o bloco de checagem de porta do brief 032 (ele falava em "instalar o LaunchAgent", que não existe). Acrescentar só duas linhas ao `echo` final: "Em máquina compartilhada com outros projetos (Pro), não suba outro servidor: aponte `ollama_url` em `config/local.yaml` para a instância já existente e defina `perfil_llm` (ver AGENTS.md)."
5. **`AGENTS.md`: texto do `origin/main` com o item Ollama substituído** por:

   > - Ollama para inferência local, subido pelo próprio usuário fora do aplicativo do Ollama (nunca o Ollama.app, nunca `brew services`), acessado pela `ollama_url` de `config/local.yaml` — por máquina. Modelo por tarefa vem do **perfil ativo** de `config/llm_routing.yaml`, escolhido por `perfil_llm` em `config/local.yaml` (ausente = `air16`): `air16` no Air (produção: `qwen3:4b` como único modelo de geração e julgamento, `qwen3:8b` só em `agente_nw calibrar-agrupamento`), `pro48` no Pro (desenvolvimento: `qwen2.5:14b`). Verificar com `ollama list` antes de sugerir download. `think: false` obrigatório em toda tarefa; o perfil pode omitir a chave do payload com `enviar_think: false`, para modelos sem modo de raciocínio. `bge-m3` para embeddings nos dois perfis. No Air, subir com `OLLAMA_MAX_LOADED_MODELS=2 OLLAMA_KEEP_ALIVE=30m ollama serve`. No Pro, **não subir servidor próprio**: `ollama_url` aponta para a instância compartilhada já existente (`http://127.0.0.1:11435`, mantida pelo `cervello`); nunca parar ou reiniciar essa instância a partir deste projeto.

   Manter a correção "claw" → "claw_planalto" se o trecho ainda existir no texto do `origin/main`; se o `origin/main` já não tiver a frase, nada a fazer.
6. **`config/llm_routing.yaml`:** manter o merge automático e acrescentar em `pro48`:
   `extrair_captura_rede_social: {modelo: qwen2.5:14b, num_ctx: 16384, temperature: 0.2, format: json, think: false}`.
7. **`cli.py`:** manter o merge automático (funções do `origin/main` + funções de hoje). Simplificar `_classificar_processo` para três categorias — `Ollama.app`, `outra instância`, `desconhecido` — removendo a categoria "LaunchAgent do projeto", a constante `ROTULO_LAUNCHAGENT_PROJETO` e `_rotulos_launchctl()` (conceito que não existe mais). O aviso continua só para `Ollama.app` na porta configurada. Ajustar `tests/test_cli_servidor_na_porta.py` para as três categorias.
8. **Nenhum servidor Ollama é parado, reiniciado ou substituído** durante a execução (mesma regra do brief 032).

---

## 4. Passos de execução

1. `git rebase --abort`. Confirmar que `git log --oneline -3` mostra `0668a79`, `fcb696d`, `24848f2` e que `git status` está limpo (exceto `scripts/migracoes/.gitkeep` e `_quarentena_outro_usuario_2026-10-08/`, que não entram).
2. `git merge origin/main`. Listar os conflitos reportados.
3. Resolver conforme a seção 3 (itens 3 a 7). Para o plist: `git rm scripts/launchd/br.agente_nw.ollama.plist`. Se `scripts/launchd/.gitkeep` ou `br.agente_nw.ciclo.plist` reaparecerem, `git rm` também.
4. `grep -rn "launchd\|LaunchAgent\|kickstart" AGENTS.md agente_nw scripts tests` — o resultado deve ser vazio.
5. `.venv/bin/ruff check .`, `.venv/bin/ruff format --check .`, `.venv/bin/mypy agente_nw`, `.venv/bin/pytest -q`. Tudo limpo, inclusive `tests/test_coleta_retomada.py` (a correção de data do commit `fcb696d` entra pelo merge).
6. `.venv/bin/agente_nw verificar-ambiente`: primeira linha `pro48 (definido em config/local.yaml)`, "Ollama responde" em `http://127.0.0.1:11435 — outra instância`, item do Playwright/Chromium presente, sem aviso de Ollama.app.
7. Commit do merge: `merge: integra briefs 031 e 032 à arquitetura sob demanda (origin/main)`. Não incluir `config/local.yaml` nem a pasta de quarentena.
8. `git push origin main`.

---

## 5. Critérios de aceite

- `git log --oneline origin/main..main` mostra os três commits de hoje mais o commit de merge; `git status` limpo.
- `grep` do passo 4 vazio.
- Suíte verde; `verificar-ambiente` retorna 0 no Pro com a instância compartilhada.
- `config/llm_routing.yaml` valida com os dois perfis declarando as mesmas sete tarefas.
- Nenhum servidor Ollama foi tocado (declarar os comandos executados no relatório final).
