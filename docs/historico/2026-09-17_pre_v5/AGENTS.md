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
├── docs/
│   ├── PLANO.md            # plano geral, escopo, fases
│   ├── ARQUITETURA.md      # blocos, contratos, fluxo
│   ├── PLAN.md             # estado vivo: pendências, dívidas, decisões abertas — atualizado após todo commit
│   ├── adr/                # decisões arquiteturais, uma por arquivo
│   └── briefs/             # cópia dos briefs executados
├── nucleo/                 # contratos, prompts, motor de relevância, agrupamento — importável pelo resto
│   ├── modelos/             # contratos Pydantic v2, frozen=True
│   ├── prompts/             # biblioteca de prompts, um arquivo por tipo de saída
│   ├── relevancia/          # cinco critérios, corte, teto
│   ├── agrupamento/         # centróide, janela, reabertura
│   ├── saidas/              # formatadores: cartão, resumo, perfil
│   └── database/queries/    # todas as consultas SQL isoladas aqui
├── coleta/
│   ├── rss/                 # feedparser, trafilatura, canonicalização
│   └── capturas/             # recepção e extração do que vem da extensão
├── perfil/                  # as quatro passagens da análise de contato
├── console/                 # Flask + templates + estáticos
├── extensao/                # extensão do Chrome (manifest v3)
├── config/
│   ├── container.py         # injeção de dependência
│   └── llm_routing.yaml     # roteamento de modelo por tarefa
├── dados/                   # agente.db — fora do git
├── saidas/                  # fora do git
├── tests/
└── scripts/
```

Nome do pacote e da pasta é sempre `agente_nw` — nunca `agente_relacionamento`. Desvio de nomenclatura é corrigido imediatamente.

## 3. Stack

- Python 3.12; Bash para utilitários.
- SQLite exclusivamente, arquivo único em `dados/agente.db`. Nunca compartilhado entre processos.
- Ollama para inferência local, `http://localhost:11434`. Modelo por tarefa definido em `config/llm_routing.yaml` (ver `PLANO.md` seção 3.1) — verificar com `ollama list` antes de sugerir download. Um modelo carregado por vez, salvo quando a máquina tiver memória para manter mais de um (ver `PLANO.md`).
- Embeddings: `bge-m3` (1024 dimensões, multilíngue).
- Índice vetorial: `sqlite-vec`, no mesmo arquivo do banco.
- Contratos: Pydantic v2 com `frozen=True`.
- Arquitetura hexagonal; dependências via `config/container.py`.
- Saída estruturada do LLM sempre em modo JSON (`format: json`); `num_ctx` explícito em toda chamada.
- Interface: console web local em `console/`, Flask, `http://localhost:8765`, só em `127.0.0.1`.
- Coleta em rede social: extensão própria do Chrome (`extensao/`, manifest v3), sempre sob demanda.
- Agendamento: `launchd` (macOS), com recuperação de execução perdida. Nunca laço infinito em processo.
- Testes: pytest. Tipagem: mypy strict. Lint: ruff.

## 4. Regras de alteração

- Mudança cirúrgica: só o que o brief pede.
- Código funcionando não se altera sem evidência de defeito.
- Sem variantes de depuração, sem arquivos paralelos de módulos existentes.
- Sem hardcode de caminhos: resolução dinâmica.
- Texto de fonte externa (notícia, perfil) nunca é alterado ao ser armazenado; limpeza roda antes do hash de deduplicação, não sobre o texto guardado.
- Restrições são estruturais, não procedurais: o que não deve ser visto a jusante é bloqueado na origem, não filtrado depois.
- Antes de diagnosticar erro: "isso funcionava antes?" Responder essa pergunta antes de tocar em código.

## 5. Git

- **Proibido `git add -A`.** Adição arquivo por arquivo, com lista explícita.
- `git status` obrigatório antes de qualquer `add`; arquivo inesperado interrompe a operação.
- Trunk-based em `main`. Sem branches de longa duração, sem recursos avançados de git.
- **Git nunca roda de forma autônoma.** O executor prepara a lista de arquivos e o texto do commit no relatório final; Sidarta autoriza.
- Remoção de arquivo rastreado: `git rm`, com critérios explícitos e exclusão de `__init__.py`, `.gitkeep` e afins.

## 6. Tarefas não assistidas

Podem rodar sem supervisão: coleta RSS, extração, geração de embeddings, agrupamento, pontuação, cartão do assunto.

Requisitos: idempotência e retomada, log em arquivo, kill switch por arquivo sentinela, shards disjuntos se houver mais de um processo, SQLite nunca compartilhado.

**Nunca rodam sozinhos:** git, coleta em rede social (sempre disparada pelo usuário, um contato por vez), alteração de ficha de contato.

## 7. Comportamento do software

- Coleta de assuntos é processamento autônomo de ponta a ponta, sem aprovação por item — o usuário revisa e marca (`usar` / `não usar` / `quero resumo`) depois de pronto, não antes.
- Coleta em rede social só começa por comando explícito do usuário no console, contato por contato; nunca em laço, nunca periódica.
- O sistema não escreve mensagem, não pontua relacionamento e não envia nada — ver `PLANO.md` seção 2. Não reintroduzir essa camada "de passagem" dentro de outro brief.
- O sistema classifica e resume; o usuário nunca recebe lista crua para triar.

## 8. Relatório final obrigatório

Todo brief termina com este bloco preenchido. Sem ele, a sessão é considerada incompleta.

```
## RELATÓRIO FINAL
- Brief executado:
- Arquivos criados:
- Arquivos alterados (com resumo da mudança em uma linha cada):
- Arquivos preservados literalmente na área afetada:
- Testes rodados e resultado:
- Comandos executados:
- Lista de arquivos para `git add` e texto sugerido do commit:
- Pendências e decisões que ficaram abertas:
- `docs/PLAN.md` atualizado: sim/não
```

## 9. Certificação

Uma tarefa só está certificada quando: testes verdes, escopo respeitado (nada além do brief), relatório final completo e `docs/PLAN.md` atualizado. Auditoria independente em doze passes é aplicada ao fim de cada fase de implementação, com validação cruzada em outro modelo.
