# Leitura do executor (parte P0) — caminho crítico do texto

Lido por mim (executor), arquivo inteiro, não por subagente. Pontos no formato do relatório.

## Tabela de certificação (parcial — P0, primeira metade)

| Arquivo | Linhas lidas/total | Resultado | Evidência | Ponto |
|---|---|---|---|---|
| agente_nw/nucleo/relevancia/qualificador.py | 109/109 | CORTA | `_itens_recentes_resumidos` manda ao LLM só (título, domínio) dos 5 itens mais recentes do assunto; o texto do item nunca entra nos prompts `rotular` e `qualificar` | P-001, P-002 |
| agente_nw/nucleo/relevancia/cartoes.py | 102/102 | CORTA | prompt `cartao` recebe (título, domínio, 300 primeiros caracteres) dos 5 itens mais recentes | P-003, P-004 |
| agente_nw/nucleo/agrupamento/agrupador.py | 286/286 | CORTA | o vetor que decide assunto/republicação/divisão vem de `titulo + texto[:2000]` | P-005 |
| agente_nw/nucleo/agrupamento/calibracao.py | 268/268 | CORTA | prompt `prerotular_calibracao` recebe `texto[:2000]` de cada item do par; a amostra é 35 pares da banda + 15 de controle, sorteados | P-006, P-007 |
| agente_nw/nucleo/agrupamento/divisao.py | 50/50 | CERTIFICADO | não manipula texto de conteúdo: divide um assunto só por cosseno entre vetores já gravados | — |
| agente_nw/nucleo/agrupamento/__init__.py | 0/0 | CERTIFICADO | arquivo vazio de pacote | — |
| agente_nw/nucleo/historico.py | 85/85 | CORTA | o histórico que vai ao prompt `redigir_ganchos` leva a mensagem cortada em 100 caracteres e o comentário do usuário em 300, e só as 5 consultas mais recentes | P-008, P-009 |
| agente_nw/nucleo/termos_contato.py | 76/76 | CORTA | prompt `extrair_termos_contato` recebe 12 dos 30 fatos lidos, cada um cortado em 300 caracteres | P-010, P-011 |
| agente_nw/nucleo/redacao.py | 365/365 | CORTA | monta a entrada de `redigir_ganchos`: fatos (10 de 40, 600 caracteres cada), notas do usuário (5, 400 caracteres), histórico (3 consultas), moldes (comentário 300), WhatsApp (10 trocas), manchetes (3 por assunto, só título) | P-012 a P-018 |
| agente_nw/nucleo/prompts/redigir_ganchos.py | 298/298 | CORTA | `cortar_por_tamanho` é o único estimador de tamanho de prompt do projeto (palavras × 1,4 contra 6.000 tokens) e corta histórico para 1, fatos para 5, depois moldes, depois WhatsApp | P-019 |
| agente_nw/nucleo/relevancia/cruzamento.py | 530/530 | CORTA | o gate `avaliar_relacao_objetivo` e o `cruzar_por_que` recebem só título e resumo do cartão; o menu fica com `itens_no_menu` dos candidatos; `interessa` do pedido entra cortado em 5 no ponto de apoio | P-020 a P-023 |
| agente_nw/nucleo/relevancia/candidatos.py | 83/83 | CORTA | a seleção ranqueia por cosseno e fica com `candidatos_por_contato`; `termo_evitado` casa o termo só em título + resumo do cartão | P-024, P-025 |

## Pontos

#### P-001 — agente_nw/nucleo/relevancia/qualificador.py:43 — `_itens_recentes_resumidos`
- Classe: C
- O que é cortado e quanto: dos itens do assunto, só os 5 últimos (`itens_do_assunto[-_MAX_ITENS_RESUMO:]`, `_MAX_ITENS_RESUMO = 5`, linha 19).
- Decisão que depende: prompts `rotular` (título do assunto) e `qualificar` (substancial, conversável, temas, justificativa) — os dois gravados no banco e usados por todo o cruzamento.
- Trecho: `recentes = itens_do_assunto[-_MAX_ITENS_RESUMO:]`
- Justificativa existente: nenhuma (constante sem comentário).
- Por que é analítico: um assunto com 20 notícias é qualificado como se tivesse 5.

#### P-002 — agente_nw/nucleo/relevancia/qualificador.py:44 — `_itens_recentes_resumidos`
- Classe: R
- O que é cortado e quanto: o texto do item é descartado por inteiro; só `(titulo, dominio)` seguem.
- Decisão que depende: as mesmas duas tarefas de LLM do P-001.
- Trecho: `return [(ic.item.titulo, ic.dominio) for ic in recentes]`
- Justificativa existente: nenhuma.
- Por que é analítico: o modelo julga se o assunto é substancial e conversável sem ter visto uma linha do corpo da notícia.

#### P-003 — agente_nw/nucleo/relevancia/cartoes.py:49 — `gerar_cartao`
- Classe: C
- O que é cortado e quanto: só os 5 itens mais recentes (`_MAX_ITENS_CARTAO = 5`, linha 14).
- Decisão que depende: prompt `cartao`, cujo resumo é gravado em `assunto.resumo_cartao` e passa a ser **a** representação do assunto para o gate do objetivo, para o `por_que` e para a redação.
- Trecho: `recentes = itens_do_assunto[-_MAX_ITENS_CARTAO:]`
- Justificativa existente: nenhuma.
- Por que é analítico: o cartão resume o assunto a partir de uma parte dos itens.

#### P-004 — agente_nw/nucleo/relevancia/cartoes.py:51 — `gerar_cartao`
- Classe: T
- O que é cortado e quanto: 300 primeiros caracteres do texto de cada item (`_TRUNCAMENTO_TRECHO = 300`, linha 16).
- Decisão que depende: o mesmo prompt `cartao` do P-003 — e, por consequência, tudo que lê `resumo_cartao`.
- Trecho: `(ic.item.titulo, ic.dominio, (ic.item.texto or "")[:_TRUNCAMENTO_TRECHO]) for ic in recentes`
- Justificativa existente: nenhuma.
- Por que é analítico: 300 caracteres são o primeiro parágrafo; o cartão afirma o assunto inteiro a partir dele.

#### P-005 — agente_nw/nucleo/agrupamento/agrupador.py:88 — `agrupar`
- Classe: T
- O que é cortado e quanto: 2.000 primeiros caracteres do texto do item, concatenados ao título, antes de `embeddar`.
- Decisão que depende: **o vetor do item** — e com ele o assunto a que o item é vinculado, a detecção de republicação (`cosseno_republicacao`), o centróide do assunto, a contagem de fontes independentes e a divisão de assunto. Também a calibração do limiar (`calibracao.py`), que compara esses mesmos vetores.
- Trecho: `texto_para_embeddar = item.titulo if item.texto is None else f"{item.titulo}\n\n{item.texto[:2000]}"`
- Justificativa existente: nenhuma no código. (O `bge-m3` aceita 8.192 tokens, muito mais que 2.000 caracteres, então o corte não é imposto pelo modelo.)
- Por que é analítico: é o corte de maior alcance do projeto — tudo que vem depois (qualificação, cartão, cruzamento) parte do agrupamento feito com esse vetor.

#### P-006 — agente_nw/nucleo/agrupamento/calibracao.py:108 — `_trecho`
- Classe: T
- O que é cortado e quanto: 2.000 primeiros caracteres do texto de cada item do par (`_TRUNCAMENTO_TRECHO = 2000`, linha 25).
- Decisão que depende: prompt `prerotular_calibracao` → rótulo "mesmo assunto?" → limiar `cosseno_mesmo_assunto` **gravado em `config/limiares.yaml`** por `_gravar_novo_limiar`.
- Trecho: `return (item.texto or "")[:_TRUNCAMENTO_TRECHO]`
- Justificativa existente: nenhuma.
- Por que é analítico: o limiar de todo o agrupamento é calibrado com pares julgados por um trecho.

#### P-007 — agente_nw/nucleo/agrupamento/calibracao.py:82,103 — `_amostrar_banda`, `_amostrar_controle`
- Classe: C
- O que é cortado e quanto: 35 pares da banda de dúvida e 15 de controle, sorteados (`random.sample`) de todos os pares possíveis.
- Decisão que depende: a mesma do P-006 (o limiar gravado no YAML).
- Trecho: `return gerador.sample(dentro_da_banda, min(_MAX_PARES_BANDA, len(dentro_da_banda)))`
- Justificativa existente: nenhuma no código; o ADR escrito por `_escrever_adr` registra a composição da amostra, o que mostra que o desenho é amostral de propósito.
- Por que é analítico: é amostragem declarada para calibrar um limiar — provavelmente a exceção mais defensável do projeto, mas a decisão é de Sidarta.

#### P-008 — agente_nw/nucleo/historico.py:56 — `_formatar_ganchos`
- Classe: T
- O que é cortado e quanto: a mensagem redigida entra no histórico com 100 caracteres.
- Decisão que depende: prompt `redigir_ganchos` (o histórico diz ao modelo o que já foi usado e o que não repetir).
- Trecho: `trecho = f' — mensagem: "{mensagem[:100]}"' if isinstance(mensagem, str) and mensagem else ""`
- Justificativa existente: nenhuma.
- Por que é analítico: o modelo recebe a ordem de "não repetir o que já foi usado" vendo 100 caracteres da mensagem anterior.

#### P-009 — agente_nw/nucleo/historico.py:58,10 — `_formatar_ganchos`, `LIMITE_PADRAO`
- Classe: T e C
- O que é cortado e quanto: o comentário do usuário sobre a mensagem entra com 300 caracteres (linha 58); e `historico_recente_para_prompt` lê só as 5 consultas mais recentes (`LIMITE_PADRAO = 5`, linha 10).
- Decisão que depende: prompt `redigir_ganchos`; o comentário do usuário é o que diz por que uma mensagem serviu ou não (brief 050).
- Trecho: `nota = f' — comentário do usuário: "{comentario[:300]}"' if comentario else ""`
- Justificativa existente: nenhuma.
- Por que é analítico: é texto escrito pelo próprio dono do projeto para corrigir a redação, cortado antes de o modelo ler.

#### P-010 — agente_nw/nucleo/termos_contato.py:60 — `termos_do_contato`
- Classe: C
- O que é cortado e quanto: lê 30 fatos (`_FATOS_LIDOS = 30`) e usa 12 (`_FATOS_NO_PROMPT = 12`).
- Decisão que depende: prompt `extrair_termos_contato` → os termos que viram **busca de notícia** sobre o contato (`coleta/rss/google_news.py`).
- Trecho: `publicacoes = [f.conteudo.strip()[:_CARACTERES_POR_FATO] for f in registros[:_FATOS_NO_PROMPT]]`
- Justificativa existente: nenhuma.
- Por que é analítico: define o que o projeto vai buscar no noticiário sobre a pessoa.

#### P-011 — agente_nw/nucleo/termos_contato.py:60 — `termos_do_contato`
- Classe: T
- O que é cortado e quanto: cada publicação (fato) entra com 300 caracteres (`_CARACTERES_POR_FATO = 300`).
- Decisão que depende: a mesma do P-010.
- Trecho: o mesmo da linha 60.
- Justificativa existente: nenhuma.
- Por que é analítico: a descrição de imagem e o texto de post costumam passar de 300 caracteres.

#### P-012 — agente_nw/nucleo/redacao.py:136,39,40 — `_fatos`
- Classe: C
- O que é cortado e quanto: 40 fatos candidatos lidos do banco (`_FATOS_CANDIDATOS = 40`), 10 no prompt (`_FATOS_NO_PROMPT = 10`), dos quais 4 garantidos por recência (`_FATOS_RECENTES_GARANTIDOS = 4`).
- Decisão que depende: prompt `redigir_ganchos` — a mensagem base nasce de uma "peculiaridade" tirada desses fatos.
- Trecho: `candidatos = fatos_q.listar_recentes(conexao, perfil_id, _FATOS_CANDIDATOS)`
- Justificativa existente: docstring de `_escolher_fatos` ("Os 4 fatos mais recentes e, entre os demais, os que mais se parecem com a consulta").
- Por que é analítico: um contato com 200 fatos é redigido a partir de 10.

#### P-013 — agente_nw/nucleo/redacao.py:108 — `_escolher_fatos`
- Classe: T
- O que é cortado e quanto: para escolher quais fatos entram, cada fato é embeddado com 600 caracteres (`_TRECHO_DO_FATO_NO_PROMPT = 600`).
- Decisão que depende: quais fatos entram no prompt (seleção por cosseno contra o texto da consulta).
- Trecho: `vetores = embeddar([consulta, *(f.conteudo[:_TRECHO_DO_FATO_NO_PROMPT] for f in resto)])`
- Justificativa existente: nenhuma na linha; o comentário da linha 41 é sobre o prompt, não sobre o embedding.
- Por que é analítico: a relevância do fato é medida sobre um trecho dele.

#### P-014 — agente_nw/nucleo/redacao.py:146 — `_fatos`
- Classe: T
- O que é cortado e quanto: cada fato entra no prompt com 600 caracteres.
- Decisão que depende: prompt `redigir_ganchos`.
- Trecho: `linhas.append(f"{data[:10]} ({fato.tipo}){sufixo}: {fato.conteudo[:_TRECHO_DO_FATO_NO_PROMPT]}")`
- Justificativa existente: comentário na linha 41 — "o fato fica inteiro no banco; o prompt leva o começo". É explicação, não aprovação.
- Por que é analítico: a peculiaridade que abre a mensagem pode estar depois do caractere 600.

#### P-015 — agente_nw/nucleo/redacao.py:153,155,43 — `_historico`
- Classe: C
- O que é cortado e quanto: 3 consultas anteriores (`_CONSULTAS_NO_HISTORICO = 3`).
- Decisão que depende: prompt `redigir_ganchos` (não repetir o que já foi usado, retomar o fio).
- Trecho: `][:_CONSULTAS_NO_HISTORICO]`
- Justificativa existente: nenhuma.
- Por que é analítico: com mais de 3 consultas, o modelo pode repetir uma mensagem antiga por não tê-la visto.

#### P-016 — agente_nw/nucleo/redacao.py:162,44,45 — `_notas`
- Classe: T e C
- O que é cortado e quanto: 5 notas (`_NOTAS_NO_PROMPT = 5`), cada uma com 400 caracteres (`_TRECHO_DA_NOTA = 400`).
- Decisão que depende: prompt `redigir_ganchos` — a nota do usuário "vale como fato dito por ele" (bloco do prompt) e é a via de correção do brief 050.
- Trecho: `f"[{nota.criado_em[:10]}] {nota.texto[:_TRECHO_DA_NOTA]}"`
- Justificativa existente: nenhuma.
- Por que é analítico: é texto do próprio dono do projeto, cortado antes da análise.

#### P-017 — agente_nw/nucleo/redacao.py:188 — `_moldes`
- Classe: T
- O que é cortado e quanto: o comentário do usuário sobre a mensagem-molde entra com 300 caracteres.
- Decisão que depende: prompt `redigir_ganchos` (o molde dá estrutura e tom).
- Trecho: `sufixo = f' — comentário do usuário: "{molde.comentario[:300]}"' if molde.comentario else ""`
- Justificativa existente: nenhuma.
- Por que é analítico: o comentário é o que explica por que aquele molde funcionou.

#### P-018 — agente_nw/nucleo/redacao.py:69,46 — `_assunto_para_redacao`
- Classe: C e R
- O que é cortado e quanto: 3 itens por assunto (`_MANCHETES_POR_ASSUNTO = 3`) e, desses, só a manchete ("veículo, data: título"). O texto da notícia é carregado em `LinkNoticia.texto` (linha 78), mas o prompt (`_bloco_assuntos`, `prompts/redigir_ganchos.py:176-190`) usa só título, `por_que`, `resumo` do cartão e manchetes — o corpo da notícia nunca vai ao modelo que escreve sobre ela.
- Decisão que depende: prompt `redigir_ganchos`, que escreve duas frases de notícia "só com o que está nas manchetes e no resumo".
- Trecho: `for com_dominio in itens_q.listar_por_assunto(conexao, item.assunto_id)[:_MANCHETES_POR_ASSUNTO]:`
- Justificativa existente: a regra do prompt ("só com o que está nas manchetes e no resumo; proibido inventar número, nome ou data") mostra que a limitação é conhecida e compensada por regra.
- Por que é analítico: a notícia redigida nasce de título + resumo do cartão (que já é o P-003/P-004), nunca do texto.

#### P-019 — agente_nw/nucleo/prompts/redigir_ganchos.py:280-294,93-95,18 — `cortar_por_tamanho`, `estimar_tokens`
- Classe: C (e é o único controle de janela do projeto)
- O que é cortado e quanto: se o prompt estimado passa de 6.000 tokens (`LIMITE_TOKENS_PADRAO`), o histórico cai para 1 consulta (`_HISTORICO_NO_CORTE = 1`) e os fatos para 5 (`_FATOS_NO_CORTE = 5`); se ainda passar, saem os moldes; se ainda passar, sai a conversa do WhatsApp.
- Decisão que depende: prompt `redigir_ganchos`.
- Trecho: `cortada = replace(entrada, historico=entrada.historico[:_HISTORICO_NO_CORTE], fatos=entrada.fatos[:_FATOS_NO_CORTE])`
- Justificativa existente: docstring da função e comentário em `redacao.py:308` ("Se o molde sair do prompt por corte de tamanho, a mensagem não grava proveniência dele"). A estimativa é declarada aproximada em `estimar_tokens` ("Contagem aproximada: palavras × 1,4").
- Por que é analítico: é corte de conteúdo do prompt. Vale notar os dois lados: é o **único** lugar do projeto que impede o prompt de passar da janela (o `num_ctx` de `redigir_ganchos` é 8.192 no `air16` e 16.384 no `pro48`, contra 6.000 estimados aqui), e ao mesmo tempo a ordem de sacrifício (histórico e fatos antes de moldes e WhatsApp) é uma decisão de produto que nunca foi aprovada explicitamente.

#### P-020 — agente_nw/nucleo/relevancia/cruzamento.py:155 — `_aplicar_gate_objetivo`
- Classe: R
- O que é cortado e quanto: o gate recebe `(titulo_gerado, resumo_cartao)` de cada candidato; nem o texto das notícias nem as manchetes.
- Decisão que depende: prompt `avaliar_relacao_objetivo` — o sim/não que **descarta** o assunto do menu (brief 049), gravado como `status="descartado"`, `motivo="sem relação com o objetivo (juízo do modelo)"`.
- Trecho: `candidatos_gate = [(assunto.titulo_gerado or "", assunto.resumo_cartao) for assunto, _ in demais]`
- Justificativa existente: o comentário das linhas 468-470 explica para que serve o gate, não por que ele vê só título e resumo.
- Por que é analítico: o descarte é definitivo para aquele pedido e se baseia no resumo do cartão, que já vem dos P-003/P-004.

#### P-021 — agente_nw/nucleo/relevancia/cruzamento.py:272,481 — `cruzar_contato`, `cruzar_contato_por_consulta`
- Classe: C
- O que é cortado e quanto: dos candidatos aprovados, só `limiares.conector.itens_no_menu` entram no menu (valor em `config/limiares.yaml`).
- Decisão que depende: o menu entregue ao usuário e os registros `assunto_contato`; o que fica fora não é gravado nem como descartado.
- Trecho: `selecionados_para_menu = demais[: limiares.conector.itens_no_menu]`
- Justificativa existente: nenhuma no código.
- Por que é analítico: define o conjunto que vai à redação. Pode ser lido como decisão de tamanho de tela, e é por isso que precisa da palavra de Sidarta.

#### P-022 — agente_nw/nucleo/relevancia/cruzamento.py:282-285,488-491 — `assuntos_para_prompt`
- Classe: R
- O que é cortado e quanto: o prompt `cruzar_por_que` recebe `(titulo_gerado, tipo, ponto_de_apoio)` — nem resumo, nem manchete, nem texto.
- Decisão que depende: prompt `cruzar_por_que` → o campo `por_que` gravado em `assunto_contato`, que é mostrado ao usuário e reaproveitado na redação.
- Trecho: `assuntos_para_prompt: list[tuple[str, str, str | None]] = [(assunto.titulo_gerado or "", avaliacao.tipo, avaliacao.ponto_de_apoio) ...]`
- Justificativa existente: comentário das linhas 52-53 — "O 'por quê' recebe só o título do assunto e os temas: qualquer posição do contato ('ele apoia X') é invenção do modelo". É uma justificativa escrita e deliberada (reduzir invenção), mas não é aprovação registrada.
- Por que é analítico: o `por_que` é texto que o usuário lê e que a redação reusa.

#### P-023 — agente_nw/nucleo/relevancia/cruzamento.py:407,49 — `cruzar_contato_por_consulta`
- Classe: C
- O que é cortado e quanto: dos interesses do pedido, só 5 (`_MAXIMO_INTERESSA_NO_APOIO = 5`) viram termos embeddados para o ponto de apoio.
- Decisão que depende: `avaliar_por_consulta` → `ponto_de_apoio` e `aderencia_consulta`, que entram no score do menu.
- Trecho: `t for t in [contexto.assunto, *contexto.interessa[:_MAXIMO_INTERESSA_NO_APOIO]] if t.strip()`
- Justificativa existente: nenhuma.
- Por que é analítico: interesse escrito pelo usuário no pedido que não é medido.

#### P-024 — agente_nw/nucleo/relevancia/candidatos.py:31,83 — `selecionar`, `selecionar_por_consulta`
- Classe: C
- O que é cortado e quanto: dos assuntos qualificados não vistos, só `limiares.conector.candidatos_por_contato` seguem (ranqueados por cosseno).
- Decisão que depende: todo o cruzamento a jusante (o gate e o menu só veem esses).
- Trecho: `return [assunto for assunto, _ in ranqueados[:limite]]`
- Justificativa existente: a docstring de `selecionar_por_consulta` explica que os evitados saem antes do corte "para não ocupar vaga" — reconhece o corte, não o justifica.
- Por que é analítico: é o primeiro afunilamento do noticiário para aquele contato.

#### P-025 — agente_nw/nucleo/relevancia/candidatos.py:41 — `termo_evitado`
- Classe: R
- O que é cortado e quanto: o termo a evitar é procurado só em `titulo_gerado + resumo_cartao`, não no texto das notícias do assunto.
- Decisão que depende: o descarte "evitado pelo contexto" (o `evitar` explícito do pedido e o `nao_me_interessa` do usuário).
- Trecho: `texto = _sem_acento_e_caixa(f"{assunto.titulo_gerado or ''} {assunto.resumo_cartao or ''}")`
- Justificativa existente: docstring — "Correspondência literal, sem acento e sem caixa, no título e no resumo do assunto". Declara o escopo, não o justifica.
- Por que é analítico: um assunto cujo termo proibido aparece só no corpo da notícia passa o filtro.
