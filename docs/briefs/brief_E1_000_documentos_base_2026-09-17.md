# brief_E1_000_documentos_base — Atualizar os documentos-base do repositório para a Proposta v5

**Data:** 17 de setembro de 2026
**Etapa:** 1 (MVP), brief 000 de 14 — dia 1 do calendário
**Executor:** Claude Code
**Repositório:** `/Users/sidarta48/github/agente_nw`
**Leia antes, nesta ordem:** `AGENTS.md` → `docs/PLANO.md` → `docs/ARQUITETURA.md` → `docs/PLAN.md` → este brief → `docs/agente_nw_proposta_comite_v5_2026-09-17.md` → `docs/agente_nw_plano_mvp_air_v3_2026-09-17.md`

---

## 1. Objetivo em uma frase

Reescrever `AGENTS.md`, `docs/PLANO.md`, `docs/ARQUITETURA.md` e `docs/PLAN.md` para que reflitam a Proposta v5 e o Plano de execução v3, fixando o calendário em datas, sem escrever nenhuma linha de código.

## 2. Contexto e o que já existe no repositório

O repositório contém hoje só documentação: `AGENTS.md` na raiz, `docs/PLANO.md`, `docs/ARQUITETURA.md`, `docs/PLAN.md`, `docs/historico/` e os documentos de proposta e plano. Não há código, não há `.git`.

Os quatro documentos-base foram escritos em 12 de setembro para um desenho anterior do produto. Desde então a proposta mudou em pontos estruturais e eles estão desatualizados. **Investigue os quatro antes de alterar** e liste no relatório final, para cada um, o que foi preservado e o que foi substituído. As diferenças conhecidas entre o que está lá e o que a v5 decide:

| Documento | O que diz hoje | O que a v5 e o plano v3 decidem |
|---|---|---|
| `AGENTS.md` | pacote `agente_relacionamento/`, estrutura `offline/modules/module_NN_nome`, embeddings `multilingual-e5-small`, "um modelo carregado por vez", agendamento por systemd/cron, "revisão humana antes do envio da mensagem" | pacote `agente_nw/`, estrutura da seção 2 de `ARQUITETURA.md` reescrita, embeddings `bge-m3`, dois modelos carregados (perfil `air16`), agendamento por `launchd`, não existe envio de mensagem — a revisão humana é a confirmação de tags e a marcação do menu |
| `docs/PLANO.md` | coletor de assuntos com fichas de contato; interface "Hoje" com cartões globais; Trilha B de análise de contato via extensão como fonte principal; roteamento `qwen2.5:7b`/`14b`; máquina de 48 GB | produto da seção 2 da v5 (menu por contato, regra do conector, ficha guiada, coleta em três camadas); quatro etapas da v5 com prazos (3,5 / 3 / 1 / 1 semanas); perfil `air16` como Etapa 1; roteamento da seção 3 da v5 |
| `docs/ARQUITETURA.md` | fluxo com Trilha A (coleta) e Trilha B (extensão); contratos `Item`, `Assunto`, `Contato`, `Conta`, `Captura`, `Publicacao`, `Fato`, `MudancaCampo`, `Perfil`, `Marcacao`; pontuação de cinco critérios com corte 65 e teto 8; console com rota `/` "Hoje" | fluxo da seção 5.2 da v5 (oito passos, saída por contato); modelo de dados da seção 4.1 da v5 com a regra "tabela nasce na etapa que a usa"; contratos da seção 4.2 (`qualificar`, `cruzar` em duas partes, `rotular`, `cartao`, `extrair_de_texto`); regra do conector da seção 2.1; console com as telas Contatos, Menu e Temas; camada de LLM com `think: false`; `launchd` com dois LaunchAgents; filtro sensível; WAL; backup |
| `docs/PLAN.md` | "Fase 1 — Núcleo, não iniciada"; seis decisões abertas; sete armadilhas | estado real: Etapa 1 em execução, brief 000 concluído; próximos passos = briefs 001 a 013 com datas; decisões abertas reduzidas às que a v5 deixa ao comitê; armadilhas atualizadas |

## 3. Escopo

Os quatro documentos-base, mais uma linha de cabeçalho em `PLANO.md` e `PLAN.md` explicitando o papel de cada um. Nada além disso.

### 3.1 `AGENTS.md`

Preservar: papel do executor (implementa briefs, sem latitude criativa), ordem de leitura, regras de alteração (mudança cirúrgica, código funcionando não se altera, sem variantes de depuração, sem hardcode de caminhos, texto de fonte externa nunca alterado ao ser armazenado, restrições estruturais), regras de git (proibido `git add -A`, `git status` antes de `add`, trunk-based, git nunca autônomo), tarefas não assistidas (idempotência, retomada, log, sentinela), relatório final obrigatório, certificação.

Substituir:
- Estrutura do repositório pela da seção 2 de `ARQUITETURA.md` reescrita (item 3.3 abaixo).
- Stack: Python 3.12 do Homebrew; SQLite em modo WAL com `sqlite-vec`; Ollama em `localhost:11434` subido por LaunchAgent do projeto, nunca pelo aplicativo; `qwen3:4b` com `think: false` obrigatório e `bge-m3`; dois modelos carregados (`OLLAMA_MAX_LOADED_MODELS=2`); Pydantic v2 `frozen=True`; arquitetura hexagonal com `config/container.py`; saída estruturada em JSON com esquema; pytest, mypy strict, ruff; `launchd` para agendamento.
- Seção "Comportamento do software": remover toda menção a mensagem e envio. Texto novo: "O sistema classifica e cruza; o usuário confirma tags e marca o menu. Não existe geração nem envio de mensagem. Nunca rodam sozinhos: git, coleta em rede social, alteração de ficha de contato."
- Acrescentar em "Regras de alteração": "Toda alteração de tabela é uma migração numerada em `scripts/migracoes/`. Nenhum brief cria ou altera tabela fora de migração." e "Categorias sensíveis (saúde, religião, política, sindicato, vida sexual, origem racial, menores) nunca chegam ao banco: prompt proíbe e `nucleo/sensivel.py` descarta depois do modelo."
- Acrescentar em "Tarefas não assistidas": "Durante uma medição de aceite, o único processo que escreve em `dados/agente.db` é o ciclo. Desenvolvimento usa cópia (`agente_nw copiar-banco`)."

### 3.2 `docs/PLANO.md`

Primeira linha após o título: `> Plano geral: o que o software é, decisões fechadas, etapas e prazos. Não muda a cada commit; muda a cada versão aprovada da proposta.`

Conteúdo, nesta ordem, condensado da v5 (não copiar a v5 inteira; o `PLANO.md` é o resumo executivo que o executor lê em cinco minutos):
1. O que o software é — seção 2 da v5 com as três regras, a regra do conector (2.1) e a ficha guiada com as três camadas de coleta (2.2), em forma resumida.
2. O que não faz — mensagem, tom, pontuação de relacionamento, envio, API de LLM, raspagem em massa, reconhecimento facial, áudio como entrada.
3. Decisões fechadas — a tabela da seção 3 da v5, inteira.
4. Etapas — as quatro etapas da v5 com o que entrega cada uma, prazo (3,5 / 3 / 1 / 1 semanas) e condição de passagem, apontando para as seções da v5.
5. Perfis de hardware — a tabela da seção 6.2 da v5, com `air16` como Etapa 1.
6. Governança de documentos — manter a seção 7 do `PLANO.md` atual, atualizando a lista do `.gitignore` para: `dados/`, `saidas/`, `capturas/`, `logs/`, `*.db`, `*.db-wal`, `*.db-shm`, `temas.yaml`, `temas.local.yaml`, `fontes.yaml`, `config/local.yaml`, `*.csv`. Manter a regra "documentos não são commitados", com uma exceção explícita: `AGENTS.md` é commitado (decisão nº 1 do `PLAN.md` antigo, fechada pela v5).

### 3.3 `docs/ARQUITETURA.md`

Primeira linha após o título: `> Arquitetura hexagonal. Dependências resolvidas em config/container.py. Nenhum módulo instancia cliente de LLM, conexão de banco ou cliente HTTP diretamente.` (manter)

Seções, nesta ordem:
1. **Fluxo** — o ciclo diário da seção 5.2 da v5, em diagrama de texto, com os oito passos (coleta → embedding e agrupamento → qualificação pela união dos temas dos perfis ativos → pré-seleção por contato → pontuação e piso → cruzamento → cartão → entrega por contato). A extensão do Chrome, a exportação de conversa e a mídia aparecem como entradas da ficha marcadas "Etapa 2".
2. **Estrutura do repositório** — esta, literal:
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
│   ├── perfil/               # importação da agenda, extração de texto, lacunas, centróide de perfil
│   ├── console/              # Flask + templates + estáticos
│   └── integracoes/          # (Etapa 3)
├── extensao/                 # (Etapa 2) extensão do Chrome
├── scripts/
│   ├── migracoes/            # 001_inicial.sql, 002_..., aplicados em ordem
│   ├── instalar_macos.sh
│   ├── verificar.sh          # ruff + mypy --strict + pytest
│   └── launchd/              # plists: ollama e ciclo
├── docs/                     # fora do git, exceto o que a governança listar
├── dados/                    # agente.db, backups/ — fora do git
├── saidas/                   # menu_AAAA-MM-DD.md — fora do git
├── logs/                     # fora do git
└── tests/
```
3. **Contratos de dados** — tabela da seção 4.1 da v5, marcando quais tabelas nascem na migração 001 (Etapa 1: `schema_version`, `tema`, `perfil`, `perfil_tema`, `fonte`, `item`, `assunto`, `assunto_contato`, `fato`, `fila_extracao`, `descarte_sensivel`, `fila_revisao`, `progresso`, tabelas vetoriais) e quais ficam para migrações das Etapas 2 e 4 (`conta`, `captura`, `midia_processada`, `conversa_tema`, `pacote_troca`).
4. **Contratos do motor** — seção 4.2 da v5 inteira (`qualificar`, `cruzar` em duas partes com a regra do nível, `rotular`, `cartao`, `extrair_de_texto`), com os exemplos JSON.
5. **Regra do conector** — seção 2.1 da v5 e a fórmula 50/30/20, o piso 0,55 ou 0,8, os pesos de nível 1,0/0,7/0,4, e a frase "pontuação e piso são determinísticos; o modelo só escreve o por_que".
6. **Agrupamento** — manter a seção atual (centróide, janela de 7 dias, encerramento, reabertura, divisão acima de 12 itens), trocando "0,82" por "limiar inicial 0,82, calibrado (ver `limiares.yaml` e ADR)".
7. **Qualificação** — substitui a antiga "Pontuação (cinco critérios)": candidatos pela união dos temas de todos os perfis ativos, teto 40/dia, contrato `qualificar`, corte 0,6/0,6, fonte independente (domínio diferente e texto divergindo mais de 30%).
8. **Camada de LLM** — manter a seção atual e acrescentar: `think: false` como parâmetro fixo do cliente; `OLLAMA_MAX_LOADED_MODELS=2` e `OLLAMA_KEEP_ALIVE=30m` no LaunchAgent do servidor; nunca o aplicativo do Ollama.
9. **Filtro de categorias sensíveis** — nova: lista de termos por categoria em `nucleo/sensivel.py`, aplicado depois de todo contrato que produz tag ou fato, registro em `descarte_sensivel` sem o trecho.
10. **Console web** — Flask, `127.0.0.1:8765`, rotas: `GET /contatos`, `GET /contato/<id>`, `POST /contato/<id>/ativar`, `POST /contato/<id>/tags/confirmar`, `POST /contato/<id>/texto`, `GET /menu/<perfil_id>`, `POST /marcar`, `GET /temas`, `POST /temas`, `POST /processar`. Só escuta em `127.0.0.1`.
11. **Agendamento** — dois LaunchAgents em `scripts/launchd/`: `br.agente_nw.ollama.plist` (sobe `ollama serve` com as duas variáveis, `RunAtLoad`, `KeepAlive`) e `br.agente_nw.ciclo.plist` (`StartCalendarInterval` 05h00, recuperação de execução perdida, gatilho no login com 5 minutos de atraso, "já rodou hoje" verificado no banco). Etapas retomáveis; sentinela de parada. Nunca rodam sozinhos: git, coleta em rede social, alteração de ficha.
12. **Banco** — WAL, `busy_timeout` 5 s, `foreign_keys` on, `sqlite-vec` carregado na abertura; backup diário pela API de backup, `dados/backups/`, retenção 7 dias; `copiar-banco` para desenvolvimento.

### 3.4 `docs/PLAN.md`

Primeira linha após o título: `> Estado vivo: fase atual, próximos passos, decisões abertas, dívidas, armadilhas. Atualizado após todo commit e ao fim de todo brief.`

Conteúdo:
- **Última atualização:** data do dia. **Fase atual:** Etapa 1 — MVP no MacBook Air M3 16 GB; brief 000 concluído. **Estado do repositório:** só documentação; sem `.git` ainda (o `git init` e o primeiro commit são listados no relatório final deste brief para o usuário executar).
- **Próximos passos:** a tabela de briefs 001 a 013 na ordem de execução do plano v3, com as datas da seção 5 deste brief.
- **Decisões em aberto:** só uma — aceitar ou não o risco de restrição de conta no LinkedIn com a captura assistida (Etapa 2), decisão do comitê. As seis decisões abertas antigas são movidas para o histórico como fechadas, com a resposta de cada uma (pacote `agente_nw`; briefs em `docs/briefs/`; `AGENTS.md` commitado; importações em fila; quantização do 14b e comparação com Qwen 3 ficam absorvidas pelo protocolo de promoção da seção 6.4 da v5).
- **Dívidas conhecidas:** nenhuma.
- **Armadilhas já identificadas — não redescobrir:** manter as sete atuais que continuam válidas (num_ctx padrão trunca em silêncio; aba em segundo plano renderiza pela metade; seletor de CSS quebra; release em quinze portais parece denso; visita a perfil é visível; dado pessoal no repositório) — retirar a nº 6 sobre `nomic-embed-text`/`bge-m3` em 8 GB, que não se aplica ao Air — e acrescentar: modo de raciocínio do Qwen3 quebra o JSON (`think: false` sempre); `launchctl setenv` não sobrevive a reboot (variáveis no plist); amostra de calibração aleatória não tem pares na faixa de dúvida (estratificar); tema de curiosidade não pode virar conector; bug de escrita durante medição invalida os cinco dias (desenvolver sobre cópia); "Qwen 2.5 4B" não existe.
- **Histórico de decisões:** manter o de 12/09 e acrescentar as de 17/09: produto é menu por contato com regra do conector; máquina-alvo Air M3 16 GB; `qwen3:4b` + `bge-m3`; captura assistida reinstalada; WhatsApp só por exportação; mídia com esquema fechado, áudio fora; sem API em nenhuma etapa; prazos 3,5 / 3 / 1 / 1 semanas.

## 4. Fora de escopo, com justificativa

- Qualquer código, `pyproject`, `.gitignore`, esquema: são do brief 001 e 002. Este brief existe para que o executor dos briefs seguintes leia documentos coerentes; misturar código aqui contamina a leitura.
- Reescrever a proposta ou o plano: são documentos aprovados; os documentos-base derivam deles, não o contrário.
- `git init`: git nunca roda pelo executor. O comando fica no relatório final.

## 5. Decisões tomadas e decisões deixadas abertas

Tomadas neste brief:
- **Dia 1 = segunda-feira, 21 de setembro de 2026.** Calendário completo na seção 6, passo 5. Se o usuário fixar outro dia 1, todo o calendário desloca-se pelo mesmo número de dias úteis, preservando fins de semana na medição e o feriado de 12 de outubro.
- Os documentos-base são escritos em português do Brasil, sem códigos de tarefa soltos no corpo; os briefs são referidos pelo nome do arquivo.
- `PLANO.md` e `PLAN.md` permanecem dois arquivos com papéis distintos, cada um com a linha de cabeçalho que diz qual é o seu.

Deixadas abertas: nenhuma.

## 6. Passos de execução

1. Ler os sete documentos da ordem de leitura. Anotar, para cada um dos quatro documentos-base, as seções que serão preservadas literalmente e as que serão substituídas. Essa anotação vai para o relatório final.
2. Reescrever `AGENTS.md` conforme 3.1. Conferir que nenhuma menção a "mensagem", "envio", "WhatsApp" como canal de saída, `agente_relacionamento`, `offline/modules`, `multilingual-e5-small` ou "um modelo carregado por vez" sobrou.
3. Reescrever `docs/ARQUITETURA.md` conforme 3.3, na ordem das doze seções. Copiar a estrutura de repositório literalmente. Copiar os contratos JSON da seção 4.2 da v5 literalmente.
4. Reescrever `docs/PLANO.md` conforme 3.2. Tamanho-alvo: metade da v5. Toda decisão da tabela da seção 3 da v5 aparece.
5. Reescrever `docs/PLAN.md` conforme 3.4, com este calendário na tabela de próximos passos:

| Brief | Dia | Data |
|---|---|---|
| 000 documentos-base | 1 | seg 21/09/2026 |
| 001 esqueleto | 2 | ter 22/09 — usuário escreve `temas.yaml` |
| 002 esquema, migrações, backup | 3 | qua 23/09 — `importar-temas` passa a gravar no banco |
| 003 cliente de LLM e embeddings | 4 | qui 24/09 |
| 006 coleta RSS e Google News | 5 | sex 25/09 — usuário roda `agente_nw coletar` diariamente daqui em diante |
| 004 filtro sensível e extrator | 6 | seg 28/09 |
| 005 importação da agenda | 7 | ter 29/09 — usuário ativa 10 contatos e confirma tags |
| 007 agrupamento e calibração | 8 | qua 30/09 — três dias de coleta acumulados |
| 008 qualificação e cartão | 9 | qui 01/10 |
| 009 regra do conector e menu | 10 | sex 02/10 |
| 011 exportação Markdown | 11 | seg 05/10 |
| 012 ciclo e LaunchAgents | 12 | ter 06/10 — primeiro reboot |
| 013 medição (cinco ciclos) | 13–17 corridos | qua 07/10 a dom 11/10 — segundo reboot sex 09/10 |
| 010 console, sobre cópia do banco | 13–16 úteis | qua 07/10, qui 08/10, sex 09/10 e ter 13/10 (seg 12/10 é feriado) |
| 013 relatório e certificação; 010 apontado para o banco real | dia útil seguinte | ter 13/10/2026 |

6. Reler os quatro documentos em sequência como se fosse o executor do brief 001 e responder por escrito, no relatório final, a três perguntas: "sei qual é o produto?", "sei onde cada arquivo vai?", "sei o que é a regra do conector?". Se alguma resposta for não, corrigir antes de encerrar.
7. Preencher o relatório final. Incluir nele, para o usuário executar: `git init`, a lista de arquivos do primeiro commit (só `AGENTS.md` — os demais documentos ficam fora do git pela governança) e o texto sugerido do commit.

## 7. Critérios de aceite

1. Os quatro documentos não contradizem a Proposta v5 em nenhum ponto verificável: modelo de dados, contratos, regra do conector com nível, perfis de hardware, etapas e prazos, calendário.
2. `grep -il "mensagem\|envio\|agente_relacionamento\|offline/modules\|e5-small" AGENTS.md docs/PLANO.md docs/ARQUITETURA.md docs/PLAN.md` retorna apenas ocorrências que negam ("não escreve mensagem", "não envia") ou que estão no histórico de decisões.
3. `docs/PLAN.md` lista os 13 briefs restantes na ordem de execução com as datas da seção 6, e tem exatamente uma decisão em aberto.
4. `PLANO.md` e `PLAN.md` começam com a linha de cabeçalho que declara o papel de cada um.
5. As três perguntas do passo 6 respondidas "sim" no relatório final.

## 8. Riscos e como reverter

- **Risco:** perder regra válida do `AGENTS.md` antigo na reescrita. **Reversão:** os originais dos quatro documentos são copiados para `docs/historico/2026-09-17_pre_v5/` antes de qualquer alteração; a lista "preservado / substituído" do relatório final permite conferir.
- **Risco:** o executor "melhorar" a v5 ao condensá-la. **Controle:** onde houver dúvida, copiar literalmente; o `PLANO.md` pode ser mais curto que a v5, nunca diferente dela.
- **Risco:** calendário com dia 1 diferente do fixado. **Reversão:** a tabela é deslocada em dias úteis; não há outra dependência de data.

## 9. Relatório final obrigatório

```
## RELATÓRIO FINAL
- Brief executado: brief_E1_000_documentos_base_2026-09-17
- Arquivos criados:
- Arquivos alterados (com resumo da mudança em uma linha cada):
- Arquivos preservados literalmente na área afetada:
- Para cada documento-base: seções preservadas / seções substituídas:
- Respostas às três perguntas do passo 6:
- Testes rodados e resultado: (não se aplica — sem código; registrar o grep do aceite 2)
- Comandos executados:
- Lista de arquivos para `git add` e texto sugerido do commit (inclui `git init`):
- Pendências e decisões que ficaram abertas:
- `docs/PLAN.md` atualizado: sim/não
```
