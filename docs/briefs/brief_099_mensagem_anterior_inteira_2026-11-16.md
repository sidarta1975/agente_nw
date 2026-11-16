# Brief 099 — A mensagem já entregue entra inteira no histórico

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Conjunto:** correção do texto por inteiro (segunda rodada, 098 a 100)
**Arquivos-alvo:** `agente_nw/nucleo/historico.py` (o corte de 100 caracteres da mensagem em `_formatar_ganchos`), `tests/test_texto_do_usuario_inteiro.py` (teste novo; o teste que fixa os 100 caracteres é o que muda de intenção), `docs/docs/doc_079_auditoria_texto_por_inteiro_2026-11-08.md` (o ponto P-028: estado e texto), `tests/test_sem_corte_de_texto.py` e a tabela de cortes não analíticos do registro (só os trechos que este brief alterar), mais o relatório, o manifesto e o PLAN
**Seções a ler:** relatório 079, ponto P-028; relatório do brief 081 (que tirou os outros três cortes do mesmo lugar) e o seu item 2.2, que mantinha este corte; `agente_nw/nucleo/historico.py` inteiro; `agente_nw/nucleo/prompts/redigir_ganchos.py` (`cortar_por_tamanho`, para saber o que acontece com o prompt maior); brief 093 e seu relatório; AGENTS §4
**Modelo:** Sonnet
**Esforço:** médio
**Teste de aceite:** `tests/test_texto_do_usuario_inteiro.py`
**Depende de:** briefs 081 e 093 executados (`4f0dc51` e `58294ff`)
**Ordem em série:** livre; antes de 100
**Data:** 2026-11-16
**Relatório 079 (autorização de Sidarta, 2026-11-16):** este brief pode atualizar a seção 6 (tabela de certificação: linha nova para arquivo que ele criar, contagem de linhas dos que ele alterar) e o apêndice A (destino das ocorrências novas da varredura) do relatório 079, só para os arquivos que ele mesmo criar ou alterar, sem criar ponto novo.
**Guarda do 093 (autorização de Sidarta, 2026-11-16):** este brief pode atualizar as listas de `tests/test_sem_corte_de_texto.py` e a tabela de cortes não analíticos do registro para os trechos que ele mesmo criar ou alterar, sem aprovar exceção nova.

---

## 1. Objetivo em uma frase

A mensagem que já foi entregue ao contato entra **inteira** no histórico que vai ao modelo, e não só os seus 100 primeiros caracteres.

## 2. Decisões (de Sidarta, 2026-11-16)

**2.1. O corte de 100 caracteres sai.** O brief 081 o havia mantido (item 2.2: "para não repetir, o começo basta"). Sidarta decidiu o contrário em 2026-11-16, ao recusar aprová-lo como exceção: a mensagem entra inteira. *Razão: é o texto que o próprio produto escreveu e entregou; o modelo precisa dele todo para não repetir ideia, estrutura nem frase, não só a abertura.*

**2.2. Nenhum outro limite do histórico muda neste brief.** O número de consultas lidas e usadas, as notas e os moldes seguem como estão (o brief 100 os registra como exceções aprovadas). Só o corte de caracteres da mensagem sai.

**2.3. O P-028 passa a `CORRIGIDO (brief 099)`.** O brief 081 já havia corrigido a parte do comentário do usuário; esta era a parte que restava no mesmo ponto. O texto do ponto diz as duas correções, com os dois números de brief.

**2.4. Prompt maior é problema do estimador, não deste brief.** Com a mensagem inteira, o histórico cresce. Quem avisa quando não cabe é o cliente do brief 082, com o estimador do brief 098; `cortar_por_tamanho` continua sacrificando outros blocos antes de qualquer texto do usuário (brief 081, decisão 2.4) e **nunca** corta caracteres. Se o relatório mostrar que o histórico passou a estourar a janela com frequência, isso é número para Sidarta, não ajuste do executor.

## 3. Escopo (arquivos)

| Arquivo | O que muda |
|---|---|
| `nucleo/historico.py` | `mensagem[:100]` sai; a mensagem entra inteira em `_formatar_ganchos`. |
| `tests/test_texto_do_usuario_inteiro.py` | O teste `test_mensagem_entregue_de_500_caracteres_chega_com_100` passa a exigir a mensagem inteira (muda de intenção por decisão de Sidarta, e o relatório diz isso); teste novo com mensagem de 3.000 caracteres. |
| `docs/docs/doc_079_...md` | P-028: estado `CORRIGIDO (brief 099)` e o texto com as duas correções. |
| `tests/test_sem_corte_de_texto.py` e a tabela de cortes não analíticos | Só os trechos que este brief alterar. |

## 4. Testes

1. Mensagem de 3.000 caracteres no histórico chega ao prompt inteira, com o último caractere presente.
2. O marcador posto no fim da mensagem aparece no prompt de `redigir_ganchos` (prova de ponta a ponta, não só da função).
3. Com o prompt grande o bastante para estourar o orçamento, a mensagem **não** é cortada: o que sai são outros blocos (nota e comentários do usuário continuam protegidos, como no brief 081).
4. O comentário do usuário continua inteiro (regressão do 081).

## 5. Fora de escopo

Mudar número de consultas, notas, moldes ou qualquer outro limite do histórico. Mudar `num_ctx` ou o estimador (brief 098). Aprovar exceção. Regravar vetor ou cartão.

## 6. Passos de execução

1. Conferir "Depende de". 2. Ler o P-028 e o relatório do 081. 3. Testes (seção 4), inclusive a mudança de intenção do teste antigo. 4. Tirar o corte. 5. P-028 no relatório 079; listas da guarda se preciso. 6. Relatório `doc_099_...`, manifesto, PLAN; `scripts/agente_entregar.sh 099`. 7. Três linhas finais.

## 7. Critérios de aceite

1. `pytest tests/test_texto_do_usuario_inteiro.py -q` verde, saída colada.
2. `grep -n "\[:100\]" agente_nw/nucleo/historico.py` sem resultado (saída colada).
3. Gate verde.
4. Verificador do 079 devolve 0, com o P-028 em `CORRIGIDO (brief 099)`.
5. O relatório diz, com número, quanto o histórico cresceu em tokens estimados num caso real do banco de exemplo (ou, se não houver caso, em texto sintético declarado como tal).
