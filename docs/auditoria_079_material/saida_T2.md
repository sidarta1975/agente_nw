# Auditoria 079 — parte T01 (prefixo T2) — 53 arquivos de tests/

Todos os 53 arquivos foram lidos do início ao fim (linhas lidas = total do `wc -l`, 8.028). Nenhum arquivo de teste contém corte analítico próprio: todos `CERTIFICADO`. Nenhum ponto T/C/R/P/NA nos testes (por isso não há blocos `T2-nnn`). O valor está nos blocos abaixo da tabela.

## 1. Tabela de certificação

| Arquivo | Linhas lidas/total | Resultado | Evidência (uma linha) | Ponto |
|---|---|---|---|---|
| tests/test_console_editar_ficha.py | 227/227 | CERTIFICADO | Exercita rota de edição de ficha (campos curtos, E.164, línguas); LLM fake devolve `esquema()` vazio, sem texto de conteúdo analisado. | — |
| tests/test_console_eu.py | 176/176 | CERTIFICADO | Exercita tela /eu (temas por nível, contar, esquecer); LLM fake devolve `PedidoExtraido` fixo com 1 declaração curta. | — |
| tests/test_console_mensagem_base.py | 87/87 | CERTIFICADO | Exercita mensagem base/usei/comentário/nota no console; `redigir` é trocado por mock que devolve só a base já pronta (não exercita o prompt). | — |
| tests/test_console_menu.py | 212/212 | CERTIFICADO | Exercita telas de menu; cada contato tem 1 só assunto, então `itens_no_menu=5` e `candidatos_por_contato=10` do limiar nunca aparecem. | — |
| tests/test_console_novo_contato.py | 155/155 | CERTIFICADO | Exercita criação/listagem de contato; só infraestrutura e `_limiares()` compartilhado. | — |
| tests/test_console_preparar.py | 122/122 | CERTIFICADO | Exercita GET do formulário preparar (404 e meios); nenhum texto de conteúdo. | — |
| tests/test_console_redes_sociais.py | 222/222 | CERTIFICADO | Exercita CRUD de links de rede social (valida só prefixo http); sem análise de texto. | — |
| tests/test_console_sem_usuario.py | 141/141 | CERTIFICADO | Exercita /temas e /eu sem/com usuário; só infraestrutura. | — |
| tests/test_console_tela_unica.py | 273/273 | CERTIFICADO | Exercita tela única (pedir, pessoa, usei, corrigir); fluxo todo com `Cenario` (preparar/redigir/localizar mockados); texto do pedido curto ("Falar com a Marta sobre vela"). | — |
| tests/test_console_temas.py | 172/172 | CERTIFICADO | Exercita CRUD de temas; embedding fake constante `[0.1]+0*1023` — não prova que o embedding recebe descrição inteira. | — |
| tests/test_consulta_contato_queries.py | 105/105 | CERTIFICADO | Exercita queries de `consulta_contato`; documenta o parâmetro `limite` (ver bloco de cortes). | — |
| tests/test_consulta_preparar.py | 385/385 | CERTIFICADO | Exercita `consulta.preparar` com TODAS as etapas mockadas (rss, extrator, agrupador, qualificador, leitor, cruzamento); documenta o teto de termos de busca (ver bloco). | — |
| tests/test_contato_divergente.py | 269/269 | CERTIFICADO | Exercita divergência nome do pedido x contato; LLM fake devolve `PedidoExtraido` pronto (a extração do texto da frase nem roda). | — |
| tests/test_cruzamento_por_consulta.py | 328/328 | CERTIFICADO | Exercita cruzamento por consulta; ESCONDE: assuntos criados só com `titulo_gerado` (sem resumo/itens), centróides injetados e embedder fake decide por `"fato" in texto`. | — |
| tests/test_cruzamento.py | 240/240 | CERTIFICADO | Exercita `cruzar_contato`; assuntos só com título + centróide injetado; LLM fake devolve respostas prontas por posição. | — |
| tests/test_cruzar_por_que_nao_atribui.py | 62/62 | CERTIFICADO | Exercita prompt `cruzar_por_que` (regra de não atribuir posição); títulos curtos, não há texto de notícia no prompt. | — |
| tests/test_divisao.py | 37/37 | CERTIFICADO | Exercita `dividir` de agrupamento com vetores 2D; sem texto. | — |
| tests/test_evitar_implicito.py | 174/174 | CERTIFICADO | Exercita "não me interessa" virando evitar; casa só pelo TÍTULO do assunto ("Política fiscal..."); assunto sem corpo. | — |
| tests/test_extensao_backend.py | 207/207 | CERTIFICADO | Exercita `PaginaExtensao`; DOCUMENTA corte do texto da página em `maximo_caracteres_pagina` e `maximo_entradas`/`maximo` de imagens (ver bloco). | — |
| tests/test_extensao_manifest.py | 79/79 | CERTIFICADO | Confere manifest.json e background.js da extensão; só infraestrutura. | — |
| tests/test_extrator.py | 91/91 | CERTIFICADO | Teste `llm_real` do extrator com texto de ~230 caracteres (cabe em qualquer corte); não testa texto longo. | — |
| tests/test_fluxo.py | 353/353 | CERTIFICADO | Exercita fluxo/fila do pedido; `Cenario` troca preparar/redigir/localizar por mocks; `pessoas_recentes(conn, 20)` documenta limite (ver bloco); `num_ctx_redacao=8192` passado no Dependencias sem teste de tamanho do prompt. | — |
| tests/test_gancho_uso_base.py | 80/80 | CERTIFICADO | Exercita `gancho_uso` com a mensagem base (assunto_id NULL) e a migração; payload JSON de poucos bytes. | — |
| tests/test_gancho_uso.py | 91/91 | CERTIFICADO | Exercita `gancho_uso` (entregue/usado); `gancho_json` é `"{}"`. | — |
| tests/test_gate_lote_ordem.py | 224/224 | CERTIFICADO | Exercita casamento posicional do gate de relação ao objetivo; assuntos só com título ("Assunto A/B/C"); mock devolve lista de bool. | — |
| tests/test_gate_objetivo.py | 196/196 | CERTIFICADO | Exercita gate (brief 049); ESCONDE: o gate falso decide por `"OAB" in candidato`, e o candidato é só o TÍTULO do assunto (assunto sem corpo); confere no prompt objetivo, frase do pedido e ficha. | — |
| tests/test_gate_zera_menu.py | 165/165 | CERTIFICADO | Exercita gate que reprova tudo (menu zera); títulos curtos, mock devolve `relaciona=False` para N candidatos. | — |
| tests/test_google_news_consulta.py | 75/75 | CERTIFICADO | Exercita `selecionar_termos`/`gerar_consultas_da_consulta`; DOCUMENTA teto de termos (ver bloco). | — |
| tests/test_google_news.py | 47/47 | CERTIFICADO | Exercita `gerar_consultas` por tema; DOCUMENTA limite de 4 termos por tema (ver bloco). | — |
| tests/test_guarda_comando.py | 134/134 | CERTIFICADO | Testa hook `guarda_comando.py` (bloqueios de git/rm/agente_nw); só infraestrutura. | — |
| tests/test_historico_formatar.py | 130/130 | CERTIFICADO | Exercita `historico.formatar`/`historico_recente_para_prompt`; DOCUMENTA "padrão de cinco" consultas no histórico do prompt (ver bloco). | — |
| tests/test_imagens.py | 63/63 | CERTIFICADO | Exercita `imagens.descrever` com visão fake; descrição curta devolvida inteira (só `strip`); descrição de qualquer tema é mantida. | — |
| tests/test_importador.py | 86/86 | CERTIFICADO | Exercita importador CSV da agenda; nota da agenda ("Gosta de futebol e viagens.") curta, vai inteira à fila de extração. | — |
| tests/test_importar_temas.py | 67/67 | CERTIFICADO | Exercita `importar_temas` com embedder fake constante; sem texto longo. | — |
| tests/test_inferencia_declaracoes.py | 122/122 | CERTIFICADO | Exercita `aplicar_declaracoes` com frases curtas de 1 linha; LLM fake devolve descrição fixa. | — |
| tests/test_inferencia_temas.py | 158/158 | CERTIFICADO | Exercita `atualizar_temas_do_usuario`/decaimento (30/90/180 dias); termos de 1 palavra. | — |
| tests/test_inicio_lista_contatos.py | 101/101 | CERTIFICADO | Exercita tela inicial; DOCUMENTA `listar_para_inicio(conn,"",20)` (25 contatos, só 20 voltam) — apresentação (ver bloco). | — |
| tests/test_itens_agrupamento.py | 154/154 | CERTIFICADO | Exercita queries de `item`; texto do item fixado em "Texto de exemplo." (nunca testa corpo de notícia); `listar_sem_assunto(conn, 10)` documenta parâmetro de limite. | — |
| tests/test_lacunas.py | 31/31 | CERTIFICADO | Exercita `campos_faltando` do perfil; sem texto. | — |
| tests/test_lint_arquivo.py | 63/63 | CERTIFICADO | Testa hook `lint_arquivo.py`; só infraestrutura. | — |
| tests/test_listas_parse.py | 225/225 | CERTIFICADO | Exercita parsing de listas de rede social; DOCUMENTA `maximo_entradas` truncando a leitura (`truncada is True`) (ver bloco); página fake com `texto="x"*600`. | — |
| tests/test_listas_queries.py | 142/142 | CERTIFICADO | Exercita queries de listas e busca por nome; `buscar_parecidos(..., 0.8, 5)` documenta limite 5 (ver bloco). | — |
| tests/test_llm_api.py | 422/422 | CERTIFICADO | Exercita clientes Anthropic/Gemini/OpenAI com MockTransport; prompt de teste é a string "prompt"; afirma que `num_ctx` NÃO vai no corpo das APIs (ver bloco P). | — |
| tests/test_llm_fumaca.py | 87/87 | CERTIFICADO | Teste `llm_real` de fumaça (20 JSONs, 100 embeddings de frases curtas); não testa prompt grande nem corte do bge-m3. | — |
| tests/test_llm_log_chamadas.py | 96/96 | CERTIFICADO | Exercita log de tentativas do `ClienteOllama`; prompt = "prompt". | — |
| tests/test_llm_payload.py | 105/105 | CERTIFICADO | Exercita corpo da chamada Ollama (`think`, `format`, `num_ctx`, imagens); prompt "prompt de teste"; só confere que o `num_ctx` da tarefa vai no corpo, sem checar que o prompt cabe. | — |
| tests/test_llm_resiliente.py | 224/224 | CERTIFICADO | Exercita backoff 2/4/8/16 s, seed 42 e `num_predict`; prompt = "prompt". | — |
| tests/test_localizacao.py | 323/323 | CERTIFICADO | Exercita localização de pessoa nas redes; página fake `x*600`; LLM fake só desempata; `fatos.listar_recentes(conn, id, 10)` usado como leitura (ver bloco). | — |
| tests/test_markdown_gerar.py | 129/129 | CERTIFICADO | Exercita `markdown.gerar`; ESCONDE possível corte: cartão de 3 linhas ("linha 1\nlinha 2\nlinha 3") mas só afirma `"Cartão: linha 1" in texto` — passa com ou sem corte das linhas 2 e 3 (ver bloco). | — |
| tests/test_markdown_ler.py | 97/97 | CERTIFICADO | Exercita `ler_marcacoes` (usei/não serve e cinco motivos); blocos de 3 linhas, sem corte. | — |
| tests/test_mensagem_base_sem_noticia.py | 43/43 | CERTIFICADO | Exercita `redigir` sem assuntos (n_assuntos=0) com LLM falso que devolve a base; confere trechos fixos do prompt; reaproveita `tests.test_redacao_redigir` (fora desta lista). | — |
| tests/test_migracao_006.py | 15/15 | CERTIFICADO | Confere coluna `aderencia_consulta` após migrar; só infraestrutura. | — |
| tests/test_migracao_007.py | 16/16 | CERTIFICADO | Confere colunas da tabela `pedido` após migrar; só infraestrutura. | — |

Resumo: 53 arquivos; 53 CERTIFICADO; 0 CORTA; 0 NÃO ANALÍTICO; 0 NÃO CONFERIDO. 

## 2. Pontos encontrados

Nenhum ponto T/C/R/P/NA gerado por arquivo de teste (regra dos testes). As observações úteis estão nos dois blocos abaixo.

## Cortes de produção documentados por teste

Formato: `arquivo de teste:linha → arquivo de produção → o que o teste afirma`. O arquivo de produção é o inferido pelo import/uso no teste (não li o código de produção).

1. tests/test_extensao_backend.py:75-83 (`test_estado_corta_o_texto_em_maximo_de_caracteres`) → `agente_nw/coleta/capturas/extensao_backend.py` (`PaginaExtensao.estado`) → com texto de 5.000 caracteres e `maximo_caracteres_pagina=1000`, `len(texto) == 1000` e a tarefa enviada à extensão leva `"maximo": 1000`. Ou seja, o texto da página capturada é cortado em N caracteres (número configurável; 1.000 no teste, valor real vem de `ExtensaoLimiares`). Classe T (texto de página de rede social capturado).
2. tests/test_extensao_backend.py:62 → mesmo arquivo (`PaginaExtensao.rolar`) → a rolagem envia `maximo_entradas == 2000` à extensão (teto de entradas por leitura de lista).
3. tests/test_extensao_backend.py:169-181 → mesmo arquivo (`PaginaExtensao.imagens`) → a ação `imagens` é pedida com `maximo=8`, `largura_minima=250`: só 8 imagens por página entram na descrição (C).
4. tests/test_listas_parse.py:148-155 (`test_maximo_de_entradas_trunca_a_leitura`) → `agente_nw/coleta/capturas/listas.py` (`ler_lista`) → com `maximo_entradas=1` a leitura devolve 1 entrada e `resultado.truncada is True` (C: lista de conexões/seguidos cortada em `maximo_entradas`; 2000 nos limiares usados pelos testes).
5. tests/test_google_news.py:25-37 (`test_limite_de_quatro_termos_por_tema`) → `agente_nw/coleta/rss/google_news.py` (`gerar_consultas`) → tema com 5 sinônimos gera consulta só com `['"tema"','"s1"','"s2"','"s3"']`: o tema e 3 sinônimos; descarta os demais (C: 4 termos por tema).
6. tests/test_google_news_consulta.py:31-37 (`test_o_teto_corta_do_fim_da_lista_de_prioridade`) e :53-57 → `agente_nw/coleta/rss/google_news.py` (`selecionar_termos`) → com `maximo=4` os termos de menor prioridade ficam de fora (assunto, tags do contato, termos_busca, interessa, nesta ordem); "o teto padrão é quatro" (C sobre os termos de busca de notícia).
7. tests/test_consulta_preparar.py:296-302 → `agente_nw/nucleo/consulta.py` (`preparar`) → `len(termos) <= limiares.coleta.max_consultas_por_pedido` (teto de termos de busca passados ao `leitor_rss.coletar`; sem `fontes.yaml` só os feeds do contexto). Mesmo teto do item 6.
8. tests/test_historico_formatar.py:110-130 (`test_historico_recente_para_prompt_limita_no_padrao_de_cinco`) → `agente_nw/nucleo/historico.py` (`historico_recente_para_prompt`) + `agente_nw/nucleo/database/queries/consulta_contato.py` (`listar_por_perfil`) → de 7 consultas anteriores do contato só as 5 mais recentes (20, 19, 18, 17, 16/09) entram no texto do histórico; 15/09 e 14/09 ficam de fora (C sobre histórico que alimenta prompt).
9. tests/test_consulta_contato_queries.py:69-77 → `agente_nw/nucleo/database/queries/consulta_contato.py` (`listar_por_perfil`) → com `limite=3` de 5 registros voltam os 3 mais recentes (mesma base do item 8; o teste não afirma o valor padrão).
10. tests/test_fluxo.py:351-353 → `agente_nw/nucleo/database/queries/pedidos.py` (`pessoas_recentes`) → chamada com limite 20 (lista de pessoas recentes da tela; provável apresentação).
11. tests/test_inicio_lista_contatos.py:37-55 → `agente_nw/nucleo/database/queries/perfis.py` (`listar_para_inicio`) → com 25 contatos e limite 20 voltam só 20 (os recentes primeiro, depois alfabética). Provável apresentação da tela inicial, mas a mesma consulta pode ser usada pela busca por nome (a lista de contatos candidatos ao pedido) — vale conferir o uso em produção.
12. tests/test_itens_agrupamento.py:64 → `agente_nw/nucleo/database/queries/itens.py` (`listar_sem_assunto`) → chamada com limite 10 (o teste não afirma corte, só passa o parâmetro; mostra que a fila de itens a agrupar tem teto por chamada).
13. tests/test_listas_queries.py:136-142 → `agente_nw/nucleo/database/queries/listas.py` (`buscar_parecidos(conn, rede, nome, 0.8, 5)`) → limiar 0,8 e teto 5 opções (C sobre candidatos de localização de pessoa; afirma só resultados com 1 ou 0 itens).
14. tests/test_localizacao.py:217,223 → `agente_nw/nucleo/database/queries/fatos.py` (`listar_recentes(conn, perfil_id, 10)`) → o teste lê "recentes" com limite 10 (não afirma corte; indica que existe leitura de fatos recentes com teto).
15. tests/test_llm_payload.py:47 / tests/test_llm_resiliente.py:145-146 → `agente_nw/nucleo/llm.py` (`ClienteOllama`) → o corpo leva `num_ctx` e `num_predict` da tarefa (e `seed=42`): são o teto de janela e de saída. Sem teste de que o prompt caiba em `num_ctx` (classe P: ausência documentada).
16. tests/test_llm_api.py:125,130,195,202,254,257 → `agente_nw/nucleo/llm.py` (`ClienteAnthropic`/`ClienteOpenAI`/`ClienteGemini`) → `max_tokens`/`maxOutputTokens` = `num_predict` da tarefa e `"num_ctx" not in json.dumps(corpo)`: nas APIs nenhum limite de janela de entrada é enviado nem conferido (classe P: o teste fixa a ausência).
17. tests/test_fluxo.py:84 → `agente_nw/nucleo/fluxo.py` (`Dependencias`) → `num_ctx_redacao=8192` é passado à redação (limite de janela da tarefa de redação; nenhum teste verifica que o prompt cabe).

## Entradas de teste que podem esconder um corte (para o relatório)

- tests/test_cruzamento_por_consulta.py, test_cruzamento.py, test_gate_objetivo.py, test_gate_lote_ordem.py, test_gate_zera_menu.py, test_evitar_implicito.py: todos criam `Assunto(titulo_gerado=...)` sem corpo/resumo/itens. O "assunto" que o gate e o filtro de evitar veem nos testes é só o título; o mock do gate decide por `"OAB" in candidato` (test_gate_objetivo.py:63). Um teste assim nunca provaria que o gate real recebe o texto inteiro da notícia.
- tests/test_itens_agrupamento.py:34-44: `Item.texto = "Texto de exemplo."` e `hash_titulo` falso; nenhum teste de agrupamento usa corpo longo.
- tests/test_markdown_gerar.py:89-98: cartão multilinha de 3 linhas, mas só `"Cartão: linha 1" in texto`; não afirma a presença de linha 2/3 (se o código de produção imprime só a 1ª linha, o teste passa; se imprime as 3, também).
- tests/test_consulta_preparar.py (todo): `leitor_rss.coletar`, `extrator_perfil.processar_fila`, `agrupador.agrupar`, `qualificador.qualificar_pendentes`, `leitor_capturas.ler_redes_sociais_do_contato` e `cruzamento.cruzar_contato_por_consulta` são trocados por lambdas; o teste só prova ordem e persistência do histórico.
- tests/test_fluxo.py `Cenario`: `fluxo_mod.preparar`, `redacao_mod.redigir` e `localizacao_mod.localizar_rede` são trocados por falsos; a redação "devolve" um `Gancho` pronto, sem prompt (todos os testes de console/fluxo/contato_divergente/gancho/tela_unica/inicio herdam isto).
- tests/test_console_mensagem_base.py:18-27: `redigir` mockado para devolver só a base.
- tests/test_localizacao.py:58, tests/test_listas_parse.py:25,183, tests/test_extensao_backend.py:197: texto de página fixo `"x" * 600` / `"x"*5000` (só serve para passar o "teaser mínimo"; não é conteúdo).
- tests/test_importador.py:42-45: nota da agenda de 27 caracteres ("Gosta de futebol e viagens.") — curta demais para um corte aparecer.
- tests/test_extrator.py:14-19 (`llm_real`): texto de ~230 caracteres; nunca exercita o extrator com texto longo.
- tests/test_llm_*.py: o prompt é "prompt"/"prompt de teste"; embeddings: `_embeddings_falsos` devolve `[0.5]*1024` por entrada; `test_llm_fumaca` embeda 100 frases curtas — nenhum teste exercita o corte silencioso do `bge-m3` acima de 8.192 tokens.
- tests/test_console_temas.py:73, test_console_eu.py:97-98, test_importar_temas.py:19-21: embedder fake devolve vetor constante, independente do texto recebido (não prova que o texto inteiro da descrição vai ao embedder).
