# Brief E1-007 — Agrupamento em assuntos e calibração do limiar

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Depende de:** brief 006 (coleta RSS), certificado — e de pelo menos dois dias de coleta real acumulada (`agente_nw coletar` rodado mais de uma vez, em dias diferentes) antes dos passos finais de execução.
**Abre a semana 2** do plano de execução.

---

## 1. Objetivo em uma frase

Transformar os itens coletados em assuntos — agrupando por proximidade de embedding numa janela de tempo, com abertura, fechamento, reabertura e divisão — e calibrar o limiar desse agrupamento contra rótulos reais do `qwen3:8b`, corrigidos por Sidarta só onde ele discordar do modelo.

---

## 2. Contexto e o que já existe

O esquema já tem tudo que este brief precisa: a tabela `assunto` (`titulo_gerado`, `primeiro_visto`, `ultimo_visto`, `n_itens`, `n_fontes_independentes`, `status`, `temas`, e os campos de qualificação que ficam `NULL` até o brief 008), `item.assunto_id` (nullable, é o que marca um item como pendente de agrupamento), e as tabelas vetoriais `vetor_item` e `vetor_assunto` (sqlite-vec, 1024 dimensões). `agente_nw/nucleo/agrupamento/` existe como pacote vazio (só `__init__.py`) — é o comentário da estrutura do repositório ("centróide, janela, reabertura, divisão") que este brief preenche.

`config/limiares.yaml` já tem os cinco valores de `agrupamento`, com `cosseno_mesmo_assunto: 0.82  # calibrar no brief 007` — é essa linha (e só essa) que a calibração reescreve. `config/llm_routing.yaml` já tem a tarefa `prerotular_calibracao` roteada para `qwen3:8b`, `think: false` — não é preciso mexer nesse arquivo.

**Importante, checado direto no repositório antes de escrever este brief:** `titulo_gerado` (o rótulo do assunto) **não é deste brief** — `docs/PLAN.md`, armadilha 24, e o próprio nome do brief 008 ("Qualificação, **rótulo**, cartão e exemplos de conversabilidade") deixam isso explícito. Este brief nunca chama a tarefa `rotular`; `assunto.titulo_gerado` fica `NULL` em todo assunto criado aqui, e `assunto.temas` fica `[]` (decidir a que tema do usuário um assunto pertence é decisão de relevância para o usuário — brief 008/`relevancia/`, não estrutura de agrupamento).

`COMANDOS_RESERVADOS` em `cli.py` já reserva `"calibrar-agrupamento": 7` — este brief o implementa de verdade, e acrescenta um segundo comando, `agrupar` (não reservado antes, mas necessário pelo mesmo motivo que `processar-fila` existiu no brief 004 antes do ciclo diário do brief 012: alguém precisa rodar o agrupamento à mão enquanto o ciclo não existe).

---

## 3. Escopo

1. **`agente_nw/nucleo/database/queries/itens.py`** (aditivo — as duas funções existentes, `existe` e `inserir`, não são tocadas): `listar_sem_assunto(conexao, limite)`, `gravar_embedding(conexao, item_id, embedding)` (mesmo padrão de `temas.gravar_embedding`: apaga e regrava em `vetor_item`), `obter_embedding(conexao, item_id) -> list[float] | None`, `vincular_assunto(conexao, item_id, assunto_id)`, `listar_por_assunto(conexao, assunto_id)` (junta com `fonte` para trazer `dominio` junto de cada item — necessário para a regra de fonte independente).
2. **`agente_nw/nucleo/database/queries/assuntos.py`** (novo): `inserir`, `obter_por_id`, `listar_candidatos(conexao, desde_janela, desde_reabertura)` (status `novo`/`em_curso` com `ultimo_visto >= desde_janela`, **união** com status `encerrado` com `ultimo_visto >= desde_reabertura`), `atualizar_apos_item(conexao, assunto_id, ultimo_visto, n_itens, n_fontes_independentes, status, agora)`, `fechar_inativos(conexao, antes_de, agora) -> int` (todos com status `novo`/`em_curso` e `ultimo_visto < antes_de` viram `encerrado`; devolve quantos), `listar_maiores_que(conexao, n) -> list[Assunto]`, `gravar_centroide(conexao, assunto_id, centroide)` (mesmo padrão de `gravar_embedding`, mas grava em `vetor_assunto.centroide`), `obter_centroide(conexao, assunto_id) -> list[float] | None`.
3. **`agente_nw/nucleo/agrupamento/agrupador.py`**: `agrupar(cliente_llm, conexao, limiares, caminho_sentinela, data_referencia, limite=100) -> ResumoAgrupamento`. Ver seção 5 para o algoritmo exato.
4. **`agente_nw/nucleo/agrupamento/divisao.py`**: `dividir(vetores_itens: dict[int, list[float]]) -> tuple[list[int], list[int]] | None` — bipartição pura, sem banco, testável isolada com vetores fabricados. Devolve `None` se não conseguir separar em duas partes não vazias.
5. **`agente_nw/nucleo/modelos/calibracao.py`** (novo): `RespostaComparacaoPar` — `{"mesmo_assunto": bool}`, `frozen=True`.
6. **`agente_nw/nucleo/prompts/prerotular_calibracao.py`**: `construir_prompt(titulo_a: str, trecho_a: str, titulo_b: str, trecho_b: str) -> str`, contrato `prerotular_calibracao`, exemplo resolvido com dois pares claramente distintos entre si e do texto real de teste (armadilha 24).
7. **`agente_nw/nucleo/agrupamento/calibracao.py`**: `calibrar(cliente_llm, conexao, caminho_limiares_yaml, caminho_adr, perguntar=input) -> ResumoCalibracao`. Ver seção 6.
8. **`agente_nw/cli.py`**: comando `agrupar` (novo, sem argumento obrigatório) e implementação real de `calibrar-agrupamento` (sai de `COMANDOS_RESERVADOS`).

---

## 4. Fora de escopo, com justificativa

- **`titulo_gerado` e `assunto.temas`.** Como já dito na seção 2 — são do brief 008, confirmado contra o próprio plano e contra `docs/PLAN.md`.
- **Divisão recursiva (um assunto dividido gerar um filho que também precisa dividir, na mesma execução).** O comando `agrupar` faz no máximo uma divisão por assunto por execução; se a parte resultante ainda estiver grande, a próxima execução do comando cuida dela. Consistente com o resto do projeto: correção limitada, não laço até resolver (AGENTS.md, e a própria calibração deste brief usa a mesma lógica de "até duas tentativas, não mais").
- **Purga de `item.texto` após 90 dias.** Já é dívida 4 registrada em `docs/PLAN.md`, sem dono definido; não é deste brief.
- **Reprocessar assuntos já formados depois de recalibrar o limiar.** A calibração só muda o valor em `limiares.yaml` — não refaz o agrupamento já feito com o limiar antigo. Refazer do zero destruiria o histórico de `primeiro_visto`/`ultimo_visto` real sem necessidade; a próxima execução de `agrupar` já usa o limiar novo para tudo que for pendente ou novo.

---

## 5. Algoritmo de agrupamento (`agrupador.agrupar`)

**Fase 1 — embedding e atribuição**, para cada item de `itens.listar_sem_assunto` (na ordem, até `limite`; interrompe se `caminho_sentinela.exists()`, mesmo padrão de `leitor.coletar`):

1. Embedding via `cliente_llm.embeddar([titulo + "\n\n" + texto[:2000]])` (texto trunca em 2000 caracteres; se `texto` for `None`, embeda só o título). Falha de rede aqui propaga e derruba o comando — de propósito, mesma regra do brief 003.
2. Grava o embedding em `vetor_item` (`itens.gravar_embedding`).
3. Data de referência do item: `item.publicado_em or item.coletado_em`.
4. Busca candidatos: `assuntos.listar_candidatos` com `desde_janela = data_item - limiares.janela_dias` (candidatos abertos) e `desde_reabertura = data_item - coleta.retencao_texto_dias` (candidatos encerrados — usa o limiar de retenção de texto já existente em `limiares.yaml`, em vez de inventar um novo número: um assunto não deveria conseguir reabrir depois que o texto de seus itens já teria sido purgado). Para cada candidato, cosseno entre o vetor do item e `assuntos.obter_centroide`. Guarda o melhor.
5. **Se não há candidato com cosseno ≥ `cosseno_mesmo_assunto`:** cria assunto novo (`primeiro_visto = ultimo_visto = data_item`, `n_itens = 1`, `n_fontes_independentes = 1`, `status = "novo"`, `temas = []`), grava seu centróide (o próprio vetor do item) e vincula o item a ele.
6. **Se há candidato:** busca os itens já no assunto candidato (`itens.listar_por_assunto`) e calcula o maior cosseno item-a-item entre o item novo e cada um deles.
   - **Se esse maior cosseno ≥ `cosseno_republicacao`:** é republicação — vincula o item ao assunto (`item.assunto_id`), mas **não** incrementa `n_itens` nem recalcula o centróide nem mexe em `n_fontes_independentes`. Só atualiza `ultimo_visto` se `data_item` for mais recente que o atual.
   - **Senão (cosseno ao centróide ≥ limiar mas abaixo de republicação):** vincula, incrementa `n_itens`, recalcula o centróide como a média de todos os vetores dos itens do assunto (incluindo o novo — busca todos via `itens.listar_por_assunto` + o novo), atualiza `ultimo_visto = data_item`. Aplica a regra de fonte independente (próximo item da lista): se aumentar, incrementa `n_fontes_independentes`. Se `status == "encerrado"`, muda para `"em_curso"` e imprime uma linha `"assunto {id} reaberto — volta ao noticiário"` no resumo. Se `status == "novo"` e `n_itens` agora é ≥ 2, muda para `"em_curso"`.
7. **Regra de fonte independente** (só roda para item não-republicação): mantém, por assunto, a lista de domínios já contados com o vetor do item que os representou. O domínio do item novo (via `fonte.dominio`, trazido por `listar_por_assunto`) só conta como fonte independente nova se (a) esse domínio ainda não está na lista **e** (b) o cosseno do item novo contra **todo** item já contado é `< (1 - divergencia_minima_fonte_independente)`, ou seja, `< 0.70` com o valor atual. Isso é o que a armadilha 4 de `docs/PLAN.md` já registrava: "fonte só é independente com domínio diferente e divergência de texto acima de 30%".

**Fase 2 — fechamento**, depois de processar todos os itens pendentes: `assuntos.fechar_inativos(conexao, data_referencia - limiares.janela_dias, agora)`.

**Fase 3 — divisão**, depois do fechamento: para cada assunto com `n_itens > itens_para_dividir` (`assuntos.listar_maiores_que`), busca os vetores de todos os seus itens, calcula a similaridade média de cada item ao centróide atual; se a média for `< cosseno_mesmo_assunto` (dispersão alta — a definição operacional de "sem coesão suficiente" da seção 6 de `ARQUITETURA.md`), chama `divisao.dividir`. Se devolver duas partes não vazias: o assunto original fica com uma partição (recalcula `primeiro_visto`/`ultimo_visto`/`n_itens`/`n_fontes_independentes`/centróide a partir só dos itens que ficaram), a outra partição vira um assunto novo (mesmo processo, `status` = `"em_curso"` se ≥ 2 itens já não-republicados, `"novo"` caso não dê pra saber — na prática sempre vai ser `em_curso` ou mais, já que só dividimos assunto com mais de 12 itens). Todos os itens migrados têm `item.assunto_id` atualizado. Se `divisao.dividir` devolver `None` (não conseguiu separar em duas partes não vazias), registra uma linha em `fila_revisao` (`tarefa="dividir_assunto"`, `entrada=str(assunto_id)`, `erro="dispersão alta mas sem separação em duas partes"`) e segue sem travar o comando.

`ResumoAgrupamento`: `itens_embeddados`, `assuntos_criados`, `itens_vinculados`, `republicacoes`, `assuntos_reabertos`, `assuntos_encerrados`, `assuntos_divididos`.

**`divisao.dividir`** — bipartição por sementes mais distantes, refinada em até 5 iterações (não é o agrupamento principal, que continua sendo ligação simples por limiar fixo — `ARQUITETURA.md` seção 6 — isto é só a ferramenta interna de separar um assunto que já cresceu demais): as duas sementes iniciais são o par de itens com menor cosseno entre si; cada item vai para a semente mais próxima; recalcula os dois centróides; repete até estabilizar ou 5 rodadas. Se qualquer rodada deixar uma partição vazia, devolve `None`.

---

## 6. Ferramenta de calibração (`calibracao.calibrar`)

1. Busca todos os itens com embedding gravado (`vetor_item` não vazio) — via uma função nova em `itens.py`, `listar_com_embedding(conexao) -> list[tuple[Item, list[float]]]` (some com essa nesse arquivo também, seção 3 item 1).
2. Calcula o cosseno de todo par (i, j), i < j. Separa em três grupos pelo valor: `dentro_da_banda` (0.70 ≤ cosseno ≤ 0.92), `controle_iguais` (cosseno > 0.92), `controle_distintos` (cosseno < 0.70).
3. Amostra (`random.Random`, sem semente fixa na execução real — a função aceita um `random.Random` injetável, e os testes passam um com semente fixa): até 35 pares de `dentro_da_banda`; até 15 de controle, split o mais parecido possível de metade/metade entre `controle_iguais` e `controle_distintos` (ex.: 8 e 7). Se um grupo tiver menos pares que o pedido, pega todos os que existirem — sem travar o comando, só relata no resumo final quantos entraram de cada grupo.
4. Para cada par amostrado, chama `cliente_llm.gerar_json("prerotular_calibracao", ..., RespostaComparacaoPar)`. `FalhaJsonInvalido` nesse par não derruba o comando — conta como erro, o par é descartado da amostra, segue para o próximo (mesmo padrão de `processar_fila`).
5. Lê o limiar atual de `cosseno_mesmo_assunto` do `limiares.yaml` (não hardcoded). Para cada par com rótulo do `qwen3:8b`, calcula o rótulo que o limiar atual daria (`cosseno >= limiar_atual`). Onde os dois discordam, é uma discordância.
6. Revisão interativa (função `perguntar`, parâmetro injetável — por padrão `input`, testes passam uma função fake): para cada discordância, imprime os dois títulos, o cosseno e o rótulo do `qwen3:8b`; pergunta `[s]im mesmo assunto / [n]ão são diferentes / [enter] aceitar o qwen3:8b`. O rótulo final de cada par é a resposta de Sidarta nas discordâncias, e o do `qwen3:8b` nos demais.
7. Varredura de limiar: para cada valor candidato (os próprios cossenos observados na amostra, ordenados), calcula quantos pares a regra `cosseno >= candidato ⟺ rótulo final = mesmo assunto` acerta. Escolhe o candidato com mais acertos; empate resolvido pelo mais próximo do limiar atual (estabilidade — não trocar o limiar à toa quando dois valores acertam igual).
8. Escreve o novo valor em `config/limiares.yaml`: **localiza e substitui só a linha de `cosseno_mesmo_assunto` por regex/string, preservando o resto do arquivo byte a byte** — nunca `yaml.safe_load` + `yaml.dump` do arquivo inteiro, que apagaria os comentários das outras linhas (inclusive o `# calibrar no brief 009` do limiar do conector, que não é deste brief).
9. Escreve o ADR em `docs/adr/adr-0001-limiar-agrupamento.md` (cria a pasta `docs/adr/` se não existir — fica dentro de `docs/`, já coberto por `docs/*` no `.gitignore`, nunca commitado, igual a `PLAN.md`/`PLANO.md`/`ARQUITETURA.md`): data, valor anterior, valor novo, composição da amostra (quantos em cada grupo), distribuição dos cossenos da banda de dúvida (mínimo, máximo, média, mediana), quantas discordâncias e como cada uma foi resolvida, acurácia final do limiar escolhido sobre a amostra.

`ResumoCalibracao`: `pares_na_banda`, `pares_controle`, `pares_avaliados`, `discordancias`, `limiar_anterior`, `limiar_novo`, `caminho_adr`.

---

## 7. Decisões tomadas e deixadas abertas

**Tomadas** (além das já embutidas na seção 5 e 6, que são a maior parte deste brief):

- **Reabertura limitada a `retencao_texto_dias` (90 dias), não ilimitada.** `ARQUITETURA.md` não fixa um prazo para reabertura; sem limite, um cosseno alto por coincidência (temas recorrentes, como "Carnaval") poderia reabrir um assunto de anos atrás. Reaproveitar o limiar de retenção de texto já existente evita inventar um número novo e é coerente: não faz sentido reabrir um assunto cujo texto já teria sido purgado.
- **Recálculo do centróide é média simples de todos os vetores do assunto, não incremental ponderado.** Na escala de um usuário só, recalcular do zero a cada item é barato e sempre exato — não há razão para a complexidade (e o risco de erro de arredondamento acumulado) de uma média incremental.
- **Ordem de checagem é candidato por cosseno ao centróide primeiro, republicação depois.** Só faz sentido checar republicação (item contra item) dentro do assunto que já passou no corte do centróide — checar republicação contra todo item de todo assunto seria caro e sem necessidade.

**Deixadas abertas:**

- Se a coleta acumulada até a execução deste brief não tiver pares suficientes na banda de dúvida (mínimo 30, conforme o critério de aceite), a calibração não pode ser certificada ainda — Sidarta precisa rodar `agente_nw coletar` em mais dias antes. Isso não é um defeito do código, é dado insuficiente; fica registrado em `docs/PLAN.md` se acontecer.

---

## 8. Passos de execução

1. `queries/itens.py`: as cinco funções novas da seção 3, item 1 (mais `listar_com_embedding` da seção 6, item 1).
2. `tests/test_itens_agrupamento.py`: cada função nova, contra um banco de teste com 4-5 itens fabricados (alguns com embedding, alguns sem; alguns com `assunto_id`, alguns sem).
3. `queries/assuntos.py`: todas as funções da seção 3, item 2.
4. `tests/test_assuntos.py`: `listar_candidatos` com um assunto dentro da janela, um fora, um encerrado dentro do prazo de reabertura e um encerrado fora dele — confirma que só os certos voltam; `fechar_inativos` muda status e devolve a contagem certa; `gravar_centroide`/`obter_centroide` fazem ida e volta.
5. `agente_nw/nucleo/agrupamento/divisao.py`: `dividir`, com testes usando vetores 2D fabricados (dois blocos bem separados de 3-4 pontos cada) — confirma que separa certo; um caso com todos os pontos idênticos confirma que devolve `None`.
6. `agente_nw/nucleo/agrupamento/agrupador.py`: `agrupar`, conforme seção 5.
7. `tests/test_agrupador.py`, com um `ClienteOllama` fake (só implementa `embeddar`, devolvendo vetores fabricados de baixa dimensão — trocar por um `Protocol`/fake mínimo, não o `ClienteOllama` real) e um banco de teste isolado (`conexao.abrir(tmp_path/...)`, nunca `container.banco()` — armadilha 18): dois itens com vetores quase iguais formam um assunto só; um terceiro item com vetor bem diferente abre assunto novo; um item republicado (vetor quase idêntico a um item já no assunto) não incrementa `n_itens`; um assunto fechado por `fechar_inativos` reabre quando chega item compatível dentro do prazo; um assunto com mais de 12 itens fabricados em dois blocos dispersos divide em dois.
8. `nucleo/modelos/calibracao.py` e `nucleo/prompts/prerotular_calibracao.py`, seguindo o padrão de `extrair_de_texto.py` (guia de campos, categoria proibida não se aplica aqui, exemplo resolvido com dois pares nitidamente diferentes de qualquer texto real de teste — armadilha 24).
9. `agente_nw/nucleo/agrupamento/calibracao.py`: `calibrar`, conforme seção 6.
10. `tests/test_calibracao.py`: amostragem estratificada com `random.Random` fixo e uma população fabricada de cossenos conhecidos — confirma a proporção pedida (até 35/15) e que grupos pequenos não travam a função; varredura de limiar com um conjunto de (cosseno, rótulo) fabricado onde o melhor corte é conhecido de antemão — confirma que a função acha esse corte; revisão interativa com uma função `perguntar` fake — confirma que só as discordâncias são perguntadas e que a resposta fake vira o rótulo final; escrita em `limiares.yaml` contra um arquivo de teste com comentários em outras linhas — confirma que só a linha do limiar muda, byte a byte no resto.
11. `cli.py`: comando `agrupar` (novo) e implementação de `calibrar-agrupamento` (sai de `COMANDOS_RESERVADOS`).
12. `tests/test_cli_agrupamento.py`: `agrupar` sem itens pendentes não erra, só relata zero; `calibrar-agrupamento` sem itens com embedding suficiente relata e não trava.
13. Rodar de verdade, nesta ordem, contra o banco real: `agente_nw agrupar` (com pelo menos dois dias de coleta acumulada); conferir no banco (`sqlite3`) que existem assuntos com `n_itens` > 1 e `n_fontes_independentes` > 1; `agente_nw calibrar-agrupamento`, respondendo às discordâncias que aparecerem; conferir que `config/limiares.yaml` mudou só a linha esperada (`git diff` não serve, o arquivo não é rastreado — comparar visualmente ou com `diff` contra uma cópia feita antes) e que o ADR foi escrito; rodar `agente_nw agrupar` de novo para confirmar que usa o limiar novo sem erro.
14. Atualizar `docs/PLAN.md`: brief 007 concluído; registrar a composição real da amostra de calibração, o limiar final e quantos assuntos reais ficaram com mais de uma fonte independente.

---

## 9. Critérios de aceite

1. Limiar calibrado sobre coleta real de dois ou mais dias, com pelo menos 30 pares dentro da banda de dúvida (0.70–0.92) avaliados.
2. ADR escrito em `docs/adr/`, com a distribuição dos cossenos da amostra.
3. Com o limiar calibrado, pelo menos cinco assuntos reais formados por mais de uma fonte independente (`n_fontes_independentes > 1`).
4. Nenhum assunto, no banco real, com mais de 12 itens sem ter passado por divisão (ou registrado em `fila_revisao` como não separável).
5. `scripts/verificar.sh` verde nos testes automatizados (todos exceto o passo 13, que é execução manual contra dado real e Ollama real).

---

## 10. Riscos e como reverter

| Risco | Controle |
|---|---|
| Coleta acumulada insuficiente para 30 pares na banda de dúvida | comando informa quantos pares entraram em cada grupo; se insuficiente, Sidarta roda `agente_nw coletar` em mais dias antes de repetir a calibração — não é um bug, é dado insuficiente |
| `qwen3:8b` falha na geração de alguns pares (JSON inválido) | não derruba o comando — o par é descartado da amostra, contabilizado como erro no resumo |
| Divisão de assunto gerar uma partição vazia (todos os itens caem do mesmo lado) | não divide, registra em `fila_revisao`, segue sem travar — próxima execução pode tentar de novo se o assunto continuar crescendo |
| Reescrita de `limiares.yaml` corromper o arquivo ou apagar comentários de outras linhas | substituição é por regex/string numa linha só, nunca reescrita do arquivo inteiro via `yaml.dump` |
| Reverter | Todos os arquivos deste brief são novos, exceto as funções aditivas em `queries/itens.py` (nenhuma das duas existentes tocada) e os dois comandos novos em `cli.py` (o segundo, `calibrar-agrupamento`, volta a `COMANDOS_RESERVADOS` se precisar desfazer) |

---

## 11. Relatório final obrigatório

Preencher o bloco da seção 8 de `AGENTS.md`, com o caminho do script de verificação para colar no terminal. Sem esse bloco preenchido, o brief não está concluído.
