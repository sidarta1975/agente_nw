# Relatório 095 — Dano nos dados já gravados e reprocessamento

**Brief:** `docs/briefs/brief_095_dano_nos_dados_e_reprocessamento_2026-11-08.md`
**Data:** 2026-11-16
**Depende de:** brief 094 executado — conferido: o commit mais novo é `3554499 test(texto): segunda auditoria independente e prova com textos extremos (brief 094)`.

## RELATÓRIO FINAL
- Brief executado: 095, dano nos dados já gravados e reprocessamento (último do conjunto 086 a 095).
- Arquivos criados:
  - `agente_nw/manutencao/__init__.py` (vazio; marca o pacote novo que o brief pede em `agente_nw/manutencao/reprocessamento.py`)
  - `agente_nw/manutencao/reprocessamento.py`
  - `tests/test_reprocessamento.py`
  - `docs/docs/doc_095_dano_nos_dados_e_reprocessamento_2026-11-16.md` (este relatório)
- Arquivos alterados (com resumo da mudança em uma linha cada):
  - `agente_nw/cli.py`: comandos `medir-dano --banco` e `reprocessar --banco --etapa {vetores,cartoes} [--simular|--confirmo] [--saida]`, com `caminho_plan` e `_cliente_do_reprocessamento` (cliente ligado ao banco onde a etapa grava).
  - `docs/docs/doc_079_auditoria_texto_por_inteiro_2026-11-08.md`: seção 6 (linhas dos três arquivos novos; `cli.py` de 1673 para 1832 linhas, com uma frase sobre os dois comandos) e apêndice A (citações de `cli.py` renumeradas pela correspondência entre a versão anterior e a atual; grupo "Brief 095" com as 26 ocorrências novas), pela autorização de 2026-11-16 no cabeçalho do brief.
  - `docs/PLAN_agente_nw.md`: Resumo, Doing e Done.
- Arquivos preservados literalmente na área afetada: `.claude/hooks/guarda_comando.py` (a regra do brief 086, item 2.10, já previa `medir-dano` e `reprocessar` com `--simular`/`--confirmo`; os nomes foram mantidos, então a lacuna [086-7] não precisa de brief), `scripts/executar_serie.sh`, `agente_nw/nucleo/agrupamento/comparar_vetores.py`, `agente_nw/nucleo/relevancia/cartoes.py`, `tests/test_sem_corte_de_texto.py`, `docs/EXCECOES_TEXTO_INTEGRAL.md`. Nenhum dado foi alterado: o banco real não foi aberto.
- Script de verificação (o gate, rodado pelo `scripts/agente_entregar.sh`; saída colada): ver seção 7.
- Comandos executados: ver seções 2, 3 e 7.
- Manifesto do commit (`logs/arquivos_095.txt` e `logs/commit_095.txt`, conteúdo colado): ver seção 8.
- Pendências e decisões que ficaram abertas: seção `## Lacunas`.
- Resumo, Doing, Backlog e Done do `docs/PLAN_agente_nw.md` atualizados: sim (Backlog e demais seções pelas lacunas, via `agente_lacunas.py`).

## 1. O que foi feito

**`medir-dano --banco <cópia>`** (2.1, 2.2b) abre a cópia em `mode=ro`, recusa o banco real (caminho resolvido igual ao de `config`) e a cópia anterior à migração 022, e imprime só contagens e versões de prompt, com o sha256 do arquivo antes e depois:

- itens, itens com corpo, itens acima dos cortes antigos (2.000 caracteres do vetor do item, brief 089; 300 caracteres do cartão e da qualificação, brief 090), itens com corpo sem resumo da versão atual;
- vetores: `vetor_item` não tem versão (lacuna [089-3]: só o tamanho do texto diz quem mudaria); `vetor_tema`, `vetor_assunto` e `vetor_perfil` do critério anterior contra o total;
- cartões, cartões de versão antiga (`cartao_versao` nula ou diferente da atual), cartões sem registro de cobertura (`cartao_itens` nulo);
- ganchos (`gancho_uso`) por versão do prompt `redigir_ganchos`, os de versão antiga e os que estão em assunto de cartão antigo;
- fatos por versão de prompt, e os de versão antiga ou sem versão (as atuais são as de `extrair_de_texto` e `extrair_captura_rede_social`, desde o brief 088);
- extrações processadas sem registro de partes lidas (`fila_extracao.partes_lidas` nulo, brief 088);
- fila de revisão pendente, por tarefa (o nome da tarefa é constante do programa, não texto de terceiros).

**`reprocessar --banco <cópia> --etapa vetores|cartoes`** (2.2):

- **simulação, o padrão** (`--simular` é aceito e não muda nada): a cópia é copiada pela API de backup do SQLite para um arquivo à parte (`<cópia>.simulacao-<etapa>-<data>.db`, ou `--saida`), a etapa grava só nesse arquivo, e o que mudaria é contado comparando-o com o banco dado, aberto em `mode=ro`. O sha256 do banco dado é conferido antes e depois. O cliente do modelo é ligado ao arquivo à parte: fila de revisão e proveniência vão para ele;
- **`--confirmo`**: grava no próprio banco dado, depois de uma cópia de segurança (`<banco>.antes-do-reprocessar-<etapa>-<data>.db`). É recusado (a) dentro de uma série (variável `SERIE_DENTRO_DO_CAFFEINATE`, que o `executar_serie.sh` exporta) e (b) no banco real sem uma linha do PLAN com `reprocessar <etapa>` e `autorizado por Sidarta em AAAA-MM-DD` — a autorização é por etapa (2.4). `--simular` e `--confirmo` juntos são recusados. A trava (`guarda_comando.py`) continua bloqueando o `--confirmo` em qualquer sessão do Claude Code (conferido na seção 7);
- **etapa `vetores`**: vetor de cada item com vetor gravado (texto inteiro, `embeddar_em_partes`), centróide de cada assunto (média dos vetores novos dos seus itens, a regra do agrupador) e vetor de cada tema (`texto_do_tema`), gravados com o identificador do critério novo. Conta, pela regra de `comparar_vetores.contar`, os itens que trocariam de assunto, fusões, separações, republicações, os assuntos com item que trocaria e os ganchos nesses assuntos. O centróide do contato (`vetor_perfil`) não é regravado: o cruzamento já o recalcula e regrava a cada pedido (`cruzamento.py`, nas duas variantes), e o `medir-dano` mostra quantos ainda são do critério anterior;
- **etapa `cartoes`**: `cartoes.gerar_cartao` para cada assunto com cartão de versão antiga (refaz também os resumos dos itens, brief 090). Conta os regravados, as falhas, os cartões que mudariam e os ganchos nesses assuntos.

Ganchos não são regravados: cada gancho é a redação entregue num pedido passado, e refazê-lo exigiria reabrir aquela consulta. O `reprocessar` conta os ganchos em assunto que mudaria (lacuna 2).

## 2. `medir-dano` numa cópia do banco

`agente_nw copiar-banco` não achou backup (`dados/backups` vazio). Usei, como o brief 089, a cópia de desenvolvimento mais recente que já existe, `dados/agente.testeedy.db` (15/10), copiada para `/tmp/b095/copia.db`; só a cópia em `/tmp` recebeu as migrações (estava na 013). O banco real não foi aberto.

```
$ .venv/bin/agente_nw copiar-banco /tmp/b095/copia.db
FALHA: nenhum backup encontrado em /Users/sidarta48/github/agente_nw/dados/backups
$ cp dados/agente.testeedy.db /tmp/b095/copia.db
$ .venv/bin/python -c "...migracoes.aplicar(conexao.abrir('/tmp/b095/copia.db'))..."
antes 13
depois 22
$ .venv/bin/agente_nw medir-dano --banco /tmp/b095/copia.db
Banco: /tmp/b095/copia.db
sha256 antes: b06a879b1cbe0bc2fd7ca4c30b50de7fbf4edfba8986ce38ed8057cf2550fc11
Itens: 570
Itens com corpo: 570
Itens com texto acima de 2000 caracteres (corte antigo do vetor do item): 424
Itens com texto acima de 300 caracteres (corte antigo do cartão e da qualificação): 570
Itens com corpo sem resumo da versão atual: 570
vetor_item: 511 vetores, sem versão gravada (o critério não se distingue)
vetor_tema: 0 de 0 do critério anterior
vetor_assunto: 413 de 413 do critério anterior
vetor_perfil: 5 de 5 do critério anterior
Cartões: 0
Cartões de versão antiga: 0
Cartões sem registro de cobertura: 0
Ganchos: 17
Ganchos de versão antiga do prompt: 17
Ganchos em assunto de cartão antigo: 0
  ganchos da versão sem versão: 17
Fatos: 149
Fatos de versão antiga ou sem versão: 149
  fatos da versão sem versão: 149
Extrações processadas sem registro de partes lidas: 151
Fila de revisão pendente: 200
  fila de revisão, extrair_de_texto: 197
  fila de revisão, extrair_pedido: 1
  fila de revisão, redigir_ganchos: 2
sha256 depois: b06a879b1cbe0bc2fd7ca4c30b50de7fbf4edfba8986ce38ed8057cf2550fc11
```

Leitura: na cópia de outubro, **todo** o derivado é do critério antigo — 424 de 570 itens passavam do corte do vetor e os 570 passavam do corte do cartão; 413 de 413 centróides de assunto e 5 de 5 de contato são do critério anterior (o mesmo número do brief 089); os 17 ganchos e os 149 fatos nasceram antes da proveniência (brief 066), então "sem versão" é tudo o que se pode dizer deles. A cópia não tem cartão nenhum. São números de uma cópia de 15/10: o banco de hoje tem outros (lacuna 4).

## 3. `reprocessar` em simulação na mesma cópia

```
$ .venv/bin/agente_nw reprocessar --banco /tmp/b095/copia.db --etapa cartoes --simular
Banco: /tmp/b095/copia.db
sha256 antes: b06a879b1cbe0bc2fd7ca4c30b50de7fbf4edfba8986ce38ed8057cf2550fc11
Cartões de versão antiga: 0
Cartões regravados: 0
Falhas (o cartão de antes fica, motivo na fila de revisão): 0
Cartões que mudariam: 0
Ganchos em assunto que mudaria: 0
Simulação gravada em /tmp/b095/copia.simulacao-cartoes-20261116121152.db
sha256 depois: b06a879b1cbe0bc2fd7ca4c30b50de7fbf4edfba8986ce38ed8057cf2550fc11
```

Antes da etapa de vetores, o porteiro (o `bge-m3` roda na 11435):

```
$ porteiro cabe bge-m3 --porta 11435; echo "codigo=$?"
Cabe: bge-m3:latest precisa de cerca de 6,1 GB.
Ficaria com 12,2 GB de 26,0 GB e 2 de 2 modelos.
A conta é estimativa: bge-m3:latest não está carregado agora, então o tamanho vem do arquivo no disco mais 5,0 GB de folga de contexto.
codigo=0
```

```
$ .venv/bin/agente_nw reprocessar --banco /tmp/b095/copia.db --etapa vetores --simular
Banco: /tmp/b095/copia.db
sha256 antes: b06a879b1cbe0bc2fd7ca4c30b50de7fbf4edfba8986ce38ed8057cf2550fc11
Traceback (most recent call last):
  (...)
  File "/Users/sidarta48/github/agente_nw/agente_nw/manutencao/reprocessamento.py", line 319, in reprocessar_vetores
    novo = embeddar_em_partes(cliente, texto_do_item(linha["titulo"], linha["texto"]))
  (...)
  File "/Users/sidarta48/github/agente_nw/agente_nw/nucleo/llm.py", line 650, in embeddar
    resposta = self._http.post(f"{self._ollama_url}/api/embed", json=corpo)
  (...)
httpx.ReadTimeout: timed out
codigo=1
$ shasum -a 256 /tmp/b095/copia.db
b06a879b1cbe0bc2fd7ca4c30b50de7fbf4edfba8986ce38ed8057cf2550fc11  /tmp/b095/copia.db
$ porteiro status
Servidor pid 1046, ollama — porta 11434, Ollama 0.40.11
    nenhum modelo carregado
Servidor pid 922, ollama — porta 11435, Ollama 0.34.2
    qwen2.5:7b    6,2 GB  sai às 10:22
```

A simulação de vetores **não chegou ao fim**: o primeiro `/api/embed` na 11435 esperou até o tempo-limite do cliente e o `bge-m3` nunca apareceu carregado no `porteiro status` (o servidor atendia `cervello` e `sergio` ao mesmo tempo). É o mesmo sintoma da medição do brief 094 ([094-1]). Não mexi no Ollama (instrução de Sidarta). O banco dado não mudou (sha256 igual ao de antes); o arquivo à parte ficou sem vetor novo nenhum. As contagens de decisão de assunto que existem para esta cópia são as do `comparar-vetores` do brief 089 (`--amostra 511`, todos os itens com vetor: 380 dos 511 vetores mudam, mediana do cosseno antigo × novo de 0,98 e menor de 0,82, nenhum item trocaria de assunto, 4 dos 25 republicados deixariam de ser). A etapa está provada pelo teste com embedding falso (seção 7); a medição real fica para quando a 11435 responder ao `bge-m3` (lacuna 7).

## 4. Algum texto é analisado só em parte?

**Não.** O `medir-dano` não envia texto a modelo, embedding nem filtro: conta por SQL (`COUNT`, `length(texto) > ?`), e os 2.000 e 300 caracteres são só o limiar da contagem. O `reprocessar vetores` manda o título e o texto inteiro de cada item, e o nome, a descrição e os sinônimos de cada tema, a `embeddar_em_partes` (brief 088), que divide o que não cabe numa chamada em partes que somam o texto todo; falha numa parte deixa o vetor de antes, nunca um parcial. O `reprocessar cartoes` usa `cartoes.gerar_cartao`, que lê os resumos de todos os itens do assunto, feitos com o texto inteiro, e consolida em níveis o que não cabe (brief 090). Provas: `tests/test_sem_corte_de_texto.py` percorre `agente_nw/manutencao/` e não acha fatia, `LIMIT` nem teto novos (verde na seção 7); o módulo novo não tem fatia nem `LIMIT` (as 12 ocorrências da varredura do 079 são a palavra "resumo", no apêndice A). Fora do texto: a seleção de quem é reprocessado é por versão (todos os cartões de versão antiga, todos os itens com vetor), sem amostra nem teto.

## 5. Guardar ou não o texto bruto de rede social daqui para frente (2.3)

**Hoje.** O que a extensão lê de uma rede social vira, na mesma hora, fatos extraídos (`extrair_captura_rede_social`) e o resumo da consulta (`consulta_contato.resumo_redes_sociais`); o texto lido não é guardado, e a imagem nunca é (só a descrição). A notícia guarda o texto (`item.texto`, 90 dias); o texto colado e a conversa do WhatsApp ficam na `fila_extracao`. Por isso a perda na entrada de rede social é irreversível: os 149 fatos sem versão da cópia não podem ser refeitos com o critério novo, só recoletados.

**Ganho de guardar.** (1) Reprocessar sem recoletar: um prompt ou critério novo de extração refaz os fatos do que já foi lido, como a notícia hoje permite com cartões e vetores. (2) Recoletar custa caro e não é neutro: exige a sessão de Sidarta, uma aba por vez com pausa entre páginas (AGENTS §6), e o que foi lido pode ter sido apagado ou editado na rede. (3) Auditoria: dá para conferir se um fato veio mesmo do texto (a proveniência do brief 066 diz o modelo e a versão, não o que ele leu). (4) Medição: o `medir-dano` poderia contar o que mudaria, em vez de só "sem versão".

**Custo.** Disco pequeno (texto; a imagem continua de fora). Uma migração com tabela própria, ligada à consulta e ao perfil, com prazo de vida como o `item.texto`; o leitor de capturas grava antes de extrair; o reprocessamento ganha uma etapa `fatos`, que exige decidir o que fazer com os fatos antigos (a tabela `fato` é só inserção: o fato refeito entra ao lado, e a escolha de fatos precisa saber qual vale).

**Risco de privacidade.** É texto de terceiros, em grande parte de pessoas que não são o contato (comentários, marcações, amigos), em disco e por tempo indeterminado, não só os fatos sobre o contato que o programa decidiu guardar. O texto entra nos backups e nas cópias de desenvolvimento, e o executor e as sessões de planejamento passam a ter mais dado pessoal ao alcance (a trava protege o `agente.db`, não as cópias). Com chave de API cadastrada (`ia_api`), cada reprocessamento manda o texto de novo para fora da máquina. A limpeza de conteúdo sensível já existente (`descarte_sensivel`) teria de valer também para o texto guardado, ou ele viraria a cópia que a limpeza não alcança.

**Meio-termos possíveis.** Guardar só o texto atribuído ao contato (o que ele publicou, não os comentários de outros); prazo curto (30 a 90 dias); cifrar a coluna; ou não guardar e aceitar recoletar. A decisão é de Sidarta (lacuna 3); este brief não implementa nada disso.

## 6. Ordem sugerida de reprocessamento (2.4)

1. **Vetores** (`reprocessar --etapa vetores`): primeiro, porque o agrupamento e a qualificação leem o centróide; sem a regravação, o assunto antigo é ausente para o produto e o agrupador abre assunto novo em vez de vincular (lacuna [089-2]). Comparar a simulação (seção 3) e autorizar no PLAN com `reprocessar vetores: autorizado por Sidarta em AAAA-MM-DD`.
2. **Resumos e cartões** (`reprocessar --etapa cartoes`): depois dos vetores, porque o cartão é feito dos itens que estão no assunto. Simular, comparar e autorizar com `reprocessar cartoes: autorizado por Sidarta em AAAA-MM-DD`.
3. **Ganchos**: não são regravados (seção 1). Com vetores e cartões novos, o próximo pedido para o contato já redige com o critério novo; os ganchos entregues ficam como histórico.

Cada etapa: rodar a simulação numa cópia recente (`copiar-banco`, que precisa de um backup em `dados/backups`), ver as contagens e só então escrever a autorização e rodar `--confirmo` contra o banco real, fora de série.

## 7. Testes e gate

```
$ .venv/bin/pytest tests/test_reprocessamento.py -q
............                                                             [100%]
12 passed in 2.29s
$ .venv/bin/pytest tests/test_sem_corte_de_texto.py tests/test_reprocessamento.py tests/test_vetores_texto_inteiro.py tests/test_guarda_comando.py -q
.............                                                            [100%]
157 passed in 6.55s
$ echo '{"tool_name":"Bash","tool_input":{"command":".venv/bin/agente_nw reprocessar --banco /tmp/b095/copia.db --etapa vetores --confirmo"}}' | python3 .claude/hooks/guarda_comando.py
Bloqueado: reprocessar só passa em simulação (--simular, sem --confirmo): gravação não roda sozinha (AGENTS §6; brief 095, item 2.2)
$ echo '{"tool_name":"Bash","tool_input":{"command":".venv/bin/agente_nw medir-dano --banco /tmp/b095/copia.db"}}' | python3 .claude/hooks/guarda_comando.py; echo "rc=$?"
rc=0
```

Os testes do brief (seção 4 dele) e onde estão: (1) `test_medir_dano_conta_o_que_veio_de_cada_versao`; (2) `test_medir_dano_no_cli_so_conta_e_nao_altera_o_banco` e `test_reprocessar_simulado_nao_mostra_texto_de_terceiros` (marca `SEGREDO-DE-TERCEIRO` em todo texto do banco sintético, ausente da saída); (3) `test_reprocessar_vetores_em_simulacao_grava_a_parte_e_nao_altera_o_banco` e `test_reprocessar_cartoes_em_simulacao_grava_a_parte_e_nao_altera_o_banco` (sha256 antes e depois); (4) `test_confirmo_dentro_de_uma_serie_e_recusado`; (5) `test_confirmo_no_banco_real_sem_autorizacao_no_plan_e_recusado` (a autorização de outra etapa não vale) e, como contraprova, `test_confirmo_no_banco_real_com_autorizacao_da_etapa_grava`; (6) `test_banco_real_de_config_e_recusado_sem_ser_aberto` (o caminho de `config`, sem troca, também com `..` no meio; a abertura do arquivo falharia o teste).

Verificador da auditoria 079, depois da atualização da seção 6 e do apêndice A:

```
$ .venv/bin/python scripts/verificar_auditoria_texto.py
340 arquivos, 284 certificados, 49 cortam, 7 não analíticos, 0 não conferidos, 6 ponto(s) aguardando decisão de Sidarta
2031 ocorrência(s) da varredura mecânica, todas com destino no relatório

8 inconsistência(s):
  - tests/test_evitar_e_fatos_inteiros.py: a tabela diz 198/198 linhas, mas o arquivo tem 200
  - ocorrência sem destino no relatório: tests/test_evitar_e_fatos_inteiros.py:104 [truncar] — ...
  (mais 6 linhas do mesmo arquivo)
```

As 8 já estavam no HEAD (`3554499`), conferido rodando o verificador numa extração do commit (`git archive HEAD` em `/tmp/b095/head`), e são de um arquivo que este brief não alterou, fora da autorização (lacuna 5). Nenhuma é dos arquivos deste brief.

Gate completo (`scripts/verificar.sh`, rodado antes da entrega; o `agente_entregar.sh` roda de novo e decide):

```
$ scripts/verificar.sh
ruff check: ok
ruff format: ok
mypy: ok
pytest: ok (1346 passed, 5 deselected in 68.16s (0:01:08))
rc=0
```

## 8. Manifesto

`logs/arquivos_095.txt`:

```
agente_nw/cli.py
agente_nw/manutencao/__init__.py
agente_nw/manutencao/reprocessamento.py
tests/test_reprocessamento.py
docs/docs/doc_095_dano_nos_dados_e_reprocessamento_2026-11-16.md
docs/docs/doc_079_auditoria_texto_por_inteiro_2026-11-08.md
docs/PLAN_agente_nw.md
```

`logs/commit_095.txt`:

```
feat(reprocessamento): medir-dano e reprocessar em cópia do banco (brief 095)

medir-dano conta, só lendo uma cópia (--banco), o que foi gravado pelo
critério antigo do texto cortado: itens acima dos cortes antigos, vetores,
cartões, ganchos e fatos de versão antiga, o que não tem registro de
cobertura e a fila de revisão pendente. Só contagens e versões.

reprocessar --etapa vetores|cartoes refaz a etapa num arquivo à parte
(simulação, o padrão) e conta o que mudaria; --confirmo grava no próprio
banco depois de uma cópia de segurança, recusado dentro de uma série e,
no banco real, sem a autorização da etapa no PLAN. Nada foi regravado.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

## Lacunas

| # | Lacuna | Destino | Impacto |
|---|---|---|---|
| 1 | Regravar no banco real, por etapa, depois de ver a simulação numa cópia recente: (a) vetores (resolve [089-2]) e (b) cartões (resolve [090-1]). Cada uma exige a linha `reprocessar <etapa>: autorizado por Sidarta em AAAA-MM-DD` no PLAN e `--confirmo` fora de série | decisão | quebra |
| 2 | Ganchos e qualificação não são refeitos: o `reprocessar` só conta os ganchos em assunto que mudaria, e a qualificação (`substancial`, `conversavel`) feita com os 300 caracteres antes do brief 090 continua como está. Refazer a qualificação seria uma terceira etapa (`--etapa qualificacao`) com a mesma forma das outras | backlog | degrada |
| 3 | Guardar ou não o texto bruto de rede social daqui para frente (análise na seção 5): ganho de reprocessar sem recoletar contra texto de terceiros em disco | decisão | degrada |
| 4 | As contagens vieram de uma cópia de 15/10 (`dados/agente.testeedy.db`), porque `dados/backups` está vazio e o `copiar-banco` só copia de backup. Para medir o banco de hoje: um backup do banco real, feito por Sidarta, e `medir-dano` numa cópia dele | pendência | degrada |
| 5 | O verificador da auditoria 079 tem 8 inconsistências que já estavam no HEAD, todas de `tests/test_evitar_e_fatos_inteiros.py` (198 linhas na seção 6, o arquivo tem 200; 7 ocorrências sem destino). A autorização de atualizar o 079 cobre só os arquivos que o próprio brief altera | dívida | nice |
| 6 | O `reprocessar` reconhece a série pela `SERIE_DENTRO_DO_CAFFEINATE`, a única variável que o `executar_serie.sh` exporta, e ele só a exporta quando o `caffeinate` existe. A trava continua bloqueando o `--confirmo` em qualquer sessão; uma variável própria da série, exportada sempre, exigiria um brief para o script | dívida | nice |
| 7 | A simulação de vetores na cópia parou no primeiro `/api/embed` da 11435 por tempo-limite, com o `bge-m3` sem carregar (mesmo sintoma do [094-1]); o banco dado não mudou. Rodar `agente_nw reprocessar --banco <cópia> --etapa vetores --simular` quando a 11435 atender o `bge-m3`, antes de decidir a lacuna 1 (a) | pendência | degrada |
