> **OBSOLETO.** Versão original do plano (12/09), com agente de mensageria (redação, cadência, envio), quatro plataformas de nuvem e LGPD. Essa camada de mensageria foi cancelada em definitivo; o projeto atual (100% local, sem redação, sem cadência) está em `docs/PLANO.md`, `docs/ARQUITETURA.md` e `docs/PLAN.md`. Mantido só como referência histórica dos prompts de redação e da análise de LGPD, caso essa função volte a ser considerada.

# Agente de Relacionamento Pessoal e Profissional — Plano Executável

**Jurisdição adotada:** Brasil (LGPD — Lei 13.709/2018). Adotada porque o enunciado veio em português e não houve indicação de outro país. Se o destino for outro, o que muda está isolado na seção 12.

**Data de verificação de preços e recursos das plataformas:** 12 de setembro de 2026.

**Decisões já tomadas neste plano** (nada de "existem várias opções"):

| Bloco | Escolha | Por quê |
|---|---|---|
| Banco de dados | SQLite (arquivo único `relacionamento.db`) + espelho em Google Sheets | Zero servidor, backup é copiar um arquivo, aguenta 10 mil contatos sem esforço |
| Coleta | RSS puro com `feedparser` + Google Alerts (saída RSS) + Google News RSS | Legal, gratuito, sem quebrar termos de uso, sem captcha |
| Extração de texto | `trafilatura` | Melhor taxa de acerto em português entre as bibliotecas livres de extração |
| Busca semântica | Embeddings `bge-m3` rodando no Ollama + `sqlite-vec` | Multilíngue de verdade, roda local, 1024 dimensões, sem custo por chamada |
| Modelo local | Qwen3 14B Q4_K_M (padrão) / Qwen3 8B (máquina fraca) / classe 27–30B MoE (máquina forte) | Licença Apache 2.0, português sólido, obediência a formato de saída |
| Executor local | Ollama (motor) + LM Studio (interface para testar e trocar modelo) | Ollama serve API compatível com OpenAI em `localhost:11434`; LM Studio resolve a parte visual |
| Agendamento | `cron` (Linux/macOS) ou Agendador de Tarefas (Windows), e as tarefas agendadas nativas de cada plataforma paga | Não exige serviço externo nem conta em automatizador |
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
│    embedding bge-m3 (1024d) ──► gravado em sqlite-vec                │
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
│    Modelo: Qwen3 14B local, ou Claude/GPT/Gemini na versão em nuvem  │
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
| Vetores | bge-m3 + sqlite-vec | Embedding multilíngue de qualidade, rodando local, gravado no mesmo arquivo |
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
| `origem_dado` | texto | sim | exigência de LGPD: de onde veio cada informação |
| `notas` | texto | não | **sem dado sensível** — ver seção 12 |
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
2. **Vetorial** (`sqlite-vec` + `bge-m3` no Ollama, ~50 ms por item): reduz 800 itens a 20 candidatos.
3. **LLM** (Qwen3 14B local ou o modelo da plataforma, ~3 s por item): nota final, justificativa em uma linha, e decisão de qual tipo de saída gerar.

Rodar o LLM em 800 itens seria caro e lento sem melhorar o resultado: a passagem vetorial já elimina o óbvio. Rodar só vetorial sem LLM produz sugestões tecnicamente aderentes e conversacionalmente ridículas — é exatamente aí que nascem as mensagens robóticas.

### 5.4 Calibração contínua

Todo descarte grava o motivo em `sugestao.motivo_descarte` com quatro opções: *irrelevante para ele*, *velho*, *tom errado*, *contato recente demais*. Semanalmente, um script recalcula: domínios cuja sugestão foi descartada como irrelevante mais de 60% das vezes perdem 3 pontos de confiabilidade; interesses de contato cujos itens são sempre descartados são marcados para revisão na ficha.

---

## 6. Camada de geração

**Regras válidas para toda saída:** português do Brasil; sem emoji salvo se a ficha do contato marcar `nivel_intimidade = próximo`; sem "espero que esteja tudo bem"; sem elogio genérico; nunca inventar fato sobre a pessoa; nunca dizer "vi que você" sobre algo que não está na fonte citada; se o fato não estiver no item coletado, não entra na mensagem.

**Critério de qualidade (o gerador verifica antes de entregar):** (a) a mensagem passaria por escrita por um humano ocupado? (b) tem no máximo uma pergunta? (c) o fato citado está no item? (d) cabe em uma tela de celular sem rolar? Reprovou em qualquer uma, regera uma vez; reprovou de novo, o item é descartado em silêncio.

### 6.1 Mensagem de abertura ou retomada

**Formato:** 2 a 3 frases, máximo 400 caracteres, termina em pergunta aberta. Três variações de tom sempre.

```
PROMPT DE SISTEMA — ABERTURA/RETOMADA

Você escreve mensagens curtas de retomada de contato, em português do Brasil, para
aplicativo de mensageria. Você recebe: (1) perfil do remetente, (2) perfil do
destinatário, (3) o gancho (notícia, evento ou marco), (4) dias desde o último
contato e o resumo da última conversa.

Produza exatamente três variações da mesma mensagem, nesta ordem:
- FORMAL: trata por você, sem gíria, sem contração informal, sem emoji.
- CORDIAL: caloroso, frases curtas, pode usar o primeiro nome no vocativo.
- DIRETO: vai ao ponto em duas frases, útil quando a relação é de negócios.

Regras absolutas:
- Máximo 400 caracteres por variação.
- No máximo UMA pergunta, sempre aberta (nunca respondível com sim ou não).
- Cite o gancho em no máximo 12 palavras, sem link e sem jargão de imprensa.
- Se os dias desde o último contato passarem de 90, reconheça o intervalo em no
  máximo cinco palavras ("sumi, mas voltei") e siga adiante. Não peça desculpas.
- Proibido: "espero que esteja tudo bem", "passando para", "tudo joia", elogio
  sem objeto, adjetivo superlativo, emoji (salvo intimidade=próximo).
- Proibido afirmar qualquer fato sobre o destinatário que não esteja no gancho.
- Não venda nada. Esta mensagem abre conversa, não propõe negócio.

Saída em JSON: {"formal": "...", "cordial": "...", "direto": "...",
"gancho_usado": "...", "risco": "baixo|medio|alto"}
O campo risco é alto quando o gancho for notícia negativa sobre a pessoa ou a
empresa dela. Se for alto, as três variações devem ser de apoio, sem pergunta
de negócio.
```

### 6.2 Pergunta aberta que puxa conversa

**Formato:** uma frase, 15 a 30 palavras, sem preâmbulo.

```
PROMPT DE SISTEMA — PERGUNTA DE ENGATE

Você gera uma única pergunta para reaquecer uma conversa com um contato, em
português do Brasil. Recebe o perfil do contato e o histórico resumido.

A pergunta deve:
- pedir opinião ou experiência, nunca informação que se acha no Google;
- estar dentro de um dos interesses declarados do contato;
- ser respondível em uma frase por quem está com pressa;
- ter entre 15 e 30 palavras;
- não conter jargão, não conter duas perguntas, não começar com "você poderia".

Se o contato tiver tema em `evitar_temas` correlato, escolha outro interesse.
Saída em JSON: {"pergunta": "...", "interesse_usado": "..."}
```

### 6.3 Resumo de notícia com sugestão de encaixe

**Formato:** resumo em 3 linhas + como usar na conversa em 1 linha.

```
PROMPT DE SISTEMA — RESUMO COM ENCAIXE

Você resume uma notícia para uso em conversa pessoal, em português do Brasil.

Entregue:
1. RESUMO: três linhas, uma ideia por linha, sem adjetivo de opinião, sem citar
   trecho literal da matéria — escreva com suas palavras.
2. POR QUE INTERESSA A ELE: uma linha, ligando explicitamente ao interesse ou ao
   negócio do contato.
3. COMO ENCAIXAR: uma linha, no formato de fala ("dá para comentar que...").
4. O QUE NÃO DIZER: uma linha, quando a notícia tiver ponto sensível
   (demissão, queda de resultado, processo). Se não houver, escreva "—".

Nunca reproduza frases da matéria. Nunca afirme número que não esteja na fonte.
Se a fonte for de opinião, diga "análise de X" e não trate como fato.
Saída em JSON com as quatro chaves: resumo, por_que, como_encaixar, nao_dizer.
```

### 6.4 Gancho para proposta comercial ou colaboração

**Formato:** contexto (1 frase) + ponte (1 frase) + convite de baixo atrito (1 frase).

```
PROMPT DE SISTEMA — GANCHO COMERCIAL

Você escreve a ponte entre um fato do mundo e uma possibilidade de negócio ou
colaboração, em português do Brasil, para mensageria.

Estrutura obrigatória, três frases:
1. CONTEXTO: o fato observado, sem elogio.
2. PONTE: o que o remetente faz que se conecta a esse fato — em linguagem de
   benefício concreto, sem adjetivo publicitário.
3. CONVITE: proposta de conversa curta e datada ("vinte minutos na semana que
   vem"), nunca "vamos marcar um dia desses".

Regras:
- Máximo 500 caracteres no total.
- Proibido: "solução inovadora", "parceria estratégica", "sinergia",
  "revolucionar", "não é só mais um", percentual inventado, promessa de resultado.
- Proibido enviar isto se o último contato foi há mais de 180 dias sem retomada
  prévia: neste caso devolva {"bloqueado": "retomar relação antes de propor"}.
- Se o tipo de relação for "família" ou "amigo", devolva
  {"bloqueado": "relação não comercial"}.

Saída em JSON: {"contexto": "...", "ponte": "...", "convite": "...",
"mensagem_unica": "..."} onde mensagem_unica é o texto corrido pronto para colar.
```

### 6.5 Briefing de pessoa antes de reunião

**Formato:** meia página, lida em 90 segundos.

```
PROMPT DE SISTEMA — BRIEFING PRÉ-REUNIÃO

Você prepara um briefing de uma página sobre uma pessoa com quem o usuário terá
reunião, em português do Brasil. Recebe a ficha do contato, o histórico de
interações e os itens de notícia dos últimos 60 dias ligados a ela ou à empresa.

Formato exato, nesta ordem, com estes títulos:
QUEM É — duas linhas: cargo, empresa, o que essa pessoa de fato decide.
NOSSA HISTÓRIA — três marcos do histórico, com data, do mais recente ao mais antigo.
O QUE MUDOU DESDE A ÚLTIMA CONVERSA — até três pontos com fonte e data. Se não
houver nada verificado, escreva "nada novo verificado" — nunca preencha por preencher.
PONTOS DE CONEXÃO — o que vocês têm em comum, em tópicos.
TRÊS PERGUNTAS PARA FAZER — abertas, específicas dessa pessoa.
EVITAR — temas marcados na ficha e assuntos sensíveis identificados nas notícias.
PRÓXIMO PASSO SUGERIDO — uma linha.

Cada afirmação factual sobre a pessoa deve trazer a fonte entre parênteses.
Afirmação sem fonte é proibida. Total: máximo 300 palavras.
```

### 6.6 Alerta de oportunidade de contato

**Formato:** cartão de 4 linhas.

```
PROMPT DE SISTEMA — ALERTA DE OPORTUNIDADE

Você identifica e anuncia uma oportunidade de contato por interesse mútuo, em
português do Brasil.

Saída, quatro linhas:
GATILHO: o que aconteceu (uma linha, com data e fonte).
POR QUE AGORA: por que hoje é melhor que daqui a duas semanas (uma linha).
ÂNGULO: o interesse mútuo que justifica a fala (uma linha).
AÇÃO: o que fazer — "mandar mensagem", "ligar", "só observar" (uma linha).

Use "só observar" sempre que o gatilho for negativo, íntimo ou ambíguo. A recusa
em agir é uma resposta legítima e deve aparecer quando for o caso.
Saída em JSON: {"gatilho": "...", "por_que_agora": "...", "angulo": "...",
"acao": "mensagem|ligacao|observar", "urgencia": "hoje|semana|mes"}
```

### 6.7 Resumo semanal priorizado

**Formato:** uma página, cinco blocos.

```
PROMPT DE SISTEMA — RESUMO SEMANAL

Você produz o resumo semanal de relacionamento, em português do Brasil. Recebe:
todas as sugestões da semana com suas notas, o estado da base de contatos
(último contato × cadência ideal) e as interações registradas.

Produza, nesta ordem:

1. AS CINCO MELHORES OPORTUNIDADES — ordenadas por nota. Para cada uma: nome,
   gancho em uma linha, ação sugerida. Nada mais.
2. QUEM ESTÁ SENDO NEGLIGENCIADO — contatos de prioridade A e B com atraso maior
   que 1,5× a cadência. Ordene pelo atraso relativo, não pelo absoluto. Para cada
   um, sugira um motivo de contato que não dependa de notícia.
3. O QUE ACONTECEU COM AS SUGESTÕES DA SEMANA PASSADA — enviadas, respondidas,
   descartadas, com a taxa em porcentagem.
4. PADRÃO OBSERVADO — uma observação honesta sobre o comportamento da semana.
   Se o usuário está falando sempre com o mesmo grupo, diga. Se está ignorando um
   segmento inteiro da base, diga.
5. UMA COISA PARA FAZER NA SEGUNDA — uma única ação, a mais alta em retorno.

Máximo 400 palavras. Sem introdução, sem encerramento motivacional.
```

### 6.8 Parser de cadastro (usado no fluxo de menos de um minuto)

```
PROMPT DE SISTEMA — PARSER DE CONTATO

Você converte texto livre sobre uma pessoa em ficha estruturada. Recebe texto
colado (bio de rede profissional, assinatura de e-mail, anotação de conversa).

Extraia apenas o que estiver no texto. Campo ausente = null. Nunca deduza,
nunca complete com conhecimento geral, nunca infira gênero, idade, origem ou
qualquer característica não escrita.

Proibido extrair, mesmo que esteja no texto: saúde, religião, opinião política,
filiação sindical, vida sexual, origem racial ou étnica, dados de crianças.
Se aparecer, ignore em silêncio.

Saída em JSON: {"nome", "apelido_uso", "cargo", "empresa", "area_atuacao",
"interesses": [], "pontos_conexao": [], "fatos_datados": [{"data","fato"}],
"telefone_e164", "email", "origem_dado", "campos_faltantes": []}

Em campos_faltantes, liste os campos obrigatórios que o usuário ainda precisa
informar: tipo_relacao, nivel_intimidade, cadencia_dias, prioridade.
```

---

## 7. Entrega e aprovação

### 7.1 Como o conteúdo chega até você

Um arquivo `pauta_AAAA-MM-DD.md` numa pasta sincronizada, aberta no **Obsidian** (grátis) ou no Google Drive. Cada sugestão é um bloco com as três variações de tom e um link de envio. No celular, o mesmo arquivo abre no app do Obsidian ou do Drive e os links funcionam com um toque.

### 7.2 Os três níveis de envio

| Nível | Como funciona | Ferramenta | Risco | Quando usar |
|---|---|---|---|---|
| **Manual** | Você lê a pauta e copia o texto | Obsidian / Drive | nenhum | primeiras duas semanas, enquanto calibra |
| **Semiautomático (recomendado)** | Link `wa.me` com o texto já preenchido: abre a conversa certa, com a mensagem escrita; você confere e aperta enviar | link `https://wa.me/5511999998888?text=TEXTO_URLENCODED` — nativo do WhatsApp, sem API, sem custo | nenhum | regime permanente |
| **Automático** | O sistema envia sozinho | API não oficial (Evolution API, Z-API) | **alto** | lembretes para você mesmo; nunca para terceiros |

### 7.3 Recomendação e o motivo técnico dela

**Fique no semiautomático. Permanentemente.** Não é conservadorismo:

- A **API oficial do WhatsApp Business** deixou de ser rota desde 15 de janeiro de 2026, quando a Meta passou a proibir que provedores de IA de propósito geral distribuam assistentes pela plataforma. Fora isso, mensagem iniciada por empresa exige template aprovado e janela de 24 horas, e desde março de 2026 há cobrança por mensagem processada — nada disso serve para uma conversa pessoal.
- As **APIs não oficiais** (que conectam sua conta pessoal) violam os Termos do WhatsApp e o risco real é banimento do seu número — o mesmo número em que estão todos os seus relacionamentos. É um risco assimétrico: ganha-se dez segundos, perde-se a agenda inteira.
- O **link `wa.me`** é um recurso oficial, não tem custo, não tem limite e não tem cadastro. A diferença de esforço entre ele e o envio automático é um toque na tela.

**Quando escalar para o nível seguinte:** só para conteúdo dirigido a você mesmo (resumo semanal no seu próprio número, lembrete de follow-up) ou para e-mail, onde o envio programado é legítimo. Para e-mail, use rascunhos criados via API do Gmail e revisados por você — nunca envio direto.

### 7.4 Registro de volta

Aprovar uma sugestão precisa gravar uma `interacao`. Duas formas, escolha uma:

- **Simples:** o link de envio é, na verdade, um redirecionador local (`http://localhost:8765/enviar/1234`) que grava a interação e só então redireciona para o `wa.me`. Dez linhas de Flask.
- **Mais simples ainda:** ao fim do dia, você marca no arquivo as que enviou trocando `[ ]` por `[x]`, e um script varre o arquivo à meia-noite. Funciona, custa dois minutos por semana e não exige servidor.

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
| Higiene da base (LGPD) | Mensal, dia 1 | `cron` | lista contatos sem interação há 24 meses para decisão | 5 min/mês |

**Meta de tempo humano: 10 minutos por dia útil + 25 minutos no fim de semana.** Se passar disso por duas semanas seguidas, o corte de relevância está baixo demais — suba de 70 para 78 e o volume cai pela metade.

---

## 9. As quatro soluções

### 9.1 Solução A — ChatGPT Plus

**Preço:** US$ 20/mês (verificado na central de ajuda da OpenAI; no Brasil o valor em reais só aparece no checkout).

**O que faz bem:** tarefas agendadas nativas, projetos com arquivos e instruções próprias, memória entre conversas, Deep Research para a varredura semanal, GPTs personalizados para o briefing pré-reunião, conectores para Gmail e Drive.

**O que não faz neste caso de uso:** a tarefa agendada não escreve de volta no seu arquivo de contatos — ela produz uma resposta no chat. O histórico de interações precisa viver fora (Google Sheets via conector, ou um CSV que você reenvia ao projeto a cada duas semanas). Não há embeddings próprios acessíveis, então o corte de relevância é feito por julgamento do modelo, não por vetor — funciona bem até ~80 contatos, degrada acima disso.

**Recursos nativos usados:** Projetos (instruções + arquivos), Memória, Tarefas agendadas, Deep Research, GPTs personalizados, conectores Gmail/Drive.

**O que vem de fora:** Google Sheets (base de contatos e histórico) e Google Alerts (entrega por e-mail, lida pelo conector do Gmail).

**Montagem (40 minutos):**

1. Crie a planilha `Relacionamento` no Google Sheets com três abas: `contatos`, `interacoes`, `descartes`. Cabeçalhos conforme a seção 3.
2. Crie um Projeto chamado "Agente de Relacionamento". Anexe: `perfil_usuario.yaml`, export CSV da aba `contatos`, e um arquivo `prompts.md` com os prompts da seção 6.
3. Cole nas instruções do projeto o texto abaixo.
4. Conecte Gmail e Google Drive nas configurações de conectores.
5. Crie duas tarefas agendadas com os prompts abaixo.

```
INSTRUÇÕES DO PROJETO — ChatGPT

Você é o agente de relacionamento de [NOME]. Perfil dele no arquivo
perfil_usuario.yaml. Base de contatos no arquivo contatos.csv e, quando mais
recente, na planilha "Relacionamento" do Google Drive — a planilha sempre vence
o CSV em caso de divergência.

Como você trabalha:
1. Você decide sozinho o que é relevante. Nunca me devolva lista de notícias para
   eu triar. Nunca pergunte "quer que eu gere a mensagem?" — gere.
2. Pontue cada achado de 0 a 100 usando os pesos do arquivo prompts.md, seção 5.
   Só me mostre o que passar de 70. Máximo 5 por dia, máximo 1 por contato por semana.
3. Para cada achado aprovado, gere a saída no formato do prompts.md correspondente
   ao tipo (abertura, pergunta, resumo com encaixe, gancho comercial, briefing,
   alerta, resumo semanal).
4. Toda mensagem vem em três tons: formal, cordial, direto.
5. Todo fato sobre uma pessoa vem com fonte e data entre parênteses. Sem fonte,
   não escreva o fato.
6. Se o contato estiver marcado opt_out, ele não existe para você.
7. Nunca registre nem repita dado de saúde, religião, opinião política, filiação
   sindical, vida sexual ou origem racial de ninguém, mesmo que apareça na fonte.

Formato de entrega diária: um bloco por contato, com nome, dias desde o último
contato, gancho, as três variações e o link
https://wa.me/[telefone]?text=[texto URL-encoded da variação cordial].
Nada antes do primeiro bloco e nada depois do último.
```

```
TAREFA AGENDADA 1 — diária, 06h00

Pesquise na web as novidades das últimas 24 horas sobre: [liste 10 a 15 termos:
empresas dos contatos A, setores, temas]. Cruze com contatos.csv. Aplique o corte
de relevância das instruções do projeto e entregue a pauta do dia no formato
definido. Se nada passar de 70, responda apenas "Nada relevante hoje" — não baixe
o critério para preencher a pauta.
```

```
TAREFA AGENDADA 2 — domingo, 18h00

Gere o resumo semanal conforme o prompt RESUMO SEMANAL do prompts.md. Para a
seção de negligenciados, calcule a partir da coluna ultimo_contato da planilha
Relacionamento e da cadência de cada um. Use Deep Research para a seção de
oportunidades, cobrindo os setores dos contatos de prioridade A.
```

**Custo mensal:** US$ 20. **Esforço de montagem:** 40 minutos. **Manutenção:** reenviar o CSV ao projeto a cada duas semanas (5 min).

---

### 9.2 Solução B — Google AI Pro (Gemini)

**Preço:** R$ 96,99/mês no Brasil, incluindo 2 TB no Google One.

**O que faz bem:** é a única das três que já mora dentro da sua planilha, do seu e-mail e da sua agenda sem precisar autorizar conector nenhum. Ações agendadas nativas. Deep Research. Gems (assistentes configurados) fazem o papel do GPT personalizado. Para quem vive no Google Workspace, é a de menor atrito.

**O que não faz neste caso de uso:** o teto de **10 ações agendadas ativas** limita o desenho — você terá uma ação diária e uma semanal, não uma por contato. As respostas de ação agendada são preparadas com antecedência, então notícia de última hora chega com atraso de algumas horas. E a ação agendada não grava de volta na planilha: a escrita precisa de Apps Script.

**Recursos nativos usados:** Gems, Ações agendadas, Deep Research, acesso nativo a Sheets/Gmail/Agenda, NotebookLM (para consolidar dossiês de setor), memória entre conversas.

**O que vem de fora:** um Apps Script de 30 linhas na própria planilha, que grava a interação quando você marca a caixa de "enviado" — é o que fecha o ciclo de histórico.

**Montagem (35 minutos):**

1. Crie a planilha `Relacionamento` no Drive (mesma estrutura da solução A).
2. Crie um Gem chamado "Relacionamento" com as instruções abaixo.
3. Ative os conectores de Workspace no Gemini (Gmail, Drive, Agenda).
4. Confirme que "Atividade do Keep" está ligada — sem isso, ações agendadas não funcionam.
5. Crie a ação diária e a semanal com os textos abaixo.
6. Cole o Apps Script na planilha (Extensões → Apps Script) para registrar envios.

```
INSTRUÇÕES DO GEM — "Relacionamento"

Você é o agente de relacionamento de [NOME]. Sua base de dados é a planilha
"Relacionamento" no meu Drive: aba contatos (fichas), aba interacoes (histórico),
aba descartes (aprendizado).

Em toda execução:
1. Leia a aba contatos inteira antes de decidir qualquer coisa.
2. Calcule, para cada contato, os dias desde o último contato registrado na aba
   interacoes, e compare com a coluna cadencia_dias.
3. Você classifica e decide. Nunca devolva lista crua para eu triar.
4. Pontuação 0-100: interesse do contato (40), ligação com meus objetivos (20),
   acionabilidade (15), frescor (10), confiabilidade da fonte (10), janela de
   contato (-20 a +5). Corte em 70.
5. Máximo 5 mensagens por dia, máximo 1 por contato por semana.
6. Toda mensagem em três tons: formal, cordial, direto. Máximo 400 caracteres,
   máximo uma pergunta, sempre aberta.
7. Todo fato sobre pessoa vem com fonte e data. Sem fonte, o fato não entra.
8. Ignore qualquer contato com consentimento = opt_out.
9. Nunca guarde nem mencione saúde, religião, política, sindicato, vida sexual
   ou origem racial de ninguém.
10. Termine sempre com a lista de links wa.me prontos, um por sugestão.
```

```
AÇÃO AGENDADA 1 — todo dia às 6h

Pesquise as novidades das últimas 24h sobre [termos]. Leia a aba contatos da
planilha Relacionamento. Aplique minhas regras do Gem Relacionamento e entregue
a pauta do dia. Se nada passar do corte, diga apenas "nada relevante hoje".
```

```
AÇÃO AGENDADA 2 — todo domingo às 18h

Faça o resumo semanal: cinco melhores oportunidades, quem está negligenciado
(atraso maior que 1,5x a cadência, prioridades A e B), o que aconteceu com as
sugestões da semana passada segundo a aba interacoes, um padrão honesto que você
observou no meu comportamento, e uma única ação para segunda-feira. Máximo 400
palavras.
```

**Custo mensal:** R$ 96,99 (já inclui 2 TB de armazenamento, então o custo marginal é menor se você já paga Google One). **Esforço:** 35 minutos. **Manutenção:** praticamente zero — a planilha é a base e o Gemini a lê direto.

---

### 9.3 Solução C — Claude Pro

**Preço:** US$ 20/mês, ou US$ 17/mês na cobrança anual (US$ 200/ano).

**O que faz bem:** é a única das três em que a rotina agendada **produz arquivos**, não apenas mensagens de chat. As tarefas agendadas do Cowork rodam remotamente — não dependem do seu computador estar ligado — e têm acesso aos conectores, às habilidades e aos arquivos da conta. Na prática, a pauta diária nasce como um `.md` pronto, que é exatamente o formato de entrega da seção 7. Projetos com instruções fixas e memória entre conversas completam o quadro.

**O que não faz neste caso de uso:** não tem planilha própria — a base de contatos precisa estar no Drive (via conector) ou como arquivo do projeto. Os limites de uso do plano Pro são sentidos se você rodar tarefas longas várias vezes ao dia; com uma rotina diária e uma semanal, o Pro é suficiente.

**Recursos nativos usados:** Projetos (instruções + arquivos), memória entre conversas, tarefas agendadas no Cowork, conectores (Google Drive, Gmail, Agenda), criação de arquivos.

**O que vem de fora:** Google Sheets como base de contatos (mesma planilha das outras soluções) e Google Alerts entregando por e-mail.

**Montagem (45 minutos):**

1. Crie a planilha `Relacionamento` no Drive.
2. Crie um Projeto "Agente de Relacionamento" e anexe `perfil_usuario.yaml` e `prompts.md` (os prompts da seção 6, copiados inteiros).
3. Cole as instruções do projeto abaixo.
4. Conecte Google Drive, Gmail e Agenda.
5. No Cowork, crie a tarefa agendada diária e a semanal com os textos abaixo.

```
INSTRUÇÕES DO PROJETO — Claude

Você é o agente de relacionamento de [NOME]. O perfil dele está em
perfil_usuario.yaml. Os formatos de saída estão em prompts.md — siga-os ao pé da
letra, inclusive os limites de caracteres. A base de contatos é a planilha
"Relacionamento" no Google Drive.

Princípios de operação:
1. Você decide o que é relevante. Eu nunca recebo lista para triar; recebo
   material pronto para aprovar ou descartar.
2. Pontuação 0-100 com os pesos da seção 5 do prompts.md. Corte em 70. Teto de 5
   por dia e 1 por contato por semana. Se nada passar, diga isso — não preencha.
3. Toda mensagem sai em três tons (formal, cordial, direto), máximo 400
   caracteres, no máximo uma pergunta aberta.
4. Todo fato sobre uma pessoa vem com fonte e data entre parênteses. Sem fonte
   verificada, o fato não existe.
5. Gancho negativo (demissão, queda, processo) nunca vira proposta comercial:
   vira mensagem de apoio ou "só observar".
6. Contato com consentimento = opt_out não é processado em hipótese alguma.
7. Nunca registre nem repita dado de saúde, religião, opinião política, filiação
   sindical, vida sexual ou origem racial de ninguém.
8. Entrega sempre como arquivo Markdown, um bloco por contato, com o link wa.me
   pronto ao final de cada bloco.
```

```
TAREFA AGENDADA — diária, 06h00

Pesquise na web as novidades das últimas 24 horas sobre [10 a 15 termos]. Leia a
planilha Relacionamento no Drive. Aplique as regras do projeto e escreva o
arquivo pauta_AAAA-MM-DD.md com a pauta do dia, um bloco por contato, cada bloco
com: nome, dias desde o último contato, gancho com fonte e data, as três
variações de tom, e o link wa.me com a variação cordial já codificada na URL.
Salve o arquivo e me avise quantos blocos foram gerados.
```

```
TAREFA AGENDADA — domingo, 18h00

Gere o arquivo semana_AAAA-SS.md seguindo o prompt RESUMO SEMANAL do prompts.md.
Calcule os negligenciados a partir da planilha. Inclua as métricas da semana:
sugestões geradas, aprovadas, descartadas e o motivo mais frequente de descarte.
```

**Custo mensal:** US$ 20 (US$ 17 no anual). **Esforço:** 45 minutos. **Manutenção:** zero; a tarefa lê a planilha a cada execução.

---

### 9.4 Solução D — Offline, com modelo local

**Preço:** R$ 0/mês. Custo é hardware e o seu tempo de montagem.

**O que faz bem:** nenhum perfil de pessoa real sai da sua máquina — e esse é o ponto inteiro, porque a base que você está construindo é um cadastro de terceiros que não pediram para estar nela. É a única das quatro em que o motor de relevância é de verdade (embeddings próprios, pesos ajustáveis, histórico completo), em que não há teto de execuções, e em que o custo não cresce com o volume.

**O que não faz:** não tem interface bonita pronta, não pesquisa a web por conta própria (precisa dos feeds RSS que você definir) e o modelo escreve um pouco pior que os três de nuvem — sobretudo em naturalidade de tom. A diferença é menor do que se imagina em mensagem curta e é irrelevante em briefing estruturado.

**Modelo recomendado:** **Qwen3 14B, quantização Q4_K_M**. Motivo: licença Apache 2.0 sem restrição comercial, português de qualidade real (não é tradução literal do inglês), e obediência confiável a formato de saída em JSON — que é o requisito que quebra a maioria dos modelos pequenos nesta arquitetura. Alternativas por faixa de máquina:

| Máquina | Modelo | Tamanho em disco | Observação |
|---|---|---|---|
| 16 GB RAM, sem GPU dedicada | `qwen3:8b` (Q4_K_M) | ~5 GB | funciona; frases um pouco mais duras |
| 32 GB RAM ou GPU 12–16 GB | `qwen3:14b` (Q4_K_M) | ~9 GB | **padrão recomendado** |
| Mac 32–64 GB ou GPU 24 GB+ | modelo MoE da classe 27–30B (ex.: `qwen3-coder:30b`, `gpt-oss:20b`) | 17–19 GB | melhor redação; confira a tag atual em ollama.com/library |

Embeddings: `bge-m3` (`ollama pull bge-m3`), 1024 dimensões, multilíngue — é o que faz a busca semântica funcionar em português sem tradução.

**Programa que executa:** **Ollama** como motor (expõe API compatível com OpenAI em `http://localhost:11434`, roda como serviço, sem interface) e **LM Studio** como bancada de testes visual para comparar modelos antes de fixar um. O código de produção fala com o Ollama.

**Requisitos de hardware:**

| Nível | Especificação | O que roda | Tempo do ciclo diário |
|---|---|---|---|
| Mínimo | 16 GB RAM, SSD 50 GB livres | qwen3:8b + bge-m3 | 12–20 min |
| Recomendado | 32 GB RAM, Apple Silicon M-series ou GPU 12 GB VRAM | qwen3:14b | 5–8 min |
| Confortável | 32–64 GB RAM com GPU 24 GB VRAM | classe 30B MoE | 3–5 min |

O ciclo roda às 5h da manhã — a duração não te afeta.

**Coleta de notícia mantendo o processamento local:** este é o ponto que confunde. O que sai da sua máquina é apenas a requisição HTTP para buscar feeds RSS públicos — a mesma coisa que o seu navegador faz ao abrir um site. O que **nunca** sai é o perfil das pessoas: o cruzamento entre notícia e contato acontece inteiramente dentro do SQLite e do Ollama. Nenhum nome, telefone ou anotação sobre alguém é enviado a qualquer servidor. Na prática:

1. `feedparser` busca os feeds → só URLs públicas saem.
2. `trafilatura` extrai o texto → local.
3. `bge-m3` no Ollama gera os embeddings do item **e** dos perfis → local.
4. A comparação e a pontuação → local.
5. `qwen3:14b` escreve as mensagens com o perfil no prompt → local.

**Montagem (3 a 4 horas na primeira vez):**

```bash
# 1. Motor local
curl -fsSL https://ollama.com/install.sh | sh        # Linux/macOS
ollama pull qwen3:14b
ollama pull bge-m3

# 2. Ambiente Python
mkdir -p ~/relacionamento && cd ~/relacionamento
python3 -m venv .venv && source .venv/bin/activate
pip install feedparser trafilatura httpx jinja2 pyyaml numpy sqlite-vec python-dateutil

# 3. Estrutura
mkdir -p dados saidas prompts fontes
sqlite3 dados/relacionamento.db < esquema.sql

# 4. Agendamento (crontab -e)
0 5 * * *  cd ~/relacionamento && .venv/bin/python coleta.py   >> logs/coleta.log 2>&1
30 5 * * * cd ~/relacionamento && .venv/bin/python gerar.py    >> logs/gerar.log 2>&1
0 18 * * 0 cd ~/relacionamento && .venv/bin/python semanal.py  >> logs/semanal.log 2>&1
```

No Windows, troque o `cron` pelo Agendador de Tarefas com as mesmas três entradas.

**Custo mensal:** R$ 0. **Esforço:** 3 a 4 horas de montagem, depois 0. **Manutenção:** atualizar o modelo a cada dois ou três meses (`ollama pull`).

---

## 10. Solução E — a combinada

A lógica da divisão é uma só: **dado de pessoa fica na sua máquina; busca e redação vão para a nuvem, sem nome junto.**

| Papel | Onde fica | Por quê |
|---|---|---|
| Cadastro e base de contatos | SQLite local + espelho de leitura no Sheets | a base é de terceiros; ela não deve morar em servidor de ninguém |
| Coleta de notícia | local, RSS via `feedparser` | público, gratuito, sem limite, sem login |
| Deduplicação e embeddings | local, `bge-m3` + `sqlite-vec` | o embedding do perfil revela o perfil; não sai |
| Primeiro corte de relevância | local, regras + vetorial | elimina 97% do volume sem chamar nuvem nenhuma |
| Julgamento fino e redação | Claude Pro (tarefa agendada do Cowork) | escreve melhor em formato longo e obedece a restrição de formato com consistência; a tarefa devolve arquivo pronto |
| Pesquisa profunda semanal | Gemini (Deep Research) ou ChatGPT (Deep Research) | varredura ampla de setor, onde nenhum nome de contato precisa aparecer |
| Consulta pelo celular | Google Sheets (só leitura, sem notas sensíveis) | ver a ficha de alguém antes de entrar na sala |
| Entrega | arquivo `.md` local + links `wa.me` | seção 7 |

**A regra de pseudonimização, que é o que torna isso defensável:** quando um item vai para a nuvem para virar mensagem, ele vai assim — *"contato P-014: diretor comercial, setor de logística, interesses: cabotagem, ESG; relação cordial, 41 dias sem contato; gancho: [notícia]"*. Sem nome, sem telefone, sem empresa quando a empresa for pequena o bastante para identificar a pessoa. O nome só é reinserido na sua máquina, na hora de renderizar a pauta. Isso é uma substituição de dez linhas de código e muda a natureza do tratamento de dados.

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
| Qualidade da redação | alta | alta | alta | média-alta | alta |
| Privacidade dos perfis | perfis na nuvem | perfis na nuvem | perfis na nuvem | **tudo local** | identificação local, redação pseudonimizada |
| Custo mensal | US$ 20 | R$ 96,99 | US$ 20 (US$ 17 anual) | R$ 0 | US$ 20 + energia |
| Esforço de montagem | 40 min | 35 min | 45 min | 3–4 h | 5–6 h |
| Escala confortável | ~80 contatos | ~80 contatos | ~100 contatos | milhares | milhares |
| Principal limitação | não escreve de volta na base | teto de 10 ações agendadas | sem planilha nativa | não busca a web sozinho; redação um pouco mais dura | exige manter código próprio |

---

## 12. Privacidade e proteção de dados — LGPD (Brasil)

Você está montando um banco de dados sobre pessoas que não pediram para estar nele. Isso é tratamento de dados pessoais de terceiros e a LGPD se aplica integralmente, mesmo sendo uso individual e profissional — a exceção de "uso exclusivamente pessoal e não econômico" (art. 4º, I) **não** cobre quem usa a base para prospecção, negócio ou trabalho.

### Base legal

| Situação | Base legal | Exigência |
|---|---|---|
| Contato profissional com quem você já se relaciona | Legítimo interesse (art. 7º, IX) | expectativa razoável do titular + registro de avaliação (LIA) + finalidade determinada |
| Contato frio, nunca falou com você | Legítimo interesse é frágil aqui | prefira só dado público de contexto profissional, e nada de anotação comportamental |
| Amigo e família | Uso pessoal, fora do escopo econômico | mantenha em base separada; não misture com a base comercial |
| Qualquer dado sensível | Consentimento específico e destacado (art. 11) | **não colete. Ponto.** |

**A LIA (avaliação de legítimo interesse) é um documento de uma página** que você escreve uma vez: qual a finalidade, por que é legítima, por que o titular esperaria isso, e qual a medida que protege o direito dele. Guarde junto com o projeto. Se um dia alguém reclamar, é ela que te defende.

### Dados admissíveis

Nome, cargo, empresa, área de atuação, contato profissional, interesses declarados publicamente, pontos de conexão com você, histórico das suas próprias interações, cadência preferida, preferência de canal.

### Dados a evitar (não são sensíveis, mas envenenam a base)

Renda, situação financeira, avaliação de personalidade ("é difícil", "é inseguro"), fofoca de terceiros, informação obtida em conversa confidencial, dados da família da pessoa, foto sem finalidade, qualquer inferência que você não diria na frente dela.

**O teste que resolve 100% dos casos:** se a pessoa pedisse para ver a ficha dela — e ela pode, art. 18, II —, você mostraria sem constrangimento? Se a resposta for não, apague o campo.

### Dado sensível (art. 5º, II) — proibido nesta base

Origem racial ou étnica, convicção religiosa, opinião política, filiação a sindicato ou a organização religiosa/filosófica/política, dado referente a saúde ou vida sexual, dado genético ou biométrico. Os prompts das seções 6.8 e 9 já trazem a instrução de descarte silencioso — mantenha-a em todas as versões.

Dados de crianças e adolescentes (art. 14) exigem consentimento específico de um dos pais: na prática, **não cadastre menores.**

### Retenção e exclusão

| Regra | Prazo | Ação |
|---|---|---|
| Contato sem interação | 24 meses | rotina mensal lista para decisão: manter com justificativa ou excluir |
| Item de notícia | 90 dias | apagar corpo do texto, manter só URL e título |
| Sugestão descartada | 180 dias | manter só a nota e o motivo, apagar o texto gerado |
| Pedido de exclusão do titular | **imediato, até 15 dias** | `DELETE` real, não flag; e inserir o telefone numa blocklist para não recadastrar |

### Contato que não manifestou consentimento

- Nunca use a base para envio em massa. Mensagem em massa é o que transforma legítimo interesse em infração.
- A primeira mensagem a alguém que nunca falou com você deve dizer quem você é e como chegou até ela. Uma frase resolve e é exigência de transparência (art. 6º, VI).
- Se a pessoa pedir para não ser contatada, marque `opt_out` **e apague as anotações comportamentais** — não basta parar de mandar mensagem.
- Se a pessoa perguntar de onde veio o dado, você precisa saber responder. É para isso que existe o campo `origem_dado`, e é por isso que ele é obrigatório.

### Segurança mínima

Disco com criptografia ligada (FileVault, BitLocker ou LUKS); backup do `.db` criptografado; a planilha espelho **sem** a coluna de notas; nenhum compartilhamento de link da planilha com "qualquer pessoa com o link".

---

## 13. Critérios de aceite

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

## 14. Modos de falha e controles

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
| Vazamento de dado | base num serviço de terceiros | Solução E com pseudonimização + disco criptografado + planilha sem notas |
| Constrangimento por anotação | a pessoa vê o que você escreveu sobre ela | o teste da seção 12: só entra na ficha o que você mostraria a ela |

---

## 15. Plano de implantação em fases

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

**Escopo:** migração da base para SQLite local, Ollama instalado, embeddings calculados, motor de relevância híbrido, pseudonimização na chamada de redação.

| Quem | Faz o quê |
|---|---|
| Humano | roda a instalação; compara por uma semana as sugestões do motor local com as da nuvem, lado a lado |
| Máquina | ciclo completo local; nuvem só recebe item pseudonimizado |

**Condição de conclusão:** o motor local concorda com o de nuvem em pelo menos 70% das sugestões de nota alta, e a base de perfis já não existe fora da sua máquina.

### Fase 4 — Métricas de relacionamento (semana 7 em diante)

**Escopo:** painel das sete métricas da seção 13, calibração automática de fontes, revisão de cadências com base em taxa de resposta real.

| Quem | Faz o quê |
|---|---|
| Humano | 15 minutos por mês olhando concentração e cobertura; ajusta prioridades |
| Máquina | recalcula confiabilidade de fontes, sugere mudança de cadência quando a taxa de resposta de um contato indica que a frequência está errada |

**Condição de conclusão:** três meses de série histórica. A partir daí o sistema tem dado suficiente para sugerir cadência melhor que a sua intuição — e esse é o ponto em que ele deixa de ser um gerador de mensagens e passa a ser um sistema de relacionamento.

---

## Três perguntas (só as que mudam a arquitetura)

1. **Quantos contatos entram na base?** Até 80, qualquer uma das três soluções de nuvem basta sozinha. Acima disso, o motor vetorial da Solução D/E deixa de ser refinamento e passa a ser requisito — sem ele, os mesmos nomes se repetem e a cauda longa some.

2. **Qual a máquina disponível?** RAM e GPU definem o modelo local e, com ele, a qualidade da redação offline. Com 16 GB, o desenho muda: o local faz coleta e filtro, e a redação continua na nuvem pseudonimizada, em definitivo.

3. **Você aceita rodar scripts Python na sua máquina, ou o sistema precisa ser inteiramente sem código?** Se for sem código, as fases 3 e 4 saem do plano e o teto de contatos fica em ~80 — não é pior, é outro sistema, e vale saber disso antes de montar.
