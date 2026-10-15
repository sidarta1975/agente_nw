# AGENTS.md — agente_nw

> Coloque este arquivo na raiz do repositório. Claude Code lê antes de qualquer tarefa.
> Padrão herdado dos repositórios lex_hub, pandora_96 e claw_planalto (ferramenta externa, não clonada nesta máquina).

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
│   │   ├── relevancia/       # qualificação, pontuação, piso, tipo (regra do conector)
│   │   ├── agrupamento/      # centróide, janela, reabertura, divisão
│   │   └── saidas/           # cartão, menu, exportação Markdown
│   ├── coleta/
│   │   ├── rss/              # feedparser, trafilatura, canonicalização, google news
│   │   └── capturas/         # leitura de rede social sob demanda (backend: extensao_backend.py)
│   ├── ponte/                 # servidor local 127.0.0.1:8766 + página-ponte (brief 044)
│   ├── perfil/                # importação da agenda, extração de texto, lacunas, centróide de perfil
│   ├── console/                # Flask + templates + estáticos; a tela única (`/`) é a interface principal
│   └── integracoes/          # (Etapa 3)
├── extensao/                  # extensão do Chrome (manifest v3): lê rede social no navegador do usuário
├── scripts/
│   ├── migracoes/             # 001_inicial.sql, 002_..., aplicados em ordem
│   ├── instalar_macos.sh
│   └── verificar.sh          # ruff + mypy --strict + pytest
├── docs/                      # fora do git, exceto o que a governança listar
├── dados/                     # agente.db, backups/ — fora do git
├── saidas/                    # menu_AAAA-MM-DD.md — fora do git
├── logs/                      # fora do git
└── tests/
```

Nome do pacote e da pasta é sempre `agente_nw`. Desvio de nomenclatura é corrigido imediatamente.

## 3. Stack

- Python 3.12 do Homebrew; Bash para utilitários.
- SQLite em modo WAL, `busy_timeout` e `foreign_keys` ligados, arquivo único em `dados/agente.db`. Nunca compartilhado entre processos. `sqlite-vec` carregado na abertura da conexão.
- Ollama para inferência local, subido pelo próprio usuário fora do aplicativo do Ollama (nunca o Ollama.app, nunca `brew services`), acessado pela `ollama_url` de `config/local.yaml` — por máquina. Modelo por tarefa vem do **perfil ativo** de `config/llm_routing.yaml`, escolhido por `perfil_llm` em `config/local.yaml` (ausente = `air16`): `air16` no Air (produção: `qwen3:4b` como único modelo de geração e julgamento, `qwen3:8b` só em `agente_nw calibrar-agrupamento`), `pro48` no Pro (desenvolvimento: `qwen2.5:14b`). Verificar com `ollama list` antes de sugerir download. Tarefas de LLM: `qualificar`, `rotular`, `cartao`, `cruzar_por_que`, `extrair_de_texto`, `extrair_captura_rede_social`, `extrair_pedido` (pedido em texto livre, brief 036), `desempatar_perfil` (pessoa nas listas do usuário, brief 037), `redigir_ganchos` (ganchos e mensagens prontas, brief 038), `extrair_termos_contato` (assuntos que o contato publica, viram buscas de notícia), `descrever_imagem` (descrição das imagens publicadas pelo contato, modelo com visão: `gemma3:12b` no pro48, `gemma3:4b` no air16), `prerotular_calibracao`. `think: false` obrigatório em toda tarefa; o perfil pode omitir a chave do payload com `enviar_think: false`, para modelos sem modo de raciocínio. `bge-m3` para embeddings nos dois perfis. No Air, subir com `OLLAMA_MAX_LOADED_MODELS=2 OLLAMA_KEEP_ALIVE=30m ollama serve`. No Pro, **não subir servidor próprio**: `ollama_url` aponta para a instância compartilhada já existente (`http://127.0.0.1:11435`, mantida pelo `cervello`); nunca parar ou reiniciar essa instância a partir deste projeto.
- Embeddings: `bge-m3` (1024 dimensões, multilíngue).
- Índice vetorial: `sqlite-vec`, no mesmo arquivo do banco.
- Contratos: Pydantic v2 com `frozen=True`.
- Arquitetura hexagonal; dependências via `config/container.py`.
- Saída estruturada do LLM sempre em modo JSON com esquema (`format: json`); `num_ctx` explícito em toda chamada.
- Interface: console web local em `console/`, Flask, `http://localhost:8765`, só em `127.0.0.1`.
- Coleta em rede social: extensão do Chrome do usuário (`extensao/`), comandada pelo programa por uma ponte local (`ponte/`, `127.0.0.1:8766`, token por execução); nunca navegador separado. Abre aba em segundo plano, uma rede por vez, com pausa entre páginas, na hora da consulta, com a sessão do próprio usuário. Ações fixas: `ola`, `abrir`, `estado`, `rolar`, `links`, `imagens`, `fechar`. As imagens publicadas são baixadas só para serem descritas por um modelo de visão (tarefa `descrever_imagem`); a imagem nunca é gravada, só a descrição.
- Agendamento: não existe. Nenhuma tarefa periódica. Toda execução é disparada explicitamente por Sidarta pelo console ou pela CLI.
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
- Quem decide que tema cabe numa mensagem é o usuário (brief 046): o programa não descarta conteúdo por tema (política, saúde, religião…). Em troca, a redação nunca afirma sobre a pessoa o que ela não disse (opinião, posição, adesão), trata fato `[antigo]` ou `[de imagem]` como não atual, e o motor só entrega assunto com relação com o objetivo do pedido (`conector.consulta.minima` é piso necessário).

## 5. Git

- **Proibido `git add -A`.** Adição arquivo por arquivo, com lista explícita.
- `git status` obrigatório antes de qualquer `add`; arquivo inesperado interrompe a operação.
- Trunk-based em `main`. Sem branches de longa duração, sem recursos avançados de git.
- **Git nunca roda de forma autônoma.** O executor prepara a lista de arquivos e o texto do commit no relatório final; Sidarta autoriza.
- Remoção de arquivo rastreado: `git rm`, com critérios explícitos e exclusão de `__init__.py`, `.gitkeep` e afins.

## 6. Tarefas não assistidas

Não existem. Nenhuma etapa do sistema — coleta RSS, extração, agrupamento, qualificação, cruzamento, cartão, leitura de rede social, geração do menu — roda sem que Sidarta a dispare explicitamente pelo console ou pela CLI. Cada disparo é isolado, corresponde a uma consulta com contexto e escreve no banco quando termina.

Requisitos que continuam valendo em toda execução, mesmo sob demanda: idempotência e retomada, log em arquivo, SQLite nunca compartilhado entre processos, desenvolvimento sempre em cópia (`agente_nw copiar-banco`) — o banco real só é tocado por operação autorizada por Sidarta.

A coleta de notícias é resiliente a bloqueio (brief 045): host que responde 429/503 fica em cooldown no banco (`coleta.cooldown_bloqueio_minutos`) e não recebe pedido nem em outro pedido nem depois de reiniciar; cada pedido faz poucas buscas (`coleta.max_consultas_por_pedido`), reaproveita termo buscado há pouco (`coleta.horas_reuso_termo`) e, com o Google bloqueado, cai no Bing News RSS (`coleta/rss/fonte_alternativa.py`, sem chave). Sem notícia nenhuma o pedido conclui com ganchos das publicações e dos temas, e a tela diz de onde vieram as notícias.

A leitura das listas do usuário nas redes (conexões, seguidos, amigos) é sob demanda e com cache local; nunca periódica. A extensão nunca abre mais de uma aba de rede social por vez, respeita `extensao.pausa_entre_paginas_s` entre páginas da mesma rede e só lê (abrir, rolar, ler texto e links): nenhuma ação na rede além disso.

**Nunca rodam sozinhos:** git, leitura de rede social, alteração de ficha de contato, a suíte de testes padrão (`scripts/verificar.sh`, pytest, ruff, mypy) — o executor escreve e mantém o script; quem roda é Sidarta, no terminal dele.

## 7. Comportamento do software

O usuário escreve um pedido em texto livre sobre uma pessoa ou um grupo e um objetivo. O sistema extrai quem, o quê, como e em que registro; reconhece ou cria o contato; decide sozinho o que buscar na notícia; localiza a pessoa nas redes do usuário com confirmação quando há dúvida; lê o que estiver disponível; seleciona assuntos e **redige o conteúdo** (ganchos e mensagens prontas no registro da relação). Nenhum cadastro é pré-requisito: contato, perfil do usuário, temas, tags e fatos são criados e mantidos pelo sistema; o usuário corrige em texto. Não existe envio de mensagem. A interface principal é a tela única do console (brief 039): o usuário escreve a frase, confirma a pessoa quando perguntado, recebe os ganchos, marca "usei" ou "não serve" e corrige em texto livre; as telas antigas (contatos, menu, temas, eu) ficam em "bastidores". O pedido roda em segundo plano, uma tarefa por vez, com `pedido.status` e `pedido.etapa`. Nunca rodam sozinhos: git, leitura de rede social, alteração de ficha de contato.

## 8. Relatório final obrigatório

Todo brief termina com este bloco preenchido. Sem ele, a sessão é considerada incompleta.

Pendência só pode ser (a) decisão de produto, que cabe a Sidarta, ou (b) algo que exige a máquina ou a presença dele — login em rede social, teste com pessoa real, aprovação de limiar. Defeito, inconsistência, limpeza ou verificação que o executor consiga resolver ou rodar sozinho é resolvido antes do relatório, não listado. Quando um critério de aceite depende de rede social ou do modelo real, o executor roda o que está ao seu alcance (por exemplo `agente_nw listas ver --rede instagram --filtro a`) e cola a saída no relatório; o que fica para Sidarta é só o que exige Sidarta.

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
