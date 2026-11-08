# Auditoria "texto por inteiro" — parte A1 (prefixo `A1`)

Lista: `parte_A1.txt` (26 arquivos, 3.609 linhas; totais conferidos com `wc -l`). Todos os arquivos
foram lidos do início à última linha. Nada foi editado, executado ou commitado.

## 1. Tabela de certificação

| Arquivo | Linhas lidas/total | Resultado | Evidência (uma linha) | Ponto |
| --- | --- | --- | --- | --- |
| `agente_nw/coleta/__init__.py` | 0/0 | CERTIFICADO | arquivo vazio: não manipula texto de conteúdo (só marca o pacote) | — |
| `agente_nw/coleta/capturas/__init__.py` | 0/0 | CERTIFICADO | arquivo vazio: não manipula texto de conteúdo (só marca o pacote) | — |
| `agente_nw/coleta/capturas/busca.py` | 151/151 | CORTA | o texto do cartão de cada candidato da busca da rede vira `nome_exibido` + 4 linhas de descrição; o resto do cartão é descartado antes de o candidato ser ordenado e mostrado | A1-001, A1-002 |
| `agente_nw/coleta/capturas/extrator.py` | 73/73 | CORTA | o bloco capturado vai inteiro ao prompt (bom), mas sem nenhuma conferência de janela, e o que é gravado é o "texto essencial" que o modelo devolve, não o bloco | A1-003, A1-004 |
| `agente_nw/coleta/capturas/imagens.py` | 68/68 | CORTA | a imagem inteira (base64) vai ao modelo de visão, mas o prompt limita a descrição a "2 a 5 frases" e essa descrição é tudo o que sobra da imagem a jusante | A1-005 |
| `agente_nw/coleta/capturas/listas.py` | 408/408 | CORTA | de cada cartão da lista ficam o nome e até 3 linhas de cabeçalho; a lista inteira é lida só até `maximo_entradas` / 3 rodadas sem novidade | A1-006, A1-007, A1-008 |
| `agente_nw/coleta/capturas/navegador.py` | 149/149 | CORTA | blocos fora da faixa 30–5.000 caracteres são jogados fora inteiros, a página é lida só em 5 rolagens e as imagens param no `maximo` | A1-009, A1-010, A1-011 |
| `agente_nw/coleta/rss/__init__.py` | 0/0 | CERTIFICADO | arquivo vazio: não manipula texto de conteúdo (só marca o pacote) | — |
| `agente_nw/coleta/rss/canonicalizar.py` | 59/59 | CORTA | `url_canonica` só normaliza URL (não é corte de conteúdo), mas `hash_titulo` resolve a deduplicação olhando apenas o título da notícia | A1-012 |
| `agente_nw/coleta/rss/fonte_alternativa.py` | 41/41 | CERTIFICADO | só monta a URL do RSS do Bing e desembrulha o redirecionador (`parse_qs(...)["url"]`): nenhum texto de notícia passa por aqui | — |
| `agente_nw/coleta/rss/google_news.py` | 86/86 | CORTA | os termos de busca que definem o que será coletado são cortados em quatro lugares (4 por tema, 3 do contato, 6 de `termos_busca`, 5 de `interessa`, e `[:maximo]` no fim) | A1-013 |
| `agente_nw/coleta/rss/leitor.py` | 365/365 | CORTA | o corpo da notícia é extraído inteiro por `trafilatura` e gravado inteiro, mas a deduplicação decide pelo hash do título, item sem corpo é gravado só com título, e o feed/pedido para em três limites diferentes | A1-014, A1-015, A1-016 |
| `agente_nw/coleta/whatsapp/__init__.py` | 0/0 | CERTIFICADO | arquivo vazio: não manipula texto de conteúdo (só marca o pacote) | — |
| `agente_nw/coleta/whatsapp/importador.py` | 60/60 | CORTA | grava todas as mensagens da conversa inteiras, mas só enfileira para extração os `meses_extraidos` meses mais recentes | A1-017 |
| `agente_nw/coleta/whatsapp/leitor.py` | 118/118 | CORTA | reconstrói mensagens de várias linhas sem perder nada, mas lê só um `.txt` do zip e descarta por substring a mensagem que contenha marca de mídia/apagada | A1-018, A1-019 |
| `agente_nw/nucleo/__init__.py` | 0/0 | CERTIFICADO | arquivo vazio: não manipula texto de conteúdo (só marca o pacote) | — |
| `agente_nw/nucleo/confirmacao.py` | 196/196 | CORTA | diálogo de confirmação no terminal; a paginação da lista ("Enter = mais") não perde nada, mas o menu de candidatos mostra só os 5 primeiros | A1-020 |
| `agente_nw/nucleo/consulta.py` | 268/268 | CORTA | orquestra a consulta: o texto do pedido é embeddado sem conferir a janela do `bge-m3`, e os tetos de blocos/imagens, de qualificação e de histórico entram daqui | A1-021, A1-022, A1-023, A1-024, A1-025, A1-026 |
| `agente_nw/nucleo/fluxo.py` | 482/482 | CORTA | fluxo do pedido (status, perguntas, retomada); não lê texto de conteúdo, mas é aqui que nasce o orçamento de prompt `num_ctx * 0,73` que corta o prompt da redação | A1-027 |
| `agente_nw/nucleo/localizacao.py` | 412/412 | CORTA | localiza a pessoa nas redes; o desempate por LLM vê só o `cabecalho` de cada candidata, os parecidos param em `maximo_parecidas` e a deduplicação do fato olha 200 fatos | A1-028, A1-029, A1-030, A1-031 |
| `agente_nw/nucleo/orquestracao.py` | 218/218 | CORTA | só encadeia os passos e repassa parâmetros; dois desses parâmetros são cortes do prompt da redação (trocas de WhatsApp e moldes) | A1-032 |
| `agente_nw/nucleo/pedido.py` | 251/251 | CORTA | a frase do pedido vai inteira ao prompt de `extrair_pedido`, mas acompanhada de só 50 contatos e sem conferência de janela | A1-033, A1-034 |
| `agente_nw/nucleo/saidas/__init__.py` | 0/0 | CERTIFICADO | arquivo vazio: não manipula texto de conteúdo (só marca o pacote) | — |
| `agente_nw/nucleo/saidas/markdown.py` | 112/112 | NÃO ANALÍTICO | gera o menu em Markdown (título + "por quê" + cartão) e relê só as marcações `[x]`/motivos; nenhum texto de conteúdo é analisado aqui | A1-035 |
| `agente_nw/nucleo/texto.py` | 61/61 | CERTIFICADO | funções de nome próprio: `casa_nome` e `similaridade_nome` usam todas as palavras das duas cadeias (`_palavras` não descarta nada) e `variantes_do_nome` acrescenta variantes sem remover o nome completo | — |
| `agente_nw/nucleo/vetores.py` | 31/31 | CERTIFICADO | não manipula texto de conteúdo: só infraestrutura numérica (cosseno e centróide ponderado sobre vetores já prontos) | — |

Resumo: 26 arquivos — 9 `CERTIFICADO`, 16 `CORTA`, 1 `NÃO ANALÍTICO`, 0 `NÃO CONFERIDO`.

## 2. Pontos encontrados

#### A1-001 — agente_nw/coleta/capturas/busca.py:112 — `_filtrar_candidatos`
- Classe: R
- O que é cortado e quanto: do texto do cartão do resultado de busca da rede social sobram a 1ª linha (`nome_exibido`) e as linhas 2 a 5 (`linhas[1:5]`), unidas por " · "; da 6ª linha em diante nada chega à `descricao`. Cartão com uma linha só fica com `descricao` vazia.
- Qual decisão do produto depende desse corte: a ordenação dos candidatos por pistas (`localizacao._casamento_com_pistas(c.descricao, pedido.pessoa_pistas)`, `localizacao.py:232`), o `cabecalho` da `Opcao` (que depois alimenta o prompt da tarefa `desempatar_perfil` e o `_pontuar`), o que o usuário vê para escolher a pessoa e, confirmada a escolha, o fato `lista_rede_social` e o campo `notas` do contato (`localizacao.confirmar`).
- Trecho de código (1 a 3 linhas, copiado):
  ```python
  nome_exibido = linhas[0] if linhas else ""
  descricao = " · ".join(linhas[1:5]) if len(linhas) > 1 else ""
  ```
- Justificativa existente no código/comentário (cite o lugar) ou "nenhuma": nenhuma para o `[1:5]`; o comentário vizinho (`busca.py:111`) justifica só o descarte de link sem texto ("link sem texto (ícone, menu): não é uma pessoa para o usuário escolher").
- Por que isto é analítico (T/C/R/P) ou só apresentação/log/identificador (NA): o valor cortado é exatamente o que ordena os candidatos e o que vai ao prompt de desempate — decisão de produto (quem é a pessoa), não tela. É R porque o cartão inteiro é substituído por um recorte de 4 linhas e o resto do caminho trata esse recorte como se fosse a descrição do perfil.

#### A1-002 — agente_nw/coleta/capturas/busca.py:140 — `buscar`
- Classe: NA
- O que é cortado e quanto: os primeiros 120 caracteres do texto da página, com espaços colapsados.
- Qual decisão do produto depende desse corte: nenhuma; só a frase de aviso ("sem sessão ativa em …") que o usuário lê.
- Trecho de código (1 a 3 linhas, copiado):
  ```python
  resumo = " ".join(texto.split())[:120]
  ```
- Justificativa existente no código/comentário (cite o lugar) ou "nenhuma": nenhuma no local; a docstring de `buscar` (`busca.py:120-126`) explica que a função devolve `autenticado=False` "com motivo".
- Por que isto é analítico (T/C/R/P) ou só apresentação/log/identificador (NA): o `resumo` só entra no campo `motivo` de `ResultadoBusca`, que é mostrado como aviso (`confirmacao.py:147`, `localizacao.py:285`) e nunca é embeddado, hasheado ou enviado a prompt. Apresentação.

#### A1-003 — agente_nw/coleta/capturas/extrator.py:68 — `extrair`
- Classe: P
- O que é cortado e quanto: nada é cortado aqui, e é esse o problema: o bloco (até 5.000 caracteres, `navegador._BLOCO_TAMANHO_MAXIMO`) é interpolado no prompt e enviado sem nenhuma medição contra o `num_ctx` da tarefa `extrair_captura_rede_social`. Acima da janela, o corte acontece do lado do modelo, em silêncio.
- Qual decisão do produto depende desse corte: a tarefa de LLM `extrair_captura_rede_social`, que decide se o bloco é publicação ou interface (`descartar`), a data do fato e o `conteudo` gravado como fato do contato.
- Trecho de código (1 a 3 linhas, copiado):
  ```python
  prompt = construir_prompt(bloco, rede)
  resposta = cliente_llm.gerar_json("extrair_captura_rede_social", prompt, RespostaCapturaRedeSocial)
  ```
- Justificativa existente no código/comentário (cite o lugar) ou "nenhuma": nenhuma; não há menção a janela nem a contagem de tokens em todo o arquivo.
- Por que isto é analítico (T/C/R/P) ou só apresentação/log/identificador (NA): é exatamente o caso P — texto de conteúdo entra num prompt de decisão sem ninguém conferir se o prompt cabe. Comparar com `fluxo.py:34/364` (A1-026), onde a redação ganhou um orçamento de tokens: aqui não existe nenhum.

#### A1-004 — agente_nw/coleta/capturas/extrator.py:53-54 — `construir_prompt`
- Classe: R
- O que é cortado e quanto: quantidade indeterminada — o prompt manda o modelo devolver "o texto essencial da publicação, limpo", e o que fica gravado é esse recorte feito pelo modelo, não o bloco capturado. O bloco original não é guardado em lugar nenhum (`imagens`/`blocos` morrem com a execução).
- Qual decisão do produto depende desse corte: todo o resto do caminho do fato de rede social — o `conteudo` devolvido é o que é gravado como fato, embeddado para os termos do contato e usado nos prompts de redação.
- Trecho de código (1 a 3 linhas, copiado):
  ```python
  - conteudo: o texto essencial da publicação, limpo, sem sugestões laterais
    nem prompts de interface. Sem chamar atenção do modelo para nada que não
  ```
- Justificativa existente no código/comentário (cite o lugar) ou "nenhuma": o próprio prompt diz por que ("sem sugestões laterais nem prompts de interface"); a docstring de `RespostaCapturaRedeSocial` (`extrator.py:12-14`) só explica o `descartar`.
- Por que isto é analítico (T/C/R/P) ou só apresentação/log/identificador (NA): o texto da publicação é substituído por uma versão menor antes de qualquer análise posterior, e essa análise posterior trata o recorte como se fosse a publicação. A limpeza de interface é legítima, mas quem define o quanto sai é o modelo, sem limite escrito, e o original não sobra para comparação — por isso fica registrado como R (dúvida honesta: parte do que sai é ruído de UI, parte pode ser texto da pessoa).

#### A1-005 — agente_nw/coleta/capturas/imagens.py:43 — `construir_prompt`
- Classe: R
- O que é cortado e quanto: a descrição da imagem é limitada a "2 a 5 frases"; o que não couber nessas frases (inclusive texto legível na imagem, que o prompt pede transcrito) não existe a jusante. A imagem nunca é gravada (`ImagemCapturada`, `imagens.py:15`), então a descrição é a única representação que sobra.
- Qual decisão do produto depende desse corte: a tarefa de visão `descrever_imagem`; a descrição vira fato `[de imagem]` do contato e entra no prompt de redação e nos termos de busca do contato.
- Trecho de código (1 a 3 linhas, copiado):
  ```python
  de forma objetiva e detalhada, em 2 a 5 frases: o que aparece (lugar, objetos, atividade, clima da cena),
  quantas pessoas há e o que fazem, e qualquer texto legível na imagem, transcrito.
  ```
- Justificativa existente no código/comentário (cite o lugar) ou "nenhuma": nenhuma para o teto de frases; a docstring de `ImagemCapturada` (`imagens.py:15`) justifica só o não gravar a imagem.
- Por que isto é analítico (T/C/R/P) ou só apresentação/log/identificador (NA): a análise seguinte (fato, redação) decide com a descrição como se tivesse visto a imagem. Dúvida registrada: o princípio auditado fala de texto, e aqui o material de origem é imagem; mas o texto legível dentro dela é conteúdo e pode não caber em 5 frases.

#### A1-006 — agente_nw/coleta/capturas/listas.py:242 — `parse_links`
- Classe: C
- O que é cortado e quanto: o mesmo perfil aparece várias vezes na página (foto, nome, botão); fica só o cartão de texto mais longo e os outros são descartados inteiros — informação que apareça apenas no cartão curto desaparece.
- Qual decisão do produto depende desse corte: a `EntradaLista` gravada no cache das listas, que é o que depois casa com o nome do contato (`queries_listas.buscar_por_nome` / `buscar_parecidos`), pontua candidatas (`localizacao._pontuar`) e vai ao prompt `desempatar_perfil`.
- Trecho de código (1 a 3 linhas, copiado):
  ```python
  elif len(texto) > len(melhores[chave][1]):
      melhores[chave] = (href, texto)
  ```
- Justificativa existente no código/comentário (cite o lugar) ou "nenhuma": a docstring de `parse_links` (`listas.py:230-231`): "O mesmo link costuma aparecer mais de uma vez (foto e nome); vale o cartão de texto mais longo."
- Por que isto é analítico (T/C/R/P) ou só apresentação/log/identificador (NA): o texto descartado é texto de conteúdo da página e alimentaria o casamento de nome e o desempate. É escolha por heurística de tamanho, não união dos cartões — logo, parte da coleção não é analisada (C).

#### A1-007 — agente_nw/coleta/capturas/listas.py:251-254 — `parse_links`
- Classe: C
- O que é cortado e quanto: das linhas úteis do cartão, ficam a 1ª como nome e no máximo 3 como cabeçalho (`linhas[1:4]`; no Instagram, `@usuário` mais `linhas[2:4]`). Da 5ª linha útil em diante nada entra na `EntradaLista`. Antes disso, `_linhas_uteis` (`listas.py:216-224`) já remove linhas de botão/rótulo pelo conjunto `_RUIDO` e pelos prefixos `_RUIDO_PREFIXOS`.
- Qual decisão do produto depende desse corte: o `cabecalho` gravado; ele é a única descrição da pessoa em `_pontuar` (`localizacao.py:92-98`), no prompt `desempatar_perfil` (`localizacao.py:104`), no filtro por texto da lista (`queries_listas.filtrar_por_texto`) e no fato `lista_rede_social` + `notas` do contato (`localizacao.confirmar`).
- Trecho de código (1 a 3 linhas, copiado):
  ```python
  nome, cabecalho = linhas[0], linhas[1:4]
  if rede == "instagram" and len(linhas) > 1:
      nome, cabecalho = linhas[1], [f"@{linhas[0].lstrip('@')}", *linhas[2:4]]
  ```
- Justificativa existente no código/comentário (cite o lugar) ou "nenhuma": a docstring de `parse_links` (`listas.py:231-232`): "A primeira linha útil é o nome; as seguintes (até 3) formam o cabeçalho"; e o comentário de `listas.py:253` sobre a ordem do Instagram.
- Por que isto é analítico (T/C/R/P) ou só apresentação/log/identificador (NA): o que fica fora do cabeçalho nunca é analisado, e a identificação da pessoa (decisão de produto) é tomada com essas 3 linhas. Coleção de linhas cortada em N (C).

#### A1-008 — agente_nw/coleta/capturas/listas.py:346-369 — `ler_lista`
- Classe: C
- O que é cortado e quanto: a lista de conexões/seguidos é lida só até `limiares.maximo_entradas` ou até `rodadas_sem_novidade` rolagens sem entrada nova, e o resultado ainda passa por `entradas[: limiares.maximo_entradas]`. Quem estiver depois do corte não existe para o programa. O sinalizador `truncada` compara `len(entradas) > maximo`, mas o laço sai quando `len >= maximo`: uma lista cortada exatamente no teto é devolvida com `truncada=False`.
- Qual decisão do produto depende desse corte: a localização da pessoa nas redes do usuário (`localizacao._candidatas_da_lista`); uma pessoa fora do pedaço lido cai no "não achei nas suas listas" e vai para a busca geral ou para o pedido de link.
- Trecho de código (1 a 3 linhas, copiado):
  ```python
  while len(acumuladas) < limiares.maximo_entradas and sem_novidade < limiares.rodadas_sem_novidade:
  truncada = len(entradas) > limiares.maximo_entradas
  return ResultadoLista(..., entradas=entradas[: limiares.maximo_entradas], truncada=truncada)
  ```
- Justificativa existente no código/comentário (cite o lugar) ou "nenhuma": a docstring de `ler_lista` (`listas.py:327-328`) declara o comportamento ("rola até o fim da lista, até `maximo_entradas` ou até três rodadas sem entrada nova"), sem justificar o valor.
- Por que isto é analítico (T/C/R/P) ou só apresentação/log/identificador (NA): é corte de coleção que decide se a pessoa é encontrada; e o único aviso ao usuário (`truncada`) pode ficar falso justamente no caso do corte no teto.

#### A1-009 — agente_nw/coleta/capturas/navegador.py:84-90 — `_extrair_blocos`
- Classe: C
- O que é cortado e quanto: cada bloco (parágrafo separado por linha em branco) com menos de 30 ou **mais de 5.000** caracteres é descartado inteiro — não truncado, descartado. Uma publicação longa (ou um bloco em que a página junte texto demais) simplesmente nunca é analisada.
- Qual decisão do produto depende desse corte: tudo o que vem da leitura de rede social: a extração `extrair_captura_rede_social`, os fatos gravados do contato, os termos de busca de notícia tirados do que a pessoa publica e o prompt de redação.
- Trecho de código (1 a 3 linhas, copiado):
  ```python
  if _BLOCO_TAMANHO_MINIMO <= len(parte.strip()) <= _BLOCO_TAMANHO_MAXIMO
  ```
- Justificativa existente no código/comentário (cite o lugar) ou "nenhuma": nenhuma; as constantes (`navegador.py:21-22`) estão sem comentário, ao contrário de `_MAX_ESPERAS_LOGIN` (`navegador.py:23`, "sem espera: o usuário já está logado…").
- Por que isto é analítico (T/C/R/P) ou só apresentação/log/identificador (NA): o descarte decide o que existe para analisar. Fica como C (item inteiro sai da coleção de blocos) e não T, porque não há truncamento: o texto grande é jogado fora por completo — que é o resultado mais severo dos dois.

#### A1-010 — agente_nw/coleta/capturas/navegador.py:142-147 — `ler`
- Classe: C
- O que é cortado e quanto: a página é lida no estado inicial e em no máximo `max_rolagens - 1` rolagens (padrão `_MAX_ROLAGENS = 5`). O que estiver abaixo disso no feed do perfil nunca é capturado.
- Qual decisão do produto depende desse corte: a mesma cadeia do A1-009 (fatos de rede social, termos de busca, redação).
- Trecho de código (1 a 3 linhas, copiado):
  ```python
  for _ in range(max(0, max_rolagens - 1)):
      dorme(rnd.uniform(intervalo_min_s, intervalo_max_s))
      pagina.rolar()
  ```
- Justificativa existente no código/comentário (cite o lugar) ou "nenhuma": a docstring de `ler` (`navegador.py:106-109`) descreve o limite ("rola no máximo `max_rolagens` vezes com intervalo aleatório"); o motivo (pausa entre páginas, não ser bloqueado) está no AGENTS.md §3, não aqui.
- Por que isto é analítico (T/C/R/P) ou só apresentação/log/identificador (NA): só parte da coleção de publicações da pessoa é analisada. Observação: o limite também serve de proteção contra bloqueio da rede — mesmo assim é corte, e o programa não registra em nenhum lugar que parou antes do fim do feed.

#### A1-011 — agente_nw/coleta/capturas/navegador.py:56-74 — `_capturar_imagens`
- Classe: C
- O que é cortado e quanto: as imagens publicadas são pedidas só até `maximo` no total da leitura (`faltam = maximo - len(acumuladas)`), e a página ainda filtra por `largura_minima`. Imagem além do teto não é descrita.
- Qual decisão do produto depende desse corte: a tarefa `descrever_imagem` e os fatos `[de imagem]` do contato; e, com `maximo_imagens=0` (o padrão do parâmetro em `ler`), nenhuma imagem é lida.
- Trecho de código (1 a 3 linhas, copiado):
  ```python
  faltam = maximo - len(acumuladas)
  if chave not in vistas and len(acumuladas) < maximo:
  ```
- Justificativa existente no código/comentário (cite o lugar) ou "nenhuma": a docstring de `_capturar_imagens` (`navegador.py:59`) declara o teto ("até `maximo` no total"), sem justificá-lo.
- Por que isto é analítico (T/C/R/P) ou só apresentação/log/identificador (NA): parte da coleção de imagens publicadas não é analisada; as descrições que faltam seriam fatos do contato. (`_chave_da_imagem`, `navegador.py:52-53`, é só identificador de deduplicação — `src` sem query string — e não conta como corte.)

#### A1-012 — agente_nw/coleta/rss/canonicalizar.py:54-59 — `hash_titulo`
- Classe: R
- O que é cortado e quanto: o texto da notícia não entra: a chave de deduplicação é o SHA-256 do **título** normalizado (sem acento, sem caixa, sem pontuação). O título inteiro entra (não é prefixo), mas o corpo não entra nunca.
- Qual decisão do produto depende desse corte: a deduplicação da coleta (`queries_itens.existe(conexao, "", hash_do_titulo)`, `leitor.py:322` e `:329`): item com título já visto é contado como duplicado e descartado antes de o corpo ser baixado (ver A1-014).
- Trecho de código (1 a 3 linhas, copiado):
  ```python
  def hash_titulo(titulo: str) -> str:
      normalizado = unicodedata.normalize("NFKD", titulo.casefold())
      return hashlib.sha256(compactado.encode("utf-8")).hexdigest()
  ```
- Justificativa existente no código/comentário (cite o lugar) ou "nenhuma": nenhuma neste arquivo; a justificativa está no uso, em `leitor.py:321` ("O mesmo título aparece em várias buscas: checa pelo título antes de qualquer pedido de rede").
- Por que isto é analítico (T/C/R/P) ou só apresentação/log/identificador (NA): a deduplicação está na lista de "analisar" das regras, e aqui ela decide com o título no lugar do texto. Não é NA: o hash não é um identificador de apresentação, é o critério de descarte de conteúdo. (`url_canonica`/`_remover_rastreio_e_ancora` são normalização de URL, não corte — explicitamente fora do escopo.)

#### A1-013 — agente_nw/coleta/rss/google_news.py:24 e 59-62, 72 — `gerar_consultas`, `selecionar_termos`
- Classe: C
- O que é cortado e quanto: quatro cortes de coleção no que vai ser buscado. Por tema: `[tema.nome, *tema.sinonimos][:4]` — do 4º sinônimo em diante nada é buscado. No pedido: `termos_contato[:3]`, `contexto.termos_busca[:6]`, `contexto.interessa[:5]` e, no fim, `escolhidos[:maximo]` (`maximo` = `coleta.max_consultas_por_pedido`, vindo de `consulta.py:172`).
- Qual decisão do produto depende desse corte: que notícia entra no banco. O que não foi buscado não é coletado, não é agrupado, não é qualificado e não pode virar gancho.
- Trecho de código (1 a 3 linhas, copiado):
  ```python
  termos = [tema.nome, *tema.sinonimos][:_MAXIMO_TERMOS_POR_TEMA]
  ("contato", termos_contato[:_MAXIMO_TERMOS_CONTATO]),
  return escolhidos[:maximo]
  ```
- Justificativa existente no código/comentário (cite o lugar) ou "nenhuma": a docstring de `selecionar_termos` (`google_news.py:54-56`) explica a prioridade entre as origens ("Prioridade: assunto, termos do contato…"), não os tetos; as constantes (`google_news.py:10-14`) estão sem comentário. O AGENTS.md §6 registra `coleta.max_consultas_por_pedido` como medida contra bloqueio.
- Por que isto é analítico (T/C/R/P) ou só apresentação/log/identificador (NA): o conjunto de termos é a coleção que define o universo analisado adiante; cortá-lo é corte de coleção com efeito direto no resultado do pedido. (`normalizar_termo`, `google_news.py:46-48`, é chave de identidade do termo — NA, não ponto.)

#### A1-014 — agente_nw/coleta/rss/leitor.py:320-331 — `_processar_fonte`
- Classe: R
- O que é cortado e quanto: a notícia é descartada como duplicada comparando só o hash do título (e depois a URL canônica). Como a checagem roda **antes** do pedido da página, o corpo nunca é lido: duas matérias diferentes com o mesmo título normalizado (atualização de uma nota, cobertura de outro veículo com texto próprio) viram uma só.
- Qual decisão do produto depende desse corte: o descarte do item (contado em `resumo.duplicados`); o texto nunca chega ao agrupamento, à qualificação nem aos embeddings.
- Trecho de código (1 a 3 linhas, copiado):
  ```python
  hash_do_titulo = hash_titulo(titulo)
  # O mesmo título aparece em várias buscas: checa pelo título antes de qualquer pedido de rede.
  if queries_itens.existe(conexao_bd, "", hash_do_titulo):
  ```
- Justificativa existente no código/comentário (cite o lugar) ou "nenhuma": o comentário de `leitor.py:321`, citado acima (economia de pedidos de rede). Pelas regras, comentário não absolve.
- Por que isto é analítico (T/C/R/P) ou só apresentação/log/identificador (NA): deduplicação é análise, e aqui ela é decidida por uma representação parcial do item (o título) em lugar do texto.

#### A1-015 — agente_nw/coleta/rss/leitor.py:333-358 — `_processar_fonte`
- Classe: R
- O que é cortado e quanto: quando a página da notícia não baixa ou o `trafilatura` não extrai nada, `corpo` fica `None` e o item é gravado assim mesmo (`texto=None`), com título e URL. Daí em diante a notícia é analisada só pelo título. (Quando a extração dá certo, o corpo entra inteiro — não há `[:N]` sobre ele em nenhum ponto do arquivo.)
- Qual decisão do produto depende desse corte: agrupamento, qualificação e cruzamento desse item; `e_ruido(titulo, corpo, …)` (`leitor.py:345`) é o único juiz do caso sem corpo, e ele está em `coleta/rss/ruido.py`, fora desta lista.
- Trecho de código (1 a 3 linhas, copiado):
  ```python
  corpo = trafilatura.extract(pagina.text)
  except Exception:
      corpo = None
  ```
- Justificativa existente no código/comentário (cite o lugar) ou "nenhuma": nenhuma; não há comentário sobre o caso `corpo is None`.
- Por que isto é analítico (T/C/R/P) ou só apresentação/log/identificador (NA): o item segue vivo no banco representado apenas pelo título, e as etapas seguintes decidem sobre ele como se fosse a notícia. Dúvida registrada: o descarte pode acabar acontecendo em `ruido.py` (arquivo não auditado aqui) — quem verificar aquele arquivo fecha o ponto.

#### A1-016 — agente_nw/coleta/rss/leitor.py:242-248, 274-284, 362-363 — `coletar`, `_processar_fonte`
- Classe: C
- O que é cortado e quanto: três paradas antecipadas sobre a coleção de notícias. (a) por feed: `break` ao atingir `maximo_itens_novos_por_feed` — as entradas restantes do feed não são olhadas; (b) por pedido: `break` quando `resumo.itens_novos >= candidatos_suficientes`, deixando os termos seguintes sem busca, e reaproveitamento de termo buscado há menos de `horas_reuso_termo` (`leitor.py:280`); (c) por tempo: `time.monotonic() > limite` (`tempo_maximo_segundos`) interrompe fontes e termos.
- Qual decisão do produto depende desse corte: o conjunto de itens que existe para agrupar/qualificar/cruzar — isto é, quais ganchos o usuário pode receber.
- Trecho de código (1 a 3 linhas, copiado):
  ```python
  if n_itens_novos_da_fonte >= limiares.maximo_itens_novos_por_feed:
      break
  if caminho_sentinela.exists() or resumo.itens_novos >= limiares.candidatos_suficientes:
  ```
- Justificativa existente no código/comentário (cite o lugar) ou "nenhuma": a docstring de `coletar` (`leitor.py:205-210`) descreve (b) e o cooldown ("param quando já há `candidatos_suficientes` notícias novas"); o `tempo_esgotado` é avisado ao usuário em `consulta.py:193-194`. Nada justifica (a).
- Por que isto é analítico (T/C/R/P) ou só apresentação/log/identificador (NA): corte de coleção puro. Observação: parte disso é a resiliência a bloqueio exigida pelo AGENTS.md §6 (cooldown, poucas buscas por pedido) — o cooldown e o `_respeitar_intervalo` em si não cortam conteúdo, mas `maximo_itens_novos_por_feed` e `candidatos_suficientes` cortam. A retomada por `ultimo_id_processado` (`leitor.py:232-240`) é idempotência, não corte: as fontes já processadas no mesmo dia é que são puladas.

#### A1-017 — agente_nw/coleta/whatsapp/importador.py:51-53 — `enfileirar_extracao`
- Classe: C
- O que é cortado e quanto: só os `limiares.meses_extraidos` meses mais recentes da conversa entram na fila de extração de fatos; os meses anteriores ficam gravados no banco e nunca são analisados. O corte é aplicado em `nucleo/database/queries/conversa.py:97` (`sorted(por_mes, reverse=True)[:meses_extraidos]`), que não está nesta lista. As mensagens em si são gravadas inteiras (`importar`, linhas 33-39) e os blocos de `maximo_caracteres_bloco` apenas particionam o mês, sem perda.
- Qual decisão do produto depende desse corte: a fila `fila_extracao` com origem `whatsapp:AAAA-MM`, isto é, quais fatos do contato nascem da conversa — e, por consequência, o prompt de redação.
- Trecho de código (1 a 3 linhas, copiado):
  ```python
  for mes, blocos in conversa_q.blocos_por_mes(
      conexao, perfil_id, limiares.maximo_caracteres_bloco, limiares.meses_extraidos
  ):
  ```
- Justificativa existente no código/comentário (cite o lugar) ou "nenhuma": a docstring de `enfileirar_extracao` (`importador.py:47-48`) descreve o enfileiramento por mês sem justificar o teto; a docstring de `blocos_por_mes` (`conversa.py:83`) repete o limite.
- Por que isto é analítico (T/C/R/P) ou só apresentação/log/identificador (NA): é corte de coleção ("meses de um conjunto", citado nas próprias regras) sobre texto de mensagem que alimenta extração por LLM.

#### A1-018 — agente_nw/coleta/whatsapp/leitor.py:97-112 — `_nome_do_txt`, `ler_zip`
- Classe: C
- O que é cortado e quanto: do zip exportado é lido **um** `.txt` — `_chat.txt` se existir, senão `nomes[0]`. Havendo mais de um arquivo de conversa no zip, os outros são ignorados por completo.
- Qual decisão do produto depende desse corte: todas as mensagens importadas e, com elas, os fatos extraídos do WhatsApp.
- Trecho de código (1 a 3 linhas, copiado):
  ```python
  do_iphone = [nome for nome in nomes if nome.rsplit("/", 1)[-1].lower() == "_chat.txt"]
  return do_iphone[0] if do_iphone else nomes[0]
  ```
- Justificativa existente no código/comentário (cite o lugar) ou "nenhuma": a docstring de `ler_zip` (`leitor.py:106-107`) diz que ignora "fotos, áudios e outros arquivos do zip" — nada sobre um segundo `.txt`.
- Por que isto é analítico (T/C/R/P) ou só apresentação/log/identificador (NA): parte da coleção de arquivos de conversa não é analisada. Dúvida registrada: a exportação normal do WhatsApp traz um `.txt` só, então na prática o corte pode nunca acontecer; mas nada no código garante isso nem avisa o usuário.

#### A1-019 — agente_nw/coleta/whatsapp/leitor.py:67-91 — `_e_conteudo_descartado`, `ler_conversa`
- Classe: C
- O que é cortado e quanto: a mensagem é descartada inteira quando **contém** (não "é igual a") qualquer uma das marcas de `_CONTEUDO_DESCARTADO` — "<mídia oculta>", "imagem ocultada", "áudio omitido", "figurinha omitida", "mensagem apagada", "esta mensagem foi apagada". Uma mensagem real que mencione uma dessas expressões (ou um texto longo com a legenda de mídia na primeira linha) sai junto. Também saem as linhas sem `": "` depois da data (`leitor.py:86-87`).
- Qual decisão do produto depende desse corte: as mensagens gravadas e enfileiradas para extração de fatos; o que sai aqui não existe em nenhuma etapa posterior.
- Trecho de código (1 a 3 linhas, copiado):
  ```python
  def _e_conteudo_descartado(texto: str) -> bool:
      minusculo = texto.strip().lower()
      return any(marca in minusculo for marca in _CONTEUDO_DESCARTADO)
  ```
- Justificativa existente no código/comentário (cite o lugar) ou "nenhuma": o comentário de `leitor.py:24` ("Mídia, figurinha e mensagem apagada: descartadas mesmo tendo autor identificado") e a docstring de `ler_conversa` (`leitor.py:73-75`).
- Por que isto é analítico (T/C/R/P) ou só apresentação/log/identificador (NA): o alvo do descarte (placeholder de mídia) não tem texto a analisar, o que é legítimo; o ponto existe porque o teste é por substring e derruba a mensagem toda, inclusive texto real que a acompanhe. A emenda de linhas de continuação (`leitor.py:81-83`) preserva mensagens de várias linhas — essa parte está correta.

#### A1-020 — agente_nw/nucleo/confirmacao.py:182 — `conduzir`
- Classe: C
- O que é cortado e quanto: no encaminhamento `ESCOLHER`, só as 5 primeiras opções (`_OPCOES_MOSTRADAS`) vão ao menu; as demais candidatas localizadas não aparecem (o usuário só as alcança pelo caminho "l", que relista a rede inteira, ou colando o link).
- Qual decisão do produto depende desse corte: a identificação da pessoa na rede social, que é gravada no contato (`localizacao.confirmar`) e passa a delimitar o que será lido dela.
- Trecho de código (1 a 3 linhas, copiado):
  ```python
  mostradas = localizacao.opcoes[:_OPCOES_MOSTRADAS]
  escolhida = _menu(conexao, mostradas, entrada, saida, permitir)
  ```
- Justificativa existente no código/comentário (cite o lugar) ou "nenhuma": nenhuma; a constante (`confirmacao.py:14`) está sem comentário.
- Por que isto é analítico (T/C/R/P) ou só apresentação/log/identificador (NA): o corte não é só de tela — ele restringe o conjunto de que a decisão pode sair naquele passo. A ordenação que define quem fica nos 5 vem de `_avaliar`/`_casamento_com_pistas`, que já trabalham com descrição parcial (A1-001, A1-007). Nota: a paginação de `_escolher_na_lista` (`confirmacao.py:57-62`, 20 por vez com "Enter = mais") não perde entrada nenhuma — ali é apresentação.

#### A1-021 — agente_nw/nucleo/consulta.py:133 — `preparar`
- Classe: P
- O que é cortado e quanto: `_texto_da_consulta` junta assunto, objetivo, todos os `interessa` e a frase livre inteira (`consulta.py:89-91`) e manda tudo para `embeddar`, sem medir nada. O `bge-m3` corta em silêncio acima de 8.192 tokens; nenhuma linha deste arquivo (nem o chamador) confere o tamanho.
- Qual decisão do produto depende desse corte: o `centroide_consulta` — "sinal principal" do motor, segundo a própria docstring (`consulta.py:122-124`): ele entra na qualificação (`vetores_extras`) e no cruzamento por contato, decidindo que assunto chega ao usuário.
- Trecho de código (1 a 3 linhas, copiado):
  ```python
  centroide_consulta = cliente_llm.embeddar([_texto_da_consulta(contexto)])[0]
  ```
- Justificativa existente no código/comentário (cite o lugar) ou "nenhuma": nenhuma; a docstring fala do papel do centróide, não do tamanho.
- Por que isto é analítico (T/C/R/P) ou só apresentação/log/identificador (NA): é P exatamente como as regras descrevem — texto vai inteiro ao embedding e ninguém confere se cabe. Em pedido curto não há perda; o risco mora no `contexto.livre`, que é a frase inteira do usuário (e, nas correções, a frase acumulada com "Correção: …", `fluxo.py:162`).

#### A1-022 — agente_nw/nucleo/consulta.py:147-149 — `preparar`
- Classe: C
- O que é cortado e quanto: a leitura de rede social recebe `maximo_blocos_por_rede`, `maximo_imagens_por_rede` e `largura_minima_imagem`. O corte é aplicado em `coleta/capturas/leitor.py:135-143` (`captura.blocos[: maximo_blocos * _BLOCOS_EXAMINADOS_POR_PUBLICACAO]` e parada ao atingir `maximo_blocos` gravados) — arquivo fora desta lista.
- Qual decisão do produto depende desse corte: quantas publicações da pessoa passam por `extrair_captura_rede_social` e viram fato; o que fica fora não existe para a redação nem para os termos de busca.
- Trecho de código (1 a 3 linhas, copiado):
  ```python
  maximo_blocos=limiares.coleta.maximo_blocos_por_rede,
  maximo_imagens=limiares.coleta.maximo_imagens_por_rede,
  ```
- Justificativa existente no código/comentário (cite o lugar) ou "nenhuma": nenhuma aqui; o comentário que justifica está no destino (`coleta/capturas/leitor.py:27`: "Os primeiros blocos de uma página costumam ser menu e cabeçalho…").
- Por que isto é analítico (T/C/R/P) ou só apresentação/log/identificador (NA): é o ponto de origem de um corte de coleção sobre as publicações capturadas; quem fecha o ponto é a auditoria de `coleta/capturas/leitor.py`.

#### A1-023 — agente_nw/nucleo/consulta.py:169-174 — `preparar`
- Classe: C
- O que é cortado e quanto: os termos de busca do pedido são cortados em `limiares.coleta.max_consultas_por_pedido` (ver A1-013, onde o corte é executado).
- Qual decisão do produto depende desse corte: quais buscas de notícia são feitas neste pedido — e portanto que notícia pode virar gancho.
- Trecho de código (1 a 3 linhas, copiado):
  ```python
  for _rotulo, termo in google_news.selecionar_termos(
      contexto, termos_contato, limiares.coleta.max_consultas_por_pedido
  )
  ```
- Justificativa existente no código/comentário (cite o lugar) ou "nenhuma": nenhuma no local; AGENTS.md §6 registra `coleta.max_consultas_por_pedido` como parte da resiliência a bloqueio.
- Por que isto é analítico (T/C/R/P) ou só apresentação/log/identificador (NA): define o universo coletado; corte de coleção.

#### A1-024 — agente_nw/nucleo/consulta.py:203-205 — `preparar`
- Classe: C
- O que é cortado e quanto: a qualificação só processa até `limiares.qualificacao.teto_por_dia` assuntos pendentes; os demais ficam sem qualificar neste pedido (e, se o teto for atingido todo dia, podem nunca ser analisados).
- Qual decisão do produto depende desse corte: a tarefa de LLM de qualificação e, em seguida, o cruzamento por contato — assunto não qualificado não entra no menu nem na redação.
- Trecho de código (1 a 3 linhas, copiado):
  ```python
  qualificador.qualificar_pendentes(
      cliente_llm, conexao, limiares.qualificacao.teto_por_dia, vetores_extras=[centroide_consulta]
  )
  ```
- Justificativa existente no código/comentário (cite o lugar) ou "nenhuma": nenhuma no local (o teto é de custo/tempo de LLM, mas isso não está escrito aqui).
- Por que isto é analítico (T/C/R/P) ou só apresentação/log/identificador (NA): parte da coleção de assuntos não é analisada. O corte é executado em `nucleo/relevancia/qualificador.py`, fora desta lista.

#### A1-025 — agente_nw/nucleo/consulta.py:246 — `preparar`
- Classe: C
- O que é cortado e quanto: o histórico do contato vai para o prompt só nas últimas `LIMITE_PADRAO` entradas — `historico_recente_para_prompt` chama `queries.listar_por_perfil(conexao, perfil_id, limite)` (`nucleo/historico.py:82-85`, fora desta lista). O histórico mais antigo não entra.
- Qual decisão do produto depende desse corte: o `historico_texto` que vai ao prompt de redação (e à tela).
- Trecho de código (1 a 3 linhas, copiado):
  ```python
  historico_texto = historico_mod.historico_recente_para_prompt(conexao, perfil_id)
  ```
- Justificativa existente no código/comentário (cite o lugar) ou "nenhuma": nenhuma no local.
- Por que isto é analítico (T/C/R/P) ou só apresentação/log/identificador (NA): histórico está na lista de textos do princípio e aqui ele chega cortado ao prompt de redação. Quem fecha o ponto é a auditoria de `nucleo/historico.py`.

#### A1-026 — agente_nw/nucleo/consulta.py:212-214 — `preparar`
- Classe: NA
- O que é cortado e quanto: `agora[:10]` — os 10 primeiros caracteres de um ISO 8601, isto é, a data do dia.
- Qual decisão do produto depende desse corte: serve de chave de dia em `assunto_contato_q.listar_do_dia`; não corta texto de conteúdo nenhum.
- Trecho de código (1 a 3 linhas, copiado):
  ```python
  data_hoje = agora[:10]
  registros = assunto_contato_q.listar_do_dia(conexao, perfil_id, data_hoje)
  ```
- Justificativa existente no código/comentário (cite o lugar) ou "nenhuma": nenhuma (não precisa).
- Por que isto é analítico (T/C/R/P) ou só apresentação/log/identificador (NA): é o caso de identificador citado nas regras (`data[:10]` de um ISO). O recorte do dia em `listar_do_dia` restringe a coleção de registros, mas isso é o escopo do pedido ("os assuntos de hoje para esta pessoa"), não substituição de texto; o título usado no menu (`consulta.py:221-237`) é rótulo de tela e de JSON do menu.

#### A1-027 — agente_nw/nucleo/fluxo.py:34 e 364 — `_escrever` / `FRACAO_DO_CONTEXTO_NO_PROMPT`
- Classe: T
- O que é cortado e quanto: o prompt da redação recebe um orçamento fixo de `num_ctx_redacao * 0,73` tokens **estimados**; o que não couber nesse orçamento é cortado no módulo de redação (`nucleo/redacao.py`, fora desta lista). O número é uma fração arbitrada, com estimativa de tokens, não contagem do modelo.
- Qual decisão do produto depende desse corte: o prompt da redação dos ganchos — fatos do contato, histórico, trechos de WhatsApp e notícias competem por esse orçamento.
- Trecho de código (1 a 3 linhas, copiado):
  ```python
  FRACAO_DO_CONTEXTO_NO_PROMPT = 0.73  # 8192 de contexto → ~6000 tokens estimados de prompt
  limite_tokens=int(deps.num_ctx_redacao * FRACAO_DO_CONTEXTO_NO_PROMPT),
  ```
- Justificativa existente no código/comentário (cite o lugar) ou "nenhuma": o comentário da própria linha 34 ("8192 de contexto → ~6000 tokens estimados de prompt").
- Por que isto é analítico (T/C/R/P) ou só apresentação/log/identificador (NA): é o único lugar da parte A1 em que alguém se preocupa com a janela — e a forma dessa preocupação é cortar o material da redação para caber. Vale as duas leituras: é a mitigação de P para a redação e, ao mesmo tempo, a origem de um truncamento de conteúdo cuja execução precisa ser auditada em `nucleo/redacao.py`. O resto de `fluxo.py` (fila, status, perguntas serializadas, `pergunta_de_contato`/`pergunta_de_divergencia`) só move identificadores e rótulos de tela.

#### A1-028 — agente_nw/nucleo/localizacao.py:101-114 — `_desempatar`
- Classe: R
- O que é cortado e quanto: o prompt de desempate recebe apenas `[o.cabecalho for o in empatadas]` — as até 3 linhas de cabeçalho de cada candidata (A1-007) ou a descrição recortada da busca geral (A1-001). O modelo não vê o cartão inteiro, nem o perfil, nem o nome exibido.
- Qual decisão do produto depende desse corte: a tarefa de LLM `desempatar_perfil`, que escolhe qual conta é a pessoa do pedido (com `confianca >= 0,7`); a escolha é gravada no contato e passa a definir o que será lido dela.
- Trecho de código (1 a 3 linhas, copiado):
  ```python
  prompt = desempatar_perfil.construir_prompt(nome, pistas, [o.cabecalho for o in empatadas])
  ```
- Justificativa existente no código/comentário (cite o lugar) ou "nenhuma": nenhuma; nem aqui nem na docstring de `_avaliar` (`localizacao.py:120`).
- Por que isto é analítico (T/C/R/P) ou só apresentação/log/identificador (NA): representação parcial levada a um prompt de decisão. `_pontuar` (`localizacao.py:92-98`) decide pelo mesmo `cabecalho`, e `_casamento_com_pistas` (`localizacao.py:204-213`) ordena pela `descricao` recortada — os três compartilham a mesma origem de corte.

#### A1-029 — agente_nw/nucleo/localizacao.py:257-264 — `_candidatas_da_lista`
- Classe: C
- O que é cortado e quanto: não havendo casamento exato, as candidatas por semelhança param em `limiares.maximo_parecidas` por nome (e em `similaridade_minima`); o corte é executado em `queries_listas.buscar_parecidos` (fora desta lista).
- Qual decisão do produto depende desse corte: quem entra em `_avaliar`/`_desempatar` e no menu de confirmação — ou seja, se a pessoa é encontrada na lista do usuário.
- Trecho de código (1 a 3 linhas, copiado):
  ```python
  achadas = queries_listas.buscar_parecidos(
      conexao, rede, nome, limiares.similaridade_minima, limiares.maximo_parecidas
  )
  ```
- Justificativa existente no código/comentário (cite o lugar) ou "nenhuma": a docstring de `_candidatas_da_lista` (`localizacao.py:249-250`) explica a ordem ("exato primeiro; só se nenhum casar, por semelhança"), não o teto.
- Por que isto é analítico (T/C/R/P) ou só apresentação/log/identificador (NA): corte de coleção sobre as candidatas que alimentam a decisão de identidade.

#### A1-030 — agente_nw/nucleo/localizacao.py:372-388 — `confirmar`
- Classe: C
- O que é cortado e quanto: para não repetir o fato `lista_rede_social`, a comparação percorre só os 200 fatos mais recentes do contato (`fatos.listar_recentes(conexao, perfil_id, 200)`). Com mais de 200 fatos, um cabeçalho já gravado antes disso é gravado de novo.
- Qual decisão do produto depende desse corte: a deduplicação de fato (que as regras contam como análise) e, por consequência, o que entra no prompt de redação (fato repetido pesa duas vezes).
- Trecho de código (1 a 3 linhas, copiado):
  ```python
  ja_tem = any(
      f.conteudo == opcao.cabecalho and f.tipo == TIPO_FATO_LISTA
      for f in fatos.listar_recentes(conexao, perfil_id, 200)
  )
  ```
- Justificativa existente no código/comentário (cite o lugar) ou "nenhuma": nenhuma; o 200 é literal, sem comentário.
- Por que isto é analítico (T/C/R/P) ou só apresentação/log/identificador (NA): é uma deduplicação decidida sobre parte da coleção de fatos. Efeito pequeno, mas é decisão, não tela.

#### A1-031 — agente_nw/nucleo/localizacao.py:191-198 — `_o_que_a_pagina_mostra`
- Classe: NA
- O que é cortado e quanto: os 160 primeiros caracteres do texto da página, com espaços colapsados.
- Qual decisão do produto depende desse corte: nenhuma; entra só no `motivo` que o usuário lê quando a lista vem vazia.
- Trecho de código (1 a 3 linhas, copiado):
  ```python
  resumo = " ".join(str(texto).split())[:160]
  return f' — a aba estava em {url}: "{resumo}"'
  ```
- Justificativa existente no código/comentário (cite o lugar) ou "nenhuma": a docstring da função (`localizacao.py:192`): "Endereço e começo do texto da página, para o usuário ver por que a lista veio vazia."
- Por que isto é analítico (T/C/R/P) ou só apresentação/log/identificador (NA): o valor só viaja dentro de `ResultadoAtualizacao.motivo` → `Localizacao.avisos` → tela/aviso do pedido; não é embeddado, hasheado nem enviado a prompt. (`canonicalizar_link` e `rede_do_link`, `localizacao.py:59-68`, são normalização de URL/identificador — não contam.)

#### A1-032 — agente_nw/nucleo/orquestracao.py:210-213 — `preparar_e_redigir`
- Classe: C
- O que é cortado e quanto: dois tetos do prompt da redação passam por aqui: `trocas_whatsapp_no_prompt` (só as N últimas trocas da conversa entram; o corte é o `LIMIT ?` de `queries/conversa.py:46`, `ultimas_trocas`) e `maximo_moldes` (só N moldes). Junto vai o `limite_tokens` de A1-027.
- Qual decisão do produto depende desse corte: o prompt de redação dos ganchos e da mensagem base — o que o modelo sabe da conversa com a pessoa.
- Trecho de código (1 a 3 linhas, copiado):
  ```python
  trocas_whatsapp_no_prompt=limiares.whatsapp.trocas_no_prompt,
  maximo_moldes=limiares.moldes.maximo,
  ```
- Justificativa existente no código/comentário (cite o lugar) ou "nenhuma": nenhuma; a docstring de `preparar_e_redigir` (`orquestracao.py:177-178`) só explica o retorno `None` e o `preparar` injetável.
- Por que isto é analítico (T/C/R/P) ou só apresentação/log/identificador (NA): corte de coleção sobre as mensagens da conversa (texto do princípio) a caminho de um prompt. O resto do arquivo é encaminhamento de desfecho (`encaminhar_localizacao`, `encaminhar_pedido`) e não toca texto.

#### A1-033 — agente_nw/nucleo/pedido.py:22 e 37-40 — `extrair`
- Classe: C
- O que é cortado e quanto: o prompt de `extrair_pedido` recebe só os 50 contatos mais recentes (`_MAXIMO_CONTATOS_NO_PROMPT`), com nome, empresa e cargo. Contato mais antigo que isso não é oferecido ao modelo como pessoa conhecida.
- Qual decisão do produto depende desse corte: a tarefa de LLM `extrair_pedido` — quem é a pessoa do pedido, e portanto o reconhecimento do contato (`resolver_contato`) e o risco de criar contato duplicado.
- Trecho de código (1 a 3 linhas, copiado):
  ```python
  for contato in perfis.listar_contatos_recentes(conexao, _MAXIMO_CONTATOS_NO_PROMPT)
  prompt = extrair_pedido.construir_prompt(frase, conhecidos)
  ```
- Justificativa existente no código/comentário (cite o lugar) ou "nenhuma": nenhuma; a constante (`pedido.py:22`) está sem comentário.
- Por que isto é analítico (T/C/R/P) ou só apresentação/log/identificador (NA): corte de coleção dentro de um prompt de decisão.

#### A1-034 — agente_nw/nucleo/pedido.py:41-44 — `extrair`
- Classe: P
- O que é cortado e quanto: nada é medido — a frase do pedido vai inteira (correção, inclusive, com o texto do pedido pai concatenado, `fluxo.py:162`) mais os 50 contatos, sem conferir o `num_ctx` da tarefa `extrair_pedido`.
- Qual decisão do produto depende desse corte: a extração do pedido (pessoa, objetivo, assunto, registro, termos de busca) — a base de todo o resto.
- Trecho de código (1 a 3 linhas, copiado):
  ```python
  return cliente_llm.gerar_json(
      "extrair_pedido", prompt, PedidoExtraido, versao_prompt=extrair_pedido.VERSAO
  )
  ```
- Justificativa existente no código/comentário (cite o lugar) ou "nenhuma": nenhuma.
- Por que isto é analítico (T/C/R/P) ou só apresentação/log/identificador (NA): caso P — prompt sem conferência de janela. Risco real porque a frase livre não tem limite de tamanho e a correção faz o texto crescer a cada rodada. (`garantir_usuario`, `pedido.py:122`, usa `login[:1].upper()` só para capitalizar o nome do usuário — identificador, não corte.)

#### A1-035 — agente_nw/nucleo/saidas/markdown.py:32-43 — `_bloco_item`
- Classe: NA
- O que é cortado e quanto: cada item do menu em Markdown aparece como `titulo_gerado` + "Por quê" + (quando é viável com esforço) `resumo_cartao`; o texto das notícias do assunto não entra.
- Qual decisão do produto depende desse corte: nenhuma análise — é o arquivo que o usuário lê e marca. A releitura (`ler_marcacoes`, linhas 89-112) extrai apenas `ac:<id>`, `[x] usei`/`[x] não serve` e o motivo entre parênteses; nada do texto exibido volta para decisão.
- Trecho de código (1 a 3 linhas, copiado):
  ```python
  linhas = [f"#### {titulo}  <!-- ac:{registro.id} -->", f"Por quê: {por_que}"]
  cartao = assunto.resumo_cartao if assunto is not None and assunto.resumo_cartao else "(não gerado)"
  ```
- Justificativa existente no código/comentário (cite o lugar) ou "nenhuma": nenhuma (é o formato do menu).
- Por que isto é analítico (T/C/R/P) ou só apresentação/log/identificador (NA): apresentação — o recorte existe para caber numa tela/arquivo que a pessoa lê, e a única coisa lida de volta são marcações e identificadores. O `zip(..., strict=False)` de `_motivos_marcados` (linha 84) ignora parênteses além dos 5 motivos conhecidos: ainda é leitura de marcação, não de texto.

## 3. Observações para o relatório do brief

- Ninguém, em toda a parte A1, mede o tamanho de um prompt ou de um texto de embedding contra a janela
  do modelo antes de chamar `gerar_json`/`embeddar`. A única noção de janela é o orçamento da redação
  (A1-027), que é uma fração fixa com tokens estimados. Os três pontos P (A1-003, A1-021, A1-034) são
  o mesmo defeito em três entradas diferentes.
- O corte mais severo encontrado é `navegador.py:89` (A1-009): bloco com mais de 5.000 caracteres é
  descartado, não truncado — a publicação longa desaparece sem registro.
- A família `cabecalho`/`descricao` (A1-001, A1-006, A1-007, A1-028) é um corte único com quatro
  consumidores: o que decide a identidade da pessoa nas redes é um recorte de 3 a 4 linhas do cartão.
- Três pontos têm o corte executado fora desta lista e precisam da outra parte da auditoria para
  fechar: `coleta/capturas/leitor.py` (A1-022), `nucleo/historico.py` (A1-025),
  `nucleo/relevancia/qualificador.py` (A1-024), `nucleo/redacao.py` (A1-027, A1-032) e
  `nucleo/database/queries/conversa.py` (A1-017, A1-032).
