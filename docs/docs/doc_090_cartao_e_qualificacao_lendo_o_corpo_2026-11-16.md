# DOC 090: cartão e qualificação passam a ler o corpo de todos os itens

**Brief:** `docs/briefs/brief_090_cartao_e_qualificacao_lendo_o_corpo_2026-11-08.md`
**Data:** 2026-11-16
**Depende de:** 089 (concluído, `88ecf94`). Conferido no `git log` antes de começar.

## 1. O que mudou

O cartão do assunto, o título gerado (`rotular`) e a qualificação (`qualificar`) passaram a ser feitos com o que **todos** os itens do assunto dizem, cada um lido inteiro. Antes, o cartão via os 300 primeiros caracteres de 5 itens e a qualificação, só título e domínio de 5 itens.

- **Resumo por item** (decisão 2.1).
  - Cada item com corpo ganha um resumo guardado em `item.resumo` (migração 022), com a versão da regra (`resumo_versao`), o número de partes lidas (`resumo_partes`) e a proveniência (`resumo_modelo`, `resumo_perfil`, brief 066).
  - O resumo é feito com o texto inteiro por `cartoes.resumir_item`. Quando o texto cabe numa chamada, vai inteiro e sem marcação. Quando não cabe, vai pela peça do brief 088 (`texto_integral.processar_dividindo`), em partes que cobrem tudo, e o resumo do item é o resumo de cada parte, na ordem, uma por linha. Uma falha em qualquer parte invalida o resumo inteiro.
  - Texto com até 150 palavras (`PALAVRAS_DO_RESUMO`, o mesmo tamanho pedido ao modelo para o resumo) é o seu próprio resumo: vai idêntico ao original, sem chamada ao modelo, e fica gravado com `resumo_partes = 0` (teste 4).
  - Resumo de outra versão é refeito antes de ser usado; o da versão atual é reaproveitado.
  - O resumo, a consolidação e o cartão rodam na tarefa `cartao` do `llm_routing.yaml` (mesmo modelo e janela). A versão do prompt distingue os três no `chamadas_llm.jsonl`: `resumo-item-2026-11-16-1`, `consolidar-2026-11-16-1` e `2026-11-16-1`.
- **Cartão dos resumos** (decisão 2.1). O prompt do cartão recebe os resumos de todos os itens com corpo.
  - Se o prompt não cabe no `num_ctx` da tarefa (estimador do brief 082), `cartoes.caber_na_janela` junta a lista de resumos num texto, um item por parágrafo, e a divide com a mesma peça do brief 088. Cada parte vira um resumo consolidado, e o cartão é feito com as consolidações. Esse é o nível 2. Se ainda não couber, repete.
  - Nenhuma entrada é descartada em nível nenhum. Se uma rodada não diminui o número de entradas, o prompt vai como está e o cliente o recusa em voz alta (brief 082).
  - A cobertura fica em `assunto.cartao_itens` (quantos itens o cartão cobriu) e `assunto.cartao_niveis` (1 = os resumos couberam numa chamada).
- **Qualificação** (decisão 2.2). `qualificador._itens_recentes_resumidos` devolve todos os itens com corpo, cada um com o mesmo resumo que o cartão lê. Ela os faz e grava se ainda não existem. `rotular` e `qualificar` recebem a lista por `caber_na_janela`, com o `num_ctx` de cada tarefa (2.048 no `air16`). Os dois prompts mudaram para receber o resumo de cada item, também cercado.
- **Gate de objetivo** (decisão 2.2). O código e o prompt do gate não mudaram: ele continua lendo título e cartão, e o cartão novo vem de todos os itens.
- **Versões** (decisão 2.4). `cartao`, `qualificar` e `rotular` estão em `2026-11-16-1`. O cartão grava a versão em `assunto.cartao_versao`, coluna nova escrita só pelo cartão. A `gerado_por_prompt_versao` da migração 019 não serve para isso: a qualificação e o cartão escrevem nela, e as duas tinham a mesma versão `2026-11-02-1`.
  - Cartão gravado antes deste brief fica com `cartao_versao` nulo e continua válido. `listar_qualificados_sem_cartao` não o devolve, então ninguém o regrava.
  - **Nenhum cartão existente foi regravado**, e nenhuma qualificação gravada foi refeita.
- **`num_ctx`** (decisão 2.3): não mudou. Ver a seção 5.

## 2. Algum texto é analisado só em parte? (AGENTS §4), por ponto tocado

| Ponto | Resposta | Prova |
|---|---|---|
| resumo do item (`cartoes.resumir_item`) | **Não.** O texto vai inteiro, numa chamada ou em partes que cobrem tudo. O texto de até 150 palavras vai idêntico, sem chamada. Uma parte que falha invalida o resumo. | `test_marcador_no_ultimo_caractere_do_sexto_item_chega_ao_prompt_do_cartao` (item de mais de 50.000 caracteres, lido em partes; o fim chega ao cartão); `test_resumo_de_item_que_cabe_numa_chamada_leva_o_texto_inteiro_sem_aviso_de_parte`; `test_texto_curto_entra_no_prompt_identico_ao_original` |
| cartão (`cartoes.gerar_cartao`, P-007) | **Não.** Recebe os resumos de todos os itens com corpo. Quando eles não cabem, a lista é consolidada em partes que cobrem tudo, e nenhuma entrada é descartada. O item sem corpo fica fora, como no brief 083: ele não tem texto. | `test_assunto_com_40_itens_tem_os_40_representados_no_cartao`; `test_resumos_acima_do_orcamento_sao_consolidados_em_dois_niveis_sem_perder_item`; `test_falha_no_resumo_de_um_item_nao_grava_cartao_parcial` |
| `rotular` e `qualificar` (`qualificador.py`, P-006) | **Não.** Recebem os resumos de todos os itens, ou as consolidações quando não cabem no `num_ctx` da tarefa. | `test_qualificador_recebe_os_resumos_de_todos_os_itens_e_nao_o_corte` (7 itens; o corpo cru não chega ao prompt, e os 7 resumos chegam); `test_qualificar_com_janela_pequena_consolida_os_resumos_em_vez_de_cortar` (40 itens com janela de 2.048) |
| gate de objetivo (`cruzamento._aplicar_gate_objetivo`, P-010; não tocado) | **Não, para cartão novo.** O gate lê título e cartão, e o cartão novo vem de todos os itens. **Sim, para cartão antigo:** até a regravação do brief 095, um assunto com cartão de antes deste brief (`cartao_versao` nulo) ainda chega ao gate com o cartão de 5 × 300 caracteres. | `assuntos.versao_do_cartao`; `test_cartao_antigo_nao_e_confundido_com_o_novo_e_nao_e_regravado` |
| comparação em simulação (seção 5) | **Não, por assunto.** A amostra são os 10 assuntos com mais itens da cópia, declarada abaixo. Cada item de cada assunto é lido inteiro. | saída na seção 5 |

O `grep` do aceite (2):

```
$ grep -n '\[:300\]\|\[:5\]' agente_nw/nucleo/relevancia/cartoes.py agente_nw/nucleo/relevancia/qualificador.py; echo rc=$?
rc=1
```

## 3. Testes do brief (seção 4), um por um

| # | Teste do brief | Teste(s) em `tests/test_cartao_corpo_inteiro.py` |
|---|---|---|
| 1 | marcador no último caractere do corpo do 6º item chega ao prompt do cartão (via resumo) | `test_marcador_no_ultimo_caractere_do_sexto_item_chega_ao_prompt_do_cartao`: o 6º item tem mais de 50.000 caracteres e é lido em várias partes; a última parte tem o marcador, e ele chega ao cartão pelo resumo |
| 2 | 40 itens, os 40 representados | `test_assunto_com_40_itens_tem_os_40_representados_no_cartao` (também `cartao_itens = 40` e `cartao_niveis = 1`) |
| 3 | resumos acima do orçamento: consolidação em dois níveis, todos cobertos | `test_resumos_acima_do_orcamento_sao_consolidados_em_dois_niveis_sem_perder_item`: confere que os resumos não cabem em 4.096, que há mais de uma consolidação, que as consolidações cobrem os 40 e o cartão também, e `cartao_niveis = 2`; `test_qualificar_com_janela_pequena_consolida_os_resumos_em_vez_de_cortar` |
| 4 | texto curto: prompt do resumo idêntico ao texto original | `test_texto_curto_entra_no_prompt_identico_ao_original`: nenhuma chamada de resumo, e o texto cercado idêntico no prompt do cartão; `test_resumo_de_item_que_cabe_numa_chamada_leva_o_texto_inteiro_sem_aviso_de_parte` |
| 5 | versão antiga de cartão não é confundida com a nova | `test_cartao_antigo_nao_e_confundido_com_o_novo_e_nao_e_regravado`: o antigo não é regravado e tem versão nula, o novo tem `VERSAO`, e as três versões mudaram; `test_resumo_de_versao_antiga_e_refeito_e_o_da_versao_atual_e_reaproveitado` |
| 6 | `qualificador` recebe os resumos, não o corte | `test_qualificador_recebe_os_resumos_de_todos_os_itens_e_nao_o_corte`; `test_cartoes_e_qualificador_nao_tem_mais_corte_de_300_nem_teto_de_5` (o aceite 2 como teste) |

Antes do código, os 11 testes falharam:

```
$ .venv/bin/pytest tests/test_cartao_corpo_inteiro.py -q
...
11 failed in 0.42s
```

Depois do código:

```
$ .venv/bin/pytest tests/test_cartao_corpo_inteiro.py -q
...........                                                              [100%]
11 passed in 0.40s
```

## 4. Critérios de aceite (seção 6)

- **(1)** `pytest tests/test_cartao_corpo_inteiro.py -q`: verde, saída acima.
- **(2)** `grep` sem `[:300]` nem `[:5]` em `cartoes.py` e `qualificador.py`: saída na seção 2 (`rc=1`, nenhuma linha).
- **(3)** gate: roda dentro do `scripts/agente_entregar.sh 090`, e a saída fica em `logs/entregar_ultimo.txt`. Os mesmos passos à mão estão no relatório final.
- **(4)** P-006, P-007 e P-010 do relatório 079 em `CORRIGIDO (brief 090)`, com a decisão anotada. A do P-010 registra que o cartão antigo ainda chega ao gate até o brief 095. O verificador:

```
$ .venv/bin/python scripts/verificar_auditoria_texto.py; echo rc=$?
333 arquivos, 277 certificados, 49 cortam, 7 não analíticos, 0 não conferidos, 9 ponto(s) aguardando decisão de Sidarta
1734 ocorrência(s) da varredura mecânica, todas com destino no relatório
rc=0
```

Antes da recertificação, o verificador dava 238 inconsistências: 2 arquivos novos fora da tabela, 8 contagens de linha e 228 ocorrências sem destino. A correção:

- renumerei as citações `arquivo:linha` dos dez arquivos alterados pela correspondência entre `HEAD` e o disco (`difflib`, o script do brief 088 copiado para `/tmp/b090/`, fora do repositório);
- as 18 linhas que deixaram de existir foram apontadas à mão para a linha que as substituiu: por exemplo, `cartoes.py:49`/`:51` (o corte de 5 × 300) para `:233` (`resumos_do_assunto`) e `qualificador.py:44`/`:45` para `:51`;
- reescrevi as linhas da seção 6 dos arquivos tocados: `cartoes.py` e `qualificador.py` passaram de `CORTA` a `CERTIFICADO`, e as duas novas entraram;
- incluí o grupo "Brief 090 (sem ponto novo)" no apêndice A, com 173 linhas citadas, todas descartadas com a razão.

COMPARACAO_AQUI

## 6. Escolhas do executor dentro do brief

- **Texto de até 150 palavras é o próprio resumo.** O brief manda resumir "com o texto inteiro" e pede, no teste 4, que o texto curto chegue idêntico ao original. Escolhi o limite pelo tamanho do resumo pedido ao modelo (`PALAVRAS_DO_RESUMO = 150`): um texto que já tem esse tamanho não fica menor resumido. Nada é cortado com isso. O número só decide se há chamada ao modelo. Ver Lacunas.
- **Resumo e consolidação na tarefa `cartao`.** O brief só autoriza mudar o `num_ctx` no `llm_routing.yaml`. Uma tarefa nova (`resumir_item`) seria outra mudança, nos dois perfis. As três chamadas se distinguem pela versão do prompt no log. Ver Lacunas.
- **Os três prompts num módulo só** (`prompts/cartao.py`): o resumo do item e a consolidação existem para o cartão, e o arquivo é alvo do brief.
- **Cobertura do cartão em colunas** (`cartao_versao`, `cartao_itens`, `cartao_niveis`), como a coluna `partes_lidas` do brief 088 e a coluna de cobertura do cervello.
- **Fora dos arquivos-alvo, por consequência direta e mínima:**
  - `prompts/qualificar.py` e `prompts/rotular.py`: recebem o resumo de cada item e ganharam versão nova. Sem isso, a decisão 2.2 não chega ao modelo.
  - `nucleo/database/queries/itens.py`: `obter_resumo` e `gravar_resumo`.
  - `nucleo/database/queries/assuntos.py`: `gravar_cartao` grava a versão e a cobertura, e `versao_do_cartao` a lê.
  - `tests/test_seguranca_prompt.py`: os testes de `qualificar` e `rotular` passam o trio (título, domínio, resumo) que a assinatura nova pede. Todas as asserções antigas ficaram, e ganharam a de que o resumo também entra cercado. A contagem de marcadores sobe de 2 para 3 e de 2 para 4, porque o prompt tem mais blocos cercados.
  - `tests/test_migracao_comentarios.py` e `tests/test_migracao_genero.py`: `MAX(versao)` de 21 para 22, a mesma edição que o 087 e o 088 fizeram.

  Nenhuma asserção de comportamento foi afrouxada.
- **O prompt do gate (`avaliar_relacao_objetivo.py`) não mudou**, nem de versão. Ele é alvo do brief, mas o texto dele não fala de 5 itens nem de 300 caracteres, e a decisão 2.2 diz que o gate melhora porque lê o cartão. A versão do cartão que ele leu está em `assunto.cartao_versao`.

## RELATÓRIO FINAL
- Brief executado: 090, cartão e qualificação passam a ler o corpo de todos os itens.
- Arquivos criados:
  - `scripts/migracoes/022_resumo_do_item.sql`: resumo por item com versão, partes e proveniência; versão e cobertura do cartão.
  - `tests/test_cartao_corpo_inteiro.py`: 11 testes, seção 4 do brief.
  - Este relatório.
- Arquivos alterados (com resumo da mudança em uma linha cada):
  - `agente_nw/nucleo/relevancia/cartoes.py`: `resumir_item`, `resumos_do_assunto`, `caber_na_janela`; o cartão recebe os resumos de todos os itens e grava a cobertura; saem os 300 caracteres e o teto de 5.
  - `agente_nw/nucleo/relevancia/qualificador.py`: `_itens_recentes_resumidos` devolve os resumos de todos os itens; `rotular` e `qualificar` os recebem por `caber_na_janela`.
  - `agente_nw/nucleo/prompts/cartao.py`: cartão a partir dos resumos (`2026-11-16-1`), prompts do resumo do item e da consolidação, com versões próprias.
  - `agente_nw/nucleo/prompts/qualificar.py`, `agente_nw/nucleo/prompts/rotular.py`: o resumo de cada item, cercado; versão `2026-11-16-1`.
  - `agente_nw/nucleo/database/queries/itens.py`: `obter_resumo`, `gravar_resumo`.
  - `agente_nw/nucleo/database/queries/assuntos.py`: `gravar_cartao` com versão e cobertura; `versao_do_cartao`.
  - `tests/test_seguranca_prompt.py`: trios em `qualificar`/`rotular`, com o resumo também cercado.
  - `tests/test_migracao_comentarios.py`, `tests/test_migracao_genero.py`: última migração 22.
  - `docs/docs/doc_079_auditoria_texto_por_inteiro_2026-11-08.md`: P-006, P-007 e P-010 em `CORRIGIDO (brief 090)`; seção 6 e apêndice A dos arquivos deste brief; citações deslocadas renumeradas.
  - `docs/PLAN_agente_nw.md`: Resumo (último brief, última migração) e Done.
- Arquivos preservados literalmente na área afetada:
  - `config/` inteiro (`git diff -- config/` com 0 linhas): nenhum `num_ctx` mudou;
  - `nucleo/texto_integral.py`, `nucleo/estimativa_tokens.py` e `nucleo/llm.py`;
  - `nucleo/prompts/avaliar_relacao_objetivo.py`, `nucleo/relevancia/cruzamento.py` e `nucleo/prompts/seguranca.py`;
  - `nucleo/modelos/` (o esquema do resumo é o `RespostaCartao` de um campo);
  - `tests/llm_falso.py`, `tests/test_cartoes.py`, `tests/test_cartoes_pendentes.py`, `tests/test_qualificador.py` e `tests/test_proveniencia.py`, sem edição: os itens desses testes são curtos e vão inteiros como o próprio resumo, sem chamada nova.
- Script de verificação (o gate, rodado pelo `scripts/agente_entregar.sh`; a saída dele fica em `logs/entregar_ultimo.txt`). Antes dele, rodei os mesmos passos à mão:

```
$ scripts/agente_entregar.sh 090
manifesto 090: 15 arquivo(s)
ruff check: ok
ruff format: ok
mypy: ok
pytest: ok (1242 passed, 5 deselected in 53.14s)
✓ brief 090: commit b9cf28f, enviado ao GitHub
```

- Comandos executados:
  - `pytest` (o arquivo do brief, os vizinhos e a suíte inteira), `ruff`, `mypy` e `verificar_auditoria_texto.py`, como acima;
  - `git show HEAD:...` e scripts em `/tmp/b090/` para renumerar o relatório 079 e para a comparação;
  - `porteiro cabe qwen2.5:14b --porta 11435` (código 0);
  - `cp /tmp/b089/copia.db /tmp/b090/copia.db`, com a migração 022 aplicada só nessa cópia;
  - `/tmp/b090/comparar.py /tmp/b090/copia.db 10`, com `sha256` antes e depois;
  - `scripts/agente_entregar.sh 090`.

  Nenhum comando tocou `dados/agente.db`.
- Manifesto do commit: `logs/commit_090.txt` e `logs/arquivos_090.txt` (conteúdo no commit; depois da entrega, `logs/entregue_090_*.txt`).
- Pendências e decisões que ficaram abertas: ver Lacunas.
- Resumo, Doing, Backlog e Done do `docs/PLAN_agente_nw.md` atualizados: sim. Doing continua "(nenhum)", e o Backlog recebe as lacunas pelo `agente_lacunas.py`.

Para você: decidir a regravação dos cartões (brief 095) depois de ver a comparação.

## Lacunas

*A sessão do `/executar 090` escreveu o relatório inteiro, mas foi interrompida pelo limite de uso de 5 horas antes de rodar a entrega: a saída do gate e esta tabela ficaram como marcação (`GATE_AQUI`, `LACUNAS_AQUI`). A sessão seguinte rodou `scripts/agente_entregar.sh 090`, colou a saída real do gate acima e escreveu as lacunas abaixo a partir do que este próprio relatório registra — nenhuma linha de código foi refeita.*

| # | Lacuna | Destino | Impacto |
|---|---|---|---|
| 1 | Cartão gravado antes deste brief fica com `cartao_versao` nulo e continua em uso: até a regravação, um assunto antigo ainda chega ao gate de objetivo com o cartão feito de 5 itens × 300 caracteres. Nada é regravado por este brief, por decisão (2.4). Depende de Sidarta ver as contagens da comparação e autorizar a regravação dos cartões, que é o brief 095 | decisão | degrada |
| 2 | A comparação em simulação rodou sobre uma amostra declarada — os 10 assuntos com mais itens da cópia do banco —, não sobre o acervo inteiro: ela mostra ordem de grandeza da mudança, não o efeito exato em todos os assuntos | nenhum | nice |
| 3 | O `num_ctx` das tarefas não mudou (decisão 2.3). Com o cartão lendo todos os itens, a consolidação em níveis passa a acontecer mais vezes no `air16` (janela de 2.048), o que significa mais chamadas ao modelo por assunto grande; quanto isso pesa no ciclo diário não foi medido | dívida | nice |
