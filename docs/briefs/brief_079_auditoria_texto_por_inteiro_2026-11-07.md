# Brief 079 — Auditoria de "texto por inteiro" em todo o código do projeto

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Conjunto:** nenhum — brief único (só leitura do código de produção)
**Arquivos-alvo:** `docs/docs/doc_079_auditoria_texto_por_inteiro_<data>.md` (o relatório), `docs/EXCECOES_TEXTO_INTEGRAL.md` (registro de exceções, criado vazio), `scripts/verificar_auditoria_texto.py` (novo), `tests/test_verificar_auditoria_texto.py` (novo), `logs/commit_079.txt`, `logs/arquivos_079.txt`, linhas do `docs/PLAN.md`. **Nenhum arquivo de código de produção é alterado.**
**Seções a ler:** `AGENTS.md` inteiro; no `docs/PLAN.md`, a armadilha 1 (`num_ctx` padrão do Ollama trunca em silêncio) e as armadilhas da área de cada módulo lido; `docs/ARQUITETURA.md` §8 (Ollama, perfis, provedores de API); a seção 4 do relatório 078 (`docs/docs/doc_078_relatorio_para_repositorio_de_referencias_2026-11-07_v2.md`), se estiver no disco — os pontos de partida também estão copiados na seção 2.2 deste brief, então a ausência do arquivo não bloqueia
**Modelo:** Opus — o trabalho é ler centenas de arquivos inteiros e julgar, em cada um, se um texto chega ao LLM, ao embedding ou a um classificador por inteiro; um julgamento apressado reproduz exatamente o erro que o brief quer caçar
**Esforço:** alto
**Teste de aceite:** `tests/test_verificar_auditoria_texto.py` (prova que o verificador funciona) e a saída de `python scripts/verificar_auditoria_texto.py` sobre o relatório real, colada no relatório
**Depende de:** nenhum. (Recomendado, não obrigatório: Sidarta ter rodado o commit/push do relatório 078.)
**Data:** 2026-11-07

---

## 1. Objetivo em uma frase

Garantir que nenhum código do projeto analise só uma parte de um texto sem que isso esteja à vista: o relatório lista **todos** os arquivos de código, certifica um a um que não há esse problema e, onde há, mostra a situação e a justificativa para **Sidarta** aprovar ou mandar corrigir.

---

## 2. Achados e definições

**2.1. O princípio (decisão do dono do projeto).** O texto integral é um princípio muito importante: quando o projeto analisa um texto (notícia, página, mensagem, comentário, histórico), analisa o texto inteiro. O princípio só pode ser quebrado se houver **justificativa aprovada por Sidarta**. Sem aprovação dele, o ponto é violação — mesmo que o código tenha um comentário explicando e mesmo que o executor ache a razão boa.

**2.2. Pontos de partida já conhecidos (relatório 078, seção 4).** Não são a lista fechada; são onde a auditoria começa. Cada um deve ser reconfirmado no código atual (arquivo, linha, commit) ou marcado como "já não existe":

| Ponto | O que corta | Commit citado no 078 |
|---|---|---|
| `nucleo/relevancia/qualificador.py::_itens_recentes_resumidos` | só título e domínio dos 5 itens mais recentes | 4954eff |
| `nucleo/relevancia/cartoes.py` (`_TRUNCAMENTO_TRECHO=300`, 5 itens) | trecho de 300 caracteres | 4954eff |
| `nucleo/agrupamento/agrupador.py:88` | `texto[:2000]` | 06ba8e0 |
| `nucleo/agrupamento/calibracao.py` | mesmo corte de 2000 | 06ba8e0 |
| `nucleo/redacao.py` | 3 manchetes só pelo título; fatos 600, notas 400 | ea26737, 657edaa, 2c31eac |
| `nucleo/historico.py` | mensagem 100, comentário 300 | não conferido no 078 |
| `nucleo/prompts/redigir_ganchos.py::cortar_por_tamanho` | 6.000 tokens estimados (palavras × 1,4) | ea26737 |
| `coleta/rss/ruido.py` | só as 3 primeiras linhas | 9098879 |
| `coleta/capturas/leitor.py` | `maximo_blocos_por_rede` 10 × 4 blocos | 9a8bb96, 657edaa |
| `coleta/capturas/extensao_backend.py:93` | 200000 caracteres | 906d759 |
| `config/limiares.yaml` | imagens 8, largura 250; WhatsApp `meses_extraidos` 24 e `trocas_no_prompt` 10 | 4366f01 |
| `perfil/extrator.py:80` | manda `item.texto` inteiro **sem conferir** se cabe no `num_ctx` | não conferido |
| `nucleo/llm.py:352` | só repassa `num_ctx`, não confere o tamanho do prompt | 9598a8e |
| `coleta/rss/leitor.py:338` | `trafilatura.extract` sem teto (o contrário: aqui o texto vai inteiro; confirmar) | não conferido |

**2.3. Quatro formas de o problema aparecer (as classes usadas no relatório).**

- **T — Truncamento do texto de um item:** `[:N]`, `max_chars`, `textwrap.shorten`, `.slice(0, N)`, `.substring`, só as primeiras linhas, só o primeiro parágrafo, hash/dedup/regex sobre um prefixo.
- **C — Corte de coleção:** analisa só parte dos itens, das mensagens ou dos meses de um conjunto (os "5 mais recentes", `LIMIT`, `[-N:]`, `fetchmany`, `islice`, `random.sample`, "top N" que descarta o resto sem avisar).
- **R — Representação parcial:** o texto é trocado por algo menor antes da análise (só título, só domínio, resumo, trecho) e a análise decide como se tivesse visto o texto.
- **P — Prompt maior que a janela:** o texto vai inteiro para o prompt, mas ninguém confere se o prompt cabe no `num_ctx` (Ollama) ou no limite de entrada do modelo (APIs e `bge-m3`, que corta em silêncio acima de 8.192 tokens). É a armadilha 1 do PLAN; **só `cortar_por_tamanho` tem estimador hoje**.

**2.4. O que não é violação, mas precisa estar listado.** Corte que só afeta **apresentação ou log** (mensagem de erro, `print`, linha de `chamadas_llm.jsonl`, rótulo de tela) e corte de **identificador** (`hash[:8]`, slug, nome de arquivo) não alimentam nenhuma análise. Vão numa tabela à parte (seção 4 do relatório), cada um com a prova de que o valor cortado não entra em decisão nenhuma. Sidarta pode contestar qualquer linha dessa tabela.

**2.5. Achado adjacente (registrar, não bloqueia).** Se uma resposta do modelo pode vir cortada (`num_predict` baixo, `done_reason == "length"`) e o código a trata como completa, isso é o problema irmão na saída. Registrar em tabela própria, sem classificar como violação.

---

## 3. Decisões

**3.1. O executor não aprova exceção, não corrige e não escreve "aprovado" em lugar nenhum.** Só Sidarta aprova. Todo ponto encontrado nasce com o estado `AGUARDANDO DECISÃO DE SIDARTA`. O executor **pode e deve** propor a justificativa que veria como a melhor (marcada "proposta do executor"), e dizer o que custaria corrigir, mas a decisão é do dono. *Razão: o princípio é do dono; quem audita não pode ser quem absolve.*

**3.2. Nenhum código de produção é alterado neste brief, nem quando a correção parecer óbvia.** Cada correção vira um brief próprio, que Sidarta manda escrever depois de decidir. *Razão: misturar auditoria e correção esconde o que foi achado.*

**3.3. Certificar exige ler o arquivo inteiro, não procurar padrão.** Para cada arquivo o executor lê do início ao fim (arquivo grande: em partes, até a última linha) e registra `linhas lidas / linhas do arquivo`. Uma busca por `[:` que não acha nada **não** certifica nada: o corte pode estar em `.split("\n")[0]`, num `LIMIT` dentro de uma consulta SQL, numa função que só recebe o título. A busca mecânica (seção 6, passo 3) serve para **não deixar escapar**, não para certificar. *Razão: ler só um pedaço do arquivo para certificar que ninguém lê só um pedaço seria repetir o erro.*

**3.4. A certificação é por arquivo, tem três resultados e nenhum é o padrão.**

- `CERTIFICADO` — li o arquivo inteiro e nele nenhum texto de conteúdo é analisado só em parte. Exige uma linha de evidência: o que o arquivo faz com texto (ou "não manipula texto de conteúdo: só infraestrutura") e, se manipula, como o texto passa por inteiro.
- `CORTA — P-nnn` — há pelo menos um ponto da seção 3 do relatório neste arquivo.
- `NÃO ANALÍTICO — NA-nnn` — o arquivo só tem cortes de apresentação/log/identificador (seção 4 do relatório), todos listados.
- `NÃO CONFERIDO` — se por qualquer razão o executor não leu o arquivo inteiro. Nunca se promove a `CERTIFICADO` por falta de evidência.

**3.5. A auditoria olha o caminho do texto, não só cada arquivo.** Um arquivo pode estar limpo e receber o texto já cortado de outro. Por isso o relatório tem, além da tabela por arquivo, um **rastreio ponta a ponta** (seção 5 do relatório): para cada origem de texto (item de RSS, captura de rede social, mensagem de WhatsApp, histórico, perfil do usuário, pedido em texto livre, comentário do usuário), a cadeia entrada → cada consumidor (LLM, embedding, classificador, deduplicação, agrupamento), dizendo em que arquivo e linha o texto é cortado ou "chega inteiro".

**3.6. Conferência de janela, por chamada de LLM e de embedding.** Para cada ponto onde o projeto chama o Ollama, uma API (`anthropic`, `gemini`, `openai`) ou `embeddar`, o relatório diz: qual é o maior texto que pode chegar ali (dado do código ou do banco de teste, não suposição), qual é o `num_ctx`/limite configurado para o perfil `air16` e para o `pro48`, e se existe conferência que impeça o corte silencioso. Sem conferência, o ponto é classe **P**. Não se mede o banco real (`agente.db`); usa-se o código, `config/limiares.yaml`, `config/perfis` e fixtures de teste.

**3.7. Universo de arquivos (o que "todos os códigos" quer dizer).** Entram, sem escolher:

- `agente_nw/**/*.py`, `config/**/*.py`, `config/**/*.yaml`, `scripts/**/*.py` e `scripts/**/*.sh`, `extensao/**/*.js` (e `*.json` de manifesto, se houver), arquivos `.sql` de migração, `*.py` na raiz do repositório;
- `tests/**/*.py`: entram na tabela, mas com certificação simplificada — o teste só precisa dizer se **constrói** entrada que esconde um corte (uma fixture que já chega cortada, por exemplo) ou se apenas exercita o código. Teste não gera ponto P/T/C/R.

Ficam fora: `.venv/`, `node_modules/`, `__pycache__/`, `dados/`, `logs/`, `docs/` (a documentação é auditada por outro brief), `.git/`. O verificador (passo 5) enumera o universo sozinho com esta mesma regra e confere que **cada** arquivo aparece **uma vez** no relatório.

**3.8. Registro de exceções.** `docs/EXCECOES_TEXTO_INTEGRAL.md` nasce com cabeçalho, a regra do 3.1 e a tabela vazia `| Ponto | Arquivo:função | O que é cortado | Justificativa aprovada | Aprovado por Sidarta em |`. Só Sidarta (ou um brief dele) escreve ali. O verificador aceita o estado `EXCEÇÃO APROVADA` num ponto somente se o registro tiver uma linha com o mesmo identificador e o texto "Aprovado por Sidarta em AAAA-MM-DD". O relatório do executor **não** usa esse estado.

---

## 4. Escopo (arquivos)

| Arquivo | Criar / alterar | O que muda |
|---|---|---|
| `docs/docs/doc_079_auditoria_texto_por_inteiro_2026-11-07.md` | criar | O relatório (estrutura na seção 7 abaixo). |
| `docs/EXCECOES_TEXTO_INTEGRAL.md` | criar | Registro vazio de exceções aprovadas (3.8). |
| `scripts/verificar_auditoria_texto.py` | criar | Verificador do relatório (passo 5). Tipado, sem dependência nova; segue o padrão dos outros scripts. |
| `tests/test_verificar_auditoria_texto.py` | criar | Testa o verificador contra árvores e relatórios sintéticos em `tmp_path` (seção 5 deste brief). |
| `logs/commit_079.txt`, `logs/arquivos_079.txt` | criar | Manifesto do commit. |
| `docs/PLAN.md` | alterar | Linhas Resumo, Doing e Done; mais as lacunas do relatório (`agente_lacunas.py`). |

Nada mais. Em particular, nenhum `.py` de `agente_nw/`, `config/`, `extensao/` nem `tests/` existente é tocado.

---

## 5. Testes

`tests/test_verificar_auditoria_texto.py` não toca o repositório real: monta, em `tmp_path`, uma árvore mínima (dois ou três `.py`, um `.js`, um `.yaml`) e um relatório sintético, e chama o verificador (se `scripts/` não for pacote importável, carregar por caminho com `importlib`, como já fazem os outros testes do projeto, se houver precedente). Casos:

1. **Relatório completo e correto** → o verificador devolve código 0.
2. **Arquivo do universo ausente do relatório** → código ≠ 0, a mensagem cita o arquivo.
3. **Arquivo aparecendo duas vezes** → falha.
4. **Contagem de linhas errada** (`linhas lidas/total` diferente do `wc -l` real) → falha, citando o arquivo.
5. **`CERTIFICADO` sem linha de evidência** → falha.
6. **`CORTA — P-001` sem o ponto P-001 na seção 3** → falha.
7. **Ponto da seção 3 sem algum campo obrigatório** (arquivo:linha, classe, o que é cortado, tamanho do corte, efeito, commit, justificativa existente ou "nenhuma", justificativa proposta, estado) → falha.
8. **Estado `EXCEÇÃO APROVADA` sem linha correspondente em `EXCECOES_TEXTO_INTEGRAL.md`** → falha; **com** a linha "Aprovado por Sidarta em 2026-11-08" → passa.
9. **Acerto da varredura mecânica:** arquivo sintético com `x[:200]` marcado `CERTIFICADO` sem que a linha apareça nas seções 3 ou 4 → falha; a mesma linha listada na seção 4 (`NA-001`) → passa.
10. **`NÃO CONFERIDO`** é aceito pelo verificador (é honesto), mas o resumo do verificador o conta e o código de saída é 2 (aviso), não 0.
11. **Padrões da varredura:** teste parametrizado com um exemplo de cada padrão da seção 6, passo 3 (inclusive o de JS), provando que cada um é detectado.

O verificador **não** valida se o julgamento do executor está certo — isso é papel de Sidarta lendo os pontos. Ele só garante que nada ficou fora, que nada foi certificado sem leitura registrada, e que nenhuma exceção foi dada por quem não pode.

---

## 6. Passos de execução

1. Conferir a seção "Depende de" (nada obrigatório). Ler o `AGENTS.md`, a armadilha 1 do PLAN e a seção 2.2 deste brief.
2. Escrever os testes da seção 5 (antes do verificador).
3. **Varredura mecânica, para não deixar escapar** (apêndice A do relatório, com o comando e a saída):
   - Python: `\[\s*:\s*[\w.]+\s*\]`, `\[\s*-\s*\d+\s*:\s*\]`, `\[\s*\d+\s*:\s*\d+\s*\]` aplicado a texto, `max_chars`, `max_len`, `maxlen`, `max_tokens`, `num_predict`, `num_ctx`, `truncat`, `cortar`, `shorten`, `islice`, `fetchmany`, `LIMIT`, `limit=`, `top_k`, `n_results`, `.head(`, `splitlines()[`, `.split(` seguido de `[`, `random.sample`, `[0]` sobre lista de linhas ou parágrafos, `trafilatura`, `.read(` com tamanho, `chunk`, `sample`, `resum`;
   - JavaScript (`extensao/`): `.slice(`, `.substring(`, `.substr(`, `innerText` com corte, `textContent` com corte, `.slice(0`;
   - YAML e SQL: toda chave que limite quantidade, tamanho, janela ou número de itens (`max`, `limite`, `maximo`, `trocas`, `meses`, `blocos`, `trecho`, `LIMIT`, `OFFSET`).
   Cada ocorrência recebe uma linha no apêndice com o arquivo, a linha, o texto da linha e o destino (`P-nnn`, `NA-nnn` ou "descartada: <razão>"). Nenhuma ocorrência fica sem destino.
4. **Leitura arquivo por arquivo** (3.3), pacote por pacote. Para cada arquivo: ler inteiro; anotar `linhas lidas/total` (conferir com `wc -l`); decidir entre `CERTIFICADO`, `CORTA`, `NÃO ANALÍTICO`, `NÃO CONFERIDO`; abrir ponto na seção 3 ou 4 quando for o caso. Para cada ponto da seção 3, descobrir o commit que introduziu o corte (`git log -S'<trecho>' --oneline -- <arquivo>` ou `git blame --no-optional-locks`; só leitura) e registrar também **se existe justificativa escrita** no código, no PLAN, no AGENTS ou em outro brief (citar onde), distinguindo-a de "nenhuma". Se o executor dividir a leitura entre subagentes, cada um lê os arquivos inteiros, e o executor refaz a leitura de **todo arquivo que monta prompt, chama LLM ou embedding, ou lê dado de coleta** antes de assinar a certificação. Quem assina é o executor.
5. **Rastreio ponta a ponta e conferência de janela** (3.5 e 3.6): preencher as seções 5 e 6 do relatório.
6. Escrever `scripts/verificar_auditoria_texto.py`. Entrada: caminho do relatório (padrão: o `doc_079_*` mais recente) e a raiz do repositório. Faz: enumera o universo (3.7); lê a tabela de certificação e confere cada arquivo uma vez, a contagem de linhas, a evidência e a coerência com as seções 3 e 4; refaz a varredura mecânica (mesmos padrões do passo 3) e exige que cada ocorrência esteja citada nas seções 3 ou 4 ou no apêndice A com destino; confere o registro de exceções (3.8). Imprime um resumo (`N arquivos, X certificados, Y cortam, Z não analíticos, W não conferidos, K pontos aguardando`) e devolve 0 (tudo coerente), 1 (inconsistência) ou 2 (coerente, mas com `NÃO CONFERIDO`). Ele **não toca** o código auditado.
7. Rodar o verificador sobre o relatório real e corrigir o **relatório** (nunca o verificador, para fazê-lo passar) até devolver 0, ou 2 com cada `NÃO CONFERIDO` explicado na seção "Lacunas".
8. Criar `docs/EXCECOES_TEXTO_INTEGRAL.md` (3.8) vazio.
9. Escrever o relatório final, o manifesto (`logs/commit_079.txt` com a mensagem do commit e `logs/arquivos_079.txt` com os 6 caminhos novos) e as linhas do PLAN. Rodar `scripts/agente_entregar.sh 079` (no máximo 3 tentativas, como manda o `/executar`).
10. Terminar com três linhas: caminho do relatório; o que foi feito, com o hash; e — **sempre**, porque há decisão de produto — `Para você: decidir os N pontos em aberto da seção 3 do relatório (aprovar exceção ou mandar corrigir).` com N real. (Se N for 0: `Nada para você.`)

O executor não roda `git` de escrita nem a suíte além do gate; leitura (`git log -S`, `git blame --no-optional-locks`, `git ls-files`) é permitida. Não toca `agente.db` real nem lê rede social.

---

## 7. Estrutura do relatório (`doc_079_...`)

Cabeçalho do AGENTS §8. Depois:

1. **Resumo para Sidarta** (≤ 15 linhas, linguagem simples): quantos arquivos, quantos certificados, quantos pontos precisam da sua decisão, os 5 mais graves em uma linha cada, e o que o verificador devolveu (código e saída colada).
2. **Método** (o universo, as regras de 3.3 e 3.4, os comandos rodados, a saída do verificador).
3. **Pontos que cortam o texto — aguardando decisão** (tabela por ponto `P-nnn`): arquivo:linha:função; classe (T, C, R ou P); o que é cortado e quanto; qual decisão do produto depende desse corte; commit que o introduziu; justificativa existente (com a citação do lugar) ou "nenhuma"; **proposta do executor** (justificativa possível *e* custo de corrigir); estado `AGUARDANDO DECISÃO DE SIDARTA`; e, em branco, `Decisão de Sidarta: ____` (aprovar exceção / mandar corrigir / outra).
4. **Cortes que não analisam texto (apresentação, log, identificador)** — `NA-nnn`, cada um com a prova de que o valor cortado não entra em decisão.
5. **Rastreio ponta a ponta** (3.5), por origem de texto, e a **conferência de janela** por chamada de LLM/embedding (3.6), em tabela: `Chamada | Maior texto possível | num_ctx / limite (air16, pro48) | Conferência de tamanho existe? | Classe`.
6. **Certificação por arquivo** — uma tabela com **todos** os arquivos do universo: `Arquivo | Linhas lidas/total | Resultado | Evidência (uma linha) | Ponto`. Abaixo da tabela, a frase: *"Certifico que, nos arquivos marcados CERTIFICADO, li o arquivo inteiro e nenhum texto de conteúdo é analisado só em parte. Os demais estão nas seções 3 e 4 ou marcados NÃO CONFERIDO."*
7. **Achados adjacentes** (2.5): respostas que podem vir cortadas.
8. **Apêndice A** — a varredura mecânica com o destino de cada ocorrência.
9. **Lacunas** (tabela do AGENTS: `# | Lacuna | Destino | Impacto`), incluindo, se o executor concordar, a lacuna "citar `docs/EXCECOES_TEXTO_INTEGRAL.md` no AGENTS e transformar o verificador em guarda permanente do gate" (destino: decisão de Sidarta).

---

## 8. Fora de escopo

- Corrigir qualquer ponto encontrado (um brief por decisão de Sidarta; sem número).
- Transformar o verificador em teste permanente do gate, que quebraria a cada edição de linha de código (decisão de Sidarta; sem número).
- Auditar a documentação (`docs/`) e o conteúdo já gravado no banco (cartões, assuntos e resumos já cortados no passado); o banco real não é lido (sem número).
- Alterar `AGENTS.md` para citar o registro de exceções (entra como lacuna).

---

## 9. Critérios de aceite

Cada um com a saída colada no relatório:

1. `pytest tests/test_verificar_auditoria_texto.py -q` passa (os 11 casos da seção 5).
2. `python scripts/verificar_auditoria_texto.py` sobre o relatório real devolve 0, ou 2 com cada `NÃO CONFERIDO` justificado; o resumo impresso confere com a seção 1 do relatório.
3. O número de arquivos da tabela de certificação é igual ao do universo enumerado pelo verificador (saída colada).
4. Cada ocorrência da varredura mecânica tem destino (o verificador comprova).
5. Cada ponto da seção 3 tem todos os campos, inclusive commit e "justificativa existente ou nenhuma", e estado `AGUARDANDO DECISÃO DE SIDARTA`.
6. Os 14 pontos de partida da seção 2.2 aparecem no relatório como ponto `P-nnn` ou como "já não existe/não é corte", com o motivo.
7. `git diff --stat` (leitura) mostra que **somente** os seis arquivos do escopo foram criados/alterados; nenhum arquivo de produção.
8. `docs/EXCECOES_TEXTO_INTEGRAL.md` existe e tem a tabela vazia.
9. `scripts/agente_entregar.sh 079` conclui (gate ruff, mypy, pytest verdes; commit só do manifesto; push).
