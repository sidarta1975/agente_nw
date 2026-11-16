# Brief 080 — Registrar as exceções ao "texto por inteiro" aprovadas por Sidarta

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Conjunto:** auditoria do texto por inteiro (briefs 080 a 083) — este é o primeiro e não depende dos outros
**Arquivos-alvo:** `docs/EXCECOES_TEXTO_INTEGRAL.md`, `docs/docs/doc_079_auditoria_texto_por_inteiro_2026-11-08.md` (seção 3: estado e decisão dos pontos aprovados; seção 6 e apêndice A: só o que o item 2.5 manda), `docs/docs/doc_080_registro_de_excecoes_2026-11-08.md` (relatório), `logs/commit_080.txt`, `logs/arquivos_080.txt`, `docs/PLAN_agente_nw.md`
**Seções a ler:** brief 079 (decisões 3.1 e 3.8), seção 3 do relatório 079 (cada ponto citado abaixo), seção 6 e apêndice A do relatório 079, seção 9 e seção 10 do `docs/docs/doc_086_executor_em_serie_2026-11-10.md`, `scripts/verificar_auditoria_texto.py`, `scripts/executar_serie.sh` e `tests/test_executar_serie.py` (do início ao fim, para o item 2.5)
**Modelo:** Sonnet
**Esforço:** médio
**Teste de aceite:** `python scripts/verificar_auditoria_texto.py` sobre o relatório 079 devolve 0 e o resumo mostra os pontos aprovados fora da lista de "aguardando"
**Depende de:** brief 079 executado (commit 700a43a e e45c9dd) e brief 086 entregue (commit e491463). O executor confere que `docs/EXCECOES_TEXTO_INTEGRAL.md` existe e está vazio; se não, para.
**Ordem em série:** antes de 081, 082, 083
**Data:** 2026-11-08 (v2, 2026-11-14: item 2.5 — Sidarta autorizou este brief a recertificar, na seção 6 e no apêndice A do relatório 079, os arquivos de código que o brief 086 criou)

---

## 1. Objetivo em uma frase

Gravar, no registro oficial, as exceções ao princípio do texto por inteiro que **Sidarta aprovou** em 2026-11-08 (e só elas), para que o verificador as reconheça e elas saiam da lista de pontos em aberto.

## 2. Decisões

**2.1. Este brief é o ato de Sidarta.** A regra do brief 079 (3.1 e 3.8) diz que só ele escreve no registro, "ou um brief dele". Este é esse brief: a aprovação foi dada por Sidarta no chat em 2026-11-08, ao aprovar a divisão em grupos proposta depois da auditoria. O executor **não aprova nada além do que está na tabela abaixo**; ponto que não está na tabela continua `AGUARDANDO DECISÃO DE SIDARTA`.

**2.2. Aprovados nesta data, cada um com o alcance exato (o que não está dito aqui não está aprovado):**

| Ponto | Alcance da aprovação |
|---|---|
| P-002 | deduplicação por hash só do título, antes de qualquer pedido de rede (evita 429) |
| P-005 | tetos de custo/bloqueio da coleta RSS (`leitor.py:246`) |
| P-008 | amostragem declarada para calibrar o limiar do agrupamento |
| P-009 | **só** o teto de 5 assuntos no menu; o teto de 10 candidatos fica em aberto (será medido) |
| P-011 | o corte que impede a redação de afirmar posição que a pessoa não declarou |
| P-015 | quanto da página é lido na rede social (rolagem limitada, por risco de bloqueio) |
| P-016 | 10 publicações recentes lidas por contato sob demanda |
| P-017 | 8 imagens descritas e o filtro por largura |
| P-018 | a imagem é descrita em poucas linhas e não guardada (AGENTS) |
| P-020 | o recorte de 3-4 linhas na busca de identidade, **com a dúvida sempre indo para Sidarta** |
| P-021 | cinco candidatas por pergunta; o teto de 200 na deduplicação fica em aberto |
| P-022 | `blocos_por_mes` (meses de conversa lidos) |
| P-023 | últimas 10 trocas no prompt |
| P-024 | mensagens sem texto (mídia) recusadas de forma explícita na exportação do WhatsApp |
| P-033 | **só o mecanismo** `cortar_por_tamanho` (sacrificar blocos quando o prompt estoura); a conferência do estimador fica para o brief 082 |
| P-038 | formulário de temas com 5 campos |
| P-043 | lotes com retomada da fila de extração (paginação) |
| P-044 | importação da agenda do Google (CSV) |
| P-045 | busca na lista pelo primeiro nome, com confirmação humana |

**2.3. Pedidos laterais que acompanham as aprovações** (não são condição da exceção, mas viram backlog no PLAN): P-005 e P-015 — a tela deve avisar quando a coleta/leitura parou por teto; P-018 — descrição mais longa quando a imagem tem texto legível; P-020 — a tela de confirmação mostra o cabeçalho inteiro da rede; P-021 — olhar o teto de 200 da deduplicação; P-009 — medir quantos dos 10 candidatos passam o gate.

**2.4. O registro guarda o valor aprovado e a condição que mantém cada exceção válida (revisão v2, a partir dos relatórios do pandora_96 e do advogada_parceira_free).** A tabela de `docs/EXCECOES_TEXTO_INTEGRAL.md` tem as colunas `Ponto | Arquivo:função | O que é cortado | Valor aprovado | Condição que mantém a exceção válida | Justificativa aprovada | Aprovado por Sidarta em`. *Valor aprovado* é o número ou a regra que existe hoje no código ou na configuração (copiado de lá, com arquivo e linha). *Condição* é, por regra geral: "vale enquanto o valor acima for o do código/configuração e o corte continuar servindo só ao fim descrito". Condições específicas: P-011 vale enquanto a redação não receber o texto para inferir posição da pessoa; P-018 vale enquanto a imagem for descrita e descartada; P-020 vale enquanto a dúvida de identidade for sempre para Sidarta; P-009 vale só para o menu de 5 (o teto de 10 candidatos não está aprovado); P-021 vale só para as cinco candidatas (o teto de 200 não está aprovado); P-033 vale só para o mecanismo de sacrifício de blocos, e depende do brief 082 conferir o estimador. *Razão: uma exceção aprovada para um número deixa de valer se alguém muda o número sem perguntar.*

**2.5. Recertificação dos arquivos de código que o brief 086 criou (autorização de Sidarta, 2026-11-14).** O verificador da auditoria 079 é um retrato de um instante: o brief 086 criou dois arquivos de código e isso bastou para ele devolver 1. Sidarta autorizou, no chat em 2026-11-14, **este brief** a atualizar também a seção 6 e o apêndice A do relatório 079, só para incluir esses arquivos. O alcance é exatamente este, e nada além:

a) **Seção 6 (certificação por arquivo).** Acrescentar uma linha para `scripts/executar_serie.sh` e uma para `tests/test_executar_serie.py`, na ordem do caminho, com `Linhas lidas/total` igual ao `wc -l` do arquivo (lidas = total; leitura parcial só vale como `NÃO CONFERIDO`) e evidência de uma linha escrita a partir da leitura do arquivo inteiro. Corrigir, no mesmo passo, as duas contagens defasadas de arquivos que o 086 alterou: `scripts/agente_entregar.sh` e `tests/test_guarda_comando.py` — só a coluna `Linhas lidas/total`, pelo `wc -l` de hoje; o resultado, a evidência e a coluna `Ponto` dessas duas linhas **não mudam**.

b) **Apêndice A (varredura mecânica).** Dar destino às três ocorrências novas, todas em `scripts/executar_serie.sh` (hoje: l. 107, `sys.argv[1:]`, e l. 121 e 123, `.split()[0]` sobre o rótulo do cabeçalho do brief), encaixando cada `arquivo:linha` no grupo `descartada:` que já existe e corresponde à razão — nenhum grupo novo — e atualizando a contagem do grupo e o total de ocorrências do texto do apêndice. Confira as linhas pela saída do próprio verificador na hora de executar, não por este brief: a numeração pode ter mudado.

c) **Texto corrido.** Atualizar os números do universo (317 → 319 arquivos, 1.272 → 1.275 ocorrências, ou o que o verificador disser) onde eles aparecem como **narrativa** nas seções 1, 2 e 6 e no apêndice A. Os blocos de saída de comando colados no relatório 079 (o `RELATÓRIO FINAL`, a mensagem do commit, a saída de 2026-11-08) são prova de uma execução passada e **não são reescritos**; a saída nova vai colada no relatório deste brief.

d) **Nenhum ponto novo.** Esta autorização não cria ponto nem aprova exceção. Se a leitura de um dos dois arquivos mostrar que ele analisa só parte de um texto de conteúdo — isto é, se a linha dele não puder ser `CERTIFICADO` —, o executor **para**, não inventa ponto nem marca `NÃO ANALÍTICO`, e registra em "Para você" que o arquivo precisa de um ponto, que só Sidarta decide. A seção 9 do `doc_086` já examinou os três cortes do script (rótulo de cabeçalho e `argv`, nenhum deles texto de conteúdo) e serve de ponto de partida, não de atalho: leia os dois arquivos.

e) **O conserto de fundo continua sendo o brief 093.** Este item resolve o retrato de hoje. Enquanto o verificador não entrar no gate de outra forma (brief 093), todo brief que criar arquivo de código repete o problema. Isso é lacuna do 093, não deste brief.

## 3. Escopo (arquivos)

| Arquivo | Criar / alterar | O que muda |
|---|---|---|
| `docs/EXCECOES_TEXTO_INTEGRAL.md` | alterar | Troca o cabeçalho da tabela pelas sete colunas de 2.4 e grava uma linha por ponto da tabela 2.2, com "Aprovado por Sidarta em 2026-11-08". "O que é cortado" vem da seção 3 do relatório 079 (copiar, não reescrever); "Justificativa aprovada" é a coluna de alcance da tabela 2.2 acrescida da razão da "Proposta do executor" do relatório. |
| `docs/docs/doc_079_..._2026-11-08.md` | alterar | Nos 19 pontos acima: estado `EXCEÇÃO APROVADA` e, na linha de decisão, `Decisão de Sidarta: aprovar exceção (2026-11-08), alcance conforme o registro`. Atualizar os números da seção 1 (pontos em aberto: 45 − 19 = 26). Mais o que o item 2.5 manda na seção 6 (duas linhas novas, duas contagens de linha corrigidas) e no apêndice A (três ocorrências com destino, contagens do grupo e do total). Nenhuma outra linha do relatório muda. |
| `docs/docs/doc_080_registro_de_excecoes_2026-11-08.md` | criar | Relatório. |
| `logs/commit_080.txt`, `logs/arquivos_080.txt`, `docs/PLAN_agente_nw.md` | criar/alterar | Manifesto e linhas do PLAN (inclui os pedidos laterais de 2.3 como backlog). |

## 4. Testes

Não há código novo. O teste é o verificador existente, rodado sobre o relatório alterado. Se o verificador rejeitar a coerência (por exemplo, número de pontos em aberto diferente do que a seção 1 diz), corrigir o **relatório**, não o verificador. O verificador tem de devolver **0** com as sete inconsistências do item 2.5 zeradas: nenhum "arquivo do universo ausente da tabela de certificação", nenhuma contagem de linha defasada e nenhuma "ocorrência sem destino no relatório". A saída crua, antes e depois, vai colada no relatório deste brief.

## 5. Fora de escopo

Qualquer correção de código (briefs 081 a 083). Aprovar outro ponto além dos 19 (só Sidarta, em nova decisão). Criar ponto para os arquivos do item 2.5 (2.5.d: o executor para). Mexer em `scripts/verificar_auditoria_texto.py` ou colocá-lo no gate (brief 093). Qualquer outra linha da seção 6 ou do apêndice A além das que o item 2.5 nomeia.

## 6. Passos de execução

1. Conferir "Depende de".
2. Rodar o verificador e guardar a saída de partida (hoje: código 1, sete inconsistências).
3. Gravar as 19 linhas no registro e atualizar os 19 pontos no relatório 079.
4. Ler `scripts/executar_serie.sh` e `tests/test_executar_serie.py` do início ao fim e fazer o que o item 2.5 manda na seção 6 e no apêndice A.
5. Rodar o verificador e colar a saída (esperado: código 0, 319 arquivos, 26 pontos aguardando, nenhuma inconsistência).
6. Relatório, manifesto e PLAN; `scripts/agente_entregar.sh 080`.
7. Terminar com as três linhas do `/executar`; "Para você" só se algo ficou fora da tabela 2.2 ou se o item 2.5.d fez parar.

## 7. Critérios de aceite

1. O registro tem exatamente 19 linhas, uma por ponto da tabela 2.2, todas com "Aprovado por Sidarta em 2026-11-08", "Valor aprovado" (com arquivo e linha) e "Condição" preenchidos.
2. O verificador devolve 0 e imprime `26 ponto(s) aguardando decisão`, sem nenhuma inconsistência.
3. A seção 6 tem linha para `scripts/executar_serie.sh` e `tests/test_executar_serie.py`, com a contagem de linhas batendo com o disco, e as contagens de `scripts/agente_entregar.sh` e `tests/test_guarda_comando.py` batem também.
4. As três ocorrências de `scripts/executar_serie.sh` aparecem no apêndice A, em grupo `descartada:` que já existia, e nenhum ponto novo foi criado (`grep -c "^#### P-"` no relatório continua dando 45).
5. `git diff --stat` mostra só os arquivos do escopo.
6. O gate do `agente_entregar.sh` fica verde.
