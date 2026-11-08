> **OBSOLETO.** Versão intermediária (12/09): já tinha cortado a redação de mensagem, mas ainda oferecia nuvem (ChatGPT/Gemini/Claude) como opção e mirava um notebook comum de 8 GB. Ambas as escolhas foram substituídas — o projeto é 100% local, na máquina de produção real (Mac 48 GB) — no plano atual em `docs/PLANO.md`, `docs/ARQUITETURA.md` e `docs/PLAN.md`. Mantido só como referência histórica do desenho do motor de relevância do coletor.

# Coletor de Assuntos — Plano Executável

**O que mudou em relação à versão anterior:** saiu toda a camada de redação de mensagem, tom, cadência e aprovação de envio. O sistema não escreve para ninguém e não presume relação nenhuma. Ele coleta, separa o que é assunto do que é ruído, agrupa, resume e entrega. Quem decide se usa, com quem e como, é você.

**Máquina de referência:** notebook de 8 GB de RAM, Core i3/i5 ou Ryzen 3/5, gráficos integrados, SSD, Windows 11.

**Consequência técnica da mudança de escopo, e ela é grande:** escrever mensagem com tom era a única tarefa que exigia modelo grande. Classificar, agrupar e resumir são tarefas de saída curta e estruturada — um modelo de 4B faz bem, e um de 1.7B faz de forma aceitável. Com isso, **a versão local deixa de ser o plano de longo prazo e passa a ser o destino natural**, rodando num notebook comum.

---

## 1. O que o sistema faz

Todo dia de madrugada ele lê as suas fontes, joga fora o que é repetição, publicidade e barulho, e junta o que sobrou em **assuntos** — não em notícias soltas. Cinco matérias sobre a mesma coisa viram um assunto só.

Cada assunto chega assim:

> **Crédito consignado para autônomos entra em vigor**
> *O que aconteceu:* a regra passou a valer em 1º de setembro. Três bancos já publicaram taxas. A adesão na primeira semana ficou abaixo do projetado.
> *Por que é assunto:* mexe com quem é autônomo ou emprega autônomo, e ainda está em aberto — dá conversa por mais duas ou três semanas.
> *Quando:* 01/09, atualizado em 10/09 · *Fontes:* 4 independentes · *Temperatura:* quente
> *Cruza com:* previdência, mercado de trabalho, crédito
> *Ainda não confirmado:* o número de adesão saiu de estimativa de consultoria, não de dado oficial.
> `[ ] usar` · `[ ] não usar` · `[ ] quero o resumo completo`

Você passa o olho na lista, marca. Marcar "quero o resumo completo" gera, na rodada seguinte, o **resumo do assunto**: linha do tempo, números com fonte, quem disse o quê, o que está em disputa e o que ainda vai acontecer. Marcar "não usar" ensina o filtro.

**O que o sistema não faz, por decisão de projeto:** não escreve mensagem, não sugere abordagem, não diz para quem falar, não pontua relacionamento, não mede há quanto tempo você não fala com alguém. Ele não tem como saber nada disso, e fingir que sabe é o que produz sugestão ridícula.

**Tempo humano: 5 minutos por dia** para marcar a lista, mais a leitura dos resumos que você mesmo pediu.

---

## 2. Arquitetura

```
┌────────────────────────────────────────────────────────────────────┐
│ 1. TEMAS                                                            │
│    Lista de temas de interesse, em texto livre, uma linha cada      │
│    Opcional: etiquetas de pessoa, usadas só como interesse          │
│    Arquivo: temas.yaml                                              │
└─────────────────────────────┬──────────────────────────────────────┘
                              ▼
┌────────────────────────────────────────────────────────────────────┐
│ 2. COLETA (diária)                                                  │
│    feedparser ──► 40 a 80 feeds RSS · Google Alerts · Google News   │
└─────────────────────────────┬──────────────────────────────────────┘
                              ▼
┌────────────────────────────────────────────────────────────────────┐
│ 3. NORMALIZAÇÃO                                                     │
│    trafilatura ──► texto limpo · URL canônica · hash de título      │
│    embedding multilingual-e5-small (384d) ──► sqlite-vec           │
└─────────────────────────────┬──────────────────────────────────────┘
                              ▼
┌────────────────────────────────────────────────────────────────────┐
│ 4. AGRUPAMENTO EM ASSUNTO                                           │
│    cluster por similaridade em janela de 7 dias                     │
│    n itens ──► 1 assunto, com contagem de fontes independentes      │
└─────────────────────────────┬──────────────────────────────────────┘
                              ▼
┌────────────────────────────────────────────────────────────────────┐
│ 5. SELEÇÃO — o que é BOM assunto (seção 5)                          │
│    densidade · durabilidade · conversabilidade · aderência · não-óbvio │
└─────────────────────────────┬──────────────────────────────────────┘
                              ▼
┌────────────────────────────────────────────────────────────────────┐
│ 6. RESUMO — dois níveis                                             │
│    a) cartão do assunto: 3 linhas, gerado para todos os aprovados   │
│    b) resumo completo: só para os que você marcar                   │
└─────────────────────────────┬──────────────────────────────────────┘
                              ▼
┌────────────────────────────────────────────────────────────────────┐
│ 7. ENTREGA E ESCOLHA                                                │
│    assuntos_AAAA-MM-DD.md com caixas de marcação                    │
│    sua marcação volta como sinal de calibração                      │
└────────────────────────────────────────────────────────────────────┘
```

| Bloco | Ferramenta | Motivo |
|---|---|---|
| Temas | arquivo YAML | você edita em 30 segundos, sem interface |
| Coleta | `feedparser` + RSS | público e autorizado; nada de raspagem com login |
| Extração | `trafilatura` | separa corpo de menu, anúncio e rodapé |
| Vetores | `multilingual-e5-small` (470 MB, CPU) + `sqlite-vec` | 384 dimensões, roda em 8 GB sem GPU |
| Agrupamento | similaridade de cosseno, ligação simples | sem biblioteca de clusterização; 30 linhas de numpy |
| Rótulo e resumo | Qwen3 4B local (ou o modelo da plataforma) | saída curta e estruturada é o forte de modelo pequeno |
| Banco | SQLite | um arquivo; backup é copiar |
| Entrega | Markdown em pasta sincronizada | abre no celular, marca com um toque |

---

## 3. Modelo de dados

### 3.1 `temas.yaml` — a única coisa que você configura

```yaml
temas:
  - id: reforma_tributaria
    descricao: "reforma tributária, split payment, IVA dual, transição 2026-2033"
    peso: 1.0
  - id: credito_pj
    descricao: "crédito para pequena e média empresa, taxas, linhas novas, inadimplência"
    peso: 0.8
  - id: ia_juridica
    descricao: "uso de inteligência artificial em escritório e tribunal, regulação"
    peso: 1.0

etiquetas_de_interesse:      # opcional — usado SÓ para marcar "cruza com"
  - id: logistica
    descricao: "cabotagem, portos, custo de frete"

ignorar:
  - "concurso público"
  - "horóscopo"
  - "lista dos 10"
```

A `descricao` é o que vira embedding. Escreva em frase corrida, com as palavras que apareceriam na matéria — não use palavra-chave solta. Isso é o ajuste de maior efeito no sistema inteiro.

### 3.2 Tabelas

- **`item`** — `id`, `url_canonica`, `titulo`, `texto`, `fonte`, `dominio`, `publicado_em`, `coletado_em`, `hash_titulo`, `embedding`, `assunto_id`.
- **`assunto`** — `id`, `titulo_gerado`, `primeiro_visto`, `ultimo_visto`, `n_itens`, `n_fontes_independentes`, `temperatura` (quente/morno/frio), `nota`, `status` (novo, em_curso, encerrado), `temas` (lista de ids), `resumo_cartao`, `resumo_completo`.
- **`marcacao`** — `assunto_id`, `data`, `escolha` (usar, nao_usar, quero_resumo), `motivo` (opcional, quatro opções fixas).
- **`fonte`** — `dominio`, `nome`, `confiabilidade` (0–10), `tipo` (veículo, blog, oficial, agregador).

Não existe tabela de pessoa, de interação, de cadência nem de mensagem. Saiu do escopo e saiu do banco.

---

## 4. Fontes

| Tipo | Fonte | Acesso | Custo |
|---|---|---|---|
| Busca por termo | Google News RSS — `https://news.google.com/rss/search?q=TERMO&hl=pt-BR&gl=BR&ceid=BR:pt-419` | RSS | grátis |
| Monitoramento nomeado | Google Alerts com entrega em "Feed" | RSS | grátis |
| Negócios | InfoMoney, Brazil Journal, NeoFeed, Startups, Exame | RSS público | grátis |
| Imprensa geral | Valor, Folha, Estadão | RSS de manchete; corpo no paywall | R$ 20–50/mês se quiser o corpo |
| Setorial | blog e newsroom das empresas do setor (`/feed`, `/rss`) | RSS | grátis |
| Vídeo | canal do YouTube — `https://www.youtube.com/feeds/videos.xml?channel_id=ID` | RSS | grátis |
| Texto longo | Substack, Medium, blogs (`/feed`) | RSS | grátis |
| Oficial | Diário Oficial da União (in.gov.br), páginas de órgão reguladores do seu setor | RSS/busca | grátis |
| Empresa | BrasilAPI CNPJ — `https://brasilapi.com.br/api/cnpj/v1/CNPJ` | REST | grátis, ~3 req/min |

**Redes sociais ficam de fora.** LinkedIn, Instagram e X proíbem coleta automatizada nos termos ou cobram caro pela API. Se quiser esse sinal, o caminho é o sininho de notificação e uma varredura manual de dez minutos por semana — e isso não é parte do sistema, é parte da sua rotina.

**Volume:** 40 a 80 feeds. Abaixo de 40 o agrupamento não tem massa para formar assunto com mais de uma fonte, que é justamente o sinal de que algo é assunto de verdade.

---

## 5. O motor — o que separa assunto bom de notícia qualquer

Este é o coração do sistema e é aqui que ele se diferencia de um leitor de RSS. Um bom assunto não é a notícia mais recente nem a mais relevante: é a que **rende conversa**.

### 5.1 Os cinco critérios

| Critério | Peso | Como é medido |
|---|---|---|
| **Densidade** | 0–25 | quantas fontes independentes cobriram o mesmo fato. 1 fonte = 5 · 2 a 3 = 15 · 4+ = 25. Fato coberto por uma fonte só costuma ser nota paga ou erro |
| **Durabilidade** | 0–25 | o assunto ainda estará de pé daqui a sete dias? Mudança de regra, dado estrutural e decisão com efeito futuro pontuam alto; resultado de placar e cotação pontuam zero |
| **Conversabilidade** | 0–20 | dá para falar disso sem ser especialista e sem precisar de contexto de trinta minutos? Julgamento do modelo, com exemplo no prompt |
| **Aderência aos seus temas** | 0–20 | cosseno entre o assunto e as descrições em `temas.yaml`, ponderado pelo `peso` do tema |
| **Não-obviedade** | 0–10 | assunto que está em todo portal grande vale menos: todo mundo já viu. Medido pela contagem de fontes de massa versus fontes especializadas |

**Corte:** ≥65 entra na lista do dia. 50–64 fica guardado e entra no resumo semanal se ganhar densidade. <50 morre.

**Teto:** no máximo 8 assuntos por dia. Se passarem mais, sobe o corte automaticamente. Lista longa é lista não lida.

### 5.2 Por que durabilidade tem o mesmo peso que densidade

Porque o uso é conversa, não informação. Uma notícia de terça-feira que morre na quarta é inútil para quem vai almoçar com alguém na sexta. Um assunto que dura três semanas serve em cinco conversas diferentes. Praticamente nenhum agregador de notícias otimiza para isso — todos otimizam para ineditismo, que é o oposto.

### 5.3 Agrupamento

1. Embedding de cada item novo com `multilingual-e5-small`.
2. Comparação com os centróides dos assuntos abertos dos últimos 7 dias. Cosseno ≥ 0,82 → entra no assunto existente e recalcula o centróide. Caso contrário, abre assunto novo.
3. Assunto sem item novo por 7 dias → `status = encerrado`.
4. Assunto que ganha item novo depois de encerrado → reabre como "volta ao noticiário", que é um sinal forte por si só.

Ligação simples com limiar fixo, não k-means: o número de assuntos do dia é desconhecido e variável, e k-means exige que você o informe de antemão.

### 5.4 Deduplicação

- URL canônica: remover `utm_*`, `fbclid`, `gclid` e âncora; seguir redirecionamento uma vez.
- Hash de título: minúsculas, sem acento, sem stopword, palavras ordenadas → SHA-1. Hash repetido em 30 dias = descarte.
- Similaridade > 0,94 = mesma matéria republicada. Fica a de fonte mais confiável; as outras contam como fonte independente **apenas** se o domínio for diferente e o texto divergir em mais de 30%.

Esse último detalhe é o que impede o sistema de achar que um release distribuído a quinze portais é um assunto denso. Sem ele, o critério de densidade vira uma medida de assessoria de imprensa.

### 5.5 Ruído estrutural, descartado antes de qualquer conta

Corpo com menos de 400 caracteres (teaser), título com padrão de lista ("os 10", "saiba como", "veja o que"), conteúdo marcado como patrocinado, itens com mais de 7 dias na primeira aparição, e qualquer termo em `ignorar`.

### 5.6 Calibração pela sua marcação

Sua marcação é a única nota que importa. Semanalmente:

- Tema cujos assuntos são marcados "não usar" em mais de 70% das vezes tem o `peso` reduzido em 0,2 e aparece no resumo semanal para você decidir se apaga.
- Domínio com mais de 60% de "não usar" perde 2 pontos de confiabilidade.
- Assunto marcado "usar" tem seu vetor somado ao perfil do tema correspondente, com peso 0,1. Em quatro semanas o sistema conhece o seu gosto melhor que o `temas.yaml` original.
- Os motivos de recusa são quatro e fixos: *não me interessa*, *velho*, *raso demais*, *não dá conversa*. Motivo livre não é analisável e por isso não existe.

---

## 6. Os resumos — formatos exatos e prompts prontos

Três saídas, só três. Nenhuma delas fala com terceiros.

### 6.1 Cartão do assunto (gerado para todos os aprovados)

```
PROMPT DE SISTEMA — CARTÃO DO ASSUNTO

Você resume um assunto para leitura rápida, em português do Brasil. Recebe: os
itens agrupados nesse assunto (título, fonte, data, texto), a lista de temas de
interesse do usuário e a contagem de fontes independentes.

Produza exatamente:
TITULO: 6 a 10 palavras, afirmativo, sem ponto final, sem palavra de manchete
  ("bomba", "chocante", "entenda"). Diga o que aconteceu, não que algo aconteceu.
O QUE ACONTECEU: três linhas, uma informação por linha, em ordem de importância.
  Números só com a fonte entre parênteses. Nada de adjetivo de opinião.
POR QUE É ASSUNTO: uma linha. Explique o que está em aberto ou o que muda na
  prática. Se a resposta honesta for "porque é curioso", diga isso.
AINDA NAO CONFIRMADO: uma linha com o que é estimativa, projeção ou versão de uma
  das partes. Se estiver tudo confirmado por fonte primária, escreva "—".

Regras absolutas:
- Nunca copie frase da matéria. Escreva com suas palavras.
- Nunca afirme número que não esteja no texto recebido.
- Se as fontes divergirem, registre a divergência em vez de escolher um lado.
- Não sugira o que fazer com o assunto. Não escreva mensagem. Não mencione pessoas
  do usuário. Sua função termina no resumo.

Saída em JSON: {"titulo", "o_que_aconteceu": [3 strings], "por_que_e_assunto",
"nao_confirmado", "temas_cruzados": [ids]}
```

### 6.2 Resumo completo (só quando você marcar)

```
PROMPT DE SISTEMA — RESUMO COMPLETO DO ASSUNTO

Você produz o resumo aprofundado de um assunto, em português do Brasil, para
alguém que vai conversar sobre isso e não quer passar vergonha. Recebe todos os
itens do assunto, inclusive os das semanas anteriores se o assunto for antigo.

Estrutura exata, com estes títulos:

EM UMA FRASE — o assunto inteiro em uma frase de no máximo 25 palavras.
COMO CHEGOU AQUI — linha do tempo de 3 a 6 marcos, cada um com data e fonte.
OS NUMEROS — até cinco números que importam, cada um com fonte e data. Se um
  número for estimativa, escreva "estimativa" na frente. Se não houver número
  confiável, escreva "sem número confiável até agora" e não invente.
QUEM DIZ O QUE — as posições em disputa, uma linha por lado, identificando quem
  sustenta cada uma. Se não houver disputa, escreva "sem controvérsia relevante".
O QUE AINDA VAI ACONTECER — datas marcadas, decisões pendentes, prazos.
O QUE EU PRECISARIA SABER PARA NAO FALAR BOBAGEM — até três pontos: o mal-entendido
  comum, o dado que parece dizer uma coisa e diz outra, o detalhe técnico que muda
  a conclusão.
FONTES — lista de 3 a 6 links, os mais primários primeiro.

Máximo 500 palavras, fora as fontes. Sem introdução, sem conclusão, sem opinião
sobre o mérito. Não sugira uso, não escreva mensagem, não mencione pessoas.
```

A seção "o que eu precisaria saber para não falar bobagem" é a que justifica o sistema existir. Resumo de notícia qualquer um lê no portal; o que não se acha pronto é o contexto que evita o erro na hora da conversa.

### 6.3 Resumo semanal

```
PROMPT DE SISTEMA — RESUMO SEMANAL

Você produz o balanço semanal do coletor, em português do Brasil. Recebe: os
assuntos da semana com nota e status, as marcações do usuário, e os assuntos da
faixa 50-64 que ficaram na espera.

Produza, nesta ordem:

1. OS CINCO ASSUNTOS DA SEMANA — os de maior nota, com título e uma linha cada.
2. O QUE SEGUE VIVO — assuntos de semanas anteriores ainda em curso, com o que
   mudou nesta semana. Uma linha cada.
3. O QUE ESQUENTOU TARDE — assuntos que passaram da faixa de espera para a de
   corte, ou seja, que ganharam densidade depois. Esta seção costuma ser a mais
   útil: é onde está o assunto que os portais já esqueceram e ainda rende conversa.
4. CALIBRAGEM — temas com alta taxa de recusa, fontes que estão entregando ruído,
   e temas sem nenhum assunto na semana (fonte faltando ou descrição mal escrita).
5. NUMEROS DA SEMANA — itens coletados, assuntos formados, assuntos entregues,
   taxa de aproveitamento segundo as suas marcações.

Máximo 350 palavras. Sem introdução. Sem elogio ao usuário. Sem sugestão de uso.
```

---

## 7. Entrega e escolha

O arquivo `assuntos_AAAA-MM-DD.md` cai numa pasta sincronizada, aberta no **Obsidian** (grátis, com app de celular) ou no Google Drive. Cada assunto é um bloco com três caixas:

```markdown
## Crédito consignado para autônomos entra em vigor
**O que aconteceu**
- A regra passou a valer em 1º de setembro (DOU, 30/08).
- Três bancos publicaram taxas entre 1,8% e 2,4% ao mês (InfoMoney, 05/09).
- A adesão na primeira semana ficou abaixo do projetado (consultoria X, 09/09).

**Por que é assunto** — ainda está em aberto: o teto de taxa vai ser revisto em outubro.
**Ainda não confirmado** — o número de adesão é estimativa de consultoria, não é dado oficial.
**Cruza com:** credito_pj, mercado_trabalho · **4 fontes** · **quente** · nota 78

- [ ] usar
- [ ] não usar → motivo: ( ) não me interessa ( ) velho ( ) raso ( ) não dá conversa
- [ ] quero o resumo completo
```

Marcar é trocar `[ ]` por `[x]`. Um script varre o arquivo na execução seguinte, grava as marcações no banco e gera os resumos completos pedidos. Sem servidor, sem aplicativo, sem login — e funciona igual no celular.

**Por que Markdown com caixa de marcação e não uma interface:** interface é a parte mais cara de construir e a primeira a ser abandonada. Um arquivo de texto numa pasta sincronizada abre em qualquer lugar, sobrevive a troca de máquina, é versionável e não depende de nada continuar existindo.

---

## 8. Ciclos

| Rotina | Quando | O que faz | Seu tempo |
|---|---|---|---|
| Coleta e normalização | diário, 05h00 (ou no primeiro login) | lê feeds, extrai texto, deduplica, calcula embeddings | 0 |
| Agrupamento e seleção | diário, encadeado | forma assuntos, pontua, corta em 65, teto de 8 | 0 |
| Cartões | diário, encadeado | gera os cartões e escreve o arquivo do dia | 0 |
| **Leitura e marcação** | quando você abrir | marcar usar / não usar / quero resumo | **5 min** |
| Resumos completos | na execução seguinte | gera só os pedidos | leitura, 3 min cada |
| Resumo semanal | domingo, 18h00 | balanço e calibragem | **10 min** |
| Calibragem | domingo, encadeado | ajusta pesos de tema e confiabilidade de fonte | 0 |

**Meta: 5 minutos por dia útil e 10 minutos no domingo.**

---

## 9. As quatro plataformas

### 9.1 ChatGPT Plus — US$ 20/mês

**Faz bem:** tarefa agendada diária, Deep Research para o balanço semanal, projeto com o `temas.yaml` anexado, memória entre conversas.
**Não faz:** agrupamento real. Sem embeddings acessíveis, o que ele chama de "assunto" é julgamento do modelo sobre o que ele acabou de ler — funciona com 15 a 20 termos monitorados e começa a perder consistência acima disso. Também não mantém histórico de assunto entre execuções: cada rodada esquece que o assunto já existia ontem, a menos que você mantenha o histórico numa planilha lida pelo conector.

**Montagem:** projeto com `temas.yaml` e `prompts.md` anexados, conector do Drive ligado numa planilha `Assuntos` (colunas: id, titulo, primeiro_visto, ultimo_visto, n_fontes, status), e uma tarefa agendada.

```
TAREFA AGENDADA — diária, 06h00

Pesquise as novidades das últimas 24 horas sobre os temas do arquivo temas.yaml.
Antes de tudo, leia a planilha Assuntos no Drive: assuntos com status em_curso
continuam existindo, não abra assunto novo para o mesmo fato.

Agrupe o que encontrou em assuntos, não em notícias: fatos sobre a mesma coisa
viram um assunto só, com a contagem de fontes independentes.

Pontue cada assunto de 0 a 100 pelos critérios do prompts.md seção 5: densidade
(25), durabilidade (25), conversabilidade (20), aderência aos meus temas (20),
não-obviedade (10). Entregue só os de nota 65 ou mais, no máximo 8.

Para cada um, gere o CARTÃO DO ASSUNTO no formato exato do prompts.md, com as
caixas de marcação ao final.

Não escreva mensagem para ninguém. Não sugira o que fazer com o assunto. Não
mencione pessoas. Se nada passar de 65, responda apenas "nada hoje" — não baixe
o critério para preencher a lista.
```

### 9.2 Google AI Pro — R$ 96,99/mês

**Faz bem:** lê e escreve na sua planilha sem conector nenhum, o que resolve o problema de memória entre execuções que trava a solução anterior. Ações agendadas nativas. Deep Research no balanço semanal.
**Não faz:** também não tem agrupamento vetorial, e o teto de 10 ações agendadas ativas limita o desenho a uma diária e uma semanal. Respostas de ação agendada são preparadas com antecedência, então o assunto da madrugada chega com algumas horas de atraso — irrelevante para um coletor de assuntos, que não é uma sala de notícias.

**Montagem:** planilha `Assuntos` no Drive, um Gem "Coletor" com as instruções acima adaptadas, ações agendadas diária e semanal, e um Apps Script de 20 linhas que grava as suas marcações de volta na planilha.

### 9.3 Claude Pro — US$ 20/mês (US$ 17 no anual)

**Faz bem:** a tarefa agendada do Cowork devolve **arquivo**, que é exatamente o formato de entrega desta seção 7 — o `assuntos_AAAA-MM-DD.md` nasce pronto, com as caixas de marcação, e a rodada seguinte lê o arquivo do dia anterior para saber o que você marcou. Isso fecha o ciclo de calibragem sem planilha e sem script.
**Não faz:** agrupamento vetorial, pela mesma razão das outras duas. E os limites de uso do Pro pesam se você rodar a coleta mais de uma vez por dia.

**Montagem:** projeto com `temas.yaml` e `prompts.md`, conector do Drive, e duas tarefas agendadas no Cowork — a diária, que lê as marcações do arquivo anterior antes de montar o novo, e a de domingo com o balanço.

### 9.4 Offline, no notebook comum — R$ 0/mês

Com a redação fora do escopo, **esta passa a ser a solução completa**, e não mais a versão avançada. Todas as tarefas que sobraram — classificar, agrupar, rotular, resumir em formato fixo — são de saída curta e estruturada, que é onde modelo pequeno se sai bem.

**Modelo por faixa de máquina:**

| RAM | Modelo | Disco | Contexto | Resultado |
|---|---|---|---|---|
| 4 GB | `qwen3:1.7b` Q4_K_M | ~1,1 GB | 2048 | cartão do assunto sai bem; resumo completo sai raso |
| **8 GB (padrão)** | **`qwen3:4b` Q4_K_M** | **~2,5 GB** | **4096** | cartão e resumo completo em qualidade de uso |
| 16 GB | `qwen3:8b` Q4_K_M | ~5 GB | 8192 | resumo completo com nuance de divergência entre fontes |

Embeddings: `multilingual-e5-small` (470 MB, 384 dimensões) em CPU via `fastembed` — sem CUDA, sem PyTorch.

**Orçamento de memória numa máquina de 8 GB com Windows 11:** sistema 3,0–3,5 GB + pesos 2,5 GB + contexto 0,4 GB + Python, SQLite e índice 0,4 GB = **~6,8 GB**. Cabe, com uma condição: um modelo carregado por vez. A fase de embeddings descarrega (`ollama stop`) antes de o modelo de linguagem subir.

**Orçamento de chamadas ao modelo — é isto que torna a coisa viável:** 800 itens coletados → regras e deduplicação cortam para ~300 → agrupamento forma ~40 assuntos → só os 15 melhores por similaridade vão ao modelo para pontuação e rótulo → 8 cartões são gerados. São 23 chamadas por dia, mais uma ou duas de resumo completo. Não 800.

**Tempo do ciclo, sem placa de vídeo:**

| Etapa | 4 GB / 1.7B | 8 GB / 4B | 16 GB / 8B |
|---|---|---|---|
| Coleta e extração (800 itens) | 6–10 min | 5–8 min | 5 min |
| Embeddings em CPU | 5–7 min | 3–5 min | 3 min |
| Agrupamento (numpy) | <1 min | <1 min | <1 min |
| Pontuação e rótulo (15 assuntos) | 3–5 min | 5–8 min | 8–12 min |
| Cartões (8) | 3–4 min | 5–7 min | 7–10 min |
| **Total** | **~18–26 min** | **~19–29 min** | **~24–31 min** |

Resumo completo, quando pedido: 1 a 3 minutos por assunto.

**Agendamento no Windows** — o ponto em que essas rotinas morrem na prática, porque às 5h o notebook está desligado:

1. Agendador de Tarefas, gatilho diário às 05h00.
2. Marcar **"Executar a tarefa o mais rápido possível após uma inicialização agendada ser perdida"**.
3. Desmarcar "Iniciar somente se estiver ligado na energia" e "Parar se passar a funcionar com bateria".
4. Segundo gatilho: ao fazer logon, com atraso de 5 minutos. O script confere no banco se já rodou hoje e sai sem fazer nada se já rodou.

Você liga o notebook, toma café, o arquivo do dia está pronto. Cada etapa grava progresso no SQLite e é retomável — se a máquina hibernar no meio, a execução seguinte continua de onde parou.

**Instalação (Windows, ~40 minutos):**

```powershell
# 1. Ollama — instalador nativo, em ollama.com/download
ollama pull qwen3:4b          # 8 GB de RAM (padrão)
# ollama pull qwen3:1.7b      # 4 GB de RAM

# 2. Python 3.12
mkdir %USERPROFILE%\coletor && cd %USERPROFILE%\coletor
py -m venv .venv
.venv\Scripts\activate
pip install feedparser trafilatura httpx jinja2 pyyaml numpy sqlite-vec fastembed python-dateutil

# 3. Evita recarregar o modelo do disco a cada chamada
setx OLLAMA_KEEP_ALIVE 30m

# 4. Estrutura
mkdir dados saidas prompts logs
sqlite3 dados\coletor.db < esquema.sql
```

**Parâmetros que importam mais que a escolha do modelo:**

| Parâmetro | Pontuação e rótulo | Resumo |
|---|---|---|
| `temperature` | 0.2 | 0.4 |
| `format` | `json` (obrigatório em modelo pequeno) | livre |
| `num_ctx` | 2048 | 4096 |
| Entrada | título + 800 caracteres de cada item, máximo 4 itens | até 6 itens do assunto |
| Exemplo no prompt | 1 exemplo resolvido | 1 exemplo resolvido |

Um exemplo resolvido dentro do prompt vale mais, num modelo de 4B, do que trocar para um modelo de 8B. É o ajuste de maior retorno nesta faixa de hardware.

---

## 10. A solução combinada, e a recomendação

| Etapa | Onde |
|---|---|
| Coleta, extração, deduplicação | local |
| Embeddings e agrupamento | local |
| Pontuação dos cinco critérios | local |
| Cartão do assunto | local |
| Resumo completo dos assuntos que você marcou | nuvem, se quiser mais profundidade |
| Balanço semanal | local, ou nuvem com Deep Research uma vez por semana |

Como aqui não circula nome de pessoa nenhuma — o sistema lida com notícia pública e com os seus temas —, a divisão é uma escolha de qualidade e de custo, não de privacidade.

### Recomendação

**Duas semanas numa plataforma de nuvem, depois local em definitivo.**

Comece pelo Claude Pro se quiser o arquivo pronto sem montar nada, ou pelo Gemini se a sua vida já está no Google Drive. As duas primeiras semanas não são para ter o sistema funcionando — são para descobrir que metade dos seus feeds é ruim e que as descrições em `temas.yaml` estão mal escritas. Descobrir isso custa quinze minutos por dia numa plataforma de nuvem e custaria uma tarde de reescrita de código se você começasse pelo local.

**Depois disso, vá para o local e fique lá.** O motivo mudou em relação à versão anterior deste plano: não é mais privacidade, é qualidade. Sem agrupamento vetorial, nenhuma das três plataformas de nuvem mantém a identidade de um assunto entre execuções — e o critério de durabilidade, que é o mais valioso dos cinco, depende exatamente disso. Um assunto que dura três semanas só é reconhecível por um sistema que lembra que ele começou há três semanas.

---

## 11. Tabela comparativa

| Critério | ChatGPT Plus | Google AI Pro | Claude Pro | Local |
|---|---|---|---|---|
| Agrupamento em assunto | por julgamento do modelo | por julgamento do modelo | por julgamento do modelo | **vetorial, com centróide persistente** |
| Assunto sobrevive entre dias | com planilha | sim, na planilha | sim, lendo o arquivo anterior | **sim, no banco** |
| Critério de durabilidade | fraco | fraco | médio | **completo** |
| Qualidade do resumo | alta | alta | alta | média a alta, conforme a RAM |
| Termos monitoráveis | ~20 | ~20 | ~25 | centenas |
| Custo mensal | US$ 20 | R$ 96,99 | US$ 20 | R$ 0 |
| Hardware | qualquer navegador | qualquer navegador | qualquer navegador | 8 GB de RAM, sem GPU |
| Montagem | 30 min | 30 min | 35 min | 2 a 3 h |
| Principal limitação | esquece o histórico do assunto | teto de 10 ações agendadas | limites de uso do plano | você mantém o código |

---

## 12. Critérios de aceite

| Métrica | Como medir | 30 dias | 90 dias |
|---|---|---|---|
| Aproveitamento | assuntos marcados "usar" ÷ entregues | ≥ 40% | ≥ 60% |
| Densidade média | fontes independentes por assunto entregue | ≥ 2,5 | ≥ 3 |
| Sobrevivência | assuntos que continuam vivos após 7 dias | ≥ 30% | ≥ 40% |
| Recusa por "velho" | ÷ total de recusas | ≤ 20% | ≤ 10% |
| Recusa por "não dá conversa" | ÷ total de recusas | ≤ 30% | ≤ 15% |
| Tempo humano | cronometrado | ≤ 8 min/dia | ≤ 5 min/dia |
| Cobertura de temas | temas com ao menos 1 assunto por semana | ≥ 70% | ≥ 90% |
| Fato errado no cartão | contagem absoluta | 0 | 0 |

A métrica de recusa por "não dá conversa" é a que mede se o sistema entendeu o produto. Se ela ficar alta, o problema não são as fontes: é o critério de conversabilidade, e o ajuste é o exemplo dentro do prompt.

---

## 13. Modos de falha

| Falha | Como aparece | Controle |
|---|---|---|
| Release disfarçado de assunto denso | o mesmo texto em 12 portais vira "4 fontes independentes" | fonte só conta como independente se o domínio for outro e o texto divergir em mais de 30% |
| Assunto fatiado | a mesma coisa aparece como três assuntos diferentes | limiar de agrupamento em 0,82 com recálculo de centróide; limiar abaixo de 0,78 gera junção indevida, acima de 0,88 gera fatiamento |
| Assunto grudado | dois fatos distintos viram um assunto só | assunto com mais de 12 itens e dispersão interna alta é dividido e volta ao rótulo |
| Número inventado | o cartão traz percentual que não estava na fonte | número sem fonte entre parênteses é removido na renderização, não no prompt |
| Repetição do que morreu | assunto encerrado volta a aparecer | `status = encerrado` após 7 dias sem item novo; reabertura só com item novo, e marcada como "volta ao noticiário" |
| Câmara de eco temática | só assunto de um tema todo dia | teto de 3 assuntos por tema por dia |
| Lista longa demais | 20 assuntos, nenhum lido | teto rígido de 8; excedente sobe o corte automaticamente |
| Fonte que virou lixo | um domínio passa a entregar só ruído | queda automática de confiabilidade a partir das suas recusas |
| Tema mudo | um tema não gera assunto há duas semanas | aparece na calibragem semanal: ou falta fonte, ou a descrição está escrita como palavra-chave em vez de frase |

---

## 14. Implantação em fases

### Fase 1 — funcionando em uma semana
**Escopo:** 8 temas escritos em frase corrida, 20 feeds, cartão do assunto apenas, entrega em arquivo.
**Você faz:** escreve o `temas.yaml` (30 min), escolhe os feeds (40 min), marca a lista todo dia (5 min).
**A máquina faz:** coleta, agrupa, pontua, entrega 8 cartões.
**Conclui quando:** cinco dias seguidos com lista gerada e aproveitamento acima de 30%. Abaixo disso, o problema está nas descrições dos temas — reescreva antes de seguir.

### Fase 2 — resumo completo e calibragem (semanas 2 e 3)
**Escopo:** leitura das suas marcações, geração dos resumos pedidos, ajuste automático de peso de tema e confiabilidade de fonte, balanço semanal.
**Conclui quando:** duas semanas com marcação completa, sem dia em branco. O histórico de marcação é o que treina o filtro; buraco nele atrasa a calibragem em semanas.

### Fase 3 — local (semanas 4 a 6)
**Escopo:** Ollama instalado com o modelo da faixa da sua máquina, embeddings em CPU, agrupamento vetorial com centróide persistente, agendamento com recuperação de execução perdida.
**Conclui quando:** por uma semana, rodando os dois em paralelo, o local e a nuvem concordam em pelo menos 70% dos assuntos entregues — e o local entrega pelo menos dois assuntos de durabilidade alta que a nuvem perdeu, que é justamente o que ele foi feito para pegar.

### Fase 4 — ampliação (semana 7 em diante)
**Escopo:** subir de 20 para 60–80 feeds, de 8 para 20 temas, painel das oito métricas da seção 12.
**Conclui quando:** três meses de série histórica. A partir daí o sistema sabe quais fontes e quais temas rendem assunto de verdade para você, e a lista de feeds passa a ser mantida por ele, não por você.

---

## Duas perguntas (só as que mudam a arquitetura)

1. **Quantos temas você quer monitorar — 8 ou 40?** Até cerca de 20, qualquer plataforma de nuvem dá conta sozinha. Acima disso, o agrupamento vetorial deixa de ser refinamento e vira requisito: sem centróide persistente, o mesmo assunto reaparece todo dia como se fosse novo.

2. **Quanta RAM tem a máquina que vai rodar isso — 4, 8 ou 16 GB?** É a única variável que muda o desenho local. Com 4 GB, o cartão sai local e o resumo completo fica na nuvem. Com 8 GB, tudo roda local.
