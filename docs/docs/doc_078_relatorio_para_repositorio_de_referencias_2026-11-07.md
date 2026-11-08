# Relatório para o repositório central de referência — agente_nw (v2, corrigida)

**Data:** 2026-11-07 · **Commit lido:** `af2a09f` (main, 2026-11-06, brief 077) · **Árvore de trabalho:** limpa (`git status` vazio) · **Correção v2:** D-02 e D-05 deixaram de ser divergências (documento histórico e resíduo anterior à remoção do filtro). Fonte de verdade para o comportamento atual: `AGENTS.md`, `PLAN.md`, `ARQUITETURA §8` e o código. **Natureza:** relatório só de leitura; nada de código, banco ou documento existente foi alterado.

---

## 0. Como foi feito e o que ficou de fora

**Método.** Li `AGENTS.md`, `docs/PLAN.md`, `docs/PLANO.md`, `docs/ARQUITETURA.md`, o histórico em `docs/historico/`, os relatórios `docs/docs/doc_064` a `doc_077`, o código de `agente_nw/`, `config/`, `scripts/`, `extensao/` e o histórico do git (`git log`, `git blame`, `git ls-files`, `git worktree list`, `git branch`; só leitura). Banco: copiei `dados/agente.db` para uma área temporária da sessão, fora do repositório, e abri a cópia em modo somente leitura. Só contagens, tamanhos e datas; nenhum texto de pessoa, notícia ou publicação foi lido ou reproduzido aqui.

**Limites (marcados "não conferido" no corpo):**

- **Nenhum teste foi executado.** Os binários do `.venv` são de macOS e a ponte roda em Linux (AGENTS §11); também não rodei `uv`. Os números de testes vêm dos relatórios dos briefs, citados com o arquivo. Contagem estática por mim: 158 arquivos em `tests/` e 850 funções `def test_` (a diferença para os 979 do relatório do brief 077 pode ser parametrização; não conferido).
- **O banco medido é o desta máquina (Pro, desenvolvimento: `perfil_llm: pro48` em `config/local.yaml`).** O arquivo foi gravado pela última vez em 2026-10-25 e está na migração 14 (o código vai até a 019). O banco de produção do Air não está acessível daqui. Todo número de banco abaixo é "cópia do arquivo de 2026-10-25, medida em 2026-11-07".
- **Um efeito colateral mínimo:** uma única chamada de `git status` foi feita sem a opção de não travar o índice; ela pode ter atualizado o cache de estatísticas do `.git/index` (não altera conteúdo, histórico nem o HEAD, que continua em `af2a09f`). As demais usaram `--no-optional-locks`.
- **Não comparei** os 85 documentos do Projeto no claude.ai com o disco; só os arquivos do repositório.
- Número do relatório: usei `078`, o próximo da sequência única de briefs e DOCs (AGENTS §10), porque o maior encontrado em `docs/briefs/` e `docs/docs/` é 077.

---

## 1. Rascunho do ESTADO_ATUAL.md

> Texto pronto para colar. Datas e contagens são desta medição.

# ESTADO_ATUAL — agente_nw

**Versão:** 1 · **Fotografia de:** 2026-11-07 · **Commit:** `af2a09f` (main) · **Origem:** relatório doc_078.

## O que é

Console local para quem escreve um pedido em texto livre sobre uma pessoa ou grupo e um objetivo. O sistema extrai quem, o quê, como e em que registro; reconhece ou cria o contato; localiza a pessoa nas redes do usuário (com confirmação quando há dúvida); lê o que estiver disponível (redes, conversa do WhatsApp, notícias); e redige uma mensagem-base mais, quando há notícia ligada ao pedido, ganchos de notícia. Não envia nada. Tudo é disparado por Sidarta (console ou CLI); não existe agendamento. (AGENTS §6 e §7.)

## Em andamento e parado

| Item | Situação | Motivo |
|---|---|---|
| Em execução | Nenhum. `docs/PLAN.md` diz "Doing: (nenhum)" e a árvore está limpa | — |
| Briefs 041 (continuidade de conversa), 042 (medição de uma semana), 043 (documentação e comitê) | Não iniciados | PLAN: "ordem sugerida; Sidarta decide". Nenhum motivo técnico registrado |
| Backlog 063-1 a 063-4, 066-1, 068-2, 068-3, 076-2 | Parados | Marcados `nice` ou `degrada`; sem dono |
| 24 testes reais pendentes de Sidarta (PLAN, "Pendências de Sidarta") | Parados | Exigem pessoa real, a extensão no Chrome e o Pro |
| Decisão aberta nº 1: risco de restrição de conta no LinkedIn com captura assistida | Aberta | Decisão do comitê |
| Worktree `/Users/sidarta48/github/agente_nw_040` (branch `brief-040`, commit `4a012fc`) | Registrada no git como `prunable` | A pasta já não existe (AGENTS §12 cita o caso) |
| Banco de desenvolvimento | Defasado | Na migração 14; o código tem até a 019. Ver §1 "Banco" e divergência D-01 |

## Módulos (linhas de Python, `wc -l`, 2026-11-07; total 15.266 em `agente_nw/`)

| Pacote | O que faz | Maiores arquivos |
|---|---|---|
| `agente_nw/nucleo/` | Regras do produto: pedido, fluxo, localização, relevância, redação, agrupamento, LLM, prompts, banco | `llm.py` 632, `relevancia/cruzamento.py` 530, `fluxo.py` 482, `localizacao.py` 412, `redacao.py` 365 |
| `agente_nw/nucleo/database/queries/` | Todo o SQL (um arquivo por assunto) | `perfis.py` 657 |
| `agente_nw/nucleo/prompts/` | 11 módulos de prompt, todos com `VERSAO`, mais `seguranca.py`; 9 dos 11 usam o cerco de dado externo (ficam de fora `extrair_pedido` e `descrever_tema`) | `redigir_ganchos.py` 298 |
| `agente_nw/coleta/rss`, `capturas`, `whatsapp` | Notícias (Google News, Bing News, feeds), leitura de redes pela extensão, conversa do WhatsApp | `rss/leitor.py` 365, `capturas/listas.py` 408 |
| `agente_nw/perfil/` | Agenda (macOS e CSV do Google), extração de texto livre, inferência de temas do usuário | `inferencia.py` 283 |
| `agente_nw/ponte/` | Servidor local `127.0.0.1:8766` entre o programa e a extensão | `servidor.py` 282 |
| `agente_nw/console/` | Console web `127.0.0.1:8765` (Flask) | `app.py` 1.043 |
| `agente_nw/cli.py` | Linha de comando | 1.494 |
| `agente_nw/integracoes/` | Pacote vazio (só `__init__.py`) | — |
| `extensao/` | Extensão do Chrome v1.1.0, 7 ações fixas: `ola`, `abrir`, `estado`, `rolar`, `links`, `imagens`, `fechar` | — |
| `config/` | `container.py`, `limiares.yaml`, `llm_routing.yaml`, `local.yaml` (da máquina), exemplos | — |
| `scripts/` | `verificar.sh` (gate), `agente_entregar.sh`, `agente_lacunas.py`, `commitar.sh`, `instalar_macos.sh`, 19 migrações em `migracoes/` | — |
| `.claude/` | Hooks `guarda_comando.py` e `lint_arquivo.py`, skill `executar` | — |

## Comandos (`agente_nw ...`)

`verificar-ambiente`, `importar-temas`, `migrar`, `backup`, `copiar-banco`, `restaurar-backup`, `coletar`, `processar-fila`, `agrupar`, `calibrar-agrupamento`, `certificar`, `qualificar`, `cartao`, `cruzar`, `menu`, `exportar-menu`, `ler-marcacoes`, `importar-agenda`, `ficha`, `ativar`, `confirmar-tags`, `console`, `ler-rede-social`, `pedir`, `preparar`, `extensao instalar|testar`, `listas atualizar|ver`, e `calibrar-conector` (nome reservado, ainda sem implementação: `COMANDOS_RESERVADOS` em `cli.py:60`). O comando `ciclo` não existe mais (removido no brief 016).

## Páginas do console

17 templates em `agente_nw/console/templates/` e 50 decoradores de rota em `console/app.py`. Principais: `/` (caixa de texto e lista de contatos), `/pedido/<id>` (e `/pessoa`, `/lista`, `/corrigir`, `/tentar-de-novo`, `/gancho/...`, `/nota`), `/pessoa/<id>` (e `/pedir`, `/sem-redes-sociais`, `/contar`, `/trocar-perfil`, `/whatsapp/...`), `/contatos` e `/contatos/<id>/...` (ficha, editar, apagar, unir, redes sociais), `/menu` (bastidores), `/eu`, `/temas`.

## Banco `dados/agente.db` (cópia do arquivo de 2026-10-25, medida em 2026-11-07)

**Migração aplicada: 14 (aplicada em 2026-10-25). Migrações no código: 19.** Faltam 015 a 019 (conversa do WhatsApp, gênero gramatical, preferências do usuário/temas, rastreio de molde, proveniência). `integrity_check` = ok; `foreign_key_check` = 0 violações.

| Tabela | Linhas | Observação |
|---|---|---|
| `perfil` | 2.202 | 2.201 contatos (todos `ativo=0`) + 1 usuário; 2.201 criados em 2026-10-12 |
| `perfil_tema` | 3.414 | 3.285 `importada` + 129 `sugerida`; 0 confirmados; só de contatos |
| `tema` | 159 | 0 têm vetor (`vetor_tema` = 0) |
| `lista_rede_social` | 1.336 | linkedin 554, instagram 440, x 337, facebook 5; lidas em 12–13/10 |
| `rede_social` | 10 | 5 perfis com rede confirmada; `rede_sem_perfil` 4 |
| `fato` | 149 | 22 perfis; 66 de LinkedIn, 33 de imagem, 8 de Facebook |
| `item` (notícias) | 712 | coletadas de 13 a 25/10; 511 com vetor |
| `assunto` | 413 | todos `encerrado`; 62 sem título e sem qualificação; 0 com cartão |
| `assunto_contato` | 38 | 15 conector, 10 viável com esforço, 13 fora do domínio |
| `fonte` | 216 | 196 agregador, 11 especializada, 7 veículo, 2 oficial; 12 com item |
| `fonte_execucao` | 285 | 2026-10-13 a 2026-10-25 |
| `pedido` | 35 | todos `concluido`; 8 com contato ambíguo; 5 sem perfil |
| `consulta_contato` | 13 | 2026-10-13 a 2026-10-25 |
| `gancho_uso` | 17 | todos `entregue`; nenhum `usado`; nenhum comentário |
| `fila_extracao` | 571 | todas `notas_agenda`; 151 processadas, 149 com erro, 271 pendentes |
| `fila_revisao` | 232 | 229 `extrair_de_texto`, 2 `redigir_ganchos`, 1 `extrair_pedido`; 0 resolvidas |
| `descarte_sensivel` | 4 | categoria `saude`; datas de 13 e 14/10, anteriores à remoção do filtro (brief 046) |
| `nota_contato` | 0 | — |
| `progresso` | 1 | etapa `coleta`, 2026-10-25 |

Logs de chamadas ao modelo: `dados/logs/chamadas_llm.jsonl` (última gravação 2026-10-15) e `console_chamadas_llm.jsonl` (2026-10-25). Nenhuma chamada real ao modelo foi registrada depois dos briefs 064 a 077.

## Decisões em vigor

1. Python 3.12 (Homebrew), SQLite em WAL, um arquivo, nunca compartilhado entre processos. Arquitetura hexagonal, contratos Pydantic v2 `frozen`, dependências por `config/container.py`.
2. Ollama sempre subido pelo próprio usuário; no Pro, instância compartilhada `127.0.0.1:11435` (mantida pelo `cervello`), nunca parar ou reiniciar a partir deste projeto. `think: false`, `format: json` e `num_ctx` explícitos em toda chamada.
3. Perfis de máquina: `air16` (produção, `qwen3:4b`) e `pro48` (desenvolvimento, `qwen2.5:14b`); embeddings `bge-m3`.
4. Geração por API (Anthropic, Gemini, OpenAI) é opcional e só liga com chave em `ia_api` (`config/local.yaml`); só `selecionar_cliente_llm` decide o provedor; embeddings sempre no Ollama local. Com chave, o texto dos prompts sai da máquina.
5. Antes de carregar modelo no Ollama local o projeto consulta o `porteiro` (brief 077); falhou ou não existe, roda como sempre.
6. Console e ponte só em `127.0.0.1`. Redes sociais só pela extensão do Chrome do usuário: uma rede por vez, uma aba, com pausa, só leitura. Imagem nunca é gravada, só a descrição.
7. Sem agendamento. Nunca rodam sozinhos: leitura de rede social, alteração de ficha, operação no banco real.
8. O usuário decide o tema; o programa não descarta conteúdo por tema (brief 046). Em troca, a redação nunca afirma sobre a pessoa o que ela não disse, trata fato `[antigo]` e `[de imagem]` como não atual, e só entrega assunto com relação com o objetivo (`conector.consulta.minima` 0,45 mais o juízo do modelo, brief 049).
9. Texto de terceiro entra nos prompts cercado como dado, nunca como instrução (briefs 068/069).
10. Git: proibido `git add -A`; commit e push só por `scripts/agente_entregar.sh`, com gate verde (ruff, mypy strict, pytest) e manifesto em `logs/`. Não criar `CLAUDE.md` (AGENTS.md é lido sozinho).
11. Estado local (banco e `docs/`) vale numa única árvore de trabalho; nunca numa worktree (AGENTS §12). O `.gitignore` exclui `docs/*`: só o `AGENTS.md` é rastreado.
12. Cada alteração de tabela é uma migração numerada em `scripts/migracoes/`.

## Pendências e dívidas (resumo; detalhe em `docs/PLAN.md`)

Dívidas numeradas abertas: 2, 4, 6, 7, 9, 10; mais 055-1, 055-2, 057-5, 058-3, 059-2, 061-4, 048-6, 040-5, 066-2, 071-1, 075-1, 075-2, 075-3, 076-3, 077-1, 077-2, 077-4. Itens listados mas já resolvidos ou obsoletos (ver §6): 066-3 (corrigida pelo brief 067), 074-1 (arquivos antigos não existem mais) e a dívida 7 (desatualizada, D-04). A dívida 2 não foi conferida (D-15).

## Caminhos principais

`AGENTS.md` · `docs/PLAN.md` (estado vivo) · `docs/PLANO.md` e `docs/ARQUITETURA.md` (parcialmente desatualizados) · `docs/briefs/` (61 arquivos) · `docs/docs/` (30 relatórios) · `docs/historico/` · `docs/adr/adr-0001-limiar-agrupamento.md` · `config/limiares.yaml`, `config/llm_routing.yaml`, `config/local.yaml` · `scripts/migracoes/` · `scripts/agente_entregar.sh` · `.claude/hooks/guarda_comando.py` · `agente_nw/nucleo/llm.py` · `agente_nw/nucleo/fluxo.py` · `agente_nw/nucleo/redacao.py` · `agente_nw/nucleo/relevancia/cruzamento.py` · `extensao/` · `dados/agente.db`, `dados/logs/` · `logs/entregue_*.txt` (manifestos de entrega). Pasta `_quarentena_outro_usuario_2026-10-08/` (3 itens, ignorada pelo git) e `Claude outputs/` (cópias de documentos).

---

## 2. Rascunho do CONTEXT.md

### 2.1 O que o projeto já tem e como adaptar ao modelo

| Já existe | Conteúdo | Como entra no modelo |
|---|---|---|
| `docs/PLAN.md` (43 KB) | Resumo, Doing, Backlog, Done (30 dias), Pendências, Decisões em aberto, Dívidas, 31 armadilhas | A parte "Done" alimenta o CONTEXT; Resumo, Doing, Pendências, Dívidas e Armadilhas viram o ESTADO_ATUAL. O PLAN deixaria de ser lido inteiro |
| `docs/historico/PLAN_historico_ate_2026-10-25.md` | Decisões por data de 12/09 a 15/10, cobrindo briefs 001–013 e 031–050 | Fonte direta das entradas antigas |
| `docs/docs/doc_NNN_*.md` (30) | Relatório final de cada brief, com saída do gate colada e tabela de lacunas | Fonte de "o que entregou" e de evidência |
| `docs/briefs/` (61) | Briefs 031–077 e E1_000–E1_013 | Fonte de nome e data do brief |
| `git log` (100 commits) | Cada commit cita o brief | Fonte do campo "commit" |
| `logs/entregue_NNN_*.txt` | Manifesto de arquivos e mensagem por entrega | Prova de escopo |

**Lacunas que o CONTEXT teria de cobrir.** (a) Os briefs 014 a 030 não têm brief no disco nem entrada no histórico; o próprio histórico avisa "o histórico dos briefs 014–030 não está aqui". Só há 10 commits (014–019, 022–025). Para 020, 021 e 026–030 não achei commit com o número (não conferido: podem ter sido feitos e comitados sem citar o número, ou não executados; o Projeto lista 029 e 030, mas não conferi). (b) Os briefs 051–054 são documentos de avaliação (`docs/docs/doc_051`–`054`) sem código. (c) Numeração dupla: o commit `ce006a5` e `ce03577` chamam "brief 013" o que o disco chama de `brief_E1_013`. (d) O `.gitignore` exclui `docs/*`: se o CONTEXT.md ficar em `docs/`, nunca entra num commit, como já ocorre com o PLAN. **Decisão de Sidarta:** colocar os dois documentos na raiz (rastreados) ou em `docs/` (fora do git, regra atual do §12).

**Formato proposto da entrada:** `data · brief · o que entregou · decisão relevante · commit`. O campo data é a data do commit (fuso do committer); em três casos o PLAN usa outra data (D-09).

### 2.2 Entradas (rascunho)

#### Frente única: produto de pedido em texto livre (cronológico)

> As quatro fases abaixo são um agrupamento por data feito neste relatório; não são as "Etapas" 1 a 4 da proposta v5 (que têm outro significado no plano).

**Fase A — coletor de assuntos no Air (plano v5), 2026-09-17 a 09-20**

| Data | Brief | Entregou | Decisão relevante | Commit |
|---|---|---|---|---|
| 09-18 | E1_000 documentos base | AGENTS.md (Proposta v5) | Produto vira "menu por contato com regra do conector"; Etapa 1 no Air M3 16 GB com `qwen3:4b` + `bge-m3` (decisões de 09-17) | `d7b679a` (associação por mensagem; não conferido) |
| 09-18 | 001 esqueleto | Pacote, config, scripts de verificação | — | `27cb571`, `148d664` |
| 09-18 | 002 esquema/migrações/backup | SQLite WAL, migração numerada, backup, `importar-temas` | `importar-temas` rodou de verdade no banco e gravou 2 temas fictícios (dívida 2) | `21592b4`, `09ed4bf` |
| 09-18 | 003 cliente Ollama e embeddings | Cliente único, cosseno, centróide | "token repeat limit" do Ollama tratado como falha de tentativa (correção feita na sessão do 004, autorizada) | `167604e`, `2654c8b` |
| 09-18 | 004 filtro sensível e extrator | Extrator de texto livre | A causa do JSON ruim era o prompt (exemplo igual à entrada), não o modelo: armadilha 24. O filtro sensível foi removido no 046 | `91b7286`, `4a38842` |
| 09-18 | 005 agenda | Importação macOS e CSV do Google; `ficha`, `ativar`, `confirmar-tags` | O macOS bloqueia a nota de contato para app não assinado (dívida 6) | `aa0f235` |
| 09-18 | 006 coleta RSS | Feeds, Google News, dedup, filtro de ruído, retomada | Corpo abaixo de 400 caracteres é ruído | `9098879`, `48f4ce0` |
| 09-19 | 007 agrupamento | Agrupamento em assuntos e calibração do limiar | Corte de fonte independente de 0,30 para 0,08 (cosseno 0,92), medido em 318 itens reais; revisão humana da calibração removida | `06ba8e0` |
| 09-19 | 008 qualificação | Qualificação, rótulo e cartão | `importar-temas` passou a gravar o vetor do tema (correção fora do escopo, autorizada) | `4954eff` |
| 09-19 | 009 regra do conector | Regra do conector e menu por contato | Caso 8 da tabela contradizia a regra; usuário confirmou o resultado corrigido | `f9a1e53` |
| 09-19 | 011 exportação Markdown | Menu em Markdown e leitura de marcações | — | `23c808b` |
| 09-19 | 012 ciclo diário | Ciclo com LaunchAgents | Achados sobre LaunchAgents de Ollama de outro projeto (`cervello`). Superado pelo 016 | `6cbef10` |
| 09-19 | 013 medição | Instrumentação de validade de JSON e `certificar` | Critério 2a medido como 12 de 12 nos casos do conector | `ce006a5`, `ce03577` |
| 09-20 | 010 console web | Contatos, Menu, Temas | Conexão SQLite por requisição (armadilha 30) | `2b93ec8` |

**Fase B — sob demanda e redes sociais, 2026-09-20 a 09-21** (briefs 014 a 030 não têm brief no disco nem registro no histórico; as linhas vêm só da mensagem do commit)

| Data | Brief | Entregou | Decisão relevante | Commit |
|---|---|---|---|---|
| 09-20 | 014 | Cadastro de redes sociais por perfil | — | `0022f68` |
| 09-20 | 015 | Histórico permanente por contato | — | `e173f1a` |
| 09-20 | 016 | Remove o ciclo automático | Nada roda sozinho: arquitetura sob demanda | `0c70dce` |
| 09-20 | 017 | Leitura de rede social por automação de navegador | Substituída pelo 044 (Playwright removido) | `c6e0969` |
| 09-20 | 018 | Contexto de consulta e orquestração sob demanda | — | `d8cd313` |
| 09-20 | 019 | Corrige 500 em `/temas` e `/eu`; formulário mínimo de novo contato | — | `3fd21ca` |
| 09-21 | 022 | Edição direta dos dados do contato | — | `4d61783` |
| 09-21 | 023 | Busca assistida de perfis em rede social, com confirmação | — | `834f742` |
| 09-21 | 024 | Configuração do perfil do usuário no console | — | `21349f6` |
| 09-21 | 025 | Apagar e unir contatos | Histórico permanente preservado | `e9c0a39` |
| — | 020, 021, 026–030 | Sem commit com o número (não conferido) | — | — |

**Fase C — Pro, pedido em texto livre, 2026-10-08 a 10-31**

| Data | Brief | Entregou | Decisão relevante | Commit |
|---|---|---|---|---|
| 10-08 | 031 | Perfil de hardware `pro48` e seleção por máquina em `config/local.yaml` | — | `24848f2` |
| 10-08 | 032 | Instância compartilhada do Ollama | Nunca parar a instância do `cervello` | `fcb696d` |
| 10-08 | 033 | Integração dos commits de hoje com `origin/main` | — | `5d46d73` (merge; associação pela mensagem, não conferido; o PLAN não lista o 033 em "Done") |
| 10-08 | 034, 035 | Contexto da consulta dirige o motor; reconsulta no dia; pesos no YAML | — | `05eaf18` |
| 10-11 | 036 | Extração do pedido em texto livre | Rótulo inventado cai no neutro | `322341c`, `88dc322` |
| 10-11 | 037 | Pessoa localizada nas listas do usuário | Cache de 30 dias; X só por link colado | `7fd4c59` e 6 correções |
| 10-12 | 044 | Extensão do Chrome e ponte local; Playwright removido | X e Instagram bloqueiam navegador automatizado; aba em foco | `906d759` e 5 correções |
| 10-13 | 038 | Redação dos ganchos e mensagens | "O agente trabalha para o usuário" (princípio de 10-13) | `ea26737`, `9ff9bde`, `657edaa` |
| 10-13 | 039 | Tela única | Pedido roda em segundo plano, uma tarefa por vez | `e9564bd` |
| 10-14 | 045 | Coleta resiliente | Cooldown por host no banco; fallback Bing News | `5e3af5b` |
| 10-14 | 046 | Usuário decide o tema | **Filtro de categoria sensível removido.** Prompts sem proibição de tema | `5e3af5b` |
| 10-15 | 047 | A mensagem nasce da pessoa e do objetivo | Mensagem-base sempre; notícia opcional | `8c8ce64` |
| 10-25 | 050 | Comentário do usuário e nota do contato | Migração 014 | `a283d4b`, `2c31eac` |
| 10-25 | 055 | Documentos canônicos | Só o AGENTS.md é rastreado; histórico fora do caminho de leitura | `acb2a67` |
| 10-25 | 056 | Orquestrador único pedido → ganchos | SQL cru movido para `queries/` | `caab38a` |
| 10-25 | 057 | Entregar num comando | Gate, commit e push pelo manifesto; trava de comandos | `d945020` |
| 10-25 | 058 | O Claude Code entrega sozinho | Hook de lint, skill `/executar` | `243fb5b` |
| 10-25 | 059 | Terminal e console: 4 diferenças unificadas | — | `19dc3f4` |
| 10-25 | 062 | Lacunas vão ao PLAN sozinhas | `agente_lacunas.py` | `b8cd5c7` |
| 10-30 | 063 | Ajustes do Claude Code | Estilo Concise; campo Esforço no brief | `b09df33` |
| 10-30 | 060 | O pedido começa pela pessoa | Lista de contatos na tela inicial | `cadf946` |
| 10-30 | 061 | Conversas do WhatsApp | Zip ou txt; fatos por mês e tom da relação | `4366f01` |
| 10-30 | 049 | Juízo de relação com o objetivo | Só notícia ligada ao objetivo vira gancho | `d2a1a54` |
| 10-30 | 048 | Molde por contexto | Mensagem que funcionou vira molde | `0bdd9be` |
| 10-31 | 040 | Perfil do usuário inferido | Temas inferidos dos pedidos, sem cadastro | `ef532fc` |
| — | 051–054 | Documentos de avaliação de skills e de evolução; auditoria de contaminação externa sem achados (21–25/10) | Sem código | — |

**Fase D — camada de IA e endurecimento, 2026-11-02 a 11-06**

| Data | Brief | Entregou | Decisão relevante | Commit |
|---|---|---|---|---|
| 11-02 | 064 | Cliente Ollama resiliente | Backoff de transporte separado da nova tentativa; seed fixo | `4b0aefb` |
| 11-02 | 065 | Molde só do que funcionou | Havendo "usei", nenhuma mensagem só "entregue" participa | `fafde0c` |
| 11-02 | 066 | Proveniência da IA | `VERSAO` obrigatória por prompt; migração 019 | `18f405f` |
| 11-02 | 067 | Geração degenerada tratada | Corrige o 064 | `bedee71` |
| 11-02 | 068 | Defesa contra injeção de prompt | `cercar_dado_externo` | `ea66368` |
| 11-02 | 069 | Terceiro cercado por inteiro | Fecha a 068-1 | `7d0e447` |
| 11-02 | 070 | `listas ver` liberada | `listas atualizar` segue bloqueada | `2ee8988` |
| 11-03 | 071 | Curadoria depois do "Sim" na divergência | — | `80b9bbe`, `6141be1` |
| 11-03 | 072 | AGENTS §11: limites da ponte do Cowork | — | `f6ed443` |
| 11-03 | 073 | AGENTS §12: uma árvore de trabalho só | — | `33a4550` |
| 11-03 | 074 | Base comum de LLM | Refatoração sem mudar comportamento | `9598a8e` |
| 11-03 | 075 | Clientes Anthropic, Gemini, OpenAI | Chave do Gemini em header, nunca na URL | `8a5d7eb` |
| 11-03 | 076 | Seleção do provedor por chave | `selecionar_cliente_llm` único | `7d59d7b` |
| 11-06 | 077 | Integração com o `porteiro` | Modo lote espera até 15 min; interativo nunca espera | `af2a09f` |

**Não iniciados:** 041, 042, 043.

#### Eventos relevantes (sem brief)

| Data | Evento |
|---|---|
| 09-12 | Escopo inicial: produto é coletor de assuntos; sem geração de mensagem; 100% local; coleta de rede só sob demanda. **Os dois primeiros itens foram superados**; o `PLANO.md` guarda a versão antiga (D-02) |
| 09-17 | Proposta do comitê v5; Etapa 1 no Air |
| 09-20 | `scripts/commitar.sh` (`97b13b5`) |
| 10-08 | Pasta `_quarentena_outro_usuario_2026-10-08` criada e ignorada (`0668a79`) |
| 10-12 | Importação de 2.201 contatos no banco (medida; origem não registrada, ver D-04) |
| 10-12/13 | Verificação real da extensão: LinkedIn 554 de 568, X 337 de ~356, Instagram 440 de 440 |
| 10-13 | Princípio "o agente trabalha para o usuário" |
| 10-21 a 25 | Auditoria de contaminação externa (incidente de outro projeto): sem achados |
| 11-02 | Dia de endurecimento: oito briefs (064–071) em um dia |

---

## 3. Soluções que outros projetos poderiam aproveitar

Evidência = arquivo de teste e relatório do brief. **Não reproduzi nenhum teste**; os "passed" são os colados nos relatórios.

| # | Problema que resolve | Como resolve | Arquivo | Commit | Estado | Evidência |
|---|---|---|---|---|---|---|
| 1 | Texto de terceiro (notícia, perfil, WhatsApp) tentando mandar no modelo | `cercar_dado_externo`: marcadores fixos, marcador forjado no texto neutralizado, instrução fixa uma vez por prompt | `agente_nw/nucleo/prompts/seguranca.py` | `ea66368`, `7d0e447` | Em produção no código (9 prompts); 3 chamadas ainda fora do cerco (PLAN 068-2) | `tests/test_seguranca_prompt.py`; doc_068 "15 passed", doc_069 "33 passed". Só `extrair_de_texto` tem teste com modelo real (PLAN 068-3) |
| 2 | Falha transitória do Ollama e geração em loop derrubando o lote | Backoff de transporte (2/4/8/16 s) separado da nova tentativa por conteúdo; `seed` fixo; teto de tokens; geração degenerada vira nova tentativa e `fila_revisao` | `agente_nw/nucleo/llm.py` | `4b0aefb`, `bedee71` | Em produção | `tests/test_llm_resiliente.py`, `test_llm_payload.py`, `test_llm_log_chamadas.py`; doc_064 "861 passed" |
| 3 | Trocar de provedor de IA sem espalhar `if` | Base `_ClienteLLMBase` com a orquestração; um cliente por provedor só implementa `_chamar`; `selecionar_cliente_llm` é o único ponto de decisão; embeddings ficam locais | `agente_nw/nucleo/llm.py`, `config/container.py` | `9598a8e`, `8a5d7eb`, `7d59d7b` | **Em teste, só com dublês** (`httpx.MockTransport`); nenhuma chamada real a API registrada; riscos de 400 em OpenAI e Gemini (PLAN 075-2, 075-3) | `tests/test_llm_api.py` (doc_075: 23 passed), `test_selecao_provedor.py` (doc_076: 22 passed) |
| 4 | Não saber qual prompt, perfil e modelo geraram um registro | `VERSAO` obrigatória em todo prompt; colunas `gerado_por_*`; modelo de embedding gravado e conferido na leitura (vetor de outro modelo conta como ausente) | `agente_nw/nucleo/prompts/*`, `scripts/migracoes/019_proveniencia.sql`, `nucleo/modelos/proveniencia.py` | `18f405f` | Em produção no código; migração 019 não aplicada no banco desta máquina | `tests/test_proveniencia.py`; doc_066 "877 passed" |
| 5 | Executor que commita fora do escopo ou sem gate | Entrega num comando: gate verde → commit só dos arquivos do manifesto → push; hook que bloqueia git de escrita e comando perigoso; lacunas do relatório vão ao PLAN sozinhas | `scripts/agente_entregar.sh`, `scripts/agente_lacunas.py`, `.claude/hooks/guarda_comando.py`, `lint_arquivo.py` | `d945020`, `243fb5b`, `b8cd5c7` | Em produção (manifestos `logs/entregue_*` como 040, 048, 049 e 056 a 060, e relatórios 064–077; a lista de `logs/` foi vista só até os primeiros 20 arquivos) | `tests/test_agente_entregar.py`, `test_agente_lacunas.py`, `test_guarda_comando.py` |
| 6 | Vários projetos disputando memória do mesmo Ollama | Consulta o `porteiro` uma vez por modelo; modo lote espera, modo interativo nunca; degrada se ausente | `agente_nw/nucleo/llm.py` | `af2a09f` | Em teste (código pronto; sem uso real registrado; caminhos fixos 077-1) | `tests/test_porteiro.py`; doc_077 "979 passed" |
| 7 | Ler redes sociais sem ser bloqueado | Extensão do Chrome do próprio usuário, comandada por ponte local com token por execução; 7 ações fixas, só leitura, uma aba | `extensao/`, `agente_nw/ponte/servidor.py`, `coleta/capturas/extensao_backend.py` | `906d759` e 5 correções | Em produção | Verificação real 12–13/10 (LinkedIn 554/568, X 337/~356, Instagram 440/440) e `lista_rede_social` = 1.336 (554+440+337+5) na medição; `tests/test_ponte_servidor.py`, `test_extensao_backend.py` |
| 8 | Buscador de notícias bloqueando (429/503) | Cooldown por host no banco que sobrevive a reinício; reuso de termo por 24 h; limite de buscas por pedido; fallback Bing News; teto de tempo | `agente_nw/coleta/rss/` (`leitor.py`, `fonte_alternativa.py`) | `5e3af5b`, `42d25fc` | Em produção | `tests/test_coleta_bloqueio.py`, `test_coleta_cooldown.py`, `test_coleta_fonte_alternativa.py`; `fonte_execucao` 285 linhas em 13 dias |
| 9 | Mesma notícia republicada parecendo assunto denso | Embedding + centróide, janela de 7 dias, fonte só independente se outro domínio e divergência ≥ 0,08; limiar calibrado por medição | `agente_nw/nucleo/agrupamento/`, `docs/adr/adr-0001-limiar-agrupamento.md` | `06ba8e0` | Em produção | `tests/test_agrupador.py`, `test_calibracao.py`; histórico: 318 itens → 283 assuntos. **Medição atual: 375 de 413 assuntos têm 1 item só** |
| 10 | Conversa de WhatsApp como fonte de fatos e de tom | Zip/txt, blocos de 6.000 caracteres por mês, fatos datados pelo mês, últimas 10 trocas para o tom | `agente_nw/coleta/whatsapp/`, `nucleo/database/queries/conversa.py` | `4366f01` | Em teste (testes reais 061-1 a 061-3 pendentes) | `tests/test_whatsapp_leitor.py`, `test_whatsapp_importador.py`, `test_whatsapp_no_prompt.py` |
| 11 | IA repetindo mensagem que o usuário nunca aprovou | Molde por contexto só do que foi marcado "usei"; rastro de qual molde originou qual mensagem | `agente_nw/nucleo/redacao.py`, `queries/gancho_uso.py` | `0bdd9be`, `fafde0c` | Em teste (testes reais 048, 065 pendentes) | `tests/test_moldes_so_confirmado.py`, `test_moldes_por_contexto.py`, `test_molde_*` |
| 12 | Banco evoluindo sem trilha | Migrações SQL numeradas, `schema_version`, backup, `copiar-banco` para desenvolver em cópia | `scripts/migracoes/`, `nucleo/database/` | `21592b4` | Em produção | `tests/test_migracoes.py`, `test_backup.py`; `schema_version` com 14 linhas |
| 13 | Notícia "parecida" com o contato mas inútil ao objetivo | Piso por embedding (0,45) e juízo sim/não do modelo sobre relação com o objetivo | `agente_nw/nucleo/relevancia/cruzamento.py`, `prompts/avaliar_relacao_objetivo.py` | `d2a1a54`, `5e3af5b` | Em teste (testes reais 049-1 a 049-4 pendentes) | `tests/test_gate_objetivo.py`, `test_gate_lote_ordem.py`, `test_gate_zera_menu.py`; sem medição real após o 049 |
| 14 | Prompt grande demais para o contexto | `cortar_por_tamanho`: estima tokens (palavras × 1,4) e cai em ordem: histórico, fatos, moldes, WhatsApp; notas do usuário protegidas | `agente_nw/nucleo/prompts/redigir_ganchos.py` | `ea26737` | Em produção, mas só na redação (ver §4) | `tests/test_redacao_prompt.py` e `test_redacao_redigir.py` existem; não conferi qual cobre o corte; limite 6.000 tokens |
| 15 | **Abandonadas:** ciclo diário com LaunchAgents (`6cbef10`, removido em `0c70dce`); Playwright (`c6e0969`, removido em `906d759`); filtro de categoria sensível (`91b7286`, removido no 046); revisão humana da calibração (removida no 007) | — | — | — | Abandonadas | Registradas no histórico do PLAN |

---

## 4. Leitura de texto por inteiro

**O projeto processa documentos?** Sim: notícias inteiras (extraídas com `trafilatura.extract` em `coleta/rss/leitor.py:338`, sem teto na gravação), publicações de redes sociais, conversas do WhatsApp e notas de agenda. Mediana de 3.035 caracteres por notícia, máximo 34.195 (712 itens, medição de 2026-11-07).

**Regra relevante.** O PLAN registra a armadilha 1: o `num_ctx` padrão do Ollama trunca a entrada em silêncio. O projeto passa `num_ctx` explícito (`llm_routing.yaml`: 2.048 a 8.192 no Air, 2.048 a 16.384 no Pro), mas **nenhum ponto confere o tamanho do prompt contra esse limite**: `nucleo/llm.py:352` só repassa `num_ctx` ao Ollama (`9598a8e`). O único estimador é o da redação (§4, item 11).

Os commits abaixo são os da última alteração da linha citada (`git blame`).

### 4.1 Pontos que leem só parte do texto

| # | Onde (arquivo : função ou linha) | Corte | O que afeta | Commit |
|---|---|---|---|---|
| 1 | `nucleo/relevancia/qualificador.py`: `_itens_recentes_resumidos` (l. 41–45) | Só **título e domínio** dos 5 itens mais recentes do assunto. O corpo nunca entra | **Classificação do assunto** (substancial, conversável, temas) e **título gerado** (`rotular`). É a classificação inteira de notícia feita por manchete | `4954eff` |
| 2 | `nucleo/relevancia/cartoes.py`: `gerar_cartao` (l. 16, 51) | Até 5 itens mais recentes, **300 caracteres** de cada. Na medição, lê 7,1% dos caracteres dos itens que estão em assuntos; 31 itens ficam fora dos 5 mais recentes | **O cartão (`resumo_cartao`) é o único resumo da notícia** que o gate de relação com o objetivo (`cruzamento.py:155`) e a redação (`redacao.py`, `resumo=assunto.resumo_cartao`) enxergam | `4954eff` |
| 3 | `nucleo/agrupamento/agrupador.py`: `agrupar` (l. 88) | Embedding de título + **2.000 primeiros caracteres**. 530 de 712 notícias (74%) são cortadas; lê 45,3% dos caracteres | Em qual assunto cada notícia cai (e portanto o centróide do assunto) | `06ba8e0` |
| 4 | `nucleo/agrupamento/calibracao.py`: `_trecho` (l. 25, 108) | 2.000 primeiros caracteres de cada item do par | Pré-rotulagem dos pares que calibram o limiar de agrupamento | `06ba8e0` |
| 5 | `nucleo/redacao.py`: `_assunto_para_redacao` (l. 46, 69) | **3 manchetes** (só título) por assunto; o texto inteiro vai só para `LinkNoticia.texto`, guardado, não ao prompt | O que o modelo de redação sabe da notícia: resumo de 300 caracteres e 3 títulos | `ea26737` |
| 6 | `coleta/rss/ruido.py`: `e_ruido` (l. 52, 57) | Corpo < 400 caracteres é ruído; detecção de "patrocinado" só nas **3 primeiras linhas** | Notícia descartada antes de entrar | `9098879` |
| 7 | `coleta/capturas/leitor.py`: `_BLOCOS_EXAMINADOS_POR_PUBLICACAO` (l. 29, 136) e `limiares.yaml: coleta.maximo_blocos_por_rede` (10) | Examina `10 × 4 = 40` blocos da página e grava até 10 publicações por rede; rolagem padrão de 5 | Fatos de rede social: o que o contato publicou além das 10 mais recentes não entra | `9a8bb96` (código), `657edaa` (limiar) |
| 8 | `limiares.yaml: coleta.maximo_imagens_por_rede` (8) e `largura_minima_imagem` (250) | Descreve até 8 imagens por rede; ignora menores que 250 px | Fatos `imagem:<rede>` | `657edaa` |
| 9 | `coleta/capturas/extensao_backend.py`: `_ler_estado` (l. 93) e `extensao.maximo_caracteres_pagina` (200.000) | Texto da página cortado em 200.000 caracteres | Praticamente inócuo; registrado por ser corte | `906d759` |
| 10 | `nucleo/redacao.py` (l. 41, 45, 146, 162) e `nucleo/historico.py` (l. 56, 58) | Fato cortado em **600** caracteres no prompt (e no cálculo de semelhança), nota em **400**, mensagem do histórico em **100**, comentário em **300**; 10 fatos por prompt | Redação: um fato longo de rede social (guardado inteiro) chega com o começo só | `657edaa`, `2c31eac`, `5e3af5b` |
| 11 | `nucleo/prompts/redigir_ganchos.py`: `cortar_por_tamanho` (l. 18, 93, 280) | Se o prompt estimado passa de **6.000 tokens**: histórico → 1 consulta, fatos → 5, depois sem moldes, depois sem WhatsApp. Estimador: palavras × 1,4 | Mensagens: fatos e tom saem sem aviso ao usuário (não conferido se há aviso) | `ea26737` |
| 12 | `nucleo/relevancia/cruzamento.py` (l. 272, 481) e `limiares.yaml: conector.itens_no_menu` (5), `candidatos_por_contato` (10) | Corte por quantidade de assuntos | Não é corte de texto de documento; registrado por ser corte de seleção | `f9a1e53` (l. 272), `05eaf18` (l. 481), `09ed4bf` (limiares) |
| 13 | `whatsapp.meses_extraidos` (24) e `trocas_no_prompt` (10) | Só os 24 meses mais recentes viram fatos; 10 últimas mensagens vão ao tom | Fatos e tom da conversa mais antiga | `4366f01` |

### 4.2 Pontos que mandam o texto inteiro, sem conferir o tamanho

| # | Onde | Situação | Risco |
|---|---|---|---|
| 14 | `perfil/extrator.py:80` (`processar_fila`) chama `construir_prompt(item.texto)` com a nota inteira | Notas de agenda medidas: máximo 3.179 caracteres, cabem. Blocos de WhatsApp de até 6.000 caracteres (`whatsapp.maximo_caracteres_bloco`) cobrem o mês em partes | No Air, `extrair_de_texto` usa `num_ctx` 4.096: bloco de 6.000 caracteres com o prompt (exemplo e instruções) fica perto do limite; **não conferido** |
| 15 | `fila_revisao`: 229 erros de `extrair_de_texto` | 226 de "validation error ... RespostaExtracaoTexto campos" | Causa **não investigada**. Não dá para afirmar que seja truncamento; não conferido |

**Conclusão.** O erro a eliminar existe em três lugares centrais: a classificação de assunto usa só títulos (item 1), o resumo que alimenta o gate e a redação usa 300 caracteres (item 2) e o agrupamento usa os 2.000 primeiros (item 3). Para cobrir o texto inteiro seria preciso processar em partes que cobrem tudo e consolidar (o desenho que o item 14 já usa para WhatsApp).

---

## 5. Qualidade dos dados

O projeto tem banco. Medido na cópia de 2026-11-07 (arquivo de 2026-10-25).

### 5.1 O que já mede e trata (verificado no código e na medição)

| O que | Como | Resultado medido |
|---|---|---|
| Notícia duplicada | `item.url_canonica UNIQUE` e `hash_titulo`; limpeza roda antes do hash, sem alterar o texto guardado (AGENTS §4) | 712 itens, 712 hashes distintos, 0 repetidos. 2 grupos com texto idêntico entre itens distintos |
| Mesmo fato em vários veículos | Agrupamento por cosseno e `n_fontes_independentes` | 389 de 413 assuntos com 1 fonte; 16 com 2; 6 com 3; 1 com 4; 1 com 7 |
| Ruído de coleta | `e_ruido` (corpo curto, lista, patrocinado, notícia velha) | 0 textos com HTML cru; 0 textos iguais ao título; 0 caracteres de substituição |
| Integridade do banco | `pragma foreign_key=ON`; migrações | `integrity_check` ok; 0 violações de chave estrangeira |
| Contato duplicado | `telefone` como chave; unir contatos (manual, brief 025) | 0 telefones repetidos; **21 nomes repetidos (46 linhas)**, sem rotina automática |
| Falha do modelo | JSON validado contra o esquema, nova tentativa, `fila_revisao` | 232 registros na fila |
| Validade de JSON | `agente_nw certificar` (brief 013) | Não rodei |
| Dado sensível | O filtro foi removido no 046 | 4 linhas antigas em `descarte_sensivel` (13–14/10, antes da remoção); nada novo depois |
| Fato de rede social | Texto integral da publicação, `data_do_fato` | 116 de 149 fatos sem data; 19 grupos de fatos duplicados |

### 5.2 O que não mede (ou mede e ninguém olha)

1. **Cobertura de vetores.** 511 de 712 notícias (71,8%) têm vetor; as 201 sem vetor são exatamente as 201 sem assunto (retomada pelo limite de 100 por execução do `agrupar`). Nenhum comando informa essa cobertura.
2. **Cobertura de qualificação.** 351 de 413 assuntos qualificados (62 sem título nem qualificação) e **0 de 413 com cartão**. Como o gate e a redação leem o cartão, no estado deste banco eles veriam "(sem resumo)" (não conferido se o fluxo gera o cartão na hora do pedido).
3. **Temas sem vetor.** 0 de 159 temas têm vetor, e as consultas de aderência fazem `JOIN vetor_tema`. Não conferido se alguma rotina completa isso depois.
4. **Fila de revisão sem saída.** Nenhum código marca `fila_revisao.resolvido = 1` (só insere com `False`); as 232 linhas ficam para sempre. 149 linhas de `fila_extracao` com erro também não têm nova tentativa documentada.
5. **Consistência interna.** Soma de `assunto.n_itens` = 496; itens com `assunto_id` = 511 (diferença de 15). Um assunto com `n_itens` 29 enquanto só 2 assuntos têm mais de 5 itens ligados.
6. **Contatos.** 2.201 contatos sem nenhum ativo; 0 vínculos de tema confirmados; faixas de preenchimento: telefone 1.023, e-mail 1.719, empresa 798, cargo 359, cidade 32. Nenhuma medição de qualidade de cadastro roda.
7. **Texto repetido em fatos** (19 grupos) e **nomes repetidos em contatos** (21 grupos) sem tratamento automático.
8. **Retenção.** `coleta.retencao_texto_dias` (90) existe em `limiares.yaml`, mas só o agrupador a usa (como janela de reabertura); **nenhuma purga existe** (dívida 4 do PLAN). Hoje nenhum texto passou de 90 dias porque a coleta é de outubro.
9. **Banco de produção (Air).** Não medido.

---

## 6. Divergências encontradas

| # | O documento diz | O código ou a medição mostram | Gravidade |
|---|---|---|---|
| D-01 | `PLAN.md`: "Última migração: 019" | O banco desta máquina está na 014 (aplicada em 2026-10-25). O código tem 019. Nenhuma chamada ao modelo foi logada depois de 2026-10-25 | Média: os briefs 064–077 nunca rodaram contra este banco |
| D-02 | Documento histórico, **não divergência**: `PLANO.md` é a proposta de 2026-09-17 ("muda a cada versão aprovada da proposta") e diz "100% local, sem API, não escreve mensagem". O PLAN já o marca como desatualizado (055-2). O que vale hoje, `AGENTS §3`, `ARQUITETURA §8` e o código (`nucleo/llm.py`, `redigir_ganchos`), concorda entre si | Só falta atualizar ou arquivar o `PLANO.md` | Baixa (já registrada) |
| D-03 | `AGENTS.md`, `PLAN`, `PLANO`, `ARQUITETURA`: nenhuma menção à regra de que **nenhum conceito jurídico entra** (busca por "jurídic" e "conceito" nos 4 arquivos: 0 ocorrências) | A regra só consta neste aviso. No código há: exemplo de prompt "Beatriz é advogada tributarista" (`prompts/extrair_de_texto.py:22,36`), "sou advogado tributarista" (`prompts/extrair_pedido.py:70`, `modelos/pedido.py:55`), "advogado/advogada" como exemplo de gênero (`prompts/redigir_ganchos.py:224`), exemplo de "tribunal superior ... prescrição intercorrente tributária" em `prompts/exemplos_conversavel.yaml:16` (rastreado), comentário "eleição da OAB" (`relevancia/cruzamento.py:470`); `temas.exemplo.yaml` (rastreado) traz "direito tributário" e "contencioso de ICMS"; `fontes.yaml:84` (fora do git) lista o Conjur como fonte de notícias | **Decisão de Sidarta:** são exemplos de profissão e de tema, não lógica jurídica; só ele diz se a regra os alcança |
| D-04 | `PLAN` dívida 7: "importação real do CSV do Google Contatos ainda não aconteceu"; dívida 6: 547 contatos, nota bloqueada em 100% | O banco tem 2.201 contatos criados em 2026-10-12, 558 com nota e 571 itens de `notas_agenda` na fila; 3.285 vínculos `importada` no mesmo dia. Nenhum documento registra essa importação nem sua origem (o histórico dos briefs 014–030 não existe) | Média |
| D-05 | Brief 046: `descarte_sensivel` "fica no banco, vazia" depois da remoção do filtro | As 4 linhas (categoria `saude`) são de 2026-10-13 e 2026-10-14 15h51 UTC, anteriores à entrega do 046: resíduo esperado, **não divergência**. `ARQUITETURA §3` ainda descreve a tabela como ativa (PLAN 055-1) | Baixa (já registrada) |
| D-06 | `PLAN`, backlog 066-1 e 068-2 | Descrevem a mesma coisa (3 chamadas sem `VERSAO` e sem cerco, fora de `nucleo/prompts/`): duplicado | Baixa |
| D-07 | `PLAN` dívida 066-3: "`_GeracaoDegenerada` escapa de `gerar_json`" | Corrigido pelo brief 067 (`bedee71`); o próprio Resumo do PLAN diz "corrigida pelo 067". A dívida segue listada | Baixa |
| D-08 | `PLAN` 074-1: dois briefs antigos de fallback "continuam no disco" e deixam `/executar` ambíguo | `ls docs/briefs | grep brief_07[45]` devolve só os briefs 074 e 075 vigentes; os antigos não existem | Baixa: item obsoleto |
| D-09 | `PLAN` Done: 071, 072 e 073 em 2026-11-02 | Os commits `80b9bbe`, `f6ed443`, `33a4550` são de 2026-11-03 (data do git; pode ser fuso) | Baixa |
| D-10 | `PLAN` Resumo: 979 testes | Contagem estática de `def test_`: 850 (parametrização pode explicar); não executei | Não conferido |
| D-11 | `ARQUITETURA §7` (l. 190): "fonte independente se o texto divergir em mais de 30%" | `limiares.yaml`: `divergencia_minima_fonte_independente: 0.08` (mudou em 2026-09-18) | Média (PLAN 055-1 já registra) |
| D-12 | `PLAN` Done: molde por contexto (048/065) entregue, concluído | Banco desta máquina: `gancho_uso` tem 17 linhas, todas `entregue`, nenhuma `usado` (e a migração 018 do molde não está aplicada): o mecanismo nunca foi exercido com dado real aqui. É coerente com as pendências 048-x e 065-x | Informativa |
| D-13 | `AGENTS §4`: "sem hardcode de caminhos" | `_PORTEIRO_PYTHON` e `_PORTEIRO_BIN` fixos em `nucleo/llm.py` (PLAN 077-1) | Já registrada |
| D-14 | Princípio de modularidade (o aviso do repositório de referência) | `console/app.py` tem 1.043 linhas e `cli.py` 1.494 (50 rotas e ~30 comandos em um arquivo cada); `integracoes/` é pacote vazio. Não comparei com `ARQUITETURA §2` | Observação, não divergência de documento |
| D-15 | `PLAN` dívida 2: temas fictícios do exemplo gravados no banco real | `tema` tem 159 linhas, todas ligadas a perfis; não identifiquei os dois fictícios (não conferido) | Não conferido |

---

## 7. Lacunas

| # | Lacuna | Destino | Impacto |
|---|---|---|---|
| 1 | Nenhum teste foi executado; números de teste vêm dos relatórios dos briefs | nenhum | Os "passed" citados não foram reproduzidos |
| 2 | O banco de produção do Air não foi medido | pendência | As contagens valem para o Pro de desenvolvimento |
| 3 | Briefs 020, 021 e 026–030 sem commit identificável | pendência | CONTEXT.md fica com buracos nessa faixa |
| 4 | Onde ficam CONTEXT.md e ESTADO_ATUAL.md (raiz rastreada ou `docs/` ignorada) | decisão | Define se entram no git |
| 5 | A regra "nenhum conceito jurídico" não está escrita em documento do projeto e há exemplos no código (D-03) | decisão | Pode pedir um brief de limpeza |
| 6 | Banco de desenvolvimento na migração 14, código na 019 | pendência | `agente_nw migrar` em cópia (`copiar-banco`) antes de qualquer teste real |
| 7 | Causa dos 229 erros de `extrair_de_texto` não investigada | backlog | Pode ser prompt, esquema ou truncamento |
| 8 | `fila_revisao` não tem caminho de resolução | backlog | 232 linhas acumuladas |
