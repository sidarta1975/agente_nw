# agente_nw — Plano de execução do MVP (Etapa 1 da Proposta v4)

**Data:** 17 de setembro de 2026
**Base:** Proposta para aprovação do comitê, versão 4, seção 5 (Etapa 1) e seção 2.2 camada 1
**Máquina:** MacBook Air 2024, chip M3, 16 GB de memória unificada, macOS Sonoma 14.6
**Modelos:** `qwen3:4b` (geração, modo de raciocínio desligado) e `bge-m3` (embeddings), ambos via Ollama com Metal
**Prazo:** três semanas, 14 briefs, um brief por sessão de execução do Claude Code
**Repositório:** `/Users/sidarta48/github/agente_nw` — hoje só documentação; o primeiro brief atualiza os documentos-base, o segundo cria o código

---

## 1. O que o MVP entrega ao fim das três semanas

Um ciclo diário que roda sozinho às 05h00 (ou no primeiro login): lê 20 a 40 feeds, agrupa em assuntos, qualifica, cruza com os contatos ativos pela regra do conector e entrega, no console local e num arquivo Markdown, o menu de assuntos por contato — conectores no alto, viáveis com esforço abaixo, nada do que o usuário não teria como sustentar. A base de contatos nasce da agenda do Mac e do Google Contatos. O usuário marca "usei" ou "não serve", e isso fica registrado para a calibragem da Etapa 2.

Fora do MVP, por decisão da proposta: extensão do Chrome, exportação de conversa do WhatsApp, modelo de visão, resumo completo, balanço semanal, integrações Google além da importação de contatos, assistentes pagos.

---

## 2. Preparação da máquina (antes do primeiro brief de código, 40 minutos)

```bash
# Homebrew, Python 3.12, SQLite recente
brew install python@3.12 sqlite
# Ollama (instalador para macOS em ollama.com/download) e os dois modelos
ollama pull qwen3:4b
ollama pull bge-m3
# Variáveis do Ollama para os dois modelos ficarem carregados juntos
launchctl setenv OLLAMA_MAX_LOADED_MODELS 2
launchctl setenv OLLAMA_KEEP_ALIVE 30m
# Ambiente do projeto
cd ~/github/agente_nw && python3.12 -m venv .venv && source .venv/bin/activate
pip install feedparser trafilatura httpx pydantic pyyaml numpy sqlite-vec flask python-dateutil pyobjc-framework-Contacts pytest mypy ruff
```

A permissão de acesso à agenda é pedida pelo macOS na primeira execução do importador; concede-se uma vez.

---

## 3. Os briefs

Nome dos arquivos: `brief_E1_NNN_<assunto>_<data>.md`, em `docs/briefs/`, fora do git, com cópia na aba Saídas. Cada brief segue o template de nove seções do projeto e termina com o relatório final obrigatório. A ordem abaixo é a de execução; a dependência está indicada.

### Semana 1 — Fundação

**000 — Atualizar os documentos-base**
`brief_E1_000_documentos_base`
Reescreve `PLANO.md`, `ARQUITETURA.md`, `PLAN.md` e `AGENTS.md` do repositório para refletir a Proposta v4: pacote `agente_nw`, modelo de dados com `assunto_contato`, `conta`, `captura`, `midia_processada`, `conversa_tema`, regra do conector, perfis de hardware, saída por contato em vez de cartões globais. Sem código. É o que o executor lê antes de qualquer brief seguinte.
Aceite: os quatro documentos não contradizem a v4 em nenhum ponto; `PLAN.md` lista os 13 briefs restantes como próximos passos. Depende de: nada.

**001 — Esqueleto do repositório e configuração**
`brief_E1_001_esqueleto`
Cria a estrutura de pastas da arquitetura, `pyproject.toml`, `.gitignore` com as regras de dado pessoal (`dados/`, `saidas/`, `capturas/`, `*.db`, `temas.yaml`, `fontes.yaml`, `config/local.yaml`, `*.csv`), `config/container.py`, `config/llm_routing.yaml` com o perfil `air16`, `config/limiares.yaml` com os valores iniciais (0,82 agrupar; 0,55 adjacência; 0,8 conversável; 0,6/0,6 qualificação), `temas.exemplo.yaml` e `fontes.exemplo.yaml` versionados, script de verificação (`ruff`, `mypy --strict`, `pytest`), script de instalação para macOS.
Aceite: verificação verde num repositório vazio de lógica; `ollama list` mostra os dois modelos; o container resolve um cliente de LLM e uma conexão de banco sem nenhum módulo instanciar nada direto. Depende de: 000.

**002 — Esquema, migrações e backup**
`brief_E1_002_esquema_migracoes_backup`
`scripts/migracoes/001_inicial.sql` com todas as tabelas da seção 4.1 da v4, incluindo `schema_version`, as restrições UNIQUE (`tema.nome`, `perfil_tema(perfil_id, tema_id)`), `assunto_contato.id` como chave primária, e a tabela virtual do `sqlite-vec`. Executor de migrações na inicialização. Modelos Pydantic v2 `frozen=True`, um módulo por entidade em `nucleo/modelos/`. Camada de consultas isolada em `nucleo/database/queries/`. Backup diário pela API de backup do SQLite em `dados/backups/`, retenção de 7 dias, e comando de restauração.
Aceite: banco criado do zero por migração; `schema_version` = 1; reimportar o mesmo tema não duplica; backup gerado e restaurado num banco temporário com contagem de linhas igual. Depende de: 001.

**003 — Cliente de LLM e embeddings**
`brief_E1_003_cliente_llm_embeddings`
Cliente único do Ollama em `nucleo/llm.py`: modelo resolvido pelo roteamento, `think: false` em toda chamada, `format` com esquema JSON, `num_ctx` obrigatório e explícito, temperatura por tarefa, um item por chamada, uma nova tentativa com temperatura 0,1 em JSON inválido e fila de revisão na segunda falha. Embeddings pelo `/api/embed` com `bge-m3`, gravação em `sqlite-vec`, função de cosseno e de centróide em `nucleo/vetores.py`.
Aceite: teste contra o Ollama real com JSON válido em 20 de 20 chamadas de um prompt de exemplo; embedding de 100 textos em menos de 30 segundos; JSON propositalmente inválido cai na fila de revisão com o erro registrado. Depende de: 002.

**004 — Filtro de categorias sensíveis e extrator de texto**
`brief_E1_004_filtro_sensivel_extrator_texto`
`nucleo/sensivel.py`: listas de termos por categoria (saúde, religião, política, sindicato, vida sexual, origem racial, menores), função que descarta tag ou fato e grava em `descarte_sensivel` sem o trecho. Contrato `extrair_de_texto` (seção 4.3 da v4) com prompt, esquema e um exemplo resolvido; processador da `fila_extracao` que roda o modelo, aplica o filtro e grava tags com origem `sugerida` e `confirmado = false`, campos guiados da ficha e fatos datados.
Aceite: conjunto de 30 frases (15 passam, 15 descartadas) com 100% de acerto; texto de cadastro de exemplo produz ao menos 4 tags e 2 campos guiados corretos; nenhum item da fila chega ao banco sem passar pelo filtro. Depende de: 003.

**005 — Importação da agenda**
`brief_E1_005_importacao_agenda`
Dois leitores idempotentes: agenda do macOS pelo framework de Contatos (pede permissão uma vez) e CSV do Google Contatos (script da seção 7.2 da v4). Normalização de telefone para E.164 como chave de identidade; e-mail como segunda chave. Marcadores viram tags `importada`; notas vão para a `fila_extracao`; nada nasce ativo. Comando `agente_nw importar-agenda`.
Aceite: a agenda real importa sem duplicar ninguém; rodar duas vezes deixa o mesmo número de perfis; contato com notas gera tags sugeridas depois de processada a fila. Depende de: 004.

### Semana 2 — Motor

**006 — Coleta RSS e Google News**
`brief_E1_006_coleta_rss`
Leitor de `fontes.yaml`; `feedparser` e `trafilatura`; URL canônica (sem `utm_*`, `fbclid`, âncora, um redirecionamento seguido); hash de título normalizado; regras de ruído estrutural (corpo abaixo de 400 caracteres, título de lista, patrocinado, mais de 7 dias na primeira aparição); gerador de consultas do Google News a partir dos temas (`quote` obrigatório, 2 segundos entre chamadas); regra de fonte independente (domínio diferente e texto divergindo mais de 30%); retenção de `item.texto` por 90 dias; progresso gravado por etapa, retomável; parada por arquivo sentinela.
Aceite: 20 feeds reais coletados em menos de 8 minutos; duplicata por URL e por título rejeitada; feed que volta vazio dois dias seguidos gera alerta no log; interromper no meio e reexecutar continua de onde parou. Depende de: 003.

**007 — Agrupamento em assuntos e calibração do limiar**
`brief_E1_007_agrupamento_calibracao`
Agrupamento por centróide em janela de 7 dias, limiar lido de `limiares.yaml`, encerramento após 7 dias sem item, reabertura marcada como "volta ao noticiário", divisão de assunto com mais de 12 itens e dispersão alta. Ferramenta de calibração: sorteia 50 pares de itens, o modelo maior disponível pré-rotula "mesmo assunto / assuntos diferentes", o usuário revisa só as discordâncias, a ferramenta calcula o limiar de melhor separação, grava em `limiares.yaml` e escreve o ADR.
Aceite: limiar calibrado e ADR escrito; com o limiar calibrado, cinco assuntos reais formados por mais de uma fonte independente; nenhum assunto com mais de 12 itens sem divisão. Depende de: 006.

**008 — Qualificação, rótulo, cartão e exemplos de conversabilidade**
`brief_E1_008_qualificacao_cartao`
Contrato `qualificar` com prompt, esquema e exemplo; seleção de candidatos pela união dos temas de todos os perfis ativos (teto de 40 por dia); corte 0,6/0,6; contrato `rotular`; contrato `cartao` para os assuntos que entrarem em algum menu. `prompts/exemplos_conversavel.yaml`: a IA escreve 10 exemplos positivos e 10 negativos de "conversável" no brief; o usuário aprova ou troca antes de o prompt ser fixado.
Aceite: 40 qualificações com JSON válido em 95% ou mais; um assunto que só toca temas de um contato (e nenhum do usuário) é qualificado; cartão sem número sem fonte entre parênteses. Depende de: 007.

**009 — Regra do conector e menu por contato**
`brief_E1_009_regra_conector_menu`
Centróide de perfil (média ponderada das descrições dos temas; nível do usuário com pesos 1,0/0,7/0,4); pré-seleção de 10 candidatos por contato; pontuação determinística 50/30/20; tipo `conector`, `viavel_com_esforco` ou `fora_do_dominio` com o piso 0,55 ou 0,8; gravação em `assunto_contato` (fora do domínio nasce descartado); ordenação por tipo e score; os 5 primeiros; contrato `cruzar` parte 2, em que o modelo só escreve o `por_que` e aponta o ponto de apoio nos viáveis; `sem_assunto` com motivo.
Aceite: conjunto de 12 casos montado à mão (4 conectores, 4 viáveis, 4 fora do domínio) com ordenação correta, zero fora do domínio exibido, os 4 descartes gravados com motivo, e `por_que` de viável citando o ponto de apoio; contato sem tag recebe `sem_assunto` sem travar o ciclo. Depende de: 008, 005.

### Semana 3 — Console, entrega e operação

**010 — Console web**
`brief_E1_010_console_web`
Flask em `127.0.0.1:8765`, sem framework de frontend, sem build. Três telas: Contatos (lista, ficha com tags por peso e origem, confirmação em lote, ativo, "gerar menu agora", indicador de lacunas por impacto, "Adicionar texto"); Menu (duas faixas, `por_que`, cartão expandível aberto por padrão nos viáveis, botões "usei" e "não serve" com os cinco motivos, contador de fora do domínio com lista sob clique); Temas (edição em linguagem natural, sinônimos, nível para os temas do usuário, sugestões pendentes). Botão "processar agora" para a fila.
Aceite: o ciclo inteiro de marcar tags, ativar contato, ler menu e marcar "usei"/"não serve" acontece no navegador sem editar arquivo à mão; o servidor recusa conexão de outro endereço que não `127.0.0.1`. Depende de: 009.

**011 — Exportação em Markdown e leitura de marcações**
`brief_E1_011_exportacao_markdown`
Gerador de `menu_AAAA-MM-DD.md` na pasta de saída configurável, um bloco por contato com as duas faixas e o `id` de `assunto_contato` em comentário HTML; leitor de marcações (`[x] usei`, `[x] não serve` com motivo) que grava no banco na rodada seguinte.
Aceite: arquivo gerado abre limpo no Obsidian e no app do Drive; marcação feita no arquivo chega ao banco com o motivo certo; arquivo editado com erro de formato gera aviso, não perda. Depende de: 009.

**012 — Ciclo diário e agendamento**
`brief_E1_012_ciclo_diario_launchd`
Orquestrador `agente_nw ciclo`: coleta → embeddings → agrupamento → qualificação → pré-seleção e pontuação → cruzamento → cartões → exportação → backup, cada etapa gravando progresso e retomável. Plist do `launchd` com `StartCalendarInterval` às 05h00 e recuperação de execução perdida; segundo gatilho no login com 5 minutos de atraso, saindo sem fazer nada se já rodou hoje. Log por execução com o tempo de cada etapa. Arquivo sentinela para parar.
Aceite: ciclo completo com 10 contatos ativos em menos de 20 minutos; Mac dormindo às 05h00 e acordado às 08h00 roda o ciclo até 08h05 e não roda de novo no dia; interrupção no meio e reexecução completam sem duplicar assunto ou menu. Depende de: 010, 011.

**013 — Medição de aceite e certificação**
`brief_E1_013_medicao_aceite`
Roda os critérios da seção 5.8 da v4 por cinco dias seguidos e produz o relatório de certificação: dias de ciclo sem intervenção, contatos com menu e quantidade de assuntos, percentual de JSON válido, tempo de ciclo, invenção de `assunto_id` (deve ser zero), resultado dos 12 casos do conector e das 30 frases do filtro, ADR do limiar, backup restaurado, aproveitamento registrado como linha de base. Atualiza `PLAN.md` com o estado real e as dívidas encontradas.
Aceite: relatório com todos os critérios cumpridos, ou lista explícita do que falhou e por quê; `PLAN.md` atualizado; fase certificada para a Etapa 2 começar. Depende de: 012.

---

## 4. Calendário

| Semana | Briefs | O que existe ao fim |
|---|---|---|
| 1 | 000 a 005 | documentos-base atualizados; banco com migrações e backup; cliente de LLM e embeddings testados contra o Ollama real; filtro sensível; agenda importada com tags sugeridas |
| 2 | 006 a 009 | coleta diária funcionando; assuntos formados com limiar calibrado; qualificação e cartões; menu por contato pela regra do conector, testado nos 12 casos |
| 3 | 010 a 013 | console, exportação, ciclo agendado no `launchd`, cinco dias de medição e certificação |

Um brief por sessão do Claude Code. Os briefs 006 e 007 podem correr em paralelo com 004 e 005 se houver duas sessões; a dependência real está indicada em cada um.

---

## 5. O que o usuário faz, e quando

| Momento | Ação | Tempo |
|---|---|---|
| Antes do brief 001 | preparação da máquina (seção 2) | 40 min |
| Brief 005 | conceder permissão de agenda; exportar o CSV do Google Contatos | 5 min |
| Brief 007 | revisar as discordâncias da pré-rotulagem dos 50 pares | 10 min |
| Brief 008 | aprovar ou trocar os 20 exemplos de conversabilidade | 10 min |
| Brief 009 | escrever os próprios temas com nível; marcar 10 contatos como ativos; confirmar as tags sugeridas em lote | 30 min, uma vez |
| Brief 013 | marcar "usei" / "não serve" diariamente por cinco dias | 5 min por dia |

Tudo o mais é do executor. Nenhum brief devolve ao usuário lista para classificar: onde há classificação, a IA propõe e o usuário confirma.

---

## 6. Riscos específicos desta execução

| Risco | Onde é tratado |
|---|---|
| Modo de raciocínio do Qwen3 ligado por engano quebra o JSON | brief 003: `think: false` é parâmetro fixo do cliente, não do prompt; teste falha se ausente |
| Limiar de agrupamento errado junta tudo ou fatia tudo | brief 007: calibração com amostra rotulada antes de qualquer assunto ir ao menu |
| Assunto de contato nunca chega ao menu | brief 008: candidatos pela união dos temas de todos os perfis ativos, testado explicitamente |
| Assunto fora do domínio do usuário aparece | brief 009: piso determinístico e conjunto de 12 casos no aceite |
| Permissão de agenda negada ou revogada | brief 005: erro explícito com instrução de onde reativar; o CSV do Google é o caminho alternativo |
| Ciclo não roda porque o Mac dormia | brief 012: recuperação de execução perdida e gatilho no login testados com o Mac de fato dormindo |
| Dado pessoal vai para o git | brief 001: `.gitignore` nasce com as regras; `git add -A` proibido pelo `AGENTS.md`; brief 013 verifica que `git status` não lista nada de `dados/` |

---

## 7. Próximo passo

Aprovado este plano, o brief 000 é escrito e entregue na aba Saídas para execução imediata; os seguintes são escritos um a um, cada um depois do relatório final do anterior.
