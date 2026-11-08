# Leitura do executor (parte P0, continuação) — pacote de prompts, cliente de LLM, captura e queries do caminho do texto

| Arquivo | Linhas lidas/total | Resultado | Evidência (uma linha) | Ponto |
|---|---|---|---|---|
| agente_nw/coleta/capturas/extensao_backend.py | 181/181 | CORTA | o texto da página capturada é cortado em `maximo_caracteres_pagina` duas vezes: no pedido à extensão (l. 88) e no recorte local da resposta (l. 93) | — |
| agente_nw/coleta/capturas/leitor.py | 170/170 | CORTA | grava o bloco integral como fato (`conteudo=bloco`, l. 155, com o comentário "texto de fonte externa não se altera"), mas examina só `maximo_blocos × 4` blocos da página e para ao gravar `maximo_blocos` | — |
| agente_nw/coleta/rss/ruido.py | 71/71 | CORTA | decide ruído pelo tamanho do corpo inteiro (l. 51) mas procura a marca de patrocinado só nas 3 primeiras linhas (l. 57) | — |
| agente_nw/nucleo/database/queries/conversa.py | 98/98 | CORTA | guarda a mensagem inteira e reparte o mês em blocos sem perder nada (`_em_blocos`), mas devolve só os `meses_extraidos` meses mais recentes (l. 97) e as `limite` últimas trocas (l. 46) | — |
| agente_nw/nucleo/database/queries/perfis.py | 657/657 | CORTA | o centróide do contato, que pontua toda a relevância, vem de 20 fatos cortados em 500 caracteres (l. 613-630); o resto do arquivo grava e lê a ficha inteira | — |
| agente_nw/nucleo/llm.py | 632/632 | CORTA | repassa `num_ctx` e `num_predict` da tarefa ao provedor (l. 240-251, 365, 473, 560) sem medir o prompt nem conferir se a resposta veio cortada; o texto do prompt chega e sai inteiro | — |
| agente_nw/nucleo/modelos/perfil.py | 35/35 | CERTIFICADO | contrato Pydantic do perfil: campos de texto (`notas`, `formacao`, `cargo`…) sem limite de tamanho e sem validador que corte | — |
| agente_nw/nucleo/prompts/__init__.py | 28/28 | CERTIFICADO | não manipula texto de conteúdo: só confere que todo módulo de prompt declara `VERSAO` | — |
| agente_nw/nucleo/prompts/avaliar_relacao_objetivo.py | 66/66 | CERTIFICADO | monta o prompt do gate com os pares (título, resumo) que recebe, cada um cercado por inteiro; não corta nada (quem escolhe o que entra é `cruzamento.py`, ponto P-010) | — |
| agente_nw/nucleo/prompts/cartao.py | 68/68 | CERTIFICADO | monta o prompt com os trios (título, domínio, trecho) que recebe, cada um cercado por inteiro; o trecho de 300 caracteres é cortado em `cartoes.py` (P-004) | — |
| agente_nw/nucleo/prompts/cruzar_por_que.py | 100/100 | CERTIFICADO | monta o prompt com os títulos e temas que recebe, cercados por inteiro; a representação reduzida vem de `cruzamento.py` (P-011) | — |
| agente_nw/nucleo/prompts/descrever_tema.py | 32/32 | CERTIFICADO | monta o prompt com o termo inteiro; pede descrição de 10 a 20 palavras, que é saída do modelo, não corte de entrada | — |
| agente_nw/nucleo/prompts/desempatar_perfil.py | 62/62 | CERTIFICADO | monta o prompt com os cabeçalhos que recebe, cercados por inteiro; o recorte ao cabeçalho vem de `localizacao.py` (P-020) | — |
| agente_nw/nucleo/prompts/exemplos_conversavel.yaml | 22/22 | CERTIFICADO | dado de prompt: 20 frases de exemplo de conversável/não conversável; nenhum limite de quantidade ou tamanho de texto analisado | — |
| agente_nw/nucleo/prompts/extrair_de_texto.py | 85/85 | CERTIFICADO | põe o texto recebido inteiro no prompt, cercado (`cercar_dado_externo(texto)`, l. 84); nenhum corte | — |
| agente_nw/nucleo/prompts/extrair_pedido.py | 91/91 | CERTIFICADO | põe a frase do usuário inteira no prompt (l. 89) e a lista de contatos que recebe; o teto de 50 contatos é de `pedido.py` (P-035) | — |
| agente_nw/nucleo/prompts/prerotular_calibracao.py | 63/63 | CERTIFICADO | monta o prompt com os dois títulos e os dois trechos que recebe, cercados por inteiro; o trecho de 2.000 caracteres é cortado em `calibracao.py` (P-008) | — |
| agente_nw/nucleo/prompts/qualificar.py | 81/81 | CERTIFICADO | monta o prompt com os pares (título, domínio) que recebe, cada título cercado por inteiro; o texto do item já não existe aqui (P-002/P-006) | — |
| agente_nw/nucleo/prompts/rotular.py | 40/40 | CERTIFICADO | monta o prompt com os pares (título, domínio) que recebe, cercados por inteiro; nenhum corte próprio | — |
| agente_nw/nucleo/prompts/seguranca.py | 40/40 | CERTIFICADO | cerca o texto de terceiro por inteiro e só neutraliza marcador forjado trocando `<` e `>` por espaço — nenhum caractere é removido | — |
| agente_nw/nucleo/relevancia/__init__.py | 0/0 | CERTIFICADO | arquivo vazio: só marca o pacote | — |
| agente_nw/nucleo/relevancia/pontuacao.py | 153/153 | CERTIFICADO | não manipula texto: pontua só por cosseno entre vetores já gravados | — |
| agente_nw/perfil/extrator.py | 124/124 | CORTA | manda `item.texto` inteiro ao prompt `extrair_de_texto` (l. 79-81) — e é justamente por isso que nada confere se ele cabe no `num_ctx` da tarefa | — |
| extensao/conteudo.js | 203/203 | CORTA | corta o `innerText` da página no `maximo` recebido (l. 199), limita imagens por `maximo`/`largura_minima` (l. 181-195) e a leitura da lista por orçamento de tempo e de páginas (l. 108, 130) | — |
| scripts/verificar_auditoria_texto.py | 414/414 | CERTIFICADO | não manipula texto de conteúdo: enumera o universo, lê o relatório desta auditoria e varre o código em busca de padrões de corte | — |
| tests/test_verificar_auditoria_texto.py | 500/500 | CERTIFICADO | só exercita o verificador contra árvores e relatórios sintéticos em `tmp_path`; não constrói entrada de produção | — |
