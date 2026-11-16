# DOC 100: as exceções aprovadas em 2026-11-16 e a regra de manutenção da guarda

**Brief:** `docs/briefs/brief_100_excecoes_aprovadas_e_regra_da_guarda_2026-11-16.md`
**Data:** 2026-11-16
**Depende de:** 093 (`922ce24`), 094 (`3554499`), 098 (`8b0dae8`) e 099 (`9481f90`), conferidos no `git log` e em `docs/docs/doc_09{3,4,8,9}_*` antes de começar. O passo 1 do brief (2.3) também foi conferido:

```
$ grep -n "\[:100\]" agente_nw/nucleo/historico.py; echo "grep=$?"
grep=1
```

O corte de 100 caracteres não está mais no código: o brief 099 foi entregue e este brief seguiu.

## 1. O que foi aprovado e onde ficou

Código de produção não mudou. O registro ganhou as aprovações da tabela 2.2 do brief, só elas, e cada uma teve o valor conferido no código antes de ser gravada.

| O que foi aprovado | Ponto do 079 | Arquivo:linha do valor | Condição |
|---|---|---|---|
| Página de rede social lida até um teto de caracteres (200.000) | P-013 (lacuna [093-1]) | `config/limiares.yaml:59` (`extensao.maximo_caracteres_pagina: 200000`); padrão `agente_nw/nucleo/modelos/configuracao.py:244`; corte em `extensao/conteudo.js:203` e `agente_nw/coleta/capturas/extensao_backend.py:142`; aviso em `extensao_backend.py:138-141` | Vale enquanto o aviso do corte continuar visível para o usuário; se o aviso aparecer com frequência, a exceção é reavaliada. |
| Assuntos por rodada (40) | P-009, segunda linha (lacuna [093-2]) | `config/limiares.yaml:10` (`qualificacao.teto_por_dia: 40`); passado em `agente_nw/nucleo/consulta.py:221` e `agente_nw/cli.py:723`; aplicado em `agente_nw/nucleo/database/queries/assuntos.py:179`; `LIMIT ?` do cartão em `assuntos.py:271` | Vale porque é o grupo de candidatos do gate, não texto cortado: nenhum texto de item deixa de ser lido por causa dele. |
| Histórico da redação (5 consultas lidas, 3 usadas) | P-028 (lacuna [093-3]) | `agente_nw/nucleo/historico.py:10` (`LIMITE_PADRAO = 5`, padrão em `:95`); `agente_nw/nucleo/redacao.py:43` (`_CONSULTAS_NO_HISTORICO = 3`, aplicado em `:156` e `:158`) | Vale enquanto o corte for de quantas conversas entram, nunca de caracteres do que o usuário escreveu. |
| Notas na redação (5) | P-029 (lacuna [093-4]) | `agente_nw/nucleo/redacao.py:44` (`_NOTAS_NO_PROMPT = 5`, aplicado em `:176`) | Teto de itens, não de caracteres. |
| Moldes na redação (2) | P-030 (lacuna [093-4]) | `config/limiares.yaml:76` (`moldes.maximo: 2`); repasse em `agente_nw/nucleo/orquestracao.py:213`; padrão em `agente_nw/nucleo/redacao.py:222` e `:289`; aplicado em `agente_nw/nucleo/database/queries/consulta_contato.py:123` | Teto de itens, não de caracteres. |
| Termos de busca (6) | P-034 (lacuna [093-5]) | `agente_nw/nucleo/modelos/pedido.py:19` (`_MAXIMO_TERMOS_BUSCA = 6`, aplicado em `:107`) | Vale como custo de rede, o mesmo motivo do P-005 (aprovado em 2026-11-08). |
| Interesses no ponto de apoio da consulta (5) | P-039 | `agente_nw/nucleo/relevancia/cruzamento.py:49` (`_MAXIMO_INTERESSA_NO_APOIO = 5`, aplicado em `:407`) | Vale enquanto o contrato do pedido mantiver `interessa` em 5 (`agente_nw/nucleo/modelos/pedido.py:18`); se esse número mudar, a exceção cai. |

Os cinco primeiros têm ponto no relatório 079 (P-013, P-009, P-028, P-029/P-030, P-034), e o sexto é o P-039: nenhuma aprovação entrou pela descrição, nenhum identificador foi inventado. Os identificadores novos do relatório 094 (P-046 a P-064) não foram tocados.

**O corte de 100 caracteres da mensagem anterior NÃO foi aprovado.** Sidarta o recusou, e o brief 099 o removeu de `agente_nw/nucleo/historico.py` (conferido acima). A linha do P-028 no registro diz isso em "Não aprovado".

**Sete linhas, não seis.** A linha "Notas e moldes" da tabela 2.2 cobre dois pontos do 079 (P-029, notas; P-030, moldes). A guarda (`linhas_de_excecao`, em `tests/test_sem_corte_de_texto.py`) acha a linha pelo identificador da primeira célula, um ponto por linha. Uma linha só, com "P-029 e P-030", deixaria um dos dois pontos sem linha para a guarda. Por isso a aprovação foi gravada em duas linhas, com o mesmo valor de decisão e a mesma condição. Nada além da tabela 2.2 foi aprovado.

**O que ficou de fora de propósito**, porque não estava na tabela 2.2:

- `conector.candidatos_por_contato` (10) continua não aprovado (primeira linha do P-009, intocada).
- `interessa` e `sobre_o_usuario` em 5 no contrato do pedido (P-034, `pedido.py:91`) continuam sem aprovação: a decisão é a [091-1]. A aprovação do P-039 *supõe* o 5 do contrato, mas não o aprova.
- O arranque a frio dos moldes, que oferece no máximo 1 molde `entregue` quando não há nenhum `usado` (`consulta_contato.py:124`, `candidatos[:1]`, brief 065), não é o "2 moldes" aprovado. Ficou como violação pendente com destino na lacuna 1 deste relatório.

**P-018:** a decisão do item 2.5 ficou registrada no texto do ponto, sem mudar o estado (`EXCEÇÃO APROVADA` desde 2026-11-08): a descrição continua em 2 a 5 frases e, quando houver texto legível na imagem, ele é transcrito inteiro em campo separado. A implementação é brief do segundo conjunto. A linha do P-018 no registro não mudou.

## 2. Arquivos

1. **`docs/EXCECOES_TEXTO_INTEGRAL.md`:** sete linhas novas no fim da tabela de exceções aprovadas, nas sete colunas do brief 080 (item 2.4), cada uma com "Aprovado por Sidarta em 2026-11-16". A linha do P-033 e as outras 18 de 2026-11-08 não mudaram. A tabela "Cortes não analíticos" não mudou: nenhum trecho deste brief é não analítico.
2. **Relatório 079:**
   - P-013, P-028, P-029, P-030 e P-034 passaram de `CORRIGIDO (brief NNN)` para `EXCEÇÃO APROVADA`. P-039 passou de `AGUARDANDO DECISÃO DE SIDARTA` para `EXCEÇÃO APROVADA`.
   - A linha de decisão de cada um começa com `Decisão de Sidarta: aprovar exceção (2026-11-16), alcance conforme o registro` e guarda, depois, a correção anterior ("Antes, corrigir (brief 081)…"). Assim o histórico não se perde.
   - No P-009, a aprovação de 2026-11-16 foi somada à de 2026-11-08. No P-018, a decisão de 2.5.
   - Os números da seção 1 e da abertura da seção 3 agora são 25 aprovados, 15 corrigidos e 5 aguardando; antes diziam "26 aguardam", texto parado desde o brief 080.
   - Seção 6: a contagem de linhas do `tests/test_sem_corte_de_texto.py` foi de 1153 para 1144.
   - Apêndice A: as 154 linhas do grupo "Brief 093" foram renumeradas pela posição nova no arquivo; continuam 154, com o mesmo destino e o mesmo motivo.
3. **`tests/test_sem_corte_de_texto.py`:** os trechos dos pontos aprovados saíram de `VIOLACOES_PENDENTES` e entraram em `EXCECOES_APROVADAS` com o ponto:
   - `extensao_backend.py` (3) e `modelos/configuracao.py`: P-013;
   - `cli.py`, `consulta.py` e `queries/assuntos.py` (2): P-009;
   - `historico.py` e `redacao.py` (2): P-028;
   - `redacao.py`: P-029;
   - `queries/consulta_contato.py` `usados[:maximo]`: P-030;
   - `orquestracao.py` e as duas assinaturas de `redacao.py`, que decidem as 10 trocas e os 2 moldes: `P-023 P-030`;
   - `modelos/pedido.py` termos: P-034;
   - `cruzamento.py`: P-039.

   Ficaram pendentes `candidatos[:1]` (P-030, destino [100-1]) e o `interessa` do contrato (P-034, [091-1]). Os comentários da lista acompanham. A lógica do teste não mudou.
4. **`AGENTS_agente_nw.md` §4:** a frase do item 2.4, nada mais (diff na seção 5).
5. **`docs/PLAN_agente_nw.md`:**
   - Resumo e Done atualizados; Doing segue "(nenhum)".
   - As decisões [093-1] a [093-4] e [093-7] ganharam "decidido em 2026-11-16 (brief 100)", com a decisão. A [093-5] ganhou "aprovado por Sidarta como exceção em 2026-11-16 (brief 100)", sem a palavra "decidido": a linha dela cita a [091-1], e a guarda daria a [091-1] por vencida (`destino_vencido` procura "decidid" em toda linha do PLAN que cita a lacuna). Pelo mesmo motivo, a nota da [093-4] cita a lacuna nova como "lacuna 1 do brief 100", sem o identificador.
   - A [091-1] ganhou a nota de que o P-039 foi aprovado e o 5 do contrato continua sem aprovação. A nota não traz "decidido", porque a parte do contrato segue aberta e a guarda ainda aponta para ela.

## 3. Algum texto é analisado só em parte? (AGENTS §4)

**Sim**, e este brief não criou corte nem mudou código. Os cortes da tabela da seção 1 agora têm aprovação de Sidarta registrada (2026-11-16). Seguem sem aprovação e com destino:

- os trechos de violação pendente do teste: P-009 (10 candidatos), P-021 (200 fatos), P-025, P-026, P-027, P-031, P-032, P-035, `interessa` do P-034 e o `[:1]` do P-030;
- os 5 pontos em aberto do 079.

A prova é o próprio teste, verde (seção 5): todo corte de `agente_nw/` tem estado.

## 4. Verificador: antes e depois

Antes (árvore limpa, `9481f90`):

```
$ .venv/bin/python scripts/verificar_auditoria_texto.py --raiz . ; echo "exit=$?"
340 arquivos, 284 certificados, 49 cortam, 7 não analíticos, 0 não conferidos, 6 ponto(s) aguardando decisão de Sidarta
2039 ocorrência(s) da varredura mecânica, todas com destino no relatório
exit=0
```

Depois (o P-039 saiu da lista de "aguardando"; os outros cinco aprovados já estavam fora dela, como `CORRIGIDO`):

```
$ .venv/bin/python scripts/verificar_auditoria_texto.py --raiz . ; echo "exit=$?"
340 arquivos, 284 certificados, 49 cortam, 7 não analíticos, 0 não conferidos, 5 ponto(s) aguardando decisão de Sidarta
2040 ocorrência(s) da varredura mecânica, todas com destino no relatório
exit=0
```

Os pontos que ainda aguardam: P-003, P-031, P-032, P-035 e P-036.

## 5. Saída dos comandos

Guarda do 093:

```
$ .venv/bin/pytest tests/test_sem_corte_de_texto.py -q
..................................                                       [100%]
34 passed in 0.50s
```

`git diff -- AGENTS_agente_nw.md`:

```diff
diff --git a/AGENTS_agente_nw.md b/AGENTS_agente_nw.md
index 15725bc..06571b8 100644
--- a/AGENTS_agente_nw.md
+++ b/AGENTS_agente_nw.md
@@ -45,6 +45,7 @@ Descrição (perfis `air16`/`pro48`, tarefas de LLM, embeddings): `docs/ARQUITET
 - Toda alteração de tabela é uma migração numerada em `scripts/migracoes/`. Nenhum brief cria ou altera tabela fora de migração.
 - Quem decide que tema cabe numa mensagem é o usuário (brief 046): o programa não descarta conteúdo por tema (política, saúde, religião…). Em troca, a redação nunca afirma sobre a pessoa o que ela não disse (opinião, posição, adesão), trata fato `[antigo]` ou `[de imagem]` como não atual, e o motor só entrega assunto com relação com o objetivo do pedido (`conector.consulta.minima` é piso necessário).
 - **Texto por inteiro (brief 079).** Quando o projeto analisa um texto (notícia, página, mensagem, comentário, histórico, fato, pedido), analisa o texto inteiro. O princípio é do dono do projeto: só Sidarta aprova exceção, e só ele (ou um brief escrito por ele) escreve em `docs/EXCECOES_TEXTO_INTEGRAL.md`. O executor não aprova exceção nem marca ponto como aprovado. Sem linha no registro, o corte é violação. O verificador é `scripts/verificar_auditoria_texto.py`. Todo brief que lê, monta ou envia texto a modelo, embedding ou filtro responde, no relatório: **"algum texto é analisado só em parte?"** (sim, onde e com que aprovação; ou não, e a prova).
+- Cada brief pode atualizar as listas de `tests/test_sem_corte_de_texto.py` e a tabela de cortes não analíticos do registro para os trechos que ele mesmo criar ou alterar, sem aprovar exceção nova — aprovar exceção continua sendo só de Sidarta.
 
 ## 5. Git
 
```

Gate, antes da entrega:

```
$ scripts/verificar.sh
ruff check: ok
ruff format: ok
mypy: ok
pytest: ok (1351 passed, 5 deselected in 50.18s)
codigo de saida: 0
```

Manifesto, `logs/arquivos_100.txt`:

```
AGENTS_agente_nw.md
docs/EXCECOES_TEXTO_INTEGRAL.md
tests/test_sem_corte_de_texto.py
docs/docs/doc_079_auditoria_texto_por_inteiro_2026-11-08.md
docs/docs/doc_100_excecoes_aprovadas_e_regra_da_guarda_2026-11-16.md
docs/PLAN_agente_nw.md
```

O brief já está no git (`27dce7b`), por isso não entra.

`logs/commit_100.txt`:

```
docs(texto): excecoes aprovadas por Sidarta em 2026-11-16 e a regra da guarda (brief 100)

Sete linhas novas em docs/EXCECOES_TEXTO_INTEGRAL.md (P-013, P-009, P-028,
P-029, P-030, P-034, P-039), cada uma com valor, arquivo e linha e condicao;
o corte de 100 caracteres da mensagem anterior nao foi aprovado (o brief 099
o removeu). Relatorio 079 com os pontos em EXCECAO APROVADA e a decisao do
P-018; a guarda move os trechos aprovados para excecao aprovada; AGENTS §4
ganha a regra que deixa cada brief manter a guarda sem aprovar excecao.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

## RELATÓRIO FINAL

- Brief executado: 100, as exceções que Sidarta aprovou em 2026-11-16 e a regra de manutenção da guarda.
- Arquivos criados: este relatório.
- Arquivos alterados (com resumo da mudança em uma linha cada):
  - `docs/EXCECOES_TEXTO_INTEGRAL.md`: sete linhas de exceção aprovada em 2026-11-16 (seis aprovações; notas e moldes em duas linhas).
  - `docs/docs/doc_079_auditoria_texto_por_inteiro_2026-11-08.md`: estados e decisões de P-009, P-013, P-018, P-028, P-029, P-030, P-034 e P-039; números do resumo; contagem de linhas do teste da guarda; citações renumeradas do grupo 093 no apêndice A.
  - `tests/test_sem_corte_de_texto.py`: trechos aprovados movidos de violação pendente para exceção aprovada; `candidatos[:1]` com destino [100-1].
  - `AGENTS_agente_nw.md`: §4, a frase do item 2.4.
  - `docs/PLAN_agente_nw.md`: Resumo, Done e as decisões [093-1] a [093-5] e [093-7] marcadas com a decisão de 2026-11-16; nota na [091-1].
- Arquivos preservados literalmente na área afetada: todo `agente_nw/`, `scripts/verificar_auditoria_texto.py`, a tabela "Cortes não analíticos" do registro e as 19 linhas de exceção de 2026-11-08 (inclusive P-018 e P-033).
- Script de verificação (o gate, rodado pelo `scripts/agente_entregar.sh`; saída colada): seção 5. O `agente_entregar.sh` roda o gate de novo e é ele que decide.
- Comandos executados: `grep` do item 2.3, `scripts/verificar_auditoria_texto.py` (antes, depois e `--varredura`), `pytest tests/test_sem_corte_de_texto.py`, `scripts/verificar.sh`, `git diff`. Nenhum comando chamou o Ollama, tocou `agente.db` ou leu rede social.
- Manifesto do commit (`logs/arquivos_100.txt` e `logs/commit_100.txt`, conteúdo colado): seção 5.
- Pendências e decisões que ficaram abertas: lacunas abaixo.
- Resumo, Doing, Backlog e Done do `docs/PLAN_agente_nw.md` atualizados: sim (Doing segue vazio; o Backlog e as Decisões recebem as lacunas pelo `agente_entregar.sh`).

## Lacunas

| # | Lacuna | Destino | Impacto |
|---|---|---|---|
| 1 | P-030: quando não há molde `usado`, a redação recebe no máximo 1 molde `entregue` (`agente_nw/nucleo/database/queries/consulta_contato.py:124`, `candidatos[:1]`, arranque a frio do brief 065). A aprovação de 2026-11-16 foi de "2 moldes" e não cobre esse 1. Aprovar como exceção ou mandar corrigir? | decisão | nice |
| 2 | A guarda (`linhas_de_excecao` em `tests/test_sem_corte_de_texto.py`) guarda uma linha por ponto. Com duas linhas P-009 no registro (2026-11-08 e 2026-11-16), só a última é conferida, por valor e condição preenchidos. A primeira continua conferida pelo verificador do 079, mas não pela guarda | dívida | nice |
