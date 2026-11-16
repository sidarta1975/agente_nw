# DOC 093: guarda permanente do texto por inteiro no gate

**Brief:** `docs/briefs/brief_093_guarda_permanente_no_gate_2026-11-08.md`
**Data:** 2026-11-16
**Depende de:** 092 (concluído, `e9aed9d`, conferido no `git log` e em `docs/docs/doc_092_*` antes de começar).

## 1. O que mudou

Código de produção não mudou. Mudaram dois arquivos de guarda e o relatório 079.

1. **`tests/test_sem_corte_de_texto.py` (novo).** Percorre `agente_nw/**/*.py` por AST e acusa:
   - fatia com limite (`x[:N]`, `x[-N:]`, `x[a:b]`; `x[:]` e `x[::-1]` não contam);
   - pedaço de divisão (`.split(...)[0]`, `.rsplit(...)[-1]`);
   - chamada `shorten`, `truncate`, `trunc*`, `cortar*`, `islice`, `head`, `sample`, `fetchmany`;
   - os nomes `max_chars`, `max_len`, `maxlen`, `max_length`, `maximo_caracteres*`;
   - `LIMIT` dentro de string (SQL);
   - teto decidido num lugar: constante ou chave de configuração passada como argumento (`_FATOS_NO_PROMPT`, `limiares.qualificacao.teto_por_dia`), valor dado ao parâmetro de teto de uma função do projeto (`fatos.listar_recentes(conexao, id, _FATOS_LIDOS)`, resolvido pelo import do arquivo) e valor padrão desse parâmetro (`limite: int = 5`). Repassar adiante a variável `limite` recebida não conta: o achado fica com quem decidiu o valor. Teto de tempo, espera ou tentativa não conta.

   **Chave** do achado (item 2.2): arquivo mais o texto normalizado das linhas do trecho (espaços colapsados, sem número de linha). Para trecho de uma linha é a linha; para trecho que ocupa várias linhas (uma chamada, um SQL) é o trecho inteiro, porque a primeira linha sozinha (`return [`) não identifica nada.

   **Três estados** (item 2.3): (a) `EXCECOES_APROVADAS`, no teste, aponta a chave para um ou mais pontos que têm linha em `docs/EXCECOES_TEXTO_INTEGRAL.md` com "Aprovado por Sidarta em", valor aprovado e condição; (b) a chave está na tabela nova "Cortes não analíticos" do registro; (c) `VIOLACOES_PENDENTES`, no teste, com o ponto e o destino. O teste falha com achado sem estado, achado em dois estados, ponto sem aprovação ou sem valor e condição, destino vencido e entrada de lista que não casa com nenhum achado (o corte saiu ou a linha mudou).

   **Destino de violação pendente.** O brief pede "o brief que vai corrigir". Nenhuma das violações restantes tem brief: todas esperam decisão de Sidarta. O destino aceita as duas formas: `brief NNN` (falha quando `docs/docs/doc_NNN_*.md` existe, isto é, o brief foi entregue) ou a lacuna do PLAN `[NNN-k]` (falha quando a linha da lacuna ganha "decidido" ou "resolvido", ou some do PLAN). A lacuna do brief em execução vale pela tabela `## Lacunas` do relatório dele até o `agente_entregar.sh` levá-la ao PLAN. É a mesma regra do brief ("destino cumprido, a entrada falha"), aplicada ao único destino que existe hoje.

2. **`docs/EXCECOES_TEXTO_INTEGRAL.md`** ganha a seção "Cortes não analíticos" (item 2.5): as classes NA-001 a NA-007 copiadas da seção 4 do relatório 079, as classes NA-008 a NA-015 tiradas dos motivos de descarte do apêndice A do mesmo relatório, e 79 linhas, uma por trecho. As exceções aprovadas (tabela de cima) não foram tocadas.

3. **Relatório 079** (autorização do cabeçalho do brief): linha nova de `tests/test_sem_corte_de_texto.py` na seção 6 e grupo "Brief 093 (sem ponto novo)" no apêndice A com as ocorrências da varredura no arquivo novo. Nenhum ponto novo, nenhum estado de ponto mudou.

## 2. Classificação, por estado

A varredura acha **187 achados em 159 chaves**, em 49 arquivos de `agente_nw/`. Por regra: 85 fatias, 58 tetos decididos, 16 `LIMIT`, 13 pedaços de divisão, 9 nomes de teto, 6 chamadas de corte.

| Estado | Chaves | Achados |
|---|---|---|
| (a) exceção aprovada | 41 | 51 |
| (b) corte não analítico | 79 | 84 |
| (c) violação pendente | 39 | 52 |
| sem estado | 0 | 0 |

**(a) exceção aprovada**, por ponto do registro: P-005 (7), P-008 (3), P-009 só o menu de 5 (1), P-015 (6), P-016 (2), P-017 (3), P-021 só as 5 candidatas (3), P-022 (1), P-023 (1), P-033 (11), P-043 (5), P-045 (1). Quatro chaves decidem dois tetos aprovados de uma vez (`P-015 P-017`, `P-016 P-017`). Nas aprovações parciais (P-009, P-021) só a parte aprovada foi para (a); a parte "não aprovada" está em (c).

**(b) não analítico**, por classe: NA-001 data (14), NA-002 trecho em erro (2), NA-003 tela (9), NA-004 Markdown (1), NA-005 migração (1), NA-007 blocos do WhatsApp (7), NA-008 endereço e nome de arquivo (11), NA-009 reparte com cobertura total (12), NA-010 índice fixo sobre nome ou texto do programa (9), NA-011 conferência de janela (3), NA-012 existência ou identificador (3), NA-013 rótulo de aviso (2), NA-014 `LIMIT ?` sem valor, decidido pelo chamador (4), NA-015 amostra de diagnóstico (1).

Linhas de (b) classificadas pelo executor deste brief, sem destino "não analítico" no relatório 079, todas sujeitas a contestação (lacuna 6). São 28:

- 21 sem destino nominal no apêndice A (nasceram depois do 079 ou estão num trecho de várias linhas que a varredura por texto via em outra linha): `navegador.py` `pedacos.append(bloco[inicio:])` e `bloco[inicio:fim]` (NA-009); `whatsapp/leitor.py` nome do arquivo no `.zip` (NA-008); `console/app.py` página da lista, `listar_para_inicio(..., 50 if termo else 20)` e `listar_recentes(conn, perfil_id, 15)` (NA-003); `comparar_vetores.py` amostra (NA-015); `confirmacao.py` página (NA-003); `queries/consulta_contato.py` e `queries/fatos.py` `LIMIT ?` genéricos (NA-014); `queries/pedidos.py` pessoas recentes e `queries/perfis.py` filtro da tela inicial (NA-003); `llm.py` registro de estouro e `processar_dividindo` do embedding (NA-011); `extrair_captura_rede_social.py` rodapé do prompt (NA-010); `redigir_ganchos.py` comentários que o corte tirou, para o aviso (NA-013); `markdown.py` bloco entre marcações (NA-004); `texto_integral.py` três fatias da divisão (NA-009).
- 7 que o 079 citava num ponto e que, na linha de hoje, não cortam: `busca.py` e `listas.py` (2) nome mais cabeçalho inteiro, depois do brief 092 (P-020 → NA-009); `importador.py` a chamada de `blocos_por_mes`, cujo teto acusado é o tamanho do bloco (P-022 → NA-007; os 24 meses estão em (a), na consulta); `queries/nota_contato.py` `LIMIT ?` genérico, com o 5 do chamador em (c) (P-029 → NA-014); `queries/perfis.py` primeira palavra e as demais (P-045 → NA-010); `redacao.py` o dia do fato numa linha que leva o fato inteiro (P-026 → NA-001).

No sentido contrário, 9 trechos que o apêndice A descartava ficaram em (a) ou (c), porque a varredura por AST vê o teto que eles decidem: `cli.py` `qualificar_cmd(args.limite)` e `queries/consulta_contato.py` `candidatos[:1]` em (c); `consulta.py` a chamada da leitura de rede social e quatro trechos do `cortar_por_tamanho` em `redigir_ganchos.py` e `redacao.py` em (a); `redacao.py` `ordem[:vagas]` e `candidatos[:_FATOS_NO_PROMPT]` em (c).

**(c) violação pendente**, por ponto e destino:

| Ponto | O que continua cortado | Onde | Destino |
|---|---|---|---|
| P-009 | os 10 candidatos (`conector.candidatos_por_contato`) escolhidos por cosseno | `relevancia/candidatos.py` (2), `relevancia/cruzamento.py` (2) | [080-5] |
| P-009 | `qualificacao.teto_por_dia` (40) assuntos por rodada na qualificação e no cartão | `cli.py`, `consulta.py`, `queries/assuntos.py` (2) | [093-2] |
| P-013 | a página da rede social em 200.000 caracteres (agora avisado, brief 083) | `capturas/extensao_backend.py` (3), `modelos/configuracao.py` | [093-1] |
| P-021 | os 200 fatos mais recentes na deduplicação | `localizacao.py` | [092-5] |
| P-025 | os 20 fatos mais recentes do centróide | `queries/perfis.py` | [089-1] |
| P-026 | 10 de 40 fatos na redação | `redacao.py` (5) | [091-2] |
| P-027 | 12 de 30 fatos nos termos de busca | `termos_contato.py` (3) | [091-2] |
| P-028 | histórico: 5 consultas lidas, 3 usadas, mensagem anterior com 100 caracteres | `historico.py` (2), `redacao.py` (2) | [093-3] |
| P-029 | 5 notas na redação | `redacao.py` | [093-4] |
| P-030 | 2 moldes na redação | `queries/consulta_contato.py` (2), `orquestracao.py`, `redacao.py` (2) | [093-4] |
| P-031 | 3 itens por assunto, só a manchete, na redação | `redacao.py` | [091-2] |
| P-032 | 4 ganchos de notícia (o excedente agora é contado) | `modelos/redacao.py` | [092-3] |
| P-034 | `interessa` com 5 itens no contrato | `modelos/pedido.py` | [091-1] |
| P-034 | `termos_busca` com 6 itens no contrato | `modelos/pedido.py` | [093-5] |
| P-035 | contatos do prompt do pedido além dos parecidos: 50 mais recentes | `pedido.py` (2) | [092-3] |
| P-039 | 5 interesses no ponto de apoio | `relevancia/cruzamento.py` | [091-1] |

Lista (c) **não vazia**, e só com pontos cujo destino não foi cumprido: nenhum tem brief entregue (nenhum tem brief), e as lacunas `[080-5]`, `[089-1]`, `[091-1]`, `[091-2]`, `[092-3]` e `[092-5]` estão abertas no PLAN (conferido: nenhuma linha delas tem "decidido" ou "resolvido"); `[093-1]` a `[093-5]` são as lacunas 1 a 5 deste relatório.

## 3. Testes antigos que fixam cortes (item 2.4)

Nenhum teste foi reescrito. Os testes que fixavam um corte que um brief deste conjunto tirou (300 caracteres do cartão, 2.000 do vetor, 600 do fato, 400 da nota, 5 do `evitar`) já foram reescritos pelos briefs 081 a 092, que mudaram o comportamento; a suíte verde é a prova de que nenhum teste afirma um corte que não existe mais. Este brief não muda comportamento, então não há "comportamento novo" para afirmar.

Continuam afirmando um corte que está em (c) — o corte é o atual, não o aprovado — e mudam junto quando o ponto for decidido:

| Teste | Ponto | Destino |
|---|---|---|
| `tests/test_extensao_backend.py::test_estado_corta_o_texto_em_maximo_de_caracteres` | P-013 | [093-1] |
| `tests/test_coleta_sem_perda_silenciosa.py` (`len(texto) == 200_000`, l. 227 e 259) | P-013 | [093-1] |
| `tests/test_pedido_extrair.py::test_termos_de_busca_acima_de_seis_sao_cortados` | P-034 | [093-5] |
| `tests/test_historico_formatar.py::test_historico_recente_para_prompt_limita_no_padrao_de_cinco` | P-028 | [093-3] |
| `tests/test_redacao_modelo.py::test_no_maximo_quatro_ganchos` | P-032 | [092-3] |
| `tests/test_candidatos.py::test_respeita_limite` | P-009 | [080-5] |
| `tests/test_assuntos_qualificacao.py::test_listar_candidatos_qualificacao_respeita_limite`, `tests/test_assuntos_sem_cartao.py::test_respeita_limite`, `tests/test_cartoes_pendentes.py::test_respeita_limite` | P-009 | [093-2] |
| `tests/test_moldes_por_contexto.py::test_usado_vem_antes_de_entregue_e_respeita_o_maximo` | P-030 | [093-4] |
| `tests/test_termos_contato.py::test_termos_filtrados_e_limitados` | P-027 | [091-2] |

## 4. Algum texto é analisado só em parte? (AGENTS §4)

**Sim**, nos 16 cortes da tabela (c) acima, nenhum com aprovação de Sidarta, todos com decisão aberta no PLAN; e nos 41 trechos de exceção aprovada (a), com a aprovação registrada em `docs/EXCECOES_TEXTO_INTEGRAL.md`. Este brief não criou corte nem mudou código de produção. A prova é o próprio teste: cada fatia, `LIMIT` e teto de `agente_nw/` tem um estado, e nenhum ficou sem estado.

## 5. Saída dos comandos

Teste de aceite (critério 1):

```
$ .venv/bin/pytest tests/test_sem_corte_de_texto.py -q
..................................                                       [100%]
34 passed in 0.51s
```

Prova do critério 2: `x[:100]` inserido no fim de `agente_nw/nucleo/texto.py` e o gate rodado.

```
$ printf '\n\ndef prova_brief_093(x: str) -> str:\n    return x[:100]\n' >> agente_nw/nucleo/texto.py
$ scripts/verificar.sh
ruff check: ok
ruff format: ok
mypy: ok
pytest: falhou (detalhe completo em logs/verificar_ultimo.txt)
FAILED tests/test_sem_corte_de_texto.py::test_todo_corte_do_codigo_de_producao_tem_estado
1 failed, 1302 passed, 5 deselected in 56.59s
codigo de saida: 1

$ grep -m1 "corte sem estado" logs/verificar_ultimo.txt
E         corte sem estado em agente_nw/nucleo/texto.py:65 [fatia]: 'return x[:100]' — texto por inteiro (AGENTS §4): tire o corte, ou classifique-o (exceção aprovada por Sidarta, corte não analítico no registro, ou violação pendente com destino)
```

Desfeito (cópia de antes restaurada) e conferido limpo:

```
$ cp /tmp/b093/texto.py.orig agente_nw/nucleo/texto.py
$ git diff --stat -- agente_nw/ && echo "agente_nw/ sem diferença" && grep -c prova_brief_093 agente_nw/nucleo/texto.py
agente_nw/ sem diferença
0
```

Gate limpo, antes da entrega:

```
$ scripts/verificar.sh
ruff check: ok
ruff format: ok
mypy: ok
pytest: ok (1303 passed, 5 deselected in 50.66s)
codigo de saida: 0
```

Verificador do 079 (as 8 inconsistências são as de `tests/test_evitar_e_fatos_inteiros.py`, do brief 091, já registradas na lacuna [092-4]; nenhuma é de arquivo deste brief):

```
$ .venv/bin/python scripts/verificar_auditoria_texto.py --raiz .
336 arquivos, 280 certificados, 49 cortam, 7 não analíticos, 0 não conferidos, 6 ponto(s) aguardando decisão de Sidarta
2000 ocorrência(s) da varredura mecânica, todas com destino no relatório

8 inconsistência(s):
  - tests/test_evitar_e_fatos_inteiros.py: a tabela diz 198/198 linhas, mas o arquivo tem 200
  - ocorrência sem destino no relatório: tests/test_evitar_e_fatos_inteiros.py:104 [truncar] (e mais 6 do mesmo arquivo)
```

Manifesto, `logs/arquivos_093.txt`:

```
tests/test_sem_corte_de_texto.py
docs/EXCECOES_TEXTO_INTEGRAL.md
docs/docs/doc_079_auditoria_texto_por_inteiro_2026-11-08.md
docs/docs/doc_093_guarda_permanente_no_gate_2026-11-16.md
docs/PLAN_agente_nw.md
```

`logs/commit_093.txt`:

```
test(texto): guarda permanente do texto por inteiro no gate (brief 093)

tests/test_sem_corte_de_texto.py percorre agente_nw/ por AST e exige que cada
fatia, LIMIT e teto decidido esteja em um de tres estados: excecao aprovada,
corte nao analitico (tabela nova em docs/EXCECOES_TEXTO_INTEGRAL.md) ou violacao
pendente com destino. Codigo de producao nao mudou.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

## RELATÓRIO FINAL

- Brief executado: 093, guarda permanente: o gate acusa todo corte novo de texto.
- Arquivos criados: `tests/test_sem_corte_de_texto.py`; este relatório.
- Arquivos alterados (com resumo da mudança em uma linha cada):
  - `docs/EXCECOES_TEXTO_INTEGRAL.md`: seção "Cortes não analíticos" (15 classes e 79 linhas); a tabela de exceções aprovadas não mudou.
  - `docs/docs/doc_079_auditoria_texto_por_inteiro_2026-11-08.md`: linha de `tests/test_sem_corte_de_texto.py` na seção 6 e grupo "Brief 093 (sem ponto novo)" no apêndice A.
  - `docs/PLAN_agente_nw.md`: Resumo, Doing e Done.
- Arquivos preservados literalmente na área afetada: todo `agente_nw/`, `scripts/verificar_auditoria_texto.py` (não precisou ler a tabela nova: o verificador confere o relatório 079, e a tabela é lida pelo teste) e os testes existentes.
- Script de verificação (o gate, rodado pelo `scripts/agente_entregar.sh`; saída colada): seção 5 (o `agente_entregar.sh` o roda de novo e decide).
- Comandos executados: `pytest` direcionado e da suíte, `scripts/verificar.sh` (duas vezes: com o `x[:100]` de prova e depois de desfeito), `scripts/verificar_auditoria_texto.py`, `ruff`, `mypy`. Nenhum comando chamou o Ollama, tocou `agente.db` ou rede social.
- Manifesto do commit (`logs/arquivos_093.txt` e `logs/commit_093.txt`, conteúdo colado): seção 5.
- Pendências e decisões que ficaram abertas: lacunas abaixo.
- Resumo, Doing, Backlog e Done do `docs/PLAN_agente_nw.md` atualizados: sim (Backlog e Decisões recebem as lacunas pelo `agente_entregar.sh`).

## Lacunas

| # | Lacuna | Destino | Impacto |
|---|---|---|---|
| 1 | P-013: a página da rede social continua cortada em 200.000 caracteres (`extensao.maximo_caracteres_pagina`, `extensao_backend.py` e `modelos/configuracao.py`). O brief 083 fez o corte avisar, mas o valor não tem linha no registro de exceções. Aprovar 200.000 como exceção ou mandar ler a página inteira? | decisão | degrada |
| 2 | P-009: `qualificacao.teto_por_dia` (40) limita quantos assuntos a qualificação e o cartão olham por rodada, escolhidos por cosseno (`consulta.py`, `cli.py`, `queries/assuntos.py`). A aprovação do P-009 vale só para o menu de 5. Aprovar o 40 ou mandar corrigir? | decisão | degrada |
| 3 | P-028: o histórico que vai à redação lê 5 consultas (`historico.LIMITE_PADRAO`), usa 3 (`redacao._CONSULTAS_NO_HISTORICO`) e mostra a mensagem anterior com 100 caracteres (`historico.py`). O brief 081 só tirou o corte do comentário. Aprovar esses tetos ou mandar corrigir? | decisão | nice |
| 4 | P-029 e P-030: a redação recebe 5 notas (`redacao._NOTAS_NO_PROMPT`) e 2 moldes (`moldes.maximo`). O brief 081 deixou cada nota e cada comentário inteiros, mas a quantidade não tem aprovação. Aprovar ou mandar corrigir? | decisão | nice |
| 5 | P-034: o contrato do pedido corta `termos_busca` em 6 itens (`modelos/pedido.py`); o brief 081 tirou só o teto do `evitar`. Aprovar o 6 ou mandar corrigir? (o 5 de `interessa` já é a decisão [091-1]) | decisão | nice |
| 6 | As classes NA-008 a NA-015 da tabela "Cortes não analíticos" foram nomeadas por este brief a partir dos motivos de descarte do apêndice A do 079, e 28 linhas da tabela foram classificadas pelo executor sem destino "não analítico" no 079 (seção 2 deste relatório). Confirmar ou contestar | decisão | nice |
| 7 | A guarda pede que todo brief que mexer numa linha classificada, ou criar corte novo, atualize as listas do `tests/test_sem_corte_de_texto.py` ou a tabela do registro. Os briefs 094 e 095 não têm esses arquivos como alvo e a tabela só é escrita por brief de Sidarta: um deles que toque numa linha classificada para no gate. Autorizar, como foi feito para o relatório 079, que cada brief atualize as listas para os trechos que ele mesmo criar ou alterar, sem aprovar exceção? | decisão | quebra |
| 8 | Limites da varredura: não acusa o teto guardado numa variável e usado adiante (`limite_efetivo = ... teto_por_dia`, `cli.py`), o valor passado a método resolvido só pelo objeto (`self.x(…, 5)`) quando o nome se repete no projeto, nem corte no JavaScript da extensão (`extensao/`, fora do item 2.1). O corte em si (fatia, `LIMIT`) continua acusado onde acontece | dívida | nice |
