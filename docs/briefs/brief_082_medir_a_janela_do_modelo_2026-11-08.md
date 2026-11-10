# Brief 082 — Medir a janela do modelo: prompt, embedding e resposta nunca cortados em silêncio

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Conjunto:** auditoria do texto por inteiro (080 a 083)
**Arquivos-alvo:** `agente_nw/nucleo/llm.py` (a base comum `_ClienteLLMBase`, `ClienteOllama._chamar` e `embeddar`, e os três clientes de API), um módulo novo pequeno para o estimador de tokens se o executor achar melhor tirá-lo de `redigir_ganchos.py`, `agente_nw/nucleo/prompts/redigir_ganchos.py` (só para reaproveitar/mover o estimador), os pontos de chamada que precisarem tratar o novo erro, `tests/test_janela_modelo.py` (novo), mais o relatório, o manifesto e o PLAN
**Seções a ler:** relatório 079, pontos P-019, P-033, P-040, P-041, P-042 e as seções 5 e 7; `docs/PLAN_agente_nw.md` armadilha 1; `nucleo/llm.py` inteiro; `config/llm_routing.yaml`; brief 077 (o padrão de aviso em `chamadas_llm.jsonl`)
**Modelo:** Opus — toca o cliente usado pelas 15 tarefas de LLM e por todos os embeddings; um engano trava o produto inteiro
**Esforço:** alto
**Teste de aceite:** `tests/test_janela_modelo.py`
**Depende de:** brief 079 executado e brief 087 executado (a fila de revisão precisa ter quem a resolva antes de receber mais itens). Deve ser executado **antes** de qualquer brief que suba tetos de texto (briefs 088 a 091).
**Ordem em série:** depois de 087; antes de 088, 089, 090 e 091
**Data:** 2026-11-08 (v2: dependência do 087 e fronteira com o 088)

---

## 1. Objetivo em uma frase

Quando um prompt não cabe na janela, quando o texto de um embedding passa do limite do modelo, ou quando a resposta vem cortada, o projeto **sabe e não grava como se estivesse bom**: registra, recusa o resultado e manda o item para revisão.

## 2. Decisões (de Sidarta, já tomadas)

**2.1. A medida autoritativa é a que o próprio modelo devolve.** O Ollama devolve `prompt_eval_count` (tokens do prompt realmente lidos) e `done_reason`; a Anthropic, `stop_reason`; o Gemini, `finishReason`; a OpenAI, `finish_reason`. O executor confere no código e nas respostas reais dos clientes quais campos existem e usa-os. Se `prompt_eval_count` for igual ou maior que o `num_ctx` da tarefa, o prompt foi cortado. Se a resposta parou por tamanho (`length`, `max_tokens`, `MAX_TOKENS`), ela veio cortada.

**2.2. Além da medida depois da chamada, uma estimativa antes dela**, para não gastar uma chamada que já se sabe perdida: o estimador de `redigir_ganchos` (palavras × 1,4) vira função compartilhada. Como o 1,4 nunca foi conferido contra o tokenizador real, a estimativa usa o maior entre `palavras × 1,4` e `caracteres ÷ 3`; ela só **bloqueia** quando passa de `num_ctx`; a decisão final é sempre a medida de 2.1 quando existir.

**2.3. O que fazer quando estoura:** (a) registrar uma linha em `chamadas_llm.jsonl` (mesmo padrão do brief 077: `"janela": true`, tarefa, modelo, tokens medidos, `num_ctx`, motivo); (b) **não usar** a resposta; (c) levantar um erro próprio de janela, subclasse do erro que os chamadores já tratam, para o item cair no caminho que hoje trata falha de LLM — e, onde existir `fila_revisao`, ir para lá. O executor lê como cada uma das 15 tarefas trata falha e não muda o desenho delas; onde nenhuma tarefa tem fila, o erro aparece ao usuário como já aparece qualquer outra falha. Nunca se responde "com o que coube". Este brief **só recusa**: dividir o texto em partes que cobrem tudo e consolidar o resultado é o brief 088, que captura o erro de janela criado aqui e o trata dividindo. Até o 088, o item recusado fica na fila de revisão do brief 087.

**2.4. Embeddings:** mesma regra, com o limite do `bge-m3` (8.192 tokens). Se a API de embeddings devolver contagem, usar; senão, estimativa conservadora (2.2) e registro.

**2.5. Resposta cortada que ainda parece válida** (lista com menos itens, cartão de duas linhas) passa a ser tratada como falha: o item não é gravado como bom. O brief não muda `num_predict` de nenhuma tarefa.

**2.6. A conferência do 1,4 do P-033:** se o Ollama estiver acessível no ambiente do executor, rodar uma vez um prompt real de redação, comparar `prompt_eval_count` com a estimativa e colar no relatório; se não estiver, declarar "não conferido" nas Lacunas. Nenhum teste automatizado chama o Ollama real.

## 3. Escopo (arquivos)

| Arquivo | Criar / alterar | O que muda |
|---|---|---|
| `nucleo/llm.py` | alterar | Conferência depois de cada chamada de geração e de embedding (2.1, 2.4); estimativa antes (2.2); erro de janela (2.3); registro em `chamadas_llm.jsonl`; tratamento de `done_reason`/`stop_reason`/`finish_reason` nos quatro clientes. |
| módulo do estimador | criar ou mover | Uma só função, usada pelo cliente e por `cortar_por_tamanho`. |
| `nucleo/prompts/redigir_ganchos.py` | alterar | Usa o estimador compartilhado; comportamento de `cortar_por_tamanho` idêntico (testes existentes verdes). |
| pontos de chamada | alterar só se o erro novo não for tratado pelo caminho existente | Mínimo necessário. |
| `tests/test_janela_modelo.py` | criar | Seção 4. |

## 4. Testes (cliente falso, sem Ollama nem rede)

1. Resposta falsa com `prompt_eval_count` igual a `num_ctx` → erro de janela, linha no log, resultado não devolvido.
2. `prompt_eval_count` menor que `num_ctx` → resultado devolvido normalmente, nada no log.
3. Prompt cuja estimativa passa do `num_ctx` → erro de janela **antes** de chamar o servidor (o cliente falso prova que não foi chamado).
4. `done_reason == "length"` com JSON válido porém incompleto → falha, não resultado.
5. O mesmo para `stop_reason == "max_tokens"` (Anthropic), `MAX_TOKENS` (Gemini) e `length` (OpenAI).
6. Embedding com texto acima do limite → erro de janela e registro; abaixo → vetor normal.
7. Tarefa com fila de revisão: o item vai para `fila_revisao` no erro de janela, com banco isolado em `tmp_path`.
8. `cortar_por_tamanho`: testes existentes continuam passando com o estimador compartilhado.

## 5. Fora de escopo

Dividir o texto em partes e consolidar (brief 088). Subir tetos de texto da notícia, do cartão ou do vetor (briefs 089 e 090). Mudar `num_ctx` ou `num_predict` de qualquer tarefa. Retentativa automática com janela maior.

## 6. Passos de execução

1. Conferir "Depende de". 2. Ler `llm.py` inteiro e a lista das 15 tarefas em `config/llm_routing.yaml`; escrever a tabela `Tarefa | num_ctx air16 | num_ctx pro48 | como trata falha hoje` no relatório. 3. Testes (seção 4). 4. Implementar. 5. 2.6 (conferência do 1,4). 6. Relatório `doc_082_...`, manifesto, PLAN; atualizar no relatório 079 os pontos P-019, P-040, P-041 e P-042 para `CORRIGIDO (brief 082)`; P-033 permanece aprovado com a conferência do 1,4 registrada. 7. `scripts/agente_entregar.sh 082`. 8. Três linhas finais.

## 7. Critérios de aceite

1. `pytest tests/test_janela_modelo.py -q` verde, saída colada.
2. Suíte completa verde (pelo gate), saída colada.
3. Tabela das 15 tarefas no relatório, sem célula em branco.
4. Verificador do 079 devolve 0.
5. Nenhum `num_ctx` nem `num_predict` mudou (`git diff` de `config/` vazio).
