# Relatório 083 — Fim da perda silenciosa de texto na coleta

**Brief:** `docs/briefs/brief_083_fim_da_perda_silenciosa_na_coleta_2026-11-08.md`
**Data:** 2026-11-16
**Depende de:** brief 079 executado (`700a43a`, relatório `doc_079_auditoria_texto_por_inteiro_2026-11-08.md`): satisfeito.

## 1. O que mudou, em poucas linhas

- **2.1 Bloco grande é partido (P-014).** `navegador.partir_bloco` divide o bloco acima de 5.000 caracteres em pedaços de até 5.000. O corte cai no último fim de parágrafo do trecho; se não houver, no último fim de frase; se também não houver, no último espaço. Só um trecho de 5.000 caracteres sem nenhum espaço seria cortado no tamanho máximo. A função confere que `"".join(pedacos) == bloco` antes de devolver. O piso de 30 caracteres continua. `CapturaBlocos.blocos_partidos` conta cada bloco partido uma vez só, mesmo que a página seja relida a cada rolagem. O número chega a `ResumoLeitura`, a `ResumoRedeSocial` (texto da consulta) e às duas saídas da CLI.
- **2.2 O corte de 200.000 deixa de ser silencioso (P-013).** O teto não mudou. O `estado` do `extensao/conteudo.js` devolve também `tamanho_original` e `cortado`. O `background.js` repassa o objeto como vem e não precisou mudar. `PaginaExtensao._ler_estado` registra o corte em dois casos: quando a extensão diz `cortado: true` (origem `extensao`) e quando o próprio programa corta, no caso de uma extensão antiga que devolva mais do que o teto (origem `programa`). O registro é uma linha `"corte_pagina": true` no `chamadas_llm.jsonl`, no padrão do aviso do `porteiro` do brief 077: falha de escrita não derruba a leitura. O aviso "página cortada em 200.000 de N caracteres" vai para `avisos_corte`, uma vez por página e tamanho. O leitor de capturas o leva a `ResumoLeitura.avisos` como `"<rede>: página cortada …"`, e de lá ele segue para o resumo da consulta e para a CLI.
- **2.3 Item sem corpo (P-003, primeira parte).** Ver a divergência na seção 5.1. `e_ruido` deixa de tratar `corpo=None` como "abaixo do teaser mínimo". O item cuja página não abre, ou cujo `trafilatura` não devolve texto (inclusive texto vazio), é gravado com `texto` nulo e contado em `ResumoColeta.itens_so_manchete`. A CLI `coletar` mostra a contagem. O esquema já distinguia esse item (`item.texto` é anulável e nada no código o anula depois), então **não houve migração**. `queries/itens.listar_por_assunto(..., com_corpo=True)` deixa esse item de fora em três lugares: no cartão (`cartoes.py`), na qualificação (`qualificador.py`; um assunto só de manchetes não é rotulado nem qualificado e conta em `ResumoQualificacao.sem_corpo`) e no gancho (`redacao._assunto_para_redacao`). O agrupador continua chamando sem o filtro: o vetor de manchete não muda, como manda o brief. O teaser mínimo de 400 caracteres ficou como estava.
- **2.3b.** O P-003 **não** foi marcado como corrigido. O `Estado` dele continua `AGUARDANDO DECISÃO DE SIDARTA` e ganhou só uma linha "Brief 083 (parte corrigida…)".
- **2.4 Patrocinado no corpo todo (P-004).** A marca é procurada em todas as linhas do corpo, mas só vale em linha de até 80 caracteres (`_LINHA_DE_DECLARACAO`). No título continua valendo como antes.

| Ponto do 079 | O que mudou | Teste |
|---|---|---|
| P-014 | bloco acima de 5.000 é partido em pedaços que reproduzem o bloco (fim de parágrafo, de frase ou de palavra) e contado em `blocos_partidos`; estado `CORRIGIDO (brief 083)` | `test_bloco_de_12000_caracteres_vira_3_pedacos_que_reproduzem_o_bloco`, `test_corte_prefere_fim_de_paragrafo`, `test_sem_frase_nem_paragrafo_corta_em_palavra`, `test_bloco_que_cabe_volta_inteiro`, `test_leitura_parte_o_bloco_grande_descarta_o_curto_e_conta_uma_vez`, `test_resumo_da_leitura_conta_os_blocos_partidos` |
| P-013 | a extensão devolve `tamanho_original` e `cortado`; o corte (da extensão ou do programa) vira linha `"corte_pagina": true` no `chamadas_llm.jsonl` e aviso no resumo; estado `CORRIGIDO (brief 083)` | `test_aviso_de_corte_no_formato_do_brief`, `test_extensao_que_cortou_vira_linha_no_log_e_aviso_no_resumo`, `test_extensao_que_nao_cortou_nao_registra_nada`, `test_corte_do_lado_do_programa_tambem_e_registrado`, `test_aviso_de_corte_chega_ao_resumo_da_leitura`, `test_conteudo_js_devolve_tamanho_original_e_se_cortou[350000-True]`, `[5000-False]` |
| P-004 | marca de patrocinado em todas as linhas de até 80 caracteres do corpo; estado `CORRIGIDO (brief 083)` | `test_publicidade_no_rodape_e_ruido`, `test_publicidade_no_meio_de_paragrafo_longo_nao_e_ruido`, `test_conteudo_patrocinado_na_primeira_linha_continua_ruido`, `test_corpo_curto_continua_abaixo_do_teaser_minimo` |
| P-003 (1ª parte) | item cujo corpo falhou é gravado com `texto` nulo, contado em `itens_so_manchete` e mantido fora do cartão, da qualificação e do gancho; **estado continua `AGUARDANDO DECISÃO DE SIDARTA`** (teaser de 400) | `test_item_sem_corpo_e_gravado_marcado_e_contado`, `test_item_sem_corpo_nao_chega_a_qualificacao_ao_cartao_nem_ao_gancho`, `test_assunto_so_de_manchetes_nao_e_qualificado` |

## 2. Algum texto é analisado só em parte? (AGENTS §4)

Sim, em dois pontos que este brief não mudou de propósito, e em nenhum ponto novo:

- **A página de rede social** continua cortada em 200.000 caracteres (`extensao/conteudo.js:203`, `extensao_backend.py:142`). O teto ficou por decisão 2.2 do brief, e a diferença é que o corte agora deixa rastro. O ponto P-013 está em `CORRIGIDO (brief 083)` porque a correção pedida era essa, não porque o corte deixou de existir.
- **O teaser mínimo de 400 caracteres** (`ruido.py:69`) continua descartando o corpo curto. É a segunda parte do P-003, que aguarda decisão de Sidarta.

O bloco partido é lido inteiro: cada pedaço vira um bloco, e a concatenação reproduz o original, conferida em `partir_bloco`. O item sem corpo deixou de ser julgado só pela manchete no cartão, na qualificação e no gancho. O agrupador continua usando o vetor da manchete desse item, porque o brief manda não mexer nisso (seção 5 do brief). A marca de patrocinado agora é procurada no corpo inteiro.

## 3. Testes do brief (seção 4)

1. **Bloco de 12.000.** Vira 3 pedaços de até 5.000, a concatenação é idêntica, nenhum pedaço termina no meio de uma palavra e todos terminam em ". ". O bloco de 27 caracteres continua descartado. O resumo conta 1 bloco partido, tanto em `navegador.ler`, com a página lida 3 vezes, quanto em `ler_redes_sociais_do_contato`.
2. **Retorno da extensão.** Com `cortado: true` e tamanho 350.000: uma linha no `chamadas_llm.jsonl` e "página cortada em 200.000 de 350.000 caracteres" em `avisos_corte`, no `ResumoLeitura.avisos` e no texto de `_resumo_rede_para_texto`. Com `cortado: false`: nem arquivo nem aviso.
3. **Patrocinado.** "Publicidade" na linha 40 de 50 é ruído. "a publicidade infantil cresceu" no meio de um parágrafo longo não é. "Conteúdo patrocinado" na primeira linha continua ruído.
4. **Item sem corpo.** A página da notícia número 1 responde 500 na rede falsa. O item é gravado com `texto` nulo e `itens_so_manchete == 1`. No assunto com um item com corpo e um sem, o título do item sem corpo não aparece em nenhum prompt de `rotular`, `qualificar` ou `cartao`, nem nas manchetes e links do gancho, e o item continua no assunto.
5. **JavaScript.** O projeto não tem suíte de teste JavaScript (ver Lacunas). Em vez de só simular a resposta, o teste roda o `estado` do próprio `extensao/conteudo.js` no `node` desta máquina, com uma página falsa de 350.000 e de 5.000 caracteres. O teste é pulado se não houver `node`.

```
$ .venv/bin/pytest tests/test_coleta_sem_perda_silenciosa.py -q
....................                                                     [100%]
20 passed in 1.17s
```

## 4. Critérios de aceite (seção 7)

**(1)** Saída acima: 20 testes passaram.

**(2) Gate.** Roda dentro do `scripts/agente_entregar.sh 083`, e a saída fica em `logs/entregar_ultimo.txt`. Antes dele, rodei os mesmos passos à mão:

```
$ .venv/bin/ruff check .
All checks passed!
$ .venv/bin/ruff format --check .
299 files already formatted
$ .venv/bin/mypy agente_nw
Success: no issues found in 125 source files
$ .venv/bin/pytest -q
1214 passed, 5 deselected in 57.69s
```

**(3) Verificador do 079.**

```
$ .venv/bin/python scripts/verificar_auditoria_texto.py
329 arquivos, 269 certificados, 53 cortam, 7 não analíticos, 0 não conferidos, 15 ponto(s) aguardando decisão de Sidarta
1554 ocorrência(s) da varredura mecânica, todas com destino no relatório
código: 0
```

O relatório 079 mudou só no que o brief e a autorização de 2026-11-16 permitem:

- **Pontos.** P-004, P-013 e P-014 passaram a `CORRIGIDO (brief 083)`, com a linha da decisão. O P-003 ganhou a linha do 083 e manteve o `Estado` em aberto.
- **Seção 6.** As linhas dos 13 arquivos alterados que já estavam na tabela foram atualizadas: contagem de linhas e, onde a evidência ficou falsa, a evidência. Entrou a linha nova de `tests/test_coleta_sem_perda_silenciosa.py`.
- **Apêndice A.** As citações deslocadas dos arquivos tocados foram renumeradas pela correspondência entre `HEAD` e a versão atual (317 citações, nenhuma sem correspondente). O grupo P-013 foi acertado à mão para as linhas certas: `conteudo.js:203` e `extensao_backend.py:142`. As 82 linhas novas do brief foram para o grupo "Brief 083 (sem ponto novo)", todas descartadas com razão.
- **Contagens.** As contagens do universo e da varredura foram atualizadas: 329 arquivos e 1.554 ocorrências.

Nenhum ponto novo foi criado.

**(4) `git diff --stat`.** Mostra os arquivos-alvo e, fora da lista literal, só consequências diretas, descritas na seção 5.2:

```
$ git diff --stat
 agente_nw/cli.py                                   |   8 +
 agente_nw/coleta/capturas/extensao_backend.py      |  66 +++-
 agente_nw/coleta/capturas/leitor.py                |   9 +
 agente_nw/coleta/capturas/navegador.py             |  67 +++-
 agente_nw/coleta/rss/leitor.py                     |   5 +-
 agente_nw/coleta/rss/ruido.py                      |  23 +-
 agente_nw/nucleo/consulta.py                       |   7 +
 agente_nw/nucleo/database/queries/itens.py         |   9 +-
 agente_nw/nucleo/redacao.py                        |   4 +-
 agente_nw/nucleo/relevancia/cartoes.py             |   2 +-
 agente_nw/nucleo/relevancia/qualificador.py        |   6 +-
 docs/PLAN_agente_nw.md                             |   3 +-
 ...c_079_auditoria_texto_por_inteiro_2026-11-08.md | 347 ++++++++++++---------
 extensao/conteudo.js                               |   9 +-
 tests/test_cli_pedir_redacao.py                    |   1 +
 tests/test_qualificador.py                         |   1 +
 16 files changed, 383 insertions(+), 184 deletions(-)
 tests/test_coleta_sem_perda_silenciosa.py (novo,      500 linhas)
```

## 5. Escolhas do executor dentro do brief

### 5.1 Divergência entre o 079 e o código: o item sem corpo era descartado, não gravado

O P-003 diz que o item cujo corpo falha "é gravado só com o título", e o brief 2.3 parte disso ("o item continua gravado"). No código de `HEAD` não era assim. `e_ruido` começava com `if corpo is None or len(corpo) < teaser_minimo: return True, "corpo abaixo do teaser mínimo"`, então o item sem corpo era **descartado** como ruído e contado em `descartados_ruido`.

Segui o estado final que o brief descreve e que o teste 4 exige: o item é gravado, marcado e contado. Por isso a coleta passa a gravar itens que antes descartava. Eles não alimentam cartão, qualificação nem gancho, mas entram no agrupamento pelo vetor da manchete, que o brief manda não mudar. Isso está registrado nas Lacunas.

### 5.2 Arquivos fora da lista literal, por consequência direta

- **Resumos da leitura.** A decisão 2.1 manda o resumo contar os blocos partidos, e a 2.2 manda mostrar o corte. O resumo mora em `coleta/capturas/leitor.py` (`ResumoLeitura`) e chega à tela por `nucleo/consulta.py` (`ResumoRedeSocial`, `_resumo_rede_para_texto`) e a `cli.py` (`ler-rede-social` e o resumo do pedido). Em cada um desses arquivos entrou um campo e uma linha.
- **Resumo da coleta.** A decisão 2.3 manda o resumo dizer quantos itens ficaram só com manchete, e isso entrou como uma linha no `cli.py coletar`.
- **Filtro do item sem corpo.** "Os pontos que montam cartão e qualificação": `cartoes.py`, `qualificador.py` e, por causa do "nem gancho" do 2.3, `redacao.py`, que monta as manchetes e links do gancho. O filtro fica num lugar só, `queries/itens.listar_por_assunto(..., com_corpo=True)`, bloqueado na origem (AGENTS §4).
- **Fixturas.** `tests/test_qualificador.py` e `tests/test_cli_pedir_redacao.py` gravavam o item da fixtura sem `texto`, ou seja, exatamente o item "só manchete" que agora fica fora. Cada uma ganhou `texto="Corpo da notícia."`. Nenhuma asserção mudou.

### 5.3 Outras escolhas

- **Dois casos de extensão antiga.** Com uma extensão antiga, que ainda não devolve `cortado`, o programa só consegue ver o corte quando a resposta passa do teto. Se ela já cortou em silêncio dentro do Chrome, a resposta chega com exatamente 200.000 caracteres e nada é avisado. Recarregar a extensão fecha esse caso (ver Pendências).
- **Por que um assunto só de manchetes é pulado.** Na qualificação, ele é pulado sem chamar o modelo, e não qualificado pelas manchetes: qualificá-las seria justamente julgar pela manchete. O número aparece em `ResumoQualificacao.sem_corpo`.

## RELATÓRIO FINAL
- Brief executado: 083 — fim da perda silenciosa de texto na coleta.
- Arquivos criados:
  - `tests/test_coleta_sem_perda_silenciosa.py`, o teste de aceite, com 20 casos;
  - este relatório.
- Arquivos alterados:
  - `agente_nw/coleta/capturas/navegador.py`: `partir_bloco`/`_onde_cortar`; `_extrair_blocos` devolve os pedaços de cada bloco; `CapturaBlocos.blocos_partidos`.
  - `agente_nw/coleta/capturas/extensao_backend.py`: `aviso_de_corte`, `_registrar_corte` (linha `"corte_pagina": true`), `avisos_corte`, `caminho_log` (o `chamadas_llm.jsonl`, passado por `abrir_pagina_extensao`).
  - `extensao/conteudo.js`: `estado` devolve `tamanho_original` e `cortado`.
  - `agente_nw/coleta/capturas/leitor.py`: `ResumoLeitura.blocos_partidos` e `avisos`, com aviso de progresso.
  - `agente_nw/nucleo/consulta.py`: `ResumoRedeSocial.blocos_partidos` e `avisos`, mostrados no texto do resumo.
  - `agente_nw/cli.py`: linhas de blocos partidos, avisos de corte e itens só com manchete.
  - `agente_nw/coleta/rss/ruido.py`: patrocinado em todas as linhas de até 80 caracteres; corpo nulo não é ruído.
  - `agente_nw/coleta/rss/leitor.py`: item sem corpo gravado com `texto` nulo e contado em `itens_so_manchete`; texto vazio do `trafilatura` conta como falha.
  - `agente_nw/nucleo/database/queries/itens.py`: `listar_por_assunto(..., com_corpo=False)`.
  - `agente_nw/nucleo/relevancia/cartoes.py`: o cartão só vê item com corpo.
  - `agente_nw/nucleo/relevancia/qualificador.py`: só item com corpo; assunto só de manchetes pulado e contado em `sem_corpo`.
  - `agente_nw/nucleo/redacao.py`: as manchetes e links do gancho só levam item com corpo.
  - `tests/test_qualificador.py`, `tests/test_cli_pedir_redacao.py`: o item da fixtura ganhou corpo.
  - `docs/docs/doc_079_auditoria_texto_por_inteiro_2026-11-08.md`: P-004, P-013 e P-014 em `CORRIGIDO (brief 083)`; a linha do 083 no P-003; seção 6; apêndice A.
  - `docs/PLAN_agente_nw.md`: Resumo e Done.
- Arquivos preservados literalmente na área afetada:
  - `extensao/background.js`, que repassa o retorno do `estado` sem mexer;
  - `agente_nw/nucleo/modelos/configuracao.py`, onde o teto de 200.000 continua;
  - `config/limiares.yaml`;
  - `agente_nw/nucleo/agrupamento/agrupador.py`, onde o vetor de manchete não mudou;
  - `scripts/migracoes/`, sem migração nova.
- Script de verificação: o gate é rodado pelo `scripts/agente_entregar.sh 083`, e a saída fica em `logs/entregar_ultimo.txt`. Os mesmos passos à mão estão na seção 4 (2).
- Comandos executados:
  - `.venv/bin/pytest tests/test_coleta_sem_perda_silenciosa.py -q`
  - `.venv/bin/ruff check .`
  - `.venv/bin/ruff format --check .`
  - `.venv/bin/mypy agente_nw`
  - `.venv/bin/pytest -q`
  - `.venv/bin/python scripts/verificar_auditoria_texto.py` (com e sem `--varredura`)
  - `scripts/agente_entregar.sh 083`
- Manifesto do commit:
  - `logs/arquivos_083.txt`: os 15 arquivos de código e teste acima, o relatório 079, este relatório e o PLAN.
  - `logs/commit_083.txt`: `feat(coleta): nenhum texto some da coleta sem rastro (brief 083)`, com o corpo descrevendo as quatro decisões.
- Pendências e decisões que ficaram abertas:
  - **Recarregar a extensão no Chrome.** Sem isso, a extensão em uso continua cortando em silêncio dentro do Chrome. O JavaScript foi provado no `node` com uma página falsa, não no Chrome.
  - **P-003, segunda parte.** O teaser de 400 caracteres continua aguardando decisão de Sidarta.
- Resumo, Doing, Backlog e Done do `docs/PLAN_agente_nw.md` atualizados: sim. Resumo e Done mudaram; Doing continua "(nenhum)"; o Backlog recebe as lacunas pelo `agente_entregar.sh`.

## Lacunas

| # | Lacuna | Destino | Impacto |
|---|---|---|---|
| 1 | Sem teste JS no projeto: não há suíte de teste para `extensao/`. O `cortado` do `conteudo.js` foi provado rodando o arquivo no `node` com uma página falsa (`test_conteudo_js_devolve_tamanho_original_e_se_cortou`, pulado sem `node`), não no Chrome | nenhum | nenhum |
| 2 | A extensão instalada no Chrome continua sem o campo `cortado` até ser recarregada. Até lá, o corte feito dentro do Chrome continua silencioso, porque o programa recebe exatamente 200.000 caracteres e não tem como saber que houve corte. Recarregar a extensão em `chrome://extensions` e abrir uma página longa fecha o caso | pendência | degrada |
| 3 | O item de notícia cujo corpo falhou antes era descartado como ruído, ao contrário do que o P-003 descrevia, e agora é gravado sem corpo. Ele fica fora do cartão, da qualificação e do gancho, mas entra no agrupamento pelo vetor da manchete (o brief manda não mudar isso) e pode puxar o centróide de um assunto. Tratar na série futura sobre o corpo da notícia | dívida | degrada |
