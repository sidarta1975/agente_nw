# PLANO.md — agente_nw

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Data desta versão:** 2026-09-12
**Máquina de produção:** MacBook Pro M5 Pro, 48 GB de memória unificada, macOS
**Natureza:** software 100% local. Não há componente em nuvem, não há serviço de terceiros, não há chamada a API de modelo remoto. Nenhum dado sai da máquina.

---

## 1. O que o software é

Um **coletor de assuntos** com **fichas de contato**.

Duas metades que se alimentam:

1. **Coleta contínua de assuntos** — roda sozinha todo dia. Lê fontes públicas (RSS), agrupa o que é a mesma coisa em *assuntos*, pontua, e entrega uma lista curta com resumo. O usuário marca o que serve e o que não serve.
2. **Análise sob demanda de contato** — roda só quando o usuário pede. O agente abre as contas de rede social daquele contato nas abas do navegador do próprio usuário, coleta o que está visível, analisa, e produz um perfil. Desse perfil saem os termos de monitoramento que alimentam a coleta contínua.

O ciclo fecha assim: o usuário indica um contato → o agente analisa e monta o perfil → o perfil vira configuração de coleta → o coletor passa a trazer assuntos que cruzam com aquele contato → o usuário decide o que fazer com eles.

## 2. O que o software NÃO faz

Decisões de escopo, tomadas e fechadas:

- **Não escreve mensagem.** Não gera texto de abordagem, não sugere tom, não propõe como falar com ninguém. O software não sabe qual é a relação entre o usuário e o contato e não vai fingir que sabe. Ele oferece assunto; o uso é decisão do usuário.
- **Não pontua relacionamento.** Não calcula cadência ideal, não avisa "você está negligenciando fulano", não mede tempo desde o último contato.
- **Não envia nada.** Não integra com aplicativo de mensageria, não cria rascunho, não agenda envio.
- **Não roda coleta periódica em rede social.** A coleta em rede social é sempre disparada pelo usuário, um contato por vez.
- **Não usa nuvem.** Nenhuma etapa, nem a mais pesada.

## 3. Decisões fechadas

| Área | Decisão |
|---|---|
| Linguagem | Python 3.12; Bash para utilitários |
| Banco | SQLite, arquivo único em `dados/agente.db` |
| Contratos | Pydantic v2, `frozen=True` |
| Inferência | Ollama local, `http://localhost:11434` |
| Modelo — tarefas simples | `qwen2.5:7b` |
| Modelo — tarefas complexas | `qwen2.5:14b` |
| Embeddings | `bge-m3` (1024 dimensões, multilíngue) |
| Índice vetorial | `sqlite-vec`, no mesmo arquivo do banco |
| Coleta de notícia | `feedparser` sobre RSS; `trafilatura` para extrair o corpo |
| Coleta em rede social | extensão própria do Chrome, sob demanda, usando a sessão já logada do usuário |
| Interface | console web local em `http://localhost:8765`, servido por Flask |
| Agendamento | `launchd` (macOS), com recuperação de execução perdida |
| Saída estruturada do LLM | modo JSON do Ollama, sempre |
| Testes | pytest; tipagem mypy strict; lint ruff |

### 3.1 Roteamento de modelo por tarefa

| Tarefa | Modelo | Razão |
|---|---|---|
| Extrair autor, data e texto de bloco capturado | `qwen2.5:7b` | saída curta em JSON, centenas de chamadas, velocidade importa |
| Pontuar assunto nos cinco critérios | `qwen2.5:7b` | julgamento fechado, nota e uma linha |
| Rotular agrupamento (título do assunto) | `qwen2.5:7b` | saída de 8 palavras |
| Cartão do assunto | `qwen2.5:14b` | precisa separar fato de estimativa e registrar divergência |
| Resumo completo do assunto | `qwen2.5:14b` | linha do tempo, números com fonte, posições em disputa |
| Síntese do perfil do contato | `qwen2.5:14b` | tarefa mais difícil do sistema: material heterogêneo |
| Verificação de lastro do perfil | `qwen2.5:14b` | 7b deixa passar afirmação sem publicação de origem |

Roteamento declarado em `config/llm_routing.yaml`, nunca no código.

Com 48 GB os três modelos ficam carregados ao mesmo tempo (~15 GB): `OLLAMA_KEEP_ALIVE=2h`, `OLLAMA_MAX_LOADED_MODELS=3`, `OLLAMA_NUM_PARALLEL=2`.

**`num_ctx` é obrigatório e explícito em toda chamada.** O padrão do Ollama trunca a entrada em silêncio e devolve resposta plausível sobre material incompleto. Valores: 4096 para extração, 8192 para cartão e resumo, 16384 para síntese de perfil.

## 4. Fases

Ordem obrigatória. Cada fase termina com certificação antes da seguinte começar.

### Fase 1 — Núcleo
Modelos Pydantic, esquema SQLite, `config/container.py`, roteamento de modelo, biblioteca de prompts, camada de consultas SQL isolada. Sem coleta, sem interface.
**Conclui quando:** esquema criado, contratos com teste, uma chamada de exemplo a cada modelo do roteamento passando com JSON válido.

### Fase 2 — Coleta de assuntos
`feedparser` + `trafilatura`, canonicalização de URL, deduplicação por hash e por similaridade, embeddings `bge-m3`, agrupamento por centróide persistente em janela de 7 dias, pontuação pelos cinco critérios, cartão do assunto. Saída em arquivo.
**Conclui quando:** cinco dias seguidos de execução sem intervenção, com assuntos formados por mais de uma fonte.

### Fase 3 — Console web
Flask em `localhost:8765`. Telas: Hoje, Assunto, Contatos, Capturas, Temas, Semana. Marcação (`usar` / `não usar` / `quero resumo`) gravando na hora e realimentando a calibragem.
**Conclui quando:** o ciclo inteiro de leitura e marcação acontece no navegador, sem editar arquivo à mão.

### Fase 4 — Fichas de contato e extensão
Ficha completa (identificação, contas, substância, operacional). Extensão do Chrome que, ao comando do console, abre as abas das contas daquele contato, rola, captura o texto visível e devolve para `localhost:8765`.
**Conclui quando:** um contato real é coletado de ponta a ponta, com blocos extraídos e atribuídos.

### Fase 5 — Análise e perfil
Quatro passagens: extração, agregação sem modelo (embeddings, distribuição de temas, cadência, vocabulário), síntese pelo 14b, verificação de lastro. O perfil sai em duas formas: texto para o usuário ler, e configuração de monitoramento para a máquina usar.
**Conclui quando:** o perfil de um contato gera termos que entram no monitoramento e produzem assunto na rodada seguinte.

### Fase 6 — Histórico e recoleta
Tabela de fatos só-inserção, versionamento de cargo/empresa/cidade, perfil de temas em duas janelas (90 dias e acumulado), detecção de mudança na recoleta, política de retenção.
**Conclui quando:** uma recoleta do mesmo contato produz um relatório de diferença, não uma fotografia nova.

## 5. Regras de coleta em rede social

Estruturais, implementadas no código, não deixadas a critério de quem executa:

- Disparo sempre pelo usuário, um contato por vez. Nunca em laço sobre a lista inteira.
- Uma aba só, reaproveitada em sequência. Aba em segundo plano no Chrome renderiza pela metade.
- Máximo 5 páginas por contato; intervalo aleatório de 4 a 9 segundos entre páginas.
- Teto configurável de contatos por dia, padrão 10.
- Tela de login, verificação ou interstício: para, devolve a aba ao usuário, registra o motivo. Nunca tenta contornar.
- Botão de parar sempre visível no console, com fila à vista.
- Registro da data da última coleta por contato, com aviso no console quando o usuário pedir recoleta antes de 30 dias — visita a perfil é visível para o dono do perfil.
- Fora de escopo: seguidores, seguindo, curtidas, mensagens diretas.

## 6. Extração sem seletor de CSS

As classes das páginas de rede social são ofuscadas e mudam de semana em semana. **Nenhum seletor específico de site no código.** A extensão captura o texto visível dos blocos genéricos da página; o `qwen2.5:7b` extrai autor, data, tipo e conteúdo de cada bloco. Layout muda, o pipeline continua funcionando.

## 7. Governança de documentos

Todo documento (`PLANO.md`, `ARQUITETURA.md`, `PLAN.md`, ADRs, briefs, relatórios, `AGENTS.md`, `README.md`) fica na pasta de documentos do projeto, **nunca é commitado** (`.gitignore`), e é entregue na aba Saídas com caminho próprio e permanente.

Este projeto acrescenta uma categoria que os outros não tinham: **dado pessoal de terceiros dentro do repositório.** O `.gitignore` precisa nascer com isto, e a proibição de `git add -A` do `AGENTS.md` deixa de ser estilo e passa a ser o que evita o acidente:

```gitignore
dados/
saidas/
capturas/
logs/
*.db
*.db-wal
*.db-shm
temas.yaml
temas.local.yaml
*.csv
```

Versionar `temas.exemplo.yaml` com dois temas fictícios, para o repositório continuar clonável.
