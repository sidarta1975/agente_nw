> **OBSOLETO.** Rascunho original do `AGENTS.md`, escrito para a metodologia de cinco frentes (Núcleo + ChatGPT + Gemini + Claude + Offline) e para uma pasta chamada `agente_relacionamento/`. A pasta real é `agente_nw` e a estrutura interna mudou (ver `docs/ARQUITETURA.md`). O `AGENTS.md` que vale hoje está na raiz do repositório, corrigido para bater com a arquitetura atual. Mantido só como referência histórica.

# AGENTS.md — Agente de Relacionamento (Núcleo + Offline)

> Coloque este arquivo na raiz do repositório. Claude Code lê antes de qualquer tarefa.
> Padrão herdado dos repositórios lex_hub, pandora_96 e claw.

---

## 1. Papel do executor

Você implementa briefs. Não tem latitude criativa. Se o brief não cobre algo, pare e registre no relatório final como pendência — não invente.

Leia, nesta ordem, antes de qualquer alteração: este arquivo → `docs/PLANO.md` → `docs/ARQUITETURA.md` → `docs/PLAN.md` → o brief da sessão → o código já existente na área afetada.

## 2. Estrutura do repositório

```
agente_relacionamento/
├── AGENTS.md
├── docs/
│   ├── PLANO.md            # plano geral, fases, frentes
│   ├── ARQUITETURA.md      # blocos, contratos, fluxo
│   ├── PLAN.md             # estado vivo: pendências, dívidas, decisões abertas — atualizado após todo commit
│   ├── adr/                # decisões arquiteturais, uma por arquivo
│   └── briefs/              # cópia dos briefs executados
├── nucleo/                 # F1 — pacote importável pelas outras frentes
│   ├── modelos/            # contratos Pydantic v2, frozen=True
│   ├── prompts/            # biblioteca de prompts, um arquivo por tipo de saída
│   ├── relevancia/         # motor de relevância
│   ├── saidas/             # formatadores dos conteúdos entregues
│   └── database/queries/   # todas as consultas SQL isoladas aqui
├── offline/                # F5 — módulos module_NN_nome
│   └── modules/
├── config/
│   ├── container.py        # injeção de dependência
│   └── llm_routing.yaml    # roteamento de modelo por tarefa
├── tests/
│   ├── nucleo/
│   └── offline/modules/module_NN_nome/
└── scripts/                # utilitários Bash
```

Módulos de `offline/` seguem `module_NN_nome`, em inglês, com testes espelhados. Desvio de nomenclatura é corrigido imediatamente.

## 3. Stack

- Python; Bash para utilitários.
- SQLite exclusivamente. Um banco por frente; nunca compartilhado entre processos.
- Ollama para inferência local. Modelos Qwen já instalados na máquina — verificar com `ollama list` antes de sugerir download. Um modelo carregado por vez.
- Embeddings: `multilingual-e5-small` (ou `-large` quando o brief exigir).
- Contratos: Pydantic v2 com `frozen=True`.
- Arquitetura hexagonal; dependências via `config/container.py`.
- Saída estruturada do LLM sempre em modo JSON.
- Testes: pytest. Tipagem: mypy strict. Lint: ruff.
- Agendamento: timers de sistema (systemd user timers) ou cron; nunca laço infinito em processo.

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

Podem rodar sem supervisão: coleta de fontes, geração de embeddings, classificação por regra, sumarização local.

Requisitos: idempotência e retomada, log em arquivo, kill switch por arquivo sentinela, shards disjuntos se houver mais de um processo, SQLite nunca compartilhado.

Nunca rodam sozinhos: git, envio de mensagem a qualquer pessoa, alteração de perfil de contato.

## 7. Comportamento do software

- Processamento autônomo de ponta a ponta. Sem aprovação por item.
- Revisão humana em um único ponto: antes do envio da mensagem. O sistema entrega pronto; o usuário aprova ou descarta.
- O sistema classifica; o usuário nunca recebe lista crua para triar.

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
