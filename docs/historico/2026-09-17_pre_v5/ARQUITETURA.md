# ARQUITETURA.md — agente_nw

Arquitetura hexagonal. Dependências resolvidas em `config/container.py`. Nenhum módulo instancia cliente de LLM, conexão de banco ou cliente HTTP diretamente.

---

## 1. Fluxo

```
TRILHA A — coleta contínua (automática, diária)

  feeds RSS ──► coleta ──► normalização ──► embedding ──► agrupamento
                                                              │
                                                              ▼
                                                    pontuação (5 critérios)
                                                              │
                                                     corte 65 · teto 8
                                                              ▼
                                                     cartão do assunto
                                                              ▼
                                                     console: Hoje


TRILHA B — análise de contato (sob demanda, disparada pelo usuário)

  console: ficha ──► "Coletar agora" ──► extensão Chrome
                                              │
                          abre aba, rola, captura texto visível, fecha
                                              │
                                              ▼
                                   POST localhost:8765/capturar
                                              │
                          extração de blocos (qwen2.5:7b, JSON)
                                              │
                          agregação sem modelo (embeddings, temas, cadência)
                                              │
                          síntese do perfil (qwen2.5:14b, num_ctx 16384)
                                              │
                          verificação de lastro (qwen2.5:14b)
                                              ▼
                      perfil ──┬──► texto para o usuário ler
                               └──► termos + feeds + centróide ──► TRILHA A
```

A trilha B configura a trilha A. É esse o acoplamento, e é o único.

## 2. Estrutura do repositório

```
agente_nw/
├── AGENTS.md
├── docs/
│   ├── PLANO.md
│   ├── ARQUITETURA.md
│   ├── PLAN.md
│   ├── adr/
│   └── briefs/
├── nucleo/
│   ├── modelos/              # contratos Pydantic v2, frozen=True
│   ├── prompts/              # um arquivo por tipo de saída
│   ├── relevancia/           # cinco critérios, corte, teto
│   ├── agrupamento/          # centróide, janela, reabertura
│   ├── saidas/               # cartão, resumo, perfil
│   └── database/queries/     # todo SQL isolado aqui
├── coleta/
│   ├── rss/                  # feedparser, trafilatura, canonicalização
│   └── capturas/             # recepção e extração do que vem da extensão
├── perfil/                   # as quatro passagens da análise de contato
├── console/                  # Flask + templates + estáticos
├── extensao/                 # extensão do Chrome (manifest v3)
├── config/
│   ├── container.py
│   └── llm_routing.yaml
├── dados/                    # agente.db — fora do git
├── saidas/                   # fora do git
├── tests/
└── scripts/
```

## 3. Contratos (Pydantic v2, `frozen=True`)

```
Item          id, url_canonica, titulo, texto, fonte, dominio, publicado_em,
              coletado_em, hash_titulo, assunto_id | None

Assunto       id, titulo_gerado, primeiro_visto, ultimo_visto, n_itens,
              n_fontes_independentes, temperatura, nota, status, temas,
              centroide, resumo_cartao | None, resumo_completo | None

Contato       id, nome, apelido_uso, cidade, telefones[], emails[],
              empresa, cargo, area_atuacao, contas[], etiquetas[],
              criado_em, atualizado_em, ultima_coleta | None

Conta         contato_id, rede, url, handle, ativa, ultima_coleta | None

Captura       id, contato_id, conta_id, coletado_em, url_origem, texto_bruto,
              processada

Publicacao    id, contato_id, conta_id, captura_id, autor_detectado, data,
              tipo, texto, links[], embedding

Fato          id, contato_id, data_do_fato, tipo, conteudo, fonte, url,
              coletado_em            # tabela só de inserção, nunca editada

MudancaCampo  id, contato_id, campo, valor_anterior, valor_novo, detectado_em

Perfil        id, contato_id, gerado_em, modelo_usado, texto_para_humano,
              termos_monitoramento[], feeds_descobertos[], centroide,
              afirmacoes[]           # cada uma com publicacao_id de lastro

Marcacao      assunto_id, data, escolha, motivo | None
```

## 4. Esquema de dados — pontos que não são óbvios

**`Fato` é só-inserção.** Nunca editado, nunca apagado. É a memória do contato e o que permite a recoleta produzir diferença em vez de fotografia.

**Campo versionado.** Cargo, empresa e cidade não são atualizados por cima: grava-se `MudancaCampo` com anterior, novo e quando. Sem isso o sistema só enxerga o estado atual e não sabe que ele é novo — e "mudou de cargo" é o sinal mais forte que existe nessa base.

**Retenção.** `Captura.texto_bruto` e `Item.texto` vivem 90 dias; depois fica título, URL e os fatos extraídos. `Fato` é permanente. Reanalisar material guardado é grátis; recoletar custa uma visita visível ao perfil da pessoa.

**Perfil tem lastro.** Toda afirmação em `Perfil.afirmacoes` aponta para ao menos uma `Publicacao`. Afirmação sem lastro é cortada na verificação, antes de virar arquivo. Sem essa passagem o perfil enche de inferência plausível e errada.

**Não se grava inferência como fato.** "Publicou sobre cabotagem em 12/09 (LinkedIn)" é `Fato`. "Interessado em logística" é conclusão — o agente deriva na hora de usar, não persiste como dado.

## 5. Agrupamento de assuntos

1. Embedding de cada item novo com `bge-m3`.
2. Comparação com os centróides dos assuntos abertos dos últimos 7 dias.
3. Cosseno ≥ 0,82 → entra no assunto e recalcula o centróide. Caso contrário, abre assunto novo.
4. Sem item novo por 7 dias → `status = encerrado`.
5. Item novo em assunto encerrado → reabre, marcado como "volta ao noticiário".

Ligação simples com limiar fixo, não k-means: o número de assuntos do dia é desconhecido e variável. Abaixo de 0,78 há junção indevida; acima de 0,88, fatiamento.

## 6. Pontuação (cinco critérios, 0–100)

| Critério | Peso | Medida |
|---|---|---|
| Densidade | 25 | fontes independentes: 1 → 5 · 2–3 → 15 · 4+ → 25 |
| Durabilidade | 25 | ainda estará de pé em 7 dias? Julgamento do modelo |
| Conversabilidade | 20 | dá para falar sem ser especialista? Julgamento do modelo |
| Aderência aos temas | 20 | cosseno com as descrições, ponderado pelo peso do tema |
| Não-obviedade | 10 | fontes de massa versus especializadas |

Corte 65. Faixa 50–64 fica em espera e volta no balanço semanal se ganhar densidade. Teto de 8 por dia e 3 por tema.

**Fonte só conta como independente** se o domínio for outro **e** o texto divergir em mais de 30%. Sem isso, um release distribuído a quinze portais vira "assunto denso" e o critério de densidade passa a medir assessoria de imprensa.

**Publicação de rede social não entra nesta conta** — tem sempre uma fonte só e nunca passaria do corte. Trilha separada: sinal isolado (teto de 2 por dia) ou reforço de assunto já formado, aparecendo como "está sendo comentado".

## 7. Camada de LLM

Cliente único, injetado. Nenhum módulo chama o Ollama direto.

Em toda chamada, obrigatoriamente: modelo resolvido pelo `llm_routing.yaml`, `num_ctx` explícito, `format: json` nas tarefas estruturadas, um item por chamada, e um exemplo resolvido dentro do prompt (em modelo desta faixa, o exemplo rende mais que trocar de modelo).

Falha de JSON inválido: uma nova tentativa com temperatura menor; segunda falha, o item vai para a fila de revisão com o erro registrado. Nunca se tenta consertar JSON com expressão regular.

## 8. Console web

Flask, `localhost:8765`, sem framework de frontend, sem build. HTML servido direto.

| Rota | Função |
|---|---|
| `GET /` | Hoje — cartões do dia com os três botões |
| `GET /assunto/<id>` | resumo completo, itens, fontes |
| `POST /marcar` | grava a marcação e realimenta a calibragem na hora |
| `GET /contatos` · `GET /contato/<id>` | lista e ficha completa com histórico e perfil |
| `POST /contato/<id>/coletar` | enfileira a coleta e devolve a lista de URLs para a extensão |
| `POST /capturar` | recebe o texto capturado pela extensão |
| `GET /capturas` | fila, estado, erros, botão de processar agora |
| `GET /temas` · `POST /temas` | edição sem tocar em arquivo |
| `GET /semana` | balanço e calibragem |

Só escuta em `127.0.0.1`. Nunca em `0.0.0.0`.

## 9. Extensão do Chrome

Manifest v3. Permissões mínimas: `activeTab`, `scripting`, `tabs`, e `host_permissions` restrito a `http://localhost:8765/*`.

Fluxo: o console enfileira → a extensão pede a próxima URL → abre na aba de trabalho → espera o carregamento → rola três vezes → captura o texto visível → `POST /capturar` → intervalo de 4 a 9 segundos → próxima.

Uma aba só, em foco, reaproveitada. Parada imediata em tela de login, verificação ou interstício, devolvendo a aba ao usuário. Botão de parar sempre visível. Nenhum seletor de CSS específico de site — quem interpreta o texto capturado é o modelo.

## 10. Agendamento

`launchd` com `StartCalendarInterval` às 05h00 e recuperação de execução perdida (o Mac pode estar dormindo). Segundo gatilho no login, com atraso de 5 minutos; o script consulta no banco se já rodou hoje e sai sem fazer nada se já rodou.

Cada etapa grava progresso no SQLite e é retomável. Nunca laço infinito em processo. Interruptor de parada por arquivo sentinela.

Tarefas não assistidas: coleta RSS, extração, embeddings, agrupamento, pontuação, cartão. **Nunca rodam sozinhos:** git, coleta em rede social, alteração de ficha de contato.
