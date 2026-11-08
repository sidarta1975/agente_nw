# Brief 032 — Verificação do relatório sobre o Ollama compartilhado no MacBook Pro

**Repositório:** `/Users/sidarta48/github/agente_nw` (MacBook Pro M5 Pro, 48 GB — máquina de desenvolvimento, perfil `pro48`)
**Depende de:** brief 031 v2 (commit `24848f2`), já aplicado. `config/local.yaml` do Pro já existe com `perfil_llm: pro48` e `ollama_url: http://127.0.0.1:11434`.
**Data:** 2026-10-08
**Natureza:** verificação ao vivo, somente leitura na Parte A; uma ação condicionada e reversível na Parte B, apenas em arquivo fora do git.

---

## 1. Objetivo em uma frase

Confirmar ou refutar, com evidência colhida na própria máquina, cada afirmação do relatório "harmonização do agente_nw com o ecossistema Ollama compartilhado" (2026-10-08) e, se as afirmações centrais se confirmarem, apontar o `agente_nw` do Pro para a instância Ollama já existente em vez de subir uma segunda.

---

## 2. Contexto

Um relatório produzido por outra sessão, analisando os repositórios em `~/github`, afirma que:

1. O `cervello` mantém um LaunchAgent próprio, `~/Library/LaunchAgents/com.ollama.cervello.plist`, servindo Ollama na porta **11435**, sempre de pé, com `qwen2.5:14b`.
2. `sergio` e `trf6` já usam essa instância (o `sergio` após correção de `:11434` para `:11435` em 2026-09-18).
3. `lex_hub`, `pandora_96` e `advogada_parceira_*` continuam apontando para a porta padrão 11434, provavelmente servida pelo Ollama.app.
4. O `agente_nw` é o único projeto que versiona um LaunchAgent de Ollama (`scripts/launchd/br.agente_nw.ollama.plist`), na porta 11434, com `KeepAlive` e sem checagem de instância já existente — e, se carregado no Pro, imporia `OLLAMA_MAX_LOADED_MODELS=2`/`OLLAMA_KEEP_ALIVE=30m` a quem mais usa a 11434.
5. Recomendação: no Pro, não carregar o LaunchAgent do `agente_nw`; apontar `ollama_url` para `http://127.0.0.1:11435`. No Air, manter tudo como está.
6. Achados menores: `AGENTS.md` do `agente_nw` está versionado, ao contrário dos outros projetos; "claw" citado no `AGENTS.md` é o `claw_planalto`, ferramenta externa.

O próprio relatório declara que **não teve acesso a processos reais** — as conclusões vêm de documentos (`brief_S1_129` do `sergio` e outros). Por isso este brief existe.

**O que já foi conferido antes deste brief, dentro da pasta do `agente_nw`** (não precisa repetir):

- `git ls-files AGENTS.md` → versionado. Afirmação 6a confirmada quanto ao `agente_nw`.
- `AGENTS.md`, linha 4: "Padrão herdado dos repositórios lex_hub, pandora_96 e claw". Referência existe.
- `scripts/launchd/br.agente_nw.ollama.plist` não define `OLLAMA_HOST` → porta 11434. Afirmação 4 confirmada quanto ao conteúdo do arquivo.
- `ollama_url` só aparece em `config/local.exemplo.yaml` e `config/local.yaml`; nenhum código fixa porta. Trocar de instância é uma linha no `local.yaml`, fora do git.
- `agente_nw verificar-ambiente` rodado hoje no Pro: "Ollama responde" na 11434 e **aviso de que o Ollama.app está rodando** — ou seja, hoje quem serve a 11434 no Pro é o aplicativo, não o LaunchAgent do `agente_nw`. Indício forte de que o LaunchAgent do `agente_nw` **não está carregado** no Pro (a confirmar na Parte A).

**Instrução ao usuário, válida até o fim deste brief:** não executar `osascript -e 'quit app "Ollama"'` nem `launchctl kickstart -k gui/$(id -u)/br.agente_nw.ollama` no Pro. A orientação dada antes deste relatório fica suspensa; se o relatório estiver certo, esse comando derrubaria o servidor que outros projetos usam.

---

## 3. Parte A — Verificação (somente leitura)

Executar cada item, registrar a saída literal e dar um veredito por afirmação: **CONFIRMADA**, **REFUTADA** ou **PARCIAL** (com o que difere). Nenhum comando desta parte altera nada.

### A1. Quem escuta em 11434 e 11435

```
lsof -nP -iTCP:11434 -sTCP:LISTEN
lsof -nP -iTCP:11435 -sTCP:LISTEN
ps -o pid,ppid,etime,command -p $(lsof -tnP -iTCP:11434 -sTCP:LISTEN -iTCP:11435 -sTCP:LISTEN | sort -u | tr '\n' ',' | sed 's/,$//')
```

Registrar, para cada porta: processo, binário (`/opt/homebrew/bin/ollama`, `/Applications/Ollama.app/...` ou outro), tempo de vida.

### A2. LaunchAgents de Ollama existentes e carregados

```
ls -la ~/Library/LaunchAgents/ | grep -i ollama
cat ~/Library/LaunchAgents/com.ollama.cervello.plist 2>/dev/null
launchctl list | grep -i -E "ollama|cervello|agente_nw"
launchctl print gui/$(id -u)/com.ollama.cervello 2>/dev/null | grep -E "state|OLLAMA_|program|last exit"
launchctl print gui/$(id -u)/br.agente_nw.ollama 2>/dev/null | grep -E "state|OLLAMA_|program|last exit"
```

Registrar: o plist do `cervello` existe? Qual `OLLAMA_HOST`? Quais `OLLAMA_MAX_LOADED_MODELS` e `OLLAMA_KEEP_ALIVE` (ou ausentes = padrão)? O `br.agente_nw.ollama` aparece em `launchctl list`? Se aparecer, com que estado e último código de saída?

### A3. O que cada instância tem disponível e carregado

```
curl -s http://127.0.0.1:11434/api/tags | python3 -c "import sys,json; print([m['name'] for m in json.load(sys.stdin)['models']])"
curl -s http://127.0.0.1:11435/api/tags | python3 -c "import sys,json; print([m['name'] for m in json.load(sys.stdin)['models']])"
curl -s http://127.0.0.1:11434/api/ps
curl -s http://127.0.0.1:11435/api/ps
curl -s http://127.0.0.1:11434/api/version; echo; curl -s http://127.0.0.1:11435/api/version; echo
```

Registrar: `qwen2.5:14b` e `bge-m3` aparecem em `/api/tags` da 11435? (Esperado sim — as duas instâncias rodam sob o mesmo usuário e compartilham `~/.ollama/models`; se não aparecerem, o `cervello` usa `OLLAMA_MODELS` próprio e a recomendação do relatório não vale sem mais trabalho.) Quais modelos estão carregados em memória em cada uma?

### A4. Quem aponta para qual porta, nos outros repositórios

Somente leitura, sem entrar em `.venv`:

```
cd ~/github
grep -rn -E "11434|11435|OLLAMA_HOST|LLM_BASE_URL|ollama_url" --include="*.py" --include="*.yaml" --include="*.yml" --include="*.toml" --include="*.env*" --include=".env*" --include="*.md" --include="*.plist" --include="*.sh" \
  sergio trf6 cervello lex_hub pandora_96 advogada_parceira_free advogada_parceira_b 2>/dev/null | grep -v "/.venv/" | grep -v "/node_modules/"
```

Ajustar os nomes das pastas ao que `ls ~/github` mostrar. Registrar, por projeto: porta efetiva em configuração ativa (`.env` real, não `.env.example`). Confirmar ou refutar as afirmações 2 e 3.

### A5. Verificar `brief_S1_129` do `sergio`

```
ls ~/github/sergio/docs/briefs/ 2>/dev/null | grep -i S1_129
```

Se existir, ler e confirmar que diz o que o relatório atribui a ele: porta 11435, `launchctl kickstart` sem `-k`, correção do `.env` do `sergio`. Se não existir, registrar como **não localizado**.

### A6. `AGENTS.md` nos outros projetos

```
for p in sergio trf6 cervello lex_hub pandora_96; do echo "== $p"; (cd ~/github/$p 2>/dev/null && git ls-files AGENTS.md; grep -n "AGENTS.md" .gitignore 2>/dev/null); done
```

Confirmar ou refutar a afirmação de que "o resto da família" ignora o `AGENTS.md` no git.

### A7. "claw"

```
grep -rn -i "claw" ~/github/lex_hub --include="*.md" 2>/dev/null | grep -v "/.venv/" | head
```

Confirmar ou refutar que `claw` é o `claw_planalto`, ferramenta externa citada em documento do `lex_hub`.

---

## 4. Parte B — Ação condicionada

Executar **somente** se A1, A2 e A3 confirmarem, ao mesmo tempo: (i) há um `ollama serve` escutando na 11435, mantido por LaunchAgent com `KeepAlive`; (ii) `qwen2.5:14b` e `bge-m3` aparecem em `/api/tags` dessa instância; (iii) `br.agente_nw.ollama` **não** está carregado no Pro.

Se qualquer uma falhar, parar na Parte A e entregar só o relatório.

### B1. `config/local.yaml` do Pro (fora do git)

Trocar `ollama_url: http://127.0.0.1:11434` por `ollama_url: http://127.0.0.1:11435`. Acrescentar comentário na linha: `# instância compartilhada mantida pelo cervello (com.ollama.cervello); não carregar br.agente_nw.ollama nesta máquina`.

### B2. `agente_nw/cli.py` — aviso do Ollama.app passa a depender da porta

Hoje `_verificar_ollama_app_na_porta` avisa sempre que o Ollama.app está rodando, independentemente de qual porta o projeto usa. Com o `agente_nw` apontando para a 11435, o aviso seria falso: o aplicativo na 11434 não interfere. Ajuste mínimo: a função recebe `ollama_url` e só emite o aviso quando a porta da URL for 11434. Quando for outra, devolve `ok=True` com detalhe `"não se aplica — projeto usa a porta <n>"`. Teste unitário para os dois casos. Esta é a única alteração versionada deste brief; vale igualmente para o Air (que continua na 11434 e continua recebendo o aviso).

### B3. Prova real na instância compartilhada

```
.venv/bin/agente_nw verificar-ambiente
.venv/bin/agente_nw qualificar --limite 3
tail -n 5 dados/logs/chamadas_llm.jsonl
curl -s http://127.0.0.1:11435/api/ps
```

Esperado: "Ollama responde" na 11435; `qwen2.5:14b` e `bge-m3` presentes; qualificação conclui com `sucesso: true` em 1 tentativa, sem erro 400 e sem item novo em `fila_revisao`; `/api/ps` da 11435 mostra `qwen2.5:14b` (e `bge-m3`, se houve embedding) carregados.

Registrar também, como informação para o usuário, não como bloqueio: se a instância do `cervello` roda com `OLLAMA_MAX_LOADED_MODELS=1` (ou padrão sem a variável), o `agente_nw` alternará `qwen2.5:14b` e `bge-m3` na memória a cada troca de tarefa — funciona, porém mais lento. Com 48 GB há espaço para os dois; se for o caso, a recomendação é o **dono do `cervello`** (outro brief, outro repositório) acrescentar `OLLAMA_MAX_LOADED_MODELS=2` ao seu plist. O `agente_nw` não edita arquivos de outros projetos.

---

## 5. Decisões já tomadas (não reabrir)

- **O `agente_nw` não altera nada fora do próprio repositório e do próprio `config/local.yaml`.** Plist do `cervello`, `.env` do `sergio`, configuração do `trf6`: só leitura. Qualquer ajuste neles é registrado como recomendação no relatório.
- **O LaunchAgent `br.agente_nw.ollama.plist` continua versionado e continua sendo o padrão do Air.** O relatório está correto em dizer que ele é adequado a uma máquina isolada. Ele não é carregado no Pro — e, se A2 mostrar que está carregado, isso é um achado a relatar, não a corrigir neste brief (descarregar derruba quem estiver usando a 11434; o usuário decide).
- **`AGENTS.md` permanece versionado no `agente_nw`.** É o contrato de trabalho do Claude Code com este repositório; o alinhamento com os outros projetos fica registrado como achado, sem ação.
- **"claw": sem ação.** Se A7 confirmar, uma nota de rodapé no `AGENTS.md` pode nomear `claw_planalto`; é cosmético e fica fora deste brief.
- **O Air não é tocado.** Perfil `air16`, LaunchAgent próprio, porta 11434, máquina sem concorrência.

---

## 6. Entregável

`docs/relatorios/relatorio_verificacao_brief_032_2026-10-08.md` com:

1. Tabela: afirmação do relatório (1 a 6) → comando/evidência → veredito (CONFIRMADA / REFUTADA / PARCIAL) → observação.
2. Saídas literais de A1 a A7 (recortadas ao essencial, sem truncar portas, binários e variáveis).
3. Se a Parte B foi executada: diff do `local.yaml` (com URLs identificadoras mascaradas, se houver), diff do `cli.py` e do teste, saída de B3.
4. Se a Parte B não foi executada: qual condição falhou e o que o usuário precisa decidir.
5. Recomendações para outros repositórios, se houver (ex.: `OLLAMA_MAX_LOADED_MODELS=2` no plist do `cervello`), explicitamente marcadas como "fora deste repositório, sem ação tomada".

Commit, somente se B2 foi feito: `fix(cli): aviso do Ollama.app só quando o projeto usa a porta 11434`. O `local.yaml` não entra no git.

---

## 7. Critérios de aceite

- Cada uma das seis afirmações do relatório tem veredito com evidência de comando, não de documento.
- Nenhum arquivo fora de `~/github/agente_nw` foi modificado; nenhum processo foi encerrado ou reiniciado.
- Se a Parte B rodou: `verificar-ambiente` passa apontando para a 11435, sem aviso de Ollama.app; qualificação real conclui com JSON válido; `git status` mostra apenas `cli.py` e o teste novo; `local.yaml` continua ignorado.
- Se a Parte B não rodou: o relatório diz exatamente qual condição falhou.
