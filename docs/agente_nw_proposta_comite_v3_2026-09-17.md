# agente_nw — Proposta para aprovação do comitê (versão 3)

**Data:** 17 de setembro de 2026
**Substitui:** as versões 1 e 2 do mesmo dia. Mudanças em relação à v2: a **regra do conector** (seção 2.1) — o assunto precisa ligar os dois lados, com ordem de preferência e piso de domínio do usuário; ela altera o contrato de `cruzar`, a tabela `perfil_tema` do usuário, a tela do menu e os critérios de aceite. Etapas, prazos e custo não mudam.
**Repositório:** `/Users/sidarta48/github/agente_nw` — hoje só documentação (`AGENTS.md`, `docs/`); nenhum código escrito
**Máquina-alvo da Etapa 1:** MacBook Air 2024, chip M3, 16 GB de memória unificada, macOS Sonoma 14.6
**Restrição vigente:** nenhuma API de modelo de linguagem, paga ou gratuita, em nenhuma das quatro etapas. Assinaturas de Gemini, Claude e GPT entram apenas na Etapa 4, operadas por pessoa.
**Nota sobre o modelo pedido:** "Qwen 2.5 4B" não existe — a família Qwen2.5 vai de 3B para 7B. O modelo de 4B é o `qwen3:4b`, e é ele que esta proposta adota para a Etapa 1. O `qwen2.5:7b` é o primeiro degrau da Etapa 2 na mesma máquina. Se o comitê preferir ficar na família 2.5 desde o início, a alternativa é `qwen2.5:3b`, com perda de qualidade em português e em JSON; não é a recomendação.

---

## 1. O que o comitê aprova

Um pacote fechado:

1. O produto descrito na seção 2 e as decisões da seção 3.
2. O modelo de dados e os dois contratos do motor (seção 4), comuns às quatro etapas.
3. As quatro etapas, na ordem e com os critérios de passagem das seções 5 a 9.
4. A restrição de API mantida até nova decisão do comitê.
5. Início imediato da Etapa 1 com brief de execução.

---

## 2. O produto

O agente_nw dá ao usuário repertório para interações sociais mais interessantes e mais produtivas, com qualquer contato — relação pessoal, formal, de rede ou de trabalho. Para cada contato, um menu curto de assuntos do momento, escolhidos porque casam com as características que o usuário atribuiu a si mesmo e àquele contato, cada assunto com uma linha dizendo por quê.

Três regras definem o comportamento e valem em todas as etapas:

- **A relevância vem de classificação declarada.** O usuário atribui características (tags) a si e a cada contato. É esse cruzamento que decide o que é relevante para quem. O sistema não adivinha quem é o contato nem qual é a relação.
- **Lógica aditiva.** O agente trabalha com o que tiver. Contato só com tags: usa as tags. Tags mais sinal vindo de publicações do contato: o sinal soma. Contato sem dado nenhum: o sistema diz "sem assunto para este contato" e segue — não trava, não exige preenchimento prévio.
- **Sinal de rede social é reforço, nunca pré-requisito.** Entra por importação manual de publicações (Etapa 2) ou por análise em assistente pago (Etapa 4). Nenhuma raspagem automática nesta proposta.

O que fica fora, por decisão: escrever mensagem, sugerir tom, pontuar relacionamento, enviar qualquer coisa.

### 2.1 A regra do conector

Um assunto serve quando liga o usuário à pessoa-alvo. Não basta interessar ao contato: se o usuário não tem base para sustentar a conversa, o assunto produz o oposto do que se quer — bobagem dita sobre coisa que não se domina afasta em vez de aproximar. Daí três faixas, em ordem de preferência:

1. **Conector.** Relevante para os dois lados: casa com temas do contato e com temas do usuário. É o assunto ideal e vai ao topo do menu.
2. **Viável com esforço.** Relevante para o contato e só adjacente ao usuário, ou conversável por não-especialista com um resumo na mão. Entra no menu abaixo dos conectores, rotulado como tal, com a preparação anexa (cartão e resumo completo, em especial a seção "o que eu precisaria saber para não falar bobagem").
3. **Fora do domínio.** Relevante para o contato e sem nenhum ponto de apoio do usuário. **Não entra no menu.** Fica registrado com o motivo, para auditoria e calibragem, mas nunca é oferecido.

O piso entre a faixa 2 e a faixa 3 é o **domínio mínimo potencial do usuário**: o assunto passa se tiver similaridade ao menos adjacente com algum tema do usuário (limiar inicial 0,55, mais baixo que o de relevância), ou se a conversabilidade medida na qualificação for alta o bastante para um não-especialista sustentar depois de ler o cartão (inicial 0,8). Basta uma das duas. Nenhuma das duas, descarte.

Para isso funcionar, os temas do usuário — e só os dele — carregam um **nível**: *domínio* (sei falar disso), *interesse* (acompanho), *curiosidade* (falaria com um resumo na mão). O nível pesa a aderência ao usuário e define o que conta como adjacente. As tags dos contatos continuam como estão.

---

## 3. Decisões tomadas

| Decisão | Escolha |
|---|---|
| Produto | Menu de assuntos por contato. Não é lista de temas com "interessa a: Maria", não é gerador de mensagem |
| Origem da relevância | Características declaradas pelo usuário para si e para cada contato |
| Regra do conector | Score do cruzamento = aderência ao contato (peso 50) + aderência ao usuário (peso 30) + conversabilidade (peso 20). Piso de domínio mínimo do usuário: adjacência ≥ 0,55 a algum tema dele **ou** conversabilidade ≥ 0,8; sem isso o assunto não entra no menu daquele contato. Limiares iniciais, calibrados na semana 1 |
| Nível dos temas do usuário | domínio / interesse / curiosidade, só no perfil do usuário. Pesos 1,0 / 0,7 / 0,4 na aderência ao usuário |
| Quem pontua e quem escreve | A pontuação e o piso são determinísticos (cossenos e a nota de conversabilidade da qualificação). O modelo só escreve o `por_que` dos assuntos já selecionados. Modelo de 4B não decide ordenação |
| Temas | Livres, escritos em linguagem natural. O sistema normaliza para tema com sinônimos e propõe tags novas ao ler texto sobre o contato. Quem classifica é a IA; o usuário confirma com um clique |
| Escala | Base dimensionada para 100 contatos. Menu gerado só para contatos marcados como ativos ou pedidos na hora |
| Hardware da Etapa 1 | MacBook Air 2024, M3, 16 GB, macOS Sonoma 14.6. Aceleração Metal pelo Ollama. O perfil de 8 GB fica como perfil de distribuição futura, não como alvo |
| Modelo da Etapa 1 | `qwen3:4b`, quantização Q4_K_M, via Ollama, modo de raciocínio desligado. É o único modelo Qwen de 4B |
| Embeddings | `bge-m3` desde a Etapa 1 (1,2 GB, cabe com folga em 16 GB; melhor em português; dispensa prefixos). `multilingual-e5-small` só no perfil de 8 GB |
| Limiares de similaridade | Valores iniciais (0,82 para agrupar) calibrados na semana 1 com 50 pares rotulados à mão. Tarefa do brief, não constante do código |
| Categorias sensíveis | Duas camadas: regra no prompt do extrator e filtro determinístico depois do modelo (lista de termos), que descarta a tag e registra o descarte. O mesmo filtro no importador da Etapa 4 |
| Esquema e backup | Tabela `schema_version` e migrações numeradas desde a semana 1; backup diário do banco em `dados/backups/`, retenção de 7 dias, fora da pasta sincronizada |
| Interface | Console web local (Flask, `localhost:8765`) com três telas, mais exportação do menu em Markdown para pasta sincronizada |
| Roteamento de modelo | Declarado em `config/llm_routing.yaml`, com um perfil por faixa de hardware. Evoluir de modelo é trocar o perfil, não o código |
| API de LLM | Nenhuma, em nenhuma etapa |
| Dados de terceiros | Ficam no dispositivo. Saem apenas em pacote pseudonimizado, por ação do usuário (Etapa 4) |
| Exemplos de "conversável" | A IA escreve o conjunto inicial de exemplos positivos e negativos; o usuário aprova; o botão "não serve" no menu realimenta |
| Nome do pacote Python | `agente_nw`, igual à pasta. Fecha a decisão aberta nº 3 do `PLAN.md` |
| Origem dos briefs | `docs/briefs/`, fora do git. Fecha a decisão nº 2 |
| `AGENTS.md` no git | Commitado. É regra de executor, não documento de produto, e não contém dado pessoal. Fecha a decisão nº 1 |
| Processamento de importações | Em fila, na rodada seguinte, com botão "processar agora" no console. Fecha a decisão nº 4 |

---

## 4. Modelo de dados e contratos comuns às quatro etapas

O mesmo esquema serve às quatro etapas. O que muda entre elas é quem preenche cada tabela e com que qualidade.

### 4.1 Tabelas

| Tabela | Campos | Observação |
|---|---|---|
| `schema_version` | versao, aplicada_em | Migrações numeradas em `scripts/migracoes/NNN_*.sql`, aplicadas em ordem na inicialização |
| `tema` | id, nome **UNIQUE**, descricao (frase corrida), sinonimos[], embedding, criado_em | A descrição é o que vira embedding; reimportar não duplica |
| `perfil` | id, tipo (usuario/contato), nome, apelido, email, telefone, empresa, cargo, notas, ativo, gerar_agora, centroide, criado_em, atualizado_em | Um registro é o próprio usuário. `gerar_agora` é ligado pelo console ou pela agenda (Etapa 3). `centroide` é a média ponderada dos embeddings das descrições dos temas do perfil, recalculada quando `perfil_tema` muda |
| `perfil_tema` | perfil_id, tema_id, peso 1–5, origem (declarada/sugerida/importada), confirmado, **nivel** (dominio/interesse/curiosidade, só quando o perfil é o usuário; nulo para contatos), registrado_em — **UNIQUE (perfil_id, tema_id)** | `origem` é o que implementa "sinal social soma, nunca condiciona"; `nivel` é o que implementa o piso de domínio do usuário |
| `fonte` | id, nome, url_feed, dominio, tipo, confiabilidade 0–10 | |
| `item` | id, fonte_id, url_canonica, titulo, texto, publicado_em, coletado_em, hash, embedding, assunto_id | `texto` vive 90 dias |
| `assunto` | id, titulo_gerado, primeiro_visto, ultimo_visto, n_itens, n_fontes_independentes, status, centroide, temas[], substancial 0–1, conversavel 0–1, justificativa, resumo_cartao | Agrupamento por centróide, janela de 7 dias |
| `assunto_contato` | **id INTEGER PRIMARY KEY**, assunto_id, perfil_id, gerado_em, **tipo** (conector/viavel_com_esforco/fora_do_dominio), **aderencia_contato**, **aderencia_usuario**, **conversavel**, score, por_que, status (novo/usado/nao_serve/descartado), motivo | **É o menu.** Sem esta tabela o produto regride para lista por tema. Linhas `fora_do_dominio` nascem com status `descartado` e nunca são exibidas; ficam para auditoria e calibragem. O `id` é o que vai no comentário do Markdown exportado |
| `descarte_sensivel` | id, perfil_id, origem_texto, termo, registrado_em | Registro do filtro determinístico: o que foi descartado e por quê, sem guardar o trecho |
| `fato` | id, perfil_id, data_do_fato, tipo, conteudo, fonte, registrado_em | Só inserção, nunca editada. Alimentada pela importação de publicações |
| `fila_extracao` | id, perfil_id, texto, criado_em, processado, erro | Texto livre sobre um contato (cadastro, notas importadas, publicações coladas) esperando o modelo propor tags |
| `pacote_troca` | id, perfil_id ou nulo, direcao (exportado/importado), conteudo_json, pseudonimizado, criado_em, processado | Etapa 4 |

### 4.2 Os dois contratos do motor

Independentes de modelo. Todo módulo que precisa de inteligência chama uma destas duas funções e recebe JSON validado por esquema. Nenhum outro módulo sabe qual modelo está rodando.

**qualificar** — recebe um assunto (título, itens resumidos, fontes) e a lista de temas conhecidos. Devolve:

```json
{"substancial": 0.8, "conversavel": 0.7, "temas": ["credito_pj", "autonomos"], "justificativa": "regra nova, ainda em disputa, dá conversa sem ser especialista"}
```

**cruzar** — em duas partes, e só a segunda usa modelo.

A primeira parte é determinística e roda em Python. Para cada assunto candidato de um contato: `aderencia_contato` = cosseno entre o centróide do assunto e o centróide do contato; `aderencia_usuario` = maior cosseno entre o centróide do assunto e cada tema do usuário, multiplicado pelo peso do nível (domínio 1,0 / interesse 0,7 / curiosidade 0,4); `conversavel` = a nota que a qualificação já deu. Score = 50 × aderência ao contato + 30 × aderência ao usuário + 20 × conversável, em 0–100. Tipo: `conector` se a aderência ao usuário for ≥ 0,55 sem o fator de nível (isto é, o assunto casa com algum tema do usuário de fato); `viavel_com_esforco` se ficar abaixo disso mas a conversabilidade for ≥ 0,8; `fora_do_dominio` no resto. Os `fora_do_dominio` são gravados com status `descartado` e param aqui. Os demais são ordenados por tipo (conectores primeiro) e depois por score; os 5 primeiros seguem.

A segunda parte recebe o contato (apelido e tags), as tags do usuário com nível, e os até 5 assuntos já selecionados com seu tipo. O modelo escreve só o `por_que`, uma linha por assunto, e é instruído a dizer, nos viáveis com esforço, qual é o ponto de apoio do usuário:

```json
{"menu": [{"assunto_id": 812, "tipo": "conector", "score": 74,
           "por_que": "ele trabalha com crédito e vocês dois lidam com autônomos"},
          {"assunto_id": 799, "tipo": "viavel_com_esforco", "score": 58,
           "por_que": "é o setor dele; seu apoio é a parte tributária do assunto — leia o cartão antes"}],
 "sem_assunto": false, "motivo": null}
```

Quando o contato não tem tag, nenhum candidato passa do piso, ou os candidatos são todos `fora_do_dominio`, `sem_assunto` é `true` e `motivo` diz qual dos três. É esse campo que implementa "zero dado, avisa, não trava". Um modelo de 4B não decide ordenação nem exclusão; essas decisões são aritméticas e auditáveis linha a linha em `assunto_contato`.

Duas funções auxiliares, mesmo padrão: **rotular** (título de 6 a 10 palavras para um assunto novo) e **cartao** (três linhas do que aconteceu, para os assuntos que entraram em algum menu).

---

## 5. Etapa 1 — MVP com Qwen3 4B

### 5.1 Alvo

MacBook Air 2024, M3, 16 GB de memória unificada, macOS Sonoma 14.6. O Ollama usa a GPU do M3 via Metal, o que muda a natureza do problema em relação a um notebook de 8 GB sem GPU: o gargalo deixa de ser memória e tempo de CPU e passa a ser só qualidade de saída do modelo pequeno. Instalação: Ollama (instalador para macOS), Python 3.12 pelo Homebrew, `sqlite-vec` em arm64, `launchd` para agendamento. O mesmo código roda no MacBook Pro de 48 GB sem alteração — só o perfil de roteamento muda na Etapa 2.

O perfil de 8 GB sem GPU (Windows) continua descrito na seção 6.2 como perfil de distribuição futura, com as ressalvas que a revisão externa apontou: memória com folga zero e velocidade de 3 a 10 tokens por segundo conforme a idade do processador. Não é alvo desta etapa e não entra nos critérios de aceite.

### 5.2 Fluxo diário (05h00, ou no primeiro login com recuperação de execução perdida)

1. **Coleta.** `feedparser` em 20 a 40 feeds de `fontes.yaml`, mais as consultas do Google News RSS geradas automaticamente dos temas. `trafilatura` extrai o corpo. URL canônica, hash de título, descarte de ruído estrutural (teaser abaixo de 400 caracteres, título de lista, patrocinado, mais de 7 dias na primeira aparição).
2. **Embedding e agrupamento.** `bge-m3` pelo Ollama (`/api/embed`), 1024 dimensões; `sqlite-vec` no mesmo arquivo do banco. Comparação com os centróides dos assuntos abertos dos últimos 7 dias; cosseno acima do limiar entra no assunto, senão abre novo. **Limiar inicial 0,82, calibrado na semana 1** com 50 pares de itens rotulados à mão (mesmo assunto / assuntos diferentes); o valor calibrado vai para `config/limiares.yaml` e para o ADR. Fonte só conta como independente com domínio diferente e texto divergindo mais de 30%.
3. **Qualificação.** Os candidatos são os assuntos mais próximos da **união dos temas de todos os perfis ativos — o usuário e cada contato ativo**, não só os do usuário. Sem isso, um assunto que interessa a um contato mas não ao usuário nunca seria qualificado e nunca chegaria ao menu daquele contato. Teto de 40 assuntos por dia, um por chamada. Corte: `substancial` ≥ 0,6 e `conversavel` ≥ 0,6.
4. **Pré-seleção por contato.** Para cada contato ativo, o `centroide` do perfil — média dos embeddings das **descrições** dos temas dele, ponderada pelo peso — contra os centróides dos assuntos qualificados → 10 candidatos. Tag crua ("cabotagem") não vira embedding: palavra solta contra centróide de artigo rende pouco; a descrição em frase corrida do tema é o que rende. Sem modelo, custa milissegundos.
5. **Pontuação e piso (regra do conector, seção 2.1).** Para cada candidato, aderência ao contato, aderência ao usuário (com o nível do tema) e conversabilidade; tipo `conector`, `viavel_com_esforco` ou `fora_do_dominio`; os `fora_do_dominio` são gravados como descartados e não seguem. Ordenação por tipo e score; os 5 primeiros seguem. Tudo em Python, sem modelo.
6. **Cruzamento.** Uma chamada por contato ativo: o modelo escreve o `por_que` dos até 5 assuntos selecionados, apontando nos viáveis com esforço qual é o ponto de apoio do usuário. Ou `sem_assunto`, com motivo.
6. **Cartão.** Três linhas para cada assunto que entrou em pelo menos um menu.
7. **Entrega.** Console mostra o menu por contato; `menu_AAAA-MM-DD.md` é gravado na pasta de saída.

### 5.3 Configuração do modelo

| Parâmetro | qualificar / rotular | cruzar / cartão |
|---|---|---|
| Modelo | `qwen3:4b` Q4_K_M (~2,5 GB em disco) | idem |
| Modo de raciocínio | **desligado** (`think: false`) | idem |
| `format` | `json` com esquema | `json` com esquema |
| `num_ctx` | 2048 | 4096 |
| `temperature` | 0,2 | 0,3 |
| Itens por chamada | 1 | 1 |
| Exemplo resolvido no prompt | 1 | 1 |

O modo de raciocínio do Qwen3 é o detalhe que derruba esta etapa se ficar ligado: dobra o tempo de resposta e o texto de pensamento entra no JSON. Vai desligado em toda chamada, sem exceção. JSON inválido: uma nova tentativa com temperatura 0,1; segunda falha, o item vai para a fila de revisão com o erro registrado. Um exemplo resolvido dentro do prompt rende mais, nesta faixa, do que trocar de modelo.

**Memória no Air de 16 GB:** macOS com o básico aberto 4 a 5 GB, pesos do `qwen3:4b` 2,5 GB, `bge-m3` 1,2 GB, contexto e cache 0,6 GB, Python com índice 0,5 GB — cerca de 9 a 10 GB. Os dois modelos ficam carregados ao mesmo tempo (`OLLAMA_MAX_LOADED_MODELS=2`, `OLLAMA_KEEP_ALIVE=30m`), sem fase de descarregar e recarregar. O ciclo pode rodar com o navegador aberto. Não há swap a temer nesta máquina; a ressalva de "folga zero" vale só para o perfil de 8 GB da seção 6.2.

### 5.4 Orçamento de chamadas e tempo

800 itens coletados → 300 depois das regras → 40 assuntos formados → até 40 qualificados (40 chamadas, porque a qualificação agora cobre os temas de todos os perfis ativos) → 10 contatos ativos cruzados (10 chamadas) → cerca de 15 cartões (15 chamadas). **Cerca de 65 chamadas por dia**, não 800.

No M3 com Metal, o `qwen3:4b` Q4 produz na faixa de 25 a 40 tokens por segundo; cada chamada devolve 100 a 300 tokens, ou seja, 4 a 10 segundos por chamada. Embeddings de 300 itens com `bge-m3` levam 1 a 2 minutos. Estimativa: 5 a 10 minutos de modelo, mais 5 de coleta e extração — **10 a 15 minutos de ciclo**, medidos na primeira semana. Com 30 contatos ativos, 12 a 20 minutos.

### 5.5 Interface

Flask em `localhost:8765`, só em `127.0.0.1`, sem framework de frontend. Três telas:

- **Contatos.** Lista e ficha. Na ficha: tags com peso e origem, marcar ativo, botão "gerar menu agora". Cadastro por texto livre: o usuário cola o que sabe da pessoa ("advogado tributarista, corre, gosta de vinho, cliente desde 2023"), o modelo propõe as tags com origem `sugerida`, o usuário confirma com um clique. O extrator é instruído a nunca registrar saúde, religião, política, sindicato, vida sexual, origem racial ou dados de menores — e, como um modelo de 4B obedece na maior parte das vezes e não sempre, um **filtro determinístico** roda depois dele: lista de termos por categoria, em `nucleo/sensivel.py`, que descarta a tag ou o fato, grava o descarte em `descarte_sensivel` sem o trecho, e nunca deixa o item chegar ao banco. O mesmo filtro roda sobre as notas importadas do Google Contatos (Etapa 3) e sobre tudo que volta dos assistentes (Etapa 4).
- **Menu.** Por contato, em duas faixas visíveis: **conectores** no alto, **viáveis com esforço** abaixo, cada um com `por_que` e cartão expandível; nos viáveis, o cartão abre por padrão, e a partir da Etapa 2 o resumo completo com "o que eu precisaria saber para não falar bobagem" fica a um clique. Botões "usei" e "não serve" (motivo entre cinco fixos: não interessa a ele, velho, raso, não dá conversa, **eu não domino** — este último realimenta o piso). Os `fora_do_dominio` não aparecem; um contador discreto ("3 assuntos ficaram fora por domínio") permite abrir a lista se o usuário quiser revisar.
- **Temas.** Edição em linguagem natural, sinônimos, sugestões pendentes de confirmação. Nos temas do usuário, o nível (domínio / interesse / curiosidade) com um seletor de três posições.

A exportação `menu_AAAA-MM-DD.md` traz um bloco por contato com caixas de marcação; um script lê as marcações de volta na rodada seguinte. É o que permite ler e marcar no celular via pasta sincronizada (Etapa 3).

### 5.6 Fora de escopo da Etapa 1

Raspagem ou extensão de navegador, sincronização, assistentes pagos, resumo completo do assunto (só o cartão), balanço semanal, multiusuário.

### 5.7 Critérios de aceite

1. Cinco dias seguidos de ciclo sem intervenção, no MacBook Air M3.
2. Menu gerado para pelo menos 5 contatos ativos, com 3 ou mais assuntos cada; contato sem tag recebe `sem_assunto` e não trava o ciclo.
2a. Regra do conector verificada com um conjunto de teste de 12 casos montado à mão (4 conectores, 4 viáveis, 4 fora do domínio): conectores sempre acima dos viáveis no menu; nenhum `fora_do_dominio` exibido; os 4 fora do domínio gravados como descartados com motivo; um assunto viável traz no `por_que` o ponto de apoio do usuário.
3. JSON válido na primeira tentativa em pelo menos 95% das chamadas.
4. Ciclo completo em no máximo 20 minutos com 10 contatos ativos.
5. Todo `assunto_id` presente em um menu existe no banco — zero invenção.
6. Limiar de agrupamento calibrado com a amostra de 50 pares e registrado em ADR; `schema_version` em uso com pelo menos uma migração aplicada; backup diário gerado e restaurado uma vez em teste.
7. Filtro de categorias sensíveis testado com um conjunto de 30 frases (15 que devem passar, 15 que devem ser descartadas), 100% de acerto.

**Indicador acompanhado, não critério:** aproveitamento (marcados "usei" ÷ entregues). A revisão externa tem razão em não fazer disso meta de aceite — "conversável" é calibrado continuamente, pelo balanço semanal da Etapa 2, e não cravado numa semana. O número é registrado desde o primeiro dia para servir de linha de base.

### 5.8 Esforço

Três semanas, uma pessoa, Claude Code executando a partir de briefs. Semana 1: núcleo (esquema com `schema_version` e migrações, contratos, cliente de LLM, roteamento, filtro sensível, backup diário) e coleta; calibração do limiar de agrupamento com a amostra rotulada. Semana 2: agrupamento, qualificação, cruzamento, menu. Semana 3: console, exportação, medição de aceite.

---

## 6. Etapa 2 — Evolução do MVP para Qwen mais potentes

### 6.1 O que não muda

Código, banco, contratos, estrutura dos prompts, console, embeddings (`bge-m3` já é o padrão desde a Etapa 1). A evolução é um perfil novo em `llm_routing.yaml`. Só o perfil de 8 GB, se um dia for ativado, exige migração de embeddings — e nesse caso é ele que migra para `e5-small`, não o contrário.

### 6.2 Perfis de hardware

| Perfil | Máquina | Modelo generativo | Embeddings | `num_ctx` (qualificar / cruzar / cartão) |
|---|---|---|---|---|
| `air16` — **Etapa 1** | MacBook Air M3, 16 GB | `qwen3:4b` | `bge-m3` | 2048 / 4096 / 4096 |
| `air16b` — primeiro degrau da Etapa 2 | mesma máquina | `qwen2.5:7b` para cartão e resumo completo; `qwen3:4b` segue em qualificar e cruzar | `bge-m3` | 4096 / 8192 / 8192 |
| `air16c` | mesma máquina | `qwen3:8b` em tudo (5 GB em disco; cabe com folga ao lado do `bge-m3`) | `bge-m3` | 4096 / 8192 / 8192 |
| `pro48` | MacBook Pro, 48 GB | `qwen3:30b-a3b` para qualificar e cruzar (mistura de especialistas, rápido); `qwen3:32b` ou `qwen2.5:14b` para cartão e resumo | `bge-m3` | 8192 / 16384 / 16384 |
| `win8` — distribuição futura | notebook de 8 GB, sem GPU, Windows | `qwen3:4b` | `multilingual-e5-small` (384 dim.), com os prefixos `query:` e `passage:` que o modelo exige | 2048 / 4096 / 4096 |

O perfil `win8` carrega as ressalvas da revisão externa: memória com folga zero (o sistema com Defender, OneDrive e Drive para computador passa de 3,5 GB), o que obriga a rodar embeddings e modelo em fases separadas com `keep_alive: 0`; velocidade de 3 a 10 tokens por segundo conforme o processador, o que transforma os 15 minutos do Air em 40 a 90; e limiar de agrupamento a recalibrar, porque a distribuição de similaridade do `e5-small` é comprimida (textos sem relação ficam em 0,7–0,8). Nada disso é problema da Etapa 1; é o preço de levar o produto a uma máquina fraca, e será medido numa máquina de 8 GB de verdade quando esse perfil for ativado.

### 6.3 O que cada degrau libera

- **7B (`qwen2.5:7b`):** resumo completo do assunto (linha do tempo, números com fonte, posições em disputa, "o que eu precisaria saber para não falar bobagem"); `por_que` mais específico; balanço semanal com calibragem automática de peso de tema e confiabilidade de fonte — é aqui que "conversável" passa a ser calibrado continuamente.
- **8B (`qwen3:8b`):** extração de tags a partir de publicações coladas **com lastro** — cada tag aponta para o trecho que a justifica; detecção de mudança de cargo, empresa ou cidade em texto colado, gravada como fato datado; menu para 30 contatos ativos no Air em menos de 20 minutos.
- **30B-A3B / 32B (só no Pro de 48 GB):** síntese de perfil por contato em texto para o usuário ler; pesos de tema sugeridos a partir do histórico de "usei" e "não serve"; menu para 100 contatos em minutos.

### 6.4 Protocolo de promoção — decidido por medida, não por impressão

Separar 20 assuntos e 10 contatos. Rodar o perfil atual e o candidato no mesmo material. Registrar: percentual de JSON válido na primeira tentativa; concordância no menu (mesmos 3 primeiros assuntos, ou diferença de score menor que 0,10); tempo por chamada. Um perfil menor só é mantido numa tarefa com **JSON válido acima de 98%** e **concordância acima de 85%** com o perfil maior. Resultado registrado em ADR. O mesmo protocolo vale no sentido inverso: um modelo maior que não melhora a concordância não justifica o tempo extra.

### 6.5 Importação manual de publicações — o sinal social desta proposta

Tela "Colar publicações" na ficha do contato. O usuário copia o texto visível das publicações de alguém (LinkedIn, Instagram, X, blog) e cola. Nada é raspado; é o usuário lendo o que está público e trazendo para o sistema, dentro dos termos de uso de cada rede. O modelo devolve:

```json
{"tags_sugeridas": [{"tag": "cabotagem", "peso": 3, "trecho": "publicou sobre o novo terminal de cabotagem em Santos"}],
 "fatos_datados": [{"data": "2026-09-12", "tipo": "publicacao", "conteudo": "comentou o terminal de cabotagem em Santos", "fonte": "LinkedIn"}]}
```

Tags passam pelo filtro determinístico de categorias sensíveis e entram em `perfil_tema` com origem `sugerida` e `confirmado = false`; o usuário confirma uma a uma. Fatos entram em `fato`, só inserção. Com o 4B funciona sem lastro; com 8B ou acima, lastro obrigatório e tag sem trecho é cortada.

### 6.6 Esforço e aceite

Duas semanas. Semana 4: perfis `air16b` e `air16c`, protocolo de medição, ADR. Semana 5: importação de publicações, resumo completo, balanço semanal. Passa quando: o perfil candidato concorda em 85% ou mais com `air16` nos 3 primeiros assuntos de 10 contatos e entrega pelo menos um assunto durável que o 4B perdeu; uma importação real de publicações produz tags confirmadas pelo usuário; o balanço semanal roda duas semanas seguidas e ajusta ao menos um peso de tema a partir das marcações.

---

## 7. Etapa 3 — Integrações com Google One e outros serviços, sem API de LLM

### 7.1 Princípio

O Google One entrega armazenamento no Drive e o aplicativo do Gemini. Não dá chave de API nem altera cota de nada — e esta etapa não precisa disso. Tudo abaixo usa o que uma conta Google comum já oferece sem OAuth e sem chave: exportação de contatos, Google Alerts em RSS, Google News em RSS, endereço secreto da agenda em iCal, pasta do Drive sincronizada no computador, e Apps Script com gatilho de tempo. Nenhum modelo de linguagem roda fora da máquina.

### 7.2 Google Contatos → fichas

O usuário exporta em `contacts.google.com` (Exportar → Google CSV). O script cria ou atualiza `perfil` por e-mail ou telefone, transforma os marcadores do Google em tags com origem `importada`, e enfileira o campo "Notas" para o modelo local propor tags com origem `sugerida`. Reimportar é idempotente.

```python
# integracoes/google_contatos.py
import csv, sqlite3, sys

def campo(row, *prefixos):
    for k, v in row.items():
        if k and v and any(k.lower().startswith(p) for p in prefixos):
            return v.strip()
    return None

def importar(csv_path, db_path):
    db = sqlite3.connect(db_path)
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            nome = row.get("Name") or " ".join(x for x in [row.get("First Name"), row.get("Last Name")] if x)
            email = campo(row, "e-mail 1 - value")
            tel = campo(row, "phone 1 - value")
            if not (nome and (email or tel)):
                continue
            empresa = campo(row, "organization 1 - name", "organization name")
            cargo = campo(row, "organization 1 - title", "organization title")
            notas = campo(row, "notes")
            marcadores = [m.strip() for m in (campo(row, "group membership", "labels") or "").split(":::")
                          if m.strip() and not m.startswith("*")]
            pid = db.execute("SELECT id FROM perfil WHERE email=? OR telefone=?", (email, tel)).fetchone()
            if pid:
                db.execute("UPDATE perfil SET nome=?, empresa=?, cargo=?, notas=?, atualizado_em=datetime('now') WHERE id=?",
                           (nome, empresa, cargo, notas, pid[0]))
                pid = pid[0]
            else:
                pid = db.execute("INSERT INTO perfil(tipo,nome,email,telefone,empresa,cargo,notas,ativo,criado_em,atualizado_em) "
                                 "VALUES('contato',?,?,?,?,?,?,0,datetime('now'),datetime('now'))",
                                 (nome, email, tel, empresa, cargo, notas)).lastrowid
            for m in marcadores:
                # depende de UNIQUE em tema.nome e em perfil_tema(perfil_id, tema_id), declarados no esquema
                db.execute("INSERT OR IGNORE INTO tema(nome,descricao,criado_em) VALUES(?,?,datetime('now'))", (m.lower(), m))
                tid = db.execute("SELECT id FROM tema WHERE nome=?", (m.lower(),)).fetchone()[0]
                db.execute("INSERT OR IGNORE INTO perfil_tema(perfil_id,tema_id,peso,origem,confirmado,registrado_em) "
                           "VALUES(?,?,3,'importada',0,datetime('now'))", (pid, tid))
            if notas:
                # o filtro de categorias sensíveis roda quando a fila é processada, antes de qualquer tag entrar
                db.execute("INSERT INTO fila_extracao(perfil_id,texto,criado_em) VALUES(?,?,datetime('now'))", (pid, notas))
    db.commit()

if __name__ == "__main__":
    importar(sys.argv[1], sys.argv[2])
```

Os nomes de coluna variam entre versões da exportação do Google; o script casa por prefixo e ignora o que não reconhece.

### 7.3 Google Alerts e Google News → fontes

Dois caminhos, ambos RSS. O Google News aceita consulta na URL e o script gera uma consulta por tema a partir do nome e dos sinônimos. O Google Alerts é criado à mão em `google.com/alerts` com entrega "Feed RSS", e a URL do feed é colada em `config/local.yaml` — não em `fontes.yaml`, porque a URL de um alerta identifica a conta. Regra de arquivos: `fontes.yaml` e `config/local.yaml` ficam fora do git; `fontes.exemplo.yaml` é versionado com três feeds públicos, no mesmo padrão já adotado para `temas.exemplo.yaml`. O script abaixo gera as entradas do Google News.

```python
# integracoes/fontes_google.py
from urllib.parse import quote
import sqlite3, yaml, sys

def url_google_news(consulta):
    return f"https://news.google.com/rss/search?q={quote(consulta)}&hl=pt-BR&gl=BR&ceid=BR:pt-419"

def gerar(db_path, fontes_yaml):
    db = sqlite3.connect(db_path)
    fontes = yaml.safe_load(open(fontes_yaml, encoding="utf-8")) or {"feeds": []}
    existentes = {f["url"] for f in fontes["feeds"]}
    for nome, sinonimos in db.execute("SELECT nome, sinonimos FROM tema"):
        termos = [nome] + (yaml.safe_load(sinonimos) if sinonimos else [])
        consulta = " OR ".join(f'"{t}"' for t in termos[:4])
        url = url_google_news(consulta)
        if url not in existentes:
            fontes["feeds"].append({"nome": f"Google News · {nome}", "url": url, "tipo": "agregador", "confiabilidade": 5})
    yaml.safe_dump(fontes, open(fontes_yaml, "w", encoding="utf-8"), allow_unicode=True, sort_keys=False)

if __name__ == "__main__":
    gerar(sys.argv[1], sys.argv[2])
```

A codificação da consulta com `quote` é obrigatória; termo com espaço sem codificar é o erro mais comum nesse feed. Intervalo de 2 segundos entre chamadas ao Google News.

### 7.4 Pasta do Drive → menu no celular e marcação de volta

Sem script novo no lado do Google: a pasta de saída do agente passa a ser uma pasta do Drive para computador. O `menu_AAAA-MM-DD.md` aparece no celular no aplicativo do Drive ou no Obsidian em minutos. O usuário marca as caixas no celular; o script abaixo lê o arquivo na rodada seguinte e grava em `assunto_contato`.

Formato gerado pelo agente (o identificador fica em comentário HTML, invisível na leitura):

```markdown
## Ricardo  <!-- perfil:14 -->
### Conectores
#### Crédito consignado para autônomos entra em vigor  <!-- ac:812 -->
Por quê: ele trabalha com crédito e vocês dois lidam com autônomos.
- [ ] usei
- [ ] não serve → motivo: ( ) não interessa a ele ( ) velho ( ) raso ( ) não dá conversa ( ) eu não domino
### Viáveis com esforço
#### Novo terminal de cabotagem em Santos  <!-- ac:799 -->
Por quê: é o setor dele; seu apoio é a parte tributária do assunto — leia o cartão antes.
- [ ] usei
- [ ] não serve → motivo: ( ) não interessa a ele ( ) velho ( ) raso ( ) não dá conversa ( ) eu não domino
```

```python
# integracoes/ler_marcacoes.py
import re, sqlite3, sys, pathlib

BLOCO = re.compile(r"<!-- ac:(\d+) -->(.*?)(?=<!-- ac:|\Z)", re.S)
MOTIVOS = {"não interessa a ele": "nao_interessa", "velho": "velho", "raso": "raso",
           "não dá conversa": "nao_da_conversa", "eu não domino": "nao_domino"}

def ler(md_path, db_path):
    db = sqlite3.connect(db_path)
    texto = pathlib.Path(md_path).read_text(encoding="utf-8")
    for ac_id, corpo in BLOCO.findall(texto):
        if re.search(r"- \[x\] usei", corpo, re.I):
            db.execute("UPDATE assunto_contato SET status='usado' WHERE id=?", (ac_id,))
        elif re.search(r"- \[x\] não serve", corpo, re.I):
            motivo = next((v for k, v in MOTIVOS.items() if re.search(rf"\(x\) {re.escape(k)}", corpo, re.I)), None)
            db.execute("UPDATE assunto_contato SET status='nao_serve', motivo=? WHERE id=?", (motivo, ac_id))
    db.commit()

if __name__ == "__main__":
    ler(sys.argv[1], sys.argv[2])
```

### 7.5 Google Agenda → menu antes da reunião

A agenda tem um "endereço secreto no formato iCal" (Configurações → a agenda → Integrar). É uma URL sem autenticação; fica em `config/local.yaml`, fora do git. O script baixa o `.ics`, pega os eventos das próximas 48 horas, extrai os e-mails dos convidados e, quando um deles bate com um `perfil`, marca o contato para "gerar menu agora" com prioridade. Resultado: antes de cada reunião com alguém da base, o menu daquela pessoa já está pronto.

```python
# integracoes/agenda_ical.py
import httpx, sqlite3, sys
from datetime import datetime, timedelta, timezone
from icalendar import Calendar

def convidados_proximos(url_ical, horas=48):
    cal = Calendar.from_ical(httpx.get(url_ical, timeout=30, follow_redirects=True).content)
    agora = datetime.now(timezone.utc); limite = agora + timedelta(hours=horas)
    emails = set()
    for ev in cal.walk("VEVENT"):
        ini = ev.get("DTSTART").dt
        if not isinstance(ini, datetime):
            continue
        ini = ini if ini.tzinfo else ini.replace(tzinfo=timezone.utc)
        if agora <= ini.astimezone(timezone.utc) <= limite:
            att = ev.get("ATTENDEE", [])
            for a in (att if isinstance(att, list) else [att]):
                emails.add(str(a).replace("mailto:", "").lower())
    return emails

def marcar(db_path, url_ical):
    db = sqlite3.connect(db_path)
    for email in convidados_proximos(url_ical):
        db.execute("UPDATE perfil SET ativo=1, gerar_agora=1 WHERE lower(email)=? AND tipo='contato'", (email,))
    db.commit()

if __name__ == "__main__":
    marcar(sys.argv[1], sys.argv[2])
```

Eventos recorrentes vêm como regra, não expandidos; a primeira versão considera só ocorrências únicas, o que cobre reuniões marcadas com pessoa de fora.

### 7.6 Apps Script → coleta noturna com o notebook desligado (opcional)

Só faz sentido se o notebook ficar desligado por dias. Um script numa conta Google comum, com gatilho diário, baixa os feeds e grava o XML bruto numa pasta do Drive; quando o notebook liga, o agente lê a pasta sincronizada em vez de chamar os feeds. Nenhum modelo, nenhuma inteligência no lado Google — só cobertura. A cota gratuita (20 mil chamadas de rede por dia, 90 minutos de gatilho) cobre 80 feeds com folga.

```javascript
// integracoes/coleta_noturna.gs — Apps Script, conta Google comum
const PASTA_ID = "id-da-pasta-agente_nw-no-drive";
const FEEDS = ["https://news.google.com/rss/search?q=...", "https://www.infomoney.com.br/feed/"]; // ou lidos de fontes.yaml copiado ao Drive

function coletaNoturna() {
  const hoje = Utilities.formatDate(new Date(), "America/Sao_Paulo", "yyyy-MM-dd");
  const pasta = DriveApp.getFolderById(PASTA_ID).createFolder("coleta_" + hoje);
  FEEDS.forEach((url, i) => {
    try {
      const xml = UrlFetchApp.fetch(url, {muteHttpExceptions: true, followRedirects: true}).getContentText();
      pasta.createFile("feed_" + String(i).padStart(3, "0") + ".xml", xml, "application/xml");
    } catch (e) {
      pasta.createFile("erro_" + i + ".txt", String(e));
    }
  });
}
// Gatilho: Gatilhos → adicionar → coletaNoturna → baseado em tempo → diário → 5h–6h
```

O mesmo script pode expor o `menu.json` mais recente numa página web simples (`doGet`), para leitura sem o Drive. Fica registrado, não entra no escopo desta etapa.

### 7.7 Outros serviços, todos por RSS ou REST público sem chave

| Serviço | Como entra | Para quê |
|---|---|---|
| YouTube (canal) | `https://www.youtube.com/feeds/videos.xml?channel_id=ID` | assunto de canais que os contatos seguem |
| Substack, Medium, blogs | `/feed` | texto longo, fonte de assunto durável |
| Reddit | `/r/<sub>/.rss` | assunto em comunidade especializada (não-obviedade) |
| Hacker News | `https://hnrss.org/frontpage` | tecnologia |
| Diário Oficial da União | RSS de `in.gov.br` | assunto oficial |
| BrasilAPI CNPJ | `https://brasilapi.com.br/api/cnpj/v1/<CNPJ>` — REST público, sem chave, ~3 chamadas/min | setor da empresa do contato vira tag `sugerida` |
| Obsidian | abre a pasta do Drive | leitura e marcação no computador e no celular |

Redes sociais não entram aqui: sem raspagem, conforme seção 2.

### 7.8 Esforço e aceite

Uma semana. Passa quando: um CSV real de contatos importa com tags; todos os temas têm feed do Google News gerado; o menu do dia aparece no celular em até 5 minutos após o ciclo; marcação feita no celular chega ao banco na rodada seguinte; contato com reunião nas próximas 48 horas recebe menu gerado com prioridade.

---

## 8. Etapa 4 — Gemini, Claude e GPT pagos, com pessoa fazendo a ponte

### 8.1 Princípio

As três assinaturas aceitam instruções fixas e arquivos anexados (Projetos no ChatGPT e no Claude, Gems no Gemini). Sem API. O agente exporta um pacote; a pessoa cola no assistente; o assistente devolve JSON; a pessoa cola de volta; o agente importa, valida e pede confirmação. Tudo que sai é pseudonimizado; o nome só volta na máquina.

### 8.2 Pacote de exportação

```json
{"versao": 1, "gerado_em": "2026-09-17T06:10:00-03:00", "pedido": "refinar_menu",
 "usuario": {"tags": ["direito tributário", "software jurídico", "corrida de rua"]},
 "contato": {"id_pseudo": "P-014", "cargo_generico": "diretor comercial", "setor": "logística",
             "tags": [{"tag": "cabotagem", "peso": 4}, {"tag": "ESG", "peso": 2}]},
 "assuntos_candidatos": [{"assunto_id": 812, "titulo": "...", "cartao": ["...", "...", "..."], "fontes": ["https://..."], "data": "2026-09-15"}],
 "menu_local": [{"assunto_id": 812, "tipo": "conector", "score": 74, "por_que": "..."}],
 "publicacoes_coladas": null}
```

Regras do pacote: sem nome, telefone, e-mail, sem nome de empresa em hipótese alguma; `cargo_generico` e `setor` vêm de **listas fechadas e grosseiras** (cerca de 20 categorias de cargo — "direção comercial", "advocacia", "engenharia" — e as seções do CNAE para setor), nunca do texto livre da ficha. É por construção, não por verificação, que uma combinação rara de cargo e setor deixa de identificar alguém: a lista não tem granularidade para isso. `id_pseudo` é gerado por contato e resolvido só localmente.

Um teste automatizado percorre cada pacote antes de gravar em `pacote_troca` e recusa se encontrar: nome, apelido, telefone ou e-mail de qualquer perfil; nome de qualquer empresa cadastrada em qualquer ficha; qualquer valor de cargo ou setor fora das listas fechadas. O teste é uma varredura por lista, não um julgamento de modelo.

### 8.3 Os três usos

**Refinar o menu.** O assistente reordena, reescreve o `por_que` e pode acrescentar até 2 assuntos que encontrou por busca própria, cada um com URL e data. O agente mostra a diferença entre o menu local e o refinado; o usuário aceita ou não. Assunto novo entra em `assunto` com fonte `assistente` e passa pela qualificação local como qualquer outro.

**Sugerir tags a partir de publicações.** A pessoa cola no pacote (`publicacoes_coladas`) o texto visível das publicações do contato, ou cola direto no assistente. O assistente devolve tags com o trecho que as justifica. Entram como `sugerida`, `confirmado = false`, confirmação uma a uma. É a análise de rede social desta proposta: sem raspagem, sem API, com pessoa lendo o que está público.

**Pesquisa profunda semanal.** Uma vez por semana, o usuário pede ao assistente (Deep Research no Gemini ou no ChatGPT, pesquisa no Claude) os assuntos das últimas duas semanas nos temas dele. O retorno entra como assuntos com fonte `pesquisa`, com URL obrigatória, e passa pela qualificação local.

### 8.4 Instrução fixa para o Projeto, Gem ou GPT

```
Você recebe um pacote JSON do agente_nw com: as características do usuário; as características
de UM contato identificado só por código (P-000); assuntos candidatos com fontes; e um pedido
(refinar_menu, sugerir_tags ou pesquisar_temas). Pode receber também publicações coladas.

Responda SOMENTE com JSON no esquema de retorno, sem texto antes ou depois, sem cerca de código.

Regras:
- Nunca tente identificar o contato. Nunca peça nome, empresa ou telefone.
- Todo assunto novo vem com URL real e data. Sem URL, não inclua.
- Toda tag sugerida vem com o trecho que a justifica, copiado do material recebido.
- Não extraia nem sugira: saúde, religião, política, sindicato, vida sexual, origem racial,
  dados de menores. Se aparecer no material, ignore.
- Não escreva mensagem, não sugira tom, não opine sobre a relação entre o usuário e o contato.
- Respeite o tipo de cada assunto (conector ou viavel_com_esforco). Não promova assunto que só
  interesse ao contato sem apoio nas características do usuário; se sugerir assunto novo, diga
  em por_que qual característica do usuário o sustenta.
- Se não houver nada a acrescentar, devolva as listas vazias.

Esquema de retorno:
{"versao": 1, "contato_id_pseudo": "P-000",
 "menu_refinado": [{"assunto_id": 0, "score": 0.0, "por_que": ""}],
 "assuntos_novos": [{"titulo": "", "url": "", "data": "AAAA-MM-DD", "por_que": ""}],
 "tags_sugeridas": [{"tag": "", "peso": 1, "evidencia": ""}],
 "observacoes": ""}
```

### 8.5 Importação e validação

O importador aceita o JSON colado, tolera cerca de código e espaços, valida contra o esquema e, se falhar, mostra o campo que quebrou e pede nova colagem — nunca conserta JSON por expressão regular. Toda tag passa pelo filtro determinístico de categorias sensíveis e entra sem confirmação; todo assunto novo exige URL; o `por_que` refinado só substitui o local depois que o usuário aceita a diferença na tela. O pacote de ida e o de volta ficam em `pacote_troca` para auditoria.

### 8.6 Variante sem copiar e colar

Uma tarefa agendada do Claude (Cowork) com o conector do Google Drive lê o pacote que o agente deixou na pasta sincronizada e grava `retorno_AAAA-MM-DD.json` na mesma pasta; o agente importa na rodada seguinte. A pessoa age só na configuração e na confirmação das tags. Gemini e ChatGPT também têm tarefas agendadas, mas respondem no chat, e o retorno precisa ser colado. Nenhuma das três variantes usa API.

A revisão externa pediu para marcar esta combinação como "a verificar". Foi verificada: na data desta proposta, o conector do Google Drive no Claude expõe criação e atualização de arquivos, e as tarefas agendadas do Cowork rodam com os conectores da conta. A ressalva que fica é a de nomenclatura — "Projetos", "Gems", "Deep Research", "tarefas agendadas" são os nomes em setembro de 2026 e mudam com frequência; o que não muda é a capacidade (instrução fixa, arquivo anexado, execução programada), e é dela que a etapa depende.

### 8.7 Esforço e aceite

Uma semana. Passa quando: ida e volta completa em cada uma das três plataformas com 3 contatos; tags importadas e confirmadas; diferença de menu exibida e aceita ou recusada; teste de pseudonimização passando em 100% dos pacotes gerados.

---

## 9. Cronograma e condições de passagem

| Etapa | Semanas | Entrega | Passa quando |
|---|---|---|---|
| 1 — MVP Qwen3 4B | 1 a 3 | ciclo diário, menu por contato, console, exportação | critérios da seção 5.7 |
| 2 — Evolução de modelo | 4 e 5 | perfis de hardware (7B e 8B no Air, 30B/32B no Pro), protocolo de medição, importação de publicações, resumo completo, balanço semanal | seção 6.6 |
| 3 — Integrações Google e RSS | 6 | contatos, alerts, news, Drive, agenda, scripts da seção 7 | seção 7.8 |
| 4 — Ponte com assistentes pagos | 7 | exportação, instrução fixa, importação, pseudonimização | seção 8.7 |

Sequência fixa; cada etapa começa com a anterior certificada. As Etapas 3 e 4 são independentes entre si e podem ser invertidas se o comitê preferir. Estimativas assumem uma pessoa em tempo integral e Claude Code executando briefs.

---

## 10. Riscos e controles

| Risco | Controle |
|---|---|
| JSON quebrado ou resposta genérica no 4B | esquema forçado, modo de raciocínio desligado, um exemplo resolvido no prompt, uma nova tentativa, fila de revisão; menu só referencia `assunto_id` existente |
| "Conversável" é subjetivo | conjunto de exemplos positivos e negativos escrito pela IA e aprovado pelo usuário antes de calibrar; botão "não serve" com motivo fixo realimenta semanalmente |
| Release distribuído a quinze portais parece assunto denso | fonte só é independente com domínio diferente e texto divergindo mais de 30% |
| Feeds instáveis | adaptadores por fonte, hash por URL canônica e título normalizado, alerta quando um feed volta vazio dois dias seguidos |
| Dados pessoais de terceiros (LGPD) | tudo local por padrão; pacote pseudonimizado com cargo e setor de listas fechadas, testado antes de sair; categorias sensíveis barradas em duas camadas (prompt e filtro determinístico) com registro do descarte; `notas` aceita fato datado, não opinião; backup fora da pasta sincronizada |
| Limiar de similaridade errado junta tudo num assunto ou fatia o mesmo assunto em três | valor inicial 0,82 tratado como hipótese; calibração na semana 1 com 50 pares rotulados; recalibração obrigatória a cada troca de modelo de embedding |
| Esquema evolui à mão ao longo de quatro etapas | `schema_version` e migrações numeradas desde a semana 1; nenhuma alteração de tabela fora de migração |
| Perda do banco (semanas de tags confirmadas) | backup diário pela API de backup do SQLite em `dados/backups/`, retenção de 7 dias, restauração testada na semana 1; Time Machine cobre o resto |
| Formatos do Google mudam (colunas do CSV, iCal) | leitores tolerantes, casamento por prefixo, erro explícito em vez de importação silenciosa errada |
| Câmara de eco (sempre os mesmos assuntos e contatos) | teto de 3 assuntos por tema por dia; métrica de concentração no balanço semanal |
| Usuário fala bobagem sobre assunto que não domina e afasta o contato | regra do conector: piso de domínio mínimo determinístico, viáveis com esforço rotulados e com preparação anexa, motivo "eu não domino" no botão "não serve" realimentando o piso; os descartes por domínio ficam auditáveis |
| Piso de domínio mal calibrado esconde assunto bom ou deixa passar assunto perigoso | limiares 0,55 e 0,8 são iniciais; calibração na semana 1 com os 12 casos de teste e revisão no balanço semanal a partir dos motivos "eu não domino" e "não dá conversa" |
| Ciclo não roda porque o notebook estava desligado | gatilho no login com atraso de 5 minutos e verificação no banco de "já rodou hoje"; cada etapa retomável |

---

## 11. Aprovação pedida

O comitê aprova, em bloco: o produto (seção 2), as decisões (seção 3), o modelo de dados e os contratos (seção 4), as quatro etapas com prazos e critérios (seções 5 a 9), a manutenção da restrição de API, e o início da Etapa 1 com brief de execução na semana seguinte à aprovação.

Aprovado, o próximo passo é atualizar `PLANO.md` e `ARQUITETURA.md` do repositório com o modelo de dados da seção 4 e a saída por contato, e escrever o brief da semana 1.

---

## 12. Críticas recebidas — o que foi aceito, ajustado e rejeitado

Duas revisões externas foram feitas sobre a versão 1. Cada ponto abaixo diz o que mudou no documento e por quê; onde não mudou, diz por que não.

### Aceitas integralmente

**Qualificar só pelos temas do usuário era um erro de lógica.** Verdade, e o mais grave da versão 1: um assunto que interessa a um contato nunca chegaria sequer a ser considerado. Corrigido na seção 5.2: a qualificação usa a união dos temas de todos os perfis ativos, com teto de 40 por dia. O orçamento de chamadas sobe de 37 para 65 e, no Air, isso custa uns 5 minutos.

Essa correção, porém, resolvia só metade: considerar não é oferecer. A versão 2 não dizia como ordenar nem quando barrar, e a revisão do autor apontou o que faltava — o assunto é um conector entre os dois lados; o ideal interessa aos dois; o viável mínimo interessa só ao contato e exige esforço do usuário; e o que o usuário não tem como sustentar não deve ser oferecido, porque bobagem dita afasta. Isso virou a regra do conector da seção 2.1, com o piso de domínio mínimo, o nível nos temas do usuário e o cruzamento em duas partes (pontuação determinística, modelo só no `por_que`). É a mudança da versão 3.

**Pré-seleção por tag crua rende pouco.** Verdade: "cabotagem" como vetor contra o centróide de um artigo é sinal fraco. Corrigido: cada perfil ganha um `centroide`, média ponderada dos embeddings das descrições em frase corrida dos seus temas; é isso que vai contra os centróides dos assuntos.

**Limiar de cosseno como valor fixo.** Aceito: 0,82 vira valor inicial, calibrado na semana 1 com 50 pares rotulados, registrado em ADR e recalibrado a cada troca de modelo de embedding. A observação sobre a distribuição comprimida do `e5-small` e sobre os prefixos `query:`/`passage:` está correta e foi anotada no perfil de 8 GB, o único onde esse modelo é usado.

**Restrições UNIQUE ausentes.** Aceito; sem elas o `INSERT OR IGNORE` não protege nada e reimportar duplica. Declaradas em `tema.nome` e em `perfil_tema (perfil_id, tema_id)`; o script de importação foi ajustado para depender delas explicitamente.

**`rowid` no leitor de marcações.** Aceito; `assunto_contato` ganha `id INTEGER PRIMARY KEY` e o script usa `id`.

**Filtro determinístico de categorias sensíveis.** Aceito sem ressalva. Um 4B obedece à instrução na maior parte das vezes, e "na maior parte" não serve para dado de terceiros. O filtro por lista roda depois do modelo no extrator, na fila de notas importadas e no importador da Etapa 4, descarta e registra o descarte sem guardar o trecho. A limitação é conhecida — lista pega termo explícito, não insinuação — e por isso as duas camadas coexistem.

**Versionamento de esquema.** Aceito; `schema_version` e migrações numeradas desde a semana 1. Quatro etapas alterando tabelas sem isso viraria migração à mão.

**Backup.** Aceito, com um ajuste de local: o backup diário vai para `dados/backups/`, não para a pasta de saída sincronizada com o Drive, porque o banco contém dado pessoal de terceiros e a pasta sincronizada é o canal do menu, não do banco.

**URLs do Google Alerts identificam a conta.** Aceito; vão para `config/local.yaml`, fora do git, e `fontes.yaml` inteiro fica fora do git com um `fontes.exemplo.yaml` versionado.

**"Conversável" não deve ser meta de aceite rígida da Etapa 1.** Aceito. O aproveitamento sai da lista de critérios e vira indicador acompanhado desde o primeiro dia, com a calibragem contínua feita pelo balanço semanal da Etapa 2. Os exemplos positivos e negativos e o botão "não serve" continuam onde estavam.

**Dependência de feeds RSS.** Já estava na tabela de riscos; a revisão só confirma. Nada a mudar além de manter adaptadores por fonte e o alerta de feed vazio.

### Aceitas com ajuste

**Orçamento de memória em 8 GB justo demais.** A crítica está certa, e a resposta foi mudar o alvo, não a conta: a Etapa 1 passa a rodar no MacBook Air M3 de 16 GB, onde os dois modelos ficam carregados juntos e o ciclo cai para 10 a 15 minutos. O perfil de 8 GB continua descrito, com as ressalvas da revisão (fases separadas com `keep_alive: 0`, 3 a 10 tokens por segundo, medir numa máquina de 8 GB de verdade), como perfil de distribuição futura — não como promessa desta proposta.

**Velocidade de 5 a 10 tokens por segundo otimista para notebook antigo.** Correto para CPU sem GPU; no Air com Metal o número é outro (25 a 40) e a promessa de tempo foi refeita para essa máquina. A ressalva ficou registrada no perfil de 8 GB.

**Pseudonimização: verificar nomes de empresas pequenas e combinações raras de cargo e setor.** Aceito o objetivo, mudado o método. Verificar "combinação rara" por teste é frágil, porque exige saber o que é raro. A solução é por construção: nome de empresa nunca sai, em nenhuma hipótese; cargo e setor vêm de listas fechadas grosseiras (cerca de 20 cargos, seções do CNAE), o que elimina a granularidade que permitiria identificar alguém. O teste automático varre nomes de empresa de todas as fichas e recusa qualquer cargo ou setor fora das listas.

### Rejeitadas, com justificativa

**Marcar a variante "tarefa agendada do Cowork com conector do Drive" como "a verificar".** Rejeitada porque foi verificada: na data desta proposta o conector do Google Drive no Claude cria e atualiza arquivos, e as tarefas agendadas do Cowork rodam com os conectores da conta. O que foi aceito da crítica é a nota de nomenclatura — os nomes de produto mudam, a capacidade não — e ela está na seção 8.6.

**Trocar `bge-m3` por `e5-small` por causa da memória.** A versão 1 fazia isso para caber em 8 GB. Com o alvo no Air de 16 GB, a razão desaparece, e `bge-m3` é melhor em português, dispensa prefixos e evita uma migração de embeddings na Etapa 2. Fica `bge-m3` desde a Etapa 1.

### Confirmado como certo pela revisão e mantido

Os dois contratos com JSON validado; `origem` em `perfil_tema`; `sem_assunto` com motivo; protocolo de promoção por medida; teste de pseudonimização que recusa o pacote; `fato` só inserção; modo de raciocínio desligado como regra; a instrução fixa aos assistentes, em especial "nunca tente identificar o contato" e "sem URL, não inclua".

Nenhuma das mudanças altera etapas, prazos ou custo. O que mudou de fato foi a máquina-alvo da Etapa 1 e, com ela, o tempo de ciclo — para menos.
