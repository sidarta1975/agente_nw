# DOC 098: o estimador de tokens passa a usar a medida real do modelo

**Brief:** `docs/briefs/brief_098_estimador_de_tokens_medido_2026-11-16.md`

## O que foi feito

`_TOKENS_POR_PALAVRA` em `agente_nw/nucleo/estimativa_tokens.py` passou de 1.4 para 2.0 (medição do brief 082: razão real 2,001 no `qwen2.5:14b`). A margem da decisão 2.2 (o maior entre palavras × fator e caracteres ÷ 3) ficou como estava. Nenhum `num_ctx`, limiar ou teto mudou.

```
$ grep -n "_TOKENS_POR_PALAVRA" agente_nw/nucleo/estimativa_tokens.py
15:_TOKENS_POR_PALAVRA = 2.0
21:    return int(len(texto.split()) * _TOKENS_POR_PALAVRA)

$ .venv/bin/pytest tests/test_janela_modelo.py -q
25 passed

$ .venv/bin/pytest -q          # antes do brief: 1346 passed; depois:
1347 passed, 5 deselected

$ .venv/bin/ruff check .   -> All checks passed!
$ .venv/bin/mypy agente_nw -> Success: no issues found in 128 source files
$ .venv/bin/python scripts/verificar_auditoria_texto.py   -> rc=0
340 arquivos, 284 certificados, 49 cortam, 7 não analíticos, 0 não conferidos, 6 ponto(s) aguardando decisão de Sidarta
```

Testes do brief (seção 4): (1) e (2) em `test_estimativa_e_o_maior_entre_palavras_e_caracteres` (100 palavras = 200; "paralelepípedo " × 10 continua em caracteres ÷ 3); (3) `test_prompt_que_so_passa_do_num_ctx_com_2_0_e_recusado_em_voz_alta` (novo: 0,6 × `num_ctx` palavras, estimado 1,2 × `num_ctx`; `FalhaJanela` com motivo `prompt_estimado_acima_da_janela`, servidor com 0 chamadas, uma linha `"janela": true` no log); (4) suíte inteira verde.

## Testes ajustados

| Teste | número antes | número depois | por quê |
|---|---|---|---|
| `test_janela_modelo.py::test_estimativa_e_o_maior_entre_palavras_e_caracteres` | 140 | 200 | 100 palavras × fator |
| `test_redacao_prompt.py::test_estimativa_e_palavras_vezes_um_virgula_quatro` (renomeado `..._vezes_dois`) | 140 | 200 | idem; a asserção continua |
| `test_texto_integral.py::test_reconstruir_as_partes_reproduz_o_original_byte_a_byte` (parâmetro `orcamento`) | 1 | 2 | uma palavra de um caractere agora estima 2 tokens; com orçamento 1 nenhuma parte caberia, e a propriedade (cada parte `<=` orçamento) deixa de ser satisfazível. O orçamento mínimo viável passou de 1 para 2; os casos 40, 700 e 3000 e todas as asserções ficaram |

Nenhum teste só passava por causa da subestimativa; nenhuma asserção deixou de existir nem passou a aceitar corte.

## Tarefas que passaram a recusar prompt que antes passava

Nenhuma encontrada. Prova: a suíte inteira (1347 testes) passa sem mudar nenhum `num_ctx` ou fixture de tarefa, e os únicos números alterados são os três acima. O efeito do 2,0 é o previsto na decisão 2.3: o `cortar_por_tamanho` (orçamento `0,73 × num_ctx`) passa a sacrificar blocos mais cedo, em tokens reais, e a redação deixa de ser recusada onde antes o prompt "cabia" só no papel. Não há prompt real de produção medido aqui; se uma tarefa recusar na prática, o log `chamadas_llm.jsonl` mostra `"janela": true` com `tokens_estimados`.

## Registro, relatórios 079 e 082, guarda

- P-033 em `docs/EXCECOES_TEXTO_INTEGRAL.md`: valor 2,0 e conferência de 2026-11-16; "Aprovado por Sidarta em 2026-11-08" mantido. Nenhuma exceção nova.
- Relatório 082: adendo no fim, nenhuma linha antiga reescrita.
- Relatório 079: seção 6 (27→28 e 396→415 linhas) e apêndice A (renumeração +19 em `tests/test_janela_modelo.py` e grupo "Brief 098", 6 ocorrências descartadas), sem ponto novo.
- `tests/test_sem_corte_de_texto.py` e a tabela de cortes não analíticos: nada a alterar; o teste passou sem edição.

## RELATÓRIO FINAL
- Brief executado: 098.
- Arquivos criados: este relatório.
- Arquivos alterados: `agente_nw/nucleo/estimativa_tokens.py` (fator 2,0 e comentário da origem); `tests/test_janela_modelo.py` (140→200 e teste novo); `tests/test_redacao_prompt.py` (140→200); `tests/test_texto_integral.py` (orçamento 1→2); `docs/EXCECOES_TEXTO_INTEGRAL.md` (linha do P-033); `docs/docs/doc_082_*.md` (adendo); `docs/docs/doc_079_*.md` (seção 6 e apêndice A); `docs/PLAN_agente_nw.md`.
- Arquivos preservados literalmente na área afetada: `config/llm_routing.yaml` e todo `num_ctx`; `agente_nw/nucleo/llm.py`; `tests/test_sem_corte_de_texto.py`.
- Script de verificação: gate rodado pelo `scripts/agente_entregar.sh` (saída abaixo, na seção da entrega).
- Comandos executados: os acima; nenhum tocou o banco real nem o Ollama.
- Manifesto: `logs/commit_098.txt` e `logs/arquivos_098.txt`.
- Pendências e decisões que ficaram abertas: ver Lacunas.
- Resumo, Doing, Backlog e Done do `docs/PLAN_agente_nw.md` atualizados: sim.

**Algum texto é analisado só em parte?** Não. O brief só troca um fator numérico do estimador; nenhum texto passa a ser fatiado, e o corte do P-033 já estava aprovado. Prova: `verificar_auditoria_texto.py` com rc=0 e `tests/test_sem_corte_de_texto.py` verde sem edição.

## Lacunas

| # | Lacuna | Destino | Impacto |
|---|---|---|---|
| 1 | O 2,0 não foi medido no `qwen3:4b` do `air16` (sem a máquina de produção nesta sessão); se a razão dele for menor, o estimador recusa e corta cedo demais, nunca tarde | pendência | nice |
