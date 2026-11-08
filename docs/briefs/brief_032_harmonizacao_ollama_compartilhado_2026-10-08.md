# Brief 032 — Verificação do relatório de harmonização com o Ollama compartilhado e adaptação do `agente_nw`

**Repositório:** `/Users/sidarta48/github/agente_nw` (MacBook Pro M5 Pro, 48 GB — máquina compartilhada com `cervello`, `sergio`, `trf6`, `lex_hub`, `pandora_96`, `advogada_parceira_*`)
**Depende de:** brief 031 v2 (perfil `pro48`, `perfil_llm` em `config/local.yaml`), já commitado em `24848f2`.
**Data:** 2026-10-08
**Insumo:** relatório "Harmonização do agente_nw com o ecossistema Ollama compartilhado" (2026-10-08), produzido por investigação só-leitura sem acesso a processos reais. Este brief primeiro **verifica** cada afirmação do relatório na máquina real e só então **adapta** o projeto ao que foi confirmado.

---

## 1. Objetivo em uma frase

No Pro, o `agente_nw` passa a usar a instância do Ollama que já está de pé para os outros projetos (em vez de subir uma segunda instância própria), sem derrubar nada que esteja servindo outro projeto; no Air, nada muda.

---

## 2. Regra absoluta durante a execução deste brief

**Nenhum comando que pare, reinicie ou substitua um servidor Ollama.** Proibidos nesta sessão: `launchctl kickstart -k`, `launchctl unload`/`bootout` de qualquer plist de Ollama que não seja `br.agente_nw.ollama`, `pkill ollama`, `osascript ... quit app "Ollama"`, `ollama serve` manual. A máquina tem automações diárias de outros projetos (classificação do `sergio` às 6h, classificação contínua do `trf6`) apoiadas em instâncias que não pertencem a este repositório. Tudo aqui é leitura (`launchctl list`, `lsof`, `curl`, `cat`, `ps`) e edição de arquivos do `agente_nw`.

---

## 3. Fase 1 — Verificação do relatório (só leitura, registrar o resultado)

Executar na máquina e registrar a saída de cada item na seção "Resultado da verificação" do relatório final. Para cada afirmação do relatório, anotar **confirmada**, **refutada** ou **parcial**, com a evidência.

| # | Afirmação do relatório | Como verificar |
|---|---|---|
| V1 | Existe `~/Library/LaunchAgents/com.ollama.cervello.plist`, `RunAtLoad=true`, `KeepAlive=true`, servindo a porta 11435 | `cat ~/Library/LaunchAgents/com.ollama.cervello.plist`; conferir `OLLAMA_HOST`, `OLLAMA_MODELS` (se definido), `OLLAMA_MAX_LOADED_MODELS`, `OLLAMA_KEEP_ALIVE` |
| V2 | A instância em 11435 está de pé e responde | `launchctl list \| grep -i ollama`; `lsof -nP -iTCP:11435 -sTCP:LISTEN`; `curl -s http://127.0.0.1:11435/api/tags` |
| V3 | A instância em 11435 enxerga `qwen2.5:14b` **e** `bge-m3` | Da saída de `/api/tags` em 11435, listar os nomes. Atenção: se o plist do `cervello` definir `OLLAMA_MODELS` para um diretório próprio, os modelos podem não ser os mesmos do `ollama list` padrão — isso muda a decisão da Fase 2 |
| V4 | Em 11434 há (ou não) um servidor, e qual é | `lsof -nP -iTCP:11434 -sTCP:LISTEN` → PID → `ps -p <PID> -o command=`; distinguir `Ollama.app` (caminho em `/Applications/Ollama.app/...`), LaunchAgent `br.agente_nw.ollama` (`/opt/homebrew/bin/ollama serve` com esse rótulo em `launchctl list`) ou outro; `curl -s http://127.0.0.1:11434/api/tags` |
| V5 | `br.agente_nw.ollama` está carregado nesta máquina | `launchctl list \| grep br.agente_nw.ollama`; `ls ~/Library/LaunchAgents/ \| grep agente_nw` |
| V6 | `sergio` aponta para 11435 (`LLM_BASE_URL`) | `grep -n LLM_BASE_URL ~/github/sergio/.env` (só leitura) |
| V7 | `trf6` usa 11435 | `grep -rn "1143[45]" ~/github/trf6 --include="*.py" --include=".env*" --include="*.yaml" --include="*.toml" \| head` |
| V8 | `lex_hub`, `pandora_96`, `advogada_parceira_*` apontam para 11434 | mesmo `grep` em cada pasta |
| V9 | O `verificar-ambiente` do `agente_nw` acusa "Ollama.app está rodando" com base em `ps aux`, independentemente da porta configurada | Ler `_verificar_ollama_app_na_porta` em `agente_nw/cli.py` (já conhecido: a checagem é por nome de processo, não por porta — confirmar) |
| V10 | `AGENTS.md` do `agente_nw` está versionado | `git ls-files AGENTS.md` |
| V11 | A string "claw" em `AGENTS.md` refere-se ao `claw_planalto` | `grep -n claw AGENTS.md` |

Afirmações do relatório que **não** precisam de verificação porque não mudam nenhuma decisão: contagem de reinícios da instância do `cervello`; histórico do `sergio` (73,4% não classificados); plano anterior "Duas Frentes".

---

## 4. Fase 2 — Decisões e adaptações (condicionadas ao resultado da Fase 1)

### 4.1. `config/local.yaml` do Pro aponta para a instância compartilhada

**Condição:** V2 e V3 confirmadas (11435 responde e enxerga `qwen2.5:14b` e `bge-m3`).

**Ação:** editar `config/local.yaml` (fora do git, já existe com `perfil_llm: pro48`): `ollama_url: http://127.0.0.1:11435`. Rodar `.venv/bin/agente_nw verificar-ambiente` e registrar a saída.

**Se V3 falhar por `bge-m3` ausente em 11435** (caso de `OLLAMA_MODELS` próprio do `cervello`): não baixar nada na instância do `cervello` sem autorização do usuário — parar, relatar e propor as duas saídas: (a) `OLLAMA_HOST=127.0.0.1:11435 ollama pull bge-m3` (1,2 GB, não afeta modelos já carregados), ou (b) manter o `agente_nw` em instância própria numa terceira porta (4.3).

### 4.2. O LaunchAgent próprio do `agente_nw` não sobe no Pro

**Condição:** sempre, independentemente da Fase 1 — no Pro, com `ollama_url` em 11435, o plist do projeto é desnecessário.

**Ações:**
- Se V5 mostrar `br.agente_nw.ollama` carregado nesta máquina: **não descarregar nesta sessão**. Registrar e deixar para o usuário decidir, porque pode ser ele o servidor de 11434 que outros projetos estão usando sem saber (V4). Se V4 mostrar que o servidor de 11434 é o `br.agente_nw.ollama`, dizer isso explicitamente no relatório — é a situação em que o `agente_nw` impõe `MAX_LOADED_MODELS=2`/`KEEP_ALIVE=30m` a `lex_hub`/`pandora_96`/`advogada_parceira_*` sem combinar.
- `scripts/instalar_macos.sh`: antes de instalar o plist, checar se já existe algo escutando na porta de destino (`lsof -nP -iTCP:11434 -sTCP:LISTEN`). Se existir, abortar com a mensagem: "já existe um servidor Ollama em 11434 (PID X, comando Y). Em máquina compartilhada, aponte `ollama_url` em config/local.yaml para a instância existente em vez de instalar o LaunchAgent do projeto." Instalar só em porta livre. Nunca usar `kickstart -k` no script.
- `scripts/launchd/br.agente_nw.ollama.plist`: continua no repositório, para o Air. Acrescentar comentário XML no topo: "Uso previsto: máquina dedicada (MacBook Air, perfil air16). Em máquina compartilhada com outros projetos, não instalar — ver AGENTS.md, seção Ollama."

### 4.3. Checagem do Ollama.app passa a ser por porta, não por nome de processo

**Condição:** V9 confirmada.

**Ação em `cli.py`:** substituir `_verificar_ollama_app_na_porta` por `_verificar_servidor_na_porta(ollama_url)`:
1. Extrair a porta de `ollama_url`.
2. `lsof -nP -iTCP:<porta> -sTCP:LISTEN -Fp` → PID → `ps -p <PID> -o command=`.
3. Classificar: `Ollama.app` (caminho contém `Ollama.app`), `LaunchAgent do projeto` (se `launchctl list` tiver `br.agente_nw.ollama` e o PID bater), `outra instância` (qualquer outro `ollama serve` — por exemplo a do `cervello`), `desconhecido`.
4. Resultado: AVISO só quando for `Ollama.app` **na porta configurada**; nos demais casos OK, com o detalhe nomeando o tipo e o PID, por exemplo `outra instância (PID 812, ollama serve) — compartilhada`. Em falha de `lsof` (Linux, permissão), OK "não verificado", não obrigatório — mantém os testes passando fora do macOS.

Com isso, no Pro apontando para 11435, o aviso "Ollama.app está rodando" desaparece, porque o Ollama.app em 11434 não é o servidor que o `agente_nw` usa. E no Air o comportamento continua o mesmo.

### 4.4. `verificar-ambiente` informa a instância em uso

Acrescentar ao item "Ollama responde" o detalhe com porta e classificação de 4.3, por exemplo: `http://127.0.0.1:11435 — outra instância (PID 812), compartilhada`. É a linha que responde "com qual servidor este projeto está falando nesta máquina".

### 4.5. `AGENTS.md` — seção Ollama reescrita

Substituir o parágrafo atual por:
- O `agente_nw` fala com o Ollama pela `ollama_url` de `config/local.yaml`, por máquina.
- Máquina dedicada (Air, `air16`): LaunchAgent próprio `br.agente_nw.ollama` em 11434, `OLLAMA_MAX_LOADED_MODELS=2`, `OLLAMA_KEEP_ALIVE=30m`, instalado por `scripts/instalar_macos.sh`.
- Máquina compartilhada (Pro, `pro48`): **não** instalar o LaunchAgent do projeto; `ollama_url` aponta para a instância já existente (hoje `http://127.0.0.1:11435`, mantida pelo `cervello`, modelo `qwen2.5:14b`). Nunca reiniciar essa instância a partir deste projeto.
- Regra para qualquer automação futura deste projeto: garantir disponibilidade com `launchctl kickstart` **sem** `-k` e só do rótulo `br.agente_nw.ollama`; nunca `ollama serve` incondicional; nunca tocar em rótulos de outros projetos.
- Corrigir "claw" para "claw_planalto (ferramenta externa, não clonada nesta máquina)" (V11).

**Decisão sobre V10 (`AGENTS.md` versionado):** mantém versionado. Diferente dos outros projetos da família, o `agente_nw` roda em duas máquinas com `git pull` como único mecanismo de sincronização; o `AGENTS.md` é a instrução de trabalho que precisa chegar ao Air junto com o código. Não alinhar ao padrão `gitignore` da família neste ponto.

### 4.6. Testes

- `tests/test_cli_servidor_na_porta.py` (novo): `_classificar_processo(comando, pid, rotulos_launchctl)` como função pura, testada com três entradas (`/Applications/Ollama.app/Contents/Resources/ollama serve` → `Ollama.app`; `/opt/homebrew/bin/ollama serve` com rótulo `br.agente_nw.ollama` e PID coincidente → `LaunchAgent do projeto`; `/opt/homebrew/bin/ollama serve` sem rótulo → `outra instância`).
- Teste de `_porta_de(ollama_url)` para `http://127.0.0.1:11434`, `http://127.0.0.1:11435`, `http://localhost:11434/`.
- `instalar_macos.sh`: sem teste automatizado; verificação manual no relatório (rodar com `set -n` para sintaxe e simular porta ocupada com `nc -l 11434` em outro terminal se o usuário autorizar; caso contrário, só a checagem de sintaxe).

---

## 5. Fora de escopo, com justificativa

- **Alterar qualquer arquivo de `cervello`, `sergio`, `trf6`, `lex_hub`, `pandora_96`, `advogada_parceira_*`.** Este brief só lê esses repositórios para verificar o relatório. Eventuais ajustes neles (por exemplo, os que apontam para 11434 sem servidor confiável) são briefs de cada projeto, decididos pelo usuário com o relatório desta Fase 1 em mãos.
- **Descarregar o `br.agente_nw.ollama` do Pro, se estiver carregado.** Ação que pode derrubar o servidor que outros projetos usam em 11434; fica registrada no relatório como decisão do usuário, com o comando exato (`launchctl bootout gui/$(id -u)/br.agente_nw.ollama`) e a consequência.
- **Instância própria do `agente_nw` em terceira porta no Pro.** Só se 4.1 falhar por V3; aí vira brief próprio com `OLLAMA_HOST` no plist e `ollama_url` correspondente.
- **Unificar os limites `OLLAMA_MAX_LOADED_MODELS`/`KEEP_ALIVE` entre projetos.** Decisão de infraestrutura da máquina, não deste repositório.

---

## 6. Passos de execução

1. Fase 1 completa (V1–V11), saídas registradas literalmente.
2. Relatar ao usuário o resultado da Fase 1 **antes** de qualquer edição, em uma tabela confirmada/refutada/parcial. Prosseguir só com o que foi confirmado.
3. `config/local.yaml`: `ollama_url` em 11435 (4.1, se condição satisfeita).
4. `cli.py`: 4.3 e 4.4; remover `_verificar_ollama_app_na_porta`.
5. `scripts/instalar_macos.sh`: checagem de porta ocupada (4.2).
6. `scripts/launchd/br.agente_nw.ollama.plist`: comentário de uso previsto (4.2).
7. `AGENTS.md`: seção Ollama (4.5), correção "claw_planalto".
8. Testes de 4.6.
9. `ruff check .`, `ruff format --check .`, `mypy agente_nw`, `pytest -q` — usando `.venv/bin/...`. Observação: `tests/test_coleta_retomada.py` falha por data fixa (`pubDate` de 18/09/2026 com limite de 7 dias) desde 25/09, sem relação com este brief; corrigir no mesmo commit gerando o `pubDate` a partir de `datetime.now() - timedelta(days=1)`.
10. `.venv/bin/agente_nw verificar-ambiente` no Pro: primeira linha `pro48`, "Ollama responde" nomeando 11435 e a instância compartilhada, sem o aviso de Ollama.app.
11. `.venv/bin/agente_nw qualificar --limite 3` — prova real do brief 031 pendente: `qwen2.5:14b` via 11435, JSON válido, nenhuma entrada em `fila_revisao`, linhas `sucesso: true` em `dados/logs/chamadas_llm.jsonl`.
12. Commit: `feat(ollama): uso de instância compartilhada por máquina, checagem de servidor por porta e proteção do instalador` — não incluir `config/local.yaml` (ignorado).

---

## 7. Critérios de aceite

- Relatório da Fase 1 com as onze verificações e evidência literal de cada uma.
- Nenhum servidor Ollama foi parado, reiniciado ou substituído durante a sessão (declarar explicitamente no relatório final, listando os comandos executados).
- No Pro: `verificar-ambiente` retorna 0 sem o aviso de Ollama.app, nomeando a instância de 11435; `qualificar --limite 3` conclui com JSON válido.
- `instalar_macos.sh` aborta com mensagem clara quando a porta de destino já está ocupada.
- No Air, após `git pull`: comportamento inalterado (`ollama_url` em 11434, LaunchAgent próprio, `verificar-ambiente` igual ao de antes).
- `pytest` sem falhas, inclusive `test_coleta_retomada.py`.
