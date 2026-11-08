> **OBSOLETO.** Segunda versão do plano de agente de mensageria (12/09), ajustada para notebook comum de 8 GB, ainda com quatro plataformas de nuvem + local + combinada. A camada de redação/cadência/envio foi cancelada em definitivo e o projeto virou 100% local. O projeto atual está em `docs/PLANO.md`, `docs/ARQUITETURA.md` e `docs/PLAN.md`. Mantido só como referência histórica.

# Agente de Relacionamento Pessoal e Profissional — Plano Executável

**Máquina de referência para a versão offline:** notebook de 8 GB de RAM, processador Intel Core i3/i5 ou Ryzen 3/5, gráficos integrados, SSD de 256 GB, Windows 11 — a configuração que domina o parque instalado no Brasil. Tudo que é local neste plano foi dimensionado para essa máquina, não para estação de desenvolvedor.

**Data de verificação de preços e recursos das plataformas:** 12 de setembro de 2026.

**Decisões já tomadas neste plano** (nada de "existem várias opções"):

| Bloco | Escolha | Por quê |
|---|---|---|
| Banco de dados | SQLite (arquivo único `relacionamento.db`) + espelho em Google Sheets | Zero servidor, backup é copiar um arquivo, aguenta 10 mil contatos sem esforço |
| Coleta | RSS puro com `feedparser` + Google Alerts (saída RSS) + Google News RSS | Legal, gratuito, sem quebrar termos de uso, sem captcha |
| Extração de texto | `trafilatura` | Melhor taxa de acerto em português entre as bibliotecas livres de extração |
| Busca semântica | Embeddings `multilingual-e5-small` (≈470 MB, roda em CPU) + `sqlite-vec` | Português nativo, 384 dimensões, cabe em notebook de 8 GB sem placa de vídeo |
| Modelo local | Qwen3 4B Q4_K_M (padrão, 8 GB de RAM) / Qwen3 1.7B (4 GB) / Qwen3 8B (16 GB) | É o maior modelo que roda com folga no notebook comum sem GPU dedicada |
| Executor local | Ollama (motor) + LM Studio (interface para testar e trocar modelo) | Ollama serve API compatível com OpenAI em `localhost:11434`; LM Studio resolve a parte visual |
| Agendamento | Agendador de Tarefas do Windows com recuperação de execução perdida (ou `cron` no Linux/macOS), e as tarefas agendadas nativas de cada plataforma paga | Notebook fica desligado de madrugada; a tarefa precisa rodar quando a máquina liga, não na hora marcada |
| Entrega | Arquivo Markdown + links `wa.me` prontos para clicar | Único caminho de envio que não viola política de mensageria (ver seção 7) |
| Automatizador (quando necessário) | n8n self-hosted (Docker) | Único que roda na sua máquina sem mensalidade e sem enviar seus dados a terceiros |

---

## 1. Visão funcional — como isso funciona na prática

Você tem uma agenda de pessoas. O sistema conhece cada uma delas: o que fazem, o que gostam de conversar, o que vocês têm em comum, quando vocês se falaram pela última vez e de quanto em quanto tempo faz sentido se falar de novo.

Todo dia de manhã, enquanto você dorme, o sistema lê as fontes de notícia que você definiu, joga fora 95% do que leu, e guarda só o que tem dono — isto é, o que interessa a uma pessoa específica da sua lista. Para cada coisa que sobrou, ele já escreve a mensagem pronta, no tom certo para aquela relação.

Quando você acorda, você não recebe uma lista de notícias para ler. Você recebe algo assim:

> **Ricardo Menezes** — 41 dias sem contato (cadência ideal: 30 dias)
> *Gancho:* a empresa dele foi citada na matéria do Valor sobre crédito para o agro.
> *Mensagem pronta (tom cordial):* "Ricardo, tudo bem? Vi a Agrocred citada na matéria do Valor sobre a nova linha de crédito — parabéns pela tração. Fiquei curioso: isso muda o perfil de cliente que vocês atendem?"
> *Enviar:* [abrir conversa no WhatsApp com o texto já colado]
> *Ações:* aprovar · editar · descartar · adiar 7 dias

Você lê, aprova ou descarta. Aprovar abre o WhatsApp com o texto já escrito; você dá uma última olhada e envia. Descartar ensina o sistema (o motivo do descarte vira sinal de calibração).

**Tempo humano: 8 a 12 minutos por dia.** Uma vez por semana, num domingo à noite, chega um resumo diferente: as cinco melhores oportunidades da semana, quem você está negligenciando, e quem tem algo acontecendo (mudança de cargo, aniversário de empresa, lançamento) que merece contato mesmo sem notícia.

**O que o sistema nunca faz:** enviar sozinho. Nenhuma mensagem sai sem o seu clique. A automação vai até a porta; quem bate é você.

---

## 2. Arquitetura

```
┌─────────────────────────────────────────────────────────────────────┐
│ 1. CADASTRO                                                          │
│    Formulário Google (celular) ─┐                                    │
│    Colar bio do LinkedIn ───────┼──► parser LLM ──► ficha estruturada│
│    Comando de texto rápido ─────┘                                    │
│    Ferramenta: Google Forms + script de parsing (1 chamada ao LLM)   │
└──────────────────────────────┬──────────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 2. ARMAZENAMENTO                                                     │
│    SQLite `relacionamento.db` (fonte da verdade)                     │
│    + espelho de leitura em Google Sheets (consulta pelo celular)     │
│    Tabelas: pessoa, empresa, interesse, interacao, item, sugestao    │
└──────────────────────────────┬──────────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 3. COLETA (diária, 05h00)                                            │
│    feedparser ──► 40 a 80 feeds RSS                                  │
│    Google Alerts (saída RSS) ──► termos por contato e por setor      │
│    Google News RSS ──► consultas nomeadas (empresa, pessoa, tema)    │
│    YouTube/Substack/blogs ──► RSS nativo                             │
└──────────────────────────────┬──────────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 4. NORMALIZAÇÃO                                                      │
│    trafilatura extrai o texto limpo ──► título, resumo, data, fonte  │
│    canonicalização de URL ──► hash de título ──► deduplicação        │
│    embedding multilingual-e5-small (384d) ──► sqlite-vec             │
└──────────────────────────────┬──────────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 5. MOTOR DE RELEVÂNCIA (híbrido, 3 passagens)                        │
│    a) regras duras: idioma, data, blocklist, teto por contato        │
│    b) similaridade vetorial item × perfil de cada contato            │
│    c) julgamento do LLM nos 20 melhores: nota 0–100 + justificativa  │
│    Corte: ≥70 vira mensagem · 55–69 vai ao resumo semanal · <55 morre │
└──────────────────────────────┬──────────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 6. GERAÇÃO                                                           │
│    Um prompt de sistema por tipo de saída (seção 6)                  │
│    Modelo: Qwen3 4B local, ou Claude/GPT/Gemini na versão em nuvem   │
│    Saída em JSON ──► renderizada por Jinja2 em Markdown              │
└──────────────────────────────┬──────────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 7. APROVAÇÃO E ENTREGA                                               │
│    `pauta_AAAA-MM-DD.md` numa pasta aberta no Obsidian ou no Drive   │
│    Cada card traz link wa.me com o texto pré-preenchido              │
│    Aprovar = clicar, conferir, enviar. Registro volta para `interacao`│
└─────────────────────────────────────────────────────────────────────┘
```

**Por que cada peça:**

| Bloco | Ferramenta | Motivo da escolha |
|---|---|---|
| Cadastro | Google Forms | Ícone na tela inicial do celular, funciona offline no app, grava direto em planilha |
| Armazenamento | SQLite | Banco relacional completo em um arquivo; roda dentro de Python sem instalar nada |
| Consulta móvel | Google Sheets | Você quer ver a ficha de alguém no elevador, antes da reunião |
| Coleta | feedparser + RSS | RSS é público e autorizado; raspagem de site com login é o que quebra |
| Extração | trafilatura | Tira menu, anúncio e rodapé; entrega o corpo da matéria |
| Vetores | multilingual-e5-small + sqlite-vec | Embedding multilíngue que roda em CPU comum; 384 dimensões deixam o índice três vezes menor |
| Julgamento final | LLM | Similaridade sozinha não sabe se a notícia *dá para conversar*; o modelo sabe |
| Renderização | Jinja2 | Separa o texto gerado do formato da pauta; trocar o layout não mexe no motor |
| Agendamento | cron | Já está no sistema operacional; não é mais um serviço para cair |

---

## 3. Modelo de dados

### 3.1 Perfil do usuário (arquivo `perfil_usuario.yaml`, um só)

| Campo | Tipo | Obrigatório | Exemplo |
|---|---|---|---|
| `nome` | texto | sim | Ana Ribeiro |
| `profissao` | texto | sim | Advogada tributarista |
| `empresa` | texto | não | Ribeiro Advogados |
| `projetos_ativos` | lista | sim | ["produto de compliance fiscal", "expansão para o Sul"] |
| `objetivos_12m` | lista | sim | ["3 clientes de médio porte", "1 parceria de canal"] |
| `temas_dominio` | lista | sim | ["reforma tributária", "split payment", "contencioso ICMS"] |
| `temas_conversa` | lista | sim | ["corrida de rua", "vinho", "história do Brasil"] |
| `estilo_escrita` | texto | sim | "direto, cordial, sem emoji, frases curtas" |
| `assinatura_padrao` | texto | não | "Abraço, Ana" |
| `nao_falar_sobre` | lista | sim | ["política partidária", "religião", "futebol"] |
| `janela_envio` | texto | sim | "seg a sex, 09h–19h" |

### 3.2 Perfil de contato (tabela `pessoa`)

| Campo | Tipo | Obrigatório | Observação |
|---|---|---|---|
| `id` | integer PK | sim | |
| `nome` | texto | sim | |
| `apelido_uso` | texto | não | como você o chama na mensagem |
| `telefone_e164` | texto | não | `5511999998888` — sem isso não há link wa.me |
| `email` | texto | não | |
| `empresa_id` | FK empresa | não | |
| `cargo` | texto | não | |
| `area_atuacao` | texto | sim | |
| `tipo_relacao` | enum | sim | cliente, sócio, parceiro, amigo, família, estratégico |
| `nivel_intimidade` | enum | sim | formal, cordial, próximo |
| `tom_preferido` | enum | sim | formal, cordial, direto |
| `interesses` | lista → tabela `interesse` | sim | máx. 8; usados no embedding |
| `pontos_conexao` | lista | sim | o que liga vocês dois |
| `evitar_temas` | lista | sim | inclusive por respeito, não só por tática |
| `cadencia_dias` | inteiro | sim | 15 / 30 / 60 / 90 / 180 |
| `prioridade` | enum A/B/C | sim | A = cadência sagrada; C = só quando houver gancho forte |
| `canal_preferido` | enum | sim | WhatsApp, e-mail, LinkedIn, telefone |
| `melhor_horario` | texto | não | "manhã" |
| `ultimo_contato` | data | derivado | calculado de `interacao` |
| `consentimento` | enum | sim | `contato_profissional_previo`, `consentimento_explicito`, `opt_out` |
| `origem_dado` | texto | sim | de onde veio cada informação — é o que permite auditar e corrigir a ficha depois |
| `notas` | texto | não | fatos datados e verificáveis; sem juízo de valor e sem o que você não mostraria à própria pessoa |
| `criado_em` / `atualizado_em` | timestamp | sim | |

### 3.3 Demais entidades

- **`empresa`**: `id`, `nome`, `cnpj`, `setor`, `porte`, `site`, `feed_rss`, `termos_monitorados` (lista).
- **`interacao`**: `id`, `pessoa_id`, `data`, `canal`, `direcao` (enviada/recebida), `resumo_1_linha`, `sugestao_id` (se veio do sistema), `resultado` (respondeu / ignorou / reunião marcada).
- **`item`**: `id`, `url_canonica`, `titulo`, `resumo`, `fonte`, `publicado_em`, `coletado_em`, `hash_titulo`, `embedding`.
- **`sugestao`**: `id`, `pessoa_id`, `item_id`, `tipo_saida`, `nota`, `justificativa`, `texto_gerado`, `status` (pendente/aprovada/editada/descartada), `motivo_descarte`.

**Relações:** `pessoa` N:1 `empresa`; `pessoa` 1:N `interacao`; `item` N:N `pessoa` através de `sugestao`. O histórico de interações é a única fonte de `ultimo_contato` — nunca se edita esse campo à mão.

### 3.4 Cadastro em menos de um minuto

Três caminhos, todos medidos:

1. **Colar e soltar (20 segundos).** Copie a bio do LinkedIn ou a assinatura de e-mail da pessoa, cole no agente com o comando `/novo`. O modelo devolve a ficha preenchida em JSON e pergunta só o que faltar: cadência e tipo de relação. Prompt pronto na seção 6.7.
2. **Formulário no celular (45 segundos).** Um Google Forms com seis campos obrigatórios (nome, telefone, empresa, área, tipo de relação, cadência) e um campo livre "o que eu sei dessa pessoa". O texto livre é processado depois pelo mesmo parser.
3. **Atualização por voz (15 segundos).** Depois de um café com alguém, você dita: "Falei com o Ricardo hoje, ele está contratando um diretor comercial e vai para Lisboa em outubro." O parser grava uma `interacao` com a data de hoje e adiciona dois fatos ao perfil.

---

## 4. Fontes de informação

### 4.1 Notícia geral e de negócios

| Fonte | Acesso | Custo | Limite | Se bloquear |
|---|---|---|---|---|
| Google News RSS | `https://news.google.com/rss/search?q=TERMO&hl=pt-BR&gl=BR&ceid=BR:pt-419` | grátis | informal, ~1 req/s | espaçar chamadas em 2s |
| Google Alerts (saída RSS) | criar alerta em `google.com/alerts`, escolher "Feed" na entrega | grátis | ~1000 alertas/conta | usar entrega por e-mail e ler a caixa |
| InfoMoney | RSS público `/feed/` | grátis | — | usar Google News filtrando `site:infomoney.com.br` |
| Brazil Journal / NeoFeed / Startups | RSS público | grátis | — | idem acima |
| Valor Econômico / Folha / Estadão | RSS de manchete público, corpo pago | R$ 20–50/mês | paywall no corpo | use só título + linha fina; **não** contorne paywall |
| Reuters / Bloomberg Línea | RSS público parcial | grátis | — | Google News |

### 4.2 Fontes por empresa e por pessoa

| Fonte | Acesso | Custo | Limite | Se bloquear |
|---|---|---|---|---|
| Blog/newsroom da empresa | RSS (`/feed`, `/rss`, `/blog/feed`) | grátis | — | Google News com `site:` |
| YouTube de canal | `https://www.youtube.com/feeds/videos.xml?channel_id=ID` | grátis | — | — |
| Substack / Medium | `/feed` nativo | grátis | — | — |
| Podcast | RSS do feed público | grátis | — | — |
| **LinkedIn** | **sem coleta automatizada** | — | os Termos proíbem raspagem | **Solução aceita:** ative o sininho ("notificar sobre publicações") nos 30 contatos prioritários e reserve 10 minutos na sexta-feira para uma varredura manual, colando o que interessa no agente. É a única rota que não te expõe a bloqueio de conta. |
| Instagram / X | API paga e restrita | X: a partir de US$ 200/mês no nível Basic | inviável para uso pessoal | mesmo tratamento do LinkedIn: sininho + varredura manual |
| Registro de empresa (CNPJ, sócios, situação) | BrasilAPI `https://brasilapi.com.br/api/cnpj/v1/CNPJ` | grátis | ~3 req/min | CNPJá (freemium) |
| Diário Oficial da União | `in.gov.br` — busca com RSS | grátis | — | leitura manual |

### 4.3 Eventos e encontros

| Fonte | Acesso | Custo | Observação |
|---|---|---|---|
| Sympla | busca por cidade e categoria, leitura de página pública | grátis | 1 varredura semanal basta |
| Eventbrite | API pública com token gratuito | grátis | limite generoso para uso pessoal |
| Agenda de entidades do seu setor (associações, conselhos) | RSS ou página estática | grátis | vale ouro para "gancho de encontro presencial" |

### 4.4 Sinais internos (os mais valiosos e os mais esquecidos)

Seu Gmail e sua agenda dizem mais sobre o estado de um relacionamento do que qualquer notícia. Duas consultas diárias resolvem:

- **Gmail:** busca `from:(dominio-do-contato) newer_than:1d` → detecta que a pessoa te escreveu e você não respondeu.
- **Google Agenda:** eventos das próximas 48h com convidado externo → dispara automaticamente um briefing de pessoa (saída 6.5).

### 4.5 Volume recomendado

40 a 80 feeds. Abaixo de 40 o motor passa fome e começa a sugerir coisa fraca; acima de 120 o custo de processamento sobe sem ganho de precisão mensurável. Regra prática: 1 feed setorial para cada 5 contatos, mais 1 feed específico para cada contato de prioridade A.

---

## 5. Motor de relevância

### 5.1 Sinais e pesos

| Sinal | Peso | Como é medido |
|---|---|---|
| Aderência ao interesse do contato | 0–40 | cosseno entre embedding do item e embedding do perfil de interesses |
| Relação com o negócio ou objetivo do usuário | 0–20 | cosseno com `temas_dominio` + `objetivos_12m` |
| Acionabilidade conversacional | 0–15 | julgamento do LLM: "dá para puxar assunto com isso sem forçar?" |
| Frescor | 0–10 | ≤24h = 10 · ≤72h = 7 · ≤7d = 4 · >7d = 0 |
| Confiabilidade da fonte | 0–10 | nota fixa por domínio, definida uma vez |
| Janela de contato | −20 a +5 | vencida = +5 · dentro da cadência = 0 · contato há menos de 7 dias = −20 |

**Corte:** ≥70 vira mensagem pronta. 55–69 entra no resumo semanal como "talvez". <55 é descartado sem aparecer.

### 5.2 Duplicidade e ruído

- **URL canônica:** remover `utm_*`, `fbclid`, `gclid`, âncora; seguir redirecionamento uma vez.
- **Hash de título:** minúsculas, sem acento, sem stopword, ordenado → SHA-1. Hash igual nos últimos 30 dias = duplicado.
- **Similaridade:** cosseno > 0,92 contra itens dos últimos 14 dias = mesma notícia em outro veículo. Fica o de fonte mais confiável.
- **Ruído estrutural:** descartar itens com menos de 400 caracteres de corpo (são teasers), listas de "as 10 melhores", conteúdo patrocinado marcado, e qualquer item cujo título case com a blocklist do usuário.
- **Teto de saturação:** máximo 1 sugestão por contato por semana, máximo 5 mensagens geradas por dia no total. Se sobrar mais, sobe o corte automaticamente até caber. Isso protege a coisa mais frágil do sistema, que é a sua reputação.

### 5.3 Técnica e ferramenta

Híbrido em três passagens, nesta ordem, porque cada passagem custa mais que a anterior:

1. **Regras** (Python puro, milissegundos): idioma, data, blocklist, teto, contato em `opt_out`.
2. **Vetorial** (`sqlite-vec` + `multilingual-e5-small` em CPU, ~120 ms por item): reduz 800 itens a 20 candidatos.
3. **LLM** (Qwen3 4B local, 20 a 40 s por item em CPU, ou o modelo da plataforma, ~3 s por item): nota final, justificativa em uma linha, e decisão de qual tipo de saída gerar.

Essa ordem é o que torna a versão offline viável em máquina fraca. Sem ela seriam 800 chamadas ao modelo por dia, o que num notebook de 8 GB levaria mais de dez horas. Com ela são 25 chamadas: vinte de pontuação e cinco de redação.

Rodar o LLM em 800 itens seria caro e lento sem melhorar o resultado: a passagem vetorial já elimina o óbvio. Rodar só vetorial sem LLM produz sugestões tecnicamente aderentes e conversacionalmente ridículas — é exatamente aí que nascem as mensagens robóticas.

### 5.4 Calibração contínua

Todo descarte grava o motivo em `sugestao.motivo_descarte` com quatro opções: *irrelevante para ele*, *velho*, *tom errado*, *contato recente demais*. Semanalmente, um script recalcula: domínios cuja sugestão foi descartada como irrelevante mais de 60% das vezes perdem 3 pontos de confiabilidade; interesses de contato cujos itens são sempre descartados são marcados para revisão na ficha.

---

## 6. Camada de geração

**Regras válidas para toda saída:** português do Brasil; sem emoji salvo se a ficha do contato marcar `nivel_intimidade = próximo`; sem "espero que esteja tudo bem"; sem elogio genérico; nunca inventar fato sobre a pessoa; nunca dizer "vi que você" sobre algo que não está na fonte citada; se o fato não estiver no item coletado, não entra na mensagem.

**Critério de qualidade (o gerador verifica antes de entregar):** (a) a mensagem passaria por escrita por um humano ocupado? (b) tem no máximo uma pergunta? (c) o fato citado está no item? (d) cabe em uma tela de celular sem rolar? Reprovou em qualquer uma, regera uma vez; reprovou de novo, o item é descartado em silêncio.

### 6.1 a 6.8 — prompts de sistema

Os oito prompts de sistema desta versão (abertura/retomada, pergunta de engate, resumo com encaixe, gancho comercial, briefing pré-reunião, alerta de oportunidade, resumo semanal e parser de cadastro) são idênticos aos da versão v1 (`agente_relacionamento_plano_2026-09-12.md`, seção 6) — ver aquele arquivo para o texto integral de cada um.

---

## 7. Entrega e aprovação

Idêntica à v1: arquivo `pauta_AAAA-MM-DD.md`, três níveis de envio (manual, semiautomático via `wa.me`, automático — desaconselhado), recomendação de ficar no semiautomático permanentemente. Ver `agente_relacionamento_plano_2026-09-12.md` seção 7 para o texto integral, incluindo o motivo técnico (API oficial do WhatsApp Business fora de rota desde 15/01/2026, risco de banimento nas APIs não oficiais).

---

## 8. Ciclos de operação

| Rotina | Quando | Disparo | O que faz | Tempo humano |
|---|---|---|---|---|
| Coleta e indexação | Diário, 05h00 | `cron` | lê feeds, extrai texto, deduplica, calcula embeddings | 0 |
| Relevância e geração | Diário, 05h30 | `cron` (encadeado) | pontua, corta, gera as mensagens, escreve a pauta | 0 |
| **Revisão da pauta** | Diário, no seu horário | você | aprovar, editar, descartar, enviar | **8–12 min** |
| Briefing pré-reunião | Sob demanda + automático 24h antes | gatilho na Google Agenda | gera briefing de cada convidado externo | 2 min de leitura |
| Varredura manual de redes | Sexta, 10 min | você | sininho do LinkedIn nos contatos A, colar o que interessar | **10 min/semana** |
| Resumo semanal | Domingo, 18h00 | `cron` | oportunidades, negligenciados, métricas, padrão observado | **15 min** |
| Calibração | Domingo, 18h30 | `cron` | recalcula confiabilidade de fontes a partir dos descartes | 0 |
| Higiene da base | Mensal, dia 1 | agendador | lista contatos sem interação há 24 meses para decisão | 5 min/mês |

**Meta de tempo humano: 10 minutos por dia útil + 25 minutos no fim de semana.** Se passar disso por duas semanas seguidas, o corte de relevância está baixo demais — suba de 70 para 78 e o volume cai pela metade.

---

## 9. As quatro plataformas

### 9.1 Solução A — ChatGPT Plus, 9.2 — Google AI Pro, 9.3 — Claude Pro

Idênticas em estrutura à v1 (mesmos preços, montagem, instruções de projeto e tarefas agendadas) — ver `agente_relacionamento_plano_2026-09-12.md` seção 9 para o texto integral.

### 9.4 Solução D — Offline, na máquina que você tem de verdade

**Preço:** R$ 0/mês. **Máquina de referência:** notebook de 8 GB de RAM, Core i3/i5 ou Ryzen 3/5, gráficos integrados, SSD, Windows 11.

#### A decisão que faz isso caber num notebook comum

Um modelo pequeno **filtra muito bem e escreve mal**. Essas duas coisas são independentes, e a arquitetura precisa tratá-las como tarefas diferentes:

| Tarefa | Natureza | Quem faz | Por quê |
|---|---|---|---|
| Cortar 800 itens para 300 | regra | Python puro | milissegundos, zero RAM |
| Cortar 300 para 20 | similaridade | `multilingual-e5-small` em CPU | 384 dimensões, 470 MB, não precisa de GPU |
| Pontuar os 20, extrair fatos, resumir em tópicos | classificação com saída curta e estruturada | Qwen3 4B local | é exatamente o que um 4B acerta: julgamento fechado, resposta de 60 tokens em JSON |
| Escrever a mensagem que vai para uma pessoa real | redação com tom | Qwen3 4B (aceitável) **ou** nuvem pseudonimizada (melhor) | é aqui, e só aqui, que o tamanho do modelo aparece no resultado |

Noventa e sete por cento do trabalho não passa perto do modelo de linguagem. Isso é o que derruba o requisito de hardware — não a escolha do modelo.

#### Modelo por faixa de máquina

| RAM da máquina | Modelo | Disco | Contexto | O que esperar |
|---|---|---|---|---|
| 4 GB (Celeron, i3 antigo, eMMC) | `qwen3:1.7b` Q4_K_M | ~1,1 GB | 2048 | classifica e extrai bem; **não redija com ele** — a redação vai para a nuvem |
| **8 GB (padrão)** | **`qwen3:4b` Q4_K_M** | **~2,5 GB** | **4096** | classifica bem e escreve mensagem curta aceitável, com uma revisão sua |
| 16 GB | `qwen3:8b` Q4_K_M | ~5 GB | 8192 | redação já sai natural na maioria das vezes |
| Qualquer uma acima + GPU de 6–8 GB (GTX 1650, RTX 3050) | o mesmo modelo da faixa | igual | igual | 5 a 10 vezes mais rápido; muda o tempo, não a qualidade |

Embeddings: **`multilingual-e5-small`** (118 milhões de parâmetros, ~470 MB, 384 dimensões), rodando em CPU via `fastembed`. Não use `bge-m3` em máquina de 8 GB: são 1,2 GB residentes e 1024 dimensões que triplicam o índice sem diferença perceptível nesta tarefa.

#### Orçamento de memória — a conta que decide se funciona

Numa máquina de 8 GB com Windows 11:

| Item | RAM |
|---|---|
| Windows 11 parado | 3,0–3,5 GB |
| Pesos do Qwen3 4B Q4_K_M | 2,5 GB |
| Cache de contexto (4096 tokens) | 0,4 GB |
| Python + SQLite + índice vetorial | 0,4 GB |
| **Total** | **~6,8 GB** |

Cabe, com uma condição: **um modelo carregado por vez**. A fase de embeddings termina e descarrega (`ollama stop` ou `OLLAMA_KEEP_ALIVE=0`) antes de o modelo de linguagem subir. E, como o ciclo roda de madrugada ou no login, o navegador não está aberto disputando memória — que é o que de fato derruba esse tipo de rotina em notebook de 8 GB.

#### Tempo do ciclo diário, sem placa de vídeo

| Etapa | 4 GB / 1.7B | 8 GB / 4B | 16 GB / 8B |
|---|---|---|---|
| Coleta RSS + extração (800 itens) | 6–10 min | 5–8 min | 5 min |
| Embeddings de 800 itens em CPU | 5–7 min | 3–5 min | 3 min |
| Pontuação de 20 itens pelo LLM | 4–7 min | 8–12 min | 12–18 min |
| Redação de 5 mensagens em 3 tons | — (vai para nuvem) | 6–10 min | 8–12 min |
| **Total** | **~18–25 min** | **~25–35 min** | **~30–40 min** |

Modelo maior é mais lento, não mais rápido. Como ninguém está esperando na frente da tela às 5h da manhã, meia hora de CPU é irrelevante — o que importa é caber na RAM.

#### Agendamento no Windows (o detalhe que quebra na prática)

Notebook às 5h da manhã está desligado ou dormindo. `cron` no papel, tarefa que nunca roda na vida real. No **Agendador de Tarefas**:

1. Gatilho: diário, 05h00.
2. Em Configurações, marcar **"Executar a tarefa o mais rápido possível após uma inicialização agendada ser perdida"** — é isso que faz o ciclo rodar quando você liga a máquina às 8h.
3. Em Condições, **desmarcar** "Iniciar a tarefa somente se o computador estiver ligado na energia" (senão não roda na bateria) e desmarcar "Parar se o computador passar a funcionar com bateria".
4. Segundo gatilho, de segurança: **ao fazer logon, com atraso de 5 minutos**, com a opção de não repetir se já rodou hoje (o próprio script checa a data do último ciclo no SQLite).
5. Marcar "Executar estando o usuário conectado ou não" e "Executar com privilégios mais altos" apenas se o Ollama estiver instalado como serviço.

Na prática: você liga o notebook, toma café, e a pauta está pronta antes de você abrir o e-mail.

**Retomada:** cada etapa grava o progresso no SQLite. Se a máquina hibernar no meio do lote, a próxima execução continua de onde parou em vez de recomeçar. Isso não é refinamento — em notebook é a diferença entre funcionar e não funcionar.

**Disco mecânico:** se a máquina ainda tiver HD e não SSD, carregar o modelo leva 1 a 2 minutos. Mantenha o modelo residente durante todo o lote com `OLLAMA_KEEP_ALIVE=30m` e não intercale as fases.

#### Instalação (Windows, ~40 minutos)

```powershell
# 1. Ollama — instalador nativo do Windows, baixado em ollama.com/download
ollama pull qwen3:4b          # máquina de 8 GB  (padrão)
# ollama pull qwen3:1.7b      # máquina de 4 GB
# ollama pull qwen3:8b        # máquina de 16 GB

# 2. Python 3.12 (Microsoft Store ou python.org — marque "Add to PATH")
mkdir %USERPROFILE%\relacionamento && cd %USERPROFILE%\relacionamento
py -m venv .venv
.venv\Scripts\activate
pip install feedparser trafilatura httpx jinja2 pyyaml numpy sqlite-vec fastembed python-dateutil

# 3. Evita recarregar o modelo do disco a cada chamada
setx OLLAMA_KEEP_ALIVE 30m

# 4. Banco
mkdir dados saidas prompts fontes logs
sqlite3 dados\relacionamento.db < esquema.sql
```

O `fastembed` baixa o `multilingual-e5-small` sozinho na primeira execução (~470 MB) e roda em CPU, sem CUDA, sem PyTorch — é por isso que ele foi escolhido no lugar do `sentence-transformers`, que arrastaria 2,5 GB de dependência para dentro de um notebook de 8 GB.

No Linux ou macOS, os mesmos comandos com `curl -fsSL https://ollama.com/install.sh | sh`, `python3 -m venv .venv` e `cron` no lugar do Agendador.

#### Parâmetros de geração — isso muda mais o resultado que trocar de modelo

| Parâmetro | Pontuação | Redação | Por quê |
|---|---|---|---|
| `temperature` | 0.2 | 0.7 | classificação precisa ser estável; texto precisa respirar |
| `format` | `json` | livre | em modelo de 4B, o modo JSON do Ollama é obrigatório — sem ele vem texto solto e o parser quebra |
| `num_ctx` | 2048 | 4096 | contexto grande consome RAM que você não tem |
| Entrada por chamada | título + 800 caracteres do corpo | ficha do contato + gancho | mandar a matéria inteira piora o resultado e estoura o contexto |
| Itens por chamada | 1 | 1 | lote não acelera em CPU e derruba a precisão |
| Exemplo no prompt | 1 exemplo resolvido | 1 exemplo resolvido | modelo pequeno precisa de exemplo; modelo grande dispensa. É o ajuste de maior efeito nesta faixa |

#### O que um modelo de 4B não faz bem — dito sem rodeio

Ironia, trocadilho, calibração fina de intimidade e qualquer texto acima de três frases. Ele também tende a repetir a mesma estrutura de frase entre contatos diferentes — o que produz exatamente a mensagem genérica que a seção 13 tenta evitar. Dois controles resolvem: a verificação automática que rejeita mensagem sem termo do perfil daquele contato, e as três variações de tom, que obrigam o modelo a reescrever.

Se a mensagem precisar ser boa de primeira, vá para a Solução E: o filtro inteiro fica na sua máquina e só o item pseudonimizado sobe para a redação. Você fica com o custo de hardware de um notebook comum e a redação de um modelo grande.

**Custo mensal:** R$ 0. **Esforço:** 2 a 3 horas de montagem, depois zero. **Manutenção:** `ollama pull` a cada dois ou três meses.

---

## 10. Solução E — a combinada

A lógica da divisão é uma só: **dado de pessoa fica na sua máquina; busca e redação vão para a nuvem, sem nome junto.**

| Papel | Onde fica | Por quê |
|---|---|---|
| Cadastro e base de contatos | SQLite local + espelho de leitura no Sheets | a base é de terceiros; ela não deve morar em servidor de ninguém |
| Coleta de notícia | local, RSS via `feedparser` | público, gratuito, sem limite, sem login |
| Deduplicação e embeddings | local, `multilingual-e5-small` + `sqlite-vec` | roda em CPU, e o embedding do perfil revela o perfil: não sai da máquina |
| Primeiro corte de relevância | local, regras + vetorial | elimina 97% do volume sem chamar nuvem nenhuma |
| Julgamento fino e redação | Claude Pro (tarefa agendada do Cowork) | um modelo de 4B filtra bem e escreve duro; a redação é justamente a etapa que compensa mandar para fora, porque vai pseudonimizada |
| Pesquisa profunda semanal | Gemini (Deep Research) ou ChatGPT (Deep Research) | varredura ampla de setor, onde nenhum nome de contato precisa aparecer |
| Consulta pelo celular | Google Sheets (só leitura, sem notas sensíveis) | ver a ficha de alguém antes de entrar na sala |
| Entrega | arquivo `.md` local + links `wa.me` | seção 7 |

**A regra de pseudonimização, que é o que torna isso defensável:** quando um item vai para a nuvem para virar mensagem, ele vai assim — *"contato P-014: diretor comercial, setor de logística, interesses: cabotagem, ESG; relação cordial, 41 dias sem contato; gancho: [notícia]"*. Sem nome, sem telefone, sem empresa quando a empresa for pequena o bastante para identificar a pessoa. O nome só é reinserido na sua máquina, na hora de renderizar a pauta. É uma substituição de dez linhas de código, e é o que permite usar a nuvem sem que a sua base de pessoas exista lá.

**O que fica online e o que fica local, em uma frase:** fica online aquilo que seria igual para qualquer usuário do mundo (a notícia, a redação, a pesquisa); fica local tudo que identifica alguém.

### Recomendação única

**Comece na Solução C (Claude Pro) sozinha, por quatro semanas, e migre para a Solução E.**

O motivo de começar pela C e não pela E: montar o local primeiro é o erro clássico — você gasta quatro horas construindo um motor antes de descobrir que a sua cadência ideal é outra, que metade dos seus feeds é ruim e que o tom das mensagens precisa de três ajustes. A versão de nuvem entrega valor no primeiro dia e é o seu laboratório de calibração. Entre as três de nuvem, a C é a escolhida por um motivo específico deste caso de uso: a rotina agendada devolve **arquivo**, e a pauta diária é um artefato que você precisa abrir, marcar e guardar.

**A exceção honesta:** se a sua vida já é Google Workspace — contatos em Sheets, agenda no Google, tudo em português com a equipe dentro do Drive —, comece pela Solução B. Você economiza a montagem de conectores e o atrito diário é menor. A diferença de qualidade de redação entre B e C existe, mas é menor que a diferença de atrito, e atrito é o que mata rotina diária.

O motivo de migrar para a E no segundo mês: a partir de ~60 contatos, o corte de relevância feito por julgamento de modelo, sem vetor, começa a repetir os mesmos nomes e a perder os contatos de cauda longa. E, sobretudo, porque a base de perfis de pessoas reais é a parte do sistema que você não quer hospedada em lugar nenhum quando ela deixar de ser um experimento.

---

## 11. Tabela comparativa

| Critério | A — ChatGPT Plus | B — Google AI Pro | C — Claude Pro | D — Offline | E — Combinada |
|---|---|---|---|---|---|
| Cobertura do objetivo | 85% | 85% | 90% | 100% | 100% |
| Automação real (sem você) | coleta + geração | coleta + geração | coleta + geração + arquivo | ciclo inteiro | ciclo inteiro |
| Motor de relevância | julgamento do modelo | julgamento do modelo | julgamento do modelo | vetorial + regras + LLM | vetorial + regras + LLM |
| Qualidade da redação | alta | alta | alta | média — frases mais duras, 3 frases no máximo | alta |
| Privacidade dos perfis | perfis na nuvem | perfis na nuvem | perfis na nuvem | **tudo local** | identificação local, redação pseudonimizada |
| Custo mensal | US$ 20 | R$ 96,99 | US$ 20 (US$ 17 anual) | R$ 0 | US$ 20 + energia |
| Esforço de montagem | 40 min | 35 min | 45 min | 2–3 h | 4–5 h |
| Escala confortável | ~80 contatos | ~80 contatos | ~100 contatos | milhares | milhares |
| Hardware exigido | qualquer aparelho com navegador | qualquer aparelho com navegador | qualquer aparelho com navegador | **8 GB de RAM, sem GPU** (4 GB com modelo menor) | 8 GB de RAM, sem GPU |
| Ciclo diário da máquina | minutos, na nuvem | minutos, na nuvem | minutos, na nuvem | 25–35 min de CPU, de madrugada | 15–20 min de CPU + nuvem |
| Principal limitação | não escreve de volta na base | teto de 10 ações agendadas | sem planilha nativa | não busca a web sozinho; a redação precisa de uma revisão sua | exige manter código próprio |

---

## 12. Critérios de aceite

| Métrica | Como medir | Meta em 30 dias | Meta em 90 dias |
|---|---|---|---|
| Precisão da relevância | aprovadas ÷ sugeridas | ≥ 50% | ≥ 70% |
| Aproveitamento | enviadas sem edição ÷ aprovadas | ≥ 40% | ≥ 60% |
| Taxa de resposta | respondidas ÷ enviadas | ≥ 30% | ≥ 45% |
| Tempo humano | cronometrado, média diária | ≤ 15 min | ≤ 10 min |
| Cobertura da base | contatos A e B contatados dentro da cadência | ≥ 60% | ≥ 85% |
| Concentração | % das mensagens indo para os 10 mesmos contatos | ≤ 50% | ≤ 35% |
| Falso positivo grave | mensagem com fato errado sobre a pessoa | 0 | 0 |

O último critério é eliminatório e não tem meta de tolerância: uma mensagem com fato inventado sobre alguém custa mais que trinta mensagens certas rendem. Se acontecer uma vez, o sistema volta para revisão manual integral até a causa ser encontrada.

Meça a concentração. É a métrica que ninguém mede e é onde estes sistemas falham na prática: eles amplificam o relacionamento com quem já está perto e continuam ignorando quem está longe — exatamente o problema que se queria resolver.

---

## 13. Modos de falha e controles

| Falha | Como aparece | Controle |
|---|---|---|
| Mensagem robótica | "Espero que esteja tudo bem! Vi que a sua empresa..." | lista de expressões proibidas no prompt + teto de 400 caracteres + exigência de uma pergunta aberta única + as três variações de tom, que obrigam o modelo a repensar a frase três vezes |
| Mensagem genérica | serviria para qualquer pessoa da base | verificação automática: se o texto não contiver nenhum termo dos `interesses` ou `pontos_conexao` daquele contato, é rejeitado antes de chegar a você |
| Informação incorreta | fato inventado ou número errado | toda afirmação exige fonte e data entre parênteses; o renderizador rejeita bloco sem URL de fonte; o corte de 400 caracteres de corpo elimina teasers, que são a maior origem de alucinação por falta de contexto |
| Fato desatualizado | cargo antigo, empresa que a pessoa já deixou | campo `atualizado_em` visível na pauta; acima de 180 dias o briefing abre com "ficha desatualizada, confirmar cargo" |
| Contato em hora ruim | mensagem às 22h de domingo | `janela_envio` no perfil do usuário + `melhor_horario` no contato; a pauta é gerada de madrugada mas os links só aparecem marcados como "enviar agora" dentro da janela |
| Contato cedo demais | três mensagens em duas semanas | peso de janela de contato em −20 + teto rígido de 1 por contato por semana |
| Tom inadequado à relação | linguagem comercial com um amigo | `tipo_relacao` bloqueia tipos de saída: "gancho comercial" é recusado para família e amigo; `nivel_intimidade` define o tom padrão |
| Oportunismo em desgraça | mensagem de negócio sobre notícia ruim | campo `risco` no gerador; risco alto força saída de apoio ou "só observar" |
| Câmara de eco | sempre os mesmos dez contatos | métrica de concentração no resumo semanal + bônus de janela para contato vencido |
| Vazamento de dado | base num serviço de terceiros | Solução E com pseudonimização + disco com criptografia ligada + planilha espelho sem a coluna de notas |
| Constrangimento por anotação | a pessoa vê o que você escreveu sobre ela | regra de esquema: o campo `notas` aceita fato datado com fonte, não opinião sobre a pessoa |

---

## 14. Plano de implantação em fases

### Fase 1 — Resultado visível em uma semana

**Escopo:** 30 contatos (todos os de prioridade A e os B mais importantes), 15 feeds, saídas de abertura e resumo semanal apenas.

| Quem | Faz o quê |
|---|---|
| Humano | preenche `perfil_usuario.yaml` (30 min); cadastra os 30 contatos colando bios (45 min); escolhe 15 feeds (30 min); revisa a pauta todo dia (10 min) |
| Máquina | coleta, pontua, gera três mensagens por dia, entrega a pauta |

**Condição de conclusão:** cinco dias seguidos com pauta gerada e pelo menos 50% das sugestões aprovadas. Se a aprovação ficar abaixo de 30%, o problema é o perfil dos contatos estar raso — volte e detalhe interesses antes de seguir.

### Fase 2 — Automação da entrega (semanas 2 e 3)

**Escopo:** links `wa.me` prontos, registro automático de interação, briefing pré-reunião disparado pela agenda, resumo semanal completo com negligenciados.

| Quem | Faz o quê |
|---|---|
| Humano | aprova e envia; marca descartes com motivo |
| Máquina | monta os links, grava interações, dispara briefings 24h antes de cada reunião com externo |

**Condição de conclusão:** tempo humano abaixo de 12 minutos por dia e histórico de interações completo por duas semanas — sem lacuna, porque é o histórico que sustenta todo o resto.

### Fase 3 — Versão offline (semanas 4 a 6)

**Escopo:** migração da base para SQLite local, Ollama instalado com o modelo que couber na sua máquina, embeddings calculados em CPU, motor de relevância híbrido, pseudonimização na chamada de redação. Nesta fase o local assume o filtro; a redação só desce para a máquina se o teste lado a lado aprovar.

| Quem | Faz o quê |
|---|---|
| Humano | roda a instalação; compara por uma semana as sugestões do motor local com as da nuvem, lado a lado |
| Máquina | ciclo completo local; nuvem só recebe item pseudonimizado |

**Condição de conclusão:** o motor local concorda com o de nuvem em pelo menos 70% das sugestões de nota alta, e a base de perfis já não existe fora da sua máquina.

### Fase 4 — Métricas de relacionamento (semana 7 em diante)

**Escopo:** painel das sete métricas da seção 12, calibração automática de fontes, revisão de cadências com base em taxa de resposta real.

| Quem | Faz o quê |
|---|---|
| Humano | 15 minutos por mês olhando concentração e cobertura; ajusta prioridades |
| Máquina | recalcula confiabilidade de fontes, sugere mudança de cadência quando a taxa de resposta de um contato indica que a frequência está errada |

**Condição de conclusão:** três meses de série histórica. A partir daí o sistema tem dado suficiente para sugerir cadência melhor que a sua intuição — e esse é o ponto em que ele deixa de ser um gerador de mensagens e passa a ser um sistema de relacionamento.

---

## Três perguntas (só as que mudam a arquitetura)

1. **Quantos contatos entram na base?** Até 80, qualquer uma das três soluções de nuvem basta sozinha. Acima disso, o motor vetorial da Solução D/E deixa de ser refinamento e passa a ser requisito — sem ele, os mesmos nomes se repetem e a cauda longa some.

2. **Quanta RAM tem a máquina que vai rodar isso — 4, 8 ou 16 GB?** É a única variável que muda o desenho local. Com 4 GB, o modelo local só classifica e a redação fica na nuvem em definitivo. Com 8 GB, ele classifica e redige o básico. Com 16 GB, a versão offline pura fica de fato utilizável.

3. **Você aceita rodar scripts Python na sua máquina, ou o sistema precisa ser inteiramente sem código?** Se for sem código, as fases 3 e 4 saem do plano e o teto de contatos fica em ~80 — não é pior, é outro sistema, e vale saber disso antes de montar.
