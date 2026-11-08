# ARQUITETURA.md — agente_nw

> Arquitetura hexagonal. Dependências resolvidas em `config/container.py`. Nenhum módulo instancia cliente de LLM, conexão de banco ou cliente HTTP diretamente.

---

## 1. Fluxo

Fluxo da Etapa 1 (desenho original; o ciclo diário às 05h00 e seus LaunchAgents foram removidos no brief 016 — hoje cada etapa roda quando Sidarta a dispara, pelo console ou pela CLI, e o fluxo principal é o pedido em texto livre da tela única, ver §10), saída por contato:

```
1. Coleta
   feeds RSS + consultas Google News (geradas dos temas) ──► feedparser + trafilatura
                                                                       │
2. Embedding e agrupamento                                            ▼
   bge-m3 ──► sqlite-vec ──► cosseno contra centróides dos assuntos abertos (janela 7 dias)
                                                                       │
3. Qualificação                                                       ▼
   candidatos = união dos temas de TODOS os perfis ativos (usuário + cada contato ativo)
   contrato "qualificar" (substancial, conversável, temas) ── teto 40/dia
                                                                       │
4. Pré-seleção por contato                                            ▼
   centróide do perfil (contato) × centróides dos assuntos qualificados ──► 10 candidatos
                                                                       │
5. Pontuação e piso — regra do conector (seção 5)                     ▼
   aderência ao contato + aderência ao usuário (com nível) + conversabilidade
   tipo: conector / viável com esforço / fora do domínio ──► 5 primeiros seguem
                                                                       │
6. Cruzamento                                                         ▼
   contrato "cruzar" (parte 2, com modelo) ──► por_que de cada assunto do menu, ou sem_assunto
                                                                       │
7. Cartão                                                              ▼
   três linhas por assunto que entrou em algum menu
                                                                       │
8. Entrega                                                             ▼
   console: telas Contatos / Menu / Temas ── e menu_AAAA-MM-DD.md na pasta de saída
```

A extensão do Chrome (captura assistida de rede social), a exportação de conversa do WhatsApp e a entrada de mídia (foto, vídeo, captura de tela) são camadas adicionais de coleta do lado do contato que alimentam os passos 2 a 4 — entram como entradas da ficha marcadas **"Etapa 2"**.

## 2. Estrutura do repositório

```
agente_nw/
├── AGENTS.md                  # regras do executor (commitado)
├── pyproject.toml
├── .gitignore
├── temas.exemplo.yaml
├── fontes.exemplo.yaml
├── config/
│   ├── container.py          # fábrica de dependências: llm(), banco(), http()
│   ├── llm_routing.yaml      # perfis de LLM: tarefa → modelo, num_ctx, temperatura, format
│   ├── limiares.yaml         # valores calibrados; nunca constante no código
│   ├── local.exemplo.yaml    # caminhos e URLs identificadoras (o local.yaml fica fora do git)
│   └── local.yaml            # por máquina: ollama_url, perfil_llm (ausente = air16)
├── agente_nw/                # pacote Python
│   ├── cli.py                # comandos: verificar-ambiente, importar-temas, importar-agenda, ficha,
│   │                         #   ativar, confirmar-tags, coletar, processar-fila, agrupar, qualificar,
│   │                         #   cartao, cruzar, menu, exportar-menu, ler-marcacoes, pedir, listas,
│   │                         #   preparar, extensao, console, copiar-banco, restaurar-backup, ...
│   ├── nucleo/
│   │   ├── modelos/          # contratos Pydantic v2, frozen=True, um módulo por entidade
│   │   ├── prompts/          # um arquivo por contrato, com esquema JSON e um exemplo resolvido
│   │   ├── database/
│   │   │   ├── conexao.py    # abre o banco: WAL, foreign_keys, busy_timeout, sqlite-vec
│   │   │   ├── migracoes.py  # aplica scripts/migracoes/*.sql em ordem
│   │   │   └── queries/      # todo SQL isolado aqui
│   │   ├── llm.py            # cliente único do Ollama
│   │   ├── vetores.py        # embeddings, cosseno, centróide
│   │   ├── pedido.py, fluxo.py   # pedido em texto livre e sua execução em segundo plano
│   ├── orquestracao.py       # a sequência pedido → ganchos, única; terminal e console entram como `Canal` (brief 056)
│   │   ├── localizacao.py, confirmacao.py   # pessoa nas listas do usuário e confirmação
│   │   ├── consulta.py, termos_contato.py   # motor dirigido pela consulta e termos de busca
│   │   ├── redacao.py, historico.py         # mensagem base, ganchos e histórico das consultas
│   │   ├── relevancia/       # qualificação, pontuação, piso, tipo (regra do conector)
│   │   ├── agrupamento/      # centróide, janela, reabertura, divisão, calibração
│   │   └── saidas/           # exportação Markdown
│   ├── coleta/
│   │   ├── rss/              # feedparser, trafilatura, canonicalização, google news, fonte alternativa
│   │   └── capturas/         # leitura de rede social sob demanda (backend: extensao_backend.py)
│   ├── ponte/                # servidor local 127.0.0.1:8766 + página-ponte (brief 044)
│   ├── perfil/               # importação da agenda, extração de texto, lacunas, centróide de perfil
│   ├── console/              # Flask + templates; a tela única (`/`) é a interface principal
│   └── integracoes/          # (Etapa 3; vazio)
├── extensao/                 # extensão do Chrome (manifest v3): lê rede social no navegador do usuário
├── scripts/
│   ├── migracoes/            # 001_inicial.sql ... 014_comentarios.sql, aplicados em ordem
│   ├── instalar_macos.sh
│   ├── agente_entregar.sh    # gate + commit + push pelo manifesto de logs/ (roda Sidarta, brief 057)
│   ├── commitar.sh           # commit por lista de arquivos e mensagem em arquivo (roda Sidarta)
│   └── verificar.sh          # ruff + mypy --strict + pytest; resumo na tela, detalhe em logs/ (roda Sidarta)
├── .claude/                  # settings.json e hooks/guarda_comando.py: trava dos comandos do modelo
├── docs/                     # fora do git: PLANO, ARQUITETURA, PLAN, briefs/, docs/, historico/, adr/
├── dados/                    # agente.db, backups/, logs/ — fora do git
├── saidas/                   # menu_AAAA-MM-DD.md — fora do git
├── logs/                     # fora do git
└── tests/
```

Nome do pacote e da pasta é sempre `agente_nw`. Removidos: `scripts/launchd/` e os LaunchAgents (brief 016); o comando `ciclo` também não existe mais em `cli.py`. Removido no brief 046: `nucleo/sensivel.py`.

## 3. Contratos de dados

O mesmo esquema serve às quatro etapas. Cada tabela nasce na migração da etapa que a usa — a migração `001_inicial.sql` contém só as tabelas da Etapa 1.

| Tabela | Campos | Nasce em |
|---|---|---|
| `schema_version` | versao, aplicada_em | Etapa 1 |
| `tema` | id, nome **UNIQUE**, descricao (frase corrida), sinonimos[], embedding, criado_em | Etapa 1 |
| `perfil` | id, tipo (usuario/contato), nome, apelido, email, telefone (chave de identidade entre fontes), empresa, cargo, setor, cidade, naturalidade, linguas[], formacao, tem_filhos, faixa_etaria, notas, ativo, gerar_agora, centroide, ultima_coleta, criado_em, atualizado_em | Etapa 1 |
| `perfil_tema` | perfil_id, tema_id, peso 1–5, origem (declarada/sugerida/importada/captura/imagem/conversa), confirmado, nivel (dominio/interesse/curiosidade, só quando perfil é usuário; nulo para contatos), registrado_em — **UNIQUE (perfil_id, tema_id)** | Etapa 1 |
| `fonte` | id, nome, url_feed, dominio, tipo, confiabilidade 0–10 | Etapa 1 |
| `item` | id, fonte_id, url_canonica, titulo, texto, publicado_em, coletado_em, hash, embedding, assunto_id | Etapa 1 |
| `assunto` | id, titulo_gerado, primeiro_visto, ultimo_visto, n_itens, n_fontes_independentes, status, centroide, temas[], substancial 0–1, conversavel 0–1, justificativa, resumo_cartao | Etapa 1 |
| `assunto_contato` | id INTEGER PRIMARY KEY, assunto_id, perfil_id, gerado_em, tipo (conector/viavel_com_esforco/fora_do_dominio), aderencia_contato, aderencia_usuario, conversavel, score, por_que, status (novo/usado/nao_serve/descartado), motivo | Etapa 1 — **é o menu** |
| `fato` | id, perfil_id, data_do_fato, tipo, conteudo, fonte, registrado_em | Etapa 1 — só inserção, nunca editada |
| `fila_extracao` | id, perfil_id, texto, criado_em, processado, erro | Etapa 1 |
| `descarte_sensivel` | id, perfil_id, origem_texto, termo, registrado_em | Etapa 1 |
| `conta` | id, perfil_id, rede, url, handle, ativa, ultima_coleta | Etapa 2 |
| `captura` | id, perfil_id, conta_id, coletado_em, url_origem, texto_bruto, processada | Etapa 2 |
| `midia_processada` | hash, perfil_id, tipo (imagem/quadro_video/captura_tela), origem, processado_em, n_tags | Etapa 2 |
| `conversa_tema` | perfil_id, tema_id, n_mensagens, ultima_data, processado_em | Etapa 2 |
| `pacote_troca` | id, perfil_id ou nulo, direcao (exportado/importado), conteudo_json, pseudonimizado, criado_em, processado | Etapa 4 |

## 4. Contratos do motor

Independentes de modelo. Todo módulo que precisa de inteligência chama uma destas funções e recebe JSON validado por esquema. Nenhum outro módulo sabe qual modelo está rodando.

**qualificar** — recebe um assunto (título, itens resumidos, fontes) e a lista de temas conhecidos. Devolve:

```json
{"substancial": 0.8, "conversavel": 0.7, "temas": ["credito_pj", "autonomos"], "justificativa": "regra nova, ainda em disputa, dá conversa sem ser especialista"}
```

**cruzar** — em duas partes, e só a segunda usa modelo.

A primeira parte é determinística e roda em Python: `aderencia_contato` = cosseno entre o centróide do assunto e o centróide do contato; `aderencia_usuario` = maior cosseno entre o centróide do assunto e cada tema do usuário, multiplicado pelo peso do nível (domínio 1,0 / interesse 0,7 / curiosidade 0,4); `conversavel` = a nota que a qualificação já deu. Score = 50 × aderência ao contato + 30 × aderência ao usuário + 20 × conversável, em 0–100. Ver a regra do conector (seção 5) para o tipo. Os `fora_do_dominio` são gravados com status `descartado` e param aqui. Os demais são ordenados por tipo (conectores primeiro) e depois por score; os 5 primeiros seguem.

A segunda parte recebe o contato (apelido e tags), as tags do usuário com nível, e os até 5 assuntos já selecionados com seu tipo. O modelo escreve só o `por_que`, uma linha por assunto, apontando nos viáveis com esforço qual é o ponto de apoio do usuário:

```json
{"menu": [{"assunto_id": 812, "tipo": "conector", "score": 74,
           "por_que": "ele trabalha com crédito e vocês dois lidam com autônomos"},
          {"assunto_id": 799, "tipo": "viavel_com_esforco", "score": 58,
           "por_que": "é o setor dele; seu apoio é a parte tributária do assunto — leia o cartão antes"}],
 "sem_assunto": false, "motivo": null}
```

Quando o contato não tem tag, nenhum candidato passa do piso, ou os candidatos são todos `fora_do_dominio`, `sem_assunto` é `true` e `motivo` diz qual dos três. É esse campo que implementa "zero dado, avisa, não trava". Um modelo de 4B não decide ordenação nem exclusão; essas decisões são aritméticas e auditáveis linha a linha em `assunto_contato`.

Duas funções auxiliares, mesmo padrão: **rotular** (título de 6 a 10 palavras para um assunto novo) e **cartao** (três linhas do que aconteceu, para os assuntos que entraram em algum menu).

**extrair_de_texto** — comum a todas as etapas, porque a Etapa 1 já o usa nas notas importadas da agenda e no cadastro por texto livre. Recebe texto livre sobre um contato e devolve campos do guia, tags com trecho de lastro e fatos datados. Passa pelo filtro determinístico antes de gravar.

```json
{"campos": {"cidade": "Santos", "setor": "logística", "linguas": ["inglês"]},
 "tags_sugeridas": [{"tag": "cabotagem", "peso": 3, "trecho": "publicou sobre o novo terminal de cabotagem"}],
 "fatos_datados": [{"data": "2026-09-12", "tipo": "publicacao", "conteudo": "comentou o terminal de cabotagem em Santos", "fonte": "LinkedIn"}]}
```

Contratos de entrada de mídia e conversa (`extrair_de_imagem`, `resumir_conversa`) entram na Etapa 2, documentados no brief que os implementa.

## 5. Regra do conector

Um assunto serve quando liga o usuário à pessoa-alvo. Não basta interessar ao contato: se o usuário não tem base para sustentar a conversa, o assunto produz o oposto do que se quer. Três faixas, em ordem de preferência:

1. **Conector.** Relevante para os dois lados: casa com temas do contato e com temas do usuário **de nível domínio ou interesse** (cosseno ≥ 0,55 ao centróide do assunto). Vai ao topo do menu.
2. **Viável com esforço.** Relevante para o contato e, do lado do usuário, apoiado só em tema de curiosidade (cosseno ≥ 0,55) ou em conversabilidade ≥ 0,8. Entra no menu abaixo dos conectores, rotulado como tal, com a preparação anexa (cartão e, a partir da Etapa 2, o resumo completo).
3. **Fora do domínio.** Relevante para o contato e sem nenhum ponto de apoio do usuário. **Não entra no menu.** Fica registrado com o motivo, para auditoria e calibragem.

O piso entre a faixa 2 e a faixa 3 é o domínio mínimo potencial do usuário: passa se tiver adjacência ≥ 0,55 a algum tema dele **ou** conversabilidade ≥ 0,8. Basta uma das duas; nenhuma das duas, descarte. Limiares iniciais, calibrados na semana 1 (ver `limiares.yaml` e ADR).

Fórmula: score = 50 × aderência ao contato + 30 × aderência ao usuário (ponderada pelo peso de nível 1,0/0,7/0,4) + 20 × conversabilidade. **A pontuação e o piso são determinísticos; o modelo só escreve o `por_que`.**

## 6. Agrupamento de assuntos

1. Embedding de cada item novo com `bge-m3`.
2. Comparação com os centróides dos assuntos abertos dos últimos 7 dias.
3. Cosseno ≥ limiar inicial 0,82, calibrado (ver `limiares.yaml` e ADR) → entra no assunto e recalcula o centróide. Caso contrário, abre assunto novo.
4. Sem item novo por 7 dias → `status = encerrado`.
5. Item novo em assunto encerrado → reabre, marcado como "volta ao noticiário".
6. Mais de 12 itens sem coesão suficiente → divide em dois assuntos.

Ligação simples com limiar fixo, não k-means: o número de assuntos do dia é desconhecido e variável.

## 7. Qualificação

Substitui a antiga pontuação de cinco critérios. Os candidatos são os assuntos mais próximos da **união dos temas de todos os perfis ativos** — o usuário e cada contato ativo, não só o usuário: sem isso, um assunto que interessa a um contato mas não ao usuário nunca seria qualificado. Teto de 40 assuntos por dia, um por chamada ao contrato `qualificar`. Corte: `substancial` ≥ 0,6 e `conversavel` ≥ 0,6.

**Fonte só conta como independente** se o domínio for outro **e** o texto divergir em mais de 30%. Sem isso, um release distribuído a quinze portais vira "assunto denso".

## 8. Camada de LLM

Cliente único (`nucleo/llm.py`), injetado por `config/container.py`. Nenhum módulo chama o Ollama direto.

Em toda chamada, obrigatoriamente: modelo resolvido pelo `llm_routing.yaml`, `num_ctx` explícito, `format: json` nas tarefas estruturadas, `think: false` (o perfil pode omitir a chave do payload com `enviar_think: false`, para modelos sem modo de raciocínio), um item por chamada, e um exemplo resolvido dentro do prompt.

Falha de JSON inválido: uma nova tentativa com temperatura menor; segunda falha, o item vai para a fila de revisão com o erro registrado. Nunca se tenta consertar JSON com expressão regular.

**Perfil ativo.** `config/llm_routing.yaml` tem um perfil por máquina; `perfil_llm` em `config/local.yaml` escolhe qual (ausente = `air16`, o `perfil_ativo` do arquivo). `memoria_minima_gb` do perfil é conferida por `verificar-ambiente`.

| Perfil | Máquina | Papel | Modelo de geração e julgamento | Visão (`descrever_imagem`) | `memoria_minima_gb` |
|---|---|---|---|---|---|
| `air16` | MacBook Air M3, 16 GB | produção | `qwen3:4b` (único); `qwen3:8b` só em `prerotular_calibracao` (`agente_nw calibrar-agrupamento`) | `gemma3:4b` | 16 |
| `pro48` | MacBook Pro, 48 GB | desenvolvimento | `qwen2.5:14b`, com `enviar_think: false` | `gemma3:12b` | 24 |

Tarefas de LLM (as mesmas nos dois perfis): `qualificar`, `rotular`, `cartao`, `cruzar_por_que`, `extrair_de_texto`, `extrair_captura_rede_social`, `extrair_pedido` (pedido em texto livre, brief 036), `desempatar_perfil` (pessoa nas listas do usuário, brief 037), `redigir_ganchos` (ganchos e mensagens prontas, brief 038), `extrair_termos_contato` (assuntos que o contato publica, viram buscas de notícia), `descrever_imagem` (descrição das imagens publicadas pelo contato; a imagem nunca é gravada), `prerotular_calibracao`. `num_ctx` e temperatura de cada uma estão no YAML (fonte da verdade). Embeddings: `bge-m3` nos dois perfis, 1024 dimensões, multilíngue; índice vetorial em `sqlite-vec`, no mesmo arquivo do banco.

**Geração por API, opcional (briefs 074/075/076).** `nucleo/llm.py` tem uma base comum,
`_ClienteLLMBase`, com a orquestração que não depende de provedor (nova tentativa por temperatura,
backoff de transporte, validação do JSON contra o esquema, log da chamada, `fila_revisao`); cada
provedor implementa só `_chamar`. Além do `ClienteOllama`, existem `ClienteAnthropic`, `ClienteGemini`
e `ClienteOpenAI`, cada um forçando o formato de saída pela via nativa do seu provedor (tool
obrigatória, `response_schema`, `response_format: json_schema`) e usando `num_predict` da tarefa como
teto de saída — `num_ctx` e `think` são do Ollama e não vão para as APIs. O bloco opcional `ia_api` de
`config/local.yaml` registra chave e modelo de cada provedor; `selecionar_cliente_llm`
(`config/container.py`) é o **único** lugar que escolhe qual atende: `provedor: auto` pega a primeira
cadastrada na ordem Anthropic, Gemini, OpenAI, e um nome explícito (`anthropic`/`gemini`/`openai`/
`ollama`) manda — sem o sub-bloco correspondente preenchido, `ValueError` na inicialização. Sem nenhuma
chave, Ollama, como sempre foi. Invariante que não muda com provedor nenhum: **embeddings são sempre do
Ollama local** — a Anthropic não tem endpoint de embedding e trocar de modelo trataria como ausente
todo centróide já gravado (brief 066), então o cliente de API recebe um `ClienteOllama` por composição e
só repassa `embeddar`/`modelo_embedding`. O Ollama, portanto, continua precisando estar de pé. A
proveniência registrada em `chamadas_llm.jsonl` leva o modelo do provedor que atendeu, não o do
`llm_routing.yaml`.

**Servidor Ollama.** Sobe pelo próprio usuário, fora do aplicativo do Ollama (nunca o Ollama.app, nunca `brew services`), acessado pela `ollama_url` de `config/local.yaml`. No Air: `OLLAMA_MAX_LOADED_MODELS=2 OLLAMA_KEEP_ALIVE=30m ollama serve`. No Pro não há servidor próprio: a `ollama_url` aponta para a instância compartilhada `http://127.0.0.1:11435`, mantida pelo `cervello`, que este projeto nunca para nem reinicia. Os LaunchAgents que subiam o servidor foram removidos no brief 016.

**Porteiro, o admin do Ollama compartilhado (brief 077).** Vários projetos desta máquina usam os
mesmos dois servidores Ollama e a memória comporta no máximo dois modelos grandes ao mesmo tempo;
quem informa se um modelo cabe é o `porteiro` (`~/github/porteiro_local`, documentado no
`INTEGRACAO.md` dele). Antes de carregar um modelo no Ollama local — geração em `_chamar` ou
embeddings em `embeddar` —, o `ClienteOllama` consulta `porteiro cabe <modelo> --porta <porta da
ollama_url> --json` por subprocesso, uma vez por modelo por instância do cliente (nunca dentro de um
laço, item por item): cada comando de lote da CLI cria o seu cliente via `container.llm()`, então uma
consulta por modelo equivale à "uma vez no início do lote" que o `porteiro` pede. O modo vem de quem
constrói o cliente, por `selecionar_cliente_llm`: `lote` (padrão, toda a CLI) espera 60 s e pergunta
de novo enquanto a resposta for "não cabe", até 16 consultas (os 15 min do documento), e então roda
assim mesmo; `interativo` (as três construções do console, com uma pessoa esperando) consulta uma vez
e nunca espera. O `porteiro` nunca impede uma chamada, nunca troca o modelo ou a porta e nunca sobe
nem para o Ollama; sua ausência, um JSON ilegível, um timeout de 30 s ou um erro dele são tratados
como se ele não existisse. Toda resposta diferente de "cabe" vira uma linha `{"porteiro": true, ...}`
em `dados/logs/chamadas_llm.jsonl`, com o código, a razão e o aviso — em uso normal, nenhuma linha
nova aparece. Com um provedor de API cadastrado a geração não consulta nada (não toca o Ollama), mas
os embeddings, que são sempre locais, continuam consultando pela composição do brief 075.

## 9. Verdade e tema (brief 046)

O programa **não descarta conteúdo por tema** (política, saúde, religião…): quem decide que tema cabe numa mensagem é o usuário. O filtro de categorias sensíveis (`nucleo/sensivel.py`, `config/termos_sensiveis.yaml`, `queries/descarte_sensivel.py`) foi removido no brief 046, junto com as proibições de tema dos prompts; a tabela `descarte_sensivel` continua no banco, vazia, sem migração destrutiva. As garantias passam a ser de verdade, e ficam nos prompts (`nucleo/prompts/`):

- Nunca atribuir ao contato opinião, posição, adesão, crença ou característica que ele não disse (`cruzar_por_que.py`, regra de verdade; `redigir_ganchos.py`, regra de redação).
- Fato `[antigo]` (mais de `redacao.meses_fato_antigo`, 12 meses, ou lembrança "Há N anos") e fato `[de imagem]` não são tratados como atuais; `redigir_ganchos` recebe os fatos já marcados.
- O motor só entrega assunto com relação com o objetivo do pedido: a aderência à consulta, `conector.consulta.minima` (0,45 em `config/limiares.yaml`), é piso necessário; abaixo dele o assunto é `fora_do_dominio` ("pouca relação com o pedido"). Contato, tags e temas do usuário só enriquecem.

## 10. Console web

Flask (`agente_nw/console/app.py`), `127.0.0.1:8765`, sem framework de frontend, sem build; o único JavaScript é o do botão "Copiar". **A tela única (`/`) é a interface principal** (brief 039): o usuário escreve a frase, confirma a pessoa quando perguntado, recebe a mensagem base e os ganchos, marca "usei" ou "não serve", comenta e corrige em texto livre. O pedido roda em segundo plano, uma tarefa por vez (`nucleo/fluxo.py`), e a página `/pedido/<id>` se atualiza sozinha. As telas antigas (contatos, menu, temas, eu) ficam em "bastidores", no rodapé.

Rotas de `@app.route` (conferidas em `console/app.py`):

| Rota | Função |
|---|---|
| `GET /` · `POST /pedir` | tela única; grava o pedido e responde na hora |
| `GET /pedido/<id>` · `GET /pedido/<id>/lista` | andamento e resultado do pedido; lista de rede social |
| `POST /pedido/<id>/pessoa` · `/corrigir` · `/tentar-de-novo` | confirma a pessoa; correção em texto (pedido filho); reexecuta |
| `POST /pedido/<id>/gancho/base/<acao>` · `/gancho/<assunto_id>/<acao>` | "usei" / "não serve" na base ou num gancho |
| `POST /pedido/<id>/gancho/base/comentar` · `/gancho/<assunto_id>/comentar` · `/nota` | comentário por mensagem; nota sobre a pessoa ou o pedido (brief 050) |
| `GET /pessoa/<id>` · `POST /pessoa/<id>/contar` · `/trocar-perfil` | o que a IA sabe; contar algo; trocar perfil de rede |
| `GET /contatos` · `POST /contatos/novo` · `GET /contatos/<id>` | bastidores: lista, cadastro e ficha |
| `POST /contatos/<id>/confirmar-tags` · `/ativar` · `/editar` · `/apagar` · `/unir` · `/adicionar-texto` · `/gerar-menu` | bastidores: ações sobre o contato |
| `GET·POST /contatos/<id>/preparar` | bastidores: preparação |
| `POST /contatos/<id>/redes-sociais/adicionar` · `/<rede_social_id>/remover` · `/buscar` | redes sociais do contato |
| `GET /menu` · `GET /menu/<perfil_id>` · `POST /menu/<perfil_id>/usei/<ac_id>` · `/nao-serve/<ac_id>` | bastidores: menu antigo e marcação |
| `GET /eu` · `POST /eu/configurar` · `/eu/redes-sociais/adicionar` · `/eu/redes-sociais/<id>/remover` | bastidores: perfil do usuário |
| `GET /temas` · `POST /temas/novo` · `/temas/<id>/atualizar` · `/nivel` · `/confirmar` · `/remover-do-usuario` | bastidores: temas |

Só escuta em `127.0.0.1`. Nunca em `0.0.0.0`. A ponte da extensão é outro servidor local, `127.0.0.1:8766` (`ponte/servidor.py`), com token por execução.

## 11. Agendamento

Não existe agendamento (brief 016). Toda execução é disparada por Sidarta pelo console ou pela CLI. O arquivo sentinela `dados/PARE` e o comando `ciclo` não existem mais no código (`grep` em `agente_nw/`, `config/` e `scripts/`, 25/10/2026).

Tarefas não assistidas: nenhuma. **Nunca rodam sozinhos:** git, leitura de rede social, alteração de ficha de contato, a suíte de testes padrão.

## 12. Banco

SQLite em modo WAL, `busy_timeout` 5 s, `foreign_keys` ligado, `sqlite-vec` carregado na abertura da conexão. Backup diário pela API de backup do SQLite, em `dados/backups/`, retenção de 7 dias, fora da pasta sincronizada com o Drive. `agente_nw copiar-banco` gera uma cópia para desenvolvimento, para que o banco real só seja tocado por operação autorizada por Sidarta.
