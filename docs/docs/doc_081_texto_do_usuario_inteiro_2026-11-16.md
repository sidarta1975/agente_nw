# DOC 081 — O que o usuário escreve chega inteiro ao modelo

**Brief:** `docs/briefs/brief_081_o_que_o_usuario_escreve_chega_inteiro_2026-11-08.md`
**Data:** 2026-11-16
**Executor:** Claude Opus 5, sessão do `/executar 081` (código e testes) e sessão seguinte de Sidarta
(terceiro estado do verificador, autorizado por escrito, e fechamento da entrega)

---

## 1. Objetivo

Nada que Sidarta escreve chega cortado ao modelo: o comentário sobre a mensagem, a nota sobre o
contato, o comentário do molde e a lista `evitar` entram inteiros, e o corte por tamanho sacrifica
qualquer outro bloco antes de tocar no texto dele.

## 2. O que mudou, ponto por ponto do relatório 079

| Ponto do 079 | O que mudou | Teste |
|---|---|---|
| P-028 (`nucleo/historico.py:56`) | O comentário do usuário no histórico perdeu o corte de 300 caracteres e entra inteiro. A mensagem já entregue continua em 100 (decisão 2.2). | `test_comentario_de_2000_caracteres_chega_inteiro_ao_prompt`, `test_mensagem_entregue_de_500_caracteres_chega_com_100` |
| P-029 (`nucleo/redacao.py:162`, `_notas`) | A nota do contato perdeu o corte de 400 caracteres (`_TRECHO_DA_NOTA`, constante removida). O teto de 5 notas fica. | `test_nota_de_1500_e_comentario_de_molde_de_1000_chegam_inteiros` |
| P-030 (`nucleo/redacao.py:188`, `_moldes`) | O comentário do molde perdeu o corte de 300 caracteres. O teto de 2 moldes fica. | o mesmo teste acima |
| P-034 (`nucleo/modelos/pedido.py:91`) | `evitar` saiu do validador que cortava em 5 itens e ganhou validador próprio, só de deduplicação. `interessa` (5), `sobre_o_usuario` (5) e `termos_busca` (6) não mudaram. | `test_evitar_mantem_oito_termos_e_interessa_continua_em_cinco`, `test_mensagem_que_cita_o_oitavo_termo_de_evitar_e_detectada` |
| P-039 (`nucleo/relevancia/cruzamento.py:407`) | **Inalterado**, como manda a decisão 2.5: o ponto de apoio usa os 5 interesses que o contrato já limita; depende de decisão futura sobre `interessa`. Estado no relatório 079 continua `AGUARDANDO DECISÃO DE SIDARTA`. | — |

Além dos quatro pontos, a decisão 2.4 (o corte por tamanho não sacrifica texto do usuário) virou
código em `nucleo/prompts/redigir_ganchos.py` e `nucleo/redacao.py`:

- `EntradaRedacao` ganhou `historico_comentarios` (um item por consulta do histórico, na mesma
  ordem), `moldes_comentados` (as linhas de molde que têm comentário) e `comentarios_preservados`
  (preenchido só pelo corte);
- `cortar_por_tamanho` passou a guardar, quando reduz o histórico a uma consulta, o comentário das
  consultas que saíram, e a só descartar os moldes **sem** comentário;
- `historico.comentarios_da_consulta` devolve o comentário de uma consulta isolado do resto, que é
  o que sobrevive ao corte;
- quando mesmo assim o prompt estoura, o texto do usuário **não** é cortado: quem avisa é a medida
  da janela (brief 082), como a decisão 2.4 determina.

`termo_evitado` (`nucleo/relevancia/candidatos.py`) não precisou mudar: ele já percorre a lista
inteira que recebe, e passou a receber os oito termos porque o teto saiu do contrato — é o que o
teste do oitavo termo prova.

## 3. Arquivos-alvo do brief que não mudaram, e por quê

| Arquivo | Por quê |
|---|---|
| `nucleo/database/queries/consulta_contato.py` | As linhas 123 e 124 são teto de **lista** (`usados[:maximo]`, `candidatos[:1]`), não corte de caractere de texto do usuário. O brief manda tocar só o corte de texto do usuário (§3). |
| `nucleo/database/queries/nota_contato.py` | Não há corte ali: a nota é lida inteira do banco; o corte estava em `_notas`, já desfeito. |
| `nucleo/relevancia/candidatos.py` | `termo_evitado` já lê a lista inteira (seção 2). |
| `config/limiares.yaml` | Nenhuma chave ficou órfã: as constantes removidas eram de Python (`_TRECHO_DA_NOTA`); busca por `trecho`, `nota`, `comentario` e `evitar` no arquivo não devolve nada. |

## 4. O terceiro estado do verificador (autorização de Sidarta, 2026-11-16)

A primeira tentativa de entregar este brief **parou**: o §6 manda marcar P-028, P-029, P-030 e
P-034 como `CORRIGIDO (brief 081)` no relatório 079, e o critério 3 exige que
`scripts/verificar_auditoria_texto.py` devolva 0 — mas o verificador só conhecia dois estados
(`AGUARDANDO DECISÃO DE SIDARTA` e `EXCEÇÃO APROVADA`) e acusava o terceiro. Os seis briefs do
conjunto que corrigem ponto (081, 082, 083, 088, 089, 090) carregam a mesma marca, então a série
pararia em cada um deles.

Sidarta autorizou por escrito, nesta conversa, ensinar o estado novo ao verificador, com teste,
aceitando-o, não contando-o como "aguardando" e continuando a exigir um número de brief — e nada
mais no verificador. Foi o que entrou:

- `ESTADO_CORRIGIDO = "CORRIGIDO (brief NNN)"` e o reconhecedor
  `^CORRIGIDO \(brief (\d{3})\)$`, sem tolerância de forma: `CORRIGIDO` sozinho,
  `CORRIGIDO (brief 81)` ou `CORRIGIDO pelo brief 081` continuam sendo recusados;
- `numeros_de_brief(raiz)`, que lê os números de `docs/briefs/brief_NNN_*.md`, e a recusa quando o
  estado cita um brief que não existe;
- a contagem de "aguardando" não mudou de regra: ela já contava só `ESTADO_ABERTO`, então o estado
  novo sai da fila de decisão sem nenhuma linha a mais.

**Uma ressalva honesta sobre "brief entregue".** A autorização pedia exigir "um número de brief
entregue". O que entrou exige um número de brief **que existe em `docs/briefs/`**, não que ele já
esteja entregue, por duas razões: (a) o critério 3 do próprio brief roda **antes** do commit, então
exigir entrega tornaria impossível a qualquer brief marcar o ponto que ele mesmo acabou de
corrigir — foi justamente o laço que travou esta entrega; (b) a prova de entrega vive em `logs/`
(ignorado pelo git) ou no histórico do git, e amarrar o verificador a isso o deixaria vermelho num
clone novo. Fica como decisão na seção de lacunas.

## 5. Saídas coladas

Critério 1 — teste de aceite:

```
$ .venv/bin/pytest tests/test_texto_do_usuario_inteiro.py -q
......                                                                   [100%]
6 passed in 1.35s
```

Critério 2 — nenhum corte de texto do usuário restou nos três pontos (grep sem resultado, código 1):

```
$ grep -n "\[:300\]\|\[:400\]\|_TRECHO_DA_NOTA" agente_nw/nucleo/historico.py agente_nw/nucleo/redacao.py agente_nw/nucleo/modelos/pedido.py
(nenhuma linha)
```

Testes do verificador, com os oito casos novos do estado `CORRIGIDO`:

```
$ .venv/bin/pytest tests/test_verificar_auditoria_texto.py -q
............................................................             [100%]
60 passed in 2.13s
```

Critério 3 — o verificador da auditoria 079 devolve 0:

```
$ python3 scripts/verificar_auditoria_texto.py
320 arquivos, 259 certificados, 54 cortam, 7 não analíticos, 0 não conferidos, 22 ponto(s) aguardando decisão de Sidarta
1290 ocorrência(s) da varredura mecânica, todas com destino no relatório
código: 0
```

Critério 4 — o gate:

```
$ scripts/verificar.sh
ruff check: ok
ruff format: ok
mypy: ok
pytest: ok (1100 passed, 5 deselected in 56.58s)
```

## 6. O que o ajuste no verificador obrigou a acertar no relatório 079

Mudar o verificador deslocou as linhas dele e do seu teste, e o relatório 079 guarda contagem de
linha e `arquivo:linha` de cada ocorrência da varredura — é o retrato de um instante de que fala a
lacuna [086-1]. Pela mesma autorização, e seguindo o que o brief 080 fez no item 2.5, foram
acertados: a contagem de `scripts/verificar_auditoria_texto.py` (414 → 438) e de
`tests/test_verificar_auditoria_texto.py` (500 → 556) na seção 6; as treze linhas do grupo
"é a própria lista de padrões da varredura (este verificador)" no apêndice A; e os números
narrativos (319 → 320 arquivos, 1.275 → 1.290 ocorrências) nas seções 1, 2, 6 e no apêndice. O
`tests/test_texto_do_usuario_inteiro.py` e as suas quinze ocorrências já tinham sido registrados
pela sessão do `/executar`. Nenhum ponto novo foi criado: `grep -c "^#### P-"` continua em 45.

## 7. Como esta entrega foi feita em duas sessões

A sessão do `/executar 081`, dentro da primeira série de verdade, escreveu os testes e o código,
marcou os quatro pontos no relatório 079 e **parou** no critério 3, sem relatório, manifesto, PLAN
nem commit — e a série parou com ela, no primeiro brief, sem tentar o 087. O executor em série fez
o certo: reconheceu que não houve entrega (nenhuma prova no disco nem no git), gravou o motivo em
`logs/serie/2026-11-16_005316/STATUS.txt`, apagou a trava e não seguiu adiante. Custo da série até
ali: US$ 1,1046 (preço de tabela).

Esta sessão não refez o código: conferiu o que estava no disco (seis testes verdes, os quatro
pontos marcados), ensinou o estado novo ao verificador com teste, acertou o relatório 079 e fechou
a entrega.

## RELATÓRIO FINAL
- Brief executado: 081 — O que o usuário escreve chega inteiro ao modelo
- Arquivos criados: `tests/test_texto_do_usuario_inteiro.py` (6 testes, seção 4 do brief); `docs/docs/doc_081_texto_do_usuario_inteiro_2026-11-16.md` (este relatório)
- Arquivos alterados (com resumo da mudança em uma linha cada):
  - `agente_nw/nucleo/historico.py` — comentário do usuário inteiro no histórico; nova `comentarios_da_consulta`, que é o que sobrevive ao corte
  - `agente_nw/nucleo/redacao.py` — `_notas` e `_moldes` sem corte de caractere, `_TRECHO_DA_NOTA` removida, comentários do histórico e dos moldes levados à entrada da redação
  - `agente_nw/nucleo/prompts/redigir_ganchos.py` — `cortar_por_tamanho` preserva nota e comentários do usuário; sacrifica só os blocos sem texto dele
  - `agente_nw/nucleo/modelos/pedido.py` — `evitar` sem teto de 5, com validador próprio
  - `scripts/verificar_auditoria_texto.py` — terceiro estado `CORRIGIDO (brief NNN)`, com o número conferido contra `docs/briefs/` (autorização de Sidarta, 2026-11-16)
  - `tests/test_verificar_auditoria_texto.py` — 8 casos novos do estado `CORRIGIDO` (aceito, fora da contagem de aguardando, brief inexistente recusado, cinco formas erradas recusadas)
  - `docs/docs/doc_079_auditoria_texto_por_inteiro_2026-11-08.md` — P-028, P-029, P-030 e P-034 em `CORRIGIDO (brief 081)`; contagens de linha, apêndice A e números narrativos acertados
  - `docs/PLAN_agente_nw.md` — Resumo, Doing e Done
- Arquivos preservados literalmente na área afetada: `agente_nw/nucleo/database/queries/consulta_contato.py`, `agente_nw/nucleo/database/queries/nota_contato.py`, `agente_nw/nucleo/relevancia/candidatos.py`, `config/limiares.yaml` (seção 3 diz por quê); nenhuma asserção de teste anterior foi editada
- Script de verificação (o gate, rodado pelo `scripts/agente_entregar.sh`; saída colada): seção 5 — `ruff check: ok`, `ruff format: ok`, `mypy: ok`, `pytest: ok (1100 passed, 5 deselected)`
- Comandos executados: `.venv/bin/pytest tests/test_texto_do_usuario_inteiro.py -q`; `.venv/bin/pytest tests/test_verificar_auditoria_texto.py -q`; `grep -n "\[:300\]\|\[:400\]\|_TRECHO_DA_NOTA" ...`; `python3 scripts/verificar_auditoria_texto.py`; `scripts/verificar.sh`; `scripts/agente_entregar.sh 081`
- Manifesto do commit (`logs/arquivos_081.txt` e `logs/commit_081.txt`, conteúdo colado): ver seção 8
- Pendências e decisões que ficaram abertas: a forma do "brief entregue" no estado `CORRIGIDO` (lacuna 1); o verificador fora do gate, que é o brief 093 (lacuna 2); o P-039 continua aguardando decisão sobre `interessa` (lacuna 3)
- Resumo, Doing, Backlog e Done do `docs/PLAN_agente_nw.md` atualizados: sim

## 8. Manifesto

`logs/arquivos_081.txt`:

```
agente_nw/nucleo/historico.py
agente_nw/nucleo/modelos/pedido.py
agente_nw/nucleo/prompts/redigir_ganchos.py
agente_nw/nucleo/redacao.py
scripts/verificar_auditoria_texto.py
tests/test_texto_do_usuario_inteiro.py
tests/test_verificar_auditoria_texto.py
docs/docs/doc_079_auditoria_texto_por_inteiro_2026-11-08.md
docs/docs/doc_081_texto_do_usuario_inteiro_2026-11-16.md
docs/PLAN_agente_nw.md
```

`logs/commit_081.txt`: assunto `feat(texto): o que o usuario escreve chega inteiro ao modelo (brief 081)`,
com o corpo que descreve os quatro pontos, a proteção no corte por tamanho e o terceiro estado do
verificador.

## Lacunas

| # | Lacuna | Destino | Impacto |
|---|---|---|---|
| 1 | O estado `CORRIGIDO (brief NNN)` exige que o brief **exista** em `docs/briefs/`, não que já esteja entregue (seção 4 diz por quê: o critério roda antes do commit e a prova de entrega vive em `logs/`, ignorado pelo git). Se você quiser a conferência de entrega mesmo assim, a saída é o verificador aceitar `CORRIGIDO` sem prova no gate do próprio brief e cobrar a prova só depois — desenho que não cabia nesta autorização | decisão | degrada |
| 2 | O verificador continua fora do gate: nada impede um brief futuro de abrir corte novo sem passar por você, e todo brief que cria arquivo de código desloca as contagens do relatório 079 à mão. É o brief 093, que fecha o conjunto | nenhum | degrada |
| 3 | P-039 (ponto de apoio com 5 interesses) ficou inalterado por decisão do brief (2.5) e continua `AGUARDANDO DECISÃO DE SIDARTA`: depende de você decidir o teto de `interessa` | decisão | nice |
| 4 | Com o texto do usuário protegido byte a byte, o prompt pode estourar o orçamento sem que nada seja cortado. É o desenho da decisão 2.4, e quem passa a avisar é a medida da janela do brief 082 — o próximo da série a tocar nisso | nenhum | degrada |
| 5 | A primeira série de verdade gastou US$ 1,1046 para parar no primeiro brief por uma contradição que estava no texto dos seis briefs, não no código. Os outros cinco (082, 083, 088, 089, 090) foram conferidos contra o verificador antes de a série ser retomada | nenhum | nice |
