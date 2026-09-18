# AGENTS.md — agente_nw

> Coloque este arquivo na raiz do repositório. Claude Code lê antes de qualquer tarefa.
> Padrão herdado dos repositórios lex_hub, pandora_96 e claw.

---

## 1. Papel do executor

Você implementa briefs. Não tem latitude criativa. Se o brief não cobre algo, pare e registre no relatório final como pendência — não invente.

Leia, nesta ordem, antes de qualquer alteração: este arquivo → `docs/PLANO.md` → `docs/ARQUITETURA.md` → `docs/PLAN.md` → o brief da sessão → o código já existente na área afetada.

## 2. Estrutura do repositório

```
agente_nw/
├── AGENTS.md
├── pyproject.toml
├── .gitignore
├── temas.exemplo.yaml
├── fontes.exemplo.yaml
├── config/
│   ├── container.py          # fábrica de dependências: llm(), banco(), http()
│   ├── llm_routing.yaml      # tarefa → modelo, num_ctx, temperatura, format
│   ├── limiares.yaml         # valores calibrados; nunca constante no código
│   └── local.exemplo.yaml    # caminhos e URLs identificadoras (o local.yaml fica fora do git)
├── agente_nw/                # pacote Python
│   ├── cli.py                # comandos: verificar-ambiente, importar-temas, importar-agenda,
│   │                         #   ficha, ativar, confirmar-tags, coletar, ciclo, copiar-banco, ...
│   ├── nucleo/
│   │   ├── modelos/          # contratos Pydantic v2, frozen=True, um módulo por entidade
│   │   ├── prompts/          # um arquivo por contrato, com esquema JSON e um exemplo resolvido
│   │   ├── database/
│   │   │   ├── conexao.py    # abre o banco: WAL, foreign_keys, busy_timeout, sqlite-vec
│   │   │   ├── migracoes.py  # aplica scripts/migracoes/*.sql em ordem
│   │   │   └── queries/      # todo SQL isolado aqui
│   │   ├── llm.py            # cliente único do Ollama
│   │   ├── vetores.py        # embeddings, cosseno, centróide
│   │   ├── sensivel.py       # filtro determinístico de categorias sensíveis
│   │   ├── relevancia/       # qualificação, pontuação, piso, tipo (regra do conector)
│   │   ├── agrupamento/      # centróide, janela, reabertura, divisão
│   │   └── saidas/           # cartão, menu, exportação Markdown
│   ├── coleta/
│   │   ├── rss/              # feedparser, trafilatura, canonicalização, google news
│   │   └── capturas/         # (Etapa 2) recepção do que vem da extensão
│   ├── perfil/                # importação da agenda, extração de texto, lacunas, centróide de perfil
│   ├── console/                # Flask + templates + estáticos
│   └── integracoes/          # (Etapa 3)
├── extensao/                 # (Etapa 2) extensão do Chrome
├── scripts/
│   ├── migracoes/             # 001_inicial.sql, 002_..., aplicados em ordem
│   ├── instalar_macos.sh
│   ├── verificar.sh          # ruff + mypy --strict + pytest
│   └── launchd/               # plists: ollama e ciclo
├── docs/                      # fora do git, exceto o que a governança listar
├── dados/                     # agente.db, backups/ — fora do git
├── saidas/                    # menu_AAAA-MM-DD.md — fora do git
├── logs/                      # fora do git
└── tests/
```

Nome do pacote e da pasta é sempre `agente_nw` — nunca `agente_relacionamento`. Desvio de nomenclatura é corrigido imediatamente.

## 3. Stack

- Python 3.12 do Homebrew; Bash para utilitários.
- SQLite em modo WAL, `busy_timeout` e `foreign_keys` ligados, arquivo único em `dados/agente.db`. Nunca compartilhado entre processos. `sqlite-vec` carregado na abertura da conexão.
- Ollama para inferência local, `http://localhost:11434`, subido pelo LaunchAgent do projeto (`scripts/launchd/br.agente_nw.ollama.plist`) — nunca pelo aplicativo do Ollama. Modelo por tarefa definido em `config/llm_routing.yaml` — verificar com `ollama list` antes de sugerir download. `qwen3:4b` com modo de raciocínio desligado (`think: false`) obrigatório em toda chamada, e `bge-m3` para embeddings. Dois modelos carregados ao mesmo tempo (`OLLAMA_MAX_LOADED_MODELS=2`, `OLLAMA_KEEP_ALIVE=30m`).
- Embeddings: `bge-m3` (1024 dimensões, multilíngue).
- Índice vetorial: `sqlite-vec`, no mesmo arquivo do banco.
- Contratos: Pydantic v2 com `frozen=True`.
- Arquitetura hexagonal; dependências via `config/container.py`.
- Saída estruturada do LLM sempre em modo JSON com esquema (`format: json`); `num_ctx` explícito em toda chamada.
- Interface: console web local em `console/`, Flask, `http://localhost:8765`, só em `127.0.0.1`.
- Coleta em rede social: extensão própria do Chrome (`extensao/`, manifest v3), sempre sob demanda (Etapa 2).
- Agendamento: `launchd` (macOS), com recuperação de execução perdida. Nunca laço infinito em processo.
- Testes: pytest. Tipagem: mypy strict. Lint: ruff. Suíte roda via `scripts/verificar.sh`, sempre por Sidarta no terminal — nunca pelo executor.

## 4. Regras de alteração

- Mudança cirúrgica: só o que o brief pede.
- Código funcionando não se altera sem evidência de defeito.
- Sem variantes de depuração, sem arquivos paralelos de módulos existentes.
- Sem hardcode de caminhos: resolução dinâmica.
- Texto de fonte externa (notícia, perfil) nunca é alterado ao ser armazenado; limpeza roda antes do hash de deduplicação, não sobre o texto guardado.
- Restrições são estruturais, não procedurais: o que não deve ser visto a jusante é bloqueado na origem, não filtrado depois.
- Antes de diagnosticar erro: "isso funcionava antes?" Responder essa pergunta antes de tocar em código.
- Toda alteração de tabela é uma migração numerada em `scripts/migracoes/`. Nenhum brief cria ou altera tabela fora de migração.
- Categorias sensíveis (saúde, religião, política, sindicato, vida sexual, origem racial, menores) nunca chegam ao banco: prompt proíbe e `nucleo/sensivel.py` descarta depois do modelo.

## 5. Git

- **Proibido `git add -A`.** Adição arquivo por arquivo, com lista explícita.
- `git status` obrigatório antes de qualquer `add`; arquivo inesperado interrompe a operação.
- Trunk-based em `main`. Sem branches de longa duração, sem recursos avançados de git.
- **Git nunca roda de forma autônoma.** O executor prepara a lista de arquivos e o texto do commit no relatório final; Sidarta autoriza.
- Remoção de arquivo rastreado: `git rm`, com critérios explícitos e exclusão de `__init__.py`, `.gitkeep` e afins.

## 6. Tarefas não assistidas

Podem rodar sem supervisão: coleta RSS, extração, geração de embeddings, agrupamento, qualificação, cruzamento, cartão do assunto.

Requisitos: idempotência e retomada, log em arquivo, kill switch por arquivo sentinela, shards disjuntos se houver mais de um processo, SQLite nunca compartilhado.

Durante uma medição de aceite, o único processo que escreve em `dados/agente.db` é o ciclo. Desenvolvimento usa cópia (`agente_nw copiar-banco`).

**Nunca rodam sozinhos:** git, coleta em rede social (sempre disparada pelo usuário, um contato por vez), alteração de ficha de contato, a suíte de testes padrão (`scripts/verificar.sh`, pytest, ruff, mypy) — o executor escreve e mantém o script; quem roda é Sidarta, no terminal dele.

## 7. Comportamento do software

O sistema classifica e cruza; o usuário confirma tags e marca o menu. Não existe geração nem envio de mensagem. Nunca rodam sozinhos: git, coleta em rede social, alteração de ficha de contato.

## 8. Relatório final obrigatório

Todo brief termina com este bloco preenchido. Sem ele, a sessão é considerada incompleta.

O executor não roda a suíte de testes padrão (pytest, ruff, mypy, `scripts/verificar.sh`) durante a sessão. Ele garante que o script está atualizado e funcional, e entrega no relatório o caminho completo, pronto para colar no terminal — quem roda e confirma o resultado é Sidarta.

```
## RELATÓRIO FINAL
- Brief executado:
- Arquivos criados:
- Arquivos alterados (com resumo da mudança em uma linha cada):
- Arquivos preservados literalmente na área afetada:
- Script de verificação (caminho completo, pronto para colar no terminal):
- Comandos executados:
- Lista de arquivos para `git add` e texto sugerido do commit:
- Pendências e decisões que ficaram abertas:
- `docs/PLAN.md` atualizado: sim/não
```

## 9. Certificação

Uma tarefa só está certificada quando: Sidarta roda o script de verificação apresentado no relatório e confirma testes verdes, escopo respeitado (nada além do brief), relatório final completo e `docs/PLAN.md` atualizado. Auditoria independente em doze passes é aplicada ao fim de cada fase de implementação, com validação cruzada em outro modelo.
