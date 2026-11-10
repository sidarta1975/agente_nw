# Brief 081 — O que o usuário escreve chega inteiro ao modelo

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Conjunto:** auditoria do texto por inteiro (080 a 083)
**Arquivos-alvo:** `agente_nw/nucleo/historico.py`, `agente_nw/nucleo/redacao.py` (`_notas`, `_moldes`), `agente_nw/nucleo/database/queries/consulta_contato.py`, `agente_nw/nucleo/database/queries/nota_contato.py` (só se o corte estiver ali), `agente_nw/nucleo/modelos/pedido.py` (validador de `evitar`), `agente_nw/nucleo/relevancia/candidatos.py` (`termo_evitado`), `config/limiares.yaml` (só chaves que ficarem sem uso), `tests/test_texto_do_usuario_inteiro.py` (novo), mais o relatório, o manifesto e o PLAN
**Seções a ler:** relatório 079, pontos P-028, P-029, P-030, P-034 e P-039; AGENTS §4 (a redação nunca afirma o que a pessoa não disse); no PLAN, o que trata de `cortar_por_tamanho` e do brief 050
**Modelo:** Sonnet
**Esforço:** médio
**Teste de aceite:** `tests/test_texto_do_usuario_inteiro.py`
**Depende de:** brief 079 executado. Não depende dos outros da série.
**Ordem em série:** livre
**Data:** 2026-11-08

---

## 1. Objetivo em uma frase

Nada que Sidarta escreve (comentário sobre a mensagem, nota sobre o contato, comentário do molde, lista de coisas a evitar) chega cortado ao modelo ou é ignorado na conferência.

## 2. Decisões (de Sidarta, já tomadas)

**2.1.** O comentário do usuário no histórico (hoje 300 caracteres), a nota do contato (hoje 400) e o comentário do molde (hoje 300) entram **inteiros**. *Razão: são a correção que ele faz do que o programa entendeu errado; cortá-la derruba o canal de correção do brief 050.*

**2.2.** O corte da **mensagem já entregue** em 100 caracteres no histórico **fica** (para não repetir, o começo basta). O limite de 5 notas e de 2 moldes também fica. Só o corte de **caracteres** do texto do usuário sai.

**2.3.** A lista `evitar` perde o teto de 5 itens no contrato (`PedidoExtraido`). `interessa` (5), `sobre_o_usuario` (5) e `termos_busca` (6) **não mudam** (o teto de `termos_busca` é custo de rede, aprovado como parte do P-005). O filtro de assunto e a conferência da mensagem passam a receber a lista `evitar` inteira.

**2.4.** `cortar_por_tamanho` continua protegendo a nota (é o único bloco que ele nunca remove) e passa a **proteger também o comentário do usuário do histórico e o comentário do molde**: se for preciso sacrificar algo para caber, sacrifica-se outro bloco, nunca o texto do usuário. Se mesmo assim estourar, o texto do usuário **não** é cortado: o brief 082 (medida da janela) é quem avisa; aqui o executor só garante, em teste, que o texto do usuário não é cortado.

**2.5.** O P-039 (ponto de apoio com 5 interesses) não muda: o `interessa` já vem limitado a 5 pelo contrato; fica registrado no relatório como "inalterado, depende de decisão futura sobre `interessa`".

## 3. Escopo (arquivos)

| Arquivo | O que muda |
|---|---|
| `nucleo/historico.py` | O comentário do usuário entra inteiro; a mensagem continua em 100. |
| `nucleo/redacao.py` | `_notas` e `_moldes` sem corte de caracteres; constantes e chaves sem uso são removidas. |
| `nucleo/database/queries/consulta_contato.py` (linhas 54 e 123 segundo o relatório 079) e `nota_contato.py:49` | Onde o corte de caracteres estiver nas consultas, tirá-lo. O executor confere linha a linha; só toca o corte de texto do usuário. |
| `nucleo/prompts/redigir_ganchos.py` | `cortar_por_tamanho` protege também os dois comentários (2.4). |
| `nucleo/modelos/pedido.py`, `nucleo/relevancia/candidatos.py` | `evitar` sem teto. |
| `config/limiares.yaml` | Remover só chaves que ficarem órfãs (provar com busca). |
| `tests/test_texto_do_usuario_inteiro.py` | Novo. |

## 4. Testes

1. Comentário de 2.000 caracteres no histórico chega ao prompt idêntico (não só o início).
2. Nota de 1.500 caracteres chega inteira ao prompt de `redigir_ganchos`; comentário de molde de 1.000, idem.
3. Mensagem entregue de 500 caracteres chega com 100 (o que ficou).
4. `PedidoExtraido` com 8 termos em `evitar` mantém os 8; com 8 em `interessa` mantém 5.
5. Mensagem que menciona o **oitavo** termo de `evitar` é detectada por `termo_evitado`.
6. Com prompt grande o bastante para estourar o orçamento, `cortar_por_tamanho` sacrifica outros blocos e preserva nota e comentários do usuário byte a byte.

## 5. Fora de escopo

Medir se o prompt cabe na janela (brief 082). O corpo da notícia no cartão e na qualificação (série futura, sem número). O teto de 5 de `interessa`.

## 6. Passos de execução

1. Conferir "Depende de". 2. Escrever os testes (seção 4). 3. Implementar. 4. Relatório `doc_081_...`, `logs/commit_081.txt`, `logs/arquivos_081.txt`, PLAN. 5. `scripts/agente_entregar.sh 081`. 6. Três linhas finais. No relatório, uma tabela `Ponto do 079 | O que mudou | Teste`, e a atualização do estado dos pontos P-028, P-029, P-030 e P-034 no relatório 079 para `CORRIGIDO (brief 081)` (o verificador deve continuar devolvendo 0).

## 7. Critérios de aceite

1. `pytest tests/test_texto_do_usuario_inteiro.py -q` verde, saída colada.
2. `grep` mostrando que não restam `[:300]`, `[:400]` nem `_TRECHO_DA_NOTA` nos três pontos (saída colada).
3. Verificador do 079 devolve 0 depois da atualização do relatório.
4. Gate do `agente_entregar.sh` verde.
