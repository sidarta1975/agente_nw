# Relatório do brief 099 — A mensagem já entregue entra inteira no histórico

Data: 2026-11-16. Depende de 081 (`4f0dc51`) e 093 (`58294ff`): satisfeito (ambos no `git log`).

## O que mudou

- `agente_nw/nucleo/historico.py`: `mensagem[:100]` saiu de `_formatar_ganchos`; a mensagem entra inteira. Nenhum outro limite do histórico mudou (5 consultas, notas, moldes: brief 100).
- `tests/test_texto_do_usuario_inteiro.py`: o teste `test_mensagem_entregue_de_500_caracteres_chega_com_100` **mudou de intenção por decisão de Sidarta (2026-11-16, brief 099 item 2.1)** e virou `..._chega_inteira`. Testes novos: mensagem de 3.000 caracteres com o último presente; marcador no fim da mensagem aparece no prompt de `redigir_ganchos` (ponta a ponta, via `construir_prompt`); prompt estourando o orçamento (1.500, 200 e 1 token) não corta a mensagem e sacrifica outros blocos (fatos e WhatsApp saem; nota e comentário ficam); comentário do usuário continua inteiro ao lado da mensagem (regressão do 081).
- `tests/test_sem_corte_de_texto.py`: saiu a chave de violação pendente da fatia `mensagem[:100]` (o trecho deixou de existir). A chave de `historico_recente_para_prompt` (limite de 5 consultas) continua, destino do brief 100.
- `docs/docs/doc_079_...md`: P-028 em `CORRIGIDO (brief 099)` com as duas correções (081 e 099); seção 6 (linhas dos dois testes e descrição do `historico.py`); apêndice A (citações deslocadas renumeradas, grupo do brief 099, sem ponto novo).

## Crescimento do histórico (critério 5)

Caso real da cópia de desenvolvimento `dados/agente.testeedy.db` (15/10), copiada para `/tmp/b099/copia.db` e aberta em `mode=ro`; o banco real não foi aberto. 17 mensagens entregues, a maior com 311 caracteres, com `estimar_tokens` (2,0 por palavra, brief 098):

| | tokens estimados |
|---|---|
| mensagens cortadas em 100 caracteres (antes) | 662 |
| mensagens inteiras (agora) | 1.282 |
| crescimento | +620 em 17 mensagens, cerca de +36 por mensagem |

Cada consulta do histórico traz poucas mensagens, então o aumento por prompt fica na casa de algumas dezenas a poucas centenas de tokens. Mensagens reais maiores (a regra do produto aceita textos longos) crescem na mesma proporção; este número não mostra estouro de janela, mas a amostra tem mensagens curtas (máximo 311 caracteres). Se estourar com frequência em uso real, é número para Sidarta (decisão 2.4 do brief).

## Saídas coladas

```
$ .venv/bin/pytest tests/test_texto_do_usuario_inteiro.py -q
..........                                                               [100%]
10 passed in 0.74s

$ .venv/bin/pytest tests/test_texto_do_usuario_inteiro.py tests/test_sem_corte_de_texto.py -q
............................................                             [100%]
44 passed in 0.89s

$ grep -n "\[:100\]" agente_nw/nucleo/historico.py
(sem resultado; grep rc=1)

$ .venv/bin/python scripts/verificar_auditoria_texto.py
(rc=0; antes do ajuste do relatório 079: 81 inconsistências, todas linhas deslocadas dos dois testes; depois: 0)
```

O gate completo (ruff, mypy, pytest) roda dentro de `scripts/agente_entregar.sh 099`; o commit só sai com ele verde.

## RELATÓRIO FINAL
- Brief executado: 099
- Arquivos criados: `docs/docs/doc_099_mensagem_anterior_inteira_2026-11-16.md`
- Arquivos alterados: `agente_nw/nucleo/historico.py` (tira `[:100]` da mensagem); `tests/test_texto_do_usuario_inteiro.py` (teste antigo muda de intenção, quatro testes novos); `tests/test_sem_corte_de_texto.py` (sai a chave da fatia que não existe mais); `docs/docs/doc_079_auditoria_texto_por_inteiro_2026-11-08.md` (P-028, seção 6, apêndice A); `docs/PLAN_agente_nw.md`
- Arquivos preservados literalmente na área afetada: `nucleo/prompts/redigir_ganchos.py` (`cortar_por_tamanho`), `nucleo/redacao.py`, `nucleo/estimativa_tokens.py`, `num_ctx`, `docs/EXCECOES_TEXTO_INTEGRAL.md`
- Script de verificação: gate dentro do `scripts/agente_entregar.sh 099`; testes do brief e verificador do 079 colados acima
- Comandos executados: os da seção "Saídas coladas" e a leitura da cópia em `/tmp/b099`
- Manifesto do commit: `logs/commit_099.txt` e `logs/arquivos_099.txt` (ver o commit)
- Pendências e decisões que ficaram abertas: ver Lacunas
- Resumo, Doing, Backlog e Done do `docs/PLAN_agente_nw.md` atualizados: sim

**Algum texto é analisado só em parte?** A mensagem entregue deixou de ser: entra inteira (testes de 500 e 3.000 caracteres, e marcador no fim visto no prompt de `redigir_ganchos`). Continua em parte, com decisão já registrada, o número de consultas do histórico (5 lidas, 3 usadas na redação; P-028, brief 100), e o `cortar_por_tamanho` ainda tira a consulta mais antiga inteira (mensagem dela inclusa) quando o prompt estoura; mantém o comentário do usuário (brief 081). Nenhum caractere é cortado.

## Lacunas

| # | Lacuna | Destino | Impacto |
|---|---|---|---|
| 1 | A amostra real tem mensagens de até 311 caracteres; com mensagens longas o histórico pode estourar a janela com mais frequência, e isso só se vê em uso real | nenhum | nice |
