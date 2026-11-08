# ARQUITETURA.md — agente_nw

> Arquitetura hexagonal. Dependências resolvidas em `config/container.py`. Nenhum módulo instancia cliente de LLM, conexão de banco ou cliente HTTP diretamente.

---

## 1. Fluxo

Ciclo diário (05h00, ou no primeiro login com recuperação de execução perdida), saída por contato:

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
├── AGENTS.md
├── pyproject.toml
├── .gitignore
├── temas.exemplo.yaml
├── fontes.exemplo.yaml
├── config/
│   ├── container.py          # fábrica de dependências: llm(), banco(), http()
│   ├── llm_routing.yaml      # tarefa → modelo, num_ctx, temperatura, format
│   ├── limiares.yaml         # valores calibrados; nunca constante no código
│   └── local.exemplo.yaml    # caminhos e URLs identificadoras (o local.yaml fica fora do git)
├── agente_nw/                # pacote Python
│   ├── cli.py                # comandos: verificar-ambiente, importar-temas, importar-agenda,
│   │                         #   ficha, ativar, confirmar-tags, coletar, ciclo, copiar-banco, ...
│   ├── nucleo/
│   │   ├── modelos/          # contratos Pydantic v2, frozen=True, um módulo por entidade
│   │   ├── prompts/          # um arquivo por contrato, com esquema JSON e um exemplo resolvido
│   │   ├── database/
│   │   │   ├── conexao.py    # abre o banco: WAL, foreign_keys, busy_timeout, sqlite-vec
│   │   │   ├── migracoes.py  # aplica scripts/migracoes/*.sql em ordem
│   │   │   └── queries/      # todo SQL isolado aqui
│   │   ├── llm.py            # cliente único do Ollama
│   │   ├── vetores.py        # embeddings, cosseno, centróide
│   │   ├── sensivel.py       # filtro determinístico de categorias sensíveis
│   │   ├── relevancia/       # qualificação, pontuação, piso, tipo (regra do conector)
│   │   ├── agrupamento/      # centróide, janela, reabertura, divisão
│   │   └── saidas/           # cartão, menu, exportação Markdown
│   ├── coleta/
│   │   ├── rss/              # feedparser, trafilatura, canonicalização, google news
│   │   └── capturas/         # (Etapa 2) recepção do que vem da extensão
│   ├── perfil/                # importação da agenda, extração de texto, lacunas, centróide de perfil
│   ├── console/                # Flask + templates + estáticos
│   └── integracoes/          # (Etapa 3)
├── extensao/                 # (Etapa 2) extensão do Chrome
├── scripts/
│   ├── migracoes/             # 001_inicial.sql, 002_..., aplicados em ordem
│   ├── instalar_macos.sh
│   ├── verificar.sh          # ruff + mypy --strict + pytest
│   └── launchd/               # plists: ollama e ciclo
├── docs/                      # fora do git, exceto o que a governança listar
├── dados/                     # agente.db, backups/ — fora do git
├── saidas/                    # menu_AAAA-MM-DD.md — fora do git
├── logs/                      # fora do git
└── tests/
```

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

Cliente único, injetado. Nenhum módulo chama o Ollama direto.

Em toda chamada, obrigatoriamente: modelo resolvido pelo `llm_routing.yaml`, `num_ctx` explícito, `format: json` nas tarefas estruturadas, `think: false` fixo como parâmetro do cliente, um item por chamada, e um exemplo resolvido dentro do prompt.

Falha de JSON inválido: uma nova tentativa com temperatura menor; segunda falha, o item vai para a fila de revisão com o erro registrado. Nunca se tenta consertar JSON com expressão regular.

O servidor Ollama sobe pelo LaunchAgent do projeto (`OLLAMA_MAX_LOADED_MODELS=2`, `OLLAMA_KEEP_ALIVE=30m`) — nunca pelo aplicativo do Ollama, que ocupa a porta sem as variáveis.

## 9. Filtro de categorias sensíveis

Categorias sensíveis (saúde, religião, política, sindicato, vida sexual, origem racial, menores) nunca chegam ao banco. Duas camadas: o prompt de todo contrato que produz tag ou fato proíbe extraí-las; depois, `nucleo/sensivel.py` aplica uma lista de termos por categoria e descarta o que passou, registrando em `descarte_sensivel` (sem guardar o trecho). O mesmo filtro roda sobre notas importadas (Etapa 3) e sobre tudo que volta de assistentes pagos (Etapa 4).

## 10. Console web

Flask, `127.0.0.1:8765`, sem framework de frontend, sem build. HTML servido direto.

| Rota | Função |
|---|---|
| `GET /contatos` · `GET /contato/<id>` | lista e ficha completa |
| `POST /contato/<id>/ativar` | marca o contato como ativo |
| `POST /contato/<id>/tags/confirmar` | confirma tags sugeridas |
| `POST /contato/<id>/texto` | recebe texto colado para extração |
| `GET /menu/<perfil_id>` | menu do contato, conectores e viáveis com esforço |
| `POST /marcar` | grava "usei" / "não serve" (com motivo) |
| `GET /temas` · `POST /temas` | edição de temas, sinônimos e nível, sem tocar em arquivo |
| `POST /processar` | processa a fila de extração agora |

Só escuta em `127.0.0.1`. Nunca em `0.0.0.0`.

## 11. Agendamento

Dois LaunchAgents em `scripts/launchd/`:

- `br.agente_nw.ollama.plist` — sobe `ollama serve` com `OLLAMA_MAX_LOADED_MODELS=2` e `OLLAMA_KEEP_ALIVE=30m`, `RunAtLoad`, `KeepAlive`.
- `br.agente_nw.ciclo.plist` — `StartCalendarInterval` às 05h00, com recuperação de execução perdida (o Mac pode estar dormindo). Segundo gatilho no login, com atraso de 5 minutos; o script consulta no banco se já rodou hoje e sai sem fazer nada se já rodou.

Cada etapa grava progresso no SQLite e é retomável. Nunca laço infinito em processo. Interruptor de parada por arquivo sentinela: `dados/PARE` (vazio; sua existência interrompe a etapa em andamento na próxima verificação). Introduzido no brief 006 para a coleta RSS; o brief 012 reaproveita o mesmo arquivo para o ciclo completo — nunca cria um segundo sentinela.

Tarefas não assistidas: coleta RSS, extração, embeddings, agrupamento, qualificação, cruzamento, cartão. **Nunca rodam sozinhos:** git, coleta em rede social, alteração de ficha de contato.

## 12. Banco

SQLite em modo WAL, `busy_timeout` 5 s, `foreign_keys` ligado, `sqlite-vec` carregado na abertura da conexão. Backup diário pela API de backup do SQLite, em `dados/backups/`, retenção de 7 dias, fora da pasta sincronizada com o Drive. `agente_nw copiar-banco` gera uma cópia para desenvolvimento, para que o banco de medição de aceite só seja escrito pelo ciclo.
