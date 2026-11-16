# Brief 098 — O estimador de tokens passa a usar a medida real do modelo

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Conjunto:** correção do texto por inteiro (segunda rodada, 098 a 100)
**Arquivos-alvo:** `agente_nw/nucleo/estimativa_tokens.py`, os testes que dependem do valor antigo (`tests/test_janela_modelo.py`, `tests/test_redacao_prompt.py`, `tests/test_comentario_sob_orcamento.py`, `tests/test_whatsapp_no_prompt.py`, `tests/test_texto_integral.py`, `tests/test_cartao_corpo_inteiro.py` — só os que mudarem de número), `docs/docs/doc_082_*.md` (a medição, em uma seção nova no fim), `docs/EXCECOES_TEXTO_INTEGRAL.md` (só a linha do P-033: valor aprovado e condição), `tests/test_sem_corte_de_texto.py` e a tabela de cortes não analíticos do registro (só os trechos que este brief alterar), mais o relatório, o manifesto e o PLAN
**Seções a ler:** relatório do brief 082 inteiro (a medição de 2,0 tokens por palavra e a decisão 2.2); `agente_nw/nucleo/estimativa_tokens.py` inteiro; a linha do P-033 em `docs/EXCECOES_TEXTO_INTEGRAL.md`; brief 093 e seu relatório (a guarda do gate); AGENTS §4
**Modelo:** Sonnet
**Esforço:** médio
**Teste de aceite:** `tests/test_janela_modelo.py`
**Depende de:** briefs 082 e 093 executados (`badf676` e `58294ff`)
**Ordem em série:** livre; antes de 100
**Data:** 2026-11-16
**Relatório 079 (autorização de Sidarta, 2026-11-16):** este brief pode atualizar a seção 6 (tabela de certificação: linha nova para arquivo que ele criar, contagem de linhas dos que ele alterar) e o apêndice A (destino das ocorrências novas da varredura) do relatório 079, só para os arquivos que ele mesmo criar ou alterar, sem criar ponto novo.
**Guarda do 093 (autorização de Sidarta, 2026-11-16):** este brief pode atualizar as listas de `tests/test_sem_corte_de_texto.py` e a tabela de cortes não analíticos do registro para os trechos que ele mesmo criar ou alterar, sem aprovar exceção nova.

---

## 1. Objetivo em uma frase

O estimador que decide se o prompt cabe na janela passa a usar 2,0 tokens por palavra — o que o brief 082 mediu no modelo de desenvolvimento — em vez de 1,4, para que pedido grande falhe em voz alta em vez de ser cortado em silêncio.

## 2. Decisões (de Sidarta, 2026-11-16)

**2.1. O valor é 2,0 tokens por palavra, com margem.** O brief 082 mediu 2,0 no `qwen2.5:14b`; o código dizia 1,4, herdado de estimativa sem medição. Subir é conservador: superestimar o prompt faz o cliente recusar cedo (erro visível), subestimar faz o modelo cortar sem avisar — e é justamente isso que o conjunto 080–095 veio acabar.

**2.2. A margem continua sendo a regra do 082, decisão 2.2:** o estimador devolve o **maior** entre palavras × fator e caracteres ÷ 3. Só o fator muda. Nada de teto novo, nada de arredondamento novo.

**2.3. O `num_ctx` das tarefas não muda.** Quem decide janela é o `config/llm_routing.yaml`, que fica como está. Se com 2,0 alguma tarefa passar a recusar prompt que antes passava, isso é informação para Sidarta, e vai no relatório como número, não como ajuste de configuração.

**2.4. Os testes que mudarem de número são ajustados, não afrouxados.** Teste que fixava um tamanho porque o estimador dizia 1,4 ganha o número novo; nenhuma asserção deixa de existir, nenhum teste passa a aceitar corte. Se algum teste só passava por causa da subestimativa, isso é achado e vai no relatório.

**2.5. O registro de exceções acompanha.** A linha do P-033 em `docs/EXCECOES_TEXTO_INTEGRAL.md` foi aprovada com a condição de que o estimador seria conferido pelo brief 082. A conferência aconteceu: a linha passa a dizer o valor novo (2,0) e que a conferência foi feita em 2026-11-16, mantendo "Aprovado por Sidarta em 2026-11-08" para a aprovação original. Nenhuma exceção nova é aprovada.

## 3. Escopo (arquivos)

| Arquivo | O que muda |
|---|---|
| `nucleo/estimativa_tokens.py` | `_TOKENS_POR_PALAVRA` de 1.4 para 2.0, com o comentário dizendo de onde vem o número (medição do 082, no `qwen2.5:14b`) e que ele é conservador de propósito. |
| testes que dependem do valor | Só os números que mudam. |
| `docs/docs/doc_082_*.md` | Seção nova no fim: a medição e o que o brief 098 fez com ela. Nenhuma linha antiga é reescrita. |
| `docs/EXCECOES_TEXTO_INTEGRAL.md` | Só a linha do P-033 (2.5). |
| `tests/test_sem_corte_de_texto.py` e a tabela de cortes não analíticos | Só os trechos que este brief alterar. |

## 4. Testes

1. `estimar_tokens` de um texto conhecido devolve palavras × 2,0 quando esse é o maior dos dois caminhos.
2. Texto de palavras muito longas (poucas palavras, muitos caracteres) continua indo pelo caminho de caracteres ÷ 3: a margem não desapareceu.
3. Um prompt que antes era estimado abaixo do `num_ctx` e agora passa dele é **recusado em voz alta** pelo cliente (a mensagem do brief 082), e não cortado — com o erro conferido no teste.
4. A suíte inteira continua verde, e o relatório diz quais testes mudaram de número e por quê.

## 5. Fora de escopo

Mudar `num_ctx`, limiares ou qualquer teto de texto. Medir o `qwen3:4b` do `air16` (não há máquina de produção nesta sessão; fica registrado como pendência de medição). Aprovar exceção nova. Regravar vetor ou cartão.

## 6. Passos de execução

1. Conferir "Depende de". 2. Ler o relatório do 082 e anotar a medição. 3. Testes (seção 4). 4. Trocar o fator. 5. Rodar a suíte inteira e ajustar só os números que o estimador mudou, listando cada um no relatório. 6. Seção nova no relatório do 082, linha do P-033 no registro, listas da guarda se preciso. 7. Relatório `doc_098_...`, manifesto, PLAN; `scripts/agente_entregar.sh 098`. 8. Três linhas finais.

## 7. Critérios de aceite

1. `pytest tests/test_janela_modelo.py -q` verde, saída colada.
2. `grep -n "_TOKENS_POR_PALAVRA" agente_nw/nucleo/estimativa_tokens.py` mostra 2.0 (saída colada).
3. Gate verde, com o número de testes antes e depois.
4. Verificador do 079 devolve 0.
5. O relatório traz a tabela `Teste | número antes | número depois | por quê` de cada teste ajustado, e a lista das tarefas que passaram a recusar prompt que antes passava (ou "nenhuma", com a prova).
