# Brief E1-006 — Coleta RSS e Google News

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Depende de:** brief 003 (concluído e certificado) e dos temas do usuário já importados (brief 001/002 — hoje ainda os dois temas de exemplo; a coleta funciona com eles, a qualidade do resultado melhora quando `temas.yaml` for o de verdade)
**Antecipado** na ordem de execução, à frente de 004 e 005, para começar a acumular material real antes da calibração do agrupamento (brief 007).

---

## 1. Objetivo em uma frase

Coletar RSS de fontes fixas e de consultas geradas a partir dos temas do usuário, com deduplicação, filtro de ruído estrutural e retomada após interrupção — sem nenhum modelo envolvido.

---

## 2. Contexto e o que já existe

`fonte` e `item` já estão na migração 001, com os modelos Pydantic `Fonte` e `Item` já escritos (`agente_nw/nucleo/modelos/fonte.py`, `item.py`) — este brief não altera nenhum dos dois. `fontes.exemplo.yaml` já existe, com três feeds reais (G1, InfoMoney, Agência Brasil); `fontes.yaml` ainda não existe — é dívida registrada desde o brief 001. `config/limiares.yaml` já tem `agrupamento.divergencia_minima_fonte_independente` (0,30) e `agrupamento.janela_dias` (7), mas nada específico de coleta — este brief acrescenta um bloco novo, não mexe nos que já existem. `queries/sistema.py` já tem `progresso_obter`/`progresso_gravar`, genéricos por etapa — este brief os reusa para a retomada, sem criar mecanismo próprio. `pyproject.toml` já traz `feedparser`, `trafilatura` e `httpx` como dependência; nada novo a instalar. `container.http()` já existe e é o único cliente HTTP do projeto — este brief não cria um segundo.

A tabela `fonte` não guarda histórico de execução (quantos itens novos em cada coleta), e o critério "feed vazio dois dias seguidos gera alerta" precisa desse histórico. Como nenhuma tabela existente serve para isso sem forçar um uso estranho (a tabela `progresso` é uma linha por etapa do ciclo, não por fonte), este brief inclui uma migração nova — é exatamente o que a governança pede: tabela nasce na migração do brief que a usa.

`fonte.tipo` não tem `CHECK` na migração (o comentário `-- veiculo | blog | oficial | agregador` é só documentação); `fontes.exemplo.yaml` já usa `especializada`, fora dessa lista. Não é defeito deste brief corrigir — o campo é texto livre por desenho, o comentário é só sugestão.

---

## 3. Escopo

1. **Migração `scripts/migracoes/002_coleta_historico.sql`**: uma tabela, `fonte_execucao (fonte_id, data, n_itens_novos, PRIMARY KEY (fonte_id, data))`. Só isso — nenhuma outra tabela da Etapa 2 em diante entra aqui.
2. **`config/limiares.yaml`**, bloco novo `coleta`: `teaser_minimo_caracteres: 400`, `dias_max_primeira_aparicao: 7`, `retencao_texto_dias: 90`, `intervalo_google_news_segundos: 2`, `dias_alerta_feed_vazio: 2`. `agente_nw/nucleo/modelos/configuracao.py` ganha `ColetaLimiares` e o campo correspondente em `Limiares`.
3. **`agente_nw/nucleo/modelos/configuracao.py`**, além do item 2: `FeedFonte` e `FontesArquivo`, no mesmo padrão de `TemaUsuario`/`TemasArquivo`, para validar `fontes.yaml`.
4. **`agente_nw/nucleo/database/queries/fontes.py`**: `obter_ou_criar`, `listar_ativas`, `registrar_execucao(conexao, fonte_id, data, n_itens_novos)`, `dois_dias_vazios(conexao, fonte_id, data_referencia) -> bool`.
5. **`agente_nw/nucleo/database/queries/itens.py`**: `existe(conexao, url_canonica, hash_titulo) -> bool`, `inserir(conexao, item: Item) -> int`.
6. **`agente_nw/coleta/rss/canonicalizar.py`**: `url_canonica(cliente_http, url) -> str` (remove `utm_source`, `utm_medium`, `utm_campaign`, `utm_term`, `utm_content`, `fbclid`, `gclid`, `igshid`, `mc_cid`, `mc_eid` e a âncora; segue **um** redirecionamento, não mais) e `hash_titulo(titulo: str) -> str` (normaliza acentuação, caixa e pontuação antes do hash, para que "Reforma tributária: o que muda?" e "reforma tributária - o que muda" caiam no mesmo hash).
7. **`agente_nw/coleta/rss/ruido.py`**: `e_ruido(titulo, corpo, publicado_em, coletado_em, limiares) -> tuple[bool, str | None]`, com as quatro regras da proposta: corpo abaixo do teaser mínimo; título de lista (padrão: começa com número seguido de "melhores", "motivos", "dicas", "maneiras", "coisas", "razões", "erros", ou variações no plural); marcado como patrocinado ("publicidade", "conteúdo patrocinado", "publieditorial", "patrocinado por" no título ou nas primeiras linhas do corpo); mais de `dias_max_primeira_aparicao` dias entre `publicado_em` e `coletado_em` na primeira vez que o item aparece.
8. **`agente_nw/coleta/rss/google_news.py`**: `gerar_consultas(temas: list[Tema]) -> list[FeedFonte]`, replicando a fórmula da proposta (`https://news.google.com/rss/search?q=...&hl=pt-BR&gl=BR&ceid=BR:pt-419`, com `urllib.parse.quote`, até 4 termos por tema — nome mais sinônimos). Só gera em memória a cada execução; não grava de volta em `fontes.yaml`.
9. **`agente_nw/coleta/rss/leitor.py`**: orquestrador — carrega `fontes.yaml`, gera as consultas do item 8 a partir dos temas do usuário no banco, junta as duas listas, processa fonte por fonte (busca o feed via `container.http()`, extrai entradas com `feedparser`, para cada entrada canonicaliza, calcula hash, verifica duplicata, verifica ruído, se passar busca a página via `container.http()` e extrai o corpo com `trafilatura.extract`, grava `fonte` e `item`), grava progresso por fonte processada (retomada), grava execução por fonte (histórico para o alerta de feed vazio), respeita o arquivo sentinela e o intervalo entre consultas ao Google News.
10. **`fontes.yaml` de partida** (não `fontes.exemplo.yaml`, que já existe e continua como está): pelo menos 20 feeds RSS brasileiros reais e testados um a um pelo executor antes de entrar no arquivo — cobrindo notícia geral, economia, tecnologia e direito (que são os dois mundos de Sidarta: advocacia e desenvolvimento de software), para que o critério de aceite de 20 feeds seja verificável neste próprio brief, não fique pendente de Sidarta escrever a lista do zero. É sugestão pronta para editar, não obrigação — Sidarta troca ou remove o que quiser depois.
11. **`agente_nw/cli.py`**: `coletar` sai de `COMANDOS_RESERVADOS` e ganha implementação real, que roda o leitor do item 9 e imprime um resumo (fontes processadas, itens novos, duplicados, descartados por ruído, alertas de feed vazio, tempo total).

---

## 4. Fora de escopo, com justificativa

- **Purga de `item.texto` depois de 90 dias.** A proposta define a regra (`retencao_texto_dias: 90`, já declarada no item 2), mas nenhum brief do plano tem hoje a tarefa de rodar a purga — nem este, nem o 012 (ciclo), que a proposta não menciona explicitamente. Fica registrado como pendência em aberto na seção 8 deste brief; implementar aqui seria inventar escopo que a proposta não pediu deste brief especificamente.
- **Deduplicação por similaridade de conteúdo (`cosseno_republicacao`).** Esse limiar já existe em `limiares.yaml`, mas depende de embedding, que só entra no agrupamento (brief 007). Este brief deduplica só por URL canônica e por hash de título normalizado, como o plano descreve.
- **Persistir as consultas do Google News em `fontes.yaml`.** A proposta descreve isso na seção 7.3 como script da Etapa 3 (`integracoes/fontes_google.py`), que escreve de volta no arquivo. Na Etapa 1, gerar em memória a cada coleta é melhor: se persistisse, as consultas ficariam desatualizadas toda vez que os temas mudassem, e teria que existir uma rotina de limpeza para as antigas. O script da Etapa 3 é outra decisão, para outro momento.
- **`agente_nw ciclo` orquestrado.** Este brief entrega `agente_nw coletar`, rodado à mão uma vez por dia, exatamente como o plano descreve para a semana 1. A orquestração automática de coleta → embeddings → ... é o brief 012.

---

## 5. Decisões tomadas e deixadas abertas

**Tomadas:**

- **Histórico de execução por fonte é tabela nova (migração 002), não um uso forçado de `progresso`.** `progresso` é uma linha por etapa do ciclo inteiro; usá-la por fonte exigiria chaves sintéticas tipo `"coleta_fonte_14"`, o que funciona mas não é o que a tabela foi desenhada para guardar. Uma tabela pequena e nomeada corretamente é mais barata de entender depois.
- **Um único HTTP para tudo.** Feed buscado via `container.http()`, página buscada via `container.http()` para o `trafilatura` extrair — nunca deixando o `feedparser` ou o `trafilatura` fazerem sua própria requisição por trás, para manter um só `User-Agent`, um só timeout e um só ponto de falha a tratar.
- **Canonicalização segue exatamente um redirecionamento.** Mais de um é sinal de encurtador de URL em cadeia ou de comportamento incomum; nesse caso a URL original é mantida, não perseguida até o fim.
- **Ruído descartado não é gravado em lugar nenhum — só contado no resumo do comando.** Diferente de `descarte_sensivel` (que registra categoria e origem para auditoria de dado sensível), aqui não há nada sensível a auditar; guardar todo item descartado por ser "lista de 10 dicas" seria banco crescendo sem função.
- **`fontes.yaml` de partida é gerado com feeds reais, testados um a um, não uma lista genérica copiada de algum lugar.** Cada URL do arquivo final respondeu de verdade durante a execução do brief. Se algum feed que parecia bom não responder, é substituído por outro até fechar pelo menos 20.
- **`fonte.tipo` continua texto livre.** Não é este brief que decide fechar essa lista (a proposta só fecha listas de cargo/setor, para a Etapa 4; fonte é uso interno, não sai em pacote).

**Deixadas abertas:**

- Rotina de purga de `item.texto` após 90 dias — nenhum brief do plano a reivindica hoje; fica pendência em `docs/PLAN.md` até algum brief (provavelmente perto do 012) assumi-la.
- `fontes.yaml` de partida é editável à vontade por Sidarta; nenhuma revisão futura deste brief depende de quais feeds ele mantiver.

---

## 6. Passos de execução

1. `scripts/migracoes/002_coleta_historico.sql`: criar `fonte_execucao` conforme a seção 3, item 1. Rodar `agente_nw migrar` e confirmar `schema_version = 2`.
2. `config/limiares.yaml` e `configuracao.py`: acrescentar o bloco `coleta` e `ColetaLimiares` (seção 3, item 2). Não tocar nos blocos existentes.
3. `configuracao.py`: acrescentar `FeedFonte` (`nome`, `url`, `tipo`, `confiabilidade`) e `FontesArquivo` (`feeds: list[FeedFonte]`), com a mesma validação de nome duplicado que `TemasArquivo` já tem para temas.
4. `queries/fontes.py` e `queries/itens.py`, conforme a seção 3, itens 4 e 5.
5. `coleta/rss/canonicalizar.py`, com testes cobrindo: remoção de cada parâmetro de rastreio listado, remoção de âncora, exatamente um redirecionamento seguido (não dois), hash igual para títulos que só diferem em acentuação/caixa/pontuação e diferente para títulos realmente diferentes.
6. `coleta/rss/ruido.py`, com um teste por regra das quatro (mais um caso que não deveria ser marcado como ruído, para garantir que a função não descarta em excesso).
7. `coleta/rss/google_news.py`, com um teste que confere a codificação (espaço, aspas ao redor de cada termo) e o limite de 4 termos por tema.
8. `coleta/rss/leitor.py`, com o fluxo completo da seção 3, item 9. Testar a retomada (item 9 abaixo) com fontes falsas, sem rede.
9. `tests/test_coleta_retomada.py`, sem rede real: simula três fontes com respostas fabricadas (`monkeypatch` no cliente HTTP), interrompe depois da primeira (arquivo sentinela criado no meio da execução, ou progresso gravado manualmente para simular queda), roda de novo no mesmo dia e confirma que as duas fontes restantes são processadas e a primeira não é reprocessada.
10. Escrever `fontes.yaml`: buscar candidatos reais de RSS brasileiro em notícia geral, economia, tecnologia e direito; testar cada URL (feed responde, tem pelo menos uma entrada recente); manter os 20 primeiros que passarem, no formato de `fontes.exemplo.yaml`. Não sobrescrever `fontes.exemplo.yaml`.
11. `cli.py`: tirar `"coletar"` de `COMANDOS_RESERVADOS`, registrar o subcomando de verdade, implementar `coletar()` chamando o leitor e imprimindo o resumo.
12. `tests/test_coleta_fumaca.py` (rede real, `fontes.exemplo.yaml` como entrada — não `fontes.yaml`, para não depender do que Sidarta tiver editado): roda o leitor completo sobre os três feeds do exemplo mais as consultas geradas dos dois temas hoje no banco; confirma que roda sem erro, gera pelo menos um item, e que rodar duas vezes seguidas não duplica nada. Pular com motivo claro, não erro cru, se a rede não responder.
13. Rodar `agente_nw coletar` de verdade, contra `fontes.yaml` (os 20 feeds reais do passo 10) mais as consultas dos temas: medir o tempo total e conferir que fica abaixo de 8 minutos; interromper no meio (arquivo sentinela) e rodar de novo no mesmo dia, conferindo que retoma sem duplicar.
14. Deixar `dados/PARE` documentado como o arquivo sentinela do projeto — vazio, sua existência interrompe a etapa em andamento na próxima verificação. Nomeado de forma genérica de propósito: o brief 012 (ciclo completo) reaproveita o mesmo arquivo para o ciclo inteiro, não cria um novo.
15. Atualizar `docs/PLAN.md`: brief 006 concluído; a pendência de "`fontes.yaml` inexistente" passa a "`fontes.yaml` com 20 feeds de partida, editável"; nova pendência registrada (purga de `item.texto`); próximo é o brief 004 (filtro de categorias sensíveis e extrator de texto).

---

## 7. Critérios de aceite

1. Migração 002 aplicada; `fonte_execucao` existe; nenhuma tabela de etapa futura foi criada.
2. Canonicalização remove todos os parâmetros de rastreio listados e segue exatamente um redirecionamento; hash de título é igual para variações de acentuação/caixa/pontuação do mesmo título.
3. As quatro regras de ruído testadas isoladamente, mais um caso que não deveria ser marcado como ruído.
4. Duplicata por URL canônica e por hash de título são rejeitadas — mesmo item coletado duas vezes gera uma linha só em `item`.
5. Interromper a coleta no meio e reexecutar no mesmo dia continua da fonte seguinte, sem duplicar nem pular nenhuma (`tests/test_coleta_retomada.py`, sem rede).
6. `fontes.yaml` de partida com pelo menos 20 feeds reais, todos testados durante a execução do brief.
7. `agente_nw coletar`, rodado contra `fontes.yaml` (20 feeds) mais as consultas geradas dos temas do usuário, completa em menos de 8 minutos — medido de verdade, uma vez, no passo 13, não simulado.
8. Feed que devolve zero itens novos em duas execuções seguidas grava alerta (verificável rodando `agente_nw coletar` duas vezes com uma fonte que não tem novidade, ou com dado fabricado em `fonte_execucao`).
9. `scripts/verificar.sh` verde nos testes que não dependem de rede; o teste de fumaça do passo 12 e a medição do passo 13 rodados manualmente com resultado relatado.

---

## 8. Riscos e como reverter

| Risco | Controle |
|---|---|
| Feed real muda de formato ou sai do ar depois que este brief fechar a lista | cada feed foi testado na hora de entrar em `fontes.yaml`, mas nada garante que continue no ar; é para isso que existe o alerta de feed vazio |
| 8 minutos não é suficiente se a rede estiver lenta no dia da medição | o critério é medido uma vez, no passo 13; se estourar por instabilidade pontual, medir de novo antes de marcar o critério como reprovado — não é motivo para redesenhar o leitor |
| Filtro de ruído descarta notícia real por engano (falso positivo) | cada regra tem um teste isolado e um teste de "não deveria descartar"; nenhuma regra combina critérios de forma a ficar agressiva demais sozinha |
| `trafilatura` não extrai corpo de algum site com paywall ou JavaScript pesado | item entra com `texto = None`; não trava a coleta; fica com corpo vazio até (se um dia for o caso) outra fonte cobrir o mesmo assunto |
| Reverter | `scripts/migracoes/002_coleta_historico.sql` é a única mudança de esquema — não aplicar essa migração (ou reverter o banco de desenvolvimento para antes dela) desfaz a tabela nova; os módulos de `coleta/rss/` são todos arquivos novos, apagáveis sem afetar o resto; a edição em `cli.py` volta a registrar `"coletar"` em `COMANDOS_RESERVADOS` |

---

## 9. Relatório final obrigatório

Preencher o bloco da seção 8 de `AGENTS.md` — com o caminho do script de verificação para colar no terminal, não com testes já rodados pelo executor. Sem esse bloco preenchido, o brief não está concluído.
