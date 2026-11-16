# DOC 089: vetores calculados com o texto inteiro

**Brief:** `docs/briefs/brief_089_vetores_com_o_texto_inteiro_2026-11-08.md`
**Data:** 2026-11-16
**Depende de:** 082 (concluído, `badf676`) e 088 (concluído, `28085a0`). Conferido no `git log` antes de começar.

## 1. O que mudou

Os três vetores que decidem o assunto de um item, o perfil de um contato e o tema de um interesse passaram a ser calculados com o texto inteiro, por `embeddar_em_partes` (brief 088). Não há corte novo.

- **(a) Vetor do item** (`agrupamento/agrupador.py`). O texto é o título mais o texto inteiro (`texto_do_item`), sem os 2.000 caracteres de antes.
  - Item que cabia no corte antigo produz o mesmo texto e, portanto, o mesmo vetor.
  - Item que não cabe numa chamada vira a média ponderada das partes.
  - Uma falha numa parte (`ValueError`, que inclui `FalhaJanelaEmbedding`) deixa o item sem vetor e sem assunto, nunca com vetor parcial. O agrupamento segue com os outros itens. O resumo conta a falha em `itens_sem_vetor`, que o `agrupar` imprime, e o item é tentado de novo no agrupamento seguinte.
- **(b) Centróide do contato** (`database/queries/perfis.py::calcular_centroide_do_contato`). Cada fato entra inteiro, e a ficha também. A constante `_TRECHO_DO_FATO_NO_CENTROIDE = 500` saiu. Uma falha numa parte sobe ao chamador, como antes.
- **(c) Vetor do tema** (`perfil/configurador.py`). O texto é `texto_do_tema(nome, descricao, sinonimos)`: nome, descrição e sinônimos, quando existirem, juntos num texto só.
  - Com descrição e sem sinônimos, o texto é o `"nome: descricao"` de antes, caractere por caractere.
  - O mesmo texto passou a valer nos outros dois lugares que gravam vetor de tema, `console/app.py:990` e `perfil/inferencia.py:121` (ver seção 5).
- **Versão do critério** (`nucleo/llm.py:54`, `VERSAO_CRITERIO_VETOR = "2026-11-16-1"`). O mecanismo é o do brief 066.
  - `ClienteOllama.modelo_embedding` passou a devolver `identificador_do_vetor(modelo)`, que é `bge-m3#criterio-2026-11-16-1`. Os vetores de antes gravaram só `bge-m3`.
  - Quem lê `vetor_tema`, `vetor_assunto` ou `vetor_perfil` pelo identificador atual não vê o vetor de critério antigo: ele é tratado como ausente.
  - A linha antiga continua no banco, intacta, e é lida normalmente pelo identificador dela (é o "válido para leitura" do item 2.3). O `comparar-vetores` usa os centróides de qualquer versão.
  - **Nenhum vetor existente foi regravado.**
- **`agente_nw comparar-vetores --amostra N --banco <cópia>`** (`cli.py`, lógica em `nucleo/agrupamento/comparar_vetores.py`). É somente leitura, com os dois parâmetros obrigatórios.
  - Recusa o banco real: compara o caminho resolvido com o de `config`.
  - Abre o arquivo em `mode=ro` e confere o SHA-256 do arquivo antes e depois.
  - O cliente de embedding é um `ClienteOllama` ligado a um banco em memória, porque `llm()` abriria e migraria o banco real.
  - Para os N itens mais recentes com vetor gravado, compara o vetor gravado (antigo) com o do texto inteiro (novo) pela mesma regra do agrupador, com os limiares de hoje. A regra exata está no docstring do módulo.
  - A saída tem só números: itens que trocariam de assunto, assuntos que se fundiriam e que se separariam, republicados que mudariam de decisão, o cosseno entre o vetor antigo e o novo, e quantos vetores de cada tabela são do critério anterior.
  - Nenhum limiar mudou.
- **Sem comando de gravação.** O item 2.5 só o regula "se existir"; a regravação é do brief 095.
- **`calibracao.py::_trecho` ficou como estava.** Não é entrada de embedding: é o trecho que vai ao **prompt** de `prerotular_calibracao`, na `calibracao.py:114-115` (`prerotular_calibracao.construir_prompt(par.item_a.titulo, _trecho(par.item_a), ...)`). Esse corte é a exceção aprovada P-008, e o brief só manda mexer nele "se for entrada de embedding".

## 2. Comparação numa cópia do banco (aceite 2)

O `agente_nw copiar-banco` não tem de onde copiar: `dados/backups/` está vazio, como no brief 087.

```
$ .venv/bin/agente_nw copiar-banco /tmp/b089/copia_oficial.db
FALHA: nenhum backup encontrado em /Users/sidarta48/github/agente_nw/dados/backups
rc=1
```

Usei a cópia de desenvolvimento mais recente que já existe, `dados/agente.testeedy.db` (15/10). Ela foi copiada para `/tmp/b089/copia.db`, e só a cópia recebeu as migrações até a 021, porque a de outubro não tinha a coluna `modelo_embedding` (migração 019). O banco real não foi aberto. Na cópia há 570 itens, 511 com vetor, e 424 com texto acima de 2.000 caracteres.

O porteiro foi consultado antes:

```
$ porteiro cabe bge-m3 --porta 11435
Cabe: bge-m3:latest precisa de cerca de 6,1 GB.
Ficaria com 20,3 GB de 26,0 GB e 2 de 2 modelos.
rc=0
```

A saída do comando, com todos os itens que têm vetor:

```
$ shasum -a 256 /tmp/b089/copia.db
f3224714f2f1e29dadeac2fb793a469ebb22cea5455ebee3ca40d8f2fb8e0b3d  /tmp/b089/copia.db
$ .venv/bin/agente_nw comparar-vetores --amostra 511 --banco /tmp/b089/copia.db
Banco: /tmp/b089/copia.db
sha256 antes: f3224714f2f1e29dadeac2fb793a469ebb22cea5455ebee3ca40d8f2fb8e0b3d
Itens na amostra: 511
Itens lidos em partes: 1
Itens com o mesmo vetor de antes: 131
Itens sem vetor novo (falha numa parte): 0
Cosseno entre o vetor antigo e o novo: menor 0.8181, mediana 0.9845
Itens que trocariam de assunto: 0
Assuntos que se fundiriam: 0
Assuntos que se separariam: 0
Itens republicados (vetor antigo): 25
Republicados que deixariam de ser: 4
Itens que passariam a ser republicação: 0
vetor_tema: 0 de 0 do critério anterior (ausentes até uma regravação autorizada)
vetor_assunto: 413 de 413 do critério anterior (ausentes até uma regravação autorizada)
vetor_perfil: 5 de 5 do critério anterior (ausentes até uma regravação autorizada)
sha256 depois: f3224714f2f1e29dadeac2fb793a469ebb22cea5455ebee3ca40d8f2fb8e0b3d
rc=0
$ shasum -a 256 /tmp/b089/copia.db
f3224714f2f1e29dadeac2fb793a469ebb22cea5455ebee3ca40d8f2fb8e0b3d  /tmp/b089/copia.db
```

A primeira rodada, com `--amostra 100`, deu o mesmo hash antes e depois, 0 trocas de assunto e 4 dos 8 republicados deixando de ser. O arquivo do banco não mudou. A abertura em `mode=ro` de um banco em modo WAL cria os arquivos `-shm` (32 KB) e `-wal` (0 byte) ao lado dele; o conteúdo do banco fica intocado.

Leitura dos números:

- **O que muda.** 380 dos 511 vetores mudam, mas pouco: a mediana do cosseno entre o vetor antigo e o novo é 0,98 e o menor é 0,82. Nenhum item trocaria de assunto. 4 dos 25 republicados deixariam de ser republicação.
- **O que a contagem não mede.** O centróide de um assunto inclui o vetor antigo do próprio item, e a maioria dos assuntos tem um item só. Por isso "trocariam de assunto" é um piso (Lacuna 4).
- **O que acontece no banco depois deste commit.** Todos os vetores de assunto (413 de 413) e de perfil (5 de 5) da cópia são do critério anterior. Até uma regravação autorizada, eles são **ausentes** para o produto, como o item 2.3 manda:
  - o agrupamento não vincula item novo a assunto antigo e abre assunto novo;
  - qualificação e menu deixam de ver os assuntos antigos;
  - os temas do usuário ficam sem vetor até serem gravados de novo.

  O centróide do contato se refaz a cada consulta, e o tema volta a ter vetor quando é inferido de novo. Ver Lacuna 2.

## 3. Algum texto é analisado só em parte? (AGENTS §4), por ponto tocado

| Ponto | Resposta | Prova |
|---|---|---|
| vetor do item (`agrupador.py:99`) | **Não.** Título e texto inteiro, em uma ou mais partes. Uma parte que falha deixa o item sem vetor. | `test_marcador_no_ultimo_caractere_de_item_de_20_mil_chega_ao_embedding`; `test_item_maior_que_uma_chamada_e_embeddado_em_partes_que_cobrem_tudo` (100.000 caracteres, a última chamada termina no marcador); `test_falha_numa_parte_deixa_o_item_sem_vetor_e_o_agrupamento_segue` |
| centróide do contato (`perfis.py:633`, `:639`) | **Sim, na contagem; não, no texto.** Cada fato entra inteiro, e a ficha também. Mas só entram os **20 fatos mais recentes** (`_MAXIMO_FATOS_NO_CENTROIDE`, `perfis.py:614`), a parte de classe C do P-025, que este brief não mudou (2.2b fala só do texto de cada fato) e que **não tem aprovação registrada**. Ver Lacuna 1. | `test_marcador_no_ultimo_caractere_de_fato_de_20_mil_chega_ao_centroide`; `test_falha_numa_parte_do_centroide_nao_devolve_vetor_parcial` |
| vetor do tema (`configurador.py:40`, `console/app.py:990`, `inferencia.py:121`) | **Não.** Nome, descrição e sinônimos, inteiros. | `test_vetor_do_tema_inclui_nome_descricao_e_sinonimos` |
| `comparar-vetores` | **Não, por item.** A amostra é o número de itens que Sidarta pede em `--amostra`, declarado na saída, e cada item vai inteiro ao embedding. | `test_comparar_vetores_nao_escreve_no_banco` (o item de 63.000 caracteres é lido em partes) |
| `calibracao.py::_trecho` (não tocado) | **Sim, 2.000 caracteres no prompt de `prerotular_calibracao`**, com a exceção aprovada P-008 (registro em `docs/EXCECOES_TEXTO_INTEGRAL.md`). Não é entrada de embedding. | `calibracao.py:107-108` e `:114-115` |

## 4. Testes do brief (seção 4), um por um

| # | Teste do brief | Teste(s) em `tests/test_vetores_texto_inteiro.py` |
|---|---|---|
| 1 | texto curto, vetor idêntico | `test_item_curto_e_embeddado_com_o_mesmo_texto_e_o_mesmo_vetor_de_antes` (texto enviado igual a `f"{titulo}\n\n{texto}"` e vetor gravado igual ao da chamada única); `test_centroide_do_contato_com_fatos_curtos_usa_o_mesmo_texto_de_antes`; `test_tema_sem_sinonimos_continua_com_o_texto_de_antes` |
| 2 | marcador no último caractere de 20.000 (agrupador e centróide) | `test_marcador_no_ultimo_caractere_de_item_de_20_mil_chega_ao_embedding`, `test_marcador_no_ultimo_caractere_de_fato_de_20_mil_chega_ao_centroide`, `test_item_maior_que_uma_chamada_e_embeddado_em_partes_que_cobrem_tudo` |
| 3 | tema com descrição e sinônimos | `test_vetor_do_tema_inclui_nome_descricao_e_sinonimos`, `test_texto_do_tema_sem_descricao_e_com_sinonimos` |
| 4 | versão antiga ausente onde o 066 já faz isso | `test_criterio_novo_tem_versao_propria_no_identificador_do_vetor` (`ClienteOllama` real), `test_vetor_de_versao_antiga_e_ausente_para_quem_pede_o_atual_e_a_linha_fica` (tema, assunto e perfil), `test_agrupador_nao_vincula_item_a_centroide_de_versao_antiga_nem_o_regrava` |
| 5 | `comparar-vetores` não escreve (hash) e recusa o banco real | `test_comparar_vetores_nao_escreve_no_banco`, `test_comparar_vetores_recusa_o_caminho_do_banco_real` (o caminho com `..` é resolvido), `test_comparar_vetores_exige_o_caminho_do_banco`, `test_comparacao_conta_trocas_fusoes_separacoes_e_republicacoes` (contagens com vetores escolhidos à mão) |
| 6 | falha numa parte invalida o vetor | `test_falha_numa_parte_deixa_o_item_sem_vetor_e_o_agrupamento_segue`, `test_falha_numa_parte_do_centroide_nao_devolve_vetor_parcial` |

Antes do código, a coleta falhou por falta do módulo novo (`ImportError: cannot import name 'comparar_vetores'`). Depois do código:

```
$ .venv/bin/pytest tests/test_vetores_texto_inteiro.py -q
.................                                                        [100%]
17 passed in 2.02s
```

## 5. Escolhas do executor dentro do brief

- **Onde mora a versão.** Ela foi junto do modelo no `modelo_embedding` que cada vetor já grava, e não numa coluna nova. É o mecanismo do brief 066, que não precisa de migração, e as consultas que filtram por modelo passaram a filtrar também por critério sem mudar nenhuma delas. `vetor_item` não tem essa coluna, porque o 066 não a versionou, e por isso o teste 4 cobre "onde o brief 066 já faz isso": tema, assunto e perfil (Lacuna 3).
- **Fora dos arquivos-alvo, por consequência direta e mínima:**
  - `console/app.py:990` e `perfil/inferencia.py:121`: uma linha cada. Os dois gravam vetor de tema com o identificador do critério novo e precisam do mesmo texto, senão a versão seria falsa. O `console/app.py:990` é o "onde mais aparece" do próprio P-037.
  - `tests/test_proveniencia.py:266-268`: o teste do 066 conferia que o valor gravado era exatamente o nome do modelo (`bge-m3`). Agora confere `identificador_do_vetor(modelo)`. A outra asserção do mesmo teste (`== cliente.modelo_embedding`) não mudou. Nenhuma asserção de comportamento foi afrouxada.
- **Falha de embedding no agrupador.** Uma falha por conteúdo (`ValueError`) deixa o item sem vetor e o laço segue. Falha de transporte (`httpx`) continua subindo, como antes, para um Ollama fora do ar não ser contado item por item.
- **Relatório 079** (autorização de 2026-11-16: seção 6 e apêndice A dos arquivos tocados e criados, sem ponto novo):
  - P-001, P-025 e P-037 em `CORRIGIDO (brief 089)`, com a decisão anotada. A do P-025 registra que o teto de 20 fatos não mudou.
  - As citações `arquivo:linha` dos oito arquivos alterados foram renumeradas pela correspondência entre `HEAD` e o disco (`difflib`, script em `/tmp/b089/`, fora do repositório). As linhas que deixaram de existir foram apontadas à mão para a equivalente: `agrupador.py:88`/`:89` → `:99`, `perfis.py:614`/`:629`/`:630` → `:633`, `configurador.py:29` → `:40`, `console/app.py:989` → `:990`.
  - Seção 6: as oito linhas reescritas (`agrupador.py` e `configurador.py` passaram a `CERTIFICADO`) e as duas novas incluídas.
  - Apêndice A: grupo "Brief 089 (sem ponto novo)" com 13 linhas, todas descartadas com a razão.

## RELATÓRIO FINAL
- Brief executado: 089, vetores calculados com o texto inteiro.
- Arquivos criados:
  - `agente_nw/nucleo/agrupamento/comparar_vetores.py`: comparação em simulação, só leitura.
  - `tests/test_vetores_texto_inteiro.py`: 17 testes, seção 4 do brief.
  - Este relatório.
- Arquivos alterados (com resumo da mudança em uma linha cada):
  - `agente_nw/nucleo/llm.py`: `VERSAO_CRITERIO_VETOR`, `identificador_do_vetor`; `modelo_embedding` devolve modelo e critério.
  - `agente_nw/nucleo/agrupamento/agrupador.py`: `texto_do_item` sem corte, `embeddar_em_partes`, item sem vetor em falha (`itens_sem_vetor`).
  - `agente_nw/nucleo/database/queries/perfis.py`: centróide do contato com cada fato inteiro e a ficha por `embeddar_em_partes`; sai `_TRECHO_DO_FATO_NO_CENTROIDE`.
  - `agente_nw/perfil/configurador.py`: `texto_do_tema` (nome, descrição, sinônimos) e `embeddar_em_partes`.
  - `agente_nw/perfil/inferencia.py`: o vetor do tema inferido usa `texto_do_tema` (uma linha).
  - `agente_nw/console/app.py`: o vetor do tema editado usa `texto_do_tema` (uma linha).
  - `agente_nw/cli.py`: `comparar-vetores --amostra N --banco <cópia>`; `agrupar` imprime os itens sem vetor.
  - `tests/test_proveniencia.py`: o valor gravado esperado é `identificador_do_vetor(modelo)`.
  - `docs/docs/doc_079_auditoria_texto_por_inteiro_2026-11-08.md`: P-001, P-025 e P-037 em `CORRIGIDO (brief 089)`; seção 6 e apêndice A dos arquivos deste brief; citações deslocadas renumeradas.
  - `docs/PLAN_agente_nw.md`: Resumo e Done.
- Arquivos preservados literalmente na área afetada:
  - `config/` inteiro: `git diff -- config/` dá 0 linhas, nenhum limiar mudou;
  - `nucleo/texto_integral.py` e `embeddar_em_partes`;
  - `nucleo/agrupamento/calibracao.py` (`_trecho`, P-008);
  - `nucleo/database/queries/{assuntos,temas,itens,perfil_tema}.py`;
  - `nucleo/relevancia/*`;
  - `.claude/hooks/guarda_comando.py` (a liberação do `comparar-vetores` já vinha do brief 086, 2.10);
  - `tests/llm_falso.py`.
- Script de verificação (o gate, rodado pelo `scripts/agente_entregar.sh`; a saída dele fica em `logs/entregar_ultimo.txt`). Antes dele, rodei os mesmos passos à mão:

```
$ .venv/bin/ruff check . ; .venv/bin/ruff format --check . ; .venv/bin/mypy agente_nw
All checks passed!
301 files already formatted
Success: no issues found in 126 source files
$ .venv/bin/pytest -q
1231 passed, 5 deselected in 52.05s
$ git diff -- config/ | wc -l
       0
$ .venv/bin/python scripts/verificar_auditoria_texto.py
331 arquivos, 273 certificados, 51 cortam, 7 não analíticos, 0 não conferidos, 12 ponto(s) aguardando decisão de Sidarta
1563 ocorrência(s) da varredura mecânica, todas com destino no relatório
rc=0
```

- Comandos executados:
  - `pytest` (o arquivo do brief, `tests/test_proveniencia.py` e a suíte inteira), `ruff`, `mypy` e `verificar_auditoria_texto.py`, como acima;
  - `porteiro cabe bge-m3 --porta 11435` (código 0) e `porteiro status`;
  - `agente_nw copiar-banco` (falhou: sem backup);
  - `cp dados/agente.testeedy.db /tmp/b089/copia.db`, com as migrações aplicadas só nessa cópia;
  - `agente_nw comparar-vetores --amostra 100` e `--amostra 511 --banco /tmp/b089/copia.db`, com `shasum -a 256` antes e depois;
  - scripts em `/tmp/b089/` para renumerar o relatório 079;
  - `scripts/agente_entregar.sh 089`.

  Nenhum comando tocou `dados/agente.db`.
- Manifesto do commit: `logs/commit_089.txt` e `logs/arquivos_089.txt` (conteúdo no commit; depois da entrega, `logs/entregue_089_*.txt`).
- Pendências e decisões que ficaram abertas: ver Lacunas.
- Resumo, Doing, Backlog e Done do `docs/PLAN_agente_nw.md` atualizados: sim. Doing continua "(nenhum)", e o Backlog recebe as lacunas pelo `agente_lacunas.py`.

Para você: ver as contagens da comparação e decidir se autoriza regravar os vetores.

## Lacunas

| # | Lacuna | Destino | Impacto |
|---|---|---|---|
| 1 | O centróide do contato usa só os 20 fatos mais recentes (`_MAXIMO_FATOS_NO_CENTROIDE`, `perfis.py:614`), a parte de classe C do P-025. O brief 089 mandou cada texto inteiro e não falou do número de fatos, e esse teto não tem linha em `docs/EXCECOES_TEXTO_INTEGRAL.md`: aprovar a exceção ou mandar corrigir é decisão sua | decisão | degrada |
| 2 | Com a versão nova do critério, todo vetor de assunto, tema e perfil gravado antes deste brief é ausente para o produto até uma regravação autorizada (item 2.3). Na cópia foram 413 de 413 assuntos e 5 de 5 perfis. Até lá, o agrupamento abre assunto novo em vez de vincular a um antigo, a qualificação e o menu não veem os assuntos antigos, e os temas do usuário ficam sem vetor até serem inferidos de novo. A regravação é do brief 095 e depende da sua autorização | decisão | quebra |
| 3 | `vetor_item` não guarda modelo nem critério (o brief 066 não a versionou), então o vetor de item do critério antigo não se distingue do novo. Só o tamanho do texto (acima de 2.000 caracteres) indica quais itens mudariam, e o `medir-dano` do brief 095 não tem como contá-los pela versão | dívida | degrada |
| 4 | Na comparação, o centróide de cada assunto inclui o vetor antigo do próprio item, e a maioria dos assuntos da cópia tem um item só. Por isso "itens que trocariam de assunto" (0 na cópia) é um piso, e não uma estimativa sem viés | dívida | nice |
| 5 | A comparação rodou na cópia de desenvolvimento de 15/10 (`dados/agente.testeedy.db`), porque `copiar-banco` não tem backup de onde copiar (`dados/backups/` vazio). Os números do banco atual podem ser outros: vale um `agente_nw backup` seu e repetir `comparar-vetores` na cópia nova | pendência | nice |
| 6 | No relatório 079, a tabela da seção 7 (janela) ainda descreve o embedding do item como "título + 2.000 caracteres" e o do centróide como "20 × 500 caracteres". A autorização cobre só a seção 6, o apêndice A e o estado dos pontos | dívida | nice |
| 7 | Item cujo vetor falha por conteúdo fica sem assunto e é tentado de novo a cada agrupamento, sem registro além da contagem impressa: embedding não tem `fila_revisao` (brief 082). Um item que sempre falha ocupa um lugar no lote de 100 do `listar_sem_assunto` | backlog | nice |
