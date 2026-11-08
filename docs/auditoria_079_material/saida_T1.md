# Auditoria T1 — tests/ (53 arquivos, 6.770 linhas; todos lidos do início ao fim)

Regra de certificação simplificada de testes: nenhum arquivo contém corte analítico próprio. Todos `CERTIFICADO`.
Marcações na coluna Ponto: `CORTE-DOC` = o teste documenta um corte de produção (ver bloco 2); `ESCONDE` = a entrada do teste esconde um corte possível (ver bloco 3); `—` = só exercita.

## 1. Tabela de certificação

| Arquivo | Linhas lidas/total | Resultado | Evidência (uma linha) | Ponto |
|---|---|---|---|---|
| tests/__init__.py | 0/0 | CERTIFICADO | Arquivo vazio. | — |
| tests/coleta_falsa.py | 117/117 | CERTIFICADO | Rede falsa (Google/Bing/RSS); página de notícia de ~840 caracteres ("Texto relevante..." x20) e títulos curtos: nunca exerce um texto longo. | ESCONDE |
| tests/llm_falso.py | 30/30 | CERTIFICADO | Proveniência falsa e parsers do prompt (divide candidatos/assuntos numerados); sem manipular texto de conteúdo. | — |
| tests/test_agente_entregar.py | 174/174 | CERTIFICADO | Testa o script de entrega (git falso, gate falso); só infraestrutura. | — |
| tests/test_agente_lacunas.py | 186/186 | CERTIFICADO | Testa o script que copia lacunas do relatório para o PLAN; texto de documento passa inteiro. | — |
| tests/test_agrupador.py | 272/272 | CERTIFICADO | Itens com `texto=None` e título de 6 a 12 caracteres; embedder falso indexado pelo próprio título; não prova o que é embeddado de um texto real. | ESCONDE |
| tests/test_ambiente.py | 17/17 | CERTIFICADO | Carrega a extensão sqlite_vec; só infraestrutura. | — |
| tests/test_assunto_contato_marcacao.py | 96/96 | CERTIFICADO | Marcar usado/nao_serve em `assunto_contato`; sem texto de conteúdo. | — |
| tests/test_assunto_contato.py | 124/124 | CERTIFICADO | CRUD e filtros de `assunto_contato`; sem texto de conteúdo. | — |
| tests/test_assuntos_qualificacao.py | 166/166 | CERTIFICADO | Consultas de candidatos à qualificação; o teste da linha 95 afirma `LIMIT` (3 criados, 2 devolvidos). | CORTE-DOC |
| tests/test_assuntos_sem_cartao.py | 62/62 | CERTIFICADO | `listar_qualificados_sem_cartao`; a linha 52 afirma limite (5 criados, 3 devolvidos). | CORTE-DOC |
| tests/test_assuntos.py | 138/138 | CERTIFICADO | CRUD de `assunto`, janela de candidatos, fechar inativos; filtros por data/n_itens, sem corte de texto. | — |
| tests/test_backup.py | 83/83 | CERTIFICADO | Backup/restauração/retenção de 7 dias de arquivos .db; só infraestrutura. | — |
| tests/test_base_mais_ganchos.py | 46/46 | CERTIFICADO | Ordem base + ganchos na redação, LLM falso devolve gancho montado; não inspeciona o prompt. | ESCONDE |
| tests/test_calibracao.py | 212/212 | CERTIFICADO | Amostragem de pares para calibrar o limiar (controle alvo 15, banda teto 35, `random.Random`); itens só com título. | CORTE-DOC, ESCONDE |
| tests/test_candidatos_por_consulta.py | 119/119 | CERTIFICADO | `selecionar_por_consulta`; a linha 117 afirma corte em 10 de 12 candidatos não evitados. | CORTE-DOC |
| tests/test_candidatos.py | 111/111 | CERTIFICADO | `selecionar` por aderência; `test_respeita_limite` (linha 103) afirma 3 de 5. | CORTE-DOC |
| tests/test_canonicalizar.py | 71/71 | CERTIFICADO | URL canônica e `hash_titulo` com títulos de 40 a 50 caracteres; normalização, sem corte. | — |
| tests/test_capturas_busca.py | 208/208 | CERTIFICADO | Filtra candidatos de busca em rede social (nome, descrição, link); descrições de 1 a 3 linhas curtas. | ESCONDE |
| tests/test_capturas_extrator.py | 66/66 | CERTIFICADO | `extrair` com bloco curto de uma linha e cliente falso que ignora o prompt. | ESCONDE |
| tests/test_capturas_leitor.py | 429/429 | CERTIFICADO | Leitor de redes; linhas 223-253 afirmam `maximo_blocos` (6 blocos, só 3 chamadas ao LLM), 363-405 `maximo_imagens`; linha 284 prova que o fato guarda o texto integral do bloco. | CORTE-DOC, ESCONDE |
| tests/test_capturas_navegador.py | 205/205 | CERTIFICADO | Leitura de página com rolagem; linhas 164-190 afirmam `maximo_imagens=3` e `max_rolagens`; blocos curtos. | CORTE-DOC, ESCONDE |
| tests/test_cartoes_pendentes.py | 118/118 | CERTIFICADO | `gerar_pendentes`; linha 110 afirma limite (3 criados, 2 candidatos); item de 41 caracteres e LLM falso que ignora o prompt. | CORTE-DOC, ESCONDE |
| tests/test_cartoes.py | 125/125 | CERTIFICADO | `gerar_cartao`; um item só, `texto` de 41 caracteres, LLM falso que ignora o prompt. | ESCONDE |
| tests/test_cli_agenda.py | 66/66 | CERTIFICADO | Comandos `ficha` e `confirmar-tags`; sem texto de conteúdo. | — |
| tests/test_cli_agrupamento.py | 116/116 | CERTIFICADO | CLI agrupar/calibrar sem itens; só casos vazios. | — |
| tests/test_cli_certificar.py | 103/103 | CERTIFICADO | Comando `certificar` sobre contagens e log JSONL; sem texto de conteúdo. | — |
| tests/test_cli_cruzamento.py | 119/119 | CERTIFICADO | CLI `menu` e `cruzar` sem dados; só casos vazios. | — |
| tests/test_cli_markdown.py | 140/140 | CERTIFICADO | Exportar menu .md e ler marcações; títulos de 6 caracteres. | — |
| tests/test_cli_pedir_confirmacao.py | 417/417 | CERTIFICADO | Menu de confirmação de perfil nas listas de rede; cabeçalhos curtos ("Sócio, escritório tributarista"); `maximo_entradas=2000` só em fixture de config. | — |
| tests/test_cli_pedir_redacao.py | 175/175 | CERTIFICADO | `pedir` com redação; item sem `texto` e LLM falso devolve gancho pronto. | ESCONDE |
| tests/test_cli_pedir.py | 93/93 | CERTIFICADO | `pedir` imprime o pedido extraído; frase de pedido curta. | — |
| tests/test_cli_qualificacao.py | 157/157 | CERTIFICADO | CLI qualificar/cartão; item com `texto` de 17 caracteres e LLM falso que ignora o prompt. | ESCONDE |
| tests/test_cli_servidor_na_porta.py | 32/32 | CERTIFICADO | Classifica processo/porta do Ollama; só infraestrutura. | — |
| tests/test_coleta_bloqueio.py | 163/163 | CERTIFICADO | Coleta com bloqueio 503; linhas 118-163 afirmam `maximo_itens_novos_por_feed=4` (feed com 6, 4 processados); página de ~840 caracteres. | CORTE-DOC, ESCONDE |
| tests/test_coleta_cooldown.py | 94/94 | CERTIFICADO | Cooldown de host no banco; fluxo de rede, não de texto. | — |
| tests/test_coleta_degradacao.py | 67/67 | CERTIFICADO | Google/Bing bloqueados: coleta termina sem erro e sem notícia. | — |
| tests/test_coleta_fonte_alternativa.py | 77/77 | CERTIFICADO | Bing News RSS; linha 56 usa notícia de 30 dias para exercitar o filtro de ruído por idade. | — |
| tests/test_coleta_fumaca.py | 79/79 | CERTIFICADO | Fumaça com rede real (`rede_real`, fora do gate); conta itens, não olha texto. | — |
| tests/test_coleta_retomada.py | 98/98 | CERTIFICADO | Retomada de ciclo por sentinela; página de ~840 caracteres. | ESCONDE |
| tests/test_coleta_reuso_termo.py | 65/65 | CERTIFICADO | Reuso de termo buscado há pouco; normaliza o termo (caixa/acento/espaços). | — |
| tests/test_coleta_rotulo_fonte.py | 95/95 | CERTIFICADO | Rótulo da fonte de notícias na tela e no terminal; texto de apresentação. | — |
| tests/test_coleta_teto_consultas.py | 44/44 | CERTIFICADO | Linhas 10-24 afirmam teto de 4 termos de busca; linhas 27-44 afirmam parada de buscas com `candidatos_suficientes`. | CORTE-DOC |
| tests/test_comentario_mensagem.py | 52/52 | CERTIFICADO | Persistência de comentário por gancho (aparado, vazio apaga); comentários de poucas palavras. | — |
| tests/test_comentario_no_prompt.py | 53/53 | CERTIFICADO | Linha 43 afirma que só as notas mais recentes (5 de 7) entram no prompt da redação. | CORTE-DOC |
| tests/test_comentario_sob_orcamento.py | 24/24 | CERTIFICADO | Linha 9 afirma que o prompt perto de 6.000 tokens corta o histórico mas mantém nota e comentário. | CORTE-DOC |
| tests/test_concorrencia.py | 40/40 | CERTIFICADO | Leitura SQLite durante escrita; só infraestrutura. | — |
| tests/test_configuracao.py | 210/210 | CERTIFICADO | Valida YAMLs de config; linhas 143-155 afirmam valores de corte de `config/limiares.yaml`. | CORTE-DOC |
| tests/test_configurador.py | 114/114 | CERTIFICADO | Salvar/adicionar/remover tema do usuário; embedder falso não inspeciona o texto embeddado. | ESCONDE |
| tests/test_console_apagar_unir.py | 210/210 | CERTIFICADO | Rotas Flask de apagar/unir contato; LLM falso devolve resposta vazia. | — |
| tests/test_console_busca_rede_social.py | 243/243 | CERTIFICADO | Rotas de busca de candidatos em rede; `estado` devolve "x"*1000 só para passar o mínimo de login. | — |
| tests/test_console_configurar_perfil.py | 235/235 | CERTIFICADO | Rotas de perfil/temas; descrição mínima de 8 palavras validada, embedder falso. | — |
| tests/test_console_contatos.py | 214/214 | CERTIFICADO | Rotas de contatos/fichas/texto; texto de uma frase vai à fila de extração com LLM falso vazio. | ESCONDE |

## 2. Cortes de produção documentados por teste

Formato: `arquivo de teste:linha → arquivo de produção → o que o teste afirma`. Os arquivos de produção abaixo foram inferidos pelos imports e nomes dos testes; este leitor não abriu o código de produção (trabalho só de leitura sobre `tests/`).

- tests/test_calibracao.py:46-56 → `agente_nw/nucleo/agrupamento/calibracao.py::_amostrar_controle` → amostra de controle com alvo de 15 pares (12 iguais + 3 distintos de 23 existentes).
- tests/test_calibracao.py:59-64 → `agente_nw/nucleo/agrupamento/calibracao.py::_amostrar_banda` → "respeita teto de 35": 50 pares na banda, 35 avaliados (amostragem aleatória por `random.Random`); os demais 15 não são rotulados.
- tests/test_assuntos_qualificacao.py:95-109 → `agente_nw/nucleo/database/queries/assuntos.py::listar_candidatos_qualificacao` → parâmetro `limite` (3 assuntos elegíveis, 2 devolvidos).
- tests/test_assuntos_sem_cartao.py:52-62 → `agente_nw/nucleo/database/queries/assuntos.py::listar_qualificados_sem_cartao` → limite (5 elegíveis, 3 devolvidos).
- tests/test_cartoes_pendentes.py:110-118 → `agente_nw/nucleo/relevancia/cartoes.py::gerar_pendentes` → limite (3 assuntos qualificados sem cartão, 2 candidatos processados).
- tests/test_candidatos.py:103-111 → `agente_nw/nucleo/relevancia/candidatos.py::selecionar` → limite (5 assuntos, 3 devolvidos).
- tests/test_candidatos_por_consulta.py:95-119 → `agente_nw/nucleo/relevancia/candidatos.py::selecionar_por_consulta` → corte em 10 (12 não evitados, 10 selecionados; os 2 restantes ficam fora); evitados saem antes do corte.
- tests/test_capturas_leitor.py:223-253 → `agente_nw/coleta/capturas/leitor.py::ler_redes_sociais_do_contato` (`maximo_blocos`) → com 6 blocos capturados e `maximo_blocos=2`, só 3 chamadas ao LLM; para ao gravar 2 fatos; mensagem "examino até ... bloco 2/6".
- tests/test_capturas_leitor.py:363-405 → `agente_nw/coleta/capturas/leitor.py` (`maximo_imagens`) → só as imagens até o máximo são descritas pelo modelo de visão; sem máximo (padrão), nenhuma imagem é descrita (linha 408-429).
- tests/test_capturas_navegador.py:164-190 → `agente_nw/coleta/capturas/navegador.py::ler` (`maximo_imagens=3`) → acumula imagens únicas só até 3; pede o lote seguinte com `maximo=1`.
- tests/test_capturas_navegador.py:115-147 e vários → `agente_nw/coleta/capturas/navegador.py::ler` (`max_rolagens`) → a leitura rola um número máximo de vezes (`max_rolagens=1` ou `2`); o resto da página não é lido.
- tests/test_coleta_bloqueio.py:118-163 → `agente_nw/coleta/rss/leitor.py::coletar` (`maximo_itens_novos_por_feed=4`) → feed de 6 notícias, só 4 novas processadas na primeira rodada; as 2 restantes só entram na segunda.
- tests/test_coleta_teto_consultas.py:10-24 → `agente_nw/coleta/rss/google_news.py::selecionar_termos` (`max_consultas_por_pedido`, valor 4) → de 6 termos possíveis (assunto, 2 do contexto, 3 de termos_busca), só 4 são buscados, na ordem assunto, termos dos ganchos, termos_busca.
- tests/test_coleta_teto_consultas.py:27-44 → `agente_nw/coleta/rss/leitor.py::coletar` (`candidatos_suficientes=10`) → a coleta para de abrir buscas quando já passou de 10 candidatos (2 das 4 buscas).
- tests/test_comentario_no_prompt.py:43-53 → `agente_nw/nucleo/redacao.py::redigir` (notas do contato no prompt de `redigir_ganchos`) → de 7 notas, só as 5 mais recentes (nota 2 a nota 6) entram no prompt; notas 0 e 1 ficam de fora.
- tests/test_comentario_sob_orcamento.py:9-24 → `agente_nw/nucleo/prompts/redigir_ganchos.py::construir_prompt` (`limite_tokens=6000`) → perto do limite, corta o histórico de consultas anteriores (3 consultas, só a "consulta 0" fica; o comentário da segunda sai) e mantém só a nota e o comentário; sem o limite o prompt passa de 6.000 tokens.
- tests/test_configuracao.py:143-151 → `config/limiares.yaml` (lido por `Limiares`) → afirma `qualificacao.teto_por_dia == 40`, `conector.candidatos_por_contato == 10`, `conector.itens_no_menu == 5`, `agrupamento.janela_dias == 7`, `agrupamento.itens_para_dividir == 12`.
- tests/test_cli_agrupamento.py, test_cli_cruzamento.py, test_cli_qualificacao.py, test_console_*.py (fixture `_limiares()`) → `agente_nw/nucleo/modelos/configuracao.py` → repetem os mesmos valores de corte (`itens_no_menu=5`, `candidatos_por_contato=10`, `teto_por_dia=40`, `maximo_entradas=2000` em `ListasLimiares`) em fixtures; não os afirmam.
- tests/test_coleta_fonte_alternativa.py:56-65 → `agente_nw/coleta/rss/` (filtro de ruído por idade, `dias_max_primeira_aparicao=7`) → notícia de 30 dias é descartada (`descartados_ruido == 2`). É filtro de item inteiro, não corte de texto.

Nenhum teste cita 2.000 caracteres, nem um número de linhas do corpo, nem N meses de WhatsApp.

## 3. Entradas que escondem um corte possível

- tests/test_agrupador.py:98-108, 121-128 e tests/test_calibracao.py:176-186: `Item(texto=None)`, título de 6 a 12 caracteres, `embeddar` falso devolve `self._vetores[texto]` indexado pelo próprio título. Não exerce o que é embeddado quando o item tem corpo: um corte do texto antes do embedding passaria despercebido.
- tests/test_cartoes.py:49-57, tests/test_cartoes_pendentes.py:51-60, tests/test_cli_qualificacao.py:120-128: um único item por assunto, `texto` de 17 a 41 caracteres, LLM falso devolve `RespostaCartao` fixa e ignora `prompt`. Não detecta corte de texto do item nem da lista de itens do assunto no prompt do cartão.
- tests/test_cli_pedir_redacao.py:77-87, tests/test_base_mais_ganchos.py, tests/test_comentario_no_prompt.py: item sem `texto`, LLM falso devolve gancho montado; só o teste de notas e comentário olha o prompt (e só procura trechos curtos).
- tests/test_capturas_extrator.py:35, 47, 56, 64 e tests/test_capturas_leitor.py:62-64, 105, 153, 229, 262: blocos de uma linha (40 a 100 caracteres); `_ClienteLLMFake` decide por `chave in prompt` (substring), então um prompt truncado ainda casaria. Não prova que um bloco longo vai inteiro para o prompt de `extrair_captura_rede_social`. Compensação: tests/test_capturas_leitor.py:284-310 prova que o fato grava o texto integral do bloco, não o resumo do modelo.
- tests/test_capturas_navegador.py:39-42, 49-51: blocos de 70 a 90 caracteres e preenchimento de ~1.500 caracteres; não exercita bloco longo.
- tests/coleta_falsa.py:18-19 e tests/test_coleta_bloqueio.py:14-15, tests/test_coleta_retomada.py:14-15: a página da notícia é um `<article>` de ~840 caracteres (42 caracteres x 20) e `teaser_minimo_caracteres=400`; não exerce texto de notícia longo nem corte do corpo antes de gravar `item.texto`.
- tests/test_canonicalizar.py:61-71: `hash_titulo` só com títulos curtos de uma linha.
- tests/test_configurador.py:18-24 e tests/test_console_configurar_perfil.py:72-77: `embeddar` falso devolve `[0.1]*1024` e `chamadas` registra os textos, mas nenhum teste confere o conteúdo ou o tamanho do texto embeddado do tema.
- tests/test_console_contatos.py:179-200: texto de uma frase vai à `fila_extracao` e o LLM falso devolve `esquema()` vazio; não exerce texto longo na extração de fatos.
- tests/test_cli_pedir_confirmacao.py:109-122: lista de rede com cabeçalhos de 1 linha; `ListasLimiares(maximo_entradas=2000)` aparece na config mas nenhum teste afirma seu efeito.
- tests/test_comentario_mensagem.py e tests/test_comentario_no_prompt.py: comentários com poucas palavras; `gancho_uso.comentar` aceita texto aparado, sem teste de comentário longo.

## 4. Pontos encontrados

Nenhum ponto T/C/R/P/NA em arquivos de teste (regra "Testes": o teste não gera ponto próprio). Os cortes de produção e as entradas que os escondem estão nos blocos 2 e 3.
