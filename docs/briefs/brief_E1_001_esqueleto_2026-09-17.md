# brief_E1_001_esqueleto — Esqueleto do repositório, configuração e verificação de ambiente

**Data:** 17 de setembro de 2026
**Etapa:** 1 (MVP), brief 001 de 14 — dia 2 (ter 22/09/2026)
**Executor:** Claude Code
**Repositório:** `/Users/sidarta48/github/agente_nw`
**Leia antes, nesta ordem:** `AGENTS.md` → `docs/PLANO.md` → `docs/ARQUITETURA.md` → `docs/PLAN.md` → este brief
**Depende de:** brief 000 concluído (documentos-base na versão 5). Se `docs/PLAN.md` não disser "brief 000 concluído", pare.

---

## 1. Objetivo em uma frase

Criar a estrutura de pastas, o pacote Python, os arquivos de configuração, o comando de linha e o script de verificação, de modo que `scripts/verificar.sh` passe num repositório ainda sem lógica e `agente_nw verificar-ambiente` confirme Python, `sqlite-vec` e os três modelos do Ollama.

## 2. Contexto e o que já existe no repositório

Documentação atualizada pelo brief 000 e nada de código. **Antes de criar qualquer arquivo, liste o conteúdo da raiz e de `docs/`** e confirme que não existe `pyproject.toml`, `agente_nw/` nem `scripts/`. Se existir, pare e registre no relatório.

A máquina de desenvolvimento e produção é o MacBook Air M3 de 16 GB com macOS Sonoma 14.6. O usuário já executou a preparação da seção 2 do plano v3: Python 3.12 do Homebrew, `brew install ollama` (fórmula, não o aplicativo), os modelos `qwen3:4b`, `bge-m3` e `qwen3:8b` puxados, e o servidor iniciado num terminal com `OLLAMA_MAX_LOADED_MODELS=2 OLLAMA_KEEP_ALIVE=30m ollama serve`. Se `curl -s localhost:11434/api/tags` não responder, pare e registre: o brief não instala o Ollama.

O usuário escreve `temas.yaml` hoje, a partir de `temas.exemplo.yaml` que este brief cria. O comando `importar-temas` deste brief **valida** o arquivo e mostra o que seria importado; a gravação no banco fica para o brief 002, que cria o esquema amanhã.

## 3. Escopo

### 3.1 Estrutura

A da seção 2 de `docs/ARQUITETURA.md`, criada com `__init__.py` em todo pacote e `.gitkeep` onde a pasta ficaria vazia. Pastas de dado (`dados/`, `saidas/`, `logs/`) criadas pelo script de instalação, não versionadas.

### 3.2 `pyproject.toml`

- Nome `agente_nw`, versão `0.1.0`, Python `>=3.12,<3.13`.
- Dependências: `feedparser`, `trafilatura`, `httpx`, `pydantic>=2`, `pyyaml`, `numpy`, `sqlite-vec`, `flask`, `python-dateutil`, `phonenumbers`, `pyobjc-framework-Contacts`.
- Dependências de desenvolvimento: `pytest`, `mypy`, `ruff`, `types-PyYAML`.
- `[project.scripts] agente_nw = "agente_nw.cli:main"`.
- `[tool.ruff]`: linha 110, regras `E, F, I, B, UP`; `[tool.mypy]`: `strict = true`, `python_version = "3.12"`, ignorar imports sem tipos de `feedparser`, `trafilatura`, `sqlite_vec`, `Contacts`.
- `[tool.pytest.ini_options]`: `testpaths = ["tests"]`.

### 3.3 `.gitignore`

Literal:
```
.venv/
__pycache__/
*.pyc
.mypy_cache/
.ruff_cache/
.pytest_cache/
.DS_Store
dados/
saidas/
capturas/
logs/
*.db
*.db-wal
*.db-shm
temas.yaml
temas.local.yaml
fontes.yaml
config/local.yaml
*.csv
docs/*
!docs/.gitkeep
```
A última regra implementa a governança: documentos ficam fora do git. `AGENTS.md` na raiz é versionado.

### 3.4 `config/llm_routing.yaml`

Literal — é o perfil `air16`; outros perfis entram na Etapa 2:
```yaml
perfil_ativo: air16
perfis:
  air16:
    embeddings:
      modelo: bge-m3
    tarefas:
      qualificar:            {modelo: qwen3:4b, num_ctx: 2048, temperature: 0.2, format: json, think: false}
      rotular:               {modelo: qwen3:4b, num_ctx: 2048, temperature: 0.2, format: json, think: false}
      cartao:                {modelo: qwen3:4b, num_ctx: 4096, temperature: 0.3, format: json, think: false}
      cruzar_por_que:        {modelo: qwen3:4b, num_ctx: 4096, temperature: 0.3, format: json, think: false}
      extrair_de_texto:      {modelo: qwen3:4b, num_ctx: 4096, temperature: 0.2, format: json, think: false}
      prerotular_calibracao: {modelo: qwen3:8b, num_ctx: 2048, temperature: 0.1, format: json, think: false}
    nova_tentativa:
      temperature: 0.1
      maximo: 1
```
`think: false` é obrigatório em toda tarefa; o carregador do roteamento recusa perfil em que qualquer tarefa não tenha `think: false` explícito.

### 3.5 `config/limiares.yaml`

Literal — valores iniciais, a calibrar nos briefs 007 e 009:
```yaml
agrupamento:
  cosseno_mesmo_assunto: 0.82     # calibrar no brief 007
  cosseno_republicacao: 0.94
  divergencia_minima_fonte_independente: 0.30
  janela_dias: 7
  itens_para_dividir: 12
qualificacao:
  substancial_minimo: 0.6
  conversavel_minimo: 0.6
  teto_por_dia: 40
conector:
  adjacencia_minima: 0.55         # calibrar no brief 009
  conversavel_viavel: 0.8         # calibrar no brief 009
  peso_aderencia_contato: 50
  peso_aderencia_usuario: 30
  peso_conversavel: 20
  peso_nivel: {dominio: 1.0, interesse: 0.7, curiosidade: 0.4}
  candidatos_por_contato: 10
  itens_no_menu: 5
```

### 3.6 `config/local.exemplo.yaml`

```yaml
banco: dados/agente.db
pasta_saida: saidas            # na Etapa 3 vira a pasta do Drive
pasta_backups: dados/backups
ollama_url: http://127.0.0.1:11434
# URLs identificadoras da conta (alerts, iCal) entram só em config/local.yaml, fora do git
```
O carregador lê `config/local.yaml` se existir, senão o exemplo.

### 3.7 `temas.exemplo.yaml`

```yaml
# Copie para temas.yaml (fora do git) e escreva os SEUS temas.
# descricao: frase corrida com as palavras que apareceriam numa notícia sobre o tema — é ela que vira embedding.
# nivel: dominio (sei falar disso) | interesse (acompanho) | curiosidade (falaria com um resumo na mão)
usuario:
  nome: Nome do usuário
  temas:
    - nome: direito tributário
      descricao: "reforma tributária, split payment, IVA dual, contencioso de ICMS e a transição até 2033"
      sinonimos: [reforma tributária, IBS, CBS]
      nivel: dominio
      peso: 5
    - nome: corrida de rua
      descricao: "provas de rua, maratonas, treinos, tênis de corrida, lesões de corredor"
      sinonimos: [maratona, meia maratona]
      nivel: interesse
      peso: 3
ignorar:
  - "horóscopo"
  - "os 10 melhores"
```

### 3.8 `fontes.exemplo.yaml`

Três feeds públicos de exemplo (`{nome, url, tipo, confiabilidade}`), com o comentário de que `fontes.yaml` fica fora do git e que as consultas do Google News são geradas pelo brief 006, não escritas à mão.

### 3.9 `config/container.py`

Fábricas explícitas com cache de instância, sem framework de injeção: `configuracao()` (lê `local.yaml`/exemplo, `llm_routing.yaml`, `limiares.yaml`, valida com Pydantic), `http()` (`httpx.Client` com timeout 30 s), `llm()` e `banco()` — estas duas ainda levantam `NotImplementedError("brief 003")` e `NotImplementedError("brief 002")` respectivamente, com os nomes já fixados. Regra do `AGENTS.md`: nenhum outro módulo cria cliente ou conexão.

### 3.10 `agente_nw/cli.py`

`argparse` com subcomandos (sem dependência extra). Neste brief: `verificar-ambiente` e `importar-temas --arquivo temas.yaml --simular`. Os demais subcomandos são registrados como nomes reservados que respondem "disponível a partir do brief NNN": `importar-agenda`, `ficha`, `ativar`, `confirmar-tags`, `coletar`, `ciclo`, `copiar-banco`, `restaurar-backup`, `exportar-menu`, `ler-marcacoes`, `calibrar-agrupamento`, `calibrar-conector`.

`verificar-ambiente` imprime uma tabela com OK/FALHA para: versão do Python (3.12.x); `sqlite3.sqlite_version`; `enable_load_extension` disponível e `sqlite_vec.load()` bem-sucedido numa conexão em memória; Ollama respondendo em `ollama_url`; presença de `qwen3:4b`, `bge-m3`, `qwen3:8b` em `/api/tags`; existência de `temas.yaml` e `fontes.yaml` (aviso, não falha). Sai com código 1 se qualquer item marcado como obrigatório falhar.

`importar-temas --simular` lê o YAML, valida com o modelo Pydantic `TemasArquivo` (nome único, `nivel` entre os três valores, `peso` 1–5, `descricao` com pelo menos 8 palavras — descrição curta demais rende embedding fraco e o comando avisa), e imprime o que seria gravado. Sem `--simular`, responde "gravação disponível a partir do brief 002".

### 3.11 Scripts

- `scripts/instalar_macos.sh`: os comandos da seção 2 do plano v3 (Homebrew, python@3.12, `brew install ollama`, os três `ollama pull`, venv, `pip install -e ".[dev]"`, `mkdir -p dados/backups saidas logs`), idempotente, com aviso explícito para não usar `brew services start ollama`.
- `scripts/verificar.sh`: `ruff check . && ruff format --check . && mypy agente_nw && pytest -q`.

### 3.12 Testes

`tests/test_configuracao.py`: os três YAML de exemplo carregam e validam; perfil de roteamento sem `think: false` numa tarefa é recusado; `limiares.yaml` tem todas as chaves listadas em 3.5. `tests/test_ambiente.py`: `sqlite_vec` carrega numa conexão em memória (`SELECT vec_version()` responde). Nenhum teste toca no Ollama neste brief.

## 4. Fora de escopo, com justificativa

- Esquema, migrações, backup: brief 002, amanhã. Este brief não cria banco.
- Cliente de LLM real: brief 003. `container.llm()` existe só como nome.
- Qualquer prompt, coleta, console: briefs posteriores.
- `git init` e primeiro commit: o usuário executa, conforme o relatório do brief 000.

## 5. Decisões tomadas e decisões deixadas abertas

Tomadas:
- Pacote de topo `agente_nw/` no repositório `agente_nw/` (não `src/`), porque é o padrão dos outros repositórios do autor e a arquitetura já foi escrita assim.
- `argparse`, sem `typer`/`click`: menos dependência, e os comandos são poucos e simples.
- Listas em YAML (`sinonimos`, `linguas`) são gravadas no banco como JSON em coluna TEXT; o modelo Pydantic converte nos dois sentidos.
- Configuração validada por Pydantic na carga: erro de YAML aparece na inicialização, não no meio do ciclo às 05h00.

Abertas: nenhuma.

## 6. Passos de execução

1. Listar raiz e `docs/`; confirmar ausência de código; confirmar `docs/PLAN.md` com "brief 000 concluído".
2. Criar a estrutura de pastas da seção 2 de `ARQUITETURA.md` com `__init__.py`/`.gitkeep`.
3. Escrever `pyproject.toml` (3.2) e `.gitignore` (3.3).
4. Escrever os quatro YAML de configuração e os dois de exemplo (3.4 a 3.8).
5. Escrever `agente_nw/nucleo/modelos/configuracao.py` com os modelos Pydantic `Configuracao`, `Roteamento`, `Limiares`, `TemasArquivo`; e `config/container.py` (3.9).
6. Escrever `agente_nw/cli.py` (3.10).
7. Escrever os scripts (3.11) e os testes (3.12).
8. Rodar `bash scripts/instalar_macos.sh` (deve ser idempotente sobre a preparação já feita), depois `bash scripts/verificar.sh`, depois `agente_nw verificar-ambiente`. Colar as três saídas no relatório.
9. Copiar `temas.exemplo.yaml` para `temas.yaml` **somente se ele não existir** e avisar o usuário no relatório de que precisa escrevê-lo hoje; rodar `agente_nw importar-temas --simular` e colar a saída.
10. Atualizar `docs/PLAN.md`: brief 001 concluído; próximo é 002; nenhuma dívida ou as encontradas.
11. Relatório final.

## 7. Critérios de aceite

1. `bash scripts/verificar.sh` verde (ruff, ruff format, mypy strict, pytest).
2. `agente_nw verificar-ambiente` marca OK em Python 3.12, `sqlite-vec` carregado, Ollama respondendo e os três modelos presentes.
3. `agente_nw importar-temas --simular` sobre `temas.exemplo.yaml` lista dois temas com nível e peso; sobre um arquivo com `nivel: outro` falha com mensagem clara.
4. `config/container.py` é o único lugar do pacote que importa `httpx.Client`; `grep -rn "httpx.Client(" agente_nw/` retorna só ele.
5. `.gitignore` contém todas as linhas de 3.3; `git status` (rodado pelo usuário depois do `git init`) não lista `docs/` além de `.gitkeep`, nem `temas.yaml`.
6. Nenhum arquivo de `dados/`, `saidas/`, `logs/` criado dentro do pacote; só pelo script de instalação.

## 8. Riscos e como reverter

- **`sqlite-vec` não carrega** (Python sem `enable_load_extension`): o `verificar-ambiente` diz exatamente isso e aponta para `brew install python@3.12` e recriação do venv. Não tentar compilar nada.
- **Ollama do aplicativo rodando na porta** além do `ollama serve` do terminal: `verificar-ambiente` avisa quando `/api/version` responde mas `ps` mostra `Ollama.app`; o usuário fecha o aplicativo. Este brief não mata processos.
- **Reversão:** o brief só cria arquivos novos; remover os criados devolve o repositório ao estado do brief 000. A lista completa vai no relatório.

## 9. Relatório final obrigatório

```
## RELATÓRIO FINAL
- Brief executado: brief_E1_001_esqueleto_2026-09-17
- Arquivos criados:
- Arquivos alterados (com resumo da mudança em uma linha cada):
- Arquivos preservados literalmente na área afetada:
- Testes rodados e resultado: (saídas de verificar.sh, verificar-ambiente e importar-temas --simular)
- Comandos executados:
- Lista de arquivos para `git add` e texto sugerido do commit:
- Pendências e decisões que ficaram abertas: (inclui: usuário precisa escrever temas.yaml hoje)
- `docs/PLAN.md` atualizado: sim/não
```
