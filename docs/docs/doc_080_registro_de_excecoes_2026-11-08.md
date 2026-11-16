# Relatório 080 — Registro das exceções ao "texto por inteiro" aprovadas por Sidarta

Executado em 2026-11-16, com o brief na versão v2 (item 2.5, autorização de Sidarta de 2026-11-14).
Nenhum código de produção foi tocado: só documentos.

## RELATÓRIO FINAL
- Brief executado: 080 (`docs/briefs/brief_080_registrar_excecoes_texto_integral_2026-11-08.md`, v2).
- Arquivos criados: este relatório; `logs/commit_080.txt` e `logs/arquivos_080.txt` (fora do git).
- Arquivos alterados (com resumo da mudança em uma linha cada):
  - `docs/EXCECOES_TEXTO_INTEGRAL.md`: cabeçalho da tabela troca para as sete colunas do item 2.4 e ganha as 19 linhas aprovadas.
  - `docs/docs/doc_079_auditoria_texto_por_inteiro_2026-11-08.md`: 19 pontos passam a `EXCEÇÃO APROVADA` com a decisão de Sidarta; seção 1 e intro da seção 3 dizem 26 em aberto; seção 6 ganha as linhas de `scripts/executar_serie.sh` e `tests/test_executar_serie.py` e corrige as contagens de `scripts/agente_entregar.sh` (136→146) e `tests/test_guarda_comando.py` (134→266); apêndice A dá destino às três ocorrências de `scripts/executar_serie.sh` (l. 107, 121, 123); texto corrido 317→319 arquivos e 1.272→1.275 ocorrências.
  - `docs/PLAN_agente_nw.md`: Resumo, Done, [079-1] (45→26) e [086-1] (resolvido).
  - `docs/briefs/brief_080_registrar_excecoes_texto_integral_2026-11-08.md`: a v2 (item 2.5) já estava no disco sem commit; entra no manifesto (AGENTS §5 / skill `/executar`).
- Arquivos preservados literalmente na área afetada: `scripts/verificar_auditoria_texto.py` (nenhuma linha; brief 080 §5), todo código de produção, as demais linhas da seção 6 e do apêndice A do relatório 079, os blocos de saída de comando colados no relatório 079 (`RELATÓRIO FINAL`, mensagem de commit, saídas de 2026-11-08) e os 26 pontos que seguem `AGUARDANDO DECISÃO DE SIDARTA`.
- Script de verificação (o gate): colado na seção "Saídas" abaixo (rodei `scripts/verificar.sh` antes de entregar; o `agente_entregar.sh` o repete).
- Comandos executados: seção "Saídas".
- Manifesto do commit: seção "Manifesto".
- Pendências e decisões que ficaram abertas: nenhuma nova. O conserto de fundo do verificador (brief 093) segue com o seu brief.
- Resumo, Doing, Backlog e Done do `docs/PLAN_agente_nw.md` atualizados: sim (Backlog pelo `agente_lacunas.py`, ver `## Lacunas`).

## 1. O que foi feito

1. **Registro (itens 2.1, 2.2, 2.4).** As 19 linhas da tabela 2.2 foram gravadas, uma por ponto, cada uma com o identificador, `Arquivo:função` e `O que é cortado` copiados da seção 3 do relatório 079 (não reescritos), `Valor aprovado` com arquivo e linha conferidos no código e em `config/limiares.yaml` de hoje, `Condição que mantém a exceção válida` (a regra geral e as seis condições específicas de P-009, P-011, P-018, P-020, P-021 e P-033), `Justificativa aprovada` (alcance da tabela 2.2 + razão da "Proposta do executor") e "Aprovado por Sidarta em 2026-11-08". P-009 registra à parte o que **não** está aprovado (`candidatos_por_contato`, 10) e P-021 também (o teto de 200 em `localizacao.py:376`). Nenhum ponto fora da tabela 2.2 foi aprovado.
2. **Relatório 079, seção 3.** Nos 19 pontos: `Estado: EXCEÇÃO APROVADA` e `Decisão de Sidarta: aprovar exceção (2026-11-08), alcance conforme o registro`. Seção 1 e a introdução da seção 3 passam a dizer 19 aprovados e 26 em aberto.
3. **Item 2.5, seção 6 e apêndice A.** Li `scripts/executar_serie.sh` (279/279 linhas) e `tests/test_executar_serie.py` (404/404 linhas) do início ao fim. Resultado dos dois: **CERTIFICADO**, sem ponto novo: o script lê só os rótulos `Modelo`, `Esforço` e `Ordem em série` do cabeçalho do brief; `sys.argv[1:]` (l. 107) é a lista de números de brief, e `.split()[0]` (l. 121 e 123) é a primeira palavra do rótulo; o brief inteiro vai ao `/executar`, que abre o arquivo; o teste usa `claude`, `pmset`, `caffeinate` e `osascript` falsos. Isso confirma o que a seção 9 do `doc_086` já dizia, sem usá-la como atalho: li os dois arquivos. O item 2.5.d não foi acionado (nada para parar).
4. As três ocorrências entraram em grupos `descartada:` que já existiam: l. 107 em "fatia a partir de índice fixo ... sem texto de conteúdo" (7→8) e l. 121 e 123 em "split de URL, nome ou linha de formato, não de texto de conteúdo" (16→18). Nenhum grupo novo. A numeração das linhas é a que o verificador devolveu hoje (a mesma que o brief citava).

## 2. Saídas

Verificador, **antes** (saída de partida, `logs/verificador_080_antes.txt`):

```
$ python3 scripts/verificar_auditoria_texto.py
319 arquivos, 256 certificados, 54 cortam, 7 não analíticos, 0 não conferidos, 45 ponto(s) aguardando decisão de Sidarta
1275 ocorrência(s) da varredura mecânica, todas com destino no relatório

7 inconsistência(s):
  - arquivo do universo ausente da tabela de certificação: scripts/executar_serie.sh
  - arquivo do universo ausente da tabela de certificação: tests/test_executar_serie.py
  - scripts/agente_entregar.sh: a tabela diz 136/136 linhas, mas o arquivo tem 146
  - tests/test_guarda_comando.py: a tabela diz 134/134 linhas, mas o arquivo tem 266
  - ocorrência sem destino no relatório: scripts/executar_serie.sh:107 [py:slice_inicio] — cite-a na seção 3, na seção 4 ou no apêndice A
  - ocorrência sem destino no relatório: scripts/executar_serie.sh:121 [linhas] — cite-a na seção 3, na seção 4 ou no apêndice A
  - ocorrência sem destino no relatório: scripts/executar_serie.sh:123 [linhas] — cite-a na seção 3, na seção 4 ou no apêndice A
exit=1
```

Verificador, **depois** (`logs/verificador_080_depois.txt`):

```
$ python3 scripts/verificar_auditoria_texto.py
319 arquivos, 258 certificados, 54 cortam, 7 não analíticos, 0 não conferidos, 26 ponto(s) aguardando decisão de Sidarta
1275 ocorrência(s) da varredura mecânica, todas com destino no relatório
exit=0
```

Conferências do critério de aceite (itens 1, 4 e 5):

```
$ grep -c '^| P-' docs/EXCECOES_TEXTO_INTEGRAL.md
19
$ grep -c 'Aprovado por Sidarta em 2026-11-08' docs/EXCECOES_TEXTO_INTEGRAL.md
19
$ grep -c '^#### P-' docs/docs/doc_079_auditoria_texto_por_inteiro_2026-11-08.md
45
$ grep -cE '^- Estado: EXCEÇÃO APROVADA' docs/docs/doc_079_auditoria_texto_por_inteiro_2026-11-08.md
19
$ grep -cE '^- Estado: AGUARDANDO' docs/docs/doc_079_auditoria_texto_por_inteiro_2026-11-08.md
26
$ wc -l scripts/executar_serie.sh tests/test_executar_serie.py scripts/agente_entregar.sh tests/test_guarda_comando.py
     279 scripts/executar_serie.sh
     404 tests/test_executar_serie.py
     146 scripts/agente_entregar.sh
     266 tests/test_guarda_comando.py
```

Pontos no registro: P-002, P-005, P-008, P-009, P-011, P-015, P-016, P-017, P-018, P-020, P-021, P-022, P-023, P-024, P-033, P-038, P-043, P-044, P-045 (19).

Gate (`scripts/verificar.sh`, rodado antes da entrega com as edições já feitas):

```
ruff check: ok
ruff format: ok
mypy: ok
pytest: ok (1086 passed, 5 deselected in 73.96s (0:01:13))
```

`git diff --stat` antes da entrega (só os arquivos do escopo):

```
 docs/EXCECOES_TEXTO_INTEGRAL.md                    |  23 +++-
 docs/PLAN_agente_nw.md                             |  (ver manifesto)
 ...registrar_excecoes_texto_integral_2026-11-08.md |  46 +++++---
 ...c_079_auditoria_texto_por_inteiro_2026-11-08.md | 120 +++++++++++----------
```

(mais este relatório, novo.)

## 3. Manifesto

`logs/arquivos_080.txt`:

```
docs/EXCECOES_TEXTO_INTEGRAL.md
docs/docs/doc_079_auditoria_texto_por_inteiro_2026-11-08.md
docs/docs/doc_080_registro_de_excecoes_2026-11-08.md
docs/briefs/brief_080_registrar_excecoes_texto_integral_2026-11-08.md
docs/PLAN_agente_nw.md
```

`logs/commit_080.txt`:

```
docs(080): registra 19 excecoes aprovadas ao texto por inteiro e recertifica os arquivos do brief 086
```

## 4. Decisões do executor (fora do que o brief diz)

- **Totais de linhas da seção 1 do relatório 079** (15.288 / 2.903 / 1.551 / 21.323 / 38.289): não os remedi, porque o critério com que foram somados naquele dia não está no relatório (uma soma nova por `find` dá outros números). Ficam como foram medidos, com uma frase que diz isso e o que mudou desde então (os dois arquivos do 086 somam 683 linhas; as duas contagens corrigidas mudaram em 142). O brief pediu atualizar só os números do universo (arquivos e ocorrências).
- **Células da tabela:** o texto copiado da seção 3 passou por escape de `|` e por junção de espaços; nenhuma barra precisou de escape (`grep -c '\\|'` no registro dá 0), então o texto é o do relatório 079, palavra por palavra.
- **Pedidos laterais do item 2.3 (cinco):** entram no Backlog pelo `agente_lacunas.py`, via a tabela abaixo, e não à mão.
- **Hash no PLAN:** o PLAN não traz o hash deste commit (ele só existe depois da entrega e a série exige árvore limpa ao fim). O hash está na linha final do `agente_entregar.sh` e em `git log -1`.
- **Data nas linhas de decisão do relatório 079:** "2026-11-08" é a data da aprovação de Sidarta (brief, item 2.1), não a da execução (2026-11-16).

## Lacunas

| # | Lacuna | Destino | Impacto |
|---|---|---|---|
| 1 | P-005 e P-015: a tela deve avisar quando a coleta ou a leitura de rede social parou por teto (hoje o `preparar` só avisa o tempo; o `truncada` das listas morre no modelo) — pedido lateral do item 2.3 | backlog | degrada |
| 2 | P-018: descrição de imagem mais longa quando a imagem tem texto legível — pedido lateral do item 2.3 | backlog | nice |
| 3 | P-020: a tela de confirmação deve mostrar o cabeçalho inteiro que a rede deu (hoje mostra 3 linhas) — pedido lateral do item 2.3 | backlog | degrada |
| 4 | P-021: olhar o teto de 200 fatos na deduplicação (`nucleo/localizacao.py:376`); fora da aprovação — pedido lateral do item 2.3 | backlog | degrada |
| 5 | P-009: medir quantos dos 10 candidatos (`conector.candidatos_por_contato`) passam o gate; o teto de 10 não está aprovado — pedido lateral do item 2.3 | backlog | degrada |
| 6 | O verificador da auditoria 079 continua sendo um retrato de um instante: todo brief que criar arquivo de código volta a deixá-lo em 1 até o brief 093 resolver (já registrado em [086-1]) | nenhum | quebra |
