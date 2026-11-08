# PLANO.md — agente_nw

> Plano geral: o que o software é, decisões fechadas, etapas e prazos. Não muda a cada commit; muda a cada versão aprovada da proposta.

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Data desta versão:** 2026-09-17 (Proposta comitê v5 / Plano de execução v3)
**Máquina-alvo da Etapa 1:** MacBook Air 2024, chip M3, 16 GB de memória unificada, macOS Sonoma 14.6
**Natureza:** software 100% local. Nenhuma API de modelo de linguagem, paga ou gratuita, em nenhuma etapa. Assinaturas de Gemini, Claude e GPT entram só na Etapa 4, operadas por pessoa (sem API).

---

## 1. O que o software é

O agente_nw dá ao usuário repertório para interações sociais mais interessantes e produtivas, com qualquer contato. Para cada contato, um **menu curto de assuntos do momento**, escolhidos porque casam com as características que o usuário atribuiu a si mesmo e àquele contato, cada assunto com uma linha dizendo por quê.

Três regras valem em todas as etapas:

- **A relevância vem de classificação declarada.** O usuário atribui características (tags) a si e a cada contato; é esse cruzamento que decide relevância. O sistema não adivinha quem é o contato nem qual é a relação.
- **Lógica aditiva.** O agente trabalha com o que tiver — contato só com tags, tags mais sinal social (o sinal soma, nunca condiciona), ou contato sem dado nenhum ("sem assunto para este contato", sem travar).
- **Sinal de rede social é reforço, nunca pré-requisito.** Entra por captura assistida no navegador do usuário, texto ou mídia arrastados, exportação de conversa do WhatsApp (Etapa 2) ou análise em assistente pago (Etapa 4). Nenhuma raspagem em massa: sempre um contato por vez, disparada pelo usuário.

**A regra do conector** (detalhe em `ARQUITETURA.md` seção 5): um assunto só entra no menu se o usuário tiver base para sustentar a conversa. Três faixas — conector (interessa aos dois lados, tema do usuário de nível domínio ou interesse), viável com esforço (só tema de curiosidade ou conversabilidade alta, com preparação anexa) e fora do domínio (não entra no menu). Pontuação e piso são determinísticos; o modelo só escreve o `por_que`.

**A ficha do contato** só coleta campo que muda o menu (temas/tags, cargo/setor/empresa, cidade, línguas, formação, esportes/hobbies, filhos como etapa de vida, faixa etária opcional). Texto livre é minerado pelo modelo; lacunas são indicador, nunca cobrança. A coleta do lado do contato tem três camadas, em valor crescente: **agenda** (semente, antecipada para a Etapa 1, chave de identidade = telefone), **rede social** por captura assistida (Etapa 2, um contato por vez, texto e captura de tela) e **WhatsApp** por exportação de conversa (Etapa 2, processado e apagado localmente, nunca sai da máquina). Fotos e vídeos entram como caminho de entrada com esquema fechado (Etapa 2); áudio não entra.

## 2. O que o software NÃO faz

- Não escreve mensagem, não sugere tom, não propõe como falar com ninguém.
- Não pontua relacionamento, não mede cadência.
- Não envia nada.
- Não usa API de LLM em nenhuma etapa.
- Não faz raspagem em massa nem coleta periódica em rede social — sempre sob demanda, um contato por vez.
- Não faz reconhecimento facial nem descreve traço físico, idade, gênero, raça ou saúde de pessoas em imagem.
- Não usa áudio como entrada.

## 3. Decisões fechadas

| Decisão | Escolha |
|---|---|
| Produto | Menu de assuntos por contato. Não é lista de temas com "interessa a: Maria", não é gerador de mensagem |
| Origem da relevância | Características declaradas pelo usuário para si e para cada contato |
| Tipo conector e nível | Conector exige tema do usuário de nível domínio ou interesse com cosseno ≥ 0,55. Tema de curiosidade rende no máximo viável com esforço. Limiares 0,55 e 0,8 calibrados com 30 linhas reais rotuladas |
| Tabelas por etapa | Esquema comum; cada tabela nasce na migração da etapa que a usa. A migração inicial contém só as tabelas da Etapa 1 |
| Regra do conector | Score = aderência ao contato (peso 50) + aderência ao usuário (peso 30) + conversabilidade (peso 20). Piso: adjacência ≥ 0,55 a algum tema do usuário **ou** conversabilidade ≥ 0,8; sem isso, não entra no menu. Limiares iniciais, calibrados na semana 1 |
| Nível dos temas do usuário | domínio / interesse / curiosidade, só no perfil do usuário. Pesos 1,0 / 0,7 / 0,4 na aderência ao usuário |
| Quem pontua e quem escreve | Pontuação e piso são determinísticos (cossenos e a nota de conversabilidade). O modelo só escreve o `por_que`. Modelo de 4B não decide ordenação |
| Temas | Livres, em linguagem natural. O sistema normaliza e propõe tags novas ao ler texto sobre o contato. A IA classifica; o usuário confirma com um clique |
| Escala | Base dimensionada para 100 contatos. Menu gerado só para contatos ativos ou pedidos na hora |
| Ficha do contato | Campos guiados por finalidade — só entra campo que muda o menu. Texto livre minerado pelo modelo; indicador de lacunas por impacto, sem cobrança |
| Agenda | Semente da base: agenda do macOS local (permissão do sistema) e CSV do Google Contatos. Telefone é a chave de identidade entre fontes. Antecipada para a Etapa 1 |
| Rede social | Reforço opcional. Captura assistida pela extensão do Chrome — um contato por vez, na sessão do usuário, texto e captura de tela (Etapa 2) — mais texto/mídia arrastados e análise via assistente pago (Etapa 4). Sem raspagem em massa. Risco de termos de uso do LinkedIn registrado para decisão do comitê |
| WhatsApp | Só por exportação de conversa; processada localmente; arquivo apagado; banco guarda agregados; nunca sai da máquina; nunca entra em pacote da Etapa 4. Sem API oficial nem não oficial |
| Fotos e vídeos | Caminho de entrada da ficha desde a Etapa 2: modelo de visão local com esquema fechado, OCR nativo do macOS antes do modelo, sem descrever pessoa, sem reconhecimento facial; imagem processada e descartada, fica só o hash. Áudio não é caminho de entrada |
| Modelo de visão | `gemma3:4b` no Air (carregado só quando a fila de mídia roda); `qwen2.5vl:7b` no Pro de 48 GB |
| Hardware da Etapa 1 | MacBook Air 2024, M3, 16 GB, macOS Sonoma 14.6. Aceleração Metal pelo Ollama |
| Modelo da Etapa 1 | `qwen3:4b`, quantização Q4_K_M, via Ollama, modo de raciocínio desligado (`think: false`) |
| Embeddings | `bge-m3` desde a Etapa 1 (1,2 GB; melhor em português; dispensa prefixos). `multilingual-e5-small` só no perfil de 8 GB (distribuição futura) |
| Limiares de similaridade | Valores iniciais (0,82 para agrupar) calibrados na semana 1 com 50 pares rotulados à mão. Tarefa do brief, não constante do código |
| Categorias sensíveis | Duas camadas: regra no prompt do extrator e filtro determinístico depois do modelo (lista de termos), que descarta a tag e registra o descarte. Mesmo filtro no importador da Etapa 4 |
| Esquema e backup | `schema_version` e migrações numeradas desde a semana 1; backup diário do banco em `dados/backups/`, retenção de 7 dias, fora da pasta sincronizada |
| Interface | Console web local (Flask, `localhost:8765`) com três telas, mais exportação do menu em Markdown para pasta sincronizada |
| Roteamento de modelo | Declarado em `config/llm_routing.yaml`, um perfil por faixa de hardware. Evoluir de modelo é trocar o perfil, não o código |
| API de LLM | Nenhuma, em nenhuma etapa |
| Dados de terceiros | Ficam no dispositivo. Saem só em pacote pseudonimizado, por ação do usuário (Etapa 4) |
| Exemplos de "conversável" | A IA escreve o conjunto inicial de exemplos positivos e negativos; o usuário aprova; "não serve" no menu realimenta |
| Nome do pacote Python | `agente_nw`, igual à pasta |
| Origem dos briefs | `docs/briefs/`, fora do git |
| `AGENTS.md` no git | Commitado. É regra de executor, não documento de produto, e não contém dado pessoal |
| Processamento de importações | Em fila, na rodada seguinte, com botão "processar agora" no console |

## 4. Etapas

| Etapa | Semanas | Entrega | Passa quando |
|---|---|---|---|
| **1 — MVP Qwen3 4B** | 1 a 3 | Importação da agenda, ciclo diário, menu por contato, console, exportação Markdown | 5 dias seguidos de ciclo sem intervenção; menu ≥5 contatos ativos com ≥3 assuntos; regra do conector concordando com rótulo humano em ≥10/12; JSON válido ≥95%; ciclo ≤20 min com 10 contatos; zero `assunto_id` inventado; limiar de agrupamento calibrado e backup restaurado em teste; filtro sensível com 100% de acerto em 30 frases. Detalhe: `agente_nw_proposta_comite_v5` seção 5.8 |
| **2 — Evolução de modelo e coleta do contato** | 4 a 6 | Perfis `air16b`/`air16c` (e `pro48`), protocolo de medição, texto e mídia na ficha, modelo de visão, extensão do Chrome, exportação de conversa do WhatsApp, resumo completo, balanço semanal | Perfil candidato concorda ≥85% com `air16` nos 3 primeiros assuntos de 10 contatos e entrega ao menos um assunto durável que o 4B perdeu; um contato real coletado de ponta a ponta pela extensão; captura de tela do Instagram gera ≥3 tags confirmadas; exportação de conversa produz `conversa_tema` e apaga o arquivo; teste do esquema de visão com 20 imagens sem campo fora do esquema e sem descrição de pessoa; balanço semanal ajusta ao menos um peso de tema. Seção 6.6 |
| **3 — Integrações Google e RSS** | 7 | Google Alerts/News, Drive, agenda (iCal), scripts da seção 7 da v5 | Todos os temas com feed do Google News gerado; menu no celular em até 5 min após o ciclo; marcação no celular chega ao banco na rodada seguinte; contato com reunião em 48h recebe menu com prioridade. Seção 7.8 |
| **4 — Ponte com assistentes pagos** | 8 | Exportação pseudonimizada, instrução fixa, importação e validação, capturas de tela por ato do usuário | Ida e volta completa nas três plataformas com 3 contatos; tags importadas e confirmadas; diferença de menu exibida e aceita/recusada; teste de pseudonimização 100%. Seção 8.7 |

Sequência fixa; cada etapa começa com a anterior certificada. As Etapas 3 e 4 são independentes entre si. Total: oito semanas.

## 5. Perfis de hardware

| Perfil | Máquina | Modelo generativo | Embeddings | `num_ctx` (qualificar / cruzar / cartão) |
|---|---|---|---|---|
| `air16` — **Etapa 1** | MacBook Air M3, 16 GB | `qwen3:4b` | `bge-m3` | 2048 / 4096 / 4096 |
| `air16b` | mesma máquina | `qwen2.5:7b` para cartão/resumo; `qwen3:4b` em qualificar/cruzar | `bge-m3` | 4096 / 8192 / 8192 |
| `air16c` | mesma máquina | `qwen3:8b` em tudo | `bge-m3` | 4096 / 8192 / 8192 |
| `pro48` | MacBook Pro, 48 GB | `qwen3:30b-a3b` em qualificar/cruzar; `qwen3:32b` ou `qwen2.5:14b` em cartão/resumo | `bge-m3` | 8192 / 16384 / 16384 |
| `win8` — distribuição futura | notebook 8 GB, sem GPU, Windows | `qwen3:4b` | `multilingual-e5-small` (prefixos `query:`/`passage:`) | 2048 / 4096 / 4096 |

## 6. Governança de documentos

Todo documento (`PLANO.md`, `ARQUITETURA.md`, `PLAN.md`, ADRs, briefs, relatórios, `README.md`) fica na pasta de documentos do projeto e **nunca é commitado** (`.gitignore`), entregue na aba Saídas com caminho próprio e permanente. **Exceção explícita: `AGENTS.md` é commitado** — é regra de executor, não documento de produto, e não contém dado pessoal.

Este projeto trata **dado pessoal de terceiros dentro do repositório**. O `.gitignore` nasce com isto, e a proibição de `git add -A` do `AGENTS.md` deixa de ser estilo e passa a ser o que evita o acidente:

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
fontes.yaml
config/local.yaml
*.csv
```

Versionar `temas.exemplo.yaml` e `fontes.exemplo.yaml`, para o repositório continuar clonável.
