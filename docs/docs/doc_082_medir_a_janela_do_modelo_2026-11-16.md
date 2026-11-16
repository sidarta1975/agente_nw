# DOC 082: medir a janela do modelo (prompt, embedding e resposta nunca cortados em silêncio)

**Brief:** `docs/briefs/brief_082_medir_a_janela_do_modelo_2026-11-08.md`
**Data:** 2026-11-16
**Depende de:** 079 (concluído, `700a43a`) e 087 (concluído, `1d03c48`). Conferido no PLAN e no `git log` antes de começar.

## 1. O que mudou, em poucas linhas

Quando um prompt não cabe no `num_ctx` da tarefa, quando o texto de um embedding passa dos 8.192 tokens do `bge-m3` ou quando a resposta para por tamanho, o cliente de LLM deixa de devolver o resultado como se estivesse bom. Ele grava uma linha `"janela": true` no `chamadas_llm.jsonl`, não usa a resposta e levanta um erro de janela.

- **Geração.** O erro é `FalhaJanela`, subclasse de `FalhaJsonInvalido`. É o erro que os chamadores das 14 tarefas de geração já tratam, por isso nenhum ponto de chamada mudou. O item vai para a `fila_revisao` com o prompt inteiro e com o mesmo `(fila_revisao id=N)` no texto, de modo que `extrair_de_texto` continua reenviável pelo brief 087.
- **Embedding.** O erro é `FalhaJanelaEmbedding`, subclasse de `ValueError`, o que `embeddar` já levantava para vetor inválido. Não há `fila_revisao`, porque embedding nunca teve uma.
- **Base comum.** As duas classes descendem de `JanelaEstourada`. É o tipo único que o brief 088 vai capturar para dividir o texto.

Quatro conferências:

1. **Antes da chamada (Ollama).** A estimativa conservadora é o maior entre `palavras × 1,4` e `caracteres ÷ 3`. Se passar do `num_ctx`, a chamada é recusada sem ir ao servidor.
2. **Depois da chamada (Ollama).** Se `prompt_eval_count` for maior ou igual ao `num_ctx`, o prompt foi cortado: é recusado, sem nova tentativa, porque o mesmo prompt cortaria de novo.
3. **Resposta cortada (os quatro clientes).** São recusadas as respostas com:
   - `done_reason == "length"` (Ollama);
   - `stop_reason` igual a `max_tokens` ou `model_context_window_exceeded` (Anthropic);
   - `finishReason == "MAX_TOKENS"` (Gemini);
   - `finish_reason == "length"` (OpenAI).

   A recusa vale mesmo com JSON válido.
4. **Embedding.** Cada texto é estimado antes da chamada. Quando o pedido tem um texto só, a conferência também usa o `prompt_eval_count` do `/api/embed`, que é a soma dos textos do pedido.

O estimador saiu de `redigir_ganchos.py` e foi para `agente_nw/nucleo/estimativa_tokens.py`. O `cortar_por_tamanho` continua usando `palavras × 1,4`, a mesma função, e o comportamento ficou idêntico, como o brief manda. O cliente usa `estimar_tokens_conservador`, que se apoia nessa mesma função.

**Algum texto é analisado só em parte (AGENTS §4)?** Não por este brief. Nada aqui corta texto. O que não cabe é recusado e vai inteiro para a fila. Antes, o Ollama cortava em silêncio. O único corte que continua na área é o `cortar_por_tamanho` (P-033, exceção aprovada), que não mudou. Provas:

- `test_redigir_ganchos_usa_o_estimador_compartilhado`;
- os testes antigos do corte (`tests/test_redacao_prompt.py`, `tests/test_comentario_sob_orcamento.py`, `tests/test_whatsapp_no_prompt.py`), todos verdes sem edição.

## 2. As 15 tarefas: janela e como cada uma trata falha

O `config/llm_routing.yaml` tem 14 tarefas de geração. A 15ª chamada de modelo do produto é o embedding. Nenhum desenho de tratamento mudou: o erro de janela cai no mesmo `except` de antes.

| Tarefa | num_ctx air16 | num_ctx pro48 | Como trata falha hoje (e portanto o erro de janela) |
|---|---|---|---|
| `qualificar` | 2.048 | 8.192 | `relevancia/qualificador.py:86`: captura `FalhaJsonInvalido`, soma `resumo.erros` e pula o assunto; o item fica na `fila_revisao` pelo cliente |
| `rotular` | 2.048 | 8.192 | `relevancia/qualificador.py:71`: igual ao `qualificar` (pula o assunto, conta erro) |
| `cartao` | 4.096 | 16.384 | `relevancia/cartoes.py:61`: nova tentativa até `_MAX_TENTATIVAS`; esgotadas, `fila_revisao` com `tarefa="cartao"` |
| `cruzar_por_que` | 4.096 | 16.384 | `relevancia/cruzamento.py:93`: nova tentativa; esgotadas, `fila_revisao` e devolve `None` |
| `avaliar_relacao_objetivo` | 4.096 | 16.384 | `relevancia/cruzamento.py:128`: nova tentativa; esgotadas, `fila_revisao` e devolve `None` |
| `extrair_de_texto` | 4.096 | 16.384 | `perfil/extrator.py:81`: marca o erro na `fila_extracao` com `(fila_revisao id=N)`; reenviável por `agente_nw revisao reenviar` (brief 087) |
| `extrair_captura_rede_social` | 4.096 | 16.384 | `coleta/capturas/extrator.py:69`: devolve `None` (o bloco não vira fato); item na `fila_revisao` |
| `extrair_pedido` | 4.096 | 8.192 | sem `except` em `nucleo/pedido.py:42`; na CLI, `cli.py:945` imprime "FALHA: não consegui entender o pedido"; no console, `fluxo.py:270` grava "deu errado em <etapa>" no pedido |
| `desempatar_perfil` | 2.048 | 2.048 | `nucleo/localizacao.py:109`: devolve `None` (sem desempate automático, segue o fluxo de confirmação) |
| `redigir_ganchos` | 8.192 | 16.384 | `nucleo/orquestracao.py:215`: vira `FalhaNaRedacao`; a CLI imprime "não consegui redigir os ganchos" (`cli.py:999`), o console mostra a falha na página |
| `extrair_termos_contato` | 4.096 | 4.096 | `nucleo/termos_contato.py:66`: devolve `[]` (sem termos do contato) |
| `descrever_tema` | 2.048 | 2.048 | `perfil/inferencia.py:113`: o próprio termo vira a descrição do tema |
| `descrever_imagem` | 4.096 | 4.096 | `coleta/capturas/imagens.py:63`: devolve `None` (a imagem não vira descrição) |
| `prerotular_calibracao` | 2.048 | 8.192 | `agrupamento/calibracao.py:124`: o par fica sem rótulo do modelo (`continue`) |
| embeddings (`bge-m3`) | 8.192 (limite do modelo) | 8.192 | sem `fila_revisao`; `redacao.py:111` captura qualquer exceção e fica com os fatos mais recentes; nos demais (`agrupador.py:89`, `consulta.py:133`, `perfis.py:630`, `cruzamento.py:410`, `inferencia.py:93`/`:120`, `configurador.py:29`, `console/app.py:989`) o erro sobe ao comando, como qualquer `ValueError` de `embeddar` já subia |

Nos clientes de API, a estimativa antes da chamada não é aplicada. O `num_ctx` é a janela do modelo local, e os provedores de API não cortam o prompt em silêncio: recusam com erro HTTP, que já cai no backoff e na `fila_revisao`. A conferência de resposta cortada vale para os quatro clientes. O teste `test_api_nao_bloqueia_pelo_num_ctx_do_ollama` fixa essa leitura.

## 3. Conferência do 1,4 (item 2.6), contra o Ollama real

O porteiro foi consultado antes, como manda a regra da máquina:

```
$ porteiro cabe qwen2.5:14b --porta 11435
Cabe: qwen2.5:14b já está carregado na porta 11435 agora. Usar esse modelo não tira ninguém da memória.
rc=0
$ porteiro cabe bge-m3 --porta 11435
Não cabe: já são 2 modelos carregados, o máximo configurado (2).
Para bge-m3:latest entrar, sairia qwen2.5:7b (é o que expira primeiro).
A conta é estimativa: bge-m3:latest não está carregado agora, então o tamanho vem do arquivo no disco mais 5,0 GB de folga de contexto.
rc=1
```

O `bge-m3` não foi carregado (código 1). O `qwen2.5:14b`, sim, com o perfil `pro48`, `num_ctx` de 16.384. O prompt de redação foi montado por `construir_prompt` com cinco fatos realistas em português e uma consulta de histórico (script em `/tmp/conf082/medir.py`, fora do repositório; nenhum banco foi tocado):

```
chaves da resposta: ['created_at', 'done', 'done_reason', 'eval_count', 'eval_duration', 'load_duration', 'model', 'prompt_eval_cached_count', 'prompt_eval_count', 'prompt_eval_duration', 'response', 'total_duration']
done_reason: stop
prompt_eval_count: 2986 eval_count: 323
palavras: 1492 caracteres: 9731
estimativa palavras x 1,4: 2088
caracteres / 3: 3243
razão real tokens/palavra: 2.001
razão real caracteres/token: 3.259
com num_predict 5 -> done_reason: length | response: '{"ganchos":'
```

**Resultado:** o 1,4 subestima em 30%. O `qwen2.5:14b` contou 2,0 tokens por palavra nesse prompt. O `caracteres ÷ 3` superestima em 8,6%. Por isso a estimativa conservadora do cliente fica acima da medida real, como deve ficar.

Consequência para o P-033 (exceção aprovada, não alterada aqui): o orçamento do `cortar_por_tamanho` é `0,73 × num_ctx` medido com o 1,4. Em tokens reais, isso chega a cerca de `0,73 × 2,0 ÷ 1,4 ≈ 1,04 × num_ctx`. Um pedido grande pode passar do corte e ainda estourar a janela. Até hoje esse prompt era cortado em silêncio pelo Ollama; a partir deste brief, ele é **recusado** (`FalhaJanela` → `FalhaNaRedacao`). Mexer no 1,4 ou na fração muda o comportamento do corte, que o brief manda manter idêntico. Fica como decisão (Lacuna 1).

Também foi feita uma conferência do código novo de ponta a ponta contra o mesmo Ollama, com banco e log em `/tmp/conf082/`. A primeira chamada é normal. A segunda tem `num_predict` igual a 5 só na memória, para forçar o corte; o YAML não foi tocado.

```
normal: temas=['Aumento da conectividade aeroportuária em cidades do Nordeste', 'Investimentos em infraestrutura aeroportuária para melhorar a segurança e a eficiência', 'Desafios operacionais enfrentados pelas companhias aéreas regionais']
cortada: tarefa 'qualificar' recusada (fila_revisao id=2): janela do modelo: resposta cortada por tamanho (limite de saída=5 tokens)
{"janela": true, "tarefa": "qualificar", "modelo": "qwen2.5:14b", "perfil": "pro48", "quando": "2026-11-16T05:08:21.890226+00:00", "motivo": "resposta_cortada", "tokens_medidos": 57, "tokens_estimados": 34, "num_ctx": 8192, "num_predict": 5, "parada": "length"}
```

Repetir o mesmo prompt deu `prompt_eval_cached_count` igual a 0 nas duas vezes, com `prompt_eval_count` de 2.749 nas duas. O significado do campo de cache não foi provado num caso com cache de verdade (Lacuna 4).

## 4. Relatório 079

- P-019, P-040, P-041 e P-042 passaram a `CORRIGIDO (brief 082)`, com a decisão em uma linha cada. O P-033 continua `EXCEÇÃO APROVADA`, com a conferência do 1,4 registrada aqui, na seção 3.
- **Seção 6.**
  - `agente_nw/nucleo/llm.py` passou para 924/924 e `CERTIFICADO`. Os pontos P-040 e P-042 ficaram citados, agora corrigidos.
  - `agente_nw/nucleo/prompts/redigir_ganchos.py` passou para 308/308. Continua `CORTA` por causa do P-033.
  - Linhas novas: `agente_nw/nucleo/estimativa_tokens.py` (24/24) e `tests/test_janela_modelo.py` (396/396), as duas `CERTIFICADO`.
- **Apêndice A.**
  - As citações antigas de `llm.py` e `redigir_ganchos.py` foram renumeradas pela correspondência linha a linha (`difflib`) entre a versão do HEAD e a atual.
  - As 46 ocorrências novas de código estão num grupo "Brief 082 (sem ponto novo)", com a razão do descarte; nenhuma corta texto.
  - As 46 ocorrências do teste novo entraram no grupo dos arquivos de teste (475 → 521).
  - Os números narrativos (324 arquivos, 1.393 ocorrências) foram acertados, como o brief 087 fez.
- **Nenhum ponto novo** e nenhuma exceção aprovada.

## RELATÓRIO FINAL
- Brief executado: 082, medir a janela do modelo.
- Arquivos criados:
  - `agente_nw/nucleo/estimativa_tokens.py`: o estimador compartilhado.
  - `tests/test_janela_modelo.py`: 24 testes, seção 4 do brief.
  - Este relatório.
- Arquivos alterados (com resumo da mudança em uma linha cada):
  - `agente_nw/nucleo/llm.py`: `JanelaEstourada`/`FalhaJanela`/`FalhaJanelaEmbedding`; `_chamar` devolve `_RespostaBruta` (texto, `prompt_eval_count`, motivo de parada); estimativa antes e medida depois em `gerar_json`; conferência em `embeddar`; linha `"janela": true` no log; motivo de parada nos quatro clientes.
  - `agente_nw/nucleo/prompts/redigir_ganchos.py`: o estimador saiu daqui e é reexportado de `nucleo/estimativa_tokens.py`; `cortar_por_tamanho` não mudou.
  - `docs/docs/doc_079_auditoria_texto_por_inteiro_2026-11-08.md`: quatro pontos em `CORRIGIDO (brief 082)`, seção 6 e apêndice A dos arquivos deste brief.
  - `docs/PLAN_agente_nw.md`: Resumo, Done e a dívida [079-7] marcada como resolvida.
- Arquivos preservados literalmente na área afetada: `config/llm_routing.yaml` e todo o `config/` (`git diff -- config/` com 0 linhas: nenhum `num_ctx` nem `num_predict` mudou); todos os pontos de chamada das 14 tarefas; `nucleo/database/queries/fila_revisao.py`; `nucleo/redacao.py`.
- Script de verificação (o gate, rodado pelo `scripts/agente_entregar.sh`; a saída dele fica em `logs/entregar_ultimo.txt`). Antes dele, rodei os mesmos passos à mão:

```
$ .venv/bin/pytest tests/test_janela_modelo.py -q
........................                                                 [100%]
24 passed in 1.39s
$ .venv/bin/ruff check . ; .venv/bin/ruff format --check . ; .venv/bin/mypy agente_nw
All checks passed!
295 files already formatted
Success: no issues found in 123 source files
$ .venv/bin/pytest -q
1145 passed, 5 deselected in 96.88s (0:01:36)
$ git diff -- config/ | wc -l
       0
$ .venv/bin/python scripts/verificar_auditoria_texto.py
324 arquivos, 264 certificados, 53 cortam, 7 não analíticos, 0 não conferidos, 18 ponto(s) aguardando decisão de Sidarta
1393 ocorrência(s) da varredura mecânica, todas com destino no relatório
rc=0
```

- Comandos executados:
  - `pytest`, `ruff`, `mypy` e `verificar_auditoria_texto.py`, como acima;
  - `porteiro cabe` para os dois modelos;
  - três scripts em `/tmp/conf082/` contra o Ollama da porta 11435, só com `qwen2.5:14b` e com banco e log em `/tmp`;
  - `curl /api/show` do `bge-m3`, que lê metadados e não carrega o modelo;
  - `scripts/agente_entregar.sh 082`.

  Nenhum comando tocou `dados/agente.db`.
- Manifesto do commit: `logs/commit_082.txt` e `logs/arquivos_082.txt` (conteúdo no commit).
- Pendências e decisões que ficaram abertas: ver Lacunas abaixo.
- Resumo, Doing, Backlog e Done do `docs/PLAN_agente_nw.md` atualizados: sim. Doing continua "(nenhum)" e o Backlog recebe as lacunas pelo `agente_lacunas.py`.

## Lacunas

| # | Lacuna | Destino | Impacto |
|---|---|---|---|
| 1 | O 1,4 do estimador subestima o `qwen2.5:14b` em 30% (2,0 tokens por palavra medidos num prompt real de redação, seção 3). O orçamento do `cortar_por_tamanho` (`0,73 × num_ctx`, P-033) chega a cerca de 1,04 × `num_ctx` em tokens reais. Um pedido grande que antes era cortado em silêncio pelo Ollama agora é recusado (`FalhaNaRedacao`). Ajustar o 1,4 ou a fração muda o corte aprovado no P-033, então a decisão é sua. Não conferido no `qwen3:4b` do `air16` | decisão | degrada |
| 2 | O limite de 8.192 do `bge-m3` vem do `bert.context_length` de `/api/show`. Não foi provado que o `/api/embed` usa esse valor, e não um `num_ctx` padrão menor, nem que a resposta real traz `prompt_eval_count`: o porteiro deu código 1 para o `bge-m3` e o modelo não foi carregado | backlog | degrada |
| 3 | `fila_revisao.classe_do_erro` classifica o erro de janela como `outro` em `revisao ver`. Uma classe `janela` exigiria mexer em `fila_revisao.py`, que não é alvo deste brief | backlog | nice |
| 4 | Não está provado se o `prompt_eval_count` do Ollama exclui os tokens que vêm do cache (`prompt_eval_cached_count`, que deu 0 nas duas medições). Se excluir, a medida depois da chamada conta menos que o real, e só a estimativa antes da chamada pega o estouro | dívida | nice |
| 5 | `cartao`, `cruzar_por_que` e `avaliar_relacao_objetivo` repetem a chamada quando recebem `FalhaJsonInvalido`, então um estouro de janela vira até `_MAX_TENTATIVAS` linhas na `fila_revisao` (a recusa pela estimativa não chama o servidor). É o mesmo desenho de antes para qualquer falha (2.3 manda não mudá-lo); o brief 088, que captura `JanelaEstourada`, é o lugar de tratar | backlog | nice |
| 6 | No relatório 079, o texto do P-033 ainda aponta o estimador em `redigir_ganchos.py` ("l. 93", "`:93`"), que agora está em `agente_nw/nucleo/estimativa_tokens.py:15`. As tabelas das seções 5.b e 7 ainda dizem que não há conferência. A autorização deste brief cobre só a seção 6, o apêndice A e o estado dos quatro pontos | dívida | nice |

---

## Adendo do brief 098 (2026-11-16): o 2,0 entra no código

A medição da seção 3 (razão real 2,001 tokens por palavra no `qwen2.5:14b`, contra 1,4 no código) foi aplicada pelo brief 098: `_TOKENS_POR_PALAVRA` em `agente_nw/nucleo/estimativa_tokens.py` passou de 1.4 para 2.0, por decisão de Sidarta. A regra da decisão 2.2 não mudou (o estimador devolve o maior entre palavras × fator e caracteres ÷ 3), nem o `num_ctx` de nenhuma tarefa. Resolve a Lacuna 1 deste relatório no que diz respeito ao fator; o corte do P-033 passa a agir em tokens reais perto de `0,73 × num_ctx`. Continua sem medição no `qwen3:4b` do `air16` (pendência de máquina). Nenhuma linha anterior deste relatório foi reescrita.
