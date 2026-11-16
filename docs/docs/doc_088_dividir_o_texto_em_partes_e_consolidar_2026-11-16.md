# DOC 088: dividir o texto em partes que cobrem tudo e consolidar o resultado

**Brief:** `docs/briefs/brief_088_dividir_o_texto_em_partes_e_consolidar_2026-11-08.md`
**Data:** 2026-11-16
**Depende de:** 082 (concluído, `badf676`) e 087 (concluído, `1d03c48`). Conferido no `git log` antes de começar: o erro de janela (`JanelaEstourada`, `FalhaJanela`, `FalhaJanelaEmbedding`) e a fila de revisão com destino já existem.

## 1. O que mudou, em poucas linhas

Quando um texto não cabe numa chamada, o projeto deixa de recusá-lo: divide-o em partes consecutivas que somam exatamente o texto todo, processa cada parte e consolida o resultado por uma regra escrita no docstring de cada uso.

- **Uma peça só, `agente_nw/nucleo/texto_integral.py`.**
  - `dividir(texto, orcamento)`: texto que cabe volta numa parte só, idêntico ao original e sem marcação. Texto que não cabe é dividido preferindo fim de parágrafo, depois de linha, de frase e de espaço; só em último caso, no limite exato. Vizinhas se sobrepõem em 500 caracteres. Antes de devolver, `dividir` confere que `reconstruir(partes) == texto` e levanta erro se não for.
  - `orcamento_do_texto(num_ctx, prompt_sem_texto)`: o orçamento por parte, em tokens, pelo estimador compartilhado do brief 082 (`estimar_tokens_conservador`). Desconta do `num_ctx` da tarefa o prompt montado com o texto vazio, o maior aviso "parte K de N" e 2 tokens de folga do estimador.
  - `processar_dividindo`: quando o servidor recusa por tamanho (`JanelaEstourada`), o orçamento cai à metade e o texto é dividido de novo, até 4 vezes. A recusa superada é descartada da `fila_revisao` com motivo, para não ficar como pendência falsa. Quando a metade não muda a divisão (quem estoura é o resto do prompt), a recusa sobe em voz alta.
  - `texto_para_o_prompt(parte)`: a parte de um texto dividido entra no cerco do dado externo com "[parte K de N de um documento maior]" na primeira linha.
  - Consolidação comum: `consolidar_vetores` (média ponderada normalizada), `consolidar_fatos` (união ordenada, sem repetição exata, guardando a parte de origem) e `consolidar_unicos` (campo único: valor igual é aceito, valores diferentes viram `Divergencia`, sem voto).
- **`extrair_de_texto` (`perfil/extrator.py::processar_item`).** O item passa pela divisão. Texto que cabe produz o mesmo prompt de antes, caractere por caractere. Texto dividido é consolidado assim:
  - tags, fatos datados e línguas: união ordenada;
  - os outros campos: únicos;
  - campo único divergente (por exemplo, cidade): o item vai inteiro para a `fila_revisao`, com os valores e as partes na `entrada` e só os campos no `erro`. Fica com erro na `fila_extracao` com o mesmo `(fila_revisao id=N)`, para o reenvio do brief 087 achar a linha;
  - parte sem resposta válida: invalida o item inteiro, e nada dele é gravado;
  - o número de partes fica em `fila_extracao.partes_lidas`.
- **`extrair_captura_rede_social` (`coleta/capturas/extrator.py::extrair`).** Mesma divisão. O prompt saiu para `nucleo/prompts/extrair_captura_rede_social.py`, com `VERSAO` e sem mudança de texto. Consolidação:
  - partes descartadas pelo modelo não contam;
  - `data_do_fato` e `tipo` são campos únicos: divergentes, o bloco vai para a `fila_revisao` e não é gravado;
  - `conteudo` é a união ordenada.
- **Vetor (`nucleo/llm.py::embeddar_em_partes`).** Cada parte é embeddada numa chamada própria, com orçamento de `LIMITE_TOKENS_EMBEDDING`. O resultado é a média dos vetores ponderada pelo número de caracteres e normalizada. Uma falha numa parte invalida o vetor, nunca há vetor parcial. Ainda não tem chamador: os vetores do agrupamento, do contato e do tema são do brief 089 (item 2.6).
- **Registro de cobertura (2.4).** Migração 021: uma coluna `fila_extracao.partes_lidas INTEGER NULL`, com `1` para inteiro numa chamada, `N` para lido em partes e `NULL` para o que foi processado antes deste brief. Escolhi coluna e não tabela porque um item da fila é lido uma vez por processamento e o reenvio regrava a linha. A versão já tinha coluna (`gerado_por_prompt_versao`, migração 019). `extrair_de_texto` sobe para `2026-11-16-1`, e o prompt de captura ganha versão (`2026-11-16-1`; antes não tinha nenhuma).
- **Relatório 079.** Seção 6 e apêndice A dos arquivos tocados e criados, como a autorização de 2026-11-16 permite. P-019 passa a `CORRIGIDO (brief 088)`, com a decisão 2.1 a 2.5 deste brief anotada junto da decisão do 082. Nenhum ponto novo. Verificador em 0.

## 2. Algum texto é analisado só em parte? (AGENTS §4), por tarefa tocada

| Tarefa | Resposta | Prova |
|---|---|---|
| `extrair_de_texto` | **Não.** O item vai inteiro: numa chamada ou em partes que cobrem tudo. Uma parte que falha invalida o item, que vai à `fila_revisao`; nunca é gravado o resultado parcial. | `test_reconstruir_as_partes_reproduz_o_original_byte_a_byte` (24 casos); `test_marcadores_do_meio_e_do_ultimo_caractere_chegam_a_um_prompt` (300.000 caracteres, e os prompts aceitos reconstroem o texto); `test_servidor_que_recusa_por_tamanho_divide_o_orcamento_e_cobre_tudo`; `test_parte_invalida_invalida_o_item_e_ele_vai_a_fila`. O `grep` abaixo mostra que `item.texto` só chega ao modelo por `processar_dividindo`. |
| `extrair_captura_rede_social` | **Não, neste extrator.** O bloco vai inteiro, em uma ou mais partes. O teto anterior a ele, de 5.000 caracteres por post no navegador (P-014), não é deste brief e continua aguardando decisão de Sidarta. | `test_bloco_longo_de_rede_social_e_lido_em_partes_e_consolidado` (os prompts reconstroem o bloco de 40.000 caracteres); `test_parte_invalida_de_bloco_longo_invalida_o_bloco`; `test_bloco_longo_com_data_divergente_vai_para_revisao`. |
| embedding (`embeddar_em_partes`) | **Não.** Todas as partes são embeddadas; falha numa delas invalida o vetor. | `test_embeddar_em_partes_pondera_pelo_numero_de_caracteres_de_cada_parte`; `test_embedding_recusado_por_tamanho_cai_a_metade_e_cobre_o_texto`; `test_falha_numa_parte_invalida_o_vetor`. |

## 3. Testes do brief (seção 4), um por um

| # | Teste do brief | Teste(s) em `tests/test_texto_integral.py` |
|---|---|---|
| 1 | cobertura byte a byte: vazio, 1 caractere, parágrafo gigante, sem espaços, emoji, 34.195 caracteres | `test_reconstruir_as_partes_reproduz_o_original_byte_a_byte` (6 textos × 4 orçamentos, comparação dos bytes UTF-8), `test_texto_que_cabe_vai_inteiro_numa_parte_so`, `test_texto_grande_e_dividido_em_varias_partes_e_prefere_fim_de_paragrafo` |
| 2 | texto curto produz exatamente o mesmo prompt de antes | `test_texto_curto_produz_exatamente_o_mesmo_prompt_de_antes`, `test_bloco_curto_de_rede_social_produz_exatamente_o_mesmo_prompt_de_antes`. O tamanho e o SHA-256 esperados foram recalculados à parte a partir do código de `badf676` (`git show badf676:...`) e conferem (seção 4) |
| 3 | marcador no meio e no último caractere de 300.000 caracteres | `test_marcadores_do_meio_e_do_ultimo_caractere_chegam_a_um_prompt` |
| 4 | sobreposição de 500; aviso "parte K de N" dentro do cerco | `test_vizinhas_se_sobrepoem_em_500_caracteres`, `test_aviso_parte_k_de_n_vai_dentro_do_cerco` |
| 5 | média ponderada normalizada 3:1 | `test_media_ponderada_normalizada_confere_com_calculo_manual`, `test_embeddar_em_partes_pondera_pelo_numero_de_caracteres_de_cada_parte`, `test_embeddar_em_partes_texto_curto_devolve_o_vetor_de_uma_chamada_so` |
| 6 | parte inválida invalida o item, que vai à fila (banco isolado) | `test_parte_invalida_invalida_o_item_e_ele_vai_a_fila`, `test_falha_numa_parte_invalida_o_vetor`, `test_parte_invalida_de_bloco_longo_invalida_o_bloco` |
| 7 | fatos iguais uma vez; fato único divergente vira aviso e revisão | `test_fatos_iguais_em_partes_vizinhas_aparecem_uma_vez`, `test_consolidar_fatos_e_uniao_ordenada_que_guarda_a_parte_de_origem`, `test_fato_unico_divergente_vira_aviso_e_revisao_sem_voto`, `test_consolidar_unicos_aponta_a_divergencia_sem_escolher_valor`, `test_bloco_longo_com_data_divergente_vai_para_revisao` |
| 8 | servidor que recusa por tamanho: orçamento à metade, texto coberto | `test_servidor_que_recusa_por_tamanho_divide_o_orcamento_e_cobre_tudo` (a recusa superada não fica na fila), `test_recusa_de_texto_que_nao_se_divide_mais_vai_a_fila_uma_vez`, `test_embedding_recusado_por_tamanho_cai_a_metade_e_cobre_o_texto` |
| 9 | registro de cobertura `1` e `N` | `test_registro_de_cobertura_grava_1_para_texto_curto_e_n_para_dividido` (também confere `NULL` para o item não processado e a versão nova do prompt) |

## 4. Critérios de aceite (seção 6), com saída

**(1) e (2): teste de aceite verde, e o teste 2 verde.**

```
$ .venv/bin/pytest tests/test_texto_integral.py -q
.................................................                        [100%]
49 passed in 3.89s

$ .venv/bin/pytest tests/test_texto_integral.py -q -k "mesmo_prompt_de_antes"
..                                                                       [100%]
2 passed, 47 deselected in 0.14s
```

Conferência independente das impressões do prompt antigo, montadas a partir do código de `badf676` num diretório temporário:

```
$ git show badf676:agente_nw/nucleo/prompts/extrair_de_texto.py > $d/antigo_extrair.py
$ git show badf676:agente_nw/coleta/capturas/extrator.py > $d/antigo_captura.py
$ .venv/bin/python $d/conf.py $d
2577 7f41b4bf611403e0b9ba23e487df453accf2aff68a06c3a550d0ac13fca30b9e
1224 e699e09c9dd0b9a68b7661e67b97878511943ec223774a18ba7b67b06aa82cef
```

São os mesmos valores de `_PROMPT_ANTIGO_EXTRAIR` e `_PROMPT_ANTIGO_CAPTURA` no teste.

**(3): nenhum `item.texto` cru enviado ao modelo em `perfil/extrator.py`.**

```
$ grep -n "item.texto" agente_nw/perfil/extrator.py
116:    entrada = f"Valores divergentes entre as partes:\n{valores}\n\nTexto do item:\n{item.texto}"
154:            item.texto, orcamento, processar, JanelaEstourada, refazer
```

- A linha 116 é a `entrada` da `fila_revisao` (texto guardado para a revisão humana, não enviado ao modelo).
- A linha 154 é o argumento de `processar_dividindo`. O que chega ao `gerar_json` é `construir_prompt(texto_integral.texto_para_o_prompt(parte))`, na l. 141.

**(4): gate.** Roda dentro do `scripts/agente_entregar.sh 088`, e a saída fica em `logs/entregar_ultimo.txt`. Antes dele, rodei os mesmos passos à mão (saída no bloco do relatório final).

**(5): verificador do 079 devolve 0.**

```
$ .venv/bin/python scripts/verificar_auditoria_texto.py
328 arquivos, 268 certificados, 53 cortam, 7 não analíticos, 0 não conferidos, 18 ponto(s) aguardando decisão de Sidarta
1461 ocorrência(s) da varredura mecânica, todas com destino no relatório
rc=0
```

Antes da recertificação, o verificador dava 191 inconsistências: 4 arquivos novos fora da tabela, 8 contagens de linha e 179 ocorrências sem destino. A correção:

- renumerei as citações `arquivo:linha` dos 11 arquivos alterados pela correspondência entre a versão de `HEAD` e a do disco (`difflib`, script em `/tmp/b088/`, fora do repositório);
- as três linhas que deixaram de existir foram apontadas à mão para a linha equivalente (`capturas/extrator.py:68` → `:108` e `:66` → `:110`; `perfil/extrator.py:78` → `:139`);
- reescrevi as linhas da seção 6 dos arquivos tocados e incluí as 4 novas;
- incluí o grupo "Brief 088 (sem ponto novo)" no apêndice A, com 65 linhas citadas, todas descartadas com a razão;
- P-019 passou a `CORRIGIDO (brief 088)`.

## 5. Escolhas do executor dentro do brief

- **Coluna e não tabela** para o registro de cobertura (2.4 deixa a escolha ao executor). A razão está na seção 1.
- **A captura de rede social não grava `partes_lidas`.** O bloco capturado não é item de `fila_extracao` e o fato da captura não tem coluna de proveniência (dívida [066-1]). A versão nova do prompt vai ao `chamadas_llm.jsonl` por `versao_prompt`. Ver Lacunas.
- **Prompt de captura em módulo próprio.** O 2.4 pede versão nova "dos prompts dessas duas tarefas em `nucleo/prompts/`", e o de captura não tinha nem módulo nem versão. Saiu sem mudança de texto, provado pelo teste 2. O cerco do bloco inteiro continua como estava (dívida [068-2], fora deste brief). Só a parte de um bloco dividido entra cercada, porque o aviso "parte K de N" tem de ir dentro do cerco (2.1).
- **Fora dos arquivos-alvo, por consequência direta e mínima:**
  - `coleta/capturas/leitor.py`: uma linha, passa `conexao=conexao` a `extrair`, para a divergência chegar à `fila_revisao`;
  - `tests/llm_falso.py`, `tests/test_capturas_extrator.py`, `tests/test_capturas_leitor.py`: `num_ctx` nos clientes falsos, porque os protocolos pedem isso agora;
  - `tests/test_migracao_comentarios.py`, `tests/test_migracao_genero.py`: `MAX(versao)` de 20 para 21, a mesma edição que o 087 fez;
  - `nucleo/database/queries/fila_extracao.py`: `registrar_partes`.

  Nenhuma asserção de comportamento antiga foi afrouxada.

## RELATÓRIO FINAL
- Brief executado: 088, dividir o texto em partes que cobrem tudo e consolidar o resultado.
- Arquivos criados:
  - `agente_nw/nucleo/texto_integral.py`: divisão, reconstrução, novo processamento com orçamento à metade e consolidação.
  - `agente_nw/nucleo/prompts/extrair_captura_rede_social.py`: prompt de captura com `VERSAO` e prompt de parte cercado.
  - `scripts/migracoes/021_cobertura_texto.sql`: `fila_extracao.partes_lidas`.
  - `tests/test_texto_integral.py`: 49 testes, seção 4 do brief.
  - Este relatório.
- Arquivos alterados (com resumo da mudança em uma linha cada):
  - `agente_nw/perfil/extrator.py`: `processar_item` usa a divisão; `_consolidar` (união e campos únicos); `DivergenciaEntrePartes` para a `fila_revisao`; grava `partes_lidas`.
  - `agente_nw/coleta/capturas/extrator.py`: `extrair` usa a divisão; `_consolidar` (descartadas não contam; data e tipo únicos, divergência à revisão); prompt movido para `nucleo/prompts/`.
  - `agente_nw/coleta/capturas/leitor.py`: passa a conexão a `extrair` (uma linha).
  - `agente_nw/nucleo/llm.py`: `num_ctx(tarefa)` no cliente base; `embeddar_em_partes`, sem mexer no que o brief 082 criou.
  - `agente_nw/nucleo/prompts/extrair_de_texto.py`: `VERSAO` `2026-11-16-1`; o texto do prompt não mudou.
  - `agente_nw/nucleo/database/queries/fila_extracao.py`: `registrar_partes`.
  - `tests/llm_falso.py`, `tests/test_capturas_extrator.py`, `tests/test_capturas_leitor.py`: `num_ctx` (e `versao_prompt`) nos clientes falsos.
  - `tests/test_migracao_comentarios.py`, `tests/test_migracao_genero.py`: última migração 21.
  - `docs/docs/doc_079_auditoria_texto_por_inteiro_2026-11-08.md`: seção 6 e apêndice A dos arquivos deste brief; P-019 em `CORRIGIDO (brief 088)`; citações deslocadas renumeradas.
  - `docs/PLAN_agente_nw.md`: Resumo (último brief e última migração), Backlog ([066-1] anotado) e Done.
- Arquivos preservados literalmente na área afetada: `config/` inteiro (`git diff -- config/` com 0 linhas); o texto dos dois prompts (provado pelo teste 2); a conferência de janela do brief 082 em `nucleo/llm.py` (`gerar_json`, `embeddar`, as classes de erro); `nucleo/estimativa_tokens.py`; `nucleo/database/queries/fila_revisao.py`; `prompts/redigir_ganchos.py::cortar_por_tamanho`; `nucleo/prompts/seguranca.py`.
- Script de verificação (o gate, rodado pelo `scripts/agente_entregar.sh`; a saída dele fica em `logs/entregar_ultimo.txt`). Antes dele, rodei os mesmos passos à mão:

```
$ .venv/bin/ruff check . ; .venv/bin/ruff format --check . ; .venv/bin/mypy agente_nw
All checks passed!
298 files already formatted
Success: no issues found in 125 source files
$ .venv/bin/pytest -q
1194 passed, 5 deselected in 86.57s (0:01:26)
$ .venv/bin/python scripts/verificar_auditoria_texto.py
328 arquivos, 268 certificados, 53 cortam, 7 não analíticos, 0 não conferidos, 18 ponto(s) aguardando decisão de Sidarta
1461 ocorrência(s) da varredura mecânica, todas com destino no relatório
rc=0
$ git diff -- config/ | wc -l
       0
```

- Comandos executados:
  - `pytest` (o arquivo do brief, os seis arquivos vizinhos e a suíte inteira), `ruff`, `mypy` e `verificar_auditoria_texto.py`, como acima;
  - `git show badf676:...` e um script em diretório temporário para recalcular as impressões do prompt antigo;
  - um script em `/tmp/b088/` para renumerar as citações do relatório 079;
  - `scripts/agente_entregar.sh 088`.

  Nenhum comando chamou o Ollama nem tocou `dados/agente.db`.
- Manifesto do commit: `logs/commit_088.txt` e `logs/arquivos_088.txt` (conteúdo no commit; depois da entrega, `logs/entregue_088_*.txt`).
- Pendências e decisões que ficaram abertas: ver Lacunas abaixo; nenhuma exige Sidarta.
- Resumo, Doing, Backlog e Done do `docs/PLAN_agente_nw.md` atualizados: sim. Doing continua "(nenhum)", e o Backlog recebe as lacunas pelo `agente_lacunas.py`.

## Lacunas

| # | Lacuna | Destino | Impacto |
|---|---|---|---|
| 1 | O bloco de rede social lido em partes não registra em quantas partes foi lido. O fato da captura não tem coluna de proveniência (dívida [066-1]), e `partes_lidas` só existe em `fila_extracao`. A versão do prompt vai só ao `chamadas_llm.jsonl` | dívida | nice |
| 2 | Nenhum teste `llm_real` confere como o modelo real responde a uma parte com o aviso "[parte K de N de um documento maior]" no cerco. Os testes deste brief usam clientes falsos, como a seção 4 manda, e o comportamento do `qwen` diante de uma parte (inventar o que falta, por exemplo) não foi medido | dívida | nice |
