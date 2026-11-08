# Regras da auditoria "texto por inteiro" (brief 079 do agente_nw)

Repositório: `/Users/sidarta48/github/agente_nw` (todos os caminhos são relativos a essa raiz).

## O princípio que está sendo auditado

Quando este projeto **analisa** um texto (notícia, página capturada, mensagem de WhatsApp, comentário
do usuário, histórico, fato, perfil), ele deve analisar o texto **inteiro**. Analisar só uma parte é
violação do princípio, a não ser que o dono do projeto (Sidarta) tenha aprovado a exceção por
escrito. "Analisar" = o texto (ou o que sobrou dele) alimenta uma decisão: prompt de LLM, embedding,
classificador, deduplicação/hash, agrupamento, ranqueamento, filtro.

Você **não aprova nada, não corrige nada e não edita nenhum arquivo do repositório**. Você só lê e
relata. Não rode o programa, não toque `dados/agente.db`, não rode git de escrita.

## As quatro classes de problema

- **T — Truncamento do texto de um item:** `[:N]`, `max_chars`, `textwrap.shorten`, `.slice(0,N)`,
  `.substring`, só as primeiras linhas/parágrafos, hash ou regex sobre um prefixo.
- **C — Corte de coleção:** analisa só parte dos itens/mensagens/meses de um conjunto ("5 mais
  recentes", `LIMIT`, `[-N:]`, `fetchmany`, `islice`, `random.sample`, "top N" que descarta o resto).
- **R — Representação parcial:** o texto é trocado por algo menor antes da análise (só o título, só
  o domínio, um resumo, um trecho) e a análise decide como se tivesse visto o texto inteiro.
- **P — Prompt maior que a janela:** o texto vai inteiro para o prompt, mas ninguém confere se o
  prompt cabe no `num_ctx` (Ollama) ou no limite de entrada do modelo (APIs, e `bge-m3`, que corta em
  silêncio acima de 8.192 tokens).

## O que NÃO é violação, mas precisa ser listado

Corte que só afeta **apresentação ou log** (mensagem de erro, `print`, linha de JSONL, rótulo de
tela, texto mostrado numa página) e corte de **identificador** (`hash[:8]`, slug, nome de arquivo,
`data[:10]` para pegar o dia de um ISO, `[:7]` para o mês). Isso é classe **NA** (não analítico) e
precisa da prova de que o valor cortado não entra em decisão nenhuma.

## Os quatro resultados possíveis por arquivo (nenhum é o padrão)

- `CERTIFICADO` — você leu o arquivo **inteiro** e nele nenhum texto de conteúdo é analisado só em
  parte. Exige uma linha de evidência: o que o arquivo faz com texto, ou "não manipula texto de
  conteúdo: só infraestrutura", e, se manipula, como o texto passa por inteiro.
- `CORTA` — há pelo menos um ponto T, C, R ou P nesse arquivo.
- `NÃO ANALÍTICO` — o arquivo só tem cortes de apresentação/log/identificador, todos listados.
- `NÃO CONFERIDO` — você não conseguiu ler o arquivo inteiro. Nunca promova a `CERTIFICADO` por falta
  de evidência; é melhor dizer `NÃO CONFERIDO` do que chutar.

**Ler o arquivo inteiro é obrigatório.** Procurar padrão com grep não certifica nada: o corte pode
estar em `.split("\n")[0]`, num `LIMIT` dentro de um SQL, ou numa função que só recebe o título.
Arquivo com mais de 2000 linhas: leia em partes, até a última linha. Registre `linhas lidas/total` e
confira o total com `wc -l`.

## Formato da sua saída

Escreva um arquivo Markdown (o caminho está no seu pedido) com **duas** seções, nesta ordem:

### 1. Tabela de certificação (uma linha por arquivo da sua lista, na ordem da lista)

```
| Arquivo | Linhas lidas/total | Resultado | Evidência (uma linha) | Ponto |
```

Em `Ponto`, ponha `—` quando não houver, ou os rótulos que você criou (ver abaixo). Não omita nenhum
arquivo da sua lista, nem acrescente arquivo que não esteja nela.

### 2. Pontos encontrados

Para cada ponto, um bloco com **todos** estes campos preenchidos:

```
#### <SEU-PREFIXO>-nnn — <arquivo>:<linha> — <função ou escopo>
- Classe: T | C | R | P | NA
- O que é cortado e quanto: ...
- Qual decisão do produto depende desse corte: (prompt de qual tarefa de LLM? embedding? filtro? só a tela?)
- Trecho de código (1 a 3 linhas, copiado):
- Justificativa existente no código/comentário (cite o lugar) ou "nenhuma":
- Por que isto é analítico (T/C/R/P) ou só apresentação/log/identificador (NA):
```

Use como `<SEU-PREFIXO>` exatamente o prefixo que o seu pedido indicar. Numere a partir de 001.

## Regras de julgamento que evitam os dois erros comuns

1. **Não invente violação.** `data[:10]` sobre um ISO 8601 é a data, não um texto cortado; `hash[:8]`
   é identificador; `url.split("?")[0]` é normalização de URL, não corte de conteúdo. Isso é NA (ou
   nem isso, quando é só infraestrutura) — mas diga isso explicitamente.
2. **Não absolva por comentário.** Um comentário no código explicando o corte **não** é aprovação; o
   ponto continua sendo ponto. Cite o comentário no campo de justificativa existente e siga.
3. Em caso de dúvida real sobre se algo alimenta análise ou só apresentação, registre o ponto e
   escreva a dúvida no campo "Por que isto é analítico".

## Testes (só para quem recebeu arquivos de `tests/`)

Certificação simplificada: o teste não gera ponto T/C/R/P. Para cada arquivo de teste diga só se ele
**constrói entrada que esconde um corte** (uma fixture que já chega cortada, um texto curtinho onde o
código cortaria um texto real, um mock que devolve só o título) ou se **apenas exercita o código**.
Resultado `CERTIFICADO` com evidência de uma linha em ambos os casos; use `CORTA` apenas se o próprio
arquivo de teste contiver o corte analítico (raro). Se um teste documenta um corte do código de
produção (por exemplo, afirma `texto[:2000]`), diga qual arquivo de produção ele documenta — isso é
prova valiosa para o relatório.
