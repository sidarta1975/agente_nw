# DOC 079 — Auditoria de "texto por inteiro" em todo o código do projeto

**Brief:** `docs/briefs/brief_079_auditoria_texto_por_inteiro_2026-11-07.md`
**Data:** 2026-11-08
**Commit:** `COMMIT_079`

---

## RELATÓRIO FINAL

- **Brief executado:** 079 — auditoria de "texto por inteiro" em todo o código do projeto. Só leitura
  do código de produção: **nenhum arquivo de `agente_nw/`, `config/`, `extensao/` ou `tests/` existente
  foi alterado**.

- **Arquivos criados:**
  - `scripts/verificar_auditoria_texto.py` — o verificador do relatório (passo 5 do brief).
  - `tests/test_verificar_auditoria_texto.py` — 52 testes do verificador, escritos antes dele, em
    árvores sintéticas em `tmp_path` (nenhum lê o repositório real).
  - `docs/EXCECOES_TEXTO_INTEGRAL.md` — registro de exceções, criado vazio: só Sidarta escreve nele.
  - `docs/docs/doc_079_auditoria_texto_por_inteiro_2026-11-08.md` (este relatório).
  - `docs/auditoria_079_material/` — o material de leitura, arquivo por arquivo, de onde este
    relatório foi consolidado (9 arquivos de leitura, a varredura mecânica crua e o universo).
  - `logs/commit_079.txt`, `logs/arquivos_079.txt`.

- **Arquivos alterados (com resumo da mudança em uma linha cada):** nenhum arquivo de código. Do
  `docs/PLAN.md`, as linhas de Resumo, Doing, Backlog e Done.

- **Arquivos preservados literalmente na área afetada:** todos os 315 arquivos de código auditados.

- **Script de verificação (o gate, rodado pelo `scripts/agente_entregar.sh`; saída colada):**

```
GATE_079
```

- **Comandos executados:**

```
$ .venv/bin/python -m pytest tests/test_verificar_auditoria_texto.py -q
52 passed in 3.70s

$ .venv/bin/python scripts/verificar_auditoria_texto.py --raiz .
317 arquivos, 256 certificados, 54 cortam, 7 não analíticos, 0 não conferidos, 45 ponto(s) aguardando decisão de Sidarta
1272 ocorrência(s) da varredura mecânica, todas com destino no relatório

$ git diff --stat
.gitignore | 8 ++++++++
 AGENTS.md  | 4 ++--
 2 files changed, 10 insertions(+), 2 deletions(-)

$ git status --short
M .gitignore
 M AGENTS.md
?? docs/
?? scripts/verificar_auditoria_texto.py
?? tests/test_verificar_auditoria_texto.py
```

- **Manifesto do commit (`logs/arquivos_079.txt` e `logs/commit_079.txt`, conteúdo colado):**

```
logs/arquivos_079.txt:
scripts/verificar_auditoria_texto.py
tests/test_verificar_auditoria_texto.py
docs/EXCECOES_TEXTO_INTEGRAL.md
docs/docs/doc_079_auditoria_texto_por_inteiro_2026-11-08.md
docs/PLAN.md
docs/auditoria_079_material/REGRAS_AUDITORIA.md
docs/auditoria_079_material/saida_P0.md
docs/auditoria_079_material/saida_P0b.md
docs/auditoria_079_material/saida_A1.md
docs/auditoria_079_material/saida_A2.md
docs/auditoria_079_material/saida_A3.md
docs/auditoria_079_material/saida_A4.md
docs/auditoria_079_material/saida_T1.md
docs/auditoria_079_material/saida_T2.md
docs/auditoria_079_material/saida_T3.md

logs/commit_079.txt:
docs(auditoria): 079 audita "texto por inteiro" nos 317 arquivos de codigo

Leitura do inicio ao fim de todos os 317 arquivos de codigo do projeto (38.289
linhas; nenhum NAO CONFERIDO), em busca de todo lugar em que o programa analisa
so uma parte de um texto. Resultado: 256 arquivos certificados, 54 que cortam, 7
com corte so de apresentacao/log/identificador, e 45 pontos que esperam decisao
de Sidarta - nenhum aprovado pelo executor. Nenhum arquivo de codigo de producao
foi alterado.

Entram tambem o verificador do relatorio (scripts/verificar_auditoria_texto.py,
52 testes) e o registro de excecoes vazio (docs/EXCECOES_TEXTO_INTEGRAL.md), em
que so Sidarta escreve: o verificador confere que cada arquivo do universo
aparece uma vez na tabela, que a contagem de linhas bate com o disco, que cada
uma das 1.272 ocorrencias da varredura mecanica tem destino e que nenhuma
excecao foi aprovada por quem nao pode.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

- **Pendências e decisões que ficaram abertas:** 45 pontos da seção 3 esperam a decisão de Sidarta
  (aprovar a exceção ou mandar corrigir); 7 cortes não analíticos da seção 4 podem ser contestados por
  ele. O executor não aprovou nenhum, não corrigiu nenhum e não escreveu nada no registro de exceções.

- **Resumo, Doing, Backlog e Done do `docs/PLAN.md` atualizados:** sim.

---

## 1. Resumo para Sidarta

Li **todos os 317 arquivos de código do projeto, do início ao fim** (315 que já existiam, mais os 2
criados por este brief): 15.288 linhas em `agente_nw/`, 2.903 em `cli.py`/console/ponte, 1.551 em
`scripts/`, `config/` e `extensao/`, e 21.323 nos 158 arquivos de teste — 38.289 linhas no total.
Nenhum arquivo ficou `NÃO CONFERIDO`.

O princípio não está sendo cumprido em **45 lugares**, e nenhum deles tem aprovação sua registrada.
Os cinco mais graves, em uma linha cada:

1. **P-013 — a página da rede social é cortada na origem, dentro do seu Chrome** (`extensao/conteudo.js:199`,
   200.000 caracteres): o que é cortado ali não existe para mais ninguém no projeto.
2. **P-014 — um post com mais de 5.000 caracteres é jogado fora inteiro, sem registro**
   (`navegador.py:89`): não é cortado, é descartado, e nada no programa diz que ele existiu.
3. **P-001 — o vetor que decide tudo no agrupamento vem de 2.000 caracteres da notícia**
   (`agrupador.py:88`): o assunto a que o item é vinculado, a republicação, o centróide e a divisão
   saem desse recorte, e o `bge-m3` aceita 8.192 *tokens*, muito mais do que isso.
4. **P-006/P-007 — a notícia é julgada sem que o corpo dela seja lido**: a qualificação
   (`qualificador.py:44`) vê só título e domínio de 5 itens, e o cartão (`cartoes.py:51`) vê 300
   caracteres; o resumo do cartão passa a ser *a* representação do assunto no resto do produto.
5. **P-040/P-041 — ninguém mede se o texto cabe na janela do modelo**, em nenhuma chamada de LLM
   além da redação, e em nenhuma chamada de embedding: um prompt maior que o `num_ctx` é cortado em
   silêncio pelo Ollama (armadilha 1 do PLAN) e o `bge-m3` corta em silêncio acima de 8.192 tokens.

Além dos 45, há 7 cortes que **não** alimentam análise (data, log, tela) na seção 4, com a prova de
cada um; se você discordar de qualquer linha dessa seção, ela volta para a seção 3.

O verificador (`scripts/verificar_auditoria_texto.py`) confere que nada ficou fora: 317 arquivos na
tabela, um por arquivo, com a contagem de linhas batendo com o disco; 1.272 ocorrências da varredura
mecânica, todas com destino; e nenhuma exceção aprovada por quem não pode. Saída dele:

```
317 arquivos, 256 certificados, 54 cortam, 7 não analíticos, 0 não conferidos, 45 ponto(s) aguardando decisão de Sidarta
1272 ocorrência(s) da varredura mecânica, todas com destino no relatório
```

**O que você decide:** cada ponto da seção 3 tem, em branco, a linha `Decisão de Sidarta: ____`.
Aprovar a exceção significa escrever a linha correspondente em `docs/EXCECOES_TEXTO_INTEGRAL.md`;
mandar corrigir significa pedir um brief. O executor não pode fazer nem um nem outro.

---

## 2. Método

**O universo.** O item 3.7 do brief define o que "todos os códigos" quer dizer, e o verificador
enumera exatamente isso, sozinho: `agente_nw/**/*.py`, `config/**/*.py` e `config/**/*.yaml`,
`scripts/**/*.py`, `scripts/**/*.sh` e as 19 migrações `scripts/migracoes/*.sql`, `extensao/**/*.js`
e o `manifest.json`, os `*.py` da raiz (não há nenhum) e `tests/**/*.py`. Ficam fora `.venv/`,
`node_modules/`, `__pycache__/`, `dados/`, `logs/`, `docs/` e `.git/`. Duas inclusões vão além da
letra do brief, de propósito, porque cobrir mais nunca cobre menos: `agente_nw/**/*.yaml` (por causa
de `nucleo/prompts/exemplos_conversavel.yaml`, que é dado de prompt) e o `extensao/manifest.json`
(citado no próprio item 3.7). Deu **317** arquivos. Ficaram fora da tabela, por serem dados e não
código: os templates HTML do console (18 arquivos, só apresentação) e as 8 fixturas de dados de
`tests/fixtures/` — estas estão cobertas na linha de certificação do teste que as lê.

**Como cada arquivo foi certificado.** Ler o arquivo **inteiro**, do início à última linha; anotar
`linhas lidas/total` e conferir o total com `wc -l`; decidir entre `CERTIFICADO`, `CORTA`,
`NÃO ANALÍTICO` e `NÃO CONFERIDO`, sem padrão nenhum (item 3.4). Procurar padrão com `grep` não
certifica nada: o corte pode estar num `LIMIT` dentro de um SQL, num `.split("\n")[0]` ou numa função
que só recebe o título — todos esses casos apareceram de verdade nesta auditoria. A varredura
mecânica (apêndice A) serve para **não deixar escapar**, nunca para certificar.

**Quem leu o quê.** A leitura foi dividida em oito partes, cada uma lendo os arquivos inteiros, e o
material bruto de cada parte está em `docs/auditoria_079_material/`. O executor leu ele mesmo, de
ponta a ponta, **todo arquivo que monta prompt, chama LLM ou embedding, ou lê dado de coleta**, como
o passo 4 do brief exige antes da assinatura: os 14 módulos de `nucleo/prompts/`, `nucleo/llm.py`,
`nucleo/relevancia/*`, `nucleo/agrupamento/*`, `nucleo/redacao.py`, `nucleo/historico.py`,
`nucleo/termos_contato.py`, `nucleo/consulta.py`, `nucleo/pedido.py`, `nucleo/localizacao.py`,
`nucleo/fluxo.py` (o trecho do orçamento de tokens), `perfil/extrator.py`, `perfil/configurador.py`,
`perfil/inferencia.py`, todo o `coleta/` (RSS, capturas e WhatsApp),
`nucleo/database/queries/{conversa,perfis}.py`, `extensao/conteudo.js` e `config/limiares.yaml`.
A releitura corrigiu um achado do material: o fato gravado da rede social **não** é o "texto
essencial" que o modelo devolve, e sim o bloco integral (`coleta/capturas/leitor.py:155`,
`conteudo=bloco`) — a saída do modelo só decide descartar ou não e a data. Quem assina é o executor.

**Consolidação dos pontos (desvio documentado).** O material de leitura trouxe 149 locais de corte.
Muitos são o mesmo corte visto de arquivos diferentes — o teto de caracteres da página, por exemplo,
aparece no YAML, no contrato Pydantic, no backend da ponte e no JavaScript da extensão. A seção 3
consolida isso em **45 pontos** `P-nnn`, cada um com todos os locais listados, em vez de 149 pontos
quase repetidos: são 45 decisões para você tomar, não 149, e nenhum local deixou de ser citado (o
verificador confere local por local). A numeração sequencial `P-nnn` substitui os rótulos por parte
(`A1-…`, `A2-…`) do material; a correspondência está no campo "Onde mais aparece" de cada ponto.

**O commit de cada ponto** vem de `git --no-optional-locks blame -L <linha>,<linha>`, que diz quem
tocou aquela linha por último — não necessariamente quem introduziu o corte. Onde os dois diferem e
isso importa, o ponto diz. Em P-040 e P-042 o blame aponta `af2a09f` (brief 077, de anteontem) porque
aquelas linhas foram reindentadas ali; a **ausência de conferência de janela** é do cliente de LLM
original (brief E1_003) e nunca foi alterada.

**Comandos rodados (só leitura):**

```
$ .venv/bin/python scripts/verificar_auditoria_texto.py --varredura --raiz . | wc -l
1272

$ .venv/bin/python scripts/verificar_auditoria_texto.py --raiz .
317 arquivos, 256 certificados, 54 cortam, 7 não analíticos, 0 não conferidos, 45 ponto(s) aguardando decisão de Sidarta
1272 ocorrência(s) da varredura mecânica, todas com destino no relatório
```

**Nota de execução.** Um dos leitores auxiliares criou, por erro de digitação de caminho, o arquivo
vazio `/private/tmp/claude-501/-Users-sidarta48/github/agente_nw/placeholder`, **fora** do
repositório; a remoção foi negada pela trava de permissão e ele continua lá. Nada no repositório foi
tocado por isso. Apagar esse arquivo é operação sua, se incomodar.
---

## 3. Pontos que cortam o texto — aguardando decisão

45 pontos. Todos nascem com o estado `AGUARDANDO DECISÃO DE SIDARTA`: o executor não aprova exceção.
A linha `Decisão de Sidarta: ____` fica em branco de propósito.

### 3.a. Notícia (coleta por RSS)

#### P-001 — agente_nw/nucleo/agrupamento/agrupador.py:88 — `agrupar`
- Classe: T
- O que é cortado e quanto: os 2.000 primeiros caracteres do texto da notícia, concatenados ao título, são tudo que vai para `embeddar`. Uma notícia de 8.000 caracteres entra com 25% dela.
- Qual decisão do produto depende desse corte: o vetor do item — e com ele o assunto a que o item é vinculado, a detecção de republicação (`cosseno_republicacao`), o centróide do assunto, a contagem de fontes independentes e a divisão de assunto. Todo o resto do produto parte desse agrupamento.
- Commit que introduziu: `06ba8e0`
- Justificativa existente: nenhuma — a linha não tem comentário e o número 2.000 não aparece em nenhum documento. O `bge-m3` aceita 8.192 tokens, então o limite não vem do modelo.
- Proposta do executor: a justificativa possível é custo — embeddar o texto inteiro de cada item é mais lento e, acima de 8.192 tokens, o `bge-m3` corta sozinho. Corrigir bem custa um brief: embeddar em janelas e guardar a média, ou subir o teto para algo próximo do limite real do modelo em caracteres (≈ 20.000) e medir o custo. Corrigir mal (só subir o número) muda o vetor de todo item novo e deixa o banco com itens vetorizados por dois critérios, o que afeta o agrupamento — tem de ser decisão sua.
- Estado: AGUARDANDO DECISÃO DE SIDARTA
- Decisão de Sidarta: ____

#### P-002 — agente_nw/coleta/rss/canonicalizar.py:54 — `hash_titulo`, e `rss/leitor.py:320-324`
- Classe: R
- O que é cortado e quanto: a deduplicação de notícia é feita por um hash **só do título** normalizado, antes de qualquer pedido de rede. O corpo do item repetido nunca é baixado.
- Qual decisão do produto depende desse corte: se o item entra ou não no banco. Duas matérias diferentes com a mesma manchete (comum em agências e republicações editadas) viram uma só, e a que fica é a primeira vista.
- Commit que introduziu: `9098879`
- Justificativa existente: o comentário de `leitor.py:321` — "O mesmo título aparece em várias buscas: checa pelo título antes de qualquer pedido de rede". É explicação (economia de rede e de bloqueio), não aprovação.
- Proposta do executor: a justificativa é forte — pedir a página para descobrir que é duplicata custa uma requisição e aumenta o risco de 429, e o brief 045 existe por causa disso. Proponho manter, registrando a exceção. Corrigir custaria um brief e abriria o risco de bloqueio que o 045 fechou.
- Estado: AGUARDANDO DECISÃO DE SIDARTA
- Decisão de Sidarta: ____
- Onde mais aparece: `agente_nw/coleta/rss/leitor.py:320` (a checagem), `agente_nw/coleta/rss/leitor.py:329` (a segunda, já com a URL canônica).

#### P-003 — agente_nw/coleta/rss/leitor.py:338 — `_processar_fonte`, e `rss/ruido.py:51`
- Classe: R
- O que é cortado e quanto: quando `trafilatura.extract` falha ou a página não abre, `corpo` fica `None` e o item é gravado **só com o título** (l. 350-359); daí em diante ele é analisado por título (o embedding do P-001 usa só o título nesse caso). E `ruido.py:51` descarta o item inteiro quando o corpo tem menos de `teaser_minimo_caracteres` (400).
- Qual decisão do produto depende desse corte: o que o agrupamento, a qualificação e o cartão veem daquele item; e, no caso do teaser mínimo, se a notícia existe para o produto.
- Commit que introduziu: `48f4ce0`
- Justificativa existente: nenhuma para o item sem corpo. Para o teaser mínimo, o brief 006 trata disso como regra de ruído (o PLAN o registra como filtro de qualidade), o que é justificativa escrita, não aprovação de exceção.
- Proposta do executor: o teaser mínimo é defensável (um teaser de 200 caracteres não sustenta cartão nem gancho). O item gravado sem corpo é pior: ele passa a ser julgado por manchete, o que é exatamente o que o AGENTS §4 proíbe na redação. Proponho marcar o item sem corpo e não deixá-lo chegar ao cartão; custo de um brief pequeno, uma coluna e um filtro.
- Estado: AGUARDANDO DECISÃO DE SIDARTA
- Decisão de Sidarta: ____
- Onde mais aparece: `agente_nw/coleta/rss/ruido.py:51`.

#### P-004 — agente_nw/coleta/rss/ruido.py:57 — `e_ruido`
- Classe: T
- O que é cortado e quanto: a busca por marca de conteúdo patrocinado ("publicidade", "conteúdo patrocinado", "publieditorial"…) olha só as **3 primeiras linhas** do corpo.
- Qual decisão do produto depende desse corte: se a notícia é descartada como ruído. Uma matéria que declara o patrocínio no rodapé passa pelo filtro e vira gancho.
- Commit que introduziu: `9098879`
- Justificativa existente: nenhuma.
- Proposta do executor: aqui o custo de corrigir é quase zero — procurar as mesmas seis marcas no corpo inteiro é uma linha e não tem efeito colateral de modelo nem de banco. Proponho corrigir num brief pequeno; se você preferir manter, o motivo seria evitar falso positivo quando a palavra "publicidade" aparece no meio do texto jornalístico.
- Estado: AGUARDANDO DECISÃO DE SIDARTA
- Decisão de Sidarta: ____

#### P-005 — agente_nw/coleta/rss/leitor.py:246 — tetos da coleta
- Classe: C
- O que é cortado e quanto: a coleta para por tempo (`tempo_maximo_segundos`, 240 s, l. 246), por quantidade de candidatos (`candidatos_suficientes`, 10, l. 275), por feed (`maximo_itens_novos_por_feed`, 15, l. 362) e por reuso de termo (24 h, l. 280); e o pedido faz no máximo `max_consultas_por_pedido` (4) buscas, escolhidas por prioridade entre assunto, contato, `termos_busca` e `interessa` (`google_news.py:59-61,72`, com tetos de 3, 6 e 5 termos por origem e 4 por tema em `:24`).
- Qual decisão do produto depende desse corte: que notícias existem no banco para aquele pedido. Tudo o que não foi coletado não pode virar gancho.
- Commit que introduziu: `5e3af5b`
- Justificativa existente: sim, e é a mais sólida do projeto: o AGENTS §6 e o brief 045 dizem que a coleta é resiliente a bloqueio e que "cada pedido faz poucas buscas". Os números estão em `config/limiares.yaml` com comentário em cada chave.
- Proposta do executor: manter e registrar a exceção em bloco. É teto de custo e de bloqueio, não corte de um texto: nenhuma notícia coletada é analisada pela metade por causa dele. O que vale pedir é que a tela diga quando a coleta parou por teto (hoje o `preparar` já avisa quando passou do tempo).
- Estado: AGUARDANDO DECISÃO DE SIDARTA
- Decisão de Sidarta: ____
- Onde mais aparece: `agente_nw/coleta/rss/leitor.py:275`, `:280`, `:362`; `agente_nw/coleta/rss/google_news.py:24,59,60,61,72`; `agente_nw/nucleo/consulta.py:172`; `config/limiares.yaml:29,30,35,36,37,40,41`.

#### P-006 — agente_nw/nucleo/relevancia/qualificador.py:43 — `_itens_recentes_resumidos`
- Classe: R e C
- O que é cortado e quanto: dos itens do assunto ficam os **5 mais recentes** (l. 43) e, de cada um, só **(título, domínio)** (l. 44). O texto da notícia não entra no prompt.
- Qual decisão do produto depende desse corte: os prompts `rotular` (o título do assunto) e `qualificar` (`substancial`, `conversavel`, temas e justificativa). O `substancial_minimo`/`conversavel_minimo` filtra o assunto para sempre a partir dessa nota.
- Commit que introduziu: `4954eff`
- Justificativa existente: nenhuma no código. O prompt diz "até cinco itens de notícia", o que mostra que o 5 é deliberado, mas não aprovado.
- Proposta do executor: a justificativa possível é que o julgamento "dá para puxar assunto com isso?" é sobre o assunto, não sobre a matéria, e títulos bastam para isso. Não me convence para `substancial` ("tem fato concreto, decisão, desdobramento?"), que é exatamente o que o corpo diz e a manchete esconde. Proponho corrigir: mandar o trecho de cada item (como o cartão já faz) e subir o `num_ctx` de `qualificar`, que hoje é 2.048 no `air16`. Custo: um brief, e mais tokens por assunto.
- Estado: AGUARDANDO DECISÃO DE SIDARTA
- Decisão de Sidarta: ____
- Onde mais aparece: `agente_nw/nucleo/relevancia/qualificador.py:44`.

#### P-007 — agente_nw/nucleo/relevancia/cartoes.py:49 — `gerar_cartao`
- Classe: C e T
- O que é cortado e quanto: os **5 itens mais recentes** (l. 49) e, de cada um, os **300 primeiros caracteres** do texto (l. 51, `_TRUNCAMENTO_TRECHO`).
- Qual decisão do produto depende desse corte: o prompt `cartao`. O resumo gerado vira `assunto.resumo_cartao` e, daí em diante, é **a** representação do assunto: é o que o gate do objetivo lê (P-010), o que o filtro de `evitar` procura (P-012) e o que o redator usa para escrever a notícia (P-031).
- Commit que introduziu: `4954eff`
- Justificativa existente: nenhuma; o prompt diz "cada um com um trecho do texto".
- Proposta do executor: este é o corte com maior efeito composto do projeto, porque todo o resto passa a ver o assunto pelo cartão. 300 caracteres é o primeiro parágrafo — às vezes só o lide. Proponho corrigir subindo o trecho para o que o `num_ctx` de `cartao` (4.096 no `air16`, 16.384 no `pro48`) permitir, com conta explícita de tokens. Custo: um brief, e cartões mais lentos.
- Estado: AGUARDANDO DECISÃO DE SIDARTA
- Decisão de Sidarta: ____
- Onde mais aparece: `agente_nw/nucleo/relevancia/cartoes.py:51`.

#### P-008 — agente_nw/nucleo/agrupamento/calibracao.py:82 — `_amostrar_banda`, `_amostrar_controle`, `_trecho`
- Classe: C e T
- O que é cortado e quanto: dos pares possíveis, 35 da banda de dúvida e 15 de controle, **sorteados** (l. 82 e 103); e cada item do par entra no prompt com 2.000 caracteres (l. 108).
- Qual decisão do produto depende desse corte: o limiar `cosseno_mesmo_assunto`, que `_gravar_novo_limiar` escreve em `config/limiares.yaml` — isto é, o critério de agrupamento de todo o produto.
- Commit que introduziu: `06ba8e0`
- Justificativa existente: nenhuma linha de código, mas o ADR escrito por `_escrever_adr` registra a composição da amostra e a acurácia, o que mostra desenho amostral deliberado.
- Proposta do executor: é amostragem declarada para calibrar um limiar, e amostra é o método certo aqui — provavelmente a exceção mais defensável do projeto. Proponho aprovar com a ressalva de que o trecho de 2.000 caracteres seja o mesmo valor do P-001 (hoje os dois são 2.000 por coincidência, não por vínculo no código).
- Estado: AGUARDANDO DECISÃO DE SIDARTA
- Decisão de Sidarta: ____
- Onde mais aparece: `agente_nw/nucleo/agrupamento/calibracao.py:103`, `:108`.

#### P-009 — agente_nw/nucleo/relevancia/candidatos.py:31 — afunilamento dos assuntos
- Classe: C
- O que é cortado e quanto: dos assuntos qualificados e não vistos, ficam `conector.candidatos_por_contato` (10) ranqueados por cosseno (`candidatos.py:31` e `:83`); desses, `conector.itens_no_menu` (5) entram no menu (`cruzamento.py:272` e `:481`). A qualificação e o cartão rodam no máximo `teto_por_dia` (40) itens por rodada (`assuntos.py:179`, `:254`, `consulta.py:204`, `cli.py:442`).
- Qual decisão do produto depende desse corte: que assuntos chegam ao gate, ao menu e à redação. O que fica fora do corte de 10 não é gravado nem como descartado.
- Commit que introduziu: `f9a1e53`
- Justificativa existente: parcial — a docstring de `selecionar_por_consulta` explica que os evitados saem antes do corte "para não ocupar vaga", o que reconhece o corte; os números têm comentário em `limiares.yaml`.
- Proposta do executor: o teto do menu é decisão de produto (quantos ganchos uma pessoa quer ver) e eu a aprovaria. O teto de 10 candidatos é diferente: ele decide, por cosseno, o que o modelo nunca vai julgar — e o brief 049 existe porque o cosseno erra. Proponho manter 5 no menu e revisar o 10 de candidatos com medição (quantos dos 10 passam o gate hoje). Custo: um brief de medição, sem risco.
- Estado: AGUARDANDO DECISÃO DE SIDARTA
- Decisão de Sidarta: ____
- Onde mais aparece: `agente_nw/nucleo/relevancia/candidatos.py:83`; `agente_nw/nucleo/relevancia/cruzamento.py:272`, `:481`; `agente_nw/nucleo/database/queries/assuntos.py:179`, `:254`; `agente_nw/nucleo/consulta.py:204`; `agente_nw/cli.py:442`; `config/limiares.yaml:10,18,19,46`.

#### P-010 — agente_nw/nucleo/relevancia/cruzamento.py:155 — `_aplicar_gate_objetivo`
- Classe: R
- O que é cortado e quanto: o gate recebe `(titulo_gerado, resumo_cartao)` de cada candidato. Nem manchetes, nem corpo — e o `resumo_cartao` já vem dos 300 caracteres do P-007.
- Qual decisão do produto depende desse corte: o sim/não do brief 049, que **descarta** o assunto do pedido (`status="descartado"`, `motivo="sem relação com o objetivo (juízo do modelo)"`). É descarte definitivo para aquele pedido.
- Commit que introduziu: `d2a1a54`
- Justificativa existente: o comentário das l. 468-470 explica para que o gate serve; não diz por que ele vê só título e resumo.
- Proposta do executor: o gate julga relação com o objetivo, e para isso o título mais o resumo costumam bastar — mas o resumo é o do P-007. Proponho tratar P-007 e P-010 como uma decisão só: se o cartão melhorar, o gate melhora de graça. Custo zero aqui.
- Estado: AGUARDANDO DECISÃO DE SIDARTA
- Decisão de Sidarta: ____

#### P-011 — agente_nw/nucleo/relevancia/cruzamento.py:282 — `assuntos_para_prompt`
- Classe: R
- O que é cortado e quanto: o prompt `cruzar_por_que` recebe `(titulo_gerado, tipo, ponto_de_apoio)` — sem resumo, sem manchete, sem corpo.
- Qual decisão do produto depende desse corte: o campo `por_que` gravado em `assunto_contato`, que o usuário lê na tela e que a redação reaproveita.
- Commit que introduziu: `f9a1e53`
- Justificativa existente: sim, e é deliberada: o comentário das l. 52-53 — "O 'por quê' recebe só o título do assunto e os temas: qualquer posição do contato ('ele apoia X') é invenção do modelo". É uma restrição de verdade, não de custo.
- Proposta do executor: aprovar. Aqui o corte é a própria proteção do AGENTS §4 (a redação nunca afirma sobre a pessoa o que ela não disse); dar mais texto ao modelo aumentaria a chance de ele inferir posição. É o único ponto desta auditoria em que o corte é o recurso, não o defeito.
- Estado: AGUARDANDO DECISÃO DE SIDARTA
- Decisão de Sidarta: ____
- Onde mais aparece: `agente_nw/nucleo/relevancia/cruzamento.py:488`.

#### P-012 — agente_nw/nucleo/relevancia/candidatos.py:41 — `termo_evitado`
- Classe: R
- O que é cortado e quanto: o termo que o usuário mandou evitar (e o `nao_me_interessa` do brief 040) é procurado só em `titulo_gerado + resumo_cartao`.
- Qual decisão do produto depende desse corte: o descarte "evitado pelo contexto". Um assunto cujo termo proibido aparece só no corpo da notícia passa o filtro e pode virar gancho.
- Commit que introduziu: `05eaf18`
- Justificativa existente: a docstring declara o escopo ("no título e no resumo do assunto"); declarar não é justificar.
- Proposta do executor: corrigir vale a pena, porque "evitar" é ordem explícita do usuário — é o tipo de falha que ele nota na primeira vez. Procurar também nas manchetes dos itens do assunto é barato (os títulos já estão no banco); procurar no corpo inteiro de todos os itens é mais caro e pode gerar falso positivo. Proponho o meio: título, resumo e manchetes.
- Estado: AGUARDANDO DECISÃO DE SIDARTA
- Decisão de Sidarta: ____

### 3.b. Rede social (extensão do Chrome)

#### P-013 — extensao/conteudo.js:199 — `estado`
- Classe: T
- O que é cortado e quanto: `texto.slice(0, maximo)` sobre o `innerText` da página, com `maximo = extensao.maximo_caracteres_pagina` (200.000, `config/limiares.yaml:59`). O mesmo teto é aplicado de novo no lado do programa (`extensao_backend.py:93`) e declarado no contrato (`modelos/configuracao.py:244`).
- Qual decisão do produto depende desse corte: **tudo** o que o produto sabe daquela leitura. O corte acontece dentro do Chrome, antes de o texto chegar ao programa: o que é cortado ali não existe para o resto do sistema, não vai para a divisão em blocos, não vira fato e não aparece em nenhum log.
- Commit que introduziu: `906d759`
- Justificativa existente: nenhuma no JavaScript nem no YAML (a chave só tem o nome).
- Proposta do executor: 200.000 caracteres é generoso para um perfil comum, então o risco prático é baixo — mas o corte é silencioso e é o único do projeto que acontece fora do programa. Proponho não mudar o número e, sim, fazer a extensão devolver `len(texto)` junto com o recorte, para o programa registrar quando cortou (uma linha de aviso em `chamadas_llm.jsonl`, no padrão do brief 077). Custo: um brief pequeno; nenhuma mudança de comportamento.
- Estado: AGUARDANDO DECISÃO DE SIDARTA
- Decisão de Sidarta: ____
- Onde mais aparece: `agente_nw/coleta/capturas/extensao_backend.py:88`, `:93`; `extensao/background.js:148`; `config/limiares.yaml:59`; `agente_nw/nucleo/modelos/configuracao.py:244`.

#### P-014 — agente_nw/coleta/capturas/navegador.py:89 — `_extrair_blocos`
- Classe: T (perda total do bloco)
- O que é cortado e quanto: o texto da página é partido em blocos por linha em branco e **só os blocos entre 30 e 5.000 caracteres sobrevivem** (`_BLOCO_TAMANHO_MINIMO`, `_BLOCO_TAMANHO_MAXIMO`, l. 21-22). Um post com mais de 5.000 caracteres é descartado inteiro, sem registro, sem aviso e sem contagem.
- Qual decisão do produto depende desse corte: se aquela publicação existe. Ela não é analisada pela metade: ela desaparece — não vira fato, não entra no `blocos_capturados` do resumo e não aparece em log nenhum.
- Commit que introduziu: `c6e0969`
- Justificativa existente: nenhuma; as duas constantes não têm comentário.
- Proposta do executor: este é, na minha leitura, o pior ponto da auditoria, porque é perda total e silenciosa de texto de origem. O teto existe para não mandar menu e rodapé ao modelo, e para isso o piso de 30 já faz quase todo o trabalho. Proponho um brief pequeno: ou partir o bloco grande em pedaços (como a conversa do WhatsApp já faz, `conversa.py:_em_blocos`), ou pelo menos contá-lo no resumo e avisar. Custo baixo; risco de não fazer nada: um post longo de alguém importante nunca é lido.
- Estado: AGUARDANDO DECISÃO DE SIDARTA
- Decisão de Sidarta: ____
- Onde mais aparece: `agente_nw/coleta/capturas/navegador.py:22`.

#### P-015 — agente_nw/coleta/capturas/navegador.py:142 — quanto da página é lido
- Classe: C
- O que é cortado e quanto: a leitura rola a página no máximo `max_rolagens` vezes (5, l. 142); no X, a rolagem tem orçamento de 12 segundos (`extensao/conteudo.js:130`); a lista de seguidos do Instagram avança 8 páginas por chamada (`conteudo.js:108`) e para em `listas.maximo_entradas` (2.000) ou `rodadas_sem_novidade` (6); `listas.py:369` marca `truncada` quando o teto corta.
- Qual decisão do produto depende desse corte: quantas publicações e quantas pessoas da lista o produto vê. O que está mais abaixo na página não existe.
- Commit que introduziu: `c6e0969`
- Justificativa existente: parcial e boa — o AGENTS §6 manda respeitar pausa entre páginas e não agir na rede; as listas têm `truncada` justamente para dizer que o teto bateu. Os comentários de `conteudo.js:66-69` explicam a paginação do Instagram.
- Proposta do executor: manter e registrar. Rolar indefinidamente numa rede social é o caminho mais curto para um bloqueio de conta, que é um risco maior do que ler 5 telas em vez de 10. O que proponho pedir: que o `truncada` das listas apareça na tela do usuário (hoje ele existe no modelo e morre ali).
- Estado: AGUARDANDO DECISÃO DE SIDARTA
- Decisão de Sidarta: ____
- Onde mais aparece: `extensao/conteudo.js:130`, `:108`; `agente_nw/coleta/capturas/listas.py:369`; `config/limiares.yaml:48,54`.

#### P-016 — agente_nw/coleta/capturas/leitor.py:136 — `ler_redes_sociais_do_contato`
- Classe: C
- O que é cortado e quanto: dos blocos capturados, são examinados `maximo_blocos × 4` (10 × 4 = 40, l. 136) e a leitura para ao gravar `maximo_blocos` (10) publicações por rede (l. 143).
- Qual decisão do produto depende desse corte: quantas publicações do contato viram fato — e, por consequência, o que a redação e os termos de busca sabem dele.
- Commit que introduziu: `9a8bb96`
- Justificativa existente: sim, no comentário das l. 27-29 ("cada um custa uma chamada ao modelo") e na chave do `limiares.yaml:42`. É justificativa de custo, escrita.
- Proposta do executor: manter. Cada bloco é uma chamada de LLM local; 10 publicações recentes é o que uma leitura sob demanda suporta sem virar lote de 10 minutos. Registre a exceção com o número à vista, para que mudá-lo seja decisão sua, não ajuste de código.
- Estado: AGUARDANDO DECISÃO DE SIDARTA
- Decisão de Sidarta: ____
- Onde mais aparece: `agente_nw/coleta/capturas/leitor.py:143`; `config/limiares.yaml:42`; `agente_nw/nucleo/consulta.py:147`.

#### P-017 — agente_nw/coleta/capturas/navegador.py:61 — quantas imagens são descritas
- Classe: C
- O que é cortado e quanto: no máximo `maximo_imagens_por_rede` (8) imagens por rede, e só as com largura ≥ 250 px (`conteudo.js:189`, `limiares.yaml:43-44`); a extensão ainda pula imagem acima de 6 MB e imagem de host fora da lista de CDNs permitidos (`background.js`).
- Qual decisão do produto depende desse corte: quantas publicações em imagem viram fato (a descrição é o único vestígio: a imagem nunca é gravada).
- Commit que introduziu: `657edaa`
- Justificativa existente: sim: as chaves do YAML têm comentário ("abaixo disso é ícone ou foto de perfil, não publicação") e cada descrição é uma chamada de modelo de visão, a mais caro do produto.
- Proposta do executor: manter. O corte por largura é um filtro de qualidade com justificativa técnica clara, e 8 imagens já é meio minuto de modelo de visão no Air.
- Estado: AGUARDANDO DECISÃO DE SIDARTA
- Decisão de Sidarta: ____
- Onde mais aparece: `extensao/conteudo.js:185`, `:189`; `extensao/background.js:120`; `config/limiares.yaml:43,44`.

#### P-018 — agente_nw/coleta/capturas/imagens.py:43 — `construir_prompt`
- Classe: R
- O que é cortado e quanto: a imagem publicada é substituída por uma descrição de "2 a 5 frases" e **nunca é gravada** (AGENTS §3). Tudo o que o produto saberá daquela imagem são essas frases.
- Qual decisão do produto depende desse corte: o fato `imagem:<rede>` gravado, que entra na redação com a marca `[de imagem]` e nos termos de busca do contato.
- Commit que introduziu: `657edaa`
- Justificativa existente: sim, e é de produto, não de custo: o AGENTS §3 manda não gravar a imagem, só a descrição.
- Proposta do executor: aprovar. É o desenho do produto, decidido por você, e a alternativa (guardar a imagem) é justamente o que o AGENTS proíbe. O que caberia pedir num brief futuro é descrição mais longa quando a imagem tem texto legível.
- Estado: AGUARDANDO DECISÃO DE SIDARTA
- Decisão de Sidarta: ____

#### P-019 — agente_nw/coleta/capturas/extrator.py:68 — `extrair`
- Classe: P
- O que é cortado e quanto: nada é cortado aqui — o bloco inteiro (até 5.000 caracteres, P-014) vai ao prompt `extrair_captura_rede_social`. O problema é que **ninguém confere se ele cabe**: o `num_ctx` da tarefa é 4.096 tokens no `air16`, e 5.000 caracteres de português são ≈ 1.400 tokens, mas o prompt tem mais 600 tokens de instrução e exemplo, e nada mede a soma.
- Qual decisão do produto depende desse corte: a extração do fato daquele bloco. Se o Ollama cortar o prompt em silêncio (armadilha 1 do PLAN), o modelo responde sobre um texto truncado e o fato gravado é parcial — sem erro, sem log.
- Commit que introduziu: `c6e0969`
- Justificativa existente: nenhuma.
- Proposta do executor: ver P-040: a correção certa é uma só, no cliente de LLM, e serve a todas as 15 tarefas. Este ponto fica aqui porque é a chamada com a maior entrada de texto de terceiro do produto.
- Estado: AGUARDANDO DECISÃO DE SIDARTA
- Decisão de Sidarta: ____

#### P-020 — agente_nw/coleta/capturas/busca.py:112 — identidade da pessoa decidida por 3-4 linhas
- Classe: R
- O que é cortado e quanto: o cartão de cada candidato na busca da rede vira `nome_exibido` (linha 0) + `descricao` (linhas 1 a 4, l. 112); na lista, o cabeçalho é 3 linhas (`listas.py:251`, `:254`); e o desempate por LLM recebe **só o `cabecalho`** de cada candidato (`localizacao.py:104`).
- Qual decisão do produto depende desse corte: qual perfil de rede social é gravado como sendo o do contato — a decisão com a maior consequência do produto, porque um perfil errado contamina fatos, redação e histórico.
- Commit que introduziu: `834f742`
- Justificativa existente: nenhuma explícita. A confirmação humana obrigatória (brief 037) é a compensação desenhada para isso.
- Proposta do executor: manter o recorte, porque o cartão da busca não tem mais do que isso e o usuário confirma. O que proponho pedir: que a tela de confirmação mostre o cabeçalho inteiro que a rede deu (hoje mostra as 3 linhas) e que a dúvida continue sempre indo para você — é o que o AGENTS §6 já exige.
- Estado: AGUARDANDO DECISÃO DE SIDARTA
- Decisão de Sidarta: ____
- Onde mais aparece: `agente_nw/coleta/capturas/listas.py:251`, `:254`; `agente_nw/nucleo/localizacao.py:104`.

#### P-021 — agente_nw/nucleo/localizacao.py:259 — quantas candidatas aparecem
- Classe: C
- O que é cortado e quanto: `maximo_parecidas` (5) candidatas na localização (`listas.py:138`), 5 opções mostradas na confirmação (`confirmacao.py:182`), e a deduplicação de fato de lista olha só os 200 fatos mais recentes (`localizacao.py:376`).
- Qual decisão do produto depende desse corte: quais pessoas você vê para escolher, e se um fato de lista é regravado.
- Commit que introduziu: `657edaa`
- Justificativa existente: os números estão em `limiares.yaml` com nome claro; nenhuma justificativa escrita.
- Proposta do executor: manter: cinco opções numa pergunta é desenho de tela, e a sexta candidata quase sempre é homônimo distante. O teto de 200 na deduplicação merece um olhar num brief de manutenção (um contato com mais de 200 fatos pode receber fato de lista repetido).
- Estado: AGUARDANDO DECISÃO DE SIDARTA
- Decisão de Sidarta: ____
- Onde mais aparece: `agente_nw/nucleo/localizacao.py:376`; `agente_nw/nucleo/confirmacao.py:182`; `agente_nw/nucleo/database/queries/listas.py:138`; `config/limiares.yaml:52`.

### 3.c. Conversa do WhatsApp

#### P-022 — agente_nw/nucleo/database/queries/conversa.py:97 — `blocos_por_mes`
- Classe: C
- O que é cortado e quanto: só os `whatsapp.meses_extraidos` (24) meses mais recentes do contato entram na fila de extração de fatos.
- Qual decisão do produto depende desse corte: que parte da conversa vira fato. Uma conversa de 6 anos é lida nos últimos 2.
- Commit que introduziu: `4366f01`
- Justificativa existente: sim, a chave do YAML tem comentário e o brief 061 trata a conversa como fonte de fatos recentes e de tom.
- Proposta do executor: manter. Fato de 5 anos entra marcado `[antigo]` e vale pouco para a redação; extrair 6 anos de conversa é um lote longo de LLM. O número está num lugar visível e é seu para mudar.
- Estado: AGUARDANDO DECISÃO DE SIDARTA
- Decisão de Sidarta: ____
- Onde mais aparece: `agente_nw/coleta/whatsapp/importador.py:51`; `config/limiares.yaml:71`.

#### P-023 — agente_nw/nucleo/database/queries/conversa.py:46 — `ultimas_trocas`
- Classe: C
- O que é cortado e quanto: o prompt de redação recebe as `whatsapp.trocas_no_prompt` (10) últimas mensagens (`SELECT ... LIMIT ?`), e `redacao.py:242` passa esse número.
- Qual decisão do produto depende desse corte: o tom da mensagem redigida (o brief 061 usa a conversa para o registro, não como fato).
- Commit que introduziu: `4366f01`
- Justificativa existente: sim, declarada no brief 061 e na docstring ("para o tom da redação").
- Proposta do executor: aprovar. Dez trocas bastam para o tom e é o bloco que `cortar_por_tamanho` sacrifica primeiro quando o prompt estoura (P-033) — o que é coerente: tom é o que menos se perde.
- Estado: AGUARDANDO DECISÃO DE SIDARTA
- Decisão de Sidarta: ____
- Onde mais aparece: `agente_nw/nucleo/redacao.py:242`; `config/limiares.yaml:73`.

#### P-024 — agente_nw/coleta/whatsapp/leitor.py:102 — o que da exportação é lido
- Classe: C
- O que é cortado e quanto: do `.zip` é lido **um** `.txt` (o `_chat.txt` do iPhone, ou o primeiro da lista, l. 102); mensagens de mídia, figurinha e apagadas são descartadas inteiras (l. 89); o console recusa arquivo acima de 20 MB (`app.py:465`) e conversa com mais de 2 participantes (`app.py:474`) — nos dois casos a conversa não é importada.
- Qual decisão do produto depende desse corte: que mensagens existem no banco.
- Commit que introduziu: `4366f01`
- Justificativa existente: sim, tudo declarado em docstring e no brief 061 (uma conversa por vez, um contato por vez; mídia não tem texto para analisar).
- Proposta do executor: aprovar. A perda é de mensagens sem texto (mídia) e a recusa é explícita para o usuário, não silenciosa — o oposto do P-014.
- Estado: AGUARDANDO DECISÃO DE SIDARTA
- Decisão de Sidarta: ____
- Onde mais aparece: `agente_nw/coleta/whatsapp/leitor.py:89`; `agente_nw/console/app.py:465`, `:474`.

### 3.d. Fatos e perfil do contato

#### P-025 — agente_nw/nucleo/database/queries/perfis.py:629 — `calcular_centroide_do_contato`
- Classe: T e C
- O que é cortado e quanto: o centróide do contato é o embedding de **20 fatos** (`_MAXIMO_FATOS_NO_CENTROIDE`) cortados em **500 caracteres** cada (`_TRECHO_DO_FATO_NO_CENTROIDE`), juntados num texto só.
- Qual decisão do produto depende desse corte: `aderencia_contato`, que entra no score de todo assunto, e o `ponto_de_apoio`. É o vetor que representa a pessoa.
- Commit que introduziu: `657edaa`
- Justificativa existente: o comentário da l. 614 — "o fato é guardado inteiro; para o vetor basta o começo". É explicação, não aprovação.
- Proposta do executor: a frase do comentário é discutível: o começo de uma descrição de imagem ("Imagem publicada: ...") é quase sempre genérico, e é o fim que tem o assunto. Juntar 20 fatos × 500 caracteres dá 10.000 caracteres ≈ 2.800 tokens, bem abaixo dos 8.192 do `bge-m3`: há folga para subir o trecho sem custo de modelo. Proponho corrigir junto com P-041 (medir antes de embeddar) — um brief só.
- Estado: AGUARDANDO DECISÃO DE SIDARTA
- Decisão de Sidarta: ____
- Onde mais aparece: `agente_nw/nucleo/database/queries/perfis.py:613`, `:614`.

#### P-026 — agente_nw/nucleo/redacao.py:101 — `_escolher_fatos` e `_fatos`
- Classe: C e T
- O que é cortado e quanto: 40 fatos candidatos lidos do banco (`_FATOS_CANDIDATOS`), 10 no prompt (`_FATOS_NO_PROMPT`), dos quais 4 garantidos por recência; a escolha dos outros 6 é por cosseno sobre `f.conteudo[:600]` (l. 108) e cada fato entra no prompt com 600 caracteres (l. 146).
- Qual decisão do produto depende desse corte: a "peculiaridade" concreta que abre a mensagem base — o coração do produto (AGENTS §7).
- Commit que introduziu: `657edaa`
- Justificativa existente: o comentário da l. 41 ("o fato fica inteiro no banco; o prompt leva o começo") e a docstring de `_escolher_fatos`. Explicação, não aprovação.
- Proposta do executor: o teto de 10 fatos tem justificativa de janela (o prompt de redação é o maior do produto). O corte em 600 caracteres é o que eu questionaria: a peculiaridade útil costuma estar no meio de um post. Proponho um brief que troque "600 caracteres de 10 fatos" por "o que couber no orçamento de tokens, fato inteiro, priorizando os 4 recentes" — o orçamento do P-033 já existe para isso.
- Estado: AGUARDANDO DECISÃO DE SIDARTA
- Decisão de Sidarta: ____
- Onde mais aparece: `agente_nw/nucleo/redacao.py:108`, `:136`, `:146`; `agente_nw/nucleo/database/queries/fatos.py:34`.

#### P-027 — agente_nw/nucleo/termos_contato.py:60 — `termos_do_contato`
- Classe: C e T
- O que é cortado e quanto: 30 fatos lidos, 12 no prompt, cada um com 300 caracteres.
- Qual decisão do produto depende desse corte: os termos que o projeto busca no noticiário **sobre aquela pessoa** — isto é, que notícias passam a existir para ela.
- Commit que introduziu: `084fa34`
- Justificativa existente: nenhuma.
- Proposta do executor: o efeito é de alcance (o que não é buscado nunca vira gancho), mas a tarefa é "sobre que assuntos ela publica", e 12 publicações recentes respondem isso razoavelmente. Proponho manter o 12 e subir os 300 caracteres, pelo mesmo motivo do P-026: o assunto do post raramente está nos primeiros 300 caracteres de uma descrição de imagem. Custo baixo (`num_ctx` 4.096 nos dois perfis).
- Estado: AGUARDANDO DECISÃO DE SIDARTA
- Decisão de Sidarta: ____
- Onde mais aparece: `agente_nw/nucleo/termos_contato.py:76`.

#### P-028 — agente_nw/nucleo/historico.py:56 — o histórico que vai ao prompt
- Classe: T e C
- O que é cortado e quanto: a mensagem já entregue entra no histórico com **100 caracteres** (l. 56) e o comentário do usuário com **300** (l. 58); `historico_recente_para_prompt` lê as 5 consultas mais recentes (l. 10) e a redação usa 3 delas (`redacao.py:153-155`).
- Qual decisão do produto depende desse corte: o prompt `redigir_ganchos` recebe a ordem de "não repetir o que já foi usado" e de "retomar o fio" vendo 100 caracteres de cada mensagem anterior; e o comentário do usuário — a via de correção do brief 050 — chega cortado em 300.
- Commit que introduziu: `657edaa`
- Justificativa existente: nenhuma.
- Proposta do executor: o corte da mensagem em 100 caracteres é defensável (para saber que não deve repetir, o começo basta). O do comentário do usuário não: é texto que **você** escreveu para corrigir a redação, e é o único lugar do produto em que a sua palavra chega truncada ao modelo. Proponho corrigir o comentário (300 → inteiro, ou 1.200) e manter o resto. Custo: uma linha e um brief pequeno.
- Estado: AGUARDANDO DECISÃO DE SIDARTA
- Decisão de Sidarta: ____
- Onde mais aparece: `agente_nw/nucleo/historico.py:58`, `:10`; `agente_nw/nucleo/redacao.py:153`, `:155`; `agente_nw/nucleo/consulta.py:246`; `agente_nw/nucleo/database/queries/consulta_contato.py:54`.

#### P-029 — agente_nw/nucleo/redacao.py:162 — `_notas`
- Classe: T e C
- O que é cortado e quanto: as 5 notas mais recentes do contato (`_NOTAS_NO_PROMPT`), cada uma com 400 caracteres (`_TRECHO_DA_NOTA`).
- Qual decisão do produto depende desse corte: a redação. O prompt diz que a nota "vale como fato dito por ele" — é a sua palavra sobre a pessoa (brief 050).
- Commit que introduziu: `2c31eac`
- Justificativa existente: nenhuma.
- Proposta do executor: mesmo argumento do P-028, e aqui é mais forte: a nota é o canal pelo qual você conserta o que o programa entendeu errado. Proponho que a nota entre inteira e que `cortar_por_tamanho` continue protegendo-a (ele já protege: a nota é o único bloco que ele nunca remove). Custo: uma linha.
- Estado: AGUARDANDO DECISÃO DE SIDARTA
- Decisão de Sidarta: ____
- Onde mais aparece: `agente_nw/nucleo/database/queries/nota_contato.py:49`.

#### P-030 — agente_nw/nucleo/redacao.py:188 — `_moldes`
- Classe: T e C
- O que é cortado e quanto: no máximo 2 moldes (`moldes.maximo`) e, de cada um, o comentário do usuário entra com 300 caracteres.
- Qual decisão do produto depende desse corte: o prompt `redigir_ganchos` (o molde dá estrutura e tom, brief 048/065). O comentário é o que explica por que aquele molde funcionou.
- Commit que introduziu: `0bdd9be`
- Justificativa existente: o `moldes.maximo` está no YAML com comentário; o 300 do comentário não tem nenhuma.
- Proposta do executor: manter os 2 moldes (mais do que isso empurra o modelo a copiar) e corrigir o 300, junto com P-028 e P-029 — os três são a mesma decisão: "o que o usuário escreve não é cortado".
- Estado: AGUARDANDO DECISÃO DE SIDARTA
- Decisão de Sidarta: ____
- Onde mais aparece: `agente_nw/nucleo/database/queries/consulta_contato.py:123`; `config/limiares.yaml:77`.

#### P-031 — agente_nw/nucleo/redacao.py:69 — `_assunto_para_redacao`
- Classe: C e R
- O que é cortado e quanto: 3 itens por assunto (`_MANCHETES_POR_ASSUNTO`) e, desses, só a manchete ("veículo, data: título"). O corpo da notícia é carregado em `LinkNoticia.texto` (l. 78) e usado na tela, mas **não entra no prompt**: `_bloco_assuntos` (`prompts/redigir_ganchos.py:176-190`) usa título, `por_que`, resumo do cartão e manchetes.
- Qual decisão do produto depende desse corte: o texto da notícia que a mensagem leva ao contato. O modelo escreve "duas frases de notícia" a partir de título e resumo do cartão (que é o P-007).
- Commit que introduziu: `ea26737`
- Justificativa existente: sim, e desenhada: a regra do prompt manda escrever "só com o que está nas manchetes e no resumo; proibido inventar número, nome ou data". O corte é compensado por regra.
- Proposta do executor: aprovar, com uma ressalva que me parece importante: como o redator nunca vê o corpo, a qualidade do gancho é refém do cartão. Se você aprovar o P-007 como está, aprove este junto; se mandar melhorar o cartão, este melhora de graça.
- Estado: AGUARDANDO DECISÃO DE SIDARTA
- Decisão de Sidarta: ____

#### P-032 — agente_nw/nucleo/modelos/redacao.py:141 — `validar_ganchos`
- Classe: C
- O que é cortado e quanto: dos ganchos de notícia devolvidos pelo modelo, ficam `MAXIMO_GANCHOS` (4), além da mensagem base; o descarte não entra na lista de `motivos` mostrada ao usuário.
- Qual decisão do produto depende desse corte: quantos ganchos você recebe.
- Commit que introduziu: `8c8ce64`
- Justificativa existente: nenhuma escrita, mas o número é de produto (quantas opções cabem numa tela).
- Proposta do executor: aprovar o teto e pedir que o descarte apareça no aviso ("o modelo devolveu 6; mostro 4"). Custo: duas linhas, num brief qualquer da área.
- Estado: AGUARDANDO DECISÃO DE SIDARTA
- Decisão de Sidarta: ____

#### P-033 — agente_nw/nucleo/prompts/redigir_ganchos.py:287 — `cortar_por_tamanho`
- Classe: C (e é o único controle de janela do projeto)
- O que é cortado e quanto: se o prompt **estimado** (palavras × 1,4, l. 93) passa do orçamento, o histórico cai para 1 consulta e os fatos para 5 (l. 287); se ainda passar, saem os moldes; se ainda passar, sai a conversa do WhatsApp. O orçamento em produção é `0,73 × num_ctx` da tarefa (`cli.py:921` e `fluxo.py:364`), não os 6.000 do padrão.
- Qual decisão do produto depende desse corte: o prompt de redação — e, pela ordem de sacrifício, o que a mensagem deixa de saber quando o pedido é grande.
- Commit que introduziu: `ea26737`
- Justificativa existente: sim: a docstring da função, o comentário de `redacao.py:308` (quando o molde sai, a proveniência não é gravada) e a declaração de que a contagem é aproximada.
- Proposta do executor: aprovar o mecanismo — é o que impede o estouro de janela na única tarefa em que alguém olhou para isso — e pedir duas coisas num brief: que a estimativa de 1,4 token por palavra seja conferida contra o tokenizador real uma vez (um erro de 20% aqui é um prompt cortado em silêncio) e que a ordem de sacrifício fique documentada na ARQUITETURA, porque é decisão de produto: hoje o projeto prefere perder histórico e fatos a perder molde e tom.
- Estado: AGUARDANDO DECISÃO DE SIDARTA
- Decisão de Sidarta: ____
- Onde mais aparece: `agente_nw/nucleo/prompts/redigir_ganchos.py:294`, `:93`; `agente_nw/cli.py:921`; `agente_nw/nucleo/fluxo.py:364`; `agente_nw/console/app.py:164`.

### 3.e. O que o próprio usuário escreve

#### P-034 — agente_nw/nucleo/modelos/pedido.py:91 — validadores de `PedidoExtraido`
- Classe: C
- O que é cortado e quanto: um validador Pydantic corta `interessa`, `evitar` e `sobre_o_usuario` em **5** itens (l. 91) e `termos_busca` em **6** (l. 101), silenciosamente, no contrato.
- Qual decisão do produto depende desse corte: tudo o que depende dessas listas — e, no caso do `evitar`, a garantia que o usuário pediu: o sexto termo que ele mandou evitar **não é conferido** na mensagem nem no filtro de assunto (`candidatos.termo_evitado` recebe a lista já cortada).
- Commit que introduziu: `322341c`
- Justificativa existente: nenhuma.
- Proposta do executor: corrigir, pelo menos para o `evitar`. Cortar o que o usuário manda evitar é a falha mais difícil de defender desta auditoria: o programa promete não falar de X e pode falar de X porque X era o sexto item. O custo é baixo (o `evitar` não vai para prompt grande; é correspondência literal). Para `interessa` e `termos_busca` o teto é razoável, porque eles viram buscas e já há teto de buscas (P-005).
- Estado: AGUARDANDO DECISÃO DE SIDARTA
- Decisão de Sidarta: ____
- Onde mais aparece: `agente_nw/nucleo/modelos/pedido.py:101`.

#### P-035 — agente_nw/nucleo/pedido.py:39 — `extrair`
- Classe: C
- O que é cortado e quanto: o prompt `extrair_pedido` recebe os **50** contatos mais recentes (`_MAXIMO_CONTATOS_NO_PROMPT`, com `listar_contatos_recentes`).
- Qual decisão do produto depende desse corte: se o modelo reconhece a pessoa do pedido como um contato já conhecido. Fora dos 50, a pessoa é tratada como nova e um contato duplicado é criado — que depois precisa de `unir-contatos`.
- Commit que introduziu: `322341c`
- Justificativa existente: nenhuma.
- Proposta do executor: o teto tem motivo (uma agenda de 547 contatos não cabe no prompt), mas a consequência é visível para o usuário. Proponho um brief que, em vez do teto por recência, filtre os contatos por semelhança de nome com a frase antes de montar o prompt — `perfis.buscar_por_nome` já faz isso e é barato.
- Estado: AGUARDANDO DECISÃO DE SIDARTA
- Decisão de Sidarta: ____
- Onde mais aparece: `agente_nw/nucleo/database/queries/perfis.py:384`.

#### P-036 — agente_nw/perfil/inferencia.py:240 — `aplicar_declaracoes`
- Classe: R
- O que é cortado e quanto: cada frase que o modelo extraiu como "sobre o usuário" é lida por **três** expressões regulares (nome, negativa, positiva); frase que não casa com nenhuma é **ignorada em silêncio**.
- Qual decisão do produto depende desse corte: o perfil do usuário (brief 040) — os temas que passam a pesar em todo cruzamento. Uma autodeclaração escrita de outra forma não existe.
- Commit que introduziu: `ef532fc`
- Justificativa existente: a docstring diz "frase sem padrão reconhecido é ignorada" — declara o comportamento, não o justifica.
- Proposta do executor: manter como está, mas pedir que a frase ignorada apareça em algum lugar (log ou tela de "Eu"), para você perceber que o programa não entendeu. Corrigir de verdade (mandar a frase ao modelo em vez de regex) é um brief maior e muda o brief 040.
- Estado: AGUARDANDO DECISÃO DE SIDARTA
- Decisão de Sidarta: ____

#### P-037 — agente_nw/perfil/configurador.py:29 — embedding do tema
- Classe: R
- O que é cortado e quanto: o vetor do tema é o embedding de `"nome: descricao"` — os **sinônimos**, que acabaram de ser gravados na linha anterior, ficam fora do vetor. O mesmo padrão está em `console/app.py:947`.
- Qual decisão do produto depende desse corte: `aderencia_usuario` e o `ponto_de_apoio` de todo assunto: um assunto que casa com o sinônimo ("olaria") e não com o nome ("cerâmica") pontua menos do que deveria.
- Commit que introduziu: `21349f6`
- Justificativa existente: nenhuma.
- Proposta do executor: corrigir é uma linha (`f"{nome}: {descricao}. {', '.join(sinonimos)}"`), mas tem efeito de banco: todo centróide de tema já gravado passa a ser de outro texto, e o brief 066 trata vetor de outro critério como ausente. Proponho um brief pequeno que inclua regravar os vetores de tema.
- Estado: AGUARDANDO DECISÃO DE SIDARTA
- Decisão de Sidarta: ____
- Onde mais aparece: `agente_nw/console/app.py:947`.

#### P-038 — agente_nw/console/app.py:1005 — formulário de temas
- Classe: C
- O que é cortado e quanto: o formulário de configuração lê `range(20)` blocos de tema; o 21º tema que o usuário digitar é ignorado sem aviso.
- Qual decisão do produto depende desse corte: o perfil do usuário.
- Commit que introduziu: `21349f6`
- Justificativa existente: nenhuma.
- Proposta do executor: o formulário mostra 5 campos e não dá para digitar 21 na tela atual, então o risco prático é nulo hoje; é dívida de forma. Proponho aprovar e deixar registrado, ou corrigir de graça num brief que já toque o console.
- Estado: AGUARDANDO DECISÃO DE SIDARTA
- Decisão de Sidarta: ____

#### P-039 — agente_nw/nucleo/relevancia/cruzamento.py:407 — ponto de apoio da consulta
- Classe: C
- O que é cortado e quanto: dos interesses que o usuário declarou no pedido, só 5 (`_MAXIMO_INTERESSA_NO_APOIO`) viram termos embeddados para o ponto de apoio.
- Qual decisão do produto depende desse corte: qual termo aparece como "ponto de apoio" no `por_que`, e parte do `aderencia_consulta`.
- Commit que introduziu: `05eaf18`
- Justificativa existente: nenhuma.
- Proposta do executor: efeito pequeno e o `interessa` já vem cortado em 5 pelo contrato (P-034), então este teto é redundante hoje. Proponho tratar como consequência do P-034: resolvido lá, cai aqui.
- Estado: AGUARDANDO DECISÃO DE SIDARTA
- Decisão de Sidarta: ____

### 3.f. Janela do modelo — ninguém mede

#### P-040 — agente_nw/nucleo/llm.py:252 — `ClienteOllama._chamar`
- Classe: P
- O que é cortado e quanto: nada aqui corta texto; o que falta é a conferência. O cliente manda `num_ctx` no payload e o prompt inteiro, **sem medir o prompt**. Se o prompt passar do `num_ctx`, o Ollama trunca em silêncio (armadilha 1 do `docs/PLAN.md`) e o modelo responde sobre um texto cortado — sem erro, sem log, sem `fila_revisao`. Vale para 14 das 15 tarefas: a única com orçamento é `redigir_ganchos` (P-033).
- Qual decisão do produto depende desse corte: toda saída de LLM do produto. As entradas de maior risco são `extrair_de_texto` (`perfil/extrator.py:79`, que manda `item.texto` inteiro), `extrair_captura_rede_social` (P-019) e `extrair_pedido` (`nucleo/pedido.py:41`, a frase acumulada de correções mais 50 contatos).
- Commit que introduziu: `af2a09f` é o último toque nessas linhas (brief 077); a ausência de conferência vem do cliente original (brief E1_003) e nunca mudou.
- Justificativa existente: nenhuma. A armadilha 1 do PLAN documenta o risco desde o começo do projeto, o que torna a ausência mais difícil de defender, não mais fácil.
- Proposta do executor: corrigir, e é a correção de melhor relação custo/benefício desta auditoria: uma função no cliente que estime os tokens do prompt (o estimador de `redigir_ganchos` já existe) e, acima do `num_ctx` da tarefa, registre uma linha de aviso no `chamadas_llm.jsonl` e mande o item para `fila_revisao` em vez de deixar o modelo responder sobre um texto cortado. Um brief, um arquivo, nenhuma mudança de prompt.
- Estado: AGUARDANDO DECISÃO DE SIDARTA
- Decisão de Sidarta: ____
- Onde mais aparece: `agente_nw/perfil/extrator.py:79`; `agente_nw/coleta/capturas/extrator.py:66`; `agente_nw/nucleo/pedido.py:41`; `config/llm_routing.yaml:8`.

#### P-041 — agente_nw/nucleo/agrupamento/agrupador.py:89 — nenhuma medida antes de `embeddar`
- Classe: P
- O que é cortado e quanto: o `bge-m3` corta a entrada em silêncio acima de **8.192 tokens** e nada no projeto mede o texto antes de embeddar — nem no item (l. 89), nem no texto da consulta (`consulta.py:133`, que junta assunto, objetivo, interesses e a frase livre inteira), nem no centróide do contato (`perfis.py:630`, 20 fatos juntos).
- Qual decisão do produto depende desse corte: todos os vetores do produto, e portanto agrupamento, qualificação e relevância. Um texto de consulta longo (uma frase de pedido comprida, com correções acumuladas) pode ser vetorizado pela metade sem ninguém saber.
- Commit que introduziu: `06ba8e0`
- Justificativa existente: nenhuma.
- Proposta do executor: mesma correção do P-040, na outra ponta do cliente: medir antes de `embeddar` e avisar quando passar. Hoje, por ironia, os cortes T desta auditoria (P-001, P-025) são o que mantém os embeddings abaixo do limite — se você aprovar subir aqueles tetos, esta conferência passa a ser obrigatória antes.
- Estado: AGUARDANDO DECISÃO DE SIDARTA
- Decisão de Sidarta: ____
- Onde mais aparece: `agente_nw/nucleo/consulta.py:133`; `agente_nw/nucleo/database/queries/perfis.py:630`; `config/llm_routing.yaml:6`.

#### P-042 — agente_nw/nucleo/llm.py:249 — `num_predict` e a resposta cortada
- Classe: P (na saída)
- O que é cortado e quanto: `num_predict` por tarefa (256 a 2.048 tokens) limita a resposta, e nada confere se ela veio cortada (`done_reason == "length"` no Ollama, `stop_reason == "max_tokens"` na Anthropic, `finish_reason` nas outras). Uma resposta cortada no meio do JSON cai no caminho de "JSON inválido" e vira nova tentativa, mas uma resposta **válida e incompleta** (uma lista com menos itens, um cartão com duas linhas) é gravada como boa.
- Qual decisão do produto depende desse corte: o conteúdo gravado de qualquer tarefa com saída longa — cartão (1.024), `extrair_de_texto` (1.024) e `redigir_ganchos` (2.048) são as de maior risco.
- Commit que introduziu: `af2a09f` (último toque; os valores vêm do brief 064).
- Justificativa existente: o brief 064 introduziu `num_predict` como teto de saída deliberado; não há justificativa para não conferir o motivo da parada.
- Proposta do executor: corrigir junto com P-040 — ler o campo de motivo da parada e registrar/recusar. É o problema irmão do P-040 na saída, e a seção 7 lista o que cada provedor devolve.
- Estado: AGUARDANDO DECISÃO DE SIDARTA
- Decisão de Sidarta: ____
- Onde mais aparece: `config/llm_routing.yaml:9`.

### 3.g. Lotes e agenda

#### P-043 — agente_nw/nucleo/database/queries/fila_extracao.py:34 — lotes com retomada
- Classe: C
- O que é cortado e quanto: `LIMIT` no lote da fila de extração (l. 34), no lote do agrupamento (`itens.py:68`) e nas duas últimas execuções do feed (`fontes.py:70`).
- Qual decisão do produto depende desse corte: quanto é processado por rodada. Diferente dos outros pontos C, aqui **nada é descartado**: o que não entrou no lote continua pendente e entra no próximo (o AGENTS §6 exige idempotência e retomada).
- Commit que introduziu: `4a38842`
- Justificativa existente: sim, o AGENTS §6 ("idempotência e retomada") e o próprio desenho da fila.
- Proposta do executor: aprovar. É paginação de lote, não corte de análise — registro aqui só porque a varredura mecânica os encontra e o princípio pede que nada fique sem resposta.
- Estado: AGUARDANDO DECISÃO DE SIDARTA
- Decisão de Sidarta: ____
- Onde mais aparece: `agente_nw/nucleo/database/queries/itens.py:68`; `agente_nw/nucleo/database/queries/fontes.py:70`.

#### P-044 — agente_nw/perfil/agenda_google_csv.py:37 — importação da agenda
- Classe: C
- O que é cortado e quanto: da agenda, só o **primeiro** telefone e o **primeiro** e-mail de cada contato entram (`agenda_google_csv.py:37-40`, `agenda_macos.py:91-93`).
- Qual decisão do produto depende desse corte: o casamento do contato por telefone/e-mail (`obter_por_telefone_ou_email`): um contato que você tem pelo segundo número não é reconhecido e vira duplicata.
- Commit que introduziu: `aa0f235`
- Justificativa existente: nenhuma.
- Proposta do executor: é dado de identificação, não texto analisado, mas o efeito (contato duplicado) é real. Proponho aprovar como está e lembrar que `unir-contatos` existe para isso; corrigir pede coluna nova e migração.
- Estado: AGUARDANDO DECISÃO DE SIDARTA
- Decisão de Sidarta: ____
- Onde mais aparece: `agente_nw/perfil/agenda_macos.py:91`.

#### P-045 — agente_nw/nucleo/database/queries/listas.py:75 — busca na lista pelo primeiro nome
- Classe: R
- O que é cortado e quanto: a busca de uma pessoa na lista da rede usa só o **primeiro nome** (`split()[:1]`, l. 75); em `perfis.py:453` o primeiro nome precisa bater por inteiro e o sobrenome só por prefixo.
- Qual decisão do produto depende desse corte: quais candidatos aparecem para você confirmar. Uma pessoa cadastrada na rede só pelo sobrenome não é encontrada.
- Commit que introduziu: `7fd4c59`
- Justificativa existente: a docstring de `buscar_por_nome` explica a regra ("O primeiro nome precisa bater por inteiro"); é desenho declarado.
- Proposta do executor: aprovar. É heurística de nome, com confirmação humana depois, e afrouxá-la aumenta o número de homônimos que você tem de resolver — que é o custo que o brief 037 tentou reduzir.
- Estado: AGUARDANDO DECISÃO DE SIDARTA
- Decisão de Sidarta: ____
- Onde mais aparece: `agente_nw/nucleo/database/queries/perfis.py:453`.
---

## 4. Cortes que não analisam texto (apresentação, log, identificador)

Sete cortes que a varredura encontra e que **não** alimentam análise nenhuma. Cada um vem com a prova.
Você pode contestar qualquer linha desta seção: contestada, ela vira ponto da seção 3.

#### NA-001 — agente_nw/cli.py:1068 — fatia de data de um ISO 8601
- Classe: NA
- O que é cortado e quanto: `[:10]` (o dia) e `[:7]` (o mês) sobre uma data ISO 8601, em 10 lugares.
- Prova de que não entra em decisão: o valor cortado é uma data, não um texto de conteúdo: `agora[:10]` é o dia da consulta (`consulta.py:212`, `cruzamento.py:201`, `:336`), `criado_em[:10]` é a data mostrada no histórico (`historico.py:64`, `redacao.py:70`, `:139`), `fromisoformat(data[:10])` é a conversão para `date` (`redacao.py:120`, `inferencia.py:269`) e `enviada_em[:7]` é a chave `AAAA-MM` do agrupamento por mês (`conversa.py:92`). Em nenhum deles existe texto depois do caractere 10 que importe: o resto é a hora.
- Onde mais aparece: `agente_nw/nucleo/consulta.py:212`; `agente_nw/nucleo/relevancia/cruzamento.py:201`, `:336`; `agente_nw/nucleo/redacao.py:70`, `:120`, `:139`; `agente_nw/nucleo/historico.py:64`; `agente_nw/perfil/inferencia.py:269`; `agente_nw/nucleo/database/queries/conversa.py:92`.

#### NA-002 — agente_nw/coleta/capturas/busca.py:140 — trecho da página na mensagem de erro
- Classe: NA
- O que é cortado e quanto: 120 caracteres (busca) e 160 (lista vazia) do texto da página, para a frase de aviso.
- Prova de que não entra em decisão: os dois valores só entram em `motivo`, que é string de mensagem para o usuário (`ResultadoBusca.motivo` e `ResultadoAtualizacao.motivo`); nenhum deles é gravado como fato, embeddado ou mandado a prompt. O texto completo da página continua disponível no mesmo fluxo pelo `estado()`.
- Onde mais aparece: `agente_nw/nucleo/localizacao.py:197`.

#### NA-003 — agente_nw/cli.py:501 — listagens de tela
- Classe: NA
- O que é cortado e quanto: tetos de linhas em listagens: 20/50 contatos na tela inicial (`console/app.py:248`, `perfis.py:411`), 20 entradas por página da lista de rede (`app.py:316`), 15 fatos na ficha (`app.py:409`), filtro do `--filtro` na impressão (`cli.py:1010`), filtro de `descartado` no `print` do menu (`cli.py:501`) e os `LIMIT` de listagem de pedidos (`pedidos.py:153`).
- Prova de que não entra em decisão: nenhuma dessas funções alimenta prompt, embedding, deduplicação ou filtro de assunto — a saída de cada uma vai para `print` ou para um template HTML. O caminho analítico usa outras consultas (`fatos.listar_recentes` para o prompt, `listar_qualificados_nao_vistos` para o cruzamento), auditadas em P-009 e P-026.
- Onde mais aparece: `agente_nw/cli.py:1010`; `agente_nw/console/app.py:248`, `:316`, `:409`; `agente_nw/nucleo/database/queries/pedidos.py:153`; `agente_nw/nucleo/database/queries/perfis.py:411`.

#### NA-004 — agente_nw/nucleo/saidas/markdown.py:34 — exportação em Markdown
- Classe: NA
- O que é cortado e quanto: o arquivo exportado mostra título, "por quê" e cartão de cada assunto, não o corpo das notícias.
- Prova de que não entra em decisão: é saída final para leitura humana; a releitura do arquivo (`ler_marcacoes`) procura só as marcações `[x]` e os ids, nunca o texto. Nada do que o Markdown mostra ou esconde volta ao banco ou a um prompt.

#### NA-005 — agente_nw/nucleo/database/migracoes.py:21 — número da migração
- Classe: NA
- O que é cortado e quanto: `caminho.name.split("_", 1)[0]` — o prefixo numérico do nome do arquivo de migração.
- Prova de que não entra em decisão: é identificador de ordenação de migração; o conteúdo do `.sql` é lido e executado inteiro (`caminho.read_text()`).

#### NA-006 — scripts/agente_entregar.sh:115 — cortes nos scripts de entrega
- Classe: NA
- O que é cortado e quanto: `tail -n 5`/`tail -n 3` da saída do gate, `${linha:3}` do nome do manifesto, `relatorios[0]`/`inicios[-1]` em `agente_lacunas.py`, `git log -3` em `commitar.sh`, `head -n 15`/`tail -n 1` em `verificar.sh`.
- Prova de que não entra em decisão do produto: são cortes da saída de terminal do fluxo de entrega (o que aparece para o executor e para você no console da entrega). Nenhum deles toca texto de notícia, de rede social, de conversa ou de pedido; o gate decide por código de saída, não pelo texto cortado.
- Onde mais aparece: `scripts/agente_lacunas.py:104`; `scripts/commitar.sh:83`; `scripts/verificar.sh:40`.

#### NA-007 — agente_nw/nucleo/database/queries/conversa.py:64 — blocos do WhatsApp repartem, não cortam
- Classe: NA
- O que é cortado e quanto: `_em_blocos` reparte as mensagens do mês em blocos de até `maximo_caracteres_bloco` (6.000).
- Prova de que não entra em decisão: nenhuma mensagem é descartada — o laço fecha um bloco e começa outro, e **todos** os blocos do mês são enfileirados (`importador.py:56-58`), um por chamada de LLM. É fatiamento com cobertura total, o oposto de truncamento. A única consequência é que o modelo vê cada bloco isolado, sem o contexto dos outros — registrado na seção 7.
- Onde mais aparece: `config/limiares.yaml:72`; `agente_nw/nucleo/modelos/configuracao.py:276`.

---

## 5. Rastreio ponta a ponta e conferência de janela

### 5.a. Por origem de texto: onde o texto é cortado, da entrada até cada consumidor

**Notícia (RSS → Google News ou Bing News).** Feed → `trafilatura.extract` traz o corpo **inteiro**
(`rss/leitor.py:338`) → gravado **inteiro** em `item.texto` (`:354`). Dedup antes do corpo, por hash do
título (**P-002**); item sem corpo é gravado só com título (**P-003**); corpo curto é descartado
(**P-003**); marca de patrocinado procurada em 3 linhas (**P-004**). Consumidores: embedding do item
recebe `titulo + texto[:2000]` (**P-001**, **P-041**); `rotular`/`qualificar` recebem título e domínio de
5 itens (**P-006**); `cartao` recebe título, domínio e 300 caracteres de 5 itens (**P-007**);
`prerotular_calibracao` recebe 2.000 caracteres de uma amostra de pares (**P-008**); o gate
`avaliar_relacao_objetivo` recebe título e resumo do cartão (**P-010**); `cruzar_por_que` recebe só o
título (**P-011**); o filtro de `evitar` procura em título e resumo (**P-012**); e o redator recebe 3
manchetes e o resumo do cartão — **nunca o corpo** (**P-031**). Em nenhum consumidor o corpo integral
chega ao modelo.

**Página de rede social (extensão do Chrome).** `innerText` da aba → cortado em 200.000 caracteres
dentro do navegador (**P-013**) → blocos por linha em branco, só os de 30 a 5.000 caracteres sobrevivem
(**P-014**) → examinados `maximo_blocos × 4`, gravados `maximo_blocos` (**P-016**) → cada bloco vai
**inteiro** ao prompt `extrair_captura_rede_social`, sem conferência de janela (**P-019**, **P-040**) →
o fato grava o **bloco integral** (`capturas/leitor.py:155`), não a saída do modelo. Quanto da página é
lido depende das rolagens e dos orçamentos de tempo (**P-015**). Imagens: até 8, largura ≥ 250 px
(**P-017**), e cada uma vira 2-5 frases (**P-018**), nunca é gravada.

**Lista de conexões/seguidos.** Cartão de cada pessoa → nome na linha 0, descrição nas linhas 1-4
(**P-020**) → cabeçalho de 3 linhas gravado → o desempate por LLM vê só o cabeçalho (**P-020**);
candidatas limitadas a 5 (**P-021**); leitura da lista limitada por entradas, rodadas e tempo
(**P-015**).

**Conversa do WhatsApp (arquivo que você envia).** `.zip` → um `.txt` (**P-024**) → mensagens; mídia e
apagadas descartadas (**P-024**) → cada mensagem gravada **inteira** (`conversa.py:inserir_mensagem`) →
extração por mês, só os 24 mais recentes (**P-022**), cada mês repartido em blocos que cobrem tudo
(**NA-007**) → prompt `extrair_de_texto` recebe o bloco inteiro, sem conferência de janela
(**P-040**). Na redação, só as 10 últimas trocas, para o tom (**P-023**).

**Fatos e perfil do contato.** Fato gravado **inteiro**, sempre (nenhum ponto corta a gravação).
Consumidores: centróide do contato = 20 fatos × 500 caracteres (**P-025**, **P-041**); prompt de
redação = 10 de 40 fatos × 600 caracteres, escolhidos por embedding do mesmo recorte (**P-026**);
termos de busca = 12 de 30 fatos × 300 caracteres (**P-027**).

**Histórico, notas e comentários (texto seu).** Nota gravada inteira; comentário gravado inteiro.
Consumidores: histórico no prompt = 3 a 5 consultas, mensagem em 100 caracteres e comentário em 300
(**P-028**); notas = 5 × 400 caracteres (**P-029**); comentário do molde = 300 caracteres (**P-030**).
Sob aperto de janela, histórico e fatos são os primeiros a sair (**P-033**).

**Pedido em texto livre (texto seu).** Frase gravada **inteira** (`pedidos.inserir`) e mandada
**inteira** ao prompt `extrair_pedido`, sem conferência de janela (**P-040**), junto com 50 contatos
(**P-035**). A saída do modelo é cortada pelo contrato: `interessa`, `evitar` e `sobre_o_usuario` em 5,
`termos_busca` em 6 (**P-034**). O texto da consulta é embeddado inteiro, sem medida (**P-041**).
Declaração sobre você mesmo fora dos três padrões é ignorada (**P-036**).

### 5.b. Conferência de janela, por chamada de LLM e de embedding

`num_ctx` do perfil `air16` / `pro48`. "Maior texto possível" vem do código e do `limiares.yaml`, nunca
do banco real. A conversão usada é conservadora: 1 token ≈ 3,5 caracteres de português.

| Chamada | Maior texto possível que chega | num_ctx (air16 / pro48) | Conferência de tamanho existe? | Classe |
|---|---|---|---|---|
| `extrair_de_texto` (nota, bloco de rede, bloco de WhatsApp) | bloco de WhatsApp de 6.000 caracteres (`whatsapp.maximo_caracteres_bloco`) ≈ 1.700 tokens, mais 450 de instrução | 4.096 / 16.384 | **não** | P (P-040) |
| `extrair_captura_rede_social` | bloco de 5.000 caracteres (`navegador.py:22`) ≈ 1.400 tokens, mais 300 | 4.096 / 16.384 | **não** | P (P-019, P-040) |
| `extrair_pedido` | frase do pedido sem teto (acumula correções) + 50 contatos ≈ 800 tokens de lista | 4.096 / 8.192 | **não** | P (P-035, P-040) |
| `qualificar` | 5 títulos + temas conhecidos ≈ 300 tokens, mais 700 de instrução e exemplos | 2.048 / 8.192 | não (mas o corte de P-006 mantém a entrada pequena) | P |
| `rotular` | 5 títulos ≈ 150 tokens | 2.048 / 8.192 | não (idem) | P |
| `cartao` | 5 × (título + 300 caracteres) ≈ 600 tokens, mais 500 | 4.096 / 16.384 | não (idem, P-007) | P |
| `cruzar_por_que` | 5 títulos + temas + contexto ≈ 400 tokens | 4.096 / 16.384 | não | P |
| `avaliar_relacao_objetivo` | 10 × (título + resumo do cartão) ≈ 900 tokens | 4.096 / 16.384 | não | P |
| `desempatar_perfil` | 5 cabeçalhos de 3 linhas ≈ 150 tokens | 2.048 / 2.048 | não | P |
| `redigir_ganchos` | tudo (fatos, histórico, notas, moldes, WhatsApp, 5 assuntos) | 8.192 / 16.384 | **sim** — `cortar_por_tamanho` contra `0,73 × num_ctx`, por estimativa de palavras × 1,4 | C (P-033) |
| `extrair_termos_contato` | 12 × 300 caracteres ≈ 1.100 tokens | 4.096 / 4.096 | não (o corte de P-027 mantém pequeno) | P |
| `descrever_tema` | um termo curto | 2.048 / 2.048 | não | P |
| `descrever_imagem` | uma imagem + texto alternativo | 4.096 / 4.096 | não (o custo é a imagem, não o texto) | P |
| `prerotular_calibracao` | 2 × (título + 2.000 caracteres) ≈ 1.300 tokens | 2.048 / 8.192 | não — **no `air16` esta é a chamada mais perto do teto** | P (P-008) |
| embedding do item (`agrupador.py:89`) | título + 2.000 caracteres ≈ 600 tokens | limite do `bge-m3`: 8.192 | **não** | P (P-041) |
| embedding da consulta (`consulta.py:133`) | assunto + objetivo + interesses + frase livre, **sem teto** | 8.192 | **não** | P (P-041) |
| embedding do centróide do contato (`perfis.py:630`) | 20 × 500 caracteres ≈ 2.900 tokens | 8.192 | **não** | P (P-025, P-041) |
| embedding de seleção de fato (`redacao.py:108`) | 30 × 600 caracteres, um por vetor ≈ 170 cada | 8.192 | não (cada texto é pequeno) | P |
| embedding do tema (`configurador.py:29`) | nome + descrição ≈ 20 tokens | 8.192 | não | P (P-037) |

Leitura da tabela: nenhuma chamada de hoje está estourando a janela por folga grande, e **é por isso
que os cortes T desta auditoria existem** — eles seguram a entrada. A exceção é
`prerotular_calibracao` no `air16`: 2 × 2.000 caracteres mais instrução e dois exemplos resolvidos
chegam perto de 2.048 tokens, e o `calibrar-agrupamento` é justamente o comando que grava um limiar no
YAML. Essa é a chamada que eu mediria primeiro se você aprovar o P-040.
---

## 6. Certificação por arquivo

Os 317 arquivos do universo, um por linha, na ordem do caminho. `Linhas lidas/total` foi conferido
com `wc -l` pelo verificador, arquivo por arquivo. A coluna `Ponto` cita os pontos das seções 3 e 4.

| Arquivo | Linhas lidas/total | Resultado | Evidência (uma linha) | Ponto |
|---|---|---|---|---|
| agente_nw/__init__.py | 0/0 | CERTIFICADO | Arquivo vazio (0 bytes de conteúdo): não manipula texto de conteúdo, só marca o pacote. | — |
| agente_nw/cli.py | 1494/1494 | CORTA | Entrega ao núcleo a frase do pedido inteira (`orquestracao.entender_pedido(..., frase, ...)`, l. 860-873) e o texto do arquivo de temas inteiro, mas dois parâmetros que ela mesma calcula limitam o que o núcleo analisa: o teto diário de qualificação (l. 442) e o orçamento de tokens do prompt de redação (l. 921). | P-009, P-033, NA-001, NA-003 |
| agente_nw/coleta/__init__.py | 0/0 | CERTIFICADO | arquivo vazio: não manipula texto de conteúdo (só marca o pacote) | — |
| agente_nw/coleta/capturas/__init__.py | 0/0 | CERTIFICADO | arquivo vazio: não manipula texto de conteúdo (só marca o pacote) | — |
| agente_nw/coleta/capturas/busca.py | 151/151 | CORTA | o texto do cartão de cada candidato da busca da rede vira `nome_exibido` + 4 linhas de descrição; o resto do cartão é descartado antes de o candidato ser ordenado e mostrado | P-020, NA-002 |
| agente_nw/coleta/capturas/extensao_backend.py | 181/181 | CORTA | o texto da página capturada é cortado em `maximo_caracteres_pagina` duas vezes: no pedido à extensão (l. 88) e no recorte local da resposta (l. 93) | P-013 |
| agente_nw/coleta/capturas/extrator.py | 73/73 | CORTA | o bloco capturado vai inteiro ao prompt (bom), mas sem nenhuma conferência de janela, e o que é gravado é o "texto essencial" que o modelo devolve, não o bloco | P-019, P-040 |
| agente_nw/coleta/capturas/imagens.py | 68/68 | CORTA | a imagem inteira (base64) vai ao modelo de visão, mas o prompt limita a descrição a "2 a 5 frases" e essa descrição é tudo o que sobra da imagem a jusante | P-018 |
| agente_nw/coleta/capturas/leitor.py | 170/170 | CORTA | grava o bloco integral como fato (`conteudo=bloco`, l. 155, com o comentário "texto de fonte externa não se altera"), mas examina só `maximo_blocos × 4` blocos da página e para ao gravar `maximo_blocos` | P-016 |
| agente_nw/coleta/capturas/listas.py | 408/408 | CORTA | de cada cartão da lista ficam o nome e até 3 linhas de cabeçalho; a lista inteira é lida só até `maximo_entradas` / 3 rodadas sem novidade | P-015, P-020 |
| agente_nw/coleta/capturas/navegador.py | 149/149 | CORTA | blocos fora da faixa 30–5.000 caracteres são jogados fora inteiros, a página é lida só em 5 rolagens e as imagens param no `maximo` | P-014, P-015, P-017 |
| agente_nw/coleta/rss/__init__.py | 0/0 | CERTIFICADO | arquivo vazio: não manipula texto de conteúdo (só marca o pacote) | — |
| agente_nw/coleta/rss/canonicalizar.py | 59/59 | CORTA | `url_canonica` só normaliza URL (não é corte de conteúdo), mas `hash_titulo` resolve a deduplicação olhando apenas o título da notícia | P-002 |
| agente_nw/coleta/rss/fonte_alternativa.py | 41/41 | CERTIFICADO | só monta a URL do RSS do Bing e desembrulha o redirecionador (`parse_qs(...)["url"]`): nenhum texto de notícia passa por aqui | — |
| agente_nw/coleta/rss/google_news.py | 86/86 | CORTA | os termos de busca que definem o que será coletado são cortados em quatro lugares (4 por tema, 3 do contato, 6 de `termos_busca`, 5 de `interessa`, e `[:maximo]` no fim) | P-005 |
| agente_nw/coleta/rss/leitor.py | 365/365 | CORTA | o corpo da notícia é extraído inteiro por `trafilatura` e gravado inteiro, mas a deduplicação decide pelo hash do título, item sem corpo é gravado só com título, e o feed/pedido para em três limites diferentes | P-002, P-003, P-005 |
| agente_nw/coleta/rss/ruido.py | 71/71 | CORTA | decide ruído pelo tamanho do corpo inteiro (l. 51) mas procura a marca de patrocinado só nas 3 primeiras linhas (l. 57) | P-003, P-004 |
| agente_nw/coleta/whatsapp/__init__.py | 0/0 | CERTIFICADO | arquivo vazio: não manipula texto de conteúdo (só marca o pacote) | — |
| agente_nw/coleta/whatsapp/importador.py | 60/60 | CORTA | grava todas as mensagens da conversa inteiras, mas só enfileira para extração os `meses_extraidos` meses mais recentes | P-022 |
| agente_nw/coleta/whatsapp/leitor.py | 118/118 | CORTA | reconstrói mensagens de várias linhas sem perder nada, mas lê só um `.txt` do zip e descarta por substring a mensagem que contenha marca de mídia/apagada | P-024 |
| agente_nw/console/__init__.py | 0/0 | CERTIFICADO | Arquivo vazio (0 bytes): não manipula texto de conteúdo, só marca o pacote. | — |
| agente_nw/console/app.py | 1043/1043 | CORTA | O texto do pedido, a nota, o comentário e o `.txt`/`.zip` do WhatsApp vão inteiros ao núcleo (`fluxo_mod.criar_pedido`, `fila_extracao.inserir`, `whatsapp_leitor.ler_arquivo(arquivo.filename, dados)`), mas: o envio de WhatsApp acima de 20 MB é recusado (l. 465), o formulário de temas só lê 20 blocos (l. 1005), o embedding do tema deixa os sinônimos de fora (l. 947) e o `num_ctx` repassado ao fluxo é o que vira o orçamento de 73% do prompt (l. 164). | P-024, P-033, P-037, P-038, NA-003 |
| agente_nw/integracoes/__init__.py | 0/0 | CERTIFICADO | Arquivo vazio (0 bytes): só marca o pacote; não manipula texto de conteúdo. | — |
| agente_nw/nucleo/__init__.py | 0/0 | CERTIFICADO | arquivo vazio: não manipula texto de conteúdo (só marca o pacote) | — |
| agente_nw/nucleo/agrupamento/__init__.py | 0/0 | CERTIFICADO | arquivo vazio de pacote | — |
| agente_nw/nucleo/agrupamento/agrupador.py | 286/286 | CORTA | o vetor que decide assunto/republicação/divisão vem de `titulo + texto[:2000]` | P-001, P-041 |
| agente_nw/nucleo/agrupamento/calibracao.py | 268/268 | CORTA | prompt `prerotular_calibracao` recebe `texto[:2000]` de cada item do par; a amostra é 35 pares da banda + 15 de controle, sorteados | P-008 |
| agente_nw/nucleo/agrupamento/divisao.py | 50/50 | CERTIFICADO | não manipula texto de conteúdo: divide um assunto só por cosseno entre vetores já gravados | — |
| agente_nw/nucleo/confirmacao.py | 196/196 | CORTA | diálogo de confirmação no terminal; a paginação da lista ("Enter = mais") não perde nada, mas o menu de candidatos mostra só os 5 primeiros | P-021 |
| agente_nw/nucleo/consulta.py | 268/268 | CORTA | orquestra a consulta: o texto do pedido é embeddado sem conferir a janela do `bge-m3`, e os tetos de blocos/imagens, de qualificação e de histórico entram daqui | P-005, P-009, P-016, P-028, P-041, NA-001 |
| agente_nw/nucleo/database/__init__.py | 0/0 | CERTIFICADO | Arquivo vazio (0 bytes): só marca o pacote. | — |
| agente_nw/nucleo/database/backup.py | 55/55 | CERTIFICADO | Não manipula texto de conteúdo: só infraestrutura (cópia do arquivo .db, retenção de 7 dias de arquivos de backup, `arquivos[-1]` escolhe o backup mais recente — arquivo, não texto). | — |
| agente_nw/nucleo/database/conexao.py | 26/26 | CERTIFICADO | Não manipula texto de conteúdo: só infraestrutura (abre o SQLite, carrega `sqlite_vec`, PRAGMAs). | — |
| agente_nw/nucleo/database/migracoes.py | 48/48 | NÃO ANALÍTICO | Só infraestrutura de esquema; o único corte é o número da migração extraído do nome do arquivo. | NA-005 |
| agente_nw/nucleo/database/queries/__init__.py | 0/0 | CERTIFICADO | Arquivo vazio (0 bytes): só marca o pacote. | — |
| agente_nw/nucleo/database/queries/assunto_contato.py | 150/150 | CERTIFICADO | Grava e lê linhas de cruzamento inteiras (`por_que`, `motivo` sem corte); nenhum LIMIT nem slice em consulta nenhuma. | — |
| agente_nw/nucleo/database/queries/assuntos.py | 257/257 | CORTA | Grava título/justificativa/resumo e centróides inteiros, mas dois seletores decidem **quais** assuntos o modelo vê. | P-009 |
| agente_nw/nucleo/database/queries/consulta_contato.py | 124/124 | CORTA | Grava `contexto_json`/`resumo_redes_sociais` inteiros; corta o histórico de consultas e as mensagens-molde que alimentam o prompt de redação. | P-028, P-030 |
| agente_nw/nucleo/database/queries/conversa.py | 98/98 | CORTA | guarda a mensagem inteira e reparte o mês em blocos sem perder nada (`_em_blocos`), mas devolve só os `meses_extraidos` meses mais recentes (l. 97) e as `limite` últimas trocas (l. 46) | P-022, P-023, NA-001, NA-007 |
| agente_nw/nucleo/database/queries/fatos.py | 56/56 | CORTA | `inserir` grava `conteudo` inteiro; `listar_recentes` escolhe só os N fatos mais recentes que vão ao prompt e aos termos de busca. | P-026 |
| agente_nw/nucleo/database/queries/fila_extracao.py | 66/66 | CORTA | Enfileira e devolve `texto` inteiro (nenhum corte de caractere); o lote de pendentes é limitado por `LIMIT`. | P-043 |
| agente_nw/nucleo/database/queries/fila_revisao.py | 15/15 | CERTIFICADO | Só INSERT de tarefa/entrada/erro, gravados por inteiro; nenhuma leitura, nenhum limite. | — |
| agente_nw/nucleo/database/queries/fontes.py | 75/75 | CORTA | Cadastro de feeds, sem texto de conteúdo; único corte de coleção é o `LIMIT 2` da regra "dois dias vazios". | P-043 |
| agente_nw/nucleo/database/queries/gancho_uso.py | 107/107 | CERTIFICADO | Grava e lê `gancho_json` e `comentario` inteiros (só `.strip()`, que não é corte de conteúdo); nenhum LIMIT. | — |
| agente_nw/nucleo/database/queries/itens.py | 104/104 | CORTA | Grava `titulo`/`texto` inteiros e lê todos os itens de um assunto; o lote do agrupador é limitado por `LIMIT`. | P-043 |
| agente_nw/nucleo/database/queries/listas.py | 138/138 | CORTA | Grava nome/cabeçalho inteiros; a busca por nome usa só o primeiro nome e as "parecidas" são cortadas em `maximo`. | P-021, P-045 |
| agente_nw/nucleo/database/queries/nota_contato.py | 59/59 | CORTA | Grava `texto` da nota inteiro; a leitura por perfil aceita `limite`, usado para o prompt de redação. | P-029 |
| agente_nw/nucleo/database/queries/pedidos.py | 191/191 | NÃO ANALÍTICO | Grava `texto` do pedido e os JSON inteiros; os três `LIMIT` servem a listagens de tela (duas sem chamador em produção hoje). | NA-003 |
| agente_nw/nucleo/database/queries/perfil_tema.py | 170/170 | CERTIFICADO | Vínculos tema↔perfil e embeddings inteiros; a escolha "confirmadas, ou todas se não houver confirmada" é filtro por status, não corte de conjunto; nenhum LIMIT. | — |
| agente_nw/nucleo/database/queries/perfis.py | 657/657 | CORTA | o centróide do contato, que pontua toda a relevância, vem de 20 fatos cortados em 500 caracteres (l. 613-630); o resto do arquivo grava e lê a ficha inteira | P-025, P-035, P-041, P-045, NA-003 |
| agente_nw/nucleo/database/queries/rede_sem_perfil.py | 30/30 | CERTIFICADO | Não manipula texto de conteúdo: marca/desmarca "sem perfil" por rede; itera `REDES_SUPORTADAS` inteira. | — |
| agente_nw/nucleo/database/queries/redes_sociais.py | 42/42 | CERTIFICADO | Só links de rede do contato, gravados e lidos inteiros, sem limite. | — |
| agente_nw/nucleo/database/queries/sistema.py | 63/63 | CERTIFICADO | Não manipula texto de conteúdo: versão de esquema, progresso, bloqueio por host e termo buscado (chave = prefixo + valor inteiro). | — |
| agente_nw/nucleo/database/queries/temas.py | 105/105 | CERTIFICADO | Nome, descrição e sinônimos gravados e lidos inteiros; `listar_com_embedding` devolve **todos** os temas com vetor do modelo atual. | — |
| agente_nw/nucleo/fluxo.py | 482/482 | CORTA | fluxo do pedido (status, perguntas, retomada); não lê texto de conteúdo, mas é aqui que nasce o orçamento de prompt `num_ctx * 0,73` que corta o prompt da redação | P-033 |
| agente_nw/nucleo/historico.py | 85/85 | CORTA | o histórico que vai ao prompt `redigir_ganchos` leva a mensagem cortada em 100 caracteres e o comentário do usuário em 300, e só as 5 consultas mais recentes | P-028, NA-001 |
| agente_nw/nucleo/llm.py | 632/632 | CORTA | repassa `num_ctx` e `num_predict` da tarefa ao provedor (l. 240-251, 365, 473, 560) sem medir o prompt nem conferir se a resposta veio cortada; o texto do prompt chega e sai inteiro | P-040, P-042 |
| agente_nw/nucleo/localizacao.py | 412/412 | CORTA | localiza a pessoa nas redes; o desempate por LLM vê só o `cabecalho` de cada candidata, os parecidos param em `maximo_parecidas` e a deduplicação do fato olha 200 fatos | P-020, P-021, NA-002 |
| agente_nw/nucleo/modelos/__init__.py | 0/0 | CERTIFICADO | Arquivo vazio (0 bytes): só marca o pacote. | — |
| agente_nw/nucleo/modelos/assunto.py | 24/24 | CERTIFICADO | Contrato frozen; `titulo_gerado`, `justificativa` e `resumo_cartao` sem limite de tamanho. | — |
| agente_nw/nucleo/modelos/assunto_contato.py | 26/26 | CERTIFICADO | Contrato Pydantic frozen de campos escalares e textos livres, sem validador que corte. | — |
| agente_nw/nucleo/modelos/calibracao.py | 9/9 | CERTIFICADO | Contrato de resposta booleana da comparação de par; nenhum texto. | — |
| agente_nw/nucleo/modelos/cartao.py | 9/9 | CERTIFICADO | Contrato de um campo `resumo: str`, sem validador que corte. | — |
| agente_nw/nucleo/modelos/configuracao.py | 383/383 | CORTA | É onde moram os tetos do produto: tamanho de página e de bloco de texto, blocos/imagens por rede, meses de conversa, trocas no prompt, moldes, candidatos e tetos por dia. | P-013, NA-007 |
| agente_nw/nucleo/modelos/consulta_contato.py | 14/14 | CERTIFICADO | Contrato frozen; guarda os JSON de contexto e o resumo como texto, sem limite. | — |
| agente_nw/nucleo/modelos/contexto_consulta.py | 30/30 | CERTIFICADO | Contrato frozen do contexto do pedido; listas sem corte **neste** arquivo (o corte está em `modelos/pedido.py`). | — |
| agente_nw/nucleo/modelos/cruzamento.py | 26/26 | CERTIFICADO | Contratos de resposta (`por_que`, `avaliacoes`) sem limite de itens nem de tamanho. | — |
| agente_nw/nucleo/modelos/extracao.py | 50/50 | CERTIFICADO | Contrato de `extrair_de_texto`: campos, tags e fatos em listas sem corte; `trecho` e `conteudo` sem limite. | — |
| agente_nw/nucleo/modelos/fato.py | 15/15 | CERTIFICADO | Contrato frozen; `conteudo` é `str` sem limite. | — |
| agente_nw/nucleo/modelos/fila.py | 26/26 | CERTIFICADO | Contratos das duas filas; `texto`/`entrada` sem limite. | — |
| agente_nw/nucleo/modelos/fonte.py | 15/15 | CERTIFICADO | Contrato de cadastro de feed; não manipula texto de conteúdo. | — |
| agente_nw/nucleo/modelos/item.py | 17/17 | CERTIFICADO | Contrato frozen; `titulo` e `texto` sem limite de tamanho. | — |
| agente_nw/nucleo/modelos/lista_rede_social.py | 21/21 | CERTIFICADO | Contrato de entrada de lista (nome, cabeçalho, link) sem corte. | — |
| agente_nw/nucleo/modelos/localizacao.py | 41/41 | CERTIFICADO | `Localizacao.opcoes` é declarada "todas, da mais para a menos provável" (linha 28); nenhum corte aqui. | — |
| agente_nw/nucleo/modelos/marcacao.py | 15/15 | CERTIFICADO | Contrato da marcação do usuário; `motivo` sem limite. | — |
| agente_nw/nucleo/modelos/pedido.py | 116/116 | CORTA | Dois `field_validator` cortam listas vindas do pedido do usuário antes de qualquer análise (5 itens; 6 termos de busca). | P-034 |
| agente_nw/nucleo/modelos/perfil.py | 35/35 | CERTIFICADO | contrato Pydantic do perfil: campos de texto (`notas`, `formacao`, `cargo`…) sem limite de tamanho e sem validador que corte | — |
| agente_nw/nucleo/modelos/perfil_tema.py | 23/23 | CERTIFICADO | Contrato do vínculo tema↔perfil; nenhum texto de conteúdo. | — |
| agente_nw/nucleo/modelos/proveniencia.py | 23/23 | CERTIFICADO | Só metadado de quem gerou a linha; não manipula texto de conteúdo. | — |
| agente_nw/nucleo/modelos/qualificacao.py | 12/12 | CERTIFICADO | Contrato da qualificação; `temas` e `justificativa` sem corte. | — |
| agente_nw/nucleo/modelos/redacao.py | 141/141 | CORTA | `validar_ganchos` lê a mensagem inteira (termos de evitar, contagem de palavras), mas entrega no máximo `MAXIMO_GANCHOS` ganchos de notícia. | P-032 |
| agente_nw/nucleo/modelos/rede_social.py | 13/13 | CERTIFICADO | Contrato de link de rede; nenhum texto de conteúdo. | — |
| agente_nw/nucleo/modelos/rotulo.py | 9/9 | CERTIFICADO | Contrato de um campo `titulo: str`, sem validador que corte. | — |
| agente_nw/nucleo/modelos/tema.py | 23/23 | CERTIFICADO | Contratos de tema e de `descrever_tema`; descrição e sinônimos sem corte. | — |
| agente_nw/nucleo/orquestracao.py | 218/218 | CORTA | só encadeia os passos e repassa parâmetros; dois desses parâmetros são cortes do prompt da redação (trocas de WhatsApp e moldes) | P-023, P-030 |
| agente_nw/nucleo/pedido.py | 251/251 | CORTA | a frase do pedido vai inteira ao prompt de `extrair_pedido`, mas acompanhada de só 50 contatos e sem conferência de janela | P-035, P-040 |
| agente_nw/nucleo/prompts/__init__.py | 28/28 | CERTIFICADO | não manipula texto de conteúdo: só confere que todo módulo de prompt declara `VERSAO` | — |
| agente_nw/nucleo/prompts/avaliar_relacao_objetivo.py | 66/66 | CERTIFICADO | monta o prompt do gate com os pares (título, resumo) que recebe, cada um cercado por inteiro; não corta nada (quem escolhe o que entra é `cruzamento.py`, ponto P-010) | — |
| agente_nw/nucleo/prompts/cartao.py | 68/68 | CERTIFICADO | monta o prompt com os trios (título, domínio, trecho) que recebe, cada um cercado por inteiro; o trecho de 300 caracteres é cortado em `cartoes.py` (P-004) | — |
| agente_nw/nucleo/prompts/cruzar_por_que.py | 100/100 | CERTIFICADO | monta o prompt com os títulos e temas que recebe, cercados por inteiro; a representação reduzida vem de `cruzamento.py` (P-011) | — |
| agente_nw/nucleo/prompts/descrever_tema.py | 32/32 | CERTIFICADO | monta o prompt com o termo inteiro; pede descrição de 10 a 20 palavras, que é saída do modelo, não corte de entrada | — |
| agente_nw/nucleo/prompts/desempatar_perfil.py | 62/62 | CERTIFICADO | monta o prompt com os cabeçalhos que recebe, cercados por inteiro; o recorte ao cabeçalho vem de `localizacao.py` (P-020) | — |
| agente_nw/nucleo/prompts/exemplos_conversavel.yaml | 22/22 | CERTIFICADO | dado de prompt: 20 frases de exemplo de conversável/não conversável; nenhum limite de quantidade ou tamanho de texto analisado | — |
| agente_nw/nucleo/prompts/extrair_de_texto.py | 85/85 | CERTIFICADO | põe o texto recebido inteiro no prompt, cercado (`cercar_dado_externo(texto)`, l. 84); nenhum corte | — |
| agente_nw/nucleo/prompts/extrair_pedido.py | 91/91 | CERTIFICADO | põe a frase do usuário inteira no prompt (l. 89) e a lista de contatos que recebe; o teto de 50 contatos é de `pedido.py` (P-035) | — |
| agente_nw/nucleo/prompts/prerotular_calibracao.py | 63/63 | CERTIFICADO | monta o prompt com os dois títulos e os dois trechos que recebe, cercados por inteiro; o trecho de 2.000 caracteres é cortado em `calibracao.py` (P-008) | — |
| agente_nw/nucleo/prompts/qualificar.py | 81/81 | CERTIFICADO | monta o prompt com os pares (título, domínio) que recebe, cada título cercado por inteiro; o texto do item já não existe aqui (P-002/P-006) | — |
| agente_nw/nucleo/prompts/redigir_ganchos.py | 298/298 | CORTA | `cortar_por_tamanho` é o único estimador de tamanho de prompt do projeto (palavras × 1,4 contra 6.000 tokens) e corta histórico para 1, fatos para 5, depois moldes, depois WhatsApp | P-033 |
| agente_nw/nucleo/prompts/rotular.py | 40/40 | CERTIFICADO | monta o prompt com os pares (título, domínio) que recebe, cercados por inteiro; nenhum corte próprio | — |
| agente_nw/nucleo/prompts/seguranca.py | 40/40 | CERTIFICADO | cerca o texto de terceiro por inteiro e só neutraliza marcador forjado trocando `<` e `>` por espaço — nenhum caractere é removido | — |
| agente_nw/nucleo/redacao.py | 365/365 | CORTA | monta a entrada de `redigir_ganchos`: fatos (10 de 40, 600 caracteres cada), notas do usuário (5, 400 caracteres), histórico (3 consultas), moldes (comentário 300), WhatsApp (10 trocas), manchetes (3 por assunto, só título) | P-023, P-026, P-028, P-029, P-030, P-031, NA-001 |
| agente_nw/nucleo/relevancia/__init__.py | 0/0 | CERTIFICADO | arquivo vazio: só marca o pacote | — |
| agente_nw/nucleo/relevancia/candidatos.py | 83/83 | CORTA | a seleção ranqueia por cosseno e fica com `candidatos_por_contato`; `termo_evitado` casa o termo só em título + resumo do cartão | P-009, P-012 |
| agente_nw/nucleo/relevancia/cartoes.py | 102/102 | CORTA | prompt `cartao` recebe (título, domínio, 300 primeiros caracteres) dos 5 itens mais recentes | P-007 |
| agente_nw/nucleo/relevancia/cruzamento.py | 530/530 | CORTA | o gate `avaliar_relacao_objetivo` e o `cruzar_por_que` recebem só título e resumo do cartão; o menu fica com `itens_no_menu` dos candidatos; `interessa` do pedido entra cortado em 5 no ponto de apoio | P-009, P-010, P-011, P-039, NA-001 |
| agente_nw/nucleo/relevancia/pontuacao.py | 153/153 | CERTIFICADO | não manipula texto: pontua só por cosseno entre vetores já gravados | — |
| agente_nw/nucleo/relevancia/qualificador.py | 109/109 | CORTA | `_itens_recentes_resumidos` manda ao LLM só (título, domínio) dos 5 itens mais recentes do assunto; o texto do item nunca entra nos prompts `rotular` e `qualificar` | P-006 |
| agente_nw/nucleo/saidas/__init__.py | 0/0 | CERTIFICADO | arquivo vazio: não manipula texto de conteúdo (só marca o pacote) | — |
| agente_nw/nucleo/saidas/markdown.py | 112/112 | NÃO ANALÍTICO | gera o menu em Markdown (título + "por quê" + cartão) e relê só as marcações `[x]`/motivos; nenhum texto de conteúdo é analisado aqui | NA-004 |
| agente_nw/nucleo/termos_contato.py | 76/76 | CORTA | prompt `extrair_termos_contato` recebe 12 dos 30 fatos lidos, cada um cortado em 300 caracteres | P-027 |
| agente_nw/nucleo/texto.py | 61/61 | CERTIFICADO | funções de nome próprio: `casa_nome` e `similaridade_nome` usam todas as palavras das duas cadeias (`_palavras` não descarta nada) e `variantes_do_nome` acrescenta variantes sem remover o nome completo | — |
| agente_nw/nucleo/vetores.py | 31/31 | CERTIFICADO | não manipula texto de conteúdo: só infraestrutura numérica (cosseno e centróide ponderado sobre vetores já prontos) | — |
| agente_nw/perfil/__init__.py | 0/0 | CERTIFICADO | Arquivo vazio (0 bytes): só marca o pacote. | — |
| agente_nw/perfil/agenda_google_csv.py | 46/46 | CORTA | `notas` do CSV vai inteira para `ContatoBruto`, mas só o primeiro telefone/e-mail/organização (coluna "1") e só a primeira coluna que casa o prefixo. | P-044 |
| agente_nw/perfil/agenda_macos.py | 107/107 | CORTA | A nota do contato é lida inteira (`str(completo.note())`), mas só o primeiro telefone e o primeiro e-mail entram no `ContatoBruto`. | P-044 |
| agente_nw/perfil/configurador.py | 73/73 | CORTA | O texto do tema vai inteiro ao embedding: `embeddar([f"{tema.nome}: {tema.descricao}"])[0]` — o `[0]` é o único resultado do lote de um item, não corte. | P-037 |
| agente_nw/perfil/extrator.py | 124/124 | CORTA | manda `item.texto` inteiro ao prompt `extrair_de_texto` (l. 79-81) — e é justamente por isso que nada confere se ele cabe no `num_ctx` da tarefa | P-040 |
| agente_nw/perfil/importador.py | 111/111 | CERTIFICADO | `bruto.notas` entra inteira na fila de extração (linha 106) e todos os `marcadores` são percorridos; o contato sem telefone nem e-mail é ignorado (filtro de identidade, não de texto). | — |
| agente_nw/perfil/inferencia.py | 283/283 | CORTA | Percorre todos os termos do pedido e todos os temas com embedding, mas cada frase de `sobre_o_usuario` só é lida por três expressões regulares e, sem padrão, é descartada. | P-036, NA-001 |
| agente_nw/perfil/lacunas.py | 25/25 | CERTIFICADO | Percorre `ORDEM_IMPACTO` inteira e devolve todos os campos vazios; não manipula texto de conteúdo. | — |
| agente_nw/perfil/normalizacao.py | 18/18 | CERTIFICADO | Normaliza telefone para E.164 com `phonenumbers`; não há corte de texto de conteúdo. | — |
| agente_nw/ponte/__init__.py | 84/84 | CERTIFICADO | Não manipula texto de conteúdo: só infraestrutura (monta o comando que abre a URL da ponte no Chrome e guarda a ponte única do processo). | — |
| agente_nw/ponte/servidor.py | 282/282 | CERTIFICADO | O corpo do `POST /resultado` é lido por inteiro pelo `Content-Length` (`self.rfile.read(tamanho)`, l. 129-131) e o `dict` de `dados` é devolvido ao chamador sem tocar em nada dentro dele: não há limite de bytes de corpo, nem limite de leitura de socket, nem teto de número de blocos, nem recorte de texto em lugar nenhum do arquivo. | — |
| config/__init__.py | 0/0 | CERTIFICADO | arquivo vazio (0 bytes de conteúdo): não manipula texto de conteúdo. | — |
| config/container.py | 196/196 | CERTIFICADO | não manipula texto de conteúdo: só infraestrutura (carrega YAML, resolve caminhos, escolhe provedor de LLM e abre o banco); nenhum `[:N]`, nenhum truncamento, nenhuma seleção de item de texto. | — |
| config/limiares.yaml | 84/84 | CORTA | arquivo de limites: 24 chaves de quantidade/tamanho/janela, consumidas por coleta, leitura de rede social, WhatsApp, agrupamento, qualificação, cruzamento e redação. | P-005, P-009, P-013, P-015, P-016, P-017, P-021, P-022, P-023, P-030, NA-007 |
| config/llm_routing.yaml | 47/47 | CORTA | declara `num_ctx`/`num_predict` por tarefa nos dois perfis e `bge-m3` para embeddings; só `redigir_ganchos` tem orçamento de prompt no código — as outras 12 tarefas e o embedding não conferem se o texto cabe. | P-040, P-041, P-042 |
| config/local.exemplo.yaml | 26/26 | CERTIFICADO | não manipula texto de conteúdo: caminhos, `ollama_url` e bloco `ia_api` comentado; nenhuma chave de tamanho, janela ou quantidade. | — |
| config/local.yaml | 10/10 | CERTIFICADO | não manipula texto de conteúdo: caminhos, `ollama_url` (11435), usuários de rede; `perfil_llm: pro48` só escolhe qual coluna da tabela de `num_ctx` (§3) vale nesta máquina. | — |
| extensao/background.js | 188/188 | CORTA | é o canal por onde o texto e as imagens da página saem do navegador: repassa `maximo` de caracteres ao `conteudo.js`, repassa `maximo`/`largura_minima` de imagens e descarta imagem por host, por 6 MB e por falha de download. | P-013, P-017 |
| extensao/conteudo.js | 203/203 | CORTA | corta o `innerText` da página no `maximo` recebido (l. 199), limita imagens por `maximo`/`largura_minima` (l. 181-195) e a leitura da lista por orçamento de tempo e de páginas (l. 108, 130) | P-013, P-015, P-017 |
| extensao/manifest.json | 44/44 | CERTIFICADO | não manipula texto de conteúdo: manifesto MV3 (permissões, service worker, `externally_connectable`); `host_permissions` é escopo de origem, não corte de texto — é a origem do descarte listado em A4-032. | — |
| extensao/ponte_conteudo.js | 18/18 | CERTIFICADO | repassa a tarefa e a resposta inteiras entre a página-ponte e a extensão (`sendMessage`/`postMessage`), sem ler, cortar ou reescrever campo nenhum. | — |
| scripts/agente_entregar.sh | 136/136 | NÃO ANALÍTICO | ferramenta de entrega (manifesto, gate, commit, push); os únicos cortes são de log na tela (`tail -n 5`, `tail -n 3`) e o descarte do prefixo de 3 caracteres do `git status --porcelain`. | NA-006 |
| scripts/agente_lacunas.py | 133/133 | NÃO ANALÍTICO | copia a tabela `## Lacunas` do relatório para o PLAN; corta só coleções de documentação (primeiro relatório do glob, última seção `## Lacunas`), nada vai a LLM, embedding ou filtro do produto. | NA-006 |
| scripts/commitar.sh | 83/83 | NÃO ANALÍTICO | `git add` arquivo por arquivo e `git commit -F`; o único corte é `git log --oneline -3`, saída de tela. | NA-006 |
| scripts/instalar_macos.sh | 40/40 | CERTIFICADO | não manipula texto de conteúdo: `brew install`, `ollama pull`, venv, `mkdir`; nenhum texto de conteúdo passa por aqui. | — |
| scripts/migracoes/001_inicial.sql | 160/160 | CERTIFICADO | todas as colunas de conteúdo são `TEXT` sem limite (`item.texto`, `fato.conteudo`, `fila_extracao.texto`, `assunto.justificativa`, `tema.descricao`); os `CHECK` são enumerações (`tipo`, `status`, `origem`) e faixas numéricas (`peso`, `confiabilidade`), nunca `length(...)`; sem view e sem `LIMIT`. | — |
| scripts/migracoes/002_coleta_historico.sql | 9/9 | CERTIFICADO | só contagem por fonte e data (`n_itens_novos INTEGER`); nenhuma coluna de texto de conteúdo. | — |
| scripts/migracoes/003_rede_social.sql | 11/11 | CERTIFICADO | `rede` e `link` são `TEXT` sem limite; nenhum `CHECK (length(...))`, nenhum truncamento. | — |
| scripts/migracoes/004_consulta_contato.sql | 18/18 | CERTIFICADO | `contexto_json`, `resumo_redes_sociais` e `assuntos_entregues_json` são `TEXT` sem limite; gatilhos só impedem UPDATE/DELETE. | — |
| scripts/migracoes/005_perfil_id_reatribuivel.sql | 19/19 | CERTIFICADO | só recria gatilhos `BEFORE UPDATE OF <colunas>`; não cria, apaga nem encurta coluna de texto. | — |
| scripts/migracoes/006_aderencia_consulta.sql | 7/7 | CERTIFICADO | acrescenta `aderencia_consulta REAL`; nenhum texto envolvido. | — |
| scripts/migracoes/007_pedido.sql | 17/17 | CERTIFICADO | `pedido.texto TEXT NOT NULL` guarda a frase do usuário por inteiro, antes de qualquer etapa; `extraido_json TEXT` sem limite. | — |
| scripts/migracoes/008_listas.sql | 20/20 | CERTIFICADO | `nome`, `nome_normalizado`, `cabecalho`, `link` são `TEXT` sem limite; `nome_normalizado` é chave de busca adicional, não substitui `nome`. | — |
| scripts/migracoes/009_gancho_uso.sql | 18/18 | CERTIFICADO | `gancho_json TEXT NOT NULL` guarda o gancho inteiro (o comentário da linha 3 diz isso); `CHECK` só na enumeração de `status`. | — |
| scripts/migracoes/010_rede_sem_perfil.sql | 12/12 | CERTIFICADO | tabela de decisão (perfil, rede, data); nenhuma coluna de texto de conteúdo. | — |
| scripts/migracoes/011_pedido_fluxo.sql | 17/17 | CERTIFICADO | sete `ADD COLUMN` (`status`, `etapa`, `erro`, `avisos_json`, `localizacao_json`, ids); `CHECK` só na enumeração de `status`. | — |
| scripts/migracoes/012_pedido_fonte_noticias.sql | 7/7 | CERTIFICADO | duas colunas `TEXT` de procedência/validade; nenhum limite. | — |
| scripts/migracoes/013_gancho_uso_sem_assunto.sql | 25/25 | CERTIFICADO | reconstrução da tabela com `SELECT` de todas as 6 colunas para todas as linhas (`SELECT id, consulta_id, assunto_id, status, gancho_json, atualizado_em FROM gancho_uso`), sem `WHERE` e sem `LIMIT`. | — |
| scripts/migracoes/014_comentarios.sql | 17/17 | CERTIFICADO | `gancho_uso.comentario TEXT` e `nota_contato.texto TEXT` sem limite; o único `CHECK (length(trim(texto)) > 0)` exige texto não vazio — é piso, não teto. | — |
| scripts/migracoes/015_conversa_whatsapp.sql | 18/18 | CERTIFICADO | `conversa_mensagem.texto TEXT NOT NULL` sem limite; `UNIQUE (perfil_id, hash)` deduplica por mensagem, e o `hash` é coluna própria (o texto guardado não é encurtado). | — |
| scripts/migracoes/016_perfil_genero_gramatical.sql | 9/9 | CERTIFICADO | uma coluna de enumeração (`masculino`/`feminino`/`desconhecido`); nenhum texto de conteúdo. | — |
| scripts/migracoes/017_preferencias_usuario_temas.sql | 25/25 | CERTIFICADO | `preferencias_json TEXT` sem limite, `peso_decaido_em TEXT` (mês) e tabela `tema_uso` de contagem; nenhum truncamento. | — |
| scripts/migracoes/018_molde_rastreio.sql | 9/9 | CERTIFICADO | uma coluna de id (`molde_origem_id`); nenhum texto. | — |
| scripts/migracoes/019_proveniencia.sql | 63/63 | CERTIFICADO | 15 colunas de proveniência `TEXT NULL` e recriação das três tabelas vec0 copiando **todas** as linhas e vetores (`SELECT ... FROM _copia_*`, sem `WHERE`/`LIMIT`), com backfill `'bge-m3'`. | — |
| scripts/verificar.sh | 65/65 | NÃO ANALÍTICO | o gate (ruff, format, mypy, pytest); a saída completa vai para `logs/verificar_ultimo.txt` e só a tela é encurtada (`head -n 15`, `tail -n 1`). | NA-006 |
| scripts/verificar_auditoria_texto.py | 414/414 | CERTIFICADO | não manipula texto de conteúdo: enumera o universo, lê o relatório desta auditoria e varre o código em busca de padrões de corte | — |
| tests/__init__.py | 0/0 | CERTIFICADO | Arquivo vazio. | — |
| tests/coleta_falsa.py | 117/117 | CERTIFICADO | Rede falsa (Google/Bing/RSS); página de notícia de ~840 caracteres ("Texto relevante..." x20) e títulos curtos: nunca exerce um texto longo. | — |
| tests/llm_falso.py | 30/30 | CERTIFICADO | Proveniência falsa e parsers do prompt (divide candidatos/assuntos numerados); sem manipular texto de conteúdo. | — |
| tests/test_agente_entregar.py | 174/174 | CERTIFICADO | Testa o script de entrega (git falso, gate falso); só infraestrutura. | — |
| tests/test_agente_lacunas.py | 186/186 | CERTIFICADO | Testa o script que copia lacunas do relatório para o PLAN; texto de documento passa inteiro. | — |
| tests/test_agrupador.py | 272/272 | CERTIFICADO | Itens com `texto=None` e título de 6 a 12 caracteres; embedder falso indexado pelo próprio título; não prova o que é embeddado de um texto real. | — |
| tests/test_ambiente.py | 17/17 | CERTIFICADO | Carrega a extensão sqlite_vec; só infraestrutura. | — |
| tests/test_assunto_contato.py | 124/124 | CERTIFICADO | CRUD e filtros de `assunto_contato`; sem texto de conteúdo. | — |
| tests/test_assunto_contato_marcacao.py | 96/96 | CERTIFICADO | Marcar usado/nao_serve em `assunto_contato`; sem texto de conteúdo. | — |
| tests/test_assuntos.py | 138/138 | CERTIFICADO | CRUD de `assunto`, janela de candidatos, fechar inativos; filtros por data/n_itens, sem corte de texto. | — |
| tests/test_assuntos_qualificacao.py | 166/166 | CERTIFICADO | Consultas de candidatos à qualificação; o teste da linha 95 afirma `LIMIT` (3 criados, 2 devolvidos). | — |
| tests/test_assuntos_sem_cartao.py | 62/62 | CERTIFICADO | `listar_qualificados_sem_cartao`; a linha 52 afirma limite (5 criados, 3 devolvidos). | — |
| tests/test_backup.py | 83/83 | CERTIFICADO | Backup/restauração/retenção de 7 dias de arquivos .db; só infraestrutura. | — |
| tests/test_base_mais_ganchos.py | 46/46 | CERTIFICADO | Ordem base + ganchos na redação, LLM falso devolve gancho montado; não inspeciona o prompt. | — |
| tests/test_calibracao.py | 212/212 | CERTIFICADO | Amostragem de pares para calibrar o limiar (controle alvo 15, banda teto 35, `random.Random`); itens só com título. | — |
| tests/test_candidatos.py | 111/111 | CERTIFICADO | `selecionar` por aderência; `test_respeita_limite` (linha 103) afirma 3 de 5. | — |
| tests/test_candidatos_por_consulta.py | 119/119 | CERTIFICADO | `selecionar_por_consulta`; a linha 117 afirma corte em 10 de 12 candidatos não evitados. | — |
| tests/test_canonicalizar.py | 71/71 | CERTIFICADO | URL canônica e `hash_titulo` com títulos de 40 a 50 caracteres; normalização, sem corte. | — |
| tests/test_capturas_busca.py | 208/208 | CERTIFICADO | Filtra candidatos de busca em rede social (nome, descrição, link); descrições de 1 a 3 linhas curtas. | — |
| tests/test_capturas_extrator.py | 66/66 | CERTIFICADO | `extrair` com bloco curto de uma linha e cliente falso que ignora o prompt. | — |
| tests/test_capturas_leitor.py | 429/429 | CERTIFICADO | Leitor de redes; linhas 223-253 afirmam `maximo_blocos` (6 blocos, só 3 chamadas ao LLM), 363-405 `maximo_imagens`; linha 284 prova que o fato guarda o texto integral do bloco. | — |
| tests/test_capturas_navegador.py | 205/205 | CERTIFICADO | Leitura de página com rolagem; linhas 164-190 afirmam `maximo_imagens=3` e `max_rolagens`; blocos curtos. | — |
| tests/test_cartoes.py | 125/125 | CERTIFICADO | `gerar_cartao`; um item só, `texto` de 41 caracteres, LLM falso que ignora o prompt. | — |
| tests/test_cartoes_pendentes.py | 118/118 | CERTIFICADO | `gerar_pendentes`; linha 110 afirma limite (3 criados, 2 candidatos); item de 41 caracteres e LLM falso que ignora o prompt. | — |
| tests/test_cli_agenda.py | 66/66 | CERTIFICADO | Comandos `ficha` e `confirmar-tags`; sem texto de conteúdo. | — |
| tests/test_cli_agrupamento.py | 116/116 | CERTIFICADO | CLI agrupar/calibrar sem itens; só casos vazios. | — |
| tests/test_cli_certificar.py | 103/103 | CERTIFICADO | Comando `certificar` sobre contagens e log JSONL; sem texto de conteúdo. | — |
| tests/test_cli_cruzamento.py | 119/119 | CERTIFICADO | CLI `menu` e `cruzar` sem dados; só casos vazios. | — |
| tests/test_cli_markdown.py | 140/140 | CERTIFICADO | Exportar menu .md e ler marcações; títulos de 6 caracteres. | — |
| tests/test_cli_pedir.py | 93/93 | CERTIFICADO | `pedir` imprime o pedido extraído; frase de pedido curta. | — |
| tests/test_cli_pedir_confirmacao.py | 417/417 | CERTIFICADO | Menu de confirmação de perfil nas listas de rede; cabeçalhos curtos ("Sócio, escritório tributarista"); `maximo_entradas=2000` só em fixture de config. | — |
| tests/test_cli_pedir_redacao.py | 175/175 | CERTIFICADO | `pedir` com redação; item sem `texto` e LLM falso devolve gancho pronto. | — |
| tests/test_cli_qualificacao.py | 157/157 | CERTIFICADO | CLI qualificar/cartão; item com `texto` de 17 caracteres e LLM falso que ignora o prompt. | — |
| tests/test_cli_servidor_na_porta.py | 32/32 | CERTIFICADO | Classifica processo/porta do Ollama; só infraestrutura. | — |
| tests/test_coleta_bloqueio.py | 163/163 | CERTIFICADO | Coleta com bloqueio 503; linhas 118-163 afirmam `maximo_itens_novos_por_feed=4` (feed com 6, 4 processados); página de ~840 caracteres. | — |
| tests/test_coleta_cooldown.py | 94/94 | CERTIFICADO | Cooldown de host no banco; fluxo de rede, não de texto. | — |
| tests/test_coleta_degradacao.py | 67/67 | CERTIFICADO | Google/Bing bloqueados: coleta termina sem erro e sem notícia. | — |
| tests/test_coleta_fonte_alternativa.py | 77/77 | CERTIFICADO | Bing News RSS; linha 56 usa notícia de 30 dias para exercitar o filtro de ruído por idade. | — |
| tests/test_coleta_fumaca.py | 79/79 | CERTIFICADO | Fumaça com rede real (`rede_real`, fora do gate); conta itens, não olha texto. | — |
| tests/test_coleta_retomada.py | 98/98 | CERTIFICADO | Retomada de ciclo por sentinela; página de ~840 caracteres. | — |
| tests/test_coleta_reuso_termo.py | 65/65 | CERTIFICADO | Reuso de termo buscado há pouco; normaliza o termo (caixa/acento/espaços). | — |
| tests/test_coleta_rotulo_fonte.py | 95/95 | CERTIFICADO | Rótulo da fonte de notícias na tela e no terminal; texto de apresentação. | — |
| tests/test_coleta_teto_consultas.py | 44/44 | CERTIFICADO | Linhas 10-24 afirmam teto de 4 termos de busca; linhas 27-44 afirmam parada de buscas com `candidatos_suficientes`. | — |
| tests/test_comentario_mensagem.py | 52/52 | CERTIFICADO | Persistência de comentário por gancho (aparado, vazio apaga); comentários de poucas palavras. | — |
| tests/test_comentario_no_prompt.py | 53/53 | CERTIFICADO | Linha 43 afirma que só as notas mais recentes (5 de 7) entram no prompt da redação. | — |
| tests/test_comentario_sob_orcamento.py | 24/24 | CERTIFICADO | Linha 9 afirma que o prompt perto de 6.000 tokens corta o histórico mas mantém nota e comentário. | — |
| tests/test_concorrencia.py | 40/40 | CERTIFICADO | Leitura SQLite durante escrita; só infraestrutura. | — |
| tests/test_configuracao.py | 210/210 | CERTIFICADO | Valida YAMLs de config; linhas 143-155 afirmam valores de corte de `config/limiares.yaml`. | — |
| tests/test_configurador.py | 114/114 | CERTIFICADO | Salvar/adicionar/remover tema do usuário; embedder falso não inspeciona o texto embeddado. | — |
| tests/test_console_apagar_unir.py | 210/210 | CERTIFICADO | Rotas Flask de apagar/unir contato; LLM falso devolve resposta vazia. | — |
| tests/test_console_busca_rede_social.py | 243/243 | CERTIFICADO | Rotas de busca de candidatos em rede; `estado` devolve "x"*1000 só para passar o mínimo de login. | — |
| tests/test_console_configurar_perfil.py | 235/235 | CERTIFICADO | Rotas de perfil/temas; descrição mínima de 8 palavras validada, embedder falso. | — |
| tests/test_console_contatos.py | 214/214 | CERTIFICADO | Rotas de contatos/fichas/texto; texto de uma frase vai à fila de extração com LLM falso vazio. | — |
| tests/test_console_editar_ficha.py | 227/227 | CERTIFICADO | Exercita rota de edição de ficha (campos curtos, E.164, línguas); LLM fake devolve `esquema()` vazio, sem texto de conteúdo analisado. | — |
| tests/test_console_eu.py | 176/176 | CERTIFICADO | Exercita tela /eu (temas por nível, contar, esquecer); LLM fake devolve `PedidoExtraido` fixo com 1 declaração curta. | — |
| tests/test_console_mensagem_base.py | 87/87 | CERTIFICADO | Exercita mensagem base/usei/comentário/nota no console; `redigir` é trocado por mock que devolve só a base já pronta (não exercita o prompt). | — |
| tests/test_console_menu.py | 212/212 | CERTIFICADO | Exercita telas de menu; cada contato tem 1 só assunto, então `itens_no_menu=5` e `candidatos_por_contato=10` do limiar nunca aparecem. | — |
| tests/test_console_novo_contato.py | 155/155 | CERTIFICADO | Exercita criação/listagem de contato; só infraestrutura e `_limiares()` compartilhado. | — |
| tests/test_console_preparar.py | 122/122 | CERTIFICADO | Exercita GET do formulário preparar (404 e meios); nenhum texto de conteúdo. | — |
| tests/test_console_redes_sociais.py | 222/222 | CERTIFICADO | Exercita CRUD de links de rede social (valida só prefixo http); sem análise de texto. | — |
| tests/test_console_sem_usuario.py | 141/141 | CERTIFICADO | Exercita /temas e /eu sem/com usuário; só infraestrutura. | — |
| tests/test_console_tela_unica.py | 273/273 | CERTIFICADO | Exercita tela única (pedir, pessoa, usei, corrigir); fluxo todo com `Cenario` (preparar/redigir/localizar mockados); texto do pedido curto ("Falar com a Marta sobre vela"). | — |
| tests/test_console_temas.py | 172/172 | CERTIFICADO | Exercita CRUD de temas; embedding fake constante `[0.1]+0*1023` — não prova que o embedding recebe descrição inteira. | — |
| tests/test_consulta_contato_queries.py | 105/105 | CERTIFICADO | Exercita queries de `consulta_contato`; documenta o parâmetro `limite` (ver bloco de cortes). | — |
| tests/test_consulta_preparar.py | 385/385 | CERTIFICADO | Exercita `consulta.preparar` com TODAS as etapas mockadas (rss, extrator, agrupador, qualificador, leitor, cruzamento); documenta o teto de termos de busca (ver bloco). | — |
| tests/test_contato_divergente.py | 269/269 | CERTIFICADO | Exercita divergência nome do pedido x contato; LLM fake devolve `PedidoExtraido` pronto (a extração do texto da frase nem roda). | — |
| tests/test_cruzamento.py | 240/240 | CERTIFICADO | Exercita `cruzar_contato`; assuntos só com título + centróide injetado; LLM fake devolve respostas prontas por posição. | — |
| tests/test_cruzamento_por_consulta.py | 328/328 | CERTIFICADO | Exercita cruzamento por consulta; ESCONDE: assuntos criados só com `titulo_gerado` (sem resumo/itens), centróides injetados e embedder fake decide por `"fato" in texto`. | — |
| tests/test_cruzar_por_que_nao_atribui.py | 62/62 | CERTIFICADO | Exercita prompt `cruzar_por_que` (regra de não atribuir posição); títulos curtos, não há texto de notícia no prompt. | — |
| tests/test_divisao.py | 37/37 | CERTIFICADO | Exercita `dividir` de agrupamento com vetores 2D; sem texto. | — |
| tests/test_evitar_implicito.py | 174/174 | CERTIFICADO | Exercita "não me interessa" virando evitar; casa só pelo TÍTULO do assunto ("Política fiscal..."); assunto sem corpo. | — |
| tests/test_extensao_backend.py | 207/207 | CERTIFICADO | Exercita `PaginaExtensao`; DOCUMENTA corte do texto da página em `maximo_caracteres_pagina` e `maximo_entradas`/`maximo` de imagens (ver bloco). | — |
| tests/test_extensao_manifest.py | 79/79 | CERTIFICADO | Confere manifest.json e background.js da extensão; só infraestrutura. | — |
| tests/test_extrator.py | 91/91 | CERTIFICADO | Teste `llm_real` do extrator com texto de ~230 caracteres (cabe em qualquer corte); não testa texto longo. | — |
| tests/test_fluxo.py | 353/353 | CERTIFICADO | Exercita fluxo/fila do pedido; `Cenario` troca preparar/redigir/localizar por mocks; `pessoas_recentes(conn, 20)` documenta limite (ver bloco); `num_ctx_redacao=8192` passado no Dependencias sem teste de tamanho do prompt. | — |
| tests/test_gancho_uso.py | 91/91 | CERTIFICADO | Exercita `gancho_uso` (entregue/usado); `gancho_json` é `"{}"`. | — |
| tests/test_gancho_uso_base.py | 80/80 | CERTIFICADO | Exercita `gancho_uso` com a mensagem base (assunto_id NULL) e a migração; payload JSON de poucos bytes. | — |
| tests/test_gate_lote_ordem.py | 224/224 | CERTIFICADO | Exercita casamento posicional do gate de relação ao objetivo; assuntos só com título ("Assunto A/B/C"); mock devolve lista de bool. | — |
| tests/test_gate_objetivo.py | 196/196 | CERTIFICADO | Exercita gate (brief 049); ESCONDE: o gate falso decide por `"OAB" in candidato`, e o candidato é só o TÍTULO do assunto (assunto sem corpo); confere no prompt objetivo, frase do pedido e ficha. | — |
| tests/test_gate_zera_menu.py | 165/165 | CERTIFICADO | Exercita gate que reprova tudo (menu zera); títulos curtos, mock devolve `relaciona=False` para N candidatos. | — |
| tests/test_google_news.py | 47/47 | CERTIFICADO | Exercita `gerar_consultas` por tema; DOCUMENTA limite de 4 termos por tema (ver bloco). | — |
| tests/test_google_news_consulta.py | 75/75 | CERTIFICADO | Exercita `selecionar_termos`/`gerar_consultas_da_consulta`; DOCUMENTA teto de termos (ver bloco). | — |
| tests/test_guarda_comando.py | 134/134 | CERTIFICADO | Testa hook `guarda_comando.py` (bloqueios de git/rm/agente_nw); só infraestrutura. | — |
| tests/test_historico_formatar.py | 130/130 | CERTIFICADO | Exercita `historico.formatar`/`historico_recente_para_prompt`; DOCUMENTA "padrão de cinco" consultas no histórico do prompt (ver bloco). | — |
| tests/test_imagens.py | 63/63 | CERTIFICADO | Exercita `imagens.descrever` com visão fake; descrição curta devolvida inteira (só `strip`); descrição de qualquer tema é mantida. | — |
| tests/test_importador.py | 86/86 | CERTIFICADO | Exercita importador CSV da agenda; nota da agenda ("Gosta de futebol e viagens.") curta, vai inteira à fila de extração. | — |
| tests/test_importar_temas.py | 67/67 | CERTIFICADO | Exercita `importar_temas` com embedder fake constante; sem texto longo. | — |
| tests/test_inferencia_declaracoes.py | 122/122 | CERTIFICADO | Exercita `aplicar_declaracoes` com frases curtas de 1 linha; LLM fake devolve descrição fixa. | — |
| tests/test_inferencia_temas.py | 158/158 | CERTIFICADO | Exercita `atualizar_temas_do_usuario`/decaimento (30/90/180 dias); termos de 1 palavra. | — |
| tests/test_inicio_lista_contatos.py | 101/101 | CERTIFICADO | Exercita tela inicial; DOCUMENTA `listar_para_inicio(conn,"",20)` (25 contatos, só 20 voltam) — apresentação (ver bloco). | — |
| tests/test_itens_agrupamento.py | 154/154 | CERTIFICADO | Exercita queries de `item`; texto do item fixado em "Texto de exemplo." (nunca testa corpo de notícia); `listar_sem_assunto(conn, 10)` documenta parâmetro de limite. | — |
| tests/test_lacunas.py | 31/31 | CERTIFICADO | Exercita `campos_faltando` do perfil; sem texto. | — |
| tests/test_lint_arquivo.py | 63/63 | CERTIFICADO | Testa hook `lint_arquivo.py`; só infraestrutura. | — |
| tests/test_listas_parse.py | 225/225 | CERTIFICADO | Exercita parsing de listas de rede social; DOCUMENTA `maximo_entradas` truncando a leitura (`truncada is True`) (ver bloco); página fake com `texto="x"*600`. | — |
| tests/test_listas_queries.py | 142/142 | CERTIFICADO | Exercita queries de listas e busca por nome; `buscar_parecidos(..., 0.8, 5)` documenta limite 5 (ver bloco). | — |
| tests/test_llm_api.py | 422/422 | CERTIFICADO | Exercita clientes Anthropic/Gemini/OpenAI com MockTransport; prompt de teste é a string "prompt"; afirma que `num_ctx` NÃO vai no corpo das APIs (ver bloco P). | — |
| tests/test_llm_fumaca.py | 87/87 | CERTIFICADO | Teste `llm_real` de fumaça (20 JSONs, 100 embeddings de frases curtas); não testa prompt grande nem corte do bge-m3. | — |
| tests/test_llm_log_chamadas.py | 96/96 | CERTIFICADO | Exercita log de tentativas do `ClienteOllama`; prompt = "prompt". | — |
| tests/test_llm_payload.py | 105/105 | CERTIFICADO | Exercita corpo da chamada Ollama (`think`, `format`, `num_ctx`, imagens); prompt "prompt de teste"; só confere que o `num_ctx` da tarefa vai no corpo, sem checar que o prompt cabe. | — |
| tests/test_llm_resiliente.py | 224/224 | CERTIFICADO | Exercita backoff 2/4/8/16 s, seed 42 e `num_predict`; prompt = "prompt". | — |
| tests/test_localizacao.py | 323/323 | CERTIFICADO | Exercita localização de pessoa nas redes; página fake `x*600`; LLM fake só desempata; `fatos.listar_recentes(conn, id, 10)` usado como leitura (ver bloco). | — |
| tests/test_markdown_gerar.py | 129/129 | CERTIFICADO | Exercita `markdown.gerar`; ESCONDE possível corte: cartão de 3 linhas ("linha 1\nlinha 2\nlinha 3") mas só afirma `"Cartão: linha 1" in texto` — passa com ou sem corte das linhas 2 e 3 (ver bloco). | — |
| tests/test_markdown_ler.py | 97/97 | CERTIFICADO | Exercita `ler_marcacoes` (usei/não serve e cinco motivos); blocos de 3 linhas, sem corte. | — |
| tests/test_mensagem_base_sem_noticia.py | 43/43 | CERTIFICADO | Exercita `redigir` sem assuntos (n_assuntos=0) com LLM falso que devolve a base; confere trechos fixos do prompt; reaproveita `tests.test_redacao_redigir` (fora desta lista). | — |
| tests/test_migracao_006.py | 15/15 | CERTIFICADO | Confere coluna `aderencia_consulta` após migrar; só infraestrutura. | — |
| tests/test_migracao_007.py | 16/16 | CERTIFICADO | Confere colunas da tabela `pedido` após migrar; só infraestrutura. | — |
| tests/test_migracao_008.py | 16/16 | CERTIFICADO | So confere colunas de `lista_rede_social` apos migrar; nao manipula texto de conteudo. | — |
| tests/test_migracao_009.py | 27/27 | CERTIFICADO | So confere colunas de `gancho_uso` e `rede_sem_perfil`; infraestrutura. | — |
| tests/test_migracao_011.py | 33/33 | CERTIFICADO | Colunas novas de `pedido` e CHECK de status; texto 'pedido antigo'/'x' so como linha de banco. | — |
| tests/test_migracao_comentarios.py | 49/49 | CERTIFICADO | Migracao 14 preserva `gancho_uso` antigo; `gancho_json='{}'`, sem texto real. | — |
| tests/test_migracao_genero.py | 49/49 | CERTIFICADO | Migracao 16 (`genero_gramatical`) e CHECK de 3 valores; infraestrutura. | — |
| tests/test_migracoes.py | 39/39 | CERTIFICADO | Conta migracoes aplicadas e tabelas virtuais vec0; infraestrutura. | — |
| tests/test_molde_adapta_genero.py | 120/120 | CERTIFICADO | Exercita `redacao.redigir` com molde de outro contato; mock de LLM le "Genero gramatical" no prompt e devolve mensagem curta (molde entra inteiro, mensagens de 1 linha). | — |
| tests/test_molde_atributo_compartilhado.py | 109/109 | CERTIFICADO | Exercita o bloco de moldes do prompt e `montar_entrada`; o molde de 1 frase entra inteiro (`assert molde in prompt`). Recuperacao limitada a `maximo_moldes` (ver bloco de cortes). | — |
| tests/test_molde_verdade_046.py | 71/71 | CERTIFICADO | Checa que as regras do prompt (`_regras`, `_bloco_moldes`) contem frases fixas; sem corte. | — |
| tests/test_moldes_por_contexto.py | 107/107 | CERTIFICADO | Documenta o teto de moldes (`maximo=2`) em `moldes_por_contexto`; mensagens-molde de 1 linha. | — |
| tests/test_moldes_so_confirmado.py | 195/195 | CERTIFICADO | Documenta: havendo `usado` so `usado` entra; sem `usado`, no maximo 1 `entregue` (a mais recente); mensagens curtas. | — |
| tests/test_normalizacao.py | 23/23 | CERTIFICADO | `telefone_e164` sobre numeros de telefone; identificador, nao texto de conteudo. | — |
| tests/test_nota_contato.py | 57/57 | CERTIFICADO | CRUD de `nota_contato`; `listar_por_perfil(..., 1)` documenta o parametro `limite` (corte opcional por contagem). | — |
| tests/test_orquestracao.py | 546/546 | CERTIFICADO | Encaminhamento claro/ambiguo/nenhum, canais terminal/web, `preparar_e_redigir` com `preparar` e `redigir` simulados; frases de pedido curtas, nada cortado. | — |
| tests/test_peculiaridade.py | 91/91 | CERTIFICADO | Fato unico e curto vai ao prompt; verifica frases das regras do prompt. A entrada nunca chega perto dos cortes (`_FATOS_NO_PROMPT`, `_TRECHO_DO_FATO_NO_PROMPT`). | — |
| tests/test_pedido_extrair.py | 104/104 | CERTIFICADO | Documenta o corte `termos_busca` > 6 (`modelos/pedido.py`); frase do pedido entra inteira no prompt. | — |
| tests/test_pedido_para_contexto.py | 52/52 | CERTIFICADO | Documenta dedupe de termos e `maximo=10` em `gerar_consultas_da_consulta`; termos curtos. | — |
| tests/test_pedido_resolver_contato.py | 159/159 | CERTIFICADO | Resolucao de contato por nome/pistas; LLM simulado devolve `PedidoExtraido` pronto (nao testa o prompt de extracao com frase longa). | — |
| tests/test_pedido_usuario.py | 40/40 | CERTIFICADO | `garantir_usuario` com `getpass`; nao manipula texto de conteudo. | — |
| tests/test_perfil_tema_nivel.py | 34/34 | CERTIFICADO | `atualizar_nivel` em `perfil_tema`; infraestrutura. | — |
| tests/test_perfis_apagar_unir.py | 247/247 | CERTIFICADO | Apagar/unir contatos e gatilhos de fato/consulta; textos "algo"/"original" so como linhas de banco. | — |
| tests/test_perfis_campos_guiados.py | 67/67 | CERTIFICADO | `atualizar_campos_guiados` (nao sobrescreve campo preenchido); campos curtos de ficha. | — |
| tests/test_perfis_centroide.py | 106/106 | CERTIFICADO | Centroide ponderado de temas confirmados, vetores de 1024 posicoes; sem texto. | — |
| tests/test_perfis_listar_todos.py | 52/52 | CERTIFICADO | `listar_todos` ordenado por nome; sem texto de conteudo. | — |
| tests/test_piso_objetivo.py | 67/67 | CERTIFICADO | `avaliar_por_consulta` com vetores; so constantes de limiar (`itens_no_menu=5`, `candidatos_por_contato=10`) na fixture, sem afirma-las. | — |
| tests/test_ponte_servidor.py | 236/236 | CERTIFICADO | Ponte HTTP local (token, long-poll, tempo limite, aquecimento); so infraestrutura. | — |
| tests/test_pontuacao.py | 88/88 | CERTIFICADO | 12 casos da secao 6 de `avaliar` com vetores; constantes de limiar na fixture, sem texto. | — |
| tests/test_porteiro.py | 467/467 | CERTIFICADO | Consulta ao `porteiro` antes de carregar modelo (espera 15x60 s, 16 consultas, timeout 30 s); prompts de teste de 1 palavra ("prompt"), o porteiro nao recebe texto, so modelo e porta. | — |
| tests/test_prompt_extrair_pedido.py | 27/27 | CERTIFICADO | Prompt de extracao contem a frase e os contatos; frase de 4 palavras, nao exercita frase longa. | — |
| tests/test_proveniencia.py | 335/335 | CERTIFICADO | Proveniencia (modelo, perfil, versao do prompt) em log/gancho/fato/assunto/vetor; textos de 1 frase e respostas simuladas (`{"resumo": "Obras comecam na orla."}`). | — |
| tests/test_qualificador.py | 165/165 | CERTIFICADO | `qualificar_pendentes(cliente, conn, 10)` com mock que devolve titulo/qualificacao; assunto de 1 item so com titulo "Titulo do item" (sem texto do item). | — |
| tests/test_reconsulta_mesmo_dia.py | 212/212 | CERTIFICADO | Reconsulta substitui menu/preserva `usado`; mock de LLM e assuntos so com titulo e centroide fixo; limiares de fixture (`teaser_minimo_caracteres=400`, `maximo_entradas=2000`, `itens_no_menu=5`) sem afirma-los. | — |
| tests/test_redacao_fato_antigo_e_foto.py | 91/91 | CERTIFICADO | Marcas `[antigo]`/`[de imagem]` em `_fatos`; o `12` passado e `meses_fato_antigo`, nao contagem; fatos de 1 linha. | — |
| tests/test_redacao_modelo.py | 126/126 | CERTIFICADO | Documenta limites de palavras por registro (60/80/110), titulo <= 12 palavras e `MAXIMO_GANCHOS=4` (`modelos/redacao.py`); rejeita, nao trunca. | — |
| tests/test_redacao_prompt.py | 110/110 | CERTIFICADO | Documenta `cortar_por_tamanho`: acima de 6000 tokens estimados fica 1 consulta de historico e 5 fatos; `estimar_tokens` = palavras x 1,4. | — |
| tests/test_redacao_redigir.py | 349/349 | CERTIFICADO | Documenta `_escolher_fatos` (10 de 30: 4 recentes + 6 por semelhanca; sem embeddings os 10 mais recentes); fatos de teste curtos escondem o corte de 600 caracteres no embedding. | — |
| tests/test_rede_sem_perfil.py | 65/65 | CERTIFICADO | CRUD de `rede_sem_perfil`; sem texto de conteudo. | — |
| tests/test_redes_sociais_queries.py | 82/82 | CERTIFICADO | CRUD de `redes_sociais`; sem texto de conteudo. | — |
| tests/test_restricoes.py | 102/102 | CERTIFICADO | Restricoes UNIQUE/CHECK/gatilhos do esquema; conteudo 'x'/'y' so como linha de banco. | — |
| tests/test_ruido.py | 51/51 | CERTIFICADO | Documenta o filtro `e_ruido`: corpo < `teaser_minimo_caracteres` (400) e ruido; `CORPO_LONGO` tem ~650 caracteres, corpo curto = "corpo curto". | — |
| tests/test_seguranca_prompt.py | 348/348 | CERTIFICADO | `cercar_dado_externo` e os 9 modulos de prompt: texto entra inteiro entre marcadores, marcador forjado neutralizado, conteudo preservado (`INJECAO in cercado`); entradas de 1 linha. | — |
| tests/test_selecao_provedor.py | 216/216 | CERTIFICADO | `selecionar_cliente_llm` (ordem Anthropic > Gemini > OpenAI); le so `container.py`/`app.py` para contar construcoes; sem texto de conteudo. | — |
| tests/test_sem_censura_de_tema.py | 75/75 | CERTIFICADO | Tag/fato politico ou de saude sao gravados; prompt de extracao sem "sensive"; texto de fila "texto qualquer" (curto), resposta simulada. | — |
| tests/test_sem_objetivo_avisa.py | 38/38 | CERTIFICADO | Todos abaixo do piso -> aviso; reaproveita fixtures de `test_cruzamento_por_consulta`; fato de 1 linha, assunto so com titulo. | — |
| tests/test_sem_redes_sociais.py | 74/74 | CERTIFICADO | Botao "sem redes sociais" no console Flask; sem texto de conteudo. | — |
| tests/test_temas_atualizar.py | 33/33 | CERTIFICADO | `temas.atualizar` regrava descricao e sinonimos; descricoes curtas, sem corte. | — |
| tests/test_termos_contato.py | 89/89 | CERTIFICADO | Documenta teto de 3 termos e rejeicao de termo > 5 palavras em `termos_contato.py`; os fatos de teste sao curtos e escondem os cortes de 12 fatos e 300 caracteres por fato do prompt. | — |
| tests/test_validacao_base.py | 69/69 | CERTIFICADO | Documenta `validar_ganchos`: base antes, so 1 base, `MAXIMO_GANCHOS` de noticia, limite 80 palavras da base. | — |
| tests/test_verificar_auditoria_texto.py | 500/500 | CERTIFICADO | só exercita o verificador contra árvores e relatórios sintéticos em `tmp_path`; não constrói entrada de produção | — |
| tests/test_vetores.py | 33/33 | CERTIFICADO | `cosseno` e `centroide` com vetores pequenos; sem texto. | — |
| tests/test_whatsapp_importador.py | 289/289 | CERTIFICADO | Documenta `meses_extraidos=2` (so os 2 meses mais recentes, julho fora); mensagens de 1 linha escondem `maximo_caracteres_bloco=6000`, que nenhum teste exercita. | — |
| tests/test_whatsapp_leitor.py | 109/109 | CERTIFICADO | Parser da exportacao (iPhone/Android/zip); descarta midia/aviso do sistema/mensagem apagada, emenda linhas, sem cortar texto de mensagem real. | — |
| tests/test_whatsapp_no_prompt.py | 110/110 | CERTIFICADO | Documenta as 10 ultimas trocas do WhatsApp no prompt (de 15) e a retirada da conversa inteira quando o prompt passa de 6000 tokens (`cortar_por_tamanho`). | — |

*Certifico que, nos arquivos marcados CERTIFICADO, li o arquivo inteiro e nenhum texto de conteúdo é
analisado só em parte. Os demais estão nas seções 3 e 4 ou marcados NÃO CONFERIDO.* (Nenhum arquivo
ficou NÃO CONFERIDO nesta auditoria.)

---

## 7. Achados adjacentes — a resposta do modelo pode vir cortada

O problema irmão do P-040, na saída: o item 2.5 do brief pede que seja registrado, não classificado
como violação.

| Onde | O que pode vir cortado | O que o provedor devolve | O que o projeto faz hoje |
|---|---|---|---|
| `agente_nw/nucleo/llm.py:249` (Ollama) | resposta acima de `num_predict` (256 a 2.048 por tarefa) | `done_reason: "length"` no JSON da resposta | ignora o campo; só olha `response` |
| `agente_nw/nucleo/llm.py:365` (`_chamar` do Ollama, bloco `options`) | idem, em `cartao` (1.024) e `redigir_ganchos` (2.048), as saídas mais longas | idem | idem |
| `agente_nw/nucleo/llm.py:473` (Anthropic) | resposta acima de `max_tokens` (= `num_predict`) | `stop_reason: "max_tokens"` | ignora |
| `agente_nw/nucleo/llm.py:560` (OpenAI) | idem | `finish_reason: "length"` | ignora |
| `agente_nw/nucleo/llm.py:425` (Gemini) | idem (`maxOutputTokens`) | `finishReason: "MAX_TOKENS"` | ignora |

Consequência: uma resposta cortada no meio do JSON cai no caminho de "JSON inválido" e ganha nova
tentativa — isso funciona. Uma resposta **sintaticamente válida e semanticamente incompleta** (um
cartão com duas linhas em vez de três, uma lista de tags que parou no meio, uma mensagem truncada que
ainda fecha a chave) é gravada como boa. Nenhum teste do projeto cobre esse caso (confirmado na
leitura dos 158 arquivos de teste), e nenhum log registra o motivo da parada. Ver P-042.

Segundo achado adjacente, de contexto e não de corte: cada bloco de conversa do WhatsApp é extraído
isolado (`NA-007`), então um assunto que atravessa dois blocos é visto duas vezes pela metade. Nada é
perdido, mas o modelo não enxerga a conversa inteira de uma vez.

---

## 8. Apêndice A — varredura mecânica, com o destino de cada ocorrência

Os padrões do passo 3 do brief, aplicados pelo verificador aos 317 arquivos do universo (a lista
exata está em `scripts/verificar_auditoria_texto.py`, `PADROES_VARREDURA`). **1.272 ocorrências**,
todas com destino. O comando e a saída crua:

```
$ .venv/bin/python scripts/verificar_auditoria_texto.py --varredura --raiz . > ocorrencias.txt
$ wc -l < ocorrencias.txt
1272
```

A saída crua, com o texto de cada linha de código, está em
`docs/auditoria_079_material/varredura_mecanica.txt` (local: o `.gitignore` versiona só os `.md` de `docs/`). Abaixo, o destino de cada ocorrência, agrupado
por destino: primeiro as que viraram ponto (seções 3 e 4), depois as descartadas, cada grupo com a
razão do descarte. O verificador refaz esta varredura e exige que **cada** `arquivo:linha` apareça
neste relatório — é o que impede que uma ocorrência fique sem resposta.

**NA-001** — 10 ocorrência(s):

```
agente_nw/cli.py:1068 agente_nw/nucleo/consulta.py:212 agente_nw/nucleo/database/queries/conversa.py:92 agente_nw/nucleo/historico.py:64
agente_nw/nucleo/redacao.py:120 agente_nw/nucleo/redacao.py:139 agente_nw/nucleo/redacao.py:70 agente_nw/nucleo/relevancia/cruzamento.py:201
agente_nw/nucleo/relevancia/cruzamento.py:336 agente_nw/perfil/inferencia.py:269
```

**NA-002** — 2 ocorrência(s):

```
agente_nw/coleta/capturas/busca.py:140 agente_nw/nucleo/localizacao.py:197
```

**NA-003** — 2 ocorrência(s):

```
agente_nw/nucleo/database/queries/pedidos.py:153 agente_nw/nucleo/database/queries/perfis.py:411
```

**NA-005** — 1 ocorrência(s):

```
agente_nw/nucleo/database/migracoes.py:21
```

**NA-007** — 3 ocorrência(s):

```
agente_nw/nucleo/database/queries/conversa.py:64 agente_nw/nucleo/modelos/configuracao.py:276 config/limiares.yaml:72
```

**P-001** — 1 ocorrência(s):

```
agente_nw/nucleo/agrupamento/agrupador.py:88
```

**P-003** — 1 ocorrência(s):

```
agente_nw/coleta/rss/leitor.py:338
```

**P-004** — 1 ocorrência(s):

```
agente_nw/coleta/rss/ruido.py:57
```

**P-005** — 10 ocorrência(s):

```
agente_nw/coleta/rss/google_news.py:24 agente_nw/coleta/rss/google_news.py:59 agente_nw/coleta/rss/google_news.py:60 agente_nw/coleta/rss/google_news.py:61
agente_nw/coleta/rss/google_news.py:72 agente_nw/coleta/rss/leitor.py:246 agente_nw/coleta/rss/leitor.py:275 agente_nw/coleta/rss/leitor.py:362
config/limiares.yaml:40 config/limiares.yaml:41
```

**P-007** — 1 ocorrência(s):

```
agente_nw/nucleo/relevancia/cartoes.py:51
```

**P-008** — 3 ocorrência(s):

```
agente_nw/nucleo/agrupamento/calibracao.py:103 agente_nw/nucleo/agrupamento/calibracao.py:108 agente_nw/nucleo/agrupamento/calibracao.py:82
```

**P-009** — 7 ocorrência(s):

```
agente_nw/cli.py:442 agente_nw/nucleo/database/queries/assuntos.py:179 agente_nw/nucleo/database/queries/assuntos.py:254 agente_nw/nucleo/relevancia/candidatos.py:31
agente_nw/nucleo/relevancia/candidatos.py:83 agente_nw/nucleo/relevancia/cruzamento.py:272 agente_nw/nucleo/relevancia/cruzamento.py:481
```

**P-010** — 1 ocorrência(s):

```
agente_nw/nucleo/relevancia/cruzamento.py:155
```

**P-012** — 1 ocorrência(s):

```
agente_nw/nucleo/relevancia/candidatos.py:41
```

**P-013** — 5 ocorrência(s):

```
agente_nw/coleta/capturas/extensao_backend.py:88 agente_nw/coleta/capturas/extensao_backend.py:93 agente_nw/nucleo/modelos/configuracao.py:244 config/limiares.yaml:59
extensao/conteudo.js:199
```

**P-015** — 3 ocorrência(s):

```
agente_nw/coleta/capturas/listas.py:369 config/limiares.yaml:48 extensao/conteudo.js:108
```

**P-016** — 4 ocorrência(s):

```
agente_nw/coleta/capturas/leitor.py:136 agente_nw/coleta/capturas/leitor.py:143 agente_nw/nucleo/consulta.py:147 config/limiares.yaml:42
```

**P-017** — 3 ocorrência(s):

```
agente_nw/coleta/capturas/navegador.py:61 config/limiares.yaml:43 extensao/conteudo.js:185
```

**P-020** — 3 ocorrência(s):

```
agente_nw/coleta/capturas/busca.py:112 agente_nw/coleta/capturas/listas.py:251 agente_nw/coleta/capturas/listas.py:254
```

**P-021** — 3 ocorrência(s):

```
agente_nw/nucleo/confirmacao.py:182 agente_nw/nucleo/database/queries/listas.py:138 config/limiares.yaml:52
```

**P-022** — 3 ocorrência(s):

```
agente_nw/coleta/whatsapp/importador.py:51 agente_nw/nucleo/database/queries/conversa.py:97 config/limiares.yaml:71
```

**P-023** — 3 ocorrência(s):

```
agente_nw/nucleo/database/queries/conversa.py:46 agente_nw/nucleo/redacao.py:242 config/limiares.yaml:73
```

**P-025** — 1 ocorrência(s):

```
agente_nw/nucleo/database/queries/perfis.py:629
```

**P-026** — 4 ocorrência(s):

```
agente_nw/nucleo/database/queries/fatos.py:34 agente_nw/nucleo/redacao.py:101 agente_nw/nucleo/redacao.py:108 agente_nw/nucleo/redacao.py:146
```

**P-027** — 2 ocorrência(s):

```
agente_nw/nucleo/termos_contato.py:60 agente_nw/nucleo/termos_contato.py:76
```

**P-028** — 4 ocorrência(s):

```
agente_nw/nucleo/historico.py:10 agente_nw/nucleo/historico.py:56 agente_nw/nucleo/historico.py:58 agente_nw/nucleo/redacao.py:155
```

**P-029** — 2 ocorrência(s):

```
agente_nw/nucleo/database/queries/nota_contato.py:49 agente_nw/nucleo/redacao.py:162
```

**P-030** — 2 ocorrência(s):

```
agente_nw/nucleo/database/queries/consulta_contato.py:123 agente_nw/nucleo/redacao.py:188
```

**P-031** — 1 ocorrência(s):

```
agente_nw/nucleo/redacao.py:69
```

**P-032** — 1 ocorrência(s):

```
agente_nw/nucleo/modelos/redacao.py:141
```

**P-033** — 5 ocorrência(s):

```
agente_nw/cli.py:921 agente_nw/console/app.py:164 agente_nw/nucleo/fluxo.py:364 agente_nw/nucleo/prompts/redigir_ganchos.py:287
agente_nw/nucleo/prompts/redigir_ganchos.py:294
```

**P-034** — 2 ocorrência(s):

```
agente_nw/nucleo/modelos/pedido.py:101 agente_nw/nucleo/modelos/pedido.py:91
```

**P-035** — 1 ocorrência(s):

```
agente_nw/nucleo/database/queries/perfis.py:384
```

**P-039** — 1 ocorrência(s):

```
agente_nw/nucleo/relevancia/cruzamento.py:407
```

**P-040** — 1 ocorrência(s):

```
config/llm_routing.yaml:8
```

**P-041** — 1 ocorrência(s):

```
agente_nw/nucleo/database/queries/perfis.py:630
```

**P-042** — 1 ocorrência(s):

```
config/llm_routing.yaml:9
```

**P-043** — 3 ocorrência(s):

```
agente_nw/nucleo/database/queries/fila_extracao.py:34 agente_nw/nucleo/database/queries/fontes.py:70 agente_nw/nucleo/database/queries/itens.py:68
```

**P-045** — 2 ocorrência(s):

```
agente_nw/nucleo/database/queries/listas.py:75 agente_nw/nucleo/database/queries/perfis.py:453
```

descartada: a palavra resumo/resumir nomeia variável, campo, função ou comentário — 276 ocorrência(s):

```
agente_nw/cli.py:1036 agente_nw/cli.py:1040 agente_nw/cli.py:1041 agente_nw/cli.py:1042
agente_nw/cli.py:1043 agente_nw/cli.py:1044 agente_nw/cli.py:1152 agente_nw/cli.py:1153
agente_nw/cli.py:1154 agente_nw/cli.py:1155 agente_nw/cli.py:1156 agente_nw/cli.py:1157
agente_nw/cli.py:1158 agente_nw/cli.py:334 agente_nw/cli.py:336 agente_nw/cli.py:337
agente_nw/cli.py:338 agente_nw/cli.py:339 agente_nw/cli.py:340 agente_nw/cli.py:341
agente_nw/cli.py:343 agente_nw/cli.py:344 agente_nw/cli.py:345 agente_nw/cli.py:346
agente_nw/cli.py:347 agente_nw/cli.py:402 agente_nw/cli.py:404 agente_nw/cli.py:405
agente_nw/cli.py:406 agente_nw/cli.py:407 agente_nw/cli.py:408 agente_nw/cli.py:415
agente_nw/cli.py:417 agente_nw/cli.py:418 agente_nw/cli.py:419 agente_nw/cli.py:420
agente_nw/cli.py:421 agente_nw/cli.py:422 agente_nw/cli.py:423 agente_nw/cli.py:429
agente_nw/cli.py:431 agente_nw/cli.py:432 agente_nw/cli.py:433 agente_nw/cli.py:434
agente_nw/cli.py:435 agente_nw/cli.py:436 agente_nw/cli.py:443 agente_nw/cli.py:445
agente_nw/cli.py:446 agente_nw/cli.py:447 agente_nw/cli.py:448 agente_nw/cli.py:480
agente_nw/cli.py:481 agente_nw/cli.py:482 agente_nw/cli.py:485 agente_nw/cli.py:486
agente_nw/cli.py:614 agente_nw/cli.py:616 agente_nw/cli.py:617 agente_nw/cli.py:618
agente_nw/cli.py:620 agente_nw/coleta/capturas/busca.py:145 agente_nw/coleta/capturas/leitor.py:102 agente_nw/coleta/capturas/leitor.py:126
agente_nw/coleta/capturas/leitor.py:127 agente_nw/coleta/capturas/leitor.py:130 agente_nw/coleta/capturas/leitor.py:131 agente_nw/coleta/capturas/leitor.py:160
agente_nw/coleta/capturas/leitor.py:166 agente_nw/coleta/capturas/leitor.py:170 agente_nw/coleta/capturas/leitor.py:48 agente_nw/coleta/capturas/leitor.py:72
agente_nw/coleta/capturas/leitor.py:73 agente_nw/coleta/rss/leitor.py:104 agente_nw/coleta/rss/leitor.py:113 agente_nw/coleta/rss/leitor.py:115
agente_nw/coleta/rss/leitor.py:119 agente_nw/coleta/rss/leitor.py:125 agente_nw/coleta/rss/leitor.py:142 agente_nw/coleta/rss/leitor.py:153
agente_nw/coleta/rss/leitor.py:161 agente_nw/coleta/rss/leitor.py:162 agente_nw/coleta/rss/leitor.py:166 agente_nw/coleta/rss/leitor.py:172
agente_nw/coleta/rss/leitor.py:173 agente_nw/coleta/rss/leitor.py:176 agente_nw/coleta/rss/leitor.py:178 agente_nw/coleta/rss/leitor.py:182
agente_nw/coleta/rss/leitor.py:183 agente_nw/coleta/rss/leitor.py:185 agente_nw/coleta/rss/leitor.py:187 agente_nw/coleta/rss/leitor.py:189
agente_nw/coleta/rss/leitor.py:213 agente_nw/coleta/rss/leitor.py:247 agente_nw/coleta/rss/leitor.py:252 agente_nw/coleta/rss/leitor.py:253
agente_nw/coleta/rss/leitor.py:257 agente_nw/coleta/rss/leitor.py:263 agente_nw/coleta/rss/leitor.py:268 agente_nw/coleta/rss/leitor.py:272
agente_nw/coleta/rss/leitor.py:278 agente_nw/coleta/rss/leitor.py:281 agente_nw/coleta/rss/leitor.py:283 agente_nw/coleta/rss/leitor.py:284
agente_nw/coleta/rss/leitor.py:286 agente_nw/coleta/rss/leitor.py:287 agente_nw/coleta/rss/leitor.py:288 agente_nw/coleta/rss/leitor.py:296
agente_nw/coleta/rss/leitor.py:307 agente_nw/coleta/rss/leitor.py:311 agente_nw/coleta/rss/leitor.py:323 agente_nw/coleta/rss/leitor.py:330
agente_nw/coleta/rss/leitor.py:347 agente_nw/coleta/rss/leitor.py:360 agente_nw/console/app.py:506 agente_nw/console/app.py:510
agente_nw/nucleo/agrupamento/agrupador.py:122 agente_nw/nucleo/agrupamento/agrupador.py:123 agente_nw/nucleo/agrupamento/agrupador.py:146 agente_nw/nucleo/agrupamento/agrupador.py:147
agente_nw/nucleo/agrupamento/agrupador.py:181 agente_nw/nucleo/agrupamento/agrupador.py:183 agente_nw/nucleo/agrupamento/agrupador.py:188 agente_nw/nucleo/agrupamento/agrupador.py:249
agente_nw/nucleo/agrupamento/agrupador.py:252 agente_nw/nucleo/agrupamento/agrupador.py:79 agente_nw/nucleo/agrupamento/agrupador.py:91 agente_nw/nucleo/consulta.py:137
agente_nw/nucleo/consulta.py:153 agente_nw/nucleo/consulta.py:154 agente_nw/nucleo/consulta.py:155 agente_nw/nucleo/consulta.py:156
agente_nw/nucleo/consulta.py:157 agente_nw/nucleo/consulta.py:158 agente_nw/nucleo/consulta.py:159 agente_nw/nucleo/consulta.py:175
agente_nw/nucleo/consulta.py:185 agente_nw/nucleo/consulta.py:186 agente_nw/nucleo/consulta.py:187 agente_nw/nucleo/consulta.py:188
agente_nw/nucleo/consulta.py:193 agente_nw/nucleo/consulta.py:195 agente_nw/nucleo/consulta.py:196 agente_nw/nucleo/consulta.py:253
agente_nw/nucleo/consulta.py:263 agente_nw/nucleo/consulta.py:53 agente_nw/nucleo/consulta.py:74 agente_nw/nucleo/consulta.py:75
agente_nw/nucleo/consulta.py:77 agente_nw/nucleo/consulta.py:78 agente_nw/nucleo/consulta.py:79 agente_nw/nucleo/consulta.py:80
agente_nw/nucleo/consulta.py:81 agente_nw/nucleo/consulta.py:82 agente_nw/nucleo/consulta.py:83 agente_nw/nucleo/consulta.py:84
agente_nw/nucleo/database/queries/assuntos.py:15 agente_nw/nucleo/database/queries/assuntos.py:212 agente_nw/nucleo/database/queries/assuntos.py:216 agente_nw/nucleo/database/queries/assuntos.py:219
agente_nw/nucleo/database/queries/assuntos.py:253 agente_nw/nucleo/database/queries/assuntos.py:32 agente_nw/nucleo/database/queries/assuntos.py:45 agente_nw/nucleo/database/queries/assuntos.py:58
agente_nw/nucleo/database/queries/consulta_contato.py:10 agente_nw/nucleo/database/queries/consulta_contato.py:19 agente_nw/nucleo/database/queries/consulta_contato.py:29 agente_nw/nucleo/database/queries/consulta_contato.py:34
agente_nw/nucleo/database/queries/consulta_contato.py:36 agente_nw/nucleo/historico.py:66 agente_nw/nucleo/historico.py:67 agente_nw/nucleo/localizacao.py:198
agente_nw/nucleo/modelos/assunto.py:24 agente_nw/nucleo/modelos/cartao.py:9 agente_nw/nucleo/modelos/consulta_contato.py:13 agente_nw/nucleo/prompts/avaliar_relacao_objetivo.py:35
agente_nw/nucleo/prompts/avaliar_relacao_objetivo.py:36 agente_nw/nucleo/prompts/avaliar_relacao_objetivo.py:39 agente_nw/nucleo/prompts/avaliar_relacao_objetivo.py:40 agente_nw/nucleo/prompts/cartao.py:28
agente_nw/nucleo/prompts/cartao.py:43 agente_nw/nucleo/prompts/cartao.py:46 agente_nw/nucleo/prompts/cartao.py:54 agente_nw/nucleo/prompts/cartao.py:64
agente_nw/nucleo/prompts/qualificar.py:53 agente_nw/nucleo/prompts/redigir_ganchos.py:184 agente_nw/nucleo/prompts/redigir_ganchos.py:185 agente_nw/nucleo/prompts/redigir_ganchos.py:209
agente_nw/nucleo/prompts/redigir_ganchos.py:66 agente_nw/nucleo/prompts/rotular.py:11 agente_nw/nucleo/prompts/rotular.py:26 agente_nw/nucleo/prompts/rotular.py:38
agente_nw/nucleo/prompts/seguranca.py:22 agente_nw/nucleo/redacao.py:85 agente_nw/nucleo/relevancia/candidatos.py:40 agente_nw/nucleo/relevancia/cartoes.py:100
agente_nw/nucleo/relevancia/cartoes.py:102 agente_nw/nucleo/relevancia/cartoes.py:39 agente_nw/nucleo/relevancia/cartoes.py:40 agente_nw/nucleo/relevancia/cartoes.py:50
agente_nw/nucleo/relevancia/cartoes.py:54 agente_nw/nucleo/relevancia/cartoes.py:63 agente_nw/nucleo/relevancia/cartoes.py:65 agente_nw/nucleo/relevancia/cartoes.py:68
agente_nw/nucleo/relevancia/cartoes.py:90 agente_nw/nucleo/relevancia/cartoes.py:92 agente_nw/nucleo/relevancia/cartoes.py:98 agente_nw/nucleo/relevancia/cruzamento.py:150
agente_nw/nucleo/relevancia/cruzamento.py:161 agente_nw/nucleo/relevancia/cruzamento.py:188 agente_nw/nucleo/relevancia/cruzamento.py:200 agente_nw/nucleo/relevancia/cruzamento.py:208
agente_nw/nucleo/relevancia/cruzamento.py:209 agente_nw/nucleo/relevancia/cruzamento.py:210 agente_nw/nucleo/relevancia/cruzamento.py:223 agente_nw/nucleo/relevancia/cruzamento.py:225
agente_nw/nucleo/relevancia/cruzamento.py:226 agente_nw/nucleo/relevancia/cruzamento.py:227 agente_nw/nucleo/relevancia/cruzamento.py:261 agente_nw/nucleo/relevancia/cruzamento.py:266
agente_nw/nucleo/relevancia/cruzamento.py:267 agente_nw/nucleo/relevancia/cruzamento.py:268 agente_nw/nucleo/relevancia/cruzamento.py:294 agente_nw/nucleo/relevancia/cruzamento.py:315
agente_nw/nucleo/relevancia/cruzamento.py:317 agente_nw/nucleo/relevancia/cruzamento.py:320 agente_nw/nucleo/relevancia/cruzamento.py:335 agente_nw/nucleo/relevancia/cruzamento.py:387
agente_nw/nucleo/relevancia/cruzamento.py:390 agente_nw/nucleo/relevancia/cruzamento.py:392 agente_nw/nucleo/relevancia/cruzamento.py:393 agente_nw/nucleo/relevancia/cruzamento.py:398
agente_nw/nucleo/relevancia/cruzamento.py:456 agente_nw/nucleo/relevancia/cruzamento.py:461 agente_nw/nucleo/relevancia/cruzamento.py:462 agente_nw/nucleo/relevancia/cruzamento.py:463
agente_nw/nucleo/relevancia/cruzamento.py:472 agente_nw/nucleo/relevancia/cruzamento.py:475 agente_nw/nucleo/relevancia/cruzamento.py:476 agente_nw/nucleo/relevancia/cruzamento.py:477
agente_nw/nucleo/relevancia/cruzamento.py:500 agente_nw/nucleo/relevancia/cruzamento.py:525 agente_nw/nucleo/relevancia/cruzamento.py:527 agente_nw/nucleo/relevancia/cruzamento.py:530
agente_nw/nucleo/relevancia/qualificador.py:107 agente_nw/nucleo/relevancia/qualificador.py:109 agente_nw/nucleo/relevancia/qualificador.py:41 agente_nw/nucleo/relevancia/qualificador.py:53
agente_nw/nucleo/relevancia/qualificador.py:57 agente_nw/nucleo/relevancia/qualificador.py:63 agente_nw/nucleo/relevancia/qualificador.py:66 agente_nw/nucleo/relevancia/qualificador.py:72
agente_nw/nucleo/relevancia/qualificador.py:76 agente_nw/nucleo/relevancia/qualificador.py:81 agente_nw/nucleo/relevancia/qualificador.py:87 agente_nw/nucleo/saidas/markdown.py:39
agente_nw/perfil/extrator.py:117 agente_nw/perfil/extrator.py:122 agente_nw/perfil/extrator.py:124 agente_nw/perfil/extrator.py:73
agente_nw/perfil/extrator.py:86 agente_nw/perfil/extrator.py:93 agente_nw/perfil/extrator.py:97 agente_nw/perfil/importador.py:103
agente_nw/perfil/importador.py:107 agente_nw/perfil/importador.py:111 agente_nw/perfil/importador.py:67 agente_nw/perfil/importador.py:70
agente_nw/perfil/importador.py:75 agente_nw/perfil/importador.py:94 agente_nw/perfil/importador.py:96 scripts/agente_lacunas.py:127
scripts/agente_lacunas.py:128 scripts/migracoes/001_inicial.sql:75 scripts/migracoes/004_consulta_contato.sql:10 scripts/migracoes/005_perfil_id_reatribuivel.sql:15
```

descartada: arquivo de teste — não gera ponto (certificação simplificada, seção 6) — 464 ocorrência(s):

```
tests/coleta_falsa.py:66 tests/llm_falso.py:23 tests/test_agente_entregar.py:174 tests/test_agente_lacunas.py:131
tests/test_agente_lacunas.py:49 tests/test_agente_lacunas.py:98 tests/test_agrupador.py:128 tests/test_agrupador.py:130
tests/test_agrupador.py:131 tests/test_agrupador.py:132 tests/test_agrupador.py:167 tests/test_agrupador.py:169
tests/test_agrupador.py:170 tests/test_agrupador.py:215 tests/test_agrupador.py:217 tests/test_agrupador.py:218
tests/test_agrupador.py:263 tests/test_agrupador.py:265 tests/test_agrupador.py:73 tests/test_assuntos_qualificacao.py:166
tests/test_assuntos_qualificacao.py:95 tests/test_assuntos_sem_cartao.py:39 tests/test_assuntos_sem_cartao.py:52 tests/test_calibracao.py:143
tests/test_calibracao.py:200 tests/test_calibracao.py:208 tests/test_calibracao.py:209 tests/test_calibracao.py:210
tests/test_calibracao.py:212 tests/test_candidatos.py:103 tests/test_capturas_leitor.py:117 tests/test_capturas_leitor.py:130
tests/test_capturas_leitor.py:131 tests/test_capturas_leitor.py:132 tests/test_capturas_leitor.py:186 tests/test_capturas_leitor.py:199
tests/test_capturas_leitor.py:200 tests/test_capturas_leitor.py:201 tests/test_capturas_leitor.py:202 tests/test_capturas_leitor.py:223
tests/test_capturas_leitor.py:229 tests/test_capturas_leitor.py:230 tests/test_capturas_leitor.py:236 tests/test_capturas_leitor.py:245
tests/test_capturas_leitor.py:250 tests/test_capturas_leitor.py:251 tests/test_capturas_leitor.py:256 tests/test_capturas_leitor.py:269
tests/test_capturas_leitor.py:278 tests/test_capturas_leitor.py:281 tests/test_capturas_leitor.py:284 tests/test_capturas_leitor.py:292
tests/test_capturas_leitor.py:297 tests/test_capturas_leitor.py:340 tests/test_capturas_leitor.py:341 tests/test_capturas_leitor.py:375
tests/test_capturas_leitor.py:385 tests/test_capturas_leitor.py:388 tests/test_capturas_leitor.py:390 tests/test_capturas_leitor.py:403
tests/test_capturas_leitor.py:408 tests/test_capturas_leitor.py:74 tests/test_capturas_leitor.py:80 tests/test_capturas_leitor.py:93
tests/test_capturas_leitor.py:94 tests/test_capturas_leitor.py:95 tests/test_capturas_navegador.py:112 tests/test_capturas_navegador.py:115
tests/test_capturas_navegador.py:143 tests/test_capturas_navegador.py:144 tests/test_capturas_navegador.py:158 tests/test_capturas_navegador.py:159
tests/test_capturas_navegador.py:164 tests/test_capturas_navegador.py:180 tests/test_capturas_navegador.py:184 tests/test_capturas_navegador.py:193
tests/test_capturas_navegador.py:39 tests/test_capturas_navegador.py:40 tests/test_capturas_navegador.py:45 tests/test_capturas_navegador.py:65
tests/test_capturas_navegador.py:66 tests/test_capturas_navegador.py:84 tests/test_cartoes.py:103 tests/test_cartoes.py:113
tests/test_cartoes.py:118 tests/test_cartoes.py:53 tests/test_cartoes.py:65 tests/test_cartoes.py:70
tests/test_cartoes.py:74 tests/test_cartoes.py:79 tests/test_cartoes.py:80 tests/test_cartoes.py:85
tests/test_cartoes.py:89 tests/test_cartoes.py:94 tests/test_cartoes_pendentes.py:103 tests/test_cartoes_pendentes.py:107
tests/test_cartoes_pendentes.py:110 tests/test_cartoes_pendentes.py:113 tests/test_cartoes_pendentes.py:116 tests/test_cartoes_pendentes.py:118
tests/test_cartoes_pendentes.py:55 tests/test_cartoes_pendentes.py:69 tests/test_cartoes_pendentes.py:70 tests/test_cartoes_pendentes.py:74
tests/test_cartoes_pendentes.py:76 tests/test_cartoes_pendentes.py:77 tests/test_cartoes_pendentes.py:78 tests/test_cartoes_pendentes.py:82
tests/test_cartoes_pendentes.py:91 tests/test_cartoes_pendentes.py:92 tests/test_cartoes_pendentes.py:95 tests/test_cartoes_pendentes.py:97
tests/test_cartoes_pendentes.py:98 tests/test_cartoes_pendentes.py:99 tests/test_cli_agrupamento.py:66 tests/test_cli_cruzamento.py:69
tests/test_cli_pedir.py:57 tests/test_cli_pedir_confirmacao.py:130 tests/test_cli_qualificacao.py:132 tests/test_cli_qualificacao.py:140
tests/test_cli_qualificacao.py:73 tests/test_coleta_bloqueio.py:111 tests/test_coleta_bloqueio.py:113 tests/test_coleta_bloqueio.py:114
tests/test_coleta_bloqueio.py:115 tests/test_coleta_bloqueio.py:118 tests/test_coleta_bloqueio.py:150 tests/test_coleta_bloqueio.py:154
tests/test_coleta_cooldown.py:15 tests/test_coleta_cooldown.py:18 tests/test_coleta_cooldown.py:19 tests/test_coleta_cooldown.py:20
tests/test_coleta_cooldown.py:21 tests/test_coleta_cooldown.py:33 tests/test_coleta_cooldown.py:36 tests/test_coleta_cooldown.py:37
tests/test_coleta_cooldown.py:60 tests/test_coleta_cooldown.py:62 tests/test_coleta_cooldown.py:63 tests/test_coleta_degradacao.py:19
tests/test_coleta_degradacao.py:21 tests/test_coleta_degradacao.py:22 tests/test_coleta_degradacao.py:23 tests/test_coleta_degradacao.py:34
tests/test_coleta_degradacao.py:36 tests/test_coleta_degradacao.py:37 tests/test_coleta_degradacao.py:38 tests/test_coleta_fonte_alternativa.py:15
tests/test_coleta_fonte_alternativa.py:35 tests/test_coleta_fonte_alternativa.py:37 tests/test_coleta_fonte_alternativa.py:50 tests/test_coleta_fonte_alternativa.py:52
tests/test_coleta_fonte_alternativa.py:53 tests/test_coleta_fonte_alternativa.py:62 tests/test_coleta_fonte_alternativa.py:64 tests/test_coleta_fonte_alternativa.py:65
tests/test_coleta_fonte_alternativa.py:73 tests/test_coleta_fonte_alternativa.py:76 tests/test_coleta_fumaca.py:63 tests/test_coleta_fumaca.py:66
tests/test_coleta_fumaca.py:67 tests/test_coleta_fumaca.py:68 tests/test_coleta_fumaca.py:69 tests/test_coleta_fumaca.py:73
tests/test_coleta_fumaca.py:79 tests/test_coleta_retomada.py:83 tests/test_coleta_retomada.py:84 tests/test_coleta_retomada.py:85
tests/test_coleta_retomada.py:92 tests/test_coleta_retomada.py:93 tests/test_coleta_retomada.py:94 tests/test_coleta_reuso_termo.py:15
tests/test_coleta_reuso_termo.py:18 tests/test_coleta_reuso_termo.py:19 tests/test_coleta_reuso_termo.py:28 tests/test_coleta_reuso_termo.py:31
tests/test_coleta_reuso_termo.py:32 tests/test_coleta_reuso_termo.py:61 tests/test_coleta_reuso_termo.py:64 tests/test_coleta_reuso_termo.py:65
tests/test_coleta_teto_consultas.py:10 tests/test_coleta_teto_consultas.py:31 tests/test_coleta_teto_consultas.py:33 tests/test_coleta_teto_consultas.py:41
tests/test_coleta_teto_consultas.py:43 tests/test_comentario_sob_orcamento.py:15 tests/test_comentario_sob_orcamento.py:17 tests/test_comentario_sob_orcamento.py:19
tests/test_comentario_sob_orcamento.py:9 tests/test_console_apagar_unir.py:67 tests/test_console_busca_rede_social.py:67 tests/test_console_configurar_perfil.py:68
tests/test_console_contatos.py:66 tests/test_console_editar_ficha.py:65 tests/test_console_eu.py:71 tests/test_console_mensagem_base.py:54
tests/test_console_menu.py:125 tests/test_console_menu.py:70 tests/test_console_novo_contato.py:62 tests/test_console_preparar.py:65
tests/test_console_redes_sociais.py:65 tests/test_console_sem_usuario.py:65 tests/test_console_tela_unica.py:185 tests/test_console_temas.py:65
tests/test_consulta_contato_queries.py:48 tests/test_consulta_contato_queries.py:69 tests/test_consulta_contato_queries.py:75 tests/test_consulta_contato_queries.py:77
tests/test_consulta_preparar.py:102 tests/test_consulta_preparar.py:136 tests/test_consulta_preparar.py:157 tests/test_consulta_preparar.py:169
tests/test_consulta_preparar.py:173 tests/test_consulta_preparar.py:177 tests/test_consulta_preparar.py:200 tests/test_consulta_preparar.py:213
tests/test_consulta_preparar.py:214 tests/test_consulta_preparar.py:227 tests/test_consulta_preparar.py:228 tests/test_consulta_preparar.py:248
tests/test_consulta_preparar.py:253 tests/test_consulta_preparar.py:72 tests/test_consulta_preparar.py:93 tests/test_cruzamento.py:146
tests/test_cruzamento.py:148 tests/test_cruzamento.py:149 tests/test_cruzamento.py:165 tests/test_cruzamento.py:167
tests/test_cruzamento.py:168 tests/test_cruzamento.py:169 tests/test_cruzamento.py:183 tests/test_cruzamento.py:186
tests/test_cruzamento.py:187 tests/test_cruzamento.py:211 tests/test_cruzamento.py:214 tests/test_cruzamento.py:230
tests/test_cruzamento.py:232 tests/test_cruzamento.py:75 tests/test_cruzamento_por_consulta.py:106 tests/test_cruzamento_por_consulta.py:166
tests/test_cruzamento_por_consulta.py:171 tests/test_cruzamento_por_consulta.py:262 tests/test_cruzamento_por_consulta.py:270 tests/test_cruzamento_por_consulta.py:321
tests/test_cruzamento_por_consulta.py:326 tests/test_divisao.py:6 tests/test_evitar_implicito.py:100 tests/test_evitar_implicito.py:151
tests/test_evitar_implicito.py:159 tests/test_evitar_implicito.py:169 tests/test_evitar_implicito.py:173 tests/test_evitar_implicito.py:174
tests/test_extensao_backend.py:178 tests/test_extensao_backend.py:18 tests/test_extensao_backend.py:21 tests/test_extensao_backend.py:23
tests/test_extensao_backend.py:42 tests/test_extensao_backend.py:60 tests/test_extensao_backend.py:62 tests/test_extensao_backend.py:64
tests/test_extensao_backend.py:75 tests/test_extensao_backend.py:77 tests/test_extensao_backend.py:83 tests/test_extensao_manifest.py:42
tests/test_extrator.py:63 tests/test_extrator.py:65 tests/test_extrator.py:66 tests/test_extrator.py:72
tests/test_fluxo.py:147 tests/test_fluxo.py:84 tests/test_gancho_uso_base.py:54 tests/test_gate_lote_ordem.py:130
tests/test_gate_lote_ordem.py:180 tests/test_gate_lote_ordem.py:194 tests/test_gate_lote_ordem.py:195 tests/test_gate_lote_ordem.py:207
tests/test_gate_lote_ordem.py:217 tests/test_gate_lote_ordem.py:223 tests/test_gate_lote_ordem.py:224 tests/test_gate_objetivo.py:109
tests/test_gate_objetivo.py:166 tests/test_gate_objetivo.py:177 tests/test_gate_objetivo.py:178 tests/test_gate_objetivo.py:179
tests/test_gate_zera_menu.py:100 tests/test_gate_zera_menu.py:153 tests/test_gate_zera_menu.py:157 tests/test_gate_zera_menu.py:158
tests/test_gate_zera_menu.py:159 tests/test_gate_zera_menu.py:160 tests/test_google_news.py:21 tests/test_google_news.py:25
tests/test_google_news.py:34 tests/test_google_news_consulta.py:21 tests/test_google_news_consulta.py:34 tests/test_google_news_consulta.py:44
tests/test_google_news_consulta.py:56 tests/test_google_news_consulta.py:57 tests/test_historico_formatar.py:26 tests/test_historico_formatar.py:45
tests/test_historico_formatar.py:53 tests/test_historico_formatar.py:59 tests/test_historico_formatar.py:74 tests/test_importador.py:26
tests/test_importador.py:29 tests/test_importador.py:32 tests/test_importador.py:34 tests/test_importador.py:35
tests/test_inicio_lista_contatos.py:37 tests/test_inicio_lista_contatos.py:54 tests/test_listas_parse.py:109 tests/test_listas_parse.py:12
tests/test_listas_parse.py:148 tests/test_listas_parse.py:150 tests/test_listas_parse.py:155 tests/test_listas_parse.py:191
tests/test_llm_api.py:124 tests/test_llm_api.py:130 tests/test_llm_api.py:195 tests/test_llm_api.py:202
tests/test_llm_api.py:254 tests/test_llm_api.py:257 tests/test_llm_payload.py:47 tests/test_llm_resiliente.py:129
tests/test_llm_resiliente.py:146 tests/test_llm_resiliente.py:3 tests/test_localizacao.py:24 tests/test_markdown_gerar.py:33
tests/test_markdown_gerar.py:36 tests/test_markdown_gerar.py:79 tests/test_markdown_gerar.py:91 tests/test_migracao_comentarios.py:16
tests/test_migracao_genero.py:19 tests/test_moldes_por_contexto.py:94 tests/test_moldes_so_confirmado.py:2 tests/test_orquestracao.py:215
tests/test_pedido_para_contexto.py:42 tests/test_ponte_servidor.py:119 tests/test_ponte_servidor.py:125 tests/test_ponte_servidor.py:127
tests/test_ponte_servidor.py:135 tests/test_ponte_servidor.py:138 tests/test_ponte_servidor.py:140 tests/test_ponte_servidor.py:144
tests/test_ponte_servidor.py:154 tests/test_ponte_servidor.py:155 tests/test_ponte_servidor.py:170 tests/test_ponte_servidor.py:190
tests/test_ponte_servidor.py:209 tests/test_ponte_servidor.py:211 tests/test_ponte_servidor.py:224 tests/test_ponte_servidor.py:82
tests/test_ponte_servidor.py:92 tests/test_porteiro.py:270 tests/test_porteiro.py:272 tests/test_porteiro.py:286
tests/test_proveniencia.py:233 tests/test_qualificador.py:100 tests/test_qualificador.py:117 tests/test_qualificador.py:120
tests/test_qualificador.py:121 tests/test_qualificador.py:133 tests/test_qualificador.py:135 tests/test_qualificador.py:136
tests/test_qualificador.py:153 tests/test_qualificador.py:155 tests/test_qualificador.py:156 tests/test_qualificador.py:157
tests/test_qualificador.py:96 tests/test_qualificador.py:99 tests/test_reconsulta_mesmo_dia.py:98 tests/test_redacao_modelo.py:116
tests/test_redacao_modelo.py:50 tests/test_redacao_modelo.py:51 tests/test_redacao_modelo.py:52 tests/test_redacao_modelo.py:53
tests/test_redacao_modelo.py:57 tests/test_redacao_prompt.py:49 tests/test_redacao_prompt.py:56 tests/test_redacao_prompt.py:84
tests/test_redacao_prompt.py:86 tests/test_redacao_redigir.py:111 tests/test_redacao_redigir.py:237 tests/test_redacao_redigir.py:332
tests/test_seguranca_prompt.py:107 tests/test_seguranca_prompt.py:113 tests/test_seguranca_prompt.py:175 tests/test_seguranca_prompt.py:180
tests/test_seguranca_prompt.py:192 tests/test_seguranca_prompt.py:194 tests/test_seguranca_prompt.py:282 tests/test_seguranca_prompt.py:288
tests/test_seguranca_prompt.py:292 tests/test_seguranca_prompt.py:335 tests/test_seguranca_prompt.py:341 tests/test_seguranca_prompt.py:89
tests/test_seguranca_prompt.py:91 tests/test_seguranca_prompt.py:93 tests/test_selecao_provedor.py:209 tests/test_selecao_provedor.py:210
tests/test_selecao_provedor.py:44 tests/test_selecao_provedor.py:45 tests/test_sem_censura_de_tema.py:56 tests/test_sem_censura_de_tema.py:61
tests/test_sem_censura_de_tema.py:63 tests/test_sem_censura_de_tema.py:64 tests/test_sem_objetivo_avisa.py:23 tests/test_sem_objetivo_avisa.py:35
tests/test_sem_objetivo_avisa.py:36 tests/test_validacao_base.py:40 tests/test_validacao_base.py:47 tests/test_validacao_base.py:50
tests/test_verificar_auditoria_texto.py:104 tests/test_verificar_auditoria_texto.py:123 tests/test_verificar_auditoria_texto.py:349 tests/test_verificar_auditoria_texto.py:350
tests/test_verificar_auditoria_texto.py:351 tests/test_verificar_auditoria_texto.py:352 tests/test_verificar_auditoria_texto.py:353 tests/test_verificar_auditoria_texto.py:354
tests/test_verificar_auditoria_texto.py:355 tests/test_verificar_auditoria_texto.py:356 tests/test_verificar_auditoria_texto.py:357 tests/test_verificar_auditoria_texto.py:358
tests/test_verificar_auditoria_texto.py:359 tests/test_verificar_auditoria_texto.py:360 tests/test_verificar_auditoria_texto.py:361 tests/test_verificar_auditoria_texto.py:362
tests/test_verificar_auditoria_texto.py:363 tests/test_verificar_auditoria_texto.py:364 tests/test_verificar_auditoria_texto.py:365 tests/test_verificar_auditoria_texto.py:366
tests/test_verificar_auditoria_texto.py:367 tests/test_verificar_auditoria_texto.py:368 tests/test_verificar_auditoria_texto.py:369 tests/test_verificar_auditoria_texto.py:370
tests/test_verificar_auditoria_texto.py:371 tests/test_verificar_auditoria_texto.py:372 tests/test_verificar_auditoria_texto.py:373 tests/test_verificar_auditoria_texto.py:389
tests/test_verificar_auditoria_texto.py:408 tests/test_verificar_auditoria_texto.py:410 tests/test_verificar_auditoria_texto.py:419 tests/test_verificar_auditoria_texto.py:492
tests/test_whatsapp_importador.py:100 tests/test_whatsapp_importador.py:102 tests/test_whatsapp_importador.py:120 tests/test_whatsapp_importador.py:122
tests/test_whatsapp_importador.py:146 tests/test_whatsapp_importador.py:157 tests/test_whatsapp_importador.py:247 tests/test_whatsapp_importador.py:257
tests/test_whatsapp_importador.py:31 tests/test_whatsapp_importador.py:77 tests/test_whatsapp_importador.py:79 tests/test_whatsapp_no_prompt.py:1
tests/test_whatsapp_no_prompt.py:102 tests/test_whatsapp_no_prompt.py:104 tests/test_whatsapp_no_prompt.py:106 tests/test_whatsapp_no_prompt.py:51
tests/test_whatsapp_no_prompt.py:72 tests/test_whatsapp_no_prompt.py:73 tests/test_whatsapp_no_prompt.py:74 tests/test_whatsapp_no_prompt.py:97
```

descartada: declaração ou repasse de num_ctx/num_predict (a ausência de conferência é P-040/P-042) — 35 ocorrência(s):

```
agente_nw/cli.py:905 agente_nw/nucleo/fluxo.py:47 agente_nw/nucleo/llm.py:352 agente_nw/nucleo/llm.py:355
agente_nw/nucleo/llm.py:473 agente_nw/nucleo/llm.py:520 agente_nw/nucleo/llm.py:560 agente_nw/nucleo/modelos/configuracao.py:63
agente_nw/nucleo/modelos/configuracao.py:67 config/llm_routing.yaml:10 config/llm_routing.yaml:11 config/llm_routing.yaml:12
config/llm_routing.yaml:13 config/llm_routing.yaml:14 config/llm_routing.yaml:15 config/llm_routing.yaml:16
config/llm_routing.yaml:17 config/llm_routing.yaml:18 config/llm_routing.yaml:19 config/llm_routing.yaml:20
config/llm_routing.yaml:21 config/llm_routing.yaml:31 config/llm_routing.yaml:32 config/llm_routing.yaml:33
config/llm_routing.yaml:34 config/llm_routing.yaml:35 config/llm_routing.yaml:36 config/llm_routing.yaml:37
config/llm_routing.yaml:38 config/llm_routing.yaml:39 config/llm_routing.yaml:40 config/llm_routing.yaml:41
config/llm_routing.yaml:42 config/llm_routing.yaml:43 config/llm_routing.yaml:44
```

descartada: extração do corpo da notícia, sem teto (ver P-003) — 1 ocorrência(s):

```
agente_nw/coleta/rss/leitor.py:13
```

descartada: fatia a partir de índice fixo (nome, palavra ou tabela), sem texto de conteúdo — 7 ocorrência(s):

```
agente_nw/cli.py:196 agente_nw/nucleo/confirmacao.py:101 agente_nw/nucleo/database/queries/perfis.py:462 agente_nw/nucleo/pedido.py:122
agente_nw/nucleo/redacao.py:111 agente_nw/nucleo/texto.py:42 scripts/agente_lacunas.py:66
```

descartada: fatia de lista ou texto já coberta pelo ponto do arquivo — 8 ocorrência(s):

```
agente_nw/coleta/rss/leitor.py:87 agente_nw/nucleo/database/queries/consulta_contato.py:124 agente_nw/nucleo/database/queries/perfis.py:427 agente_nw/nucleo/database/queries/perfis.py:436
agente_nw/nucleo/pedido.py:122 agente_nw/nucleo/redacao.py:106 agente_nw/nucleo/redacao.py:110 agente_nw/nucleo/redacao.py:113
```

descartada: leitura de arquivo/zip ou amostragem já coberta pelo ponto do arquivo — 2 ocorrência(s):

```
agente_nw/coleta/whatsapp/leitor.py:112 agente_nw/ponte/servidor.py:131
```

descartada: leitura de innerText/textContent ou slice já coberta pelo ponto do arquivo — 5 ocorrência(s):

```
extensao/conteudo.js:163 extensao/conteudo.js:198 extensao/conteudo.js:53 extensao/conteudo.js:59
extensao/conteudo.js:61
```

descartada: max_tokens/max_chars de API já coberto por P-042 — 2 ocorrência(s):

```
agente_nw/nucleo/llm.py:473 agente_nw/nucleo/llm.py:560
```

descartada: nome de função/variável de corte já coberto pelo ponto do arquivo — 7 ocorrência(s):

```
agente_nw/coleta/capturas/listas.py:165 agente_nw/coleta/capturas/listas.py:367 agente_nw/nucleo/prompts/extrair_de_texto.py:29 agente_nw/nucleo/prompts/redigir_ganchos.py:255
agente_nw/nucleo/prompts/redigir_ganchos.py:280 agente_nw/nucleo/prompts/redigir_ganchos.py:298 agente_nw/nucleo/redacao.py:309
```

descartada: palavra trocas/meses/blocos/trecho em nome, docstring ou comentário — 108 ocorrência(s):

```
agente_nw/cli.py:1042 agente_nw/cli.py:617 agente_nw/coleta/capturas/leitor.py:100 agente_nw/coleta/capturas/leitor.py:131
agente_nw/coleta/capturas/leitor.py:133 agente_nw/coleta/capturas/leitor.py:134 agente_nw/coleta/capturas/leitor.py:135 agente_nw/coleta/capturas/leitor.py:139
agente_nw/coleta/capturas/leitor.py:142 agente_nw/coleta/capturas/leitor.py:146 agente_nw/coleta/capturas/leitor.py:21 agente_nw/coleta/capturas/leitor.py:27
agente_nw/coleta/capturas/leitor.py:28 agente_nw/coleta/capturas/leitor.py:87 agente_nw/coleta/capturas/leitor.py:99 agente_nw/coleta/capturas/navegador.py:108
agente_nw/coleta/capturas/navegador.py:126 agente_nw/coleta/capturas/navegador.py:129 agente_nw/coleta/capturas/navegador.py:133 agente_nw/coleta/capturas/navegador.py:136
agente_nw/coleta/capturas/navegador.py:149 agente_nw/coleta/capturas/navegador.py:48 agente_nw/coleta/capturas/navegador.py:84 agente_nw/coleta/whatsapp/importador.py:1
agente_nw/coleta/whatsapp/importador.py:47 agente_nw/coleta/whatsapp/importador.py:48 agente_nw/coleta/whatsapp/importador.py:49 agente_nw/coleta/whatsapp/importador.py:52
agente_nw/coleta/whatsapp/importador.py:56 agente_nw/nucleo/agrupamento/calibracao.py:107 agente_nw/nucleo/agrupamento/calibracao.py:115 agente_nw/nucleo/consulta.py:157
agente_nw/nucleo/consulta.py:43 agente_nw/nucleo/consulta.py:78 agente_nw/nucleo/consulta.py:79 agente_nw/nucleo/database/queries/conversa.py:42
agente_nw/nucleo/database/queries/conversa.py:55 agente_nw/nucleo/database/queries/conversa.py:65 agente_nw/nucleo/database/queries/conversa.py:70 agente_nw/nucleo/database/queries/conversa.py:75
agente_nw/nucleo/database/queries/conversa.py:76 agente_nw/nucleo/database/queries/conversa.py:79 agente_nw/nucleo/database/queries/conversa.py:80 agente_nw/nucleo/database/queries/conversa.py:83
agente_nw/nucleo/database/queries/conversa.py:96 agente_nw/nucleo/database/queries/fila_extracao.py:56 agente_nw/nucleo/database/queries/fila_extracao.py:57 agente_nw/nucleo/historico.py:59
agente_nw/nucleo/llm.py:589 agente_nw/nucleo/llm.py:590 agente_nw/nucleo/llm.py:592 agente_nw/nucleo/llm.py:597
agente_nw/nucleo/modelos/configuracao.py:190 agente_nw/nucleo/modelos/configuracao.py:265 agente_nw/nucleo/modelos/configuracao.py:266 agente_nw/nucleo/modelos/configuracao.py:274
agente_nw/nucleo/modelos/configuracao.py:278 agente_nw/nucleo/modelos/extracao.py:31 agente_nw/nucleo/orquestracao.py:211 agente_nw/nucleo/orquestracao.py:212
agente_nw/nucleo/prompts/cartao.py:19 agente_nw/nucleo/prompts/cartao.py:24 agente_nw/nucleo/prompts/cartao.py:29 agente_nw/nucleo/prompts/cartao.py:30
agente_nw/nucleo/prompts/cartao.py:36 agente_nw/nucleo/prompts/cartao.py:37 agente_nw/nucleo/prompts/cartao.py:39 agente_nw/nucleo/prompts/cartao.py:43
agente_nw/nucleo/prompts/extrair_de_texto.py:38 agente_nw/nucleo/prompts/extrair_de_texto.py:40 agente_nw/nucleo/prompts/extrair_de_texto.py:66 agente_nw/nucleo/prompts/extrair_de_texto.py:68
agente_nw/nucleo/prompts/extrair_de_texto.py:69 agente_nw/nucleo/prompts/prerotular_calibracao.py:13 agente_nw/nucleo/prompts/prerotular_calibracao.py:29 agente_nw/nucleo/prompts/prerotular_calibracao.py:31
agente_nw/nucleo/prompts/prerotular_calibracao.py:44 agente_nw/nucleo/prompts/prerotular_calibracao.py:46 agente_nw/nucleo/prompts/prerotular_calibracao.py:51 agente_nw/nucleo/prompts/prerotular_calibracao.py:53
agente_nw/nucleo/prompts/prerotular_calibracao.py:60 agente_nw/nucleo/prompts/prerotular_calibracao.py:62 agente_nw/nucleo/prompts/redigir_ganchos.py:142 agente_nw/nucleo/prompts/redigir_ganchos.py:146
agente_nw/nucleo/prompts/redigir_ganchos.py:261 agente_nw/nucleo/prompts/redigir_ganchos.py:277 agente_nw/nucleo/prompts/redigir_ganchos.py:87 agente_nw/nucleo/prompts/seguranca.py:34
agente_nw/nucleo/prompts/seguranca.py:35 agente_nw/nucleo/prompts/seguranca.py:5 agente_nw/nucleo/redacao.py:116 agente_nw/nucleo/redacao.py:123
agente_nw/nucleo/redacao.py:131 agente_nw/nucleo/redacao.py:141 agente_nw/nucleo/redacao.py:167 agente_nw/nucleo/redacao.py:171
agente_nw/nucleo/redacao.py:207 agente_nw/nucleo/redacao.py:208 agente_nw/nucleo/redacao.py:232 agente_nw/nucleo/redacao.py:243
agente_nw/nucleo/redacao.py:272 agente_nw/nucleo/redacao.py:273 agente_nw/nucleo/redacao.py:302 agente_nw/nucleo/redacao.py:303
agente_nw/perfil/extrator.py:55 agente_nw/perfil/extrator.py:60 config/limiares.yaml:68 scripts/migracoes/001_inicial.sql:134
```

descartada: parâmetro de limite, nome de coluna ou SQL de apresentação — 173 ocorrência(s):

```
agente_nw/cli.py:1307 agente_nw/cli.py:1430 agente_nw/cli.py:440 agente_nw/cli.py:443
agente_nw/coleta/capturas/extensao_backend.py:104 agente_nw/coleta/capturas/extensao_backend.py:119 agente_nw/coleta/capturas/extensao_backend.py:128 agente_nw/coleta/capturas/extensao_backend.py:180
agente_nw/coleta/capturas/extensao_backend.py:32 agente_nw/coleta/capturas/extensao_backend.py:34 agente_nw/coleta/capturas/extensao_backend.py:47 agente_nw/coleta/capturas/leitor.py:116
agente_nw/coleta/capturas/leitor.py:135 agente_nw/coleta/capturas/leitor.py:27 agente_nw/coleta/capturas/leitor.py:87 agente_nw/coleta/capturas/leitor.py:89
agente_nw/coleta/capturas/leitor.py:99 agente_nw/coleta/capturas/listas.py:328 agente_nw/coleta/capturas/listas.py:346 agente_nw/coleta/capturas/listas.py:355
agente_nw/coleta/capturas/listas.py:367 agente_nw/coleta/capturas/navegador.py:103 agente_nw/coleta/capturas/navegador.py:107 agente_nw/coleta/capturas/navegador.py:140
agente_nw/coleta/capturas/navegador.py:147 agente_nw/coleta/capturas/navegador.py:57 agente_nw/coleta/capturas/navegador.py:59 agente_nw/coleta/capturas/navegador.py:72
agente_nw/coleta/rss/google_news.py:52 agente_nw/coleta/rss/google_news.py:54 agente_nw/coleta/rss/google_news.py:55 agente_nw/coleta/rss/google_news.py:81
agente_nw/coleta/rss/google_news.py:84 agente_nw/coleta/rss/google_news.py:85 agente_nw/coleta/rss/leitor.py:242 agente_nw/coleta/rss/leitor.py:277
agente_nw/coleta/whatsapp/importador.py:52 agente_nw/nucleo/agrupamento/agrupador.py:77 agente_nw/nucleo/agrupamento/agrupador.py:83 agente_nw/nucleo/agrupamento/calibracao.py:177
agente_nw/nucleo/consulta.py:148 agente_nw/nucleo/consulta.py:194 agente_nw/nucleo/database/backup.py:30 agente_nw/nucleo/database/backup.py:33
agente_nw/nucleo/database/queries/assuntos.py:148 agente_nw/nucleo/database/queries/assuntos.py:250 agente_nw/nucleo/database/queries/assuntos.py:255 agente_nw/nucleo/database/queries/consulta_contato.py:46
agente_nw/nucleo/database/queries/consulta_contato.py:48 agente_nw/nucleo/database/queries/consulta_contato.py:56 agente_nw/nucleo/database/queries/consulta_contato.py:57 agente_nw/nucleo/database/queries/consulta_contato.py:78
agente_nw/nucleo/database/queries/consulta_contato.py:82 agente_nw/nucleo/database/queries/consulta_contato.py:83 agente_nw/nucleo/database/queries/consulta_contato.py:86 agente_nw/nucleo/database/queries/conversa.py:42
agente_nw/nucleo/database/queries/conversa.py:43 agente_nw/nucleo/database/queries/conversa.py:47 agente_nw/nucleo/database/queries/conversa.py:69 agente_nw/nucleo/database/queries/conversa.py:80
agente_nw/nucleo/database/queries/conversa.py:83 agente_nw/nucleo/database/queries/conversa.py:96 agente_nw/nucleo/database/queries/fatos.py:31 agente_nw/nucleo/database/queries/fatos.py:35
agente_nw/nucleo/database/queries/fatos.py:54 agente_nw/nucleo/database/queries/fila_extracao.py:32 agente_nw/nucleo/database/queries/fila_extracao.py:35 agente_nw/nucleo/database/queries/itens.py:40
agente_nw/nucleo/database/queries/itens.py:66 agente_nw/nucleo/database/queries/itens.py:69 agente_nw/nucleo/database/queries/listas.py:131 agente_nw/nucleo/database/queries/listas.py:135
agente_nw/nucleo/database/queries/nota_contato.py:39 agente_nw/nucleo/database/queries/nota_contato.py:46 agente_nw/nucleo/database/queries/pedidos.py:157 agente_nw/nucleo/database/queries/pedidos.py:159
agente_nw/nucleo/database/queries/pedidos.py:172 agente_nw/nucleo/database/queries/pedidos.py:180 agente_nw/nucleo/database/queries/pedidos.py:181 agente_nw/nucleo/database/queries/perfis.py:386
agente_nw/nucleo/database/queries/perfis.py:387 agente_nw/nucleo/database/queries/perfis.py:414 agente_nw/nucleo/database/queries/perfis.py:415 agente_nw/nucleo/database/queries/perfis.py:427
agente_nw/nucleo/database/queries/perfis.py:436 agente_nw/nucleo/historico.py:83 agente_nw/nucleo/historico.py:85 agente_nw/nucleo/localizacao.py:260
agente_nw/nucleo/modelos/configuracao.py:190 agente_nw/nucleo/modelos/configuracao.py:192 agente_nw/nucleo/modelos/configuracao.py:208 agente_nw/nucleo/modelos/configuracao.py:209
agente_nw/nucleo/modelos/configuracao.py:224 agente_nw/nucleo/modelos/configuracao.py:228 agente_nw/nucleo/modelos/configuracao.py:242 agente_nw/nucleo/modelos/configuracao.py:277
agente_nw/nucleo/modelos/configuracao.py:302 agente_nw/nucleo/modelos/configuracao.py:81 agente_nw/nucleo/modelos/pedido.py:95 agente_nw/nucleo/modelos/redacao.py:10
agente_nw/nucleo/modelos/redacao.py:101 agente_nw/nucleo/modelos/redacao.py:105 agente_nw/nucleo/modelos/redacao.py:126 agente_nw/nucleo/modelos/redacao.py:129
agente_nw/nucleo/orquestracao.py:173 agente_nw/nucleo/orquestracao.py:210 agente_nw/nucleo/orquestracao.py:213 agente_nw/nucleo/prompts/cruzar_por_que.py:79
agente_nw/nucleo/prompts/redigir_ganchos.py:18 agente_nw/nucleo/prompts/redigir_ganchos.py:194 agente_nw/nucleo/prompts/redigir_ganchos.py:195 agente_nw/nucleo/prompts/redigir_ganchos.py:214
agente_nw/nucleo/prompts/redigir_ganchos.py:216 agente_nw/nucleo/prompts/redigir_ganchos.py:25 agente_nw/nucleo/prompts/redigir_ganchos.py:280 agente_nw/nucleo/prompts/redigir_ganchos.py:281
agente_nw/nucleo/prompts/redigir_ganchos.py:284 agente_nw/nucleo/prompts/redigir_ganchos.py:289 agente_nw/nucleo/prompts/redigir_ganchos.py:292 agente_nw/nucleo/prompts/redigir_ganchos.py:297
agente_nw/nucleo/prompts/redigir_ganchos.py:298 agente_nw/nucleo/prompts/redigir_ganchos.py:7 agente_nw/nucleo/redacao.py:168 agente_nw/nucleo/redacao.py:171
agente_nw/nucleo/redacao.py:175 agente_nw/nucleo/redacao.py:183 agente_nw/nucleo/redacao.py:209 agente_nw/nucleo/redacao.py:219
agente_nw/nucleo/redacao.py:271 agente_nw/nucleo/redacao.py:274 agente_nw/nucleo/redacao.py:304 agente_nw/nucleo/redacao.py:309
agente_nw/nucleo/redacao.py:310 agente_nw/nucleo/relevancia/candidatos.py:18 agente_nw/nucleo/relevancia/candidatos.py:56 agente_nw/nucleo/relevancia/candidatos.py:63
agente_nw/nucleo/relevancia/cartoes.py:89 agente_nw/nucleo/relevancia/cartoes.py:91 agente_nw/nucleo/relevancia/qualificador.py:50 agente_nw/nucleo/relevancia/qualificador.py:55
agente_nw/perfil/extrator.py:67 agente_nw/perfil/extrator.py:75 agente_nw/perfil/inferencia.py:257 agente_nw/ponte/servidor.py:20
agente_nw/ponte/servidor.py:227 agente_nw/ponte/servidor.py:236 agente_nw/ponte/servidor.py:238 agente_nw/ponte/servidor.py:243
agente_nw/ponte/servidor.py:245 agente_nw/ponte/servidor.py:259 agente_nw/ponte/servidor.py:52 agente_nw/ponte/servidor.py:74
config/limiares.yaml:57 config/limiares.yaml:76 config/llm_routing.yaml:24 config/llm_routing.yaml:47
extensao/background.js:123 extensao/background.js:132 extensao/background.js:149 extensao/background.js:159
extensao/background.js:31 extensao/background.js:36 extensao/background.js:98 extensao/conteudo.js:107
extensao/conteudo.js:118 extensao/conteudo.js:132 extensao/conteudo.js:133 extensao/conteudo.js:145
extensao/conteudo.js:146 extensao/conteudo.js:181 extensao/conteudo.js:197 extensao/conteudo.js:69
extensao/conteudo.js:96
```

descartada: split de URL, nome ou linha de formato, não de texto de conteúdo — 16 ocorrência(s):

```
agente_nw/coleta/capturas/busca.py:104 agente_nw/coleta/capturas/busca.py:108 agente_nw/coleta/capturas/leitor.py:36 agente_nw/coleta/capturas/listas.py:175
agente_nw/coleta/capturas/listas.py:176 agente_nw/coleta/capturas/listas.py:192 agente_nw/coleta/capturas/listas.py:195 agente_nw/coleta/capturas/listas.py:212
agente_nw/coleta/capturas/listas.py:218 agente_nw/coleta/capturas/listas.py:263 agente_nw/coleta/capturas/navegador.py:53 agente_nw/nucleo/database/queries/perfis.py:35
agente_nw/nucleo/localizacao.py:62 agente_nw/nucleo/relevancia/cartoes.py:40 extensao/conteudo.js:187 scripts/agente_lacunas.py:118
```

descartada: é a própria lista de padrões da varredura (este verificador) — 13 ocorrência(s):

```
scripts/verificar_auditoria_texto.py:18 scripts/verificar_auditoria_texto.py:7 scripts/verificar_auditoria_texto.py:83 scripts/verificar_auditoria_texto.py:89
scripts/verificar_auditoria_texto.py:90 scripts/verificar_auditoria_texto.py:91 scripts/verificar_auditoria_texto.py:92 scripts/verificar_auditoria_texto.py:93
scripts/verificar_auditoria_texto.py:94 scripts/verificar_auditoria_texto.py:95 scripts/verificar_auditoria_texto.py:97 scripts/verificar_auditoria_texto.py:98
scripts/verificar_auditoria_texto.py:99
```

---

## 9. Lacunas

| # | Lacuna | Destino | Impacto |
|---|---|---|---|
| 1 | Os 45 pontos da seção 3 deste relatório esperam a decisão de Sidarta (aprovar a exceção, escrevendo a linha em `docs/EXCECOES_TEXTO_INTEGRAL.md`, ou mandar corrigir). Enquanto nenhum for decidido, o projeto quebra o princípio do texto por inteiro em 45 lugares sem aprovação registrada | decisão | degrada |
| 2 | Depois das decisões, cada correção aprovada precisa de um brief próprio (o brief 079 proíbe corrigir aqui). Os dois que eu faria primeiro: P-014 (post acima de 5.000 caracteres descartado inteiro, em silêncio) e P-034 (o `evitar` do usuário cortado em 5 itens) | backlog | degrada |
| 3 | `AGENTS.md` não cita `docs/EXCECOES_TEXTO_INTEGRAL.md` nem o princípio do texto por inteiro, e `scripts/verificar_auditoria_texto.py` não roda no gate — então nada impede que o próximo brief abra um corte novo sem passar por você. Transformá-lo em guarda permanente quebraria a cada edição de linha (o relatório cita `arquivo:linha`), então a forma certa precisa de desenho | decisão | degrada |
| 4 | O material bruto da leitura (`docs/auditoria_079_material/`, 11 arquivos, ~250 KB) vai ao GitHub junto com o relatório, por causa da regra nova do `.gitignore` que versiona `docs/**/*.md`. É a prova de que cada arquivo foi lido inteiro; se você preferir não versionar isso, é uma decisão sua (apagar a pasta não invalida o relatório) | decisão | nice |
| 5 | Ficaram fora do universo, por não serem código: os 18 templates HTML do console e as 8 fixturas de dados de `tests/fixtures/` (CSV, TXT, ZIP e JSON). Os templates só apresentam, e as fixturas estão cobertas na linha do teste que as lê, mas nenhum dos dois foi auditado linha por linha | dívida | nice |
| 6 | A coluna "Commit que introduziu" de cada ponto vem de `git blame`, que dá o **último toque** na linha, não necessariamente a introdução do corte. Onde os dois diferem e isso importa (P-040, P-042), o ponto diz; nos outros 43 a diferença não foi conferida um por um | dívida | nice |
| 7 | Nenhum teste do projeto cobre resposta de modelo cortada por `num_predict` que ainda seja JSON válido (seção 7). Isso vale tanto para o Ollama quanto para os três provedores de API do brief 075 | dívida | degrada |
