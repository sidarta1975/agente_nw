# Auditoria "texto por inteiro" — parte A4 (prefixo `A4`)

Lista: 33 arquivos, 1.551 linhas (conferido com `wc -l`, soma exata 1.551). Todos lidos do início ao fim.
Nenhum arquivo do repositório foi editado; nada foi executado; `dados/agente.db` não foi tocado.

## 1. Tabela de certificação

| Arquivo | Linhas lidas/total | Resultado | Evidência (uma linha) | Ponto |
| --- | --- | --- | --- | --- |
| config/__init__.py | 0/0 | CERTIFICADO | arquivo vazio (0 bytes de conteúdo): não manipula texto de conteúdo. | — |
| config/container.py | 196/196 | CERTIFICADO | não manipula texto de conteúdo: só infraestrutura (carrega YAML, resolve caminhos, escolhe provedor de LLM e abre o banco); nenhum `[:N]`, nenhum truncamento, nenhuma seleção de item de texto. | — |
| config/limiares.yaml | 84/84 | CORTA | arquivo de limites: 24 chaves de quantidade/tamanho/janela, consumidas por coleta, leitura de rede social, WhatsApp, agrupamento, qualificação, cruzamento e redação. | A4-001 … A4-025 |
| config/llm_routing.yaml | 47/47 | CORTA | declara `num_ctx`/`num_predict` por tarefa nos dois perfis e `bge-m3` para embeddings; só `redigir_ganchos` tem orçamento de prompt no código — as outras 12 tarefas e o embedding não conferem se o texto cabe. | A4-026, A4-027, A4-028 |
| config/local.exemplo.yaml | 26/26 | CERTIFICADO | não manipula texto de conteúdo: caminhos, `ollama_url` e bloco `ia_api` comentado; nenhuma chave de tamanho, janela ou quantidade. | — |
| config/local.yaml | 10/10 | CERTIFICADO | não manipula texto de conteúdo: caminhos, `ollama_url` (11435), usuários de rede; `perfil_llm: pro48` só escolhe qual coluna da tabela de `num_ctx` (§3) vale nesta máquina. | — |
| extensao/background.js | 188/188 | CORTA | é o canal por onde o texto e as imagens da página saem do navegador: repassa `maximo` de caracteres ao `conteudo.js`, repassa `maximo`/`largura_minima` de imagens e descarta imagem por host, por 6 MB e por falha de download. | A4-029 … A4-034 |
| extensao/manifest.json | 44/44 | CERTIFICADO | não manipula texto de conteúdo: manifesto MV3 (permissões, service worker, `externally_connectable`); `host_permissions` é escopo de origem, não corte de texto — é a origem do descarte listado em A4-032. | — |
| extensao/ponte_conteudo.js | 18/18 | CERTIFICADO | repassa a tarefa e a resposta inteiras entre a página-ponte e a extensão (`sendMessage`/`postMessage`), sem ler, cortar ou reescrever campo nenhum. | — |
| scripts/agente_entregar.sh | 136/136 | NÃO ANALÍTICO | ferramenta de entrega (manifesto, gate, commit, push); os únicos cortes são de log na tela (`tail -n 5`, `tail -n 3`) e o descarte do prefixo de 3 caracteres do `git status --porcelain`. | A4-035, A4-036 |
| scripts/agente_lacunas.py | 133/133 | NÃO ANALÍTICO | copia a tabela `## Lacunas` do relatório para o PLAN; corta só coleções de documentação (primeiro relatório do glob, última seção `## Lacunas`), nada vai a LLM, embedding ou filtro do produto. | A4-037, A4-038 |
| scripts/commitar.sh | 83/83 | NÃO ANALÍTICO | `git add` arquivo por arquivo e `git commit -F`; o único corte é `git log --oneline -3`, saída de tela. | A4-039 |
| scripts/instalar_macos.sh | 40/40 | CERTIFICADO | não manipula texto de conteúdo: `brew install`, `ollama pull`, venv, `mkdir`; nenhum texto de conteúdo passa por aqui. | — |
| scripts/migracoes/001_inicial.sql | 160/160 | CERTIFICADO | todas as colunas de conteúdo são `TEXT` sem limite (`item.texto`, `fato.conteudo`, `fila_extracao.texto`, `assunto.justificativa`, `tema.descricao`); os `CHECK` são enumerações (`tipo`, `status`, `origem`) e faixas numéricas (`peso`, `confiabilidade`), nunca `length(...)`; sem view e sem `LIMIT`. | — |
| scripts/migracoes/002_coleta_historico.sql | 9/9 | CERTIFICADO | só contagem por fonte e data (`n_itens_novos INTEGER`); nenhuma coluna de texto de conteúdo. | — |
| scripts/migracoes/003_rede_social.sql | 11/11 | CERTIFICADO | `rede` e `link` são `TEXT` sem limite; nenhum `CHECK (length(...))`, nenhum truncamento. | — |
| scripts/migracoes/004_consulta_contato.sql | 18/18 | CERTIFICADO | `contexto_json`, `resumo_redes_sociais` e `assuntos_entregues_json` são `TEXT` sem limite; gatilhos só impedem UPDATE/DELETE. | — |
| scripts/migracoes/005_perfil_id_reatribuivel.sql | 19/19 | CERTIFICADO | só recria gatilhos `BEFORE UPDATE OF <colunas>`; não cria, apaga nem encurta coluna de texto. | — |
| scripts/migracoes/006_aderencia_consulta.sql | 7/7 | CERTIFICADO | acrescenta `aderencia_consulta REAL`; nenhum texto envolvido. | — |
| scripts/migracoes/007_pedido.sql | 17/17 | CERTIFICADO | `pedido.texto TEXT NOT NULL` guarda a frase do usuário por inteiro, antes de qualquer etapa; `extraido_json TEXT` sem limite. | — |
| scripts/migracoes/008_listas.sql | 20/20 | CERTIFICADO | `nome`, `nome_normalizado`, `cabecalho`, `link` são `TEXT` sem limite; `nome_normalizado` é chave de busca adicional, não substitui `nome`. | — |
| scripts/migracoes/009_gancho_uso.sql | 18/18 | CERTIFICADO | `gancho_json TEXT NOT NULL` guarda o gancho inteiro (o comentário da linha 3 diz isso); `CHECK` só na enumeração de `status`. | — |
| scripts/migracoes/010_rede_sem_perfil.sql | 12/12 | CERTIFICADO | tabela de decisão (perfil, rede, data); nenhuma coluna de texto de conteúdo. | — |
| scripts/migracoes/011_pedido_fluxo.sql | 17/17 | CERTIFICADO | sete `ADD COLUMN` (`status`, `etapa`, `erro`, `avisos_json`, `localizacao_json`, ids); `CHECK` só na enumeração de `status`. | — |
| scripts/migracoes/012_pedido_fonte_noticias.sql | 7/7 | CERTIFICADO | duas colunas `TEXT` de procedência/validade; nenhum limite. | — |
| scripts/migracoes/013_gancho_uso_sem_assunto.sql | 25/25 | CERTIFICADO | reconstrução da tabela com `SELECT` de todas as 6 colunas para todas as linhas (`SELECT id, consulta_id, assunto_id, status, gancho_json, atualizado_em FROM gancho_uso`), sem `WHERE` e sem `LIMIT`. | — |
| scripts/migracoes/014_comentarios.sql | 17/17 | CERTIFICADO | `gancho_uso.comentario TEXT` e `nota_contato.texto TEXT` sem limite; o único `CHECK (length(trim(texto)) > 0)` exige texto não vazio — é piso, não teto. | — |
| scripts/migracoes/015_conversa_whatsapp.sql | 18/18 | CERTIFICADO | `conversa_mensagem.texto TEXT NOT NULL` sem limite; `UNIQUE (perfil_id, hash)` deduplica por mensagem, e o `hash` é coluna própria (o texto guardado não é encurtado). | — |
| scripts/migracoes/016_perfil_genero_gramatical.sql | 9/9 | CERTIFICADO | uma coluna de enumeração (`masculino`/`feminino`/`desconhecido`); nenhum texto de conteúdo. | — |
| scripts/migracoes/017_preferencias_usuario_temas.sql | 25/25 | CERTIFICADO | `preferencias_json TEXT` sem limite, `peso_decaido_em TEXT` (mês) e tabela `tema_uso` de contagem; nenhum truncamento. | — |
| scripts/migracoes/018_molde_rastreio.sql | 9/9 | CERTIFICADO | uma coluna de id (`molde_origem_id`); nenhum texto. | — |
| scripts/migracoes/019_proveniencia.sql | 63/63 | CERTIFICADO | 15 colunas de proveniência `TEXT NULL` e recriação das três tabelas vec0 copiando **todas** as linhas e vetores (`SELECT ... FROM _copia_*`, sem `WHERE`/`LIMIT`), com backfill `'bge-m3'`. | — |
| scripts/verificar.sh | 65/65 | NÃO ANALÍTICO | o gate (ruff, format, mypy, pytest); a saída completa vai para `logs/verificar_ultimo.txt` e só a tela é encurtada (`head -n 15`, `tail -n 1`). | A4-040 |

Resumo: 33 arquivos — **CERTIFICADO 25**, **CORTA 3**, **NÃO ANALÍTICO 5**, **NÃO CONFERIDO 0**.

## 2. Pontos encontrados

### 2.0 Inventário das chaves de `config/limiares.yaml` que limitam quantidade, tamanho ou janela

Cada chave abaixo aparece como ponto numerado adiante, com o código consumidor encontrado por `grep`
pelo nome da chave em `agente_nw/` (o modelo Pydantic que a valida é sempre
`agente_nw/nucleo/modelos/configuracao.py`).

| Chave (linha) | Valor | Código consumidor | Efeito |
| --- | --- | --- | --- |
| `extensao.maximo_caracteres_pagina` (59) | 200000 | `agente_nw/coleta/capturas/extensao_backend.py:88,93` | analítico (T) — A4-001 |
| `coleta.maximo_blocos_por_rede` (42) | 10 | `agente_nw/nucleo/consulta.py:147` → `coleta/capturas/leitor.py:135-143` | analítico (C) — A4-002 |
| `coleta.maximo_imagens_por_rede` (43) | 8 | `agente_nw/nucleo/consulta.py:148` → `leitor.py:116` | analítico (C) — A4-003 |
| `coleta.largura_minima_imagem` (44) | 250 | `consulta.py:149` → `leitor.py:117` → `navegador.py:140,147` | analítico (C) — A4-004 |
| `whatsapp.meses_extraidos` (71) | 24 | `coleta/whatsapp/importador.py:52` → `nucleo/database/queries/conversa.py:97` | analítico (C) — A4-005 |
| `whatsapp.maximo_caracteres_bloco` (72) | 6000 | `importador.py:52` → `conversa.py:_em_blocos` (linhas 64-76) | não cortante (NA) — A4-006 |
| `whatsapp.trocas_no_prompt` (73) | 10 | `nucleo/orquestracao.py:212` → `nucleo/redacao.py` (HISTÓRICO) | analítico (C) — A4-007 |
| `coleta.maximo_itens_novos_por_feed` (40) | 15 | `coleta/rss/leitor.py:362` | analítico (C) — A4-008 |
| `coleta.tempo_maximo_segundos` (41) | 240 | `coleta/rss/leitor.py:242` | analítico (C) — A4-009 |
| `coleta.candidatos_suficientes` (37) | 10 | `coleta/rss/leitor.py:275` | analítico (C) — A4-010 |
| `coleta.max_consultas_por_pedido` (35) | 4 | `nucleo/consulta.py:172` (`google_news.selecionar_termos`) | analítico (C) — A4-011 |
| `coleta.horas_reuso_termo` (36) | 24 | `coleta/rss/leitor.py:133-135` | analítico (C) — A4-012 |
| `coleta.retencao_texto_dias` (31) | 90 | `nucleo/agrupamento/agrupador.py:95` (+ comentário `item.texto -- vive 90 dias`, 001_inicial.sql:83) | analítico (C) — A4-013 |
| `coleta.teaser_minimo_caracteres` (29) | 400 | `coleta/rss/ruido.py:51` | analítico (C) — A4-014 |
| `coleta.dias_max_primeira_aparicao` (30) | 7 | `coleta/rss/ruido.py:68` | analítico (C) — A4-015 |
| `agrupamento.janela_dias` (5) / `itens_para_dividir` (6) | 7 / 12 | `agrupamento/agrupador.py:94,187,191` | analítico (C) — A4-016 |
| `qualificacao.teto_por_dia` (10) | 40 | `nucleo/consulta.py:204`, `cli.py:442` | analítico (C) — A4-017 |
| `cartao.teto_por_dia` (46) | 40 | `nucleo/modelos/configuracao.py:216` (limite da geração de cartão) | analítico (C) — A4-018 |
| `conector.candidatos_por_contato` (18) / `itens_no_menu` (19) | 10 / 5 | `nucleo/relevancia/cruzamento.py:220,272,365,481` | analítico (C) — A4-019 |
| `listas.maximo_entradas` (48) / `rodadas_sem_novidade` (54) | 2000 / 6 | `coleta/capturas/listas.py:346,355,367`; `extensao_backend.py:104,180` | analítico (C) — A4-020 |
| `listas.maximo_parecidas` (52) | 5 | `nucleo/localizacao.py:260` | analítico (C) — A4-021 |
| `moldes.maximo` (77) | 2 | `nucleo/orquestracao.py:213` → `redacao.py:174-190` | analítico (C) — A4-022 |
| `redacao.meses_fato_antigo` (68) | 12 | `nucleo/redacao.py:116-141` | só marcação (NA) — A4-023 |
| `temas_usuario.janela_dias_interesse/_dominio`, `dias_para_decair` (82-84) | 30 / 90 / 180 | `perfil/inferencia.py:159-160` | analítico (C) — A4-024 |
| `listas.redes_so_por_link` (55) | `[]` | `cli.py:988`, `nucleo/pedido.py:243`, `localizacao.py:282`, `coleta/capturas/busca.py:49` | hoje não corta (NA) — A4-025 |

Chaves de `limiares.yaml` que **não** limitam quantidade/tamanho/janela e por isso não geram ponto:
limiares de cosseno e de pontuação (`agrupamento.cosseno_*`, `divergencia_minima_fonte_independente`,
`qualificacao.substancial_minimo`/`conversavel_minimo`, `conector.adjacencia_minima`,
`conversavel_viavel`, pesos, `conector.consulta.*`, `listas.similaridade_minima`,
`similaridade_contato_forcado`, `temas_usuario.similaridade_mesmo_tema`, `usos_para_*`) e
parâmetros de tempo/ambiente (`intervalo_google_news_segundos`, `dias_alerta_feed_vazio`,
`cooldown_bloqueio_minutos`, `minutos_reaproveitamento`, `usar_fonte_alternativa`,
`listas.pausa_rolagem_s`, `validade_dias`, `extensao.tempo_limite_tarefa_s`,
`pausa_entre_paginas_s`, `textos_botao_mostrar_mais`, `aba_em_segundo_plano`, `espera_extensao_s`,
`espera_render_s`, `navegador_app`, `navegador_perfil`). São pisos de similaridade e política de
ritmo/validade; nenhum encurta um texto nem descarta item por tamanho.

---

#### A4-001 — config/limiares.yaml:59 — `extensao.maximo_caracteres_pagina`
- Classe: T
- O que é cortado e quanto: o texto da página de rede social lida no Chrome, em 200.000 caracteres — duas vezes: a extensão recebe `maximo` e devolve já cortado, e o backend corta de novo o que recebeu.
- Qual decisão do produto depende desse corte: todo o conteúdo que a extração de rede social vê (tarefa `extrair_captura_rede_social`) e, por consequência, os fatos gravados sobre o contato; também o teste de "página ainda desenhando" (`len(texto.strip()) < MIN_CHARS_AUTENTICADO`).
- Trecho de código (copiado):
  ```
  maximo_caracteres_pagina: 200000
  # agente_nw/coleta/capturas/extensao_backend.py:93
  return str(dados.get("url", "")), texto[: self._limiares.maximo_caracteres_pagina]
  ```
- Justificativa existente no código/comentário: nenhuma no YAML (a chave está no bloco comentado "brief 044: leitura de rede social pelo Chrome do usuário", sem explicar o número).
- Por que isto é analítico: o que passa de 200.000 caracteres nunca chega ao prompt de extração nem a qualquer gravação; é corte do texto de origem, irrecuperável a jusante.

#### A4-002 — config/limiares.yaml:42 — `coleta.maximo_blocos_por_rede`
- Classe: C
- O que é cortado e quanto: os blocos de publicação lidos por rede do contato, 10 por rede; em `leitor.py:136` a lista de blocos é fatiada (`captura.blocos[: maximo_blocos * _BLOCOS_EXAMINADOS_POR_PUBLICACAO]`) e em `:143` o laço para ao atingir `maximo_blocos` gravados.
- Qual decisão do produto depende desse corte: quantos trechos da rede social vão à tarefa `extrair_captura_rede_social` e viram fato do contato.
- Trecho de código (copiado):
  ```
  maximo_blocos_por_rede: 10      # blocos lidos por rede do contato; cada um custa uma chamada ao modelo
  ```
- Justificativa existente no código/comentário: o comentário da própria linha ("cada um custa uma chamada ao modelo") e `leitor.py:27` ("Os primeiros blocos de uma página costumam ser menu e cabeçalho: o limite de `maximo_blocos` vale..."). Comentário não é aprovação; o ponto continua.
- Por que isto é analítico: do 11º bloco em diante o conteúdo publicado não é lido por modelo nenhum.

#### A4-003 — config/limiares.yaml:43 — `coleta.maximo_imagens_por_rede`
- Classe: C
- O que é cortado e quanto: as imagens publicadas descritas por rede, 8 (o padrão do modelo em `configuracao.py:192` é 0, isto é, sem a chave no YAML não se lê imagem nenhuma).
- Qual decisão do produto depende desse corte: quantas descrições a tarefa `descrever_imagem` produz e, portanto, quantos fatos `[de imagem]` a redação recebe.
- Trecho de código (copiado):
  ```
  maximo_imagens_por_rede: 8      # imagens publicadas descritas por rede (modelo de visão); 0 = não lê
  ```
- Justificativa existente no código/comentário: só o comentário da linha (explica o 0, não o 8).
- Por que isto é analítico: a 9ª imagem em diante nunca é descrita; o conteúdo dela não existe para o sistema.

#### A4-004 — config/limiares.yaml:44 — `coleta.largura_minima_imagem`
- Classe: C
- O que é cortado e quanto: imagens com menos de 250 px de largura são descartadas antes de qualquer descrição.
- Qual decisão do produto depende desse corte: entrada da tarefa `descrever_imagem` (`navegador.py:140,147`).
- Trecho de código (copiado):
  ```
  largura_minima_imagem: 250      # abaixo disso é ícone ou foto de perfil, não publicação
  ```
- Justificativa existente no código/comentário: o comentário da linha ("abaixo disso é ícone ou foto de perfil").
- Por que isto é analítico: é descarte de item de conteúdo por critério de tamanho, decidido antes de ver o conteúdo; publicação pequena some junto com os ícones.

#### A4-005 — config/limiares.yaml:71 — `whatsapp.meses_extraidos`
- Classe: C
- O que é cortado e quanto: os meses de conversa do contato extraídos em fatos — só os 24 mais recentes (`sorted(por_mes, reverse=True)[:meses_extraidos]`).
- Qual decisão do produto depende desse corte: a fila de extração (`extrair_de_texto`) e os fatos sobre o contato que a redação usa.
- Trecho de código (copiado):
  ```
  meses_extraidos: 24             # meses mais recentes do contato extraídos em fatos
  # agente_nw/nucleo/database/queries/conversa.py:97
  for mes in sorted(por_mes, reverse=True)[:meses_extraidos]
  ```
- Justificativa existente no código/comentário: o comentário da linha e a docstring de `blocos_por_mes` ("do mais recente para o mais antigo, até `meses_extraidos` meses (brief 061)").
- Por que isto é analítico: mensagem mais antiga que 24 meses está no banco (`conversa_mensagem`, sem limite) mas nunca alimenta extração — texto guardado e não analisado.

#### A4-006 — config/limiares.yaml:72 — `whatsapp.maximo_caracteres_bloco`
- Classe: NA
- O que é cortado e quanto: nada é descartado — 6.000 caracteres é o tamanho de cada **bloco** em que o mês é partido.
- Qual decisão do produto depende desse corte: quantas chamadas de `extrair_de_texto` o mês custa; o conteúdo vai inteiro, repartido.
- Trecho de código (copiado):
  ```
  # agente_nw/nucleo/database/queries/conversa.py:68-76
  if atual and tamanho + len(texto) + 1 > maximo_caracteres:
      blocos.append("\n".join(atual)); atual, tamanho = [], 0
  ```
- Justificativa existente no código/comentário: comentário da linha ("tamanho de cada bloco enviado à extração (cada um é uma chamada)").
- Por que isto é NA: `_em_blocos` fecha o bloco e abre outro; nenhuma mensagem é perdida nem encurtada. (Ressalva, não ponto: uma mensagem única maior que 6.000 caracteres vira um bloco maior que o limite, nunca um texto cortado.)

#### A4-007 — config/limiares.yaml:73 — `whatsapp.trocas_no_prompt`
- Classe: C
- O que é cortado e quanto: o HISTÓRICO do prompt de redação recebe só as 10 últimas mensagens da conversa.
- Qual decisão do produto depende desse corte: prompt da tarefa `redigir_ganchos` (tom da relação), via `orquestracao.py:212`.
- Trecho de código (copiado):
  ```
  trocas_no_prompt: 10            # últimas mensagens no HISTÓRICO da redação, para o tom
  ```
- Justificativa existente no código/comentário: o comentário da linha.
- Por que isto é analítico: o resto da conversa não entra no prompt que decide o texto entregue.

#### A4-008 — config/limiares.yaml:40 — `coleta.maximo_itens_novos_por_feed`
- Classe: C
- O que é cortado e quanto: 15 notícias novas por feed em cada coleta — as mais recentes; o laço para quando atinge o número.
- Qual decisão do produto depende desse corte: o conjunto de itens que recebem embedding, agrupamento, qualificação e cruzamento.
- Trecho de código (copiado):
  ```
  maximo_itens_novos_por_feed: 15  # notícias novas por feed em cada coleta (as mais recentes)
  # agente_nw/coleta/rss/leitor.py:362
  if n_itens_novos_da_fonte >= limiares.maximo_itens_novos_por_feed:
  ```
- Justificativa existente no código/comentário: o comentário da linha.
- Por que isto é analítico: notícia do 16º item em diante não é coletada nem analisada nesta rodada.

#### A4-009 — config/limiares.yaml:41 — `coleta.tempo_maximo_segundos`
- Classe: C
- O que é cortado e quanto: a coleta inteira para em 240 s e segue com o que já tem (`limite = inicio + tempo_maximo_segundos`).
- Qual decisão do produto depende desse corte: quais feeds entram no corpus do pedido; os que ficaram de fora não são analisados.
- Trecho de código (copiado):
  ```
  tempo_maximo_segundos: 240  # teto de uma coleta; passado isso ela para e segue com o que já tem
  ```
- Justificativa existente no código/comentário: o comentário da linha.
- Por que isto é analítico: é corte de coleção dependente do relógio — o conjunto analisado muda sem o usuário saber.

#### A4-010 — config/limiares.yaml:37 — `coleta.candidatos_suficientes`
- Classe: C
- O que é cortado e quanto: as buscas seguintes não são abertas depois de 10 notícias novas.
- Qual decisão do produto depende desse corte: o corpus do pedido (termos de busca que nunca vão à rede).
- Trecho de código (copiado):
  ```
  # agente_nw/coleta/rss/leitor.py:275
  if caminho_sentinela.exists() or resumo.itens_novos >= limiares.candidatos_suficientes:
  ```
- Justificativa existente no código/comentário: comentário da linha 37 ("notícias novas que bastam: as buscas seguintes não são abertas") e docstring em `leitor.py:210`.
- Por que isto é analítico: assunto que só apareceria na 3ª busca não existe para o cruzamento.

#### A4-011 — config/limiares.yaml:35 — `coleta.max_consultas_por_pedido`
- Classe: C
- O que é cortado e quanto: 4 buscas de notícia por pedido; `selecionar_termos` devolve no máximo esse número de termos entre assunto, contato, `termos_busca` e `interessa`.
- Qual decisão do produto depende desse corte: quais eixos do pedido chegam a virar busca (e, portanto, notícia analisada).
- Trecho de código (copiado):
  ```
  # agente_nw/nucleo/consulta.py:172
  contexto, termos_contato, limiares.coleta.max_consultas_por_pedido
  ```
- Justificativa existente no código/comentário: comentário da linha 35 (lista os quatro eixos).
- Por que isto é analítico: termo descartado não traz notícia, e o pedido é avaliado como se a cobertura fosse completa.

#### A4-012 — config/limiares.yaml:36 — `coleta.horas_reuso_termo`
- Classe: C
- O que é cortado e quanto: termo buscado há menos de 24 h não volta à rede; vale o resultado anterior.
- Qual decisão do produto depende desse corte: o corpus de notícias do pedido (notícia publicada nas últimas horas não aparece).
- Trecho de código (copiado):
  ```
  # agente_nw/coleta/rss/leitor.py:135
  return agora - datetime.fromisoformat(quando) < timedelta(hours=limiares.horas_reuso_termo)
  ```
- Justificativa existente no código/comentário: comentário da linha 36 e docstring em `leitor.py:209`.
- Por que isto é analítico: é reaproveitamento de coleção parcial; o que surgiu depois da última busca não é analisado.

#### A4-013 — config/limiares.yaml:31 — `coleta.retencao_texto_dias`
- Classe: C
- O que é cortado e quanto: o texto da notícia vive 90 dias; depois disso o agrupamento só considera a janela `data_item - 90 dias`.
- Qual decisão do produto depende desse corte: reabertura de assunto e agrupamento (`agrupador.py:95`), que é entrada de qualificação e cruzamento.
- Trecho de código (copiado):
  ```
  # agente_nw/nucleo/agrupamento/agrupador.py:95
  desde_reabertura = _subtrai_dias(data_item, limiares.coleta.retencao_texto_dias)
  ```
- Justificativa existente no código/comentário: comentário em `scripts/migracoes/001_inicial.sql:83` (`texto TEXT, -- vive 90 dias`).
- Por que isto é analítico: assunto mais antigo que a janela não é reaberto nem recomparado, embora a linha do item continue no banco.

#### A4-014 — config/limiares.yaml:29 — `coleta.teaser_minimo_caracteres`
- Classe: C
- O que é cortado e quanto: notícia com corpo abaixo de 400 caracteres é descartada inteira como ruído, antes de qualquer análise.
- Qual decisão do produto depende desse corte: entrada de embedding, agrupamento, qualificação e cruzamento.
- Trecho de código (copiado):
  ```
  # agente_nw/coleta/rss/ruido.py:51
  if corpo is None or len(corpo) < limiares.teaser_minimo_caracteres:
      return True, "corpo abaixo do teaser mínimo"
  ```
- Justificativa existente no código/comentário: nenhuma além do nome ("teaser") e do motivo devolvido.
- Por que isto é analítico: é descarte de item de conteúdo decidido por tamanho, sem que o texto seja lido — notícia curta e relevante vira ruído. (Registro anexo, de outro arquivo: `ruido.py:56` analisa só as três primeiras linhas do corpo para achar "patrocinado" — ponto da parte que audita `coleta/rss/ruido.py`.)

#### A4-015 — config/limiares.yaml:30 — `coleta.dias_max_primeira_aparicao`
- Classe: C
- O que é cortado e quanto: item cuja publicação é mais de 7 dias anterior à primeira coleta é descartado como ruído.
- Qual decisão do produto depende desse corte: o mesmo corpus de notícias analisado adiante.
- Trecho de código (copiado):
  ```
  # agente_nw/coleta/rss/ruido.py:68
  if dias_ate_coleta > limiares.dias_max_primeira_aparicao:
  ```
- Justificativa existente no código/comentário: nenhuma no YAML; só o motivo devolvido pelo código.
- Por que isto é analítico: descarta item de conteúdo por data, não por conteúdo; o texto nunca é analisado.

#### A4-016 — config/limiares.yaml:5-6 — `agrupamento.janela_dias` e `itens_para_dividir`
- Classe: C
- O que é cortado e quanto: o agrupamento compara só itens dentro de 7 dias (`agrupador.py:94,187`); só assuntos com mais de 12 itens são examinados para divisão (`:191`).
- Qual decisão do produto depende desse corte: formação dos assuntos (quem agrupa com quem), base de tudo o que vem depois.
- Trecho de código (copiado):
  ```
  # agente_nw/nucleo/agrupamento/agrupador.py:187,191
  antes_de = _subtrai_dias(data_referencia, limiares.agrupamento.janela_dias)
  for assunto in assuntos.listar_maiores_que(conexao, limiares.agrupamento.itens_para_dividir):
  ```
- Justificativa existente no código/comentário: nenhuma para `janela_dias`; o `cosseno_mesmo_assunto` da linha 2 traz "calibrar no brief 007".
- Por que isto é analítico: item fora da janela não é comparado; assunto com 12 itens ou menos nunca é revisto.

#### A4-017 — config/limiares.yaml:10 — `qualificacao.teto_por_dia`
- Classe: C
- O que é cortado e quanto: no máximo 40 assuntos qualificados por dia (`qualificar_pendentes(..., teto_por_dia, ...)`).
- Qual decisão do produto depende desse corte: a tarefa `qualificar`; assunto que não cabe no teto fica sem `substancial`/`conversavel` e não entra no cruzamento daquele pedido.
- Trecho de código (copiado):
  ```
  # agente_nw/nucleo/consulta.py:204
  cliente_llm, conexao, limiares.qualificacao.teto_por_dia, vetores_extras=[centroide_consulta]
  ```
- Justificativa existente no código/comentário: nenhuma.
- Por que isto é analítico: é teto de coleção sobre o que o modelo chega a ler.

#### A4-018 — config/limiares.yaml:45-46 — `cartao.teto_por_dia`
- Classe: C
- O que é cortado e quanto: 40 cartões por dia (limite da geração de cartão, validado em `configuracao.py:216`).
- Qual decisão do produto depende desse corte: a tarefa `cartao` (resumo do assunto); assunto além do teto não ganha cartão naquele dia.
- Trecho de código (copiado):
  ```
  cartao:
    teto_por_dia: 40
  ```
- Justificativa existente no código/comentário: nenhuma.
- Por que isto é analítico: decide quais assuntos têm resumo gerado por modelo. Dúvida registrada: o cartão é também material de tela; o teto limita a geração, não só a exibição.

#### A4-019 — config/limiares.yaml:18-19 — `conector.candidatos_por_contato` e `itens_no_menu`
- Classe: C
- O que é cortado e quanto: 10 candidatos avaliados por contato e só os 5 primeiros da ordenação entram no menu (`demais[: limiares.conector.itens_no_menu]`, nos dois caminhos: 272 e 481).
- Qual decisão do produto depende desse corte: quais assuntos recebem "por quê" (`cruzar_por_que`) e gancho redigido (`redigir_ganchos`); o resto é descartado.
- Trecho de código (copiado):
  ```
  # agente_nw/nucleo/relevancia/cruzamento.py:272
  selecionados_para_menu = demais[: limiares.conector.itens_no_menu]
  ```
- Justificativa existente no código/comentário: nenhuma no YAML.
- Por que isto é analítico: é "top N" que descarta o resto, e a redação só vê os selecionados.

#### A4-020 — config/limiares.yaml:48,54 — `listas.maximo_entradas` e `rodadas_sem_novidade`
- Classe: C
- O que é cortado e quanto: a lista do usuário na rede para em 2.000 entradas ou após 6 rodadas sem novidade; `listas.py:367` marca `truncada = len(entradas) > limiares.maximo_entradas`.
- Qual decisão do produto depende desse corte: a localização da pessoa nas redes do usuário (`localizacao.py`), ou seja, se o contato é encontrado.
- Trecho de código (copiado):
  ```
  # agente_nw/coleta/capturas/listas.py:346
  while len(acumuladas) < limiares.maximo_entradas and sem_novidade < limiares.rodadas_sem_novidade:
  ```
- Justificativa existente no código/comentário: comentário da linha 54 ("listas que carregam aos poucos (Instagram) pedem mais paciência") e docstring em `listas.py:328`.
- Por que isto é analítico: entrada não lida não pode casar com o nome do pedido; o programa decide "não achei" sobre uma lista parcial (há a flag `truncada`, que é aviso, não recuperação).

#### A4-021 — config/limiares.yaml:52 — `listas.maximo_parecidas`
- Classe: C
- O que é cortado e quanto: no máximo 5 entradas parecidas são oferecidas na confirmação "é esta pessoa?".
- Qual decisão do produto depende desse corte: a escolha do perfil do contato (`localizacao.py:260`), com desempate por `desempatar_perfil`.
- Trecho de código (copiado):
  ```
  # agente_nw/nucleo/localizacao.py:260
  conexao, rede, nome, limiares.similaridade_minima, limiares.maximo_parecidas
  ```
- Justificativa existente no código/comentário: nenhuma.
- Por que isto é analítico: a 6ª candidata, ainda acima da similaridade mínima, não é mostrada nem avaliada.

#### A4-022 — config/limiares.yaml:76-77 — `moldes.maximo`
- Classe: C
- O que é cortado e quanto: 2 mensagens-molde de outro contato oferecidas à redação.
- Qual decisão do produto depende desse corte: prompt de `redigir_ganchos` (`orquestracao.py:213` → `redacao.py:174-190`).
- Trecho de código (copiado):
  ```
  maximo: 2                       # mensagens-molde de outro contato oferecidas à redação
  ```
- Justificativa existente no código/comentário: o comentário da linha.
- Por que isto é analítico: é "top N" sobre os moldes; o modelo decide o tom vendo só dois.

#### A4-023 — config/limiares.yaml:67-68 — `redacao.meses_fato_antigo`
- Classe: NA
- O que é cortado e quanto: nada; fato mais velho que 12 meses recebe a marca `[antigo]` e continua no prompt.
- Qual decisão do produto depende disso: a redação não afirma fato marcado como posição atual (`redacao.py:131-141`).
- Trecho de código (copiado):
  ```
  # agente_nw/nucleo/redacao.py:141
  if _e_antigo(fato, data, meses_fato_antigo, hoje):
      marcas.append(_MARCA_ANTIGO)
  ```
- Justificativa existente no código/comentário: comentário da linha 68 ("vai ao prompt marcado [antigo]") e a docstring de `_fatos`.
- Por que isto é NA: é rótulo, não corte — o texto do fato segue inteiro para o prompt (o que de fato o corta é `fato.conteudo[:_TRECHO_DO_FATO_NO_PROMPT]` em `redacao.py:145`, ponto da parte que audita `nucleo/redacao.py`).

#### A4-024 — config/limiares.yaml:82-84 — `temas_usuario.janela_dias_interesse`, `janela_dias_dominio`, `dias_para_decair`
- Classe: C
- O que é cortado e quanto: a inferência do nível de um tema do usuário só conta usos dentro de 30 ou 90 dias; sem uso por 180 dias o peso decai.
- Qual decisão do produto depende desse corte: `perfil_tema.nivel` e `peso`, que entram na pontuação do cruzamento (`peso_nivel`, `peso_aderencia_usuario`).
- Trecho de código (copiado):
  ```
  # agente_nw/perfil/inferencia.py:159-160
  desde_interesse = (hoje - timedelta(days=limiares.janela_dias_interesse)).isoformat()
  desde_dominio = (hoje - timedelta(days=limiares.janela_dias_dominio)).isoformat()
  ```
- Justificativa existente no código/comentário: comentários das linhas 80-84 (regra "3 usos em 30 dias, 6 em 90") e `017_preferencias_usuario_temas.sql:4-8`.
- Por que isto é analítico: uso fora da janela não conta; o perfil é decidido sobre parte do histórico de pedidos.

#### A4-025 — config/limiares.yaml:55 — `listas.redes_so_por_link`
- Classe: NA
- O que é cortado e quanto: hoje nada — a lista está vazia, logo nenhuma rede é excluída da leitura automática.
- Qual decisão do produto depende disso: se a extensão lê a lista daquela rede (`cli.py:988`, `pedido.py:243`, `localizacao.py:282`, `busca.py:49`).
- Trecho de código (copiado):
  ```
  redes_so_por_link: []           # redes que a extensão não deve ler sozinha (ex.: [x]); vazio = todas automáticas
  ```
- Justificativa existente no código/comentário: o comentário da linha.
- Por que isto é NA agora: valor vazio não corta nada. Fica registrado porque, preenchido, passa a ser corte de coleção (rede inteira deixa de ser lida) — então o efeito é analítico quando usado.

#### A4-026 — config/llm_routing.yaml:8-21 e 31-44 — `num_ctx` por tarefa (perfis `air16` e `pro48`)
- Classe: P
- O que é cortado e quanto: o `num_ctx` declarado por tarefa é enviado ao Ollama (`llm.py:352`), mas só a redação confere se o prompt cabe: `cli.py:905-921` e `fluxo.py:364` calculam `limite_tokens = int(num_ctx * FRACAO_DO_CONTEXTO_NO_PROMPT)` para `redigir_ganchos`. As outras 12 tarefas — entre elas `extrair_de_texto`, `extrair_captura_rede_social`, `qualificar`, `cartao`, `cruzar_por_que`, `avaliar_relacao_objetivo` — mandam o texto sem nenhuma verificação de tamanho.
- Qual decisão do produto depende disso: todas essas tarefas; no `air16`, `extrair_de_texto` tem 4.096 tokens de janela e recebe blocos de WhatsApp de até 6.000 caracteres mais o prompt fixo — o excedente é descartado em silêncio pelo servidor.
- Trecho de código (copiado):
  ```
  extrair_de_texto:      {modelo: qwen3:4b, num_ctx: 4096, temperature: 0.2, format: json, think: false, num_predict: 1024}
  # agente_nw/nucleo/llm.py:352
  "num_ctx": tarefa.num_ctx,
  ```
- Justificativa existente no código/comentário: nenhuma no YAML; a única defesa documentada é o `FRACAO_DO_CONTEXTO_NO_PROMPT` da redação.
- Por que isto é analítico: é exatamente a classe P — o texto vai inteiro ao prompt e ninguém confere se cabe na janela.

#### A4-027 — config/llm_routing.yaml:8-21 e 31-44 — `num_predict` por tarefa
- Classe: P
- O que é cortado e quanto: o teto de tokens da resposta (256 a 2.048, ver tabela da §3). Resposta JSON mais longa que o teto é cortada no meio e falha o esquema.
- Qual decisão do produto depende disso: a saída estruturada de toda tarefa (`format: json`); em `redigir_ganchos` (2.048) é o texto entregue ao usuário, em `extrair_de_texto`/`extrair_captura_rede_social` (1.024) é quantos fatos cabem numa extração.
- Trecho de código (copiado):
  ```
  redigir_ganchos:       {modelo: qwen3:4b, num_ctx: 8192, temperature: 0.5, format: json, think: false, num_predict: 2048}
  ```
- Justificativa existente no código/comentário: nenhuma.
- Por que isto é analítico (P): não corta o texto de origem, mas limita em silêncio o que o modelo consegue devolver sobre esse texto — a extração de um bloco grande pode parar antes de relatar todos os fatos que leu.

#### A4-028 — config/llm_routing.yaml:6-7 e 28-29 — `embeddings.modelo: bge-m3`
- Classe: P
- O que é cortado e quanto: o `bge-m3` corta em silêncio acima de 8.192 tokens; nenhum lugar do projeto mede o texto antes de pedir embedding (grep por `num_ctx` não encontra nada no caminho de embedding; não há contagem de tokens).
- Qual decisão do produto depende disso: todos os vetores — `vetor_item`, `vetor_assunto`, `vetor_tema`, `vetor_perfil` —, logo o agrupamento por cosseno, a adjacência contato/assunto e `conector.consulta.minima`.
- Trecho de código (copiado):
  ```
  embeddings:
    modelo: bge-m3
  ```
- Justificativa existente no código/comentário: nenhuma sobre tamanho; o comentário em `019_proveniencia.sql:11-12` só registra que os dois perfis sempre usaram esse modelo e que `Roteamento` recusa perfil com outro.
- Por que isto é analítico (P): notícia longa ou bloco grande é vetorizado só pelo começo, e o cosseno é usado como se representasse o texto inteiro.

#### A4-029 — extensao/background.js:147-150 — `tratar`, ação `estado`
- Classe: T (ponto de passagem do corte)
- O que é cortado e quanto: o texto da página; o programa manda `maximo` (200.000, A4-001) e o `background.js` o entrega a `globalThis.agenteNw.estado(max)`, que devolve o `innerText` já limitado.
- Qual decisão do produto depende desse corte: todo o conteúdo de rede social que chega à extração (`extrair_captura_rede_social`).
- Trecho de código (copiado):
  ```
  return await comNovaTentativa(tarefa.aba_id, (max) => globalThis.agenteNw.estado(max), [
    tarefa.maximo,
  ]);
  ```
- Justificativa existente no código/comentário: nenhuma; o cabeçalho do arquivo só diz que o conjunto de ações é fixo.
- Por que isto é analítico: é corte do texto de origem no navegador, irrecuperável a jusante. O corte em si é aplicado dentro de `extensao/conteudo.js` (arquivo que não está nesta lista — fica como pendência de leitura para quem o tiver); aqui está provado que o limite é repassado e usado.

#### A4-030 — extensao/background.js:119-124 — `imagens`
- Classe: C (ponto de passagem do corte)
- O que é cortado e quanto: a lista de imagens da página é pedida já limitada por `maximo` (8, A4-003), `largura_minima` (250, A4-004) e `ignorar`.
- Qual decisão do produto depende desse corte: quantas imagens a tarefa `descrever_imagem` descreve e, portanto, quantos fatos `[de imagem]` existem.
- Trecho de código (copiado):
  ```
  (opcoes) => globalThis.agenteNw.listarImagens(opcoes),
  [{ maximo: tarefa.maximo, largura_minima: tarefa.largura_minima, ignorar: tarefa.ignorar }],
  ```
- Justificativa existente no código/comentário: comentário da linha 118 ("Só LÊ: baixa os bytes das imagens publicadas (para serem descritas)").
- Por que isto é analítico: imagem fora da lista nunca é descrita; o conteúdo dela não existe para o sistema.

#### A4-031 — extensao/background.js:98 e 132 — `imagens` / `LIMITE_BYTES_IMAGEM`
- Classe: C
- O que é cortado e quanto: imagem com mais de 6 MB (`6 * 1024 * 1024`) é pulada depois de baixada; nenhuma descrição é gerada e nenhum aviso é devolvido.
- Qual decisão do produto depende desse corte: entrada da tarefa `descrever_imagem`.
- Trecho de código (copiado):
  ```
  const LIMITE_BYTES_IMAGEM = 6 * 1024 * 1024;
  if (buffer.byteLength > LIMITE_BYTES_IMAGEM) continue;
  ```
- Justificativa existente no código/comentário: nenhuma (a constante não tem comentário).
- Por que isto é analítico: descarta item de conteúdo por tamanho de arquivo, critério sem relação com o que a imagem mostra; a foto em alta resolução é justamente a mais informativa.

#### A4-032 — extensao/background.js:96-107 e 128 — `imagemPermitida`
- Classe: C
- O que é cortado e quanto: imagem servida por host fora de `HOSTS_DE_IMAGEM` (8 domínios das quatro redes e seus CDNs) é descartada sem download.
- Qual decisão do produto depende desse corte: entrada da tarefa `descrever_imagem`.
- Trecho de código (copiado):
  ```
  for (const img of lista) {
    if (!imagemPermitida(img.src)) continue;
  ```
- Justificativa existente no código/comentário: o cabeçalho do arquivo ("só age em linkedin, instagram, facebook e x") e `manifest.json:12-21` (`host_permissions`), que é a trava real do navegador.
- Por que isto é analítico, com ressalva: é restrição estrutural de origem (coerente com o AGENTS §4, "bloqueado na origem"), mas o efeito prático é que imagem publicada hospedada em outro CDN não é analisada e isso não aparece em nenhum aviso.

#### A4-033 — extensao/background.js:129-136 — `imagens`, falha de download
- Classe: C
- O que é cortado e quanto: imagem cujo `fetch` não responde `ok`, ou lança, é pulada em silêncio (um `catch` vazio com comentário).
- Qual decisão do produto depende desse corte: entrada da tarefa `descrever_imagem`; a contagem de imagens descritas cai sem explicação.
- Trecho de código (copiado):
  ```
  } catch (e) {
    // imagem que não baixa é pulada
  }
  ```
- Justificativa existente no código/comentário: o próprio comentário citado ("imagem que não baixa é pulada") — descrição, não aprovação.
- Por que isto é analítico: item de conteúdo sai da coleção analisada sem registro; a jusante não há como saber que faltou.

#### A4-034 — extensao/background.js:76 e 88-93 — `abrir` / `comNovaTentativa`
- Classe: C
- O que é cortado e quanto: `carregada(aba.id, 30000)` desiste de esperar o carregamento em 30 s e segue; a nova tentativa espera 10 s (`carregada(abaId, 10000)`). A leitura acontece sobre o que estiver desenhado nesse instante.
- Qual decisão do produto depende desse corte: o texto e os links lidos da rede social (ações `estado`, `rolar`, `links`), entrada de `extrair_captura_rede_social` e da localização do contato.
- Trecho de código (copiado):
  ```
  await carregada(aba.id, 30000);
  ```
- Justificativa existente no código/comentário: comentário da linha 86 ("Uma navegação no meio da leitura (ex.: volta do login) derruba a injeção: tenta de novo uma vez").
- Por que isto é analítico (com a dúvida registrada): o tempo limite não corta um texto por si; mas, estourado, a página é lida pela metade e a análise segue como se fosse a página inteira. Há mitigação parcial no backend (`extensao_backend.py:70-82`, espera `espera_render_s` quando o texto está curto), que não cobre página longa parcialmente desenhada.

#### A4-035 — scripts/agente_entregar.sh:115 e 130 — `tail -n 5` / `tail -n 3`
- Classe: NA
- O que é cortado e quanto: as últimas 5 (ou 3) linhas do log de entrega mostradas na tela, quando o commit ou o push falha.
- Qual decisão do produto depende disso: nenhuma; o log completo fica em `logs/entregar_ultimo.txt`.
- Trecho de código (copiado):
  ```
  tail -n 5 "$LOG"
  ```
- Justificativa existente no código/comentário: cabeçalho do arquivo ("O detalhe vai para logs/entregar_ultimo.txt").
- Por que isto é NA: corte de apresentação de log; nenhum valor cortado entra em prompt, embedding, hash ou filtro, e o arquivo inteiro continua no disco.

#### A4-036 — scripts/agente_entregar.sh:74 — leitura do `git status --porcelain`
- Classe: NA
- O que é cortado e quanto: os 3 primeiros caracteres de cada linha (`${linha:3}`), que são o código de estado do git, e o lado esquerdo de um `->` em renomeação.
- Qual decisão do produto depende disso: só a comparação entre caminhos alterados e o manifesto do commit.
- Trecho de código (copiado):
  ```
  caminho="${linha:3}"
  caminho="${caminho##* -> }"
  ```
- Justificativa existente no código/comentário: nenhuma explícita; é o formato documentado do `--porcelain`.
- Por que isto é NA: corte de identificador/formato (prefixo de estado), não de texto de conteúdo.

#### A4-037 — scripts/agente_lacunas.py:104-108 — `main`
- Classe: NA
- O que é cortado e quanto: se o glob `doc_<NNN>_*.md` casar com mais de um relatório, só o primeiro em ordem alfabética é lido (`relatorios[0]`).
- Qual decisão do produto depende disso: quais linhas de lacuna vão ao `docs/PLAN.md`; não toca nenhum texto do produto.
- Trecho de código (copiado):
  ```
  relatorios = sorted((args.raiz / "docs" / "docs").glob(f"doc_{args.numero}_*.md"))
  lacunas = ler_lacunas(relatorios[0].read_text())
  ```
- Justificativa existente no código/comentário: a docstring do módulo ("Lê a tabela de `## Lacunas` de `docs/docs/doc_<NNN>_*.md`").
- Por que isto é NA: é ferramenta de entrega sobre documentação; nada daqui alimenta LLM, embedding, hash ou filtro do produto. (Vale como observação de qualidade, não como violação do princípio.)

#### A4-038 — scripts/agente_lacunas.py:50-53 — `ler_lacunas`
- Classe: NA
- O que é cortado e quanto: havendo mais de uma seção `## Lacunas` no relatório, só a última é lida (`inicios[-1]`), e a tabela é lida de `tabela[2:]` (descarta cabeçalho e separador).
- Qual decisão do produto depende disso: as linhas copiadas para o PLAN.
- Trecho de código (copiado):
  ```
  inicios = [i for i, linha in enumerate(linhas) if linha.strip() == "## Lacunas"]
  corpo = linhas[inicios[-1] + 1 :]
  ```
- Justificativa existente no código/comentário: a docstring de `ler_lacunas` ("da última seção `## Lacunas`").
- Por que isto é NA: corte de estrutura de documento numa ferramenta de processo; `tabela[2:]` descarta cabeçalho e separador de Markdown, que não são conteúdo.

#### A4-039 — scripts/commitar.sh:83 — `git log --oneline -3`
- Classe: NA
- O que é cortado e quanto: a exibição do histórico depois do commit, 3 linhas.
- Qual decisão do produto depende disso: nenhuma; é confirmação visual.
- Trecho de código (copiado):
  ```
  git log --oneline -3
  ```
- Justificativa existente no código/comentário: cabeçalho do arquivo, passo 8.
- Por que isto é NA: apresentação pura; nenhum texto de conteúdo passa por este script (ele só lê o arquivo de mensagem de commit e o repassa inteiro a `git commit -F`).

#### A4-040 — scripts/verificar.sh:40,48,55,62,65 — `etapa`/`falhou`
- Classe: NA
- O que é cortado e quanto: na falha, mostra `head -n 15` da saída da etapa (e, no pytest, as linhas `FAILED|ERROR` mais `tail -n 1`); a saída completa de cada etapa vai para `logs/verificar_ultimo.txt`.
- Qual decisão do produto depende disso: nenhuma; o código de saída do gate vem do comando, não do trecho mostrado.
- Trecho de código (copiado):
  ```
  head -n 15 "$PARCIAL"
  grep -E '^(FAILED|ERROR) ' "$PARCIAL" || true
  ```
- Justificativa existente no código/comentário: cabeçalho do arquivo ("A saída completa vai para logs/verificar_ultimo.txt. Na tela fica 'ok' ou 'falhou' por etapa").
- Por que isto é NA: corte de apresentação de log, com o original preservado em arquivo; nada alimenta análise.

## 3. `num_ctx` e `num_predict` por tarefa, nos dois perfis (`config/llm_routing.yaml`)

Perfil ativo nesta máquina: `pro48` (`config/local.yaml:5`, `perfil_llm: pro48`); o padrão versionado do
arquivo é `air16` (`llm_routing.yaml:1`). Embeddings: `bge-m3` nos dois perfis (`air16` linhas 6-7,
`pro48` linhas 28-29). `pro48` tem `enviar_think: false` (linha 27). Nos dois perfis
`nova_tentativa: {temperature: 0.1, maximo: 1}`.

| Tarefa | air16 modelo | air16 `num_ctx` | air16 `num_predict` | pro48 modelo | pro48 `num_ctx` | pro48 `num_predict` |
| --- | --- | --- | --- | --- | --- | --- |
| qualificar | qwen3:4b | 2048 | 256 | qwen2.5:14b | 8192 | 256 |
| rotular | qwen3:4b | 2048 | 256 | qwen2.5:14b | 8192 | 256 |
| cartao | qwen3:4b | 4096 | 1024 | qwen2.5:14b | 16384 | 1024 |
| cruzar_por_que | qwen3:4b | 4096 | 512 | qwen2.5:14b | 16384 | 512 |
| avaliar_relacao_objetivo | qwen3:4b | 4096 | 512 | qwen2.5:14b | 16384 | 512 |
| extrair_de_texto | qwen3:4b | 4096 | 1024 | qwen2.5:14b | 16384 | 1024 |
| extrair_captura_rede_social | qwen3:4b | 4096 | 1024 | qwen2.5:14b | 16384 | 1024 |
| extrair_pedido | qwen3:4b | 4096 | 512 | qwen2.5:14b | 8192 | 512 |
| desempatar_perfil | qwen3:4b | 2048 | 256 | qwen2.5:14b | 2048 | 256 |
| redigir_ganchos | qwen3:4b | 8192 | 2048 | qwen2.5:14b | 16384 | 2048 |
| extrair_termos_contato | qwen3:4b | 4096 | 512 | qwen2.5:14b | 4096 | 512 |
| descrever_tema | qwen3:4b | 2048 | 512 | qwen2.5:14b | 2048 | 512 |
| descrever_imagem | gemma3:4b | 4096 | 1024 | gemma3:12b | 4096 | 1024 |
| prerotular_calibracao | qwen3:8b | 2048 | 512 | qwen2.5:14b | 8192 | 512 |

Confronto que importa ao relatório: só `redigir_ganchos` tem orçamento de prompt calculado a partir do
`num_ctx` (`cli.py:905-921`, `fluxo.py:364`, `console/app.py:164`). `extrair_de_texto` recebe blocos de
WhatsApp de até 6.000 caracteres (`limiares.yaml:72`) com 4.096 tokens de janela no `air16`;
`extrair_captura_rede_social` recebe blocos de página limitados a 200.000 caracteres no total
(`limiares.yaml:59`) com 4.096 (air16) / 16.384 (pro48) tokens de janela. Nenhuma das duas confere o
tamanho do prompt (A4-026).
