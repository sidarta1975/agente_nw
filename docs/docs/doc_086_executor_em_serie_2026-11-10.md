# Relatório 086 — Executor em série: rodar vários briefs, um depois do outro, sem acompanhamento

**Brief:** `docs/briefs/brief_086_executor_em_serie_2026-11-08.md` (v2, com o item 2.10)
**Data:** 2026-11-10
**Modelo e esforço do cabeçalho:** Opus, esforço alto

---

## 1. O que passou a existir

`scripts/executar_serie.sh 080 081 087 082` roda os briefs da lista um depois do outro, cada um numa
sessão nova do Claude Code, confere por conta própria se cada um **entregou de verdade**, para na
primeira falha e avisa por notificação do macOS. O sinal de sucesso não é o código de saída do Claude
Code — uma parada correta do `/executar` também sai com 0, provado no relatório 085, item 2.2.

Junto com ele, três ajustes que a série exige: o `docs/PLAN_agente_nw.md` deixa de ficar sujo depois do
commit (item 2.4 do brief), a trava passa a liberar `git worktree list` (2.7) e a liberar comando
`agente_nw` **de leitura apontando para uma cópia do banco** (2.10), que era o que impedia a medição
dos briefs 089 e 095 de rodar sem ninguém por perto.

Nada neste brief grava no git: o único caminho para commitar continua sendo o
`scripts/agente_entregar.sh` (AGENTS §5). O critério de aceite 2 prova isso por `grep`.

## 2. Arquivos

| Arquivo | Criado / alterado | O que mudou |
|---|---|---|
| `scripts/executar_serie.sh` | criado (279 linhas) | Pré-voo de seis conferências, laço por brief com `claude -p "/executar NNN"`, conferência de entrega em seis itens, `STATUS.txt`, notificação, `caffeinate`, trava de instância |
| `.claude/serie.settings.json` | criado | Permissões da série (item 2.5): o `allow` do projeto mais `mkdir`, `cp`, `mv`, `sed` e `python3 scripts/*`; o `deny` do projeto repetido; os dois hooks repetidos, para a trava valer mesmo que o arquivo substitua o do projeto em vez de somar |
| `scripts/agente_entregar.sh` | alterado | As lacunas do relatório vão para o PLAN **antes** do commit (passo 1b novo); a linha de contagem continua impressa no mesmo lugar da saída; em `--simular` não roda nada |
| `.claude/hooks/guarda_comando.py` | alterado | `git worktree list` passa (2.7); `agente_nw` de leitura em cópia passa com as cinco condições (2.10) |
| `AGENTS_agente_nw.md` | alterado | §10: a frase "o script nasce no brief 086" dá lugar à frase que diz que o script existe e como se usa (2.9) |
| `tests/test_executar_serie.py` | criado (21 testes) | Seção 4 do brief |
| `tests/test_guarda_comando.py` | alterado | 132 linhas **acrescentadas**, nenhuma removida: os casos do 2.10 e do 2.7 |
| `scripts/agente_lacunas.py` | **não alterado** | O item 2.4 não exigiu: o script já aponta para `docs/PLAN_agente_nw.md` e é idempotente (a marca `[NNN-#]` já no PLAN é pulada), então rodar antes do commit bastou |

## 3. As barreiras do relatório 085, uma por uma

| Barreira do 085 | Como foi resolvida | Teste |
|---|---|---|
| A1 — o script da série não existe | `scripts/executar_serie.sh` | `tests/test_executar_serie.py` inteiro |
| A2 — árvore suja | pré-voo recusa a série com `git status --porcelain` não vazio, imprimindo o que está sujo | `test_arvore_suja_nem_comeca` |
| A3 — parada do `/executar` sai com 0 | a conferência de entrega de seis itens, nunca o código de saída | `test_saida_zero_sem_manifesto_para_e_nao_tenta_o_seguinte`, `test_primeira_linha_com_parou_para_a_serie`, `test_is_error_verdadeiro_para_a_serie` |
| A4 — PLAN sujo depois do commit | `agente_lacunas.py` roda no passo 1b, antes do commit, e o PLAN entra no manifesto | `tests/test_agente_entregar.py` (16 testes, sem edição) e o critério de aceite 3 |
| A5 — comandos de terminal fora do `allow` | `.claude/serie.settings.json`, passado por `--settings`; o `.claude/settings.json` da sessão interativa não muda | o script só passa `--settings` quando o arquivo existe (`test_dois_briefs_entregues_concluem_a_serie` roda sem ele) |
| A6 — limite da assinatura | `--max-budget-usd` e `--max-turns` por brief (constantes no topo, ajustáveis por `SERIE_MAX_BUDGET_USD` e `SERIE_MAX_TURNS`); a conferência pega a parada e o `STATUS.txt` traz o comando para retomar | `test_is_error_verdadeiro_para_a_serie` (estouro chega como `subtype` diferente de `success`) |
| A7 — outras sessões na mesma árvore | trava de instância `logs/serie/TRAVA`, uma série por vez, removida no fim | `test_trava_de_instancia_recusa_a_segunda_serie`, `test_trava_de_instancia_e_removida_no_fim` |
| A8 — push dependente do Chaveiro | a conferência `origin/main..HEAD = 0` pega, e o `STATUS.txt` traz o comando de envio | `test_commit_sem_push_para_e_o_status_traz_o_comando_de_envio` |
| A9 — "Para você" do 083 | pendência humana que não impede o commit vira linha de pendência no `STATUS.txt` e a série segue | `test_para_voce_sem_parou_vira_pendencia_e_a_serie_segue` |
| A10 — `git worktree list` bloqueado | a trava passa a deixar passar `worktree list`; `add`, `remove` e `prune` seguem bloqueados | `test_worktree_list_e_leitura_e_passa`, `test_worktree_de_escrita_continua_bloqueado` |
| A11 — Mac dormir | `caffeinate -dimsu` em volta da série inteira (o script se re-executa dentro dele) e recusa quando o Mac está na bateria | `test_caffeinate_e_osascript_sao_chamados`, `test_energia_na_bateria_nem_comeca` |

## 4. O item 2.10, condição por condição

| Condição do 2.10 | Como a trava confere | Teste |
|---|---|---|
| 1. subcomando na lista fechada de leitura | conjunto `AGENTE_NW_LEITURA_EM_COPIA` = `comparar-vetores`, `medir-dano`, `reprocessar`; o resto cai na decisão de hoje (`ask`) | `test_leitura_apontando_para_a_copia_passa`, `test_subcomando_fora_da_lista_de_leitura_continua_perguntando` |
| 2. o comando traz `--banco <caminho>` | `_valor_da_opcao`, que entende `--banco valor` e `--banco=valor`; sem a opção, devolve `ask` | `test_leitura_sem_apontar_a_copia_continua_perguntando` |
| 3. o caminho não é o banco real | bloqueia qualquer argumento que cite `agente.db`; e, pelo caminho resolvido (`Path.resolve()`, que desfaz `..` e link simbólico), bloqueia o que cai dentro de `dados/` | `test_tentativa_de_driblar_a_copia_e_bloqueada`, `test_link_simbolico_para_o_banco_real_e_bloqueado`, `test_pasta_que_e_link_para_dados_e_bloqueada` |
| 4. o caminho é literal | bloqueia se o valor tiver `$`, `` ` ``, `~`, `*` ou `?` — a trava lê o texto do comando e não sabe no que uma variável se transforma na hora de rodar | `test_tentativa_de_driblar_a_copia_e_bloqueada` (casos `$BANCO`, `"$HOME/..."`, `~/...`, `$(echo ...)`, `/tmp/*.db`) |
| 5. `reprocessar` só em simulação | exige `--simular` e recusa `--confirmo` | `test_tentativa_de_driblar_a_copia_e_bloqueada` (três casos) |

Leitura que eu precisei fixar e que o brief não escreve com estas palavras: **"não é o banco real" ficou
sendo "não mora em `dados/`"**. Razão: o `--banco` pode apontar para um arquivo que ainda não existe (a
cópia é criada na mesma linha de comando), e aí não há link simbólico para resolver no último pedaço do
caminho; resolver a pasta que o contém e recusar tudo que cai em `dados/` fecha a porta sem depender de
o arquivo já existir. O efeito prático é que a cópia tem de ficar fora de `dados/` (por exemplo em
`/tmp`), o que é mais restrito que o texto do brief, nunca menos.

O que **não** mudou na trava: `ler-rede-social`, `pedir`, `extensao` e `listas atualizar` seguem
bloqueados mesmo com `--banco` de cópia (`test_rede_social_continua_bloqueada_mesmo_com_copia`);
`sqlite3` sobre `agente.db` segue bloqueado; git de escrita segue bloqueado; qualquer outro `agente_nw`
na pasta principal segue perguntando. **Nenhuma proteção foi afrouxada.** A lista de 24 comandos
bloqueados e a de 30 liberados que já existiam no teste continuam passando sem uma asserção editada.

## 5. O item 2.4, e por que a saída não mudou de lugar

O `agente_lacunas.py` passou a rodar no passo **1b**, logo depois de o manifesto ser lido e **antes** da
conferência "nada fora da lista". Três consequências de propósito:

1. a alteração do PLAN entra no commit do próprio brief, e a árvore fica limpa depois dele — que é o que
   a série precisa (barreira A4);
2. se o executor esquecer o `docs/PLAN_agente_nw.md` no manifesto, a conferência do passo 2 agora acusa
   ("há arquivo fora da lista"), em vez de o PLAN ficar sujo em silêncio depois do commit;
3. em `--simular` não roda nada: a simulação não toca em arquivo nenhum, e passou a imprimir a linha
   `1b.` dizendo o que rodaria.

A **linha de contagem** das lacunas continua impressa no mesmo ponto da saída (penúltima linha, antes do
`✓ brief NNN: commit ...`), porque ela é guardada numa variável e só impressa no fim. Foi assim que a
mudança de ordem não exigiu editar nenhuma asserção de `tests/test_agente_entregar.py`, que afirma
exatamente essa ordem — os 16 testes daquele arquivo passam sem uma linha alterada.

## 6. Como o script decide que um brief entregou

Por brief, em sessão nova: `claude -p "/executar NNN" --model <do cabeçalho> --effort <do cabeçalho>
--permission-prompts none --max-turns ... --max-budget-usd ... --output-format json` (mais
`--settings .claude/serie.settings.json`, quando o arquivo existe), com o JSON cru guardado em
`logs/serie/<data>/NNN.json`. Depois, **ignorando o código de saída**, as seis conferências:

1. `is_error` falso e `subtype` igual a `success` no JSON;
2. a primeira das três linhas finais não começa com `PAROU:`;
3. `logs/entregue_<NNN>_commit.txt` e `logs/entregue_<NNN>_arquivos.txt` existem;
4. o assunto do commit mais novo cita o número do brief;
5. `git rev-list --count origin/main..HEAD` é 0;
6. `git status --porcelain` está vazio.

Falhou qualquer uma: a série **para**, grava `logs/serie/<data>/STATUS.txt` (brief, motivo, custo somado,
comando para retomar), notifica e sai com 1 — sem tentar o brief seguinte. Brief já entregue (manifesto
`entregue_*` no disco) é pulado, o que permite retomar com a mesma lista.

O pré-voo, antes da primeira chamada: trava de instância; energia na tomada; árvore limpa; nada pendente
de envio; um arquivo por número de brief; `Modelo`, `Esforço` e `Ordem em série` presentes e legíveis; e a
ordem da lista conferida contra `depois de` / `antes de`. Texto de ordem fora das formas aceitas (por
exemplo "antes de qualquer brief que suba tetos de texto") é impresso como aviso e **não** é aplicado,
como manda o item 2.3.

## 7. Saída dos comandos

Testes do brief:

```
$ .venv/bin/pytest tests/test_executar_serie.py tests/test_guarda_comando.py -q
........................................................................ [ 62%]
...........................................                              [100%]
115 passed in 35.78s
```

Critério de aceite 2 — o script não tem git de escrita nem simulação:

```
$ grep -nE "git (add|commit|push)|--simular" scripts/executar_serie.sh
código de saída do grep: 1
```

Critério de aceite 4 — o teste da trava só cresceu:

```
$ git diff --numstat tests/test_guarda_comando.py
132	0	tests/test_guarda_comando.py
$ git diff tests/test_guarda_comando.py | grep -c "^-[^-]"
0
```

Estabilidade do teste novo (três corridas seguidas, por causa de um defeito que apareceu e foi
corrigido — ver seção 8):

```
$ for i in 1 2 3; do .venv/bin/pytest tests/test_executar_serie.py -q | tail -1; done
21 passed in 21.61s
21 passed in 25.21s
21 passed in 28.69s
```

Gate completo, rodado por mim antes de entregar:

```
$ scripts/verificar.sh
ruff check: ok
ruff format: ok
mypy: ok
pytest: ok (1086 passed, 5 deselected in 66.59s (0:01:06))
```

A entrega, com o gate rodado **pelo `scripts/agente_entregar.sh`** (é esta a saída que o AGENTS §8 pede):

```
$ scripts/agente_entregar.sh 086
manifesto 086: 9 arquivo(s)
ruff check: ok
ruff format: ok
mypy: ok
pytest: ok (1086 passed, 5 deselected in 57.90s)
lacunas do 086: 1 no Backlog, 0 em Pendências, 4 em Dívidas, 2 em Decisões
✓ brief 086: commit e491463, enviado ao GitHub
```

Critério de aceite 3 — a árvore fica limpa depois da entrega, e as lacunas entraram **dentro** do
commit (é a prova de ponta a ponta do item 2.4):

```
$ git status --porcelain -uall
            (vazio)
$ git rev-list --count origin/main..HEAD
0
$ git show e491463 --stat | tail -4
 scripts/executar_serie.sh                         | 279 +++++++++++++++
 tests/test_executar_serie.py                      | 404 ++++++++++++++++++++++
 tests/test_guarda_comando.py                      | 132 +++++++
 9 files changed, 1308 insertions(+), 10 deletions(-)
$ git show e491463 -- docs/PLAN_agente_nw.md | grep -c "^+.*\[086-"
7
```

Note a ordem da penúltima linha da entrega: a contagem das lacunas aparece onde sempre apareceu, embora
elas tenham sido gravadas no PLAN no começo. Era o que permitia não editar nenhuma asserção de
`tests/test_agente_entregar.py`.

Escopo, antes de acrescentar relatório, PLAN e manifesto:

```
$ git status --porcelain -uall
 M .claude/hooks/guarda_comando.py
 M AGENTS_agente_nw.md
 M scripts/agente_entregar.sh
 M tests/test_guarda_comando.py
?? .claude/serie.settings.json
?? scripts/executar_serie.sh
?? tests/test_executar_serie.py
```

## 8. Um defeito meu, achado e corrigido pelo próprio teste

A primeira versão do pré-voo conferia a energia com `pmset -g batt | grep -q "AC Power"`. Com
`set -o pipefail`, o `grep -q` fecha o pipe assim que acha o que procura, o `pmset` morre com SIGPIPE e o
**pipeline inteiro falha justamente quando a conferência deu certo**. O efeito era intermitente: na
primeira corrida, 18 testes passaram e 3 falharam, com a série recusando-se a começar dizendo que o Mac
estava na bateria enquanto o `pmset` real dizia `AC Power`. Corrigido guardando a saída numa variável e
comparando com `case`, nos dois lugares onde o padrão aparecia (energia e assunto do commit). As três
corridas seguidas acima são a prova de que a intermitência acabou.

## 9. Algum texto é analisado só em parte?

**Não se aplica, e a prova é o escopo:** nada neste brief lê, monta ou envia texto de conteúdo a modelo,
embedding ou filtro. Os três cortes que o `scripts/executar_serie.sh` faz são de **rótulo de cabeçalho**,
não de conteúdo analisado: `sys.argv[1:]` (a lista de números de brief da linha de comando),
`campo(texto, "Modelo").split()[0]` e `bruto.split()[0]` (a primeira palavra dos campos `Modelo` e
`Esforço`, que é exatamente o que o item 2.3 do brief manda ler, porque o campo traz justificativa depois
do nome). Na linguagem da auditoria 079 são cortes **não analíticos**. O cabeçalho dos briefs é lido por
expressão regular sobre o arquivo inteiro, sem limite de tamanho, e o texto do brief em si nunca é
cortado: ele é entregue inteiro ao `/executar`, que abre o arquivo.

O `.claude/hooks/guarda_comando.py` também não analisa texto de conteúdo: lê a linha de comando.

## 10. O que ficou de fora, e por quê

**O verificador da auditoria 079 ficou vermelho, e isto exige decisão sua.**
`scripts/verificar_auditoria_texto.py` devolvia 0 antes deste brief e passou a devolver 1, com sete
inconsistências:

```
$ .venv/bin/python scripts/verificar_auditoria_texto.py
319 arquivos, 256 certificados, 54 cortam, 7 não analíticos, 0 não conferidos, 45 ponto(s) aguardando decisão de Sidarta
1275 ocorrência(s) da varredura mecânica, todas com destino no relatório

7 inconsistência(s):
  - arquivo do universo ausente da tabela de certificação: scripts/executar_serie.sh
  - arquivo do universo ausente da tabela de certificação: tests/test_executar_serie.py
  - scripts/agente_entregar.sh: a tabela diz 136/136 linhas, mas o arquivo tem 146
  - tests/test_guarda_comando.py: a tabela diz 134/134 linhas, mas o arquivo tem 266
  - ocorrência sem destino no relatório: scripts/executar_serie.sh:107 [py:slice_inicio]
  - ocorrência sem destino no relatório: scripts/executar_serie.sh:121 [linhas]
  - ocorrência sem destino no relatório: scripts/executar_serie.sh:123 [linhas]
```

Causa, e por que não é um defeito deste brief: o verificador do 079 é um retrato de um instante. Ele
exige que **todo** arquivo de código do universo esteja na tabela de certificação do relatório 079, com a
contagem de linhas exata, e que **toda** ocorrência da varredura esteja citada no relatório. Qualquer
brief que crie um arquivo de código ou mude o número de linhas de um já existente deixa o verificador
vermelho — não só este: o 081 cria `tests/test_texto_do_usuario_inteiro.py` e muda linhas de
`nucleo/historico.py`, o 083 cria outro teste, e assim por diante.

Por que eu não consertei: `docs/docs/doc_079_...md` e `scripts/verificar_auditoria_texto.py` **não estão
nos arquivos-alvo do brief 086**, e o brief 079 (itens 3.1 e 3.8) é explícito em que o executor não
escreve no relatório de auditoria por conta própria. AGENTS §1: o que o brief não cobre, eu registro, não
invento. **O verificador não está no gate** (`scripts/verificar.sh` roda ruff, format, mypy e pytest), então
isto não derrubou esta entrega — mas derruba o critério de aceite 2 do **brief 080**, que é o próximo da
ordem e manda o verificador devolver 0.

As três saídas possíveis, para você escolher (eu recomendo a primeira):

1. **O brief 080 recertifica os arquivos novos.** Ele já tem o `doc_079` como alvo (seção 3) e é só
   acrescentar duas linhas na tabela de certificação, corrigir duas contagens e citar as três ocorrências
   como não analíticas (são leitura de rótulo de cabeçalho e da linha de comando, nunca de conteúdo).
   Custo: minutos, dentro de um brief que já mexe no mesmo arquivo. Exige uma frase sua autorizando o 080
   a tocar, no `doc_079`, também a seção 6 e o apêndice A.
2. **Um brief curto antes do 080**, só para recertificar o que o 086 criou. Mais limpo quanto a escopo,
   mais um ciclo de ida e volta.
3. **Antecipar o brief 093** (guarda permanente no gate), que troca a conferência por contagem de linhas
   por um teste estático com chave estável (`arquivo + linha normalizada`, item 2.2 do 093) — a solução de
   fundo, que faz o problema não voltar. Mas ele depende do 092, que depende do 083 e do 087.

Até você decidir, a série **não deve começar pelo 080**: ele pararia no próprio critério de aceite.

## RELATÓRIO FINAL

- **Brief executado:** 086 — executor em série (v2, com o item 2.10).
- **Arquivos criados:** `scripts/executar_serie.sh`; `.claude/serie.settings.json`;
  `tests/test_executar_serie.py`; `docs/docs/doc_086_executor_em_serie_2026-11-10.md`;
  `logs/commit_086.txt` e `logs/arquivos_086.txt` (manifesto, fora do git).
- **Arquivos alterados (uma linha cada):** `scripts/agente_entregar.sh` — lacunas no PLAN antes do commit
  (passo 1b), sem mudar a ordem da saída; `.claude/hooks/guarda_comando.py` — `git worktree list` passa e
  `agente_nw` de leitura em cópia passa com as cinco condições do 2.10; `AGENTS_agente_nw.md` — §10, a
  frase do script da série; `tests/test_guarda_comando.py` — 132 linhas acrescentadas, nenhuma removida;
  `docs/PLAN_agente_nw.md` — Resumo, Doing, Backlog e Done.
- **Arquivos preservados literalmente na área afetada:** `scripts/agente_lacunas.py` (o item 2.4 não
  exigiu mudança), `scripts/commitar.sh`, `scripts/verificar.sh`, `.claude/settings.json`,
  `.claude/skills/executar/SKILL.md`, `.claude/hooks/lint_arquivo.py`, `tests/test_agente_entregar.py`,
  `tests/test_agente_lacunas.py` e todo `agente_nw/`.
- **Script de verificação (o gate, rodado pelo `scripts/agente_entregar.sh`; saída colada):** seção 7
  (`ruff check: ok`, `ruff format: ok`, `mypy: ok`, `pytest: ok (1086 passed, 5 deselected)`).
- **Comandos executados:** `pytest tests/test_executar_serie.py`, `pytest tests/test_guarda_comando.py`,
  `pytest tests/test_agente_entregar.py tests/test_agente_lacunas.py`, `bash -n` nos dois scripts,
  `grep -nE "git (add|commit|push)|--simular"`, `git diff --numstat`, `scripts/verificar.sh`,
  `scripts/verificar_auditoria_texto.py`, `git status --porcelain -uall`,
  `scripts/agente_entregar.sh 086`.
- **Manifesto do commit (`logs/arquivos_086.txt` e `logs/commit_086.txt`, conteúdo colado):** seção 11.
- **Pendências e decisões que ficaram abertas:** a decisão da seção 10 (quem recertifica os arquivos novos
  no relatório 079 antes de o brief 080 rodar). Nada mais.
- **Resumo, Doing, Backlog e Done do `docs/PLAN_agente_nw.md` atualizados:** sim.

## 11. Manifesto

`logs/commit_086.txt`:

```
feat(serie): executar_serie.sh roda briefs em serie sem acompanhamento (brief 086)

- scripts/executar_serie.sh: pre-voo, laco por brief, conferencia de entrega em seis itens,
  STATUS.txt, notificacao, caffeinate e trava de instancia
- .claude/serie.settings.json: permissoes da serie (settings da sessao interativa nao muda)
- agente_entregar.sh: lacunas no PLAN antes do commit, para a arvore nao ficar suja depois
- trava: libera `git worktree list` e `agente_nw` de leitura apontando para copia do banco
- AGENTS §10: o script existe e como se usa
```

`logs/arquivos_086.txt`:

```
scripts/executar_serie.sh
.claude/serie.settings.json
scripts/agente_entregar.sh
.claude/hooks/guarda_comando.py
AGENTS_agente_nw.md
tests/test_executar_serie.py
tests/test_guarda_comando.py
docs/docs/doc_086_executor_em_serie_2026-11-10.md
docs/PLAN_agente_nw.md
```

O próprio brief 086 não entra no manifesto porque já está no git: ele foi commitado em `a93a364`,
junto dos briefs 080 a 095 e dos relatórios 084 e 085.

## Lacunas

| # | Lacuna | Destino | Impacto |
|---|---|---|---|
| 1 | O verificador da auditoria 079 passou a devolver 1: dois arquivos novos fora da tabela de certificação, duas contagens de linha defasadas e três ocorrências de varredura sem destino (seção 10). Ele é um retrato de um instante, então **todo** brief que criar arquivo de código repete isto. Três saídas na seção 10; a escolha é sua, e o brief 080 para no próprio critério de aceite até ela existir | decisão | quebra |
| 2 | Uma série de verdade, com um brief real, ainda não rodou: os 21 testes usam um `claude` falso. O ensaio natural continua sendo um brief só de documentos, com a lista de um item | backlog | degrada |
| 3 | O `--settings .claude/serie.settings.json` não foi provado contra o Claude Code real: não sei se ele soma ao `.claude/settings.json` ou o substitui. Por isso o arquivo repete o `allow`, o `deny` e os dois hooks do projeto — se substituir, a trava continua de pé. Provar exige uma execução real | dívida | nice |
| 4 | O custo somado no `STATUS.txt` vem do `total_cost_usd` do JSON, que é preço de tabela e não desconta a assinatura; e não há como ler quanto resta da janela de uso | dívida | nice |
| 5 | A conferência "o assunto do commit cita o número do brief" aceita o número em qualquer posição do assunto (`*086*`). Um commit de outro brief cujo texto contenha o número passaria. Para a série de hoje não acontece, mas não é uma garantia forte | dívida | nice |
| 6 | A revisão humana dos relatórios entre briefs continua sem mecanismo: o `STATUS.txt` reúne hashes, custo e pendências, mas nada obriga a leitura antes do brief seguinte | decisão | degrada |
| 7 | `reprocessar` é o único subcomando da lista do 2.10 que também grava; a trava o separa por `--simular`/`--confirmo`, que é texto de linha de comando. Se o brief 095 escolher outro nome de opção, a trava precisa de um brief para acompanhar | dívida | nice |
