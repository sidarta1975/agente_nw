# Relatório 094 — Segunda auditoria independente do texto por inteiro

**Brief:** `docs/briefs/brief_094_segunda_auditoria_independente_2026-11-08.md`
**Data:** 2026-11-16
**Depende de:** brief 093, conferido (`Último brief concluído: 093` no PLAN; commits `922ce24` e `58294ff`).

Resposta curta: o projeto lê o texto inteiro nas tarefas que dividem em partes (cartão, extração de texto, captura de rede social, embedding): o último caractere de um texto de 5.000.000 caracteres chegou a uma chamada nas quatro. Nas outras onze tarefas, um texto grande demais é recusado em voz alta (linha de janela no log e o prompt inteiro na `fila_revisao`), e nenhuma passou em silêncio. A auditoria cega achou **19 pontos novos (P-046 a P-064)**, que o 079 não tinha. Os mais graves são o WhatsApp de um mês já extraído, que nunca volta à extração (P-053), e o pedido de embedding sem `truncate: false` (P-046). Código de produção não mudou.

## 1. Como a independência foi mantida

- **Ordem.** A lista cega (seção 3) foi fechada antes de abrir o `doc_079`. Também ficou para depois o `docs/EXCECOES_TEXTO_INTEGRAL.md`, que repete os pontos do 079, embora o brief o liste em "Seções a ler". O relatório `relatorio_agente_nw_*` de `referencias/relatorios_projetos` não foi aberto.
- **Vazamento que houve.** O AGENTS §1 manda ler o PLAN até as Dívidas, e as Decisões em aberto citam alguns pontos do 079 pelo número (P-009, P-013, P-028 a P-030, P-034, P-039). Os auditores não leram essas seções (instrução explícita). Quem coordenou leu.
- **Certificados do 079, só a lista.** Para sortear a amostra, a tabela da seção 6 do 079 foi lida por `verificar_auditoria_texto.ler_certificacao` só para extrair os nomes com `CERTIFICADO`, sem imprimir evidência nem ponto: 280 arquivos hoje, os 256 do 079 mais os que os briefs 080–093 recertificaram.
- **Quem leu.** Cinco auditores, um por lote, cada um com a mesma regra: ler cada arquivo do início ao fim e informar linhas lidas/total. Nenhum deles viu o 079, o registro de exceções, a guarda `tests/test_sem_corte_de_texto.py` nem o verificador. A busca não se limitou a fatias: tetos, `LIMIT`, regex que apaga texto, limites escondidos de biblioteca (`csv`, Flask, Ollama `/api/embed`), paginação, janela, filtros e descartes. As lições vieram dos relatórios do `advogada_parceira_free` e do `lex_hub`.

## 2. Cobertura

### 2.a. Lidos inteiros (maior risco: montam prompt, chamam LLM ou embedding, leem a coleta)

121 arquivos de produção, todos com linhas lidas = linhas do arquivo:

| Lote | Arquivos | Linhas |
|---|---|---|
| A — núcleo do LLM | `nucleo/llm.py`, `texto_integral.py`, `estimativa_tokens.py`, `texto.py`, `vetores.py`, `config/container.py`, `config/*.yaml`, `nucleo/modelos/*` (24), `nucleo/prompts/*` (15) | ≈ 3.700 |
| B — redação e relevância | `redacao.py`, `pedido.py`, `fluxo.py`, `orquestracao.py`, `consulta.py`, `historico.py`, `termos_contato.py`, `localizacao.py`, `confirmacao.py`, `relevancia/*` (6), `saidas/markdown.py` | 3.900 |
| C — coleta, perfil, agrupamento | `coleta/**` (15), `perfil/*` (9), `nucleo/agrupamento/*` (5), `ponte/*` (2), `extensao/*` (4) | ≈ 4.700 |
| D — consultas, CLI, console | `nucleo/database/queries/*` (20), `database/{backup,conexao,migracoes}.py`, `cli.py` (1.673), `console/app.py` (1.088), `scripts/migracoes/*.sql` (22, 531 linhas) | ≈ 6.000 |

### 2.b. Amostra dos certificados do 079

- **Semente:** `random.seed(94)`.
- **Universo:** os 280 certificados menos os que já estavam no 2.a, o que deixa 200.
- **Sorteio:** `random.sample(resto, 30)` sobre a lista ordenada.

Os 30 sorteados, todos lidos inteiros: `agente_nw/nucleo/__init__.py`, `agente_nw/nucleo/saidas/__init__.py`, `scripts/executar_serie.sh`, `scripts/migracoes/005_perfil_id_reatribuivel.sql`, `tests/coleta_falsa.py`, `tests/test_assuntos_qualificacao.py`, `tests/test_candidatos_por_consulta.py`, `tests/test_cartoes_pendentes.py`, `tests/test_coleta_degradacao.py`, `tests/test_coleta_retomada.py`, `tests/test_coleta_reuso_termo.py`, `tests/test_comentario_sob_orcamento.py`, `tests/test_concorrencia.py`, `tests/test_console_novo_contato.py`, `tests/test_console_redes_sociais.py`, `tests/test_console_temas.py`, `tests/test_extensao_backend.py`, `tests/test_fluxo.py`, `tests/test_gancho_uso.py`, `tests/test_gancho_uso_base.py`, `tests/test_google_news_consulta.py`, `tests/test_imagens.py`, `tests/test_lacunas.py`, `tests/test_markdown_gerar.py`, `tests/test_mensagem_base_sem_noticia.py`, `tests/test_moldes_so_confirmado.py`, `tests/test_perfis_campos_guiados.py`, `tests/test_prompt_extrair_pedido.py`, `tests/test_redacao_fato_antigo_e_foto.py`, `tests/test_seguranca_prompt.py`.

**Resultado da amostra:** nenhum ponto novo. Quatro testes fixam cortes que já existem em produção e já têm destino:

- `test_comentario_sob_orcamento.py` fixa o sacrifício do histórico (P-033);
- `test_extensao_backend.py` fixa os 200.000 caracteres da página (P-013) e os tetos de rolagem e de imagens (P-015, P-017);
- `test_google_news_consulta.py` fixa o teto de termos (P-005);
- três testes de lote fixam o `teto_por_dia` e o `candidatos_por_contato` (P-009).

Nenhum cliente falso da amostra esconde corte de prompt. `seguranca._neutralizar` só troca `<`/`>` do marcador forjado por espaço e não apaga texto: conferido no código.

## 3. Lista cega (escrita antes de abrir o 079)

Só os achados analíticos estão aqui. Os cortes de exibição sem perda de alcance (datas `[:10]`, `fato[:40]` no aviso, `[:160]` em mensagem de erro, `opcoes[:5]` com a opção "l") ficaram fora. G = gravidade.

| # | arquivo:linha | O que fica de fora | Silencioso? | G |
|---|---|---|---|---|
| 1 | `nucleo/llm.py:648` | `/api/embed` sem `"truncate": false` e sem `options.num_ctx`: se o servidor usar janela menor que 8.192, ele trunca e a medida (`>= 8192`) não pega; em lote (`len(textos) > 1`, l. 654) a medida nem é conferida | sim, se a janela do servidor for menor (não conferido) | alta |
| 2 | `nucleo/llm.py:385`, `texto_integral.py:78` | nem a conferência nem o orçamento das partes reservam espaço para `num_predict`; uma parte pode encher a janela (4.093 de 4.096) e o Ollama pode deslocar o contexto ao gerar | não conferido | média |
| 3 | `coleta/capturas/extrator.py:104` | o orçamento da parte é medido sem o cerco e o aviso de parte: a primeira divisão é sempre recusada e refeita pela metade | não (recusa registrada) | baixa |
| 4 | `prompts/redigir_ganchos.py:305-328`, `redacao.py:323-331` | no corte por tamanho saem o histórico (fica 1), os moldes sem comentário e a conversa inteira do WhatsApp; só os fatos são avisados | sim (menos os fatos) | alta |
| 5 | `redacao.py:40-47, 70-72, 139, 153-196` | 10 de 40 fatos, 5 notas, 3 consultas, 3 manchetes por assunto (as mais antigas, `ORDER BY i.id`), 10 trocas de WhatsApp, 2 moldes | sim | média |
| 6 | `redacao.py:107-116` | `embeddar([consulta, *fatos])` direto, em lote; `FalhaJanelaEmbedding` de um fato longo é engolida pelo `except Exception` e a escolha volta aos 10 mais recentes | sim | média |
| 7 | `historico.py:56` | mensagem anterior com 100 caracteres no prompt | sim | média |
| 8 | `redacao.py:76-82`, `prompts/redigir_ganchos.py:180-194` | o corpo da notícia não entra na redação (título, por quê, cartão, manchetes) | sim (desenho) | média |
| 9 | `relevancia/cruzamento.py:155, 283, 365, 407, 481` | gate lê título e cartão; o "por quê" lê só o título; 10 candidatos, 5 no menu; 5 termos de `interessa` no apoio | sim | média |
| 10 | `cruzamento.py:159-162, 290-294`; `termos_contato.py:62-66`; `localizacao.py:106-111`; `capturas/imagens.py:60-63`; `capturas/leitor.py:189`; `perfil/inferencia.py:121-125`; `cli.py:585-588` | falha de janela, ou falha de JSON, registrada na `fila_revisao` mas engolida: gate pulado, por quê nulo, termos `[]`, desempate ambíguo, imagem sem fato, bloco contado como "descartado pelo modelo", tema sem vetor (`except: pass`), `sem_corpo` que o `qualificar` não imprime | o usuário não vê | média |
| 11 | `consulta.py:138`, `cruzamento.py:410`, `perfil/inferencia.py:95` | `embeddar` direto, sem partes: texto grande é recusado (o pedido falha) em vez de lido | não (recusa) | baixa |
| 12 | `relevancia/cartoes.py:97-99, 246-272` | `texto_e_o_proprio_resumo` conta palavras com `split()`: texto sem espaços vai cru; a recusa sai com o motivo "número sem fonte" | não (motivo errado) | baixa |
| 13 | `relevancia/candidatos.py:39-50` | o "evitar" procura em título, cartão, manchete e resumo, não no `item.texto`; item sem resumo entra só pela manchete | sim | média |
| 14 | `termos_contato.py:14-15, 56-59` | 12 de 30 fatos | sim | média |
| 15 | `modelos/pedido.py:88-107`, `prompts/extrair_pedido.py:61-63` | validador corta `interessa`/`sobre_o_usuario` em 5 e `termos_busca` em 6; pista fora de `CHAVES_DE_PISTA` sai; o prompt pede "até 5" | sim | média |
| 16 | `pedido.py:23, 37-60` | lista de contatos do prompt: os parecidos e até 50 recentes; palavra com menos de 3 letras não conta | sim | baixa |
| 17 | `localizacao.py:271, 390-395, 430` | 5 parecidas; dedup do fato de lista sobre 200; o aviso não sai no caminho do link do pedido | parcial | baixa |
| 18 | `queries/perfis.py:614, 631-633` | centróide com os 20 fatos mais recentes; havendo fatos, a ficha não entra | sim | alta |
| 19 | `queries/conversa.py:55-61`, `whatsapp/importador.py:49-55` | mês que já tem linha em `fila_extracao` é pulado inteiro: mensagens novas desse mês, de uma exportação posterior, nunca são extraídas | sim | alta |
| 20 | `queries/conversa.py:95-98` | só os 24 meses mais recentes vão à extração | sim | média |
| 21 | `queries/conversa.py:85-89` | a extração recebe só as mensagens do contato; as do usuário (o contexto do "sim, isso mesmo") ficam fora | sim | média (DÚVIDA) |
| 22 | `whatsapp/leitor.py:67-69, 81-117` | "mensagem apagada" casada por substring descarta mensagem real, e as linhas seguintes grudam na anterior; aviso de sistema sem ": " idem; linhas antes do 1º cabeçalho; do zip, `_chat.txt` ou `nomes[0]` | sim | média |
| 23 | `queries/assuntos.py:146-179`, `cli.py:582` | qualificação dos 40 mais parecidos (`teto_por_dia`); os demais ficam com `substancial` nulo | sim | média |
| 24 | `rss/leitor.py:328-332`, `canonicalizar.py:54`, `queries/itens.py:41` | dedup só pelo título normalizado, sem janela de tempo | só contador | média |
| 25 | `rss/ruido.py:45-56, 69-72, 85` | notícia inteira descartada se o título ou **qualquer linha curta** do corpo contém "publicidade"/"patrocinado por" (pega o rótulo de anúncio do layout); também teaser abaixo de 400, título de lista e primeira coleta mais de 7 dias depois | só contador, sem motivo por item | alta |
| 26 | `rss/leitor.py:341-366, 346` | o resumo da entrada do feed nunca é gravado; `trafilatura.extract` com os padrões (remoção de boilerplate não conferida) | não / não conferido | baixa |
| 27 | `rss/google_news.py:24, 59-72` | tetos de termos por origem e no total | sim | baixa |
| 28 | `extensao/conteudo.js:203`, `extensao_backend.py:142` | página em 200.000 caracteres | avisa | média |
| 29 | `capturas/leitor.py:136-169` | 40 blocos examinados, para no 10º gravado | parcial | média |
| 30 | `capturas/leitor.py:57-59` | dedup de imagem por `(perfil, tipo, link da publicação)`: a 2ª imagem em diante de um carrossel é pulada | sim | média |
| 31 | `capturas/navegador.py:21, 124-125` | bloco com menos de 30 caracteres descartado ("Parabéns, Ana!") | sim | média |
| 32 | `navegador.py:61-79`, `conteudo.js:181-195`, `background.js:126-136` | 8 imagens; imagem não carregada, host fora da lista, acima de 6 MB, sem reposição | sim | média |
| 33 | `capturas/busca.py:104-111` | a chave do link entra em `vistos` antes de conferir o texto: se a 1ª ocorrência é a foto sem texto, a que tem nome e cabeçalho é pulada | sim (não conferido no DOM) | média |
| 34 | `capturas/listas.py:139-147, 221`, `conteudo.js:59` | cabeçalho sem as linhas "conectado/mutual/em comum"; `truncada` falso quando a lista para no teto exato; o 1º texto do href nunca é trocado | sim | baixa |
| 35 | `extensao/conteudo.js:162-167, 200` | "…mais" só é clicado em `<button>` com o rótulo configurado; o texto escondido de LinkedIn/Facebook não é lido | sim (não conferido) | DÚVIDA |
| 36 | `agrupamento/calibracao.py:25, 107-108` | item em 2.000 caracteres no `prerotular_calibracao` | sim | alta |
| 37 | `perfil/agenda_google_csv.py:49-53`, `perfil/importador.py:74-76` | só "Phone 1", "E-mail 1", "Organization 1"; contato sem telefone nem e-mail é ignorado e suas notas nunca vão à extração | contador | baixa |
| 38 | `console/app.py:208, 444, 726` | lote de 20 da `fila_extracao`; a página da pessoa diz "processando conversa…" sem nada processando | sim | média |
| 39 | `console/app.py` (formulários) | Flask 3.1 com `MAX_FORM_MEMORY_SIZE = 500_000`: texto colado acima de ~500 KB recebe 413 genérico | não (recusa) | baixa |
| 40 | `queries/perfis.py:267-299` | ao unir contatos, campo já preenchido no canônico (inclusive `notas`) descarta o do duplicado | sim | baixa |
| 41 | `console/app.py:411`, `templates/pessoa.html:31`, `app.py:239` | inalcançável: só 15 fatos × 300 caracteres na página da pessoa, nenhuma outra tela; notas de escopo "contato" e mensagens do WhatsApp sem tela | — (exibição) | baixa |
| 42 | `console/app.py:66, 467-470` | WhatsApp acima de 20 MB recusado | avisa | baixa |
| 43 | `console/app.py:1050` | formulário lê 20 temas | sim | baixa |
| 44 | `modelos/redacao.py:141-145` | 4 ganchos | avisa (NA: saída do modelo) | — |

Sem achado: `fluxo.py`, `orquestracao.py`, `pontuacao.py`, `saidas/markdown.py`, `ponte/servidor.py` (lê todo o `Content-Length`), `agrupador.py` (título e texto inteiros por `embeddar_em_partes`), `perfil/extrator.py`, `capturas/extrator.py` (só o #3), `comparar_vetores.py`, `texto_integral.py` (cobertura de 100% conferida: última parte `(inicio, len(texto))`, `reconstruir` igual ao texto ou `ValueError`; texto vazio, texto no orçamento exato e palavra única sem espaço também dão reconstrução exata), `agenda_google_csv.py` (`field_size_limit` elevado a `sys.maxsize`), migrações (nenhum `CHECK(length)` que limite texto).

## 4. Comparação com o 079 (depois da lista)

### 4.a. Tabela de divergências

| Achado desta auditoria | Estava no 079? | Estado |
|---|---|---|
| 1 embedding sem `truncate:false`/`num_ctx`, lote sem medida | não: o P-041 trata da medida, e a 082-4 da dívida do cache | **P-046 (novo)** |
| 2 `num_predict` fora do orçamento / deslocamento de contexto | não | **P-047 (novo)** |
| 3 orçamento da parte da captura | não | **P-048 (novo)** |
| 4 corte por tamanho da redação (WhatsApp, histórico, moldes) | sim, P-033 | EXCEÇÃO APROVADA (só o mecanismo). Divergência: a saída do WhatsApp e do histórico continua sem aviso, e só os fatos avisam (brief 091); vai para a lacuna 3 |
| 5 tetos da redação (fatos, notas, consultas, manchetes, trocas, moldes) | sim, P-026, P-029, P-030, P-031, P-023, P-028 | P-023 aprovado; P-031 aguardando; os tetos de quantidade dos P-026/029/030 em decisão ([091], [093-3], [093-4]). Novo detalhe: as 3 manchetes são as **mais antigas** (`ORDER BY i.id`), entra no P-031 |
| 6 `embeddar` direto nos fatos, falha engolida | não: o P-026 tratava o `[:600]`, e o 091 o tirou e abriu este caminho | **P-049 (novo)** |
| 7 mensagem anterior em 100 | sim, P-028 | decisão [093-3] |
| 8 corpo fora da redação | sim, P-031 | AGUARDANDO DECISÃO DE SIDARTA |
| 9 gate, por quê, 10/5, apoio | sim, P-010, P-011, P-009, P-039 | P-010 corrigido (090); P-011 e P-009 aprovados (P-009 só o menu, [093-2]); P-039 aguardando |
| 10 falhas de janela engolidas, o usuário não vê | não | **P-050 (novo)** |
| 11 `embeddar` direto sem partes (consulta, apoio, tema) | parcial: o P-041 cobria a medida da consulta, não a recusa em vez da divisão | **P-051 (novo)** |
| 12 `texto_e_o_proprio_resumo` por `split()` | não | **P-052 (novo)** |
| 13 "evitar" fora do `item.texto` | sim, P-012 | CORRIGIDO (091); resto na dívida [091-3] |
| 14 termos do contato 12 de 30 | sim, P-027 | CORRIGIDO (091) no corte por caractere; teto em decisão |
| 15 validadores do pedido | sim, P-034 | CORRIGIDO (081) para `evitar`; 5 e 6 em decisão ([091-1], [093-5]) |
| 16 50 contatos no prompt do pedido | sim, P-035 | AGUARDANDO DECISÃO DE SIDARTA (092 mudou a escolha) |
| 17 localização 5/200 | sim, P-021 | EXCEÇÃO APROVADA. Novo: o aviso não sai no caminho do link do pedido, entra no P-050 |
| 18 centróide com 20 fatos | sim, P-025 | CORRIGIDO (089) por caractere; teto em decisão ([089-1]) |
| 19 mês do WhatsApp já extraído é pulado | não | **P-053 (novo)** |
| 20 24 meses | sim, P-022 | EXCEÇÃO APROVADA |
| 21 só mensagens do contato na extração | não | **P-054 (novo)** |
| 22 parser do WhatsApp (substring, linhas que grudam) | parcial: o P-024 aprova descartar mídia e apagadas e ler um `.txt` | **P-055 (novo)**: o falso positivo e a troca de autor |
| 23 `teto_por_dia` 40 | sim, P-009 | decisão [093-2] |
| 24 dedup por título | sim, P-002 | EXCEÇÃO APROVADA |
| 25 filtro de ruído/patrocínio descarta notícia inteira | parcial: o P-004 (3 linhas) foi corrigido pelo 083, que estendeu a busca a toda linha curta; o P-003 (teaser de 400) aguarda | **P-056 (novo)**: o falso positivo que a correção do 083 ampliou, mais título de lista e 7 dias |
| 26 resumo do feed não gravado, `trafilatura` | parcial: o P-003 trata do corpo que falha, não do resumo do feed | **P-060 (novo)** |
| 27 termos de busca | sim, P-005 | EXCEÇÃO APROVADA |
| 28 página em 200.000 | sim, P-013 | CORRIGIDO (083) no aviso; valor em decisão [093-1] |
| 29 10 blocos por rede | sim, P-016 | EXCEÇÃO APROVADA |
| 30 2ª imagem do carrossel pulada | não | **P-057 (novo)** |
| 31 bloco abaixo de 30 caracteres | sim, P-014 (faixa 30–5.000) | CORRIGIDO (083) no teto de 5.000; o mínimo de 30 está na tabela NA do 093. Contestado aqui: "Parabéns, Ana!" é texto do contato, vai para a lacuna 7 |
| 32 imagens: 8 e filtros | sim, P-017 | EXCEÇÃO APROVADA |
| 33 `busca.py` com `vistos` antes do texto | não: o P-020 trata das 3–4 linhas, não da ocorrência pulada | **P-058 (novo)** |
| 34 cabeçalho da lista, `truncada` no teto exato | parcial, P-020 | EXCEÇÃO APROVADA no cabeçalho. Novo: `truncada` falso no teto exato, entra no P-064 |
| 35 "…mais" não expandido | não | **P-059 (novo)** |
| 36 calibração em 2.000 | sim, P-008 | EXCEÇÃO APROVADA |
| 37 agenda: primeiro telefone e e-mail | sim, P-044 | EXCEÇÃO APROVADA. Novo: contato sem telefone nem e-mail perde as notas, entra no P-064 |
| 38 lote de 20 e "processando…" | sim, P-043 | EXCEÇÃO APROVADA no `LIMIT`. Novo: a tela promete um processamento que não acontece, entra no P-050 |
| 39 Flask 500 KB | não | **P-061 (novo)** |
| 40 unir contatos perde notas | não | **P-062 (novo)** |
| 41 texto guardado sem tela | não | **P-063 (novo)** |
| 42 WhatsApp acima de 20 MB | sim, P-024 | EXCEÇÃO APROVADA |
| 43 20 temas no formulário | sim, P-038 | EXCEÇÃO APROVADA |
| 44 4 ganchos | sim, P-032 | AGUARDANDO DECISÃO DE SIDARTA (correção feita, [092-3]) |
| contato sem telefone nem e-mail; `truncada` no teto | não | **P-064 (novo)** |

Na outra direção, pontos do 079 que esta auditoria **não** achou de forma independente:

- P-015 (rolagens e orçamento de 12 s);
- P-018 ("2 a 5 frases" por imagem);
- P-036 (frases de autodeclaração por regex);
- P-045 (primeiro nome na busca da lista).

Lidos agora, os quatro continuam valendo como o 079 descreve. Não foram vistos porque são tetos de leitura no JS da extensão (P-015), limite pedido ao modelo e não corte do texto de entrada (P-018), e regras de casamento, não de tamanho (P-036, P-045). É a mesma lição do P-18 do `advogada_parceira_free`: procurar também apagamento e casamento por padrão, não só tamanho.

### 4.b. Pontos novos

| Ponto | Onde | O que | Gravidade | Brief proposto |
|---|---|---|---|---|
| P-046 | `nucleo/llm.py:648, 654` | `/api/embed` sem `"truncate": false` nem `options.num_ctx`. O `bge-m3` declara `bert.context_length` 8192 e não tem `num_ctx` no Modelfile (lido pelo `/api/show` do Ollama 0.34.2 da 11435), então a janela efetiva é a padrão do servidor, que pode ser menor. Com o `truncate` padrão (verdadeiro), o servidor corta e devolve `prompt_eval_count` menor que 8192, que passa pela conferência. Em lote, a medida não é conferida | alta, se a janela do servidor for menor (medição real não concluída, seção 6) | "embedding com `truncate: false` e `num_ctx` explícito", com teste `llm_real` que mede uma parte de 24.000 caracteres |
| P-047 | `nucleo/llm.py:385`, `texto_integral.py:78` | o orçamento das partes e a conferência prévia não descontam `num_predict`, e o pedido ao Ollama não desliga o deslocamento de contexto: parte que enche a janela pode ter o começo descartado durante a geração | média, não conferido | "reservar `num_predict` na janela" |
| P-048 | `coleta/capturas/extrator.py:104` | orçamento medido sobre `construir_prompt("")`, sem cerco nem aviso de parte (prompt da parte estima 4.216 numa janela de 4.096): toda primeira divisão é recusada, refeita pela metade e deixa uma linha descartada na `fila_revisao` | baixa (não corta) | "orçamento medido com `construir_prompt_de_parte`" |
| P-049 | `nucleo/redacao.py:107-116` | `embeddar([consulta, *fatos])` direto; fato longo levanta `FalhaJanelaEmbedding`, engolida, e os fatos do prompt voltam a ser os 10 mais recentes, sem aviso | média | "escolha de fatos com `embeddar_em_partes` e aviso" |
| P-050 | `cruzamento.py:159-162, 290-294`; `termos_contato.py:62-66`; `localizacao.py:106-111, 430`; `capturas/imagens.py:60-63`; `capturas/leitor.py:189`; `perfil/inferencia.py:121-125`; `cli.py:585-588`; `console/app.py:208, 444, 726` | falha de janela ou de JSON registrada, mas o usuário vê um resultado normal: gate pulado, por quê nulo, termos vazios, desempate ambíguo, imagem sem fato, bloco "descartado pelo modelo", tema sem vetor, `sem_corpo` não impresso, "processando" sem processar | média | "toda falha registrada chega ao aviso do pedido" |
| P-051 | `consulta.py:138`, `cruzamento.py:410`, `perfil/inferencia.py:95` | `embeddar` direto: frase, interesse ou termo acima da janela derruba o pedido em vez de ser lido em partes | baixa (recusa em voz alta) | junto com o P-049 |
| P-052 | `relevancia/cartoes.py:97-99, 246-272` | texto sem espaços com até 150 "palavras" vai cru como resumo; a recusa sai com motivo enganoso | baixa | pequeno, junto com o P-048 |
| P-053 | `queries/conversa.py:55-61`, `coleta/whatsapp/importador.py:49-55` | mês que já tem linha na `fila_extracao` é pulado inteiro: as mensagens novas do mês da primeira exportação, vindas na segunda, nunca são extraídas | **alta** | "extração do WhatsApp por mensagem nova, não por mês" |
| P-054 | `queries/conversa.py:85-89` | extração de fatos só com as mensagens do contato; as do usuário, que dão o contexto das respostas, ficam fora | média (DÚVIDA de produto) | decisão de Sidarta antes de brief |
| P-055 | `coleta/whatsapp/leitor.py:67-69, 81-117` | marca de mídia/apagada por substring descarta mensagem real; linhas de continuação de mensagem descartada e aviso de sistema sem ": " grudam na anterior, com autor e hora errados | média | "parser do WhatsApp por linha inteira" |
| P-056 | `coleta/rss/ruido.py:45-56, 72, 85` | notícia inteira descartada por "publicidade" em qualquer linha curta (rótulo de anúncio entre parágrafos), por título de lista e por primeira coleta mais de 7 dias depois; o resumo da coleta não diz qual nem por quê | média-alta | "descarte por ruído com motivo e título, e marca de patrocínio só no cabeçalho declarado" (precisa de decisão sobre o critério) |
| P-057 | `coleta/capturas/leitor.py:57-59` | 2ª imagem em diante de um carrossel nunca é descrita (dedup pelo link da publicação) | média | "dedup de imagem pelo `src`" |
| P-058 | `coleta/capturas/busca.py:104-111` | a ocorrência do candidato com nome e cabeçalho é pulada quando a primeira do mesmo link é a foto | média (não conferido em site real) | "dedup da busca depois de conferir o texto" |
| P-059 | `extensao/conteudo.js:162-167, 200` | "…mais" só em `<button>` com rótulo configurado: o texto escondido de posts longos no LinkedIn/Facebook não é lido | DÚVIDA (exige teste com rede real) | teste de Sidarta, depois brief |
| P-060 | `coleta/rss/leitor.py:341-366, 346` | o resumo da entrada do feed é descartado; item cuja página falha fica só com a manchete, embora o feed trouxesse um resumo; `trafilatura` com padrões não conferidos | baixa | "guardar o resumo do feed" |
| P-061 | `console/app.py` (formulários) | `MAX_FORM_MEMORY_SIZE` do Flask (500.000): texto colado maior recebe 413 genérico | baixa (recusa) | "limite declarado e mensagem em português" |
| P-062 | `nucleo/database/queries/perfis.py:267-299` | `unir_contatos` descarta as `notas` (e outros campos) do duplicado quando o canônico já tem valor | baixa | "unir concatena notas" |
| P-063 | `console/app.py:239, 411`, `templates/pessoa.html:31` | texto guardado sem tela: fatos além de 15 ou de 300 caracteres, notas de escopo "contato" e mensagens do WhatsApp | baixa (exibição; lição P-17 do `advogada_parceira_free`) | "ver fatos, notas e conversa inteiros" |
| P-064 | `perfil/importador.py:74-76`, `coleta/capturas/listas.py:221` | contato da agenda sem telefone nem e-mail é ignorado e suas notas nunca vão à extração; `truncada` falso quando a lista para no teto exato | baixa | pequeno, sem brief próprio |

Nenhum ponto novo foi escrito no 079: a autorização do brief cobre só a seção 6 e o apêndice A, "sem criar ponto novo". Os P-046 a P-064 vivem neste relatório, e o estado de cada um é de Sidarta.

### 4.c. Código de produção

Não mudou. O único candidato a "defeito pequeno e claro" era o P-046 (`"truncate": false`, uma linha). Ele muda o comportamento contra o Ollama real: parte que hoje é cortada passaria a dar HTTP 400. Sem medir a janela efetiva do servidor, isso pode derrubar o agrupamento inteiro. Por isso ficou como lacuna.

## 5. Prova com textos extremos (item 2.3)

`tests/test_texto_extremo_ponta_a_ponta.py`:

- **Texto.** Sintético, com palavras e espaços, em dois tamanhos: 34.195 caracteres (o "item de 34.195" do brief) e 5.000.000. O marcador `MARCADOR-UNICO-094-FIM` termina no último caractere e aparece uma vez só.
- **Cliente.** O `ClienteOllama` de verdade, com a conferência de janela do produto. Só o servidor é falso: `_chamar` guarda o prompt e responde um JSON válido, e o `/api/embed` é um `MockTransport` que guarda cada texto.
- **Critério.** Para cada uma das 15 tarefas (as 14 de geração do roteamento e o embedding; o teste confere que o conjunto é o do `llm_routing.yaml`), o marcador chega a uma chamada, ou há linha `"janela": true` no log **e** o prompt inteiro, com o marcador, na `fila_revisao`. Nas quatro tarefas que dividem em partes, chegar é obrigatório.

Nenhuma tarefa ficou fora: todas recebem texto de terceiros ou do pedido.

| Tarefa | Entrada usada | 34.195 | 5.000.000 |
|---|---|---|---|
| cartao | `cartoes.resumir_item` (pública) | chegou, 4 chamadas | chegou, 466 chamadas |
| extrair_de_texto | `perfil.extrator.processar_item` (pública) | chegou, 4 | chegou, 544 |
| extrair_captura_rede_social | `capturas.extrator.extrair` (pública) | chegou, 7 | chegou, 997 (P-048: uma rodada recusada e refeita) |
| embeddings | `embeddar_em_partes` (pública) | chegou, 2 partes | chegou, 208 partes |
| extrair_pedido | `pedido.extrair` (pública) | recusou em voz alta | recusou em voz alta |
| descrever_imagem | `imagens.descrever` (pública; devolve `None`, ver P-050) | recusou | recusou |
| qualificar, rotular, cruzar_por_que, avaliar_relacao_objetivo, desempatar_perfil, redigir_ganchos, extrair_termos_contato, descrever_tema, prerotular_calibracao | montador do prompt + `gerar_json` | recusou | recusou |

O que o teste **não** prova: os cortes de seleção que acontecem antes do montador (quantos fatos, manchetes, meses ou blocos; os 2.000 da calibração; o sacrifício de blocos da redação). Eles estão nas seções 3 e 4. O P-008 e o P-033 são exceções aprovadas, então o teste não os trata como defeito. Também não prova o comportamento do Ollama real (P-046, P-047).

## 6. Algum texto é analisado só em parte? (AGENTS §4)

Sim, e o código deste brief não mudou nada disso.

- **Cortes conhecidos.** Os aprovados estão no registro. Os que ainda esperam decisão estão no 079 e nas lacunas dos briefs 089–093.
- **Cortes novos.** P-053 (mensagens novas de um mês do WhatsApp nunca extraídas), P-054, P-055, P-056, P-057, P-058, P-059, P-060, P-062 e P-064, sem aprovação nenhuma.
- **Possivelmente silencioso no Ollama real.** P-046 e P-047, ainda não medidos.

A prova de que as tarefas não cortam em silêncio **depois** do montador é o teste da seção 5.

Tentativa de medir o P-046 no Ollama real (porta 11435, a do projeto):

```
$ porteiro cabe bge-m3 --porta 11435; echo "codigo=$?"
Cabe: bge-m3:latest precisa de cerca de 6,1 GB.
Ficaria com 12,2 GB de 26,0 GB e 2 de 2 modelos.
A conta é estimativa: bge-m3:latest não está carregado agora, então o tamanho vem do arquivo no disco mais 5,0 GB de folga de contexto.
codigo=0

$ curl -s http://127.0.0.1:11435/api/show -d '{"model":"bge-m3"}'   (resumido)
parameters: None
{'bert.block_count': 24, 'bert.context_length': 8192}
{"version":"0.34.2"}

$ python3 (POST /api/embed com texto sintético de 54.389 caracteres, timeout de 300 s)
TimeoutError: timed out
```

O pedido de embedding não respondeu em 300 s, e não foi repetido, para não insistir no servidor compartilhado. Fica para Sidarta (lacuna 1).

## 7. Saída dos comandos

```
$ .venv/bin/pytest tests/test_texto_extremo_ponta_a_ponta.py -q
...............................                                          [100%]
31 passed in 2.39s

$ .venv/bin/ruff check tests/test_texto_extremo_ponta_a_ponta.py && .venv/bin/mypy tests/test_texto_extremo_ponta_a_ponta.py
All checks passed!
Success: no issues found in 1 source file

$ .venv/bin/python scripts/verificar_auditoria_texto.py
337 arquivos, 281 certificados, 49 cortam, 7 não analíticos, 0 não conferidos, 6 ponto(s) aguardando decisão de Sidarta
2005 ocorrência(s) da varredura mecânica, todas com destino no relatório
8 inconsistência(s):
  - tests/test_evitar_e_fatos_inteiros.py: a tabela diz 198/198 linhas, mas o arquivo tem 200
  - ocorrência sem destino no relatório: tests/test_evitar_e_fatos_inteiros.py:104 [truncar] (e mais 6 do mesmo arquivo: 112, 132, 133, 148, 149, 198)
```

As 8 inconsistências que sobram são do `tests/test_evitar_e_fatos_inteiros.py` (brief 091), registradas como dívida [092-4] e fora da autorização deste brief. As do arquivo novo deste brief (linha ausente na seção 6 e 5 ocorrências sem destino) foram resolvidas com a linha na seção 6 e o grupo "Brief 094 (sem ponto novo)" no apêndice A.

Gate completo (`scripts/verificar.sh`, rodado antes da entrega; o `agente_entregar.sh` roda de novo e decide):

```
$ scripts/verificar.sh; echo "saida=$?"
ruff check: ok
ruff format: ok
mypy: ok
pytest: ok (1334 passed, 5 deselected in 58.69s)
saida=0
```

## RELATÓRIO FINAL

- Brief executado: 094, segunda auditoria independente do texto por inteiro.
- Arquivos criados: `tests/test_texto_extremo_ponta_a_ponta.py` (31 testes); este relatório.
- Arquivos alterados (com resumo da mudança em uma linha cada):
  - `docs/docs/doc_079_auditoria_texto_por_inteiro_2026-11-08.md`: linha do teste novo na seção 6 e grupo "Brief 094 (sem ponto novo)" no apêndice A, como o brief autoriza.
  - `docs/PLAN_agente_nw.md`: Resumo, Doing e Done.
- Arquivos preservados literalmente na área afetada: todo `agente_nw/`, `config/`, `extensao/`, `docs/EXCECOES_TEXTO_INTEGRAL.md`, `tests/test_sem_corte_de_texto.py`, `scripts/verificar_auditoria_texto.py`.
- Script de verificação (o gate, rodado pelo `scripts/agente_entregar.sh`; saída colada): seção 7.
- Comandos executados: `pytest` direcionado e o gate (`scripts/verificar.sh`), `ruff`, `mypy`, `scripts/verificar_auditoria_texto.py`; `porteiro cabe`, `/api/show` e uma tentativa de `/api/embed` na 11435 (seção 6). Nenhum banco real, nenhuma leitura de rede social.
- Manifesto do commit (`logs/arquivos_094.txt` e `logs/commit_094.txt`, conteúdo colado):

```
docs/docs/doc_094_segunda_auditoria_independente_2026-11-16.md
docs/docs/doc_079_auditoria_texto_por_inteiro_2026-11-08.md
docs/PLAN_agente_nw.md
tests/test_texto_extremo_ponta_a_ponta.py
```

```
test(texto): segunda auditoria independente e prova com textos extremos (brief 094)

Auditoria cega do texto por inteiro: 19 pontos novos (P-046 a P-064) no
relatorio 094; teste permanente com as 15 tarefas do roteamento e textos de
34.195 e 5.000.000 caracteres. Codigo de producao nao mudou.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

- Pendências e decisões que ficaram abertas: lacunas abaixo.
- Resumo, Doing, Backlog e Done do `docs/PLAN_agente_nw.md` atualizados: sim (Backlog e Decisões recebem as lacunas pelo `agente_entregar.sh`).

Para você: ver se há achados novos (P-046 em diante). Há 19, na seção 4.b.

## Lacunas

| # | Lacuna | Destino | Impacto |
|---|---|---|---|
| 1 | P-046: o `/api/embed` vai sem `"truncate": false` e sem `num_ctx`. O `bge-m3` não declara `num_ctx` no Modelfile, e a medição real (texto de 54.389 caracteres na 11435) não respondeu em 300 s. Falta saber se o servidor corta em silêncio antes de 8.192 tokens: medir e, se cortar, fazer o brief "embedding com `truncate: false` e `num_ctx` explícito" | decisão | quebra |
| 2 | P-053: no WhatsApp, o mês que já tem linha na `fila_extracao` é pulado inteiro (`queries/conversa.py:55-61`, `whatsapp/importador.py:49-55`), e as mensagens novas desse mês, vindas numa segunda exportação, nunca viram fatos. Brief proposto: extração por mensagem nova, não por mês | backlog | degrada |
| 3 | P-033 está aprovado como mecanismo, mas no corte por tamanho da redação a conversa do WhatsApp, o histórico e os moldes saem sem aviso; só os fatos avisam (brief 091). A aprovação inclui sair sem aviso? | decisão | degrada |
| 4 | P-056: o filtro de ruído descarta a notícia inteira por "publicidade" em qualquer linha curta, critério que o brief 083 ampliou para corrigir o P-004, além do título de lista e dos 7 dias, sem dizer qual item nem por quê. Decidir o critério antes do brief | decisão | degrada |
| 5 | P-049, P-050 e P-051: falhas registradas na `fila_revisao` que o usuário não vê (gate pulado, termos vazios, desempate ambíguo, imagem sem fato, "processando" sem processar) e `embeddar` direto sem partes na escolha de fatos, na consulta e no apoio. Brief proposto: "toda falha registrada chega ao aviso do pedido" e escolha de fatos por `embeddar_em_partes` | backlog | degrada |
| 6 | P-047, P-048 e P-052: `num_predict` fora do orçamento das partes (deslocamento de contexto não conferido no Ollama), orçamento da captura sem o cerco (uma rodada recusada por bloco grande) e `texto_e_o_proprio_resumo` por `split()` | backlog | nice |
| 7 | P-054, P-055, P-057, P-058, P-060 a P-064: só as mensagens do contato na extração do WhatsApp (decisão de produto), parser do WhatsApp por substring, 2ª imagem do carrossel, dedup da busca antes do texto, resumo do feed descartado, limite de 500 KB do Flask, notas perdidas ao unir, texto sem tela, contato da agenda sem telefone. Contesto também a classificação NA do mínimo de 30 caracteres por bloco (`navegador.py:21`): "Parabéns, Ana!" é texto do contato. Decidir quais viram brief | decisão | nice |
| 8 | P-059: o "…mais" de posts longos só é expandido em `<button>` com o rótulo configurado. Conferir num LinkedIn e num Facebook reais se o texto escondido é lido | pendência | nice |
| 9 | O teste da seção 5 prova as 15 tarefas a partir do montador do prompt; os cortes de seleção anteriores a ele não são provados ponta a ponta com o banco. Um brief que corrigir um deles deve trocar o caso deste arquivo pela entrada pública | dívida | nice |
