# Brief E1-008 — Qualificação, rótulo, cartão e exemplos de conversabilidade

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Depende de:** brief 007 (agrupamento e calibração), certificado — 283 assuntos reais já disponíveis como candidatos.

---

## 1. Objetivo em uma frase

Dar a cada assunto um título, uma nota de quão substancial e conversável ele é, e um cartão de três linhas — as três únicas coisas que um modelo escreve nesta camada; o resto (quem é candidato, quanto pontua, o que aparece pra quem) continua sendo aritmética determinística, auditável linha a linha.

---

## 2. Contexto e o que já existe

O esquema já tem tudo: `assunto.titulo_gerado`, `substancial`, `conversavel`, `justificativa`, `resumo_cartao`, `temas` (JSON de ids) — todos `NULL`/`[]` em todo assunto formado pelo brief 007, por desenho explícito daquele brief. `config/limiares.yaml` já tem `qualificacao.substancial_minimo: 0.6`, `qualificacao.conversavel_minimo: 0.6` e `qualificacao.teto_por_dia: 40`. `config/llm_routing.yaml` já roteia `qualificar`, `rotular` e `cartao` para `qwen3:4b`, `think: false`, com `num_ctx` de 2048/2048/4096 respectivamente.

**Este brief não toca em nada de brief 009** (regra do conector, `assunto_contato`, menu). Qualificação decide "esse assunto é substancial e dá conversa" — uma pergunta sobre o assunto em si. A regra do conector decide "esse assunto serve pra esse contato, com esse usuário" — uma pergunta sobre o par assunto+contato+usuário, com dado que só existe depois de qualificação e agrupamento. Um assunto que só interessa a um contato (nenhum tema do usuário perto dele) é qualificado normalmente aqui — descartar por falta de ponto de apoio do usuário é decisão do brief 009, não deste.

**Por isso o critério de aceite 2 existe** (seção 5 da proposta, "regra do conector", ainda não implementada): qualificação tem que ser cega a de quem é o tema — ela vê a união de todos os temas de todos os perfis ativos só para *escolher quem vale a pena mandar pro modelo* (o teto de 40/dia), nunca para decidir o resultado.

---

## 3. Escopo

1. **`agente_nw/nucleo/modelos/rotulo.py`**: `RespostaRotulo` — `{"titulo": str}`, `frozen=True`.
2. **`agente_nw/nucleo/modelos/qualificacao.py`**: `RespostaQualificar` — `{"substancial": float 0–1, "conversavel": float 0–1, "temas": list[str], "justificativa": str}`, `frozen=True`.
3. **`agente_nw/nucleo/modelos/cartao.py`**: `RespostaCartao` — `{"resumo": str}`, `frozen=True`.
4. **`agente_nw/nucleo/prompts/rotular.py`**, **`.../qualificar.py`**, **`.../cartao.py`**: `construir_prompt(...)` + exemplo resolvido, mesmo padrão de `extrair_de_texto.py` (armadilha 24: exemplo com cenário nitidamente distinto de qualquer entrada real de teste).
5. **`agente_nw/nucleo/prompts/exemplos_conversavel.yaml`**: os 20 exemplos da seção 4 abaixo, carregados por `qualificar.py` para compor o prompt (few-shot de calibração de "conversável").
6. **`agente_nw/nucleo/database/queries/assuntos.py`** (aditivo — nenhuma das funções do brief 007 é tocada): `listar_candidatos_qualificacao(conexao, limite)` (assuntos com `substancial IS NULL`, ordenados pelo maior cosseno entre seu centróide e qualquer tema da união de todos os perfis ativos — usuário e contatos com `ativo=1` —, `LIMIT limite`), `gravar_titulo(conexao, assunto_id, titulo)`, `gravar_qualificacao(conexao, assunto_id, substancial, conversavel, justificativa, temas_ids)`, `gravar_cartao(conexao, assunto_id, resumo_cartao)`.
7. **`agente_nw/nucleo/relevancia/qualificador.py`**: `qualificar_pendentes(cliente_llm, conexao, limite) -> ResumoQualificacao`. Ver seção 5.
8. **`agente_nw/nucleo/relevancia/cartoes.py`**: `gerar_cartao(cliente_llm, conexao, assunto_id) -> str | None`. Ver seção 6.
9. **`agente_nw/cli.py`**: comando `qualificar` (novo, `--limite` opcional, default do `teto_por_dia`), comando `cartao <assunto_id>` (novo, prévia manual).

---

## 4. Os 20 exemplos de conversabilidade

**Aprove ou troque antes de eu considerar o prompt fechado** — é o único ponto de aprovação deste brief, e é rápido: são rótulos que você já sabe de cabeça, não um exercício de comparar par a par.

**Conversável (dá pra puxar assunto com um resumo curto na mão, sem ser especialista):**

1. Uma empresa brasileira conhecida anuncia demissões em massa.
2. Um prefeito de capital toma posse e anuncia prioridades de governo.
3. Um time de futebol grande demite o técnico após sequência de derrotas.
4. O governo anuncia mudança na tabela do Imposto de Renda.
5. Um aplicativo popular (WhatsApp, Instagram) lança uma função nova e polêmica.
6. Uma celebridade brasileira se envolve em polêmica pública.
7. Chuvas fortes causam alagamentos numa grande cidade.
8. O Banco Central anuncia mudança na taxa Selic.
9. Uma nova lei de trânsito entra em vigor mudando o cotidiano.
10. Uma empresa de tecnologia global anuncia um produto novo de IA para o público geral.

**Não conversável (exige bagagem técnica específica pra falar com naturalidade):**

1. Mudança numa interpretação técnica de norma contábil sobre reconhecimento de receita.
2. Decisão de câmara técnica da Anvisa sobre bioequivalência de um medicamento genérico.
3. Alteração num parâmetro técnico de protocolo de rede (ex.: uma RFC de TLS).
4. Julgamento de tese repetitiva em tribunal superior sobre prescrição intercorrente tributária.
5. Divulgação de paper acadêmico sobre otimização de hiperparâmetros em modelo de linguagem.
6. Mudança em cláusula específica de acordo de compensação entre instituições financeiras.
7. Detalhe técnico de atualização de kernel Linux sobre gerenciamento de memória.
8. Novo padrão técnico de compactação de vídeo aprovado por consórcio internacional.
9. Disputa societária entre fundos sobre cláusula de tag along num contrato específico.
10. Resultado de ensaio clínico fase 2 de um composto farmacêutico sem nome comercial.

`prompts/exemplos_conversavel.yaml`:

```yaml
conversavel:
  - "Uma empresa brasileira conhecida anuncia demissões em massa."
  - "Um prefeito de capital toma posse e anuncia prioridades de governo."
  - "Um time de futebol grande demite o técnico após sequência de derrotas."
  - "O governo anuncia mudança na tabela do Imposto de Renda."
  - "Um aplicativo popular (WhatsApp, Instagram) lança uma função nova e polêmica."
  - "Uma celebridade brasileira se envolve em polêmica pública."
  - "Chuvas fortes causam alagamentos numa grande cidade."
  - "O Banco Central anuncia mudança na taxa Selic."
  - "Uma nova lei de trânsito entra em vigor mudando o cotidiano."
  - "Uma empresa de tecnologia global anuncia um produto novo de IA para o público geral."
nao_conversavel:
  - "Mudança numa interpretação técnica de norma contábil sobre reconhecimento de receita."
  - "Decisão de câmara técnica da Anvisa sobre bioequivalência de um medicamento genérico."
  - "Alteração num parâmetro técnico de protocolo de rede (ex.: uma RFC de TLS)."
  - "Julgamento de tese repetitiva em tribunal superior sobre prescrição intercorrente tributária."
  - "Divulgação de paper acadêmico sobre otimização de hiperparâmetros em modelo de linguagem."
  - "Mudança em cláusula específica de acordo de compensação entre instituições financeiras."
  - "Detalhe técnico de atualização de kernel Linux sobre gerenciamento de memória."
  - "Novo padrão técnico de compactação de vídeo aprovado por consórcio internacional."
  - "Disputa societária entre fundos sobre cláusula de tag along num contrato específico."
  - "Resultado de ensaio clínico fase 2 de um composto farmacêutico sem nome comercial."
```

---

## 5. `qualificador.qualificar_pendentes`

1. Busca a união dos `tema_id` de `perfil_tema` de todos os perfis com `tipo='usuario'` ou `ativo=1`; busca os embeddings desses temas (`vetor_tema`).
2. `assuntos.listar_candidatos_qualificacao(conexao, limite)`: para cada assunto com `substancial IS NULL`, cosseno do seu centróide contra cada tema da união, guarda o maior; ordena decrescente, corta em `limite` (default `limiares.qualificacao.teto_por_dia`).
3. Para cada candidato, nessa ordem:
   a. Se `titulo_gerado is None`: monta o prompt de `rotular` (assunto + até 5 itens mais recentes — título e domínio da fonte de cada um) e chama `gerar_json("rotular", ..., RespostaRotulo)`. `FalhaJsonInvalido` aqui pula o assunto inteiro (sem título, não faz sentido qualificar) — conta como erro no resumo, segue pro próximo candidato.
   b. Monta o prompt de `qualificar` (título, os mesmos itens resumidos, domínios das fontes, e a lista de nomes de todos os temas conhecidos — `queries_temas.listar`) e chama `gerar_json("qualificar", ..., RespostaQualificar)`. `FalhaJsonInvalido` conta como erro, segue pro próximo.
   c. Mapeia os nomes de `temas` da resposta para id via `queries_temas.obter_por_nome` — nome que não bate com nenhum tema conhecido é descartado silenciosamente (o modelo alucinou um nome fora da lista dada; não é erro que trava, é entrada inválida que se ignora, mesmo espírito do filtro de categoria sensível).
   d. `assuntos.gravar_qualificacao(conexao, assunto_id, substancial, conversavel, justificativa, temas_ids)`. Commit por assunto (mesmo padrão de `processar_fila`/`agrupar`).
4. `ResumoQualificacao`: `candidatos`, `titulos_gerados`, `qualificados`, `erros`.

Sem corte de `substancial_minimo`/`conversavel_minimo` aqui — os dois valores são gravados sempre, o corte 0,6/0,6 é filtro de leitura pra quem consome (brief 009), não motivo pra não gravar.

---

## 6. `cartoes.gerar_cartao`

1. Busca o assunto e seus itens (até 5 mais recentes, com domínio da fonte e, se houver, os primeiros 300 caracteres do texto).
2. Monta o prompt de `cartao` (título, itens com trecho, domínios) e chama `gerar_json("cartao", ..., RespostaCartao)`.
3. **Verificação determinística, não o modelo**: todo número no texto do cartão (dígito, ainda que dentro de "40%" ou "R$ 200 milhões") precisa ter uma fonte entre parênteses na mesma linha — ex.: "(G1)", "(Valor Econômico)". Checagem por linha: linha com dígito sem `(` e `)` na mesma linha reprova.
4. Se reprovar: tenta de novo (mesma lógica de `nova_tentativa` do `gerar_json` — usa a temperatura de nova tentativa). Se reprovar de novo: registra em `fila_revisao` (`tarefa="cartao"`, `entrada=str(assunto_id)`, `erro="número sem fonte entre parênteses"`) e devolve `None` — quem chamou decide o que fazer (o brief 009, quando existir, decide como tratar um cartão ausente; não é problema deste brief resolver antecipadamonce).
5. Se aprovar: `assuntos.gravar_cartao(conexao, assunto_id, resumo)`, devolve o texto.

---

## 7. Decisões tomadas e deixadas abertas

**Tomadas:**

- **Candidatura por proximidade à união de temas, sem limiar de corte — só o teto de 40/dia.** É o que a proposta pede (seção 2 de contexto): o teto já limita o volume, um limiar de corte adicional aqui seria decisão sem pedido.
- **Assunto já qualificado não é requalificado, mesmo que ganhe itens novos depois.** Mesma lógica do brief 007 (recalibrar não reprocessa o que já foi formado): requalificação automática de assunto que já tinha nota abre uma complexidade (que fila tem prioridade, o quê ainda vale) que a proposta não pede. Fica registrado como limitação conhecida, não como defeito.
- **Nome de tema que o modelo devolver fora da lista conhecida é descartado, não vira tema novo.** Diferente de `extrair_de_texto` (onde tag nova de contato pode virar tema novo, brief 004) — aqui a lista de temas já é dada ao modelo no prompt; um nome fora dela é alucinação, não uma sugestão legítima de tema novo.
- **`gerar_cartao` não é chamado em lote para todo assunto qualificado — só sob demanda** (comando `cartao <assunto_id>`, e futuramente pelo brief 009 para quem entrar de fato num menu). Gerar cartão pra todo assunto qualificado gastaria chamada de LLM com quem nunca vai aparecer pra ninguém.

**Deixadas abertas:**

- Cartão que falha duas vezes na verificação de número-com-fonte fica sem `resumo_cartao` (registrado em `fila_revisao`); o brief 009 decide como o menu se comporta diante de um assunto sem cartão (mostrar sem cartão expansível, tentar de novo no próximo ciclo, etc.) — não é decisão deste brief.

---

## 8. Passos de execução

1. Os três modelos (`rotulo.py`, `qualificacao.py`, `cartao.py`) e os três prompts, com `prompts/exemplos_conversavel.yaml` exatamente como a seção 4 (não alterar os exemplos sem me avisar — são aprovação de produto, não detalhe de implementação).
2. `queries/assuntos.py`: as quatro funções aditivas da seção 3, item 6.
3. `tests/test_assuntos_qualificacao.py`: `listar_candidatos_qualificacao` com temas de um contato ativo e do usuário fabricados — confirma que a ordenação por proximidade funciona e que um assunto próximo só do tema de um contato (não do usuário) ainda aparece na lista (base do critério de aceite 2). `gravar_qualificacao`/`gravar_titulo`/`gravar_cartao` fazem ida e volta.
4. `nucleo/relevancia/qualificador.py`, conforme seção 5.
5. `tests/test_qualificador.py`, com um `ClienteOllama` fake (retornos fabricados por tarefa): título gerado antes de qualificar num assunto sem título; assunto que já tem título não chama `rotular` de novo; nome de tema fora da lista conhecida é descartado sem travar; erro de JSON num candidato não impede os demais.
6. `nucleo/relevancia/cartoes.py`, conforme seção 6.
7. `tests/test_cartoes.py`: cartão com número e fonte entre parênteses na mesma linha aprova; cartão com número sem fonte reprova, tenta de novo, e se falhar de novo vai pra `fila_revisao` e devolve `None`.
8. `cli.py`: comandos `qualificar` e `cartao <assunto_id>`.
9. `tests/test_cli_qualificacao.py`: `qualificar` sem candidatos não erra; `cartao` de um assunto sem qualificação ainda funciona (o cartão não depende de `substancial`/`conversavel` estarem preenchidos); `cartao` de um `assunto_id` inexistente dá erro claro.
10. Rodar de verdade, contra o banco real (283 assuntos do brief 007, todos candidatos): `agente_nw qualificar` até completar pelo menos 40 qualificações reais — registrar o percentual real de JSON válido. Se vier abaixo de 95%, documentar como achado real em `docs/PLAN.md` (mesmo padrão da dívida do brief 004), não travar tentando de novo indefinidamente.
11. Verificação do critério de aceite 2: escolher, no resultado real, um assunto cujo único tema próximo seja de um contato (não do usuário) e confirmar que foi qualificado normalmente (tem `substancial`/`conversavel` gravados).
12. Verificação do critério de aceite 3: rodar `agente_nw cartao <id>` para 5 a 10 assuntos reais já qualificados; conferir manualmente que nenhum cartão real tem número sem fonte entre parênteses (a checagem determinística já barra isso na gravação — esta é a confirmação de que a checagem está funcionando contra dado real, não só contra os testes fabricados).
13. Atualizar `docs/PLAN.md`: brief 008 concluído; percentual real de JSON válido medido; quantos assuntos qualificados de fato.

---

## 9. Critérios de aceite

1. Pelo menos 40 qualificações reais rodadas, com JSON válido em 95% ou mais (ou, se abaixo, documentado como achado real em `docs/PLAN.md`, não como brief não concluído — mesmo tratamento dado à confiabilidade do `qwen3:4b` no brief 004).
2. Um assunto real que só toca tema de um contato (nenhum do usuário) foi qualificado normalmente.
3. Nenhum cartão real gerado tem número sem fonte entre parênteses.
4. `scripts/verificar.sh` verde nos testes automatizados.

---

## 10. Riscos e como reverter

| Risco | Controle |
|---|---|
| `qwen3:4b` alucinar nome de tema fora da lista dada | descartado silenciosamente, não vira tema novo, não trava a qualificação do resto da resposta |
| Cartão insistir em número sem fonte mesmo depois de nova tentativa | vai para `fila_revisao`, assunto fica sem `resumo_cartao` — decisão de exibição fica para o brief 009 |
| Percentual real de JSON válido abaixo de 95% | documentado como achado real, mesmo tratamento do brief 004 — não é motivo para travar o brief indefinidamente tentando de novo |
| Reverter | Todos os arquivos deste brief são novos, exceto as quatro funções aditivas em `queries/assuntos.py` (nenhuma função do brief 007 tocada) e os dois comandos novos em `cli.py` |

---

## 11. Relatório final obrigatório

Preencher o bloco da seção 8 de `AGENTS.md`, com o caminho do script de verificação para colar no terminal. Sem esse bloco preenchido, o brief não está concluído.
