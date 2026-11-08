# Saida T3 (parte_T02: 52 arquivos de tests/, 6.449 linhas)

Todos os 52 arquivos foram lidos do inicio ao fim; total conferido com `wc -l` (6.449). Resultado simplificado para testes: `CERTIFICADO` em todos; os que tocam um corte de producao ou escondem um corte levam a nota na evidencia e entram no bloco "Cortes de producao documentados por teste".

## 1. Tabela de certificacao

| Arquivo | Linhas lidas/total | Resultado | Evidencia (uma linha) | Ponto |
|---|---|---|---|---|
| tests/test_migracao_008.py | 16/16 | CERTIFICADO | So confere colunas de `lista_rede_social` apos migrar; nao manipula texto de conteudo. | — |
| tests/test_migracao_009.py | 27/27 | CERTIFICADO | So confere colunas de `gancho_uso` e `rede_sem_perfil`; infraestrutura. | — |
| tests/test_migracao_011.py | 33/33 | CERTIFICADO | Colunas novas de `pedido` e CHECK de status; texto 'pedido antigo'/'x' so como linha de banco. | — |
| tests/test_migracao_comentarios.py | 49/49 | CERTIFICADO | Migracao 14 preserva `gancho_uso` antigo; `gancho_json='{}'`, sem texto real. | — |
| tests/test_migracao_genero.py | 49/49 | CERTIFICADO | Migracao 16 (`genero_gramatical`) e CHECK de 3 valores; infraestrutura. | — |
| tests/test_migracoes.py | 39/39 | CERTIFICADO | Conta migracoes aplicadas e tabelas virtuais vec0; infraestrutura. | — |
| tests/test_molde_adapta_genero.py | 120/120 | CERTIFICADO | Exercita `redacao.redigir` com molde de outro contato; mock de LLM le "Genero gramatical" no prompt e devolve mensagem curta (molde entra inteiro, mensagens de 1 linha). | — |
| tests/test_molde_atributo_compartilhado.py | 109/109 | CERTIFICADO | Exercita o bloco de moldes do prompt e `montar_entrada`; o molde de 1 frase entra inteiro (`assert molde in prompt`). Recuperacao limitada a `maximo_moldes` (ver bloco de cortes). | — |
| tests/test_molde_verdade_046.py | 71/71 | CERTIFICADO | Checa que as regras do prompt (`_regras`, `_bloco_moldes`) contem frases fixas; sem corte. | — |
| tests/test_moldes_por_contexto.py | 107/107 | CERTIFICADO | Documenta o teto de moldes (`maximo=2`) em `moldes_por_contexto`; mensagens-molde de 1 linha. | — |
| tests/test_moldes_so_confirmado.py | 195/195 | CERTIFICADO | Documenta: havendo `usado` so `usado` entra; sem `usado`, no maximo 1 `entregue` (a mais recente); mensagens curtas. | — |
| tests/test_normalizacao.py | 23/23 | CERTIFICADO | `telefone_e164` sobre numeros de telefone; identificador, nao texto de conteudo. | — |
| tests/test_nota_contato.py | 57/57 | CERTIFICADO | CRUD de `nota_contato`; `listar_por_perfil(..., 1)` documenta o parametro `limite` (corte opcional por contagem). | — |
| tests/test_orquestracao.py | 546/546 | CERTIFICADO | Encaminhamento claro/ambiguo/nenhum, canais terminal/web, `preparar_e_redigir` com `preparar` e `redigir` simulados; frases de pedido curtas, nada cortado. | — |
| tests/test_peculiaridade.py | 91/91 | CERTIFICADO | Fato unico e curto vai ao prompt; verifica frases das regras do prompt. A entrada nunca chega perto dos cortes (`_FATOS_NO_PROMPT`, `_TRECHO_DO_FATO_NO_PROMPT`). | — |
| tests/test_pedido_extrair.py | 104/104 | CERTIFICADO | Documenta o corte `termos_busca` > 6 (`modelos/pedido.py`); frase do pedido entra inteira no prompt. | — |
| tests/test_pedido_para_contexto.py | 52/52 | CERTIFICADO | Documenta dedupe de termos e `maximo=10` em `gerar_consultas_da_consulta`; termos curtos. | — |
| tests/test_pedido_resolver_contato.py | 159/159 | CERTIFICADO | Resolucao de contato por nome/pistas; LLM simulado devolve `PedidoExtraido` pronto (nao testa o prompt de extracao com frase longa). | — |
| tests/test_pedido_usuario.py | 40/40 | CERTIFICADO | `garantir_usuario` com `getpass`; nao manipula texto de conteudo. | — |
| tests/test_perfil_tema_nivel.py | 34/34 | CERTIFICADO | `atualizar_nivel` em `perfil_tema`; infraestrutura. | — |
| tests/test_perfis_apagar_unir.py | 247/247 | CERTIFICADO | Apagar/unir contatos e gatilhos de fato/consulta; textos "algo"/"original" so como linhas de banco. | — |
| tests/test_perfis_campos_guiados.py | 67/67 | CERTIFICADO | `atualizar_campos_guiados` (nao sobrescreve campo preenchido); campos curtos de ficha. | — |
| tests/test_perfis_centroide.py | 106/106 | CERTIFICADO | Centroide ponderado de temas confirmados, vetores de 1024 posicoes; sem texto. | — |
| tests/test_perfis_listar_todos.py | 52/52 | CERTIFICADO | `listar_todos` ordenado por nome; sem texto de conteudo. | — |
| tests/test_piso_objetivo.py | 67/67 | CERTIFICADO | `avaliar_por_consulta` com vetores; so constantes de limiar (`itens_no_menu=5`, `candidatos_por_contato=10`) na fixture, sem afirma-las. | — |
| tests/test_ponte_servidor.py | 236/236 | CERTIFICADO | Ponte HTTP local (token, long-poll, tempo limite, aquecimento); so infraestrutura. | — |
| tests/test_pontuacao.py | 88/88 | CERTIFICADO | 12 casos da secao 6 de `avaliar` com vetores; constantes de limiar na fixture, sem texto. | — |
| tests/test_porteiro.py | 467/467 | CERTIFICADO | Consulta ao `porteiro` antes de carregar modelo (espera 15x60 s, 16 consultas, timeout 30 s); prompts de teste de 1 palavra ("prompt"), o porteiro nao recebe texto, so modelo e porta. | — |
| tests/test_prompt_extrair_pedido.py | 27/27 | CERTIFICADO | Prompt de extracao contem a frase e os contatos; frase de 4 palavras, nao exercita frase longa. | — |
| tests/test_proveniencia.py | 335/335 | CERTIFICADO | Proveniencia (modelo, perfil, versao do prompt) em log/gancho/fato/assunto/vetor; textos de 1 frase e respostas simuladas (`{"resumo": "Obras comecam na orla."}`). | — |
| tests/test_qualificador.py | 165/165 | CERTIFICADO | `qualificar_pendentes(cliente, conn, 10)` com mock que devolve titulo/qualificacao; assunto de 1 item so com titulo "Titulo do item" (sem texto do item). | — |
| tests/test_reconsulta_mesmo_dia.py | 212/212 | CERTIFICADO | Reconsulta substitui menu/preserva `usado`; mock de LLM e assuntos so com titulo e centroide fixo; limiares de fixture (`teaser_minimo_caracteres=400`, `maximo_entradas=2000`, `itens_no_menu=5`) sem afirma-los. | — |
| tests/test_redacao_fato_antigo_e_foto.py | 91/91 | CERTIFICADO | Marcas `[antigo]`/`[de imagem]` em `_fatos`; o `12` passado e `meses_fato_antigo`, nao contagem; fatos de 1 linha. | — |
| tests/test_redacao_modelo.py | 126/126 | CERTIFICADO | Documenta limites de palavras por registro (60/80/110), titulo <= 12 palavras e `MAXIMO_GANCHOS=4` (`modelos/redacao.py`); rejeita, nao trunca. | — |
| tests/test_redacao_prompt.py | 110/110 | CERTIFICADO | Documenta `cortar_por_tamanho`: acima de 6000 tokens estimados fica 1 consulta de historico e 5 fatos; `estimar_tokens` = palavras x 1,4. | — |
| tests/test_redacao_redigir.py | 349/349 | CERTIFICADO | Documenta `_escolher_fatos` (10 de 30: 4 recentes + 6 por semelhanca; sem embeddings os 10 mais recentes); fatos de teste curtos escondem o corte de 600 caracteres no embedding. | — |
| tests/test_rede_sem_perfil.py | 65/65 | CERTIFICADO | CRUD de `rede_sem_perfil`; sem texto de conteudo. | — |
| tests/test_redes_sociais_queries.py | 82/82 | CERTIFICADO | CRUD de `redes_sociais`; sem texto de conteudo. | — |
| tests/test_restricoes.py | 102/102 | CERTIFICADO | Restricoes UNIQUE/CHECK/gatilhos do esquema; conteudo 'x'/'y' so como linha de banco. | — |
| tests/test_ruido.py | 51/51 | CERTIFICADO | Documenta o filtro `e_ruido`: corpo < `teaser_minimo_caracteres` (400) e ruido; `CORPO_LONGO` tem ~650 caracteres, corpo curto = "corpo curto". | — |
| tests/test_seguranca_prompt.py | 348/348 | CERTIFICADO | `cercar_dado_externo` e os 9 modulos de prompt: texto entra inteiro entre marcadores, marcador forjado neutralizado, conteudo preservado (`INJECAO in cercado`); entradas de 1 linha. | — |
| tests/test_selecao_provedor.py | 216/216 | CERTIFICADO | `selecionar_cliente_llm` (ordem Anthropic > Gemini > OpenAI); le so `container.py`/`app.py` para contar construcoes; sem texto de conteudo. | — |
| tests/test_sem_censura_de_tema.py | 75/75 | CERTIFICADO | Tag/fato politico ou de saude sao gravados; prompt de extracao sem "sensive"; texto de fila "texto qualquer" (curto), resposta simulada. | — |
| tests/test_sem_objetivo_avisa.py | 38/38 | CERTIFICADO | Todos abaixo do piso -> aviso; reaproveita fixtures de `test_cruzamento_por_consulta`; fato de 1 linha, assunto so com titulo. | — |
| tests/test_sem_redes_sociais.py | 74/74 | CERTIFICADO | Botao "sem redes sociais" no console Flask; sem texto de conteudo. | — |
| tests/test_temas_atualizar.py | 33/33 | CERTIFICADO | `temas.atualizar` regrava descricao e sinonimos; descricoes curtas, sem corte. | — |
| tests/test_termos_contato.py | 89/89 | CERTIFICADO | Documenta teto de 3 termos e rejeicao de termo > 5 palavras em `termos_contato.py`; os fatos de teste sao curtos e escondem os cortes de 12 fatos e 300 caracteres por fato do prompt. | — |
| tests/test_validacao_base.py | 69/69 | CERTIFICADO | Documenta `validar_ganchos`: base antes, so 1 base, `MAXIMO_GANCHOS` de noticia, limite 80 palavras da base. | — |
| tests/test_vetores.py | 33/33 | CERTIFICADO | `cosseno` e `centroide` com vetores pequenos; sem texto. | — |
| tests/test_whatsapp_importador.py | 289/289 | CERTIFICADO | Documenta `meses_extraidos=2` (so os 2 meses mais recentes, julho fora); mensagens de 1 linha escondem `maximo_caracteres_bloco=6000`, que nenhum teste exercita. | — |
| tests/test_whatsapp_leitor.py | 109/109 | CERTIFICADO | Parser da exportacao (iPhone/Android/zip); descarta midia/aviso do sistema/mensagem apagada, emenda linhas, sem cortar texto de mensagem real. | — |
| tests/test_whatsapp_no_prompt.py | 110/110 | CERTIFICADO | Documenta as 10 ultimas trocas do WhatsApp no prompt (de 15) e a retirada da conversa inteira quando o prompt passa de 6000 tokens (`cortar_por_tamanho`). | — |

Resultado: 52 `CERTIFICADO`, 0 `CORTA`, 0 `NAO ANALITICO`, 0 `NAO CONFERIDO`. Nenhum teste contem corte analitico proprio (nenhum slice, LIMIT ou max_chars aplicado a texto dentro de `tests/` desta lista), por isso a secao 2 abaixo fica sem pontos T3-nnn.

## Cortes de producao documentados por teste

Formato: `arquivo de teste:linha -> arquivo de producao -> o que o teste afirma`. Numeros de producao conferidos por leitura/grep do codigo (somente leitura).

### Cortes de texto de item (classe T) ou prompt
- tests/test_redacao_prompt.py:82-90 (`test_prompt_grande_corta_historico_para_um_e_fatos_para_cinco`) -> agente_nw/nucleo/prompts/redigir_ganchos.py (`cortar_por_tamanho`, linhas 20-21 e 280-295; `LIMITE_TOKENS_PADRAO = 6000`, linha 18) -> prompt estimado acima de 6.000 tokens: o historico cai para 1 consulta (`consulta 0` fica, `consulta 1` sai) e os fatos para 5 (`fato 4` fica, `fato 5` sai). Cada item fica inteiro; o corte e por contagem de itens.
- tests/test_redacao_prompt.py:97-98 (`estimar_tokens`) -> agente_nw/nucleo/prompts/redigir_ganchos.py:93 -> estimativa de tokens = numero de palavras x 1,4 (100 palavras = 140); e esta estimativa, nao o `num_ctx`, que decide o corte acima.
- tests/test_whatsapp_no_prompt.py:97-110 (`test_conversa_sai_do_prompt_antes_das_notas_perto_do_limite`) -> agente_nw/nucleo/prompts/redigir_ganchos.py:280-295 -> acima de 6.000 tokens a conversa de WhatsApp sai do prompt por inteiro (`trocas_whatsapp=[]`), mantendo as notas do usuario; ordem de descarte: historico/fatos, moldes, conversa.

### Cortes de colecao (classe C)
- tests/test_redacao_redigir.py:315-324 (`test_fatos_escolhidos_sao_os_recentes_mais_os_parecidos_com_a_consulta`) -> agente_nw/nucleo/redacao.py:96-111 (`_escolher_fatos`; `_FATOS_NO_PROMPT = 10` linha 39, `_FATOS_RECENTES_GARANTIDOS = 4` linha 42) -> de 30 fatos candidatos entram 10: os 4 mais recentes mais os 6 mais parecidos com a consulta (por embedding); os outros 20 saem do prompt.
- tests/test_redacao_redigir.py:327-332 (`test_poucos_fatos_entram_todos_e_sem_embeddings_ficam_os_recentes`) -> agente_nw/nucleo/redacao.py:96-111 -> com 8 fatos entram todos; com 30 fatos e sem `embeddar` (ou com falha) ficam so os 10 mais recentes.
- tests/test_whatsapp_no_prompt.py:51-77 (`test_as_ultimas_trocas_aparecem_no_historico`, chama `montar_entrada(..., 12, 10)`) -> agente_nw/nucleo/redacao.py:198-209 (`trocas_whatsapp_no_prompt=10`) -> de 15 mensagens gravadas so as 10 mais recentes vao ao prompt (a mais antiga e "mensagem 5"; as 5 primeiras saem).
- tests/test_whatsapp_importador.py:146-163 (`test_agrupamento_por_mes_e_limite_de_meses`) -> agente_nw/coleta/whatsapp/importador.py:47-52 (`limiares.meses_extraidos`; fixture `_LIMIARES` usa 24, linha 31) -> com `meses_extraidos=2` e mensagens de julho, agosto e setembro, so agosto e setembro vao para `fila_extracao`; julho fica fora da extracao.
- tests/test_whatsapp_importador.py:126-143 (`test_so_mensagens_do_contato_vao_para_a_fila`) -> agente_nw/coleta/whatsapp/importador.py (`enfileirar_extracao`) -> so as mensagens do contato vao para a extracao; as do usuario nao entram no texto enfileirado (`"pergunta do davi" not in texto`). Corte por autor, nao por tamanho.
- tests/test_moldes_por_contexto.py:94-107 (`test_usado_vem_antes_de_entregue_e_respeita_o_maximo`) e tests/test_moldes_so_confirmado.py:81-118 -> agente_nw/nucleo/database/queries/consulta_contato.py (`moldes_por_contexto`, parametro `maximo`) e agente_nw/nucleo/redacao.py:209 (`maximo_moldes=2`) -> 3 mensagens candidatas, `maximo=2` devolve 2; havendo `usado`, so `usado` entra (mesmo com `entregue` mais recente); sem `usado`, no maximo 1 `entregue`, a mais recente. `nao_serve` nunca entra (test_moldes_por_contexto.py:61-69).
- tests/test_pedido_extrair.py:74-76 (`test_termos_de_busca_acima_de_seis_sao_cortados`) -> agente_nw/nucleo/modelos/pedido.py:19 e :101 (`_MAXIMO_TERMOS_BUSCA = 6`) -> sete termos de busca viram os seis primeiros (`["a".."f"]`; "g" sai). O irmao `_MAXIMO_INTERESSA = 5` (linha 18, :91) nao tem teste.
- tests/test_pedido_para_contexto.py:39-52 -> agente_nw/coleta/rss/google_news.py (`gerar_consultas_da_consulta(..., maximo=10)`) -> ordem assunto, contato, 2 termos de busca; `interessa` repetido nos termos nao gera consulta duplicada (4 feeds no total).
- tests/test_termos_contato.py:63-82 (`test_termos_filtrados_e_limitados`) -> agente_nw/nucleo/termos_contato.py:13, :17, :71, :76 (`MAXIMO_TERMOS = 3`, `_MAXIMO_PALAVRAS_DO_TERMO = 5`) -> de 7 termos devolvidos pelo modelo ficam 3 (sem repetidos, sem termo de mais de 5 palavras). Nota: o prompt desse modulo corta cada fato em 300 caracteres e usa so 12 fatos (`_CARACTERES_POR_FATO = 300`, `_FATOS_NO_PROMPT = 12`, linhas 15-16 e 60), mas nenhum teste exercita isso (ver bloco de entradas que escondem cortes).
- tests/test_nota_contato.py:26 (`listar_por_perfil(conn, contato.id, 1)`) -> agente_nw/nucleo/database/queries/nota_contato.py:38-46 (parametro `limite`) -> `limite=1` devolve so a nota mais recente.
- tests/test_validacao_base.py:50-58 (`test_so_fica_uma_base_e_ela_vai_antes_e_o_limite_de_noticias_vale`) e tests/test_redacao_modelo.py:116-119 (`test_no_maximo_quatro_ganchos`) -> agente_nw/nucleo/modelos/redacao.py:12 e :141 (`MAXIMO_GANCHOS = 4`, `aceitos[:MAXIMO_GANCHOS]`) -> de 6 ganchos de noticia aceitos ficam 4 (mais 1 base): os demais saem da resposta do modelo.

### Limites de tamanho de saida do modelo ou filtros por tamanho (nao cortam o texto de origem)
- tests/test_redacao_modelo.py:50-57 e tests/test_validacao_base.py:40-47 -> agente_nw/nucleo/modelos/redacao.py:10 (`LIMITE_PALAVRAS_MENSAGEM`: proximo 60, cordial 80, formal 110) -> mensagem acima do limite e rejeitada (nao truncada); com limite+1 palavras o gancho some e o motivo cita "limite N".
- tests/test_redacao_modelo.py:90-94 -> agente_nw/nucleo/modelos/redacao.py:11 (`MAXIMO_PALAVRAS_TITULO = 12`) -> titulo de 13 palavras rejeita o gancho.
- tests/test_ruido.py:23-26 e :9 (`CORPO_LONGO`) -> agente_nw/coleta/rss/ruido.py:51-52 (`len(corpo) < limiares.teaser_minimo_caracteres`; fixture usa 400) -> item com corpo abaixo de 400 caracteres e descartado como ruido; a fixture `CORPO_LONGO` (~650 caracteres) fica acima do corte.

## Entradas de teste que escondem um corte de producao

- tests/test_termos_contato.py:40-41, :65, :87 -> agente_nw/nucleo/termos_contato.py:15-16 e :60 (12 fatos, 300 caracteres por fato): todos os fatos de teste tem uma linha curta ("Sotaque nao atrapalha...", "algo"); nem o limite de 12 fatos nem o de 300 caracteres e acionado.
- tests/test_redacao_redigir.py:303-312 (`_fatos`, "fato i sobre vela/cozinha") -> agente_nw/nucleo/redacao.py:41 e :107 (`_TRECHO_DO_FATO_NO_PROMPT = 600`, `f.conteudo[:600]` ao embeddar): fatos de ~20 caracteres, o corte de 600 caracteres no embedding nao aparece.
- tests/test_peculiaridade.py:19-27 e tests/test_redacao_fato_antigo_e_foto.py:37-42 -> mesmos limites de `redacao.py` (10 fatos, 600 caracteres): um fato por teste, de uma linha.
- tests/test_whatsapp_importador.py:31 e :126-143 -> agente_nw/coleta/whatsapp/importador.py:52 (`limiares.maximo_caracteres_bloco`, fixture 6000): todas as mensagens de teste tem poucas palavras; nenhum teste verifica o que acontece com um mes que passa de 6.000 caracteres (se o bloco e partido ou cortado).
- tests/test_qualificador.py:65-83 -> agente_nw/nucleo/relevancia/qualificador.py: o item do assunto tem so titulo ("Titulo do item"), sem `texto`; o mock de LLM (`_ClienteFake`, linhas 34-52) nunca olha o prompt, entao o que o prompt de qualificacao leva do texto do item nao e coberto.
- tests/test_reconsulta_mesmo_dia.py:44-57, :118-133 e tests/test_sem_objetivo_avisa.py:18-21 -> agente_nw/nucleo/relevancia/cruzamento.py: assuntos so com titulo (`titulo_gerado`), centroide fixo e mock de `avaliar_relacao_objetivo` que devolve `relaciona=True` para todos sem ler o resumo; o que o gate le do texto do assunto nao e coberto. As constantes `itens_no_menu=5`, `candidatos_por_contato=10`, `teaser_minimo_caracteres=400`, `maximo_entradas=2000` aparecem na fixture `limiares` (linhas 63-98) e nunca sao afirmadas.
- tests/test_prompt_extrair_pedido.py:9-17, tests/test_pedido_extrair.py:84-88 e tests/test_pedido_resolver_contato.py:113-117 -> agente_nw/nucleo/prompts/extrair_pedido.py e agente_nw/nucleo/pedido.py: frases de pedido de 4 a 6 palavras; nenhum teste prova que uma frase longa do usuario entra inteira no prompt de extracao.
- tests/test_proveniencia.py:200-218 e tests/test_sem_censura_de_tema.py:37-51 -> agente_nw/perfil/extrator.py (`processar_fila`): texto de fila de 1 frase ("Joao abriu um escritorio em Curitiba.", "texto qualquer"); o LLM e simulado e o teste so confere proveniencia/gravacao, nao que um texto longo de fila chegue inteiro ao prompt.
- tests/test_whatsapp_no_prompt.py:51-77 -> mensagens "mensagem 0..14" de 2 palavras; so a contagem (10 de 15) e provada, nao o tamanho de cada troca. O teste de corte de tamanho (:97-110) usa uma unica linha de 6.000 palavras e prova que a conversa inteira sai, nao um corte parcial.
- tests/test_porteiro.py: os prompts de teste sao "prompt"/"outro prompt"/"um texto"; irrelevante para o corte, pois o porteiro so recebe modelo e porta e o teste nao verifica `num_ctx` nem tamanho de entrada do `bge-m3`.

## 2. Pontos encontrados

Nenhum ponto T3-nnn: nenhum arquivo desta lista contem corte analitico proprio (T, C, R ou P). Os cortes de producao documentados acima pertencem aos arquivos de producao citados e devem ser tratados na parte de producao da auditoria.
