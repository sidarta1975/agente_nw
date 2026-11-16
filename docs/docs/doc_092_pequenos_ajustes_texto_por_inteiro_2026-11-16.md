# DOC 092: pequenos ajustes de texto por inteiro

**Brief:** `docs/briefs/brief_092_pequenos_ajustes_texto_integral_2026-11-08.md`
**Data:** 2026-11-16
**Depende de:** 083 e 087 (concluídos, `572ab02` e `1d03c48`; conferidos no `git log` e nos relatórios `doc_083_*` e `doc_087_*` antes de começar).

## 1. O que mudou

Cada item é uma correção mínima. Nenhum corte novo; os itens que mexem no que Sidarta vê só acrescentam aviso.

1. **P-032**: `validar_ganchos` acrescenta o motivo "o modelo devolveu N ganchos de notícia válidos; mostro 4" quando passa do teto. O que é descartado não mudou (ficam os 4 primeiros).
2. **P-035**: `pedido.extrair` monta a lista de contatos do prompt com **todo** contato cujo nome ou apelido tem uma palavra (3 letras ou mais, sem acento nem caixa) que aparece na frase, sem teto; os mais recentes completam até 50. O contato parecido com o nome do pedido deixa de ficar de fora por ser antigo.
3. **P-036**: `inferencia.aplicar_declaracoes` devolve a lista das frases sem padrão e aceita `avisar`. A frase aparece no `pedir` (CLI), nos avisos do pedido no console (`CanalWeb.pedido_entendido` grava; `_escrever` os mantém) e na tela "Eu" (parâmetro `ignorada` no redirecionamento). Frase ignorada continua sem efeito; só deixa de ser silenciosa.
4. **P-005 / P-015**: a coleta conta as buscas que nem abriu por teto (`termos_nao_buscados`) e as notícias de feed não examinadas por `maximo_itens_novos_por_feed` (`itens_fora_do_teto_do_feed`); `consulta.preparar` e `agente_nw coletar` avisam. A leitura de página de rede social marca `parou_no_teto_de_rolagens` quando a última rolagem ainda trouxe texto novo e conta os blocos que ficaram fora do teto de publicações; o resumo e o `avisar` dizem. A leitura de lista que para no teto de entradas (`truncada`, que morria no modelo) chega a `ResultadoAtualizacao.truncada`, aos avisos da localização e ao `agente_nw listas atualizar`.
5. **P-020**: o cabeçalho da pessoa na lista (`listas.parse_links`, antes 3 linhas) e na busca geral (`busca._filtrar_candidatos`, antes 4) traz **todas** as linhas úteis que a rede deu. A confirmação já mostrava `opcao.cabecalho` inteiro; o desempate por LLM passa a receber o cabeçalho inteiro também.
6. **P-044**: `agenda_google_csv.ler_contatos` sobe `csv.field_size_limit` durante a leitura e o devolve ao valor anterior. Campo de 300.000 caracteres lido sem erro.
7. **P-009**: `assunto_contato.medir_passagem_do_gate(conexao)` mede candidatos avaliados e quantos passam o gate. O número real **não foi obtido**: ver lacuna 1.
8. **P-021**: `localizacao.confirmar` avisa (parâmetro `avisar`) quando o contato já tem 200 fatos ou mais, isto é, quando a deduplicação olhou só os 200 mais recentes. **Condição de validade do brief 080, registrada aqui:** a aprovação de P-021 em `docs/EXCECOES_TEXTO_INTEGRAL.md` vale só para as cinco candidatas; o teto de 200 fatos **não está aprovado** e segue em aberto (lacuna 5). Sem o teto atingido, nada aparece.
9. **P-018**: não feito. O relatório 079 propõe descrição mais longa para imagem com texto legível, mas sem valor, e o brief diz que sem aprovação do dono o item vira lacuna "decisão" (lacuna 2).

Nenhum item estava `JÁ RESOLVIDO` pelos briefs 081 e 083.

Fora da lista de alvos, por consequência direta dos itens: `agente_nw/nucleo/modelos/pedido.py` (campo `frases_ignoradas`), `agente_nw/nucleo/fluxo.py`, `agente_nw/console/app.py` e `console/templates/eu.html` (mostrar a frase ignorada), `agente_nw/nucleo/confirmacao.py` e `fluxo.py` (passar `avisar` ao `confirmar`), `agente_nw/nucleo/modelos/redacao.py`, `agente_nw/nucleo/consulta.py`, `agente_nw/cli.py`, `agente_nw/nucleo/database/queries/assunto_contato.py`.

## 2. Tabela por ponto

| Ponto | Resolvido / já resolvido / lacuna | Teste |
|---|---|---|
| P-032 | Resolvido | `test_gancho_alem_do_teto_vira_motivo_com_a_conta`, `test_dentro_do_teto_nao_ha_motivo_de_excesso` |
| P-035 | Resolvido | `test_contato_de_nome_parecido_fora_dos_mais_recentes_chega_ao_prompt`, `test_todos_os_contatos_parecidos_chegam_ao_prompt_mesmo_passando_do_teto` |
| P-036 | Resolvido | `test_frase_sem_padrao_e_devolvida_e_avisada`, `test_frase_com_padrao_nao_e_ignorada` |
| P-005 | Resolvido (aviso) | `test_coleta_que_para_por_candidatos_suficientes_conta_as_buscas_que_ficaram_de_fora`, `test_coleta_que_rodou_todas_as_buscas_nao_avisa_de_teto` |
| P-015 | Resolvido (aviso) | `test_leitura_cuja_ultima_rolagem_ainda_trouxe_texto_novo_marca_o_teto`, `test_leitura_que_acabou_antes_do_teto_nao_marca`, `test_leitor_avisa_teto_de_rolagens_e_blocos_que_ficaram_de_fora`, `test_lista_truncada_chega_ao_resultado_da_atualizacao_com_o_motivo` |
| P-020 | Resolvido | `test_cabecalho_da_lista_traz_todas_as_linhas_da_rede`, `test_cabecalho_da_busca_geral_traz_todas_as_linhas_da_rede` |
| P-044 | Resolvido (`field_size_limit`; a parte "só o primeiro telefone/e-mail" não era do brief) | `test_agenda_com_campo_de_300000_caracteres_e_lida` |
| P-009 | Medição pronta; **número não obtido** (lacuna 1) | `test_medicao_do_gate_conta_candidatos_e_os_que_passaram`, `test_medicao_do_gate_sem_dados_devolve_zeros` |
| P-021 | Resolvido (aviso); teto de 200 segue sem aprovação | `test_contato_com_200_fatos_avisa_que_a_deduplicacao_olhou_so_os_200_mais_recentes`, `test_contato_com_poucos_fatos_nao_avisa` |
| P-018 | Lacuna (decisão) | — |

## 3. Algum texto é analisado só em parte? (AGENTS §4)

**Sim**, nos mesmos pontos que o brief não mandava abrir, todos com os tetos que já eram do código:

- **Coleta (P-005):** o teto de buscas, de candidatos, de tempo e de itens por feed continuam; o que muda é que ficam contados e avisados. Registro em `docs/EXCECOES_TEXTO_INTEGRAL.md` (P-005, aprovado em 2026-11-08).
- **Rede social (P-015):** 5 rolagens, 12 s no X, 2.000 entradas na lista; continuam, agora com aviso. Aprovado em 2026-11-08 (P-015).
- **Contatos no prompt do pedido (P-035):** o prompt ainda leva no máximo 50 contatos que **não** casam com a frase, mas os que casam entram todos. Ponto ainda `AGUARDANDO DECISÃO` no 079 (lacuna 3).
- **Ganchos (P-032):** continuam 4 de notícia; o descarte aparece. Ponto `AGUARDANDO DECISÃO` (lacuna 3).
- **Autodeclaração (P-036):** frase sem padrão continua sem efeito; aparece. Ponto `AGUARDANDO DECISÃO` (lacuna 3).
- **Dedução de fato de lista (P-021):** 200 fatos recentes, sem aprovação do teto; agora avisa quando é atingido.
- **Cabeçalho (P-020):** passou a **inteiro** nos dois lugares (lista e busca geral), sem teto de linhas.
- **Agenda (P-044):** o campo longo é lido inteiro; só o primeiro telefone/e-mail continua (aprovado 2026-11-08).

Nenhum texto do usuário nem de fonte externa é cortado de forma nova. Prova: `scripts/verificar_auditoria_texto.py` (seção 4) e os 19 testes.

## 4. Saída dos comandos

```
$ .venv/bin/pytest tests/test_pequenos_ajustes_texto.py -q
...................                                                      [100%]
19 passed in 0.89s

$ scripts/verificar.sh
ruff check: ok
ruff format: ok
mypy: ok
pytest: ok (1269 passed, 5 deselected in 51.68s)

$ .venv/bin/python scripts/verificar_auditoria_texto.py
335 arquivos, 279 certificados, 49 cortam, 7 não analíticos, 0 não conferidos, 6 ponto(s) aguardando decisão de Sidarta
1812 ocorrência(s) da varredura mecânica, todas com destino no relatório
(8 inconsistências, todas em tests/test_evitar_e_fatos_inteiros.py, do brief 091; ver lacuna 4)

$ .venv/bin/agente_nw copiar-banco /tmp/medicao092/copia.db
FALHA: nenhum backup encontrado em /Users/sidarta48/github/agente_nw/dados/backups
```

## 5. RELATÓRIO FINAL

- Brief executado: 092
- Arquivos criados: `tests/test_pequenos_ajustes_texto.py` (19 testes); este relatório.
- Arquivos alterados:
  - `agente_nw/nucleo/modelos/redacao.py`: motivo do excesso de ganchos.
  - `agente_nw/nucleo/pedido.py`: contatos do prompt por semelhança de nome; `frases_ignoradas` no resultado.
  - `agente_nw/nucleo/modelos/pedido.py`: campo `frases_ignoradas`.
  - `agente_nw/perfil/inferencia.py`: `aplicar_declaracoes` devolve e avisa a frase ignorada.
  - `agente_nw/nucleo/fluxo.py`: aviso da frase ignorada e do teto de 200 fatos nos avisos do pedido.
  - `agente_nw/console/app.py`, `agente_nw/console/templates/eu.html`: a tela "Eu" mostra a frase ignorada.
  - `agente_nw/coleta/rss/leitor.py`, `agente_nw/nucleo/consulta.py`: conta e aviso de teto da coleta.
  - `agente_nw/coleta/capturas/navegador.py`, `agente_nw/coleta/capturas/leitor.py`: teto de rolagens e blocos fora do teto de publicações.
  - `agente_nw/coleta/capturas/listas.py`, `agente_nw/nucleo/localizacao.py`: `truncada` até o aviso; cabeçalho inteiro; aviso dos 200 fatos.
  - `agente_nw/coleta/capturas/busca.py`: descrição inteira.
  - `agente_nw/nucleo/confirmacao.py`: passa `avisar` ao `confirmar`.
  - `agente_nw/perfil/agenda_google_csv.py`: `csv.field_size_limit`.
  - `agente_nw/nucleo/database/queries/assunto_contato.py`: `medir_passagem_do_gate`.
  - `agente_nw/cli.py`: avisos de teto da coleta e da lista.
  - `docs/docs/doc_079_*.md`: tabela de certificação (contagem de linhas dos 15 arquivos alterados e linha do teste novo) e apêndice A (linhas renumeradas pela correspondência entre a versão anterior e a atual, mais o bloco "Brief 092"), sem ponto novo e sem mudar o estado de nenhum ponto.
  - `docs/PLAN_agente_nw.md`: Resumo, Doing e Done.
- Arquivos preservados literalmente na área afetada: `nucleo/llm.py`, `config/`, os prompts, `docs/EXCECOES_TEXTO_INTEGRAL.md` (só Sidarta o edita), `cruzamento.py`, `candidatos.py`.
- Script de verificação: ver seção 4 (o `agente_entregar.sh` o roda de novo e decide).
- Comandos executados: `pytest` direcionado e da suíte, `scripts/verificar.sh`, `scripts/verificar_auditoria_texto.py`, `ruff`, `mypy`, `agente_nw copiar-banco` (falhou sem backup, ver acima). Nenhum comando tocou o Ollama (cliente falso), então o `porteiro` não foi consultado; nenhum tocou `agente.db` nem rede social.
- Manifesto do commit: `logs/commit_092.txt` e `logs/arquivos_092.txt` (conteúdo na entrega).
- Pendências e decisões que ficaram abertas: ver Lacunas.
- Resumo, Doing, Backlog e Done do `docs/PLAN_agente_nw.md` atualizados: sim (Backlog, Pendências, Dívidas e Decisões recebem as lacunas pelo `agente_entregar.sh`).

Para você: a medição do P-009 (lacuna 1) e a decisão do P-018 (lacuna 2).

## Lacunas

| # | Lacuna | Destino | Impacto |
|---|---|---|---|
| 1 | P-009: a medição "quantos dos candidatos passam o gate" está pronta (`assunto_contato.medir_passagem_do_gate`), mas o número não foi obtido: `agente_nw copiar-banco` não achou backup em `dados/backups` e o banco real não pode ser tocado aqui. Falta uma cópia feita por Sidarta para rodar a função nela e registrar o número | pendência | degrada |
| 2 | P-018: descrição de imagem com texto legível com limite maior. O relatório 079 propõe, mas não dá o valor, e sem aprovação o brief manda registrar como decisão. Qual limite (hoje "2 a 5 frases")? | decisão | nice |
| 3 | P-032, P-035 e P-036 continuam `AGUARDANDO DECISÃO DE SIDARTA` no relatório 079: o brief só autorizou a seção 6 e o apêndice A, e o executor não marca ponto. As três correções estão feitas; falta Sidarta registrar o estado de cada ponto | decisão | nice |
| 4 | O relatório 079 já tinha 8 inconsistências do brief 091 em `tests/test_evitar_e_fatos_inteiros.py` (a tabela diz 198 linhas, o arquivo tem 200, e 7 ocorrências de `truncar` deslocadas). Não são de arquivo deste brief, então não foram tocadas | dívida | nice |
| 5 | P-021: o teto de 200 fatos na deduplicação segue sem aprovação e só ganhou aviso. A correção de fundo é conferir por consulta ao conteúdo (`fatos.existe`-like) em vez de olhar os 200 mais recentes | backlog | degrada |
| 6 | Os avisos de teto dizem o que ficou de fora quando isso é contável (buscas, notícias do feed, blocos); para rolagem e lista não há como saber quantos itens a rede ainda tinha, e o aviso diz só que o teto bateu | nenhum | nice |
| 7 | P-035: a semelhança é por palavra inteira do nome ou apelido; um apelido que só o usuário usa e que não está no cadastro cai no complemento por recência, como antes | backlog | nice |
| 8 | Na tabela do relatório 079, a descrição das linhas de `pedido.py`, `inferencia.py`, `listas.py` e `agenda_google_csv.py` ainda fala dos cortes antigos (50 contatos, 3 linhas de cabeçalho); o brief autorizou só a contagem de linhas | dívida | nice |
