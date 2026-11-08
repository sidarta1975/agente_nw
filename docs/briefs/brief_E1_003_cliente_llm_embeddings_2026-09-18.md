# Brief E1-003 — Cliente de LLM e embeddings

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Depende de:** brief 002 (concluído e certificado)
**Não depende de:** nenhum brief posterior. Nenhum brief posterior roda sem este.

---

## 1. Objetivo em uma frase

Dar ao projeto um único cliente do Ollama — geração com JSON validado e nova tentativa, e embeddings — mais as funções de cosseno e centróide, fechando `container.llm()` e liberando todos os módulos que precisam de inteligência.

---

## 2. Contexto e o que já existe

`config/container.py` já tem `llm()` como `raise NotImplementedError("brief 003")`. `banco()`, `http()` e `configuracao()` já funcionam e são cacheados por processo — este brief usa os três, não recria nenhum.

`config/llm_routing.yaml` já declara o perfil `air16` com seis tarefas (`qualificar`, `rotular`, `cartao`, `cruzar_por_que`, `extrair_de_texto`, `prerotular_calibracao`), cada uma com `modelo`, `num_ctx`, `temperature`, `format` e `think`, mais `nova_tentativa: {temperature: 0.1, maximo: 1}`. `agente_nw/nucleo/modelos/configuracao.py` já valida essas seis tarefas via `Roteamento`/`TarefaRoteamento`, e `TarefaRoteamento` já **recusa carregar qualquer perfil em que `think` não seja `false`** — a validação de que "o modo de raciocínio nunca liga" já existe na configuração; este brief garante que o valor validado chega inteiro em toda chamada HTTP, não que ele seja recusado (isso já está feito).

A migração 001 já criou `fila_revisao` (`id, tarefa, entrada, erro, criado_em, resolvido`) e `agente_nw/nucleo/modelos/fila.py` já tem o modelo Pydantic `FilaRevisao` correspondente — nenhum dos dois precisa ser criado ou alterado aqui. As quatro tabelas virtuais do `sqlite-vec` (`vetor_tema`, `vetor_item`, `vetor_assunto`, `vetor_perfil`, todas em 1024 dimensões) também já existem. `agente_nw/nucleo/database/queries/temas.py` já tem `gravar_embedding(conexao, tema_id, embedding)`, que serializa com `sqlite_vec.serialize_float32` e grava em `vetor_tema` — este brief não mexe nessa função nem a duplica; é o padrão que os módulos dos briefs 006, 007 e 009 vão repetir para `vetor_item`, `vetor_assunto` e `vetor_perfil`, cada um na sua própria camada de consultas, quando essas tabelas de conteúdo existirem.

`agente_nw/nucleo/llm.py` e `agente_nw/nucleo/vetores.py` ainda não existem — este brief os cria. `agente_nw/nucleo/prompts/` está vazio e **continua vazio** depois deste brief: os prompts de cada contrato de produto (`qualificar`, `cruzar`, `extrair_de_texto`, etc.) são autoria dos briefs que implementam esses contratos (004, 008, 009); este brief entrega só o cano por onde qualquer prompt futuro vai passar.

---

## 3. Escopo

1. `agente_nw/nucleo/llm.py` — classe `ClienteOllama` com dois métodos:
   - `gerar_json(tarefa: str, prompt: str, esquema: type[BaseModel]) -> BaseModel`: resolve modelo/`num_ctx`/`temperature`/`format`/`think` pelo nome da tarefa no perfil ativo de `llm_routing.yaml`; chama `POST /api/generate` do Ollama; valida a resposta contra `esquema`; em JSON malformado ou reprovado no esquema, tenta de novo com a temperatura de `nova_tentativa`; na segunda falha, grava uma linha em `fila_revisao` com o erro e levanta `FalhaJsonInvalido`.
   - `embeddar(textos: list[str]) -> list[list[float]]`: chama `POST /api/embed` com o modelo de embeddings do perfil ativo (`bge-m3`), em lote, e devolve um vetor de 1024 posições por texto.
2. `agente_nw/nucleo/vetores.py` — `cosseno(a, b) -> float` e `centroide(vetores, pesos=None) -> list[float]`, com NumPy (já é dependência do projeto).
3. `agente_nw/nucleo/database/queries/fila_revisao.py` — `inserir(conexao, tarefa, entrada, erro, agora) -> int`, usando o modelo `FilaRevisao` já existente.
4. `config/container.py` — `llm()` deixa de levantar `NotImplementedError` e passa a devolver um `ClienteOllama` cacheado, construído a partir de `configuracao()`, `http()` e `banco()`.
5. Testes: um de fumaça contra o Ollama real (geração), um de embeddings contra o Ollama real, um que força a fila de revisão, um que intercepta a chamada HTTP sem precisar do Ollama rodando para confirmar que `think: false` sempre vai no corpo da requisição, e testes unitários de `cosseno`/`centroide` sem rede nenhuma.

---

## 4. Fora de escopo, com justificativa

- **Os prompts de produto** (`qualificar`, `cruzar`, `extrair_de_texto`, `rotular`, `cartao`). O cliente é agnóstico ao conteúdo do prompt — só resolve modelo e parâmetros pelo nome da tarefa. Escrever o prompt de cada contrato é trabalho do brief que implementa esse contrato (004, 008, 009), com o texto e os exemplos resolvidos que cada um pede.
- **Gravação de embedding em `vetor_item`, `vetor_assunto` e `vetor_perfil`.** As tabelas de conteúdo (`item`, `assunto` preenchido, `perfil` com centróide) ainda não têm dado — não há o que gravar. Cada brief que passa a preencher essas tabelas (006, 007, 009) escreve sua própria função de gravação em sua própria camada de consultas, no mesmo padrão de `queries/temas.gravar_embedding`. Criar aqui uma função genérica sem nenhum chamador real seria código morto até essas tabelas existirem.
- **Medir a taxa real de JSON válido em produção.** O critério de aceite abaixo é um teste de fumaça (20 chamadas de um prompt fixo). O percentual definitivo é medido no brief 013, sobre uso real de cinco dias.
- **Retentativa configurável por tarefa.** `nova_tentativa` já é um bloco único em `llm_routing.yaml`, válido para toda tarefa do perfil. Diferenciar por tarefa não foi pedido e não tem caso de uso hoje.

---

## 5. Decisões tomadas e deixadas abertas

**Tomadas:**

- **Falha de rede é erro diferente de JSON inválido.** Se o Ollama não responder ou responder com status de erro HTTP, o cliente deixa a exceção do `httpx` subir (`raise_for_status()`); isso não vai para `fila_revisao`, que é só para respostas recebidas e reprovadas na validação. Confundir os dois esconderia uma queda do servidor atrás de um registro de "JSON ruim".
- **`format: json` é o modo solto do Ollama, não um esquema JSON no corpo da chamada.** `llm_routing.yaml` guarda a string `"json"`, não um esquema — a API do Ollama garante só que a resposta é JSON sintaticamente válido; quem valida contra o esquema do contrato é o Pydantic, no cliente, depois da resposta chegar. É o que a proposta descreve como "JSON validado por esquema".
- **`think` vem inteiro do roteamento em toda chamada, nunca hardcoded.** O cliente lê `tarefa.think` (sempre `False`, porque a validação de `TarefaRoteamento` já barra qualquer outro valor na carga da configuração) e manda no corpo da requisição — a garantia dupla é proposital: configuração recusa perfil errado, cliente nunca omite o campo.
- **Uma chamada, um item.** Sem lote na geração — já é a decisão da proposta ("Itens por chamada: 1"). O lote existe só em `embeddar`, porque a API de embeddings do Ollama aceita lista de entrada nativamente e os briefs futuros (006 e 007) vão chamar com dezenas de textos de uma vez.
- **`gerar_json` não tenta reparar JSON por conta própria.** Falhou a validação nas duas tentativas, vai para a fila; nenhuma expressão regular tentando consertar aspas ou vírgulas — a proposta já rejeitou esse caminho para o importador da Etapa 4, e o mesmo raciocínio vale aqui.
- **Teste de fumaça usa a tarefa `qualificar` com um esquema e um prompt fabricados para o teste**, não um contrato de produto. Isso evita que o brief 003 escreva um prompt "provisório" de `qualificar` que o brief 008 teria que jogar fora.

**Deixadas abertas, para brief futuro:**

- Se a taxa real de JSON válido medida no brief 013 ficar abaixo de 95%, ajustar o prompt genérico de cada contrato é trabalho dos briefs 004/008/009, não deste.

---

## 6. Passos de execução

1. Criar `agente_nw/nucleo/vetores.py` com `cosseno(a: Sequence[float], b: Sequence[float]) -> float` (0,0 se algum vetor tiver norma zero, para nunca dividir por zero) e `centroide(vetores: Sequence[Sequence[float]], pesos: Sequence[float] | None = None) -> list[float]` (pesos uniformes se omitidos; `ValueError` explícito em lista vazia — centróide de nada não é zero, é indefinido).
2. Criar `agente_nw/nucleo/database/queries/fila_revisao.py` com `inserir(conexao, tarefa: str, entrada: str, erro: str, agora: str) -> int`, devolvendo o `id` da linha gravada.
3. Criar `agente_nw/nucleo/llm.py`:
   - Exceção `FalhaJsonInvalido(RuntimeError)`, guardando `tarefa`, `fila_revisao_id` e `erro`.
   - Classe `ClienteOllama(http_client, conexao_bd, roteamento, ollama_url)`.
   - `_tarefa(nome: str) -> TarefaRoteamento`: busca no perfil ativo; `KeyError` com mensagem clara se o nome não existir em `llm_routing.yaml`.
   - `gerar_json`: monta o corpo (`model`, `prompt`, `format`, `think`, `options: {num_ctx, temperature}`, `stream: false`), chama `POST {ollama_url}/api/generate`, `raise_for_status()`, tenta `json.loads` da resposta e depois `esquema.model_validate`; em falha de qualquer uma das duas, repete uma vez com a temperatura de `nova_tentativa`; falhando de novo, grava em `fila_revisao` via o módulo do passo 2 e levanta `FalhaJsonInvalido`.
   - `embeddar`: `POST {ollama_url}/api/embed` com `model` do bloco `embeddings` do perfil e `input` como a lista de textos; devolve a lista de vetores na mesma ordem da entrada; confere que cada vetor tem 1024 posições antes de devolver.
4. Editar `config/container.py`: `llm()` deixa de levantar `NotImplementedError`, ganha `@functools.lru_cache(maxsize=1)` e devolve `ClienteOllama(http(), banco(), configuracao().roteamento, configuracao().local.ollama_url)`.
5. `tests/test_vetores.py`: `cosseno` de vetores iguais = 1,0; de vetores ortogonais = 0,0; vetor de norma zero não quebra; `centroide` de dois vetores com pesos iguais bate com a média simples; `centroide([])` levanta `ValueError`.
6. `tests/test_llm_payload.py` (sem rede — intercepta a chamada com um transporte falso do `httpx`, por exemplo `httpx.MockTransport`): confirma que o corpo enviado a `/api/generate` sempre tem `"think": false` e que `format`, `num_ctx` e `temperature` batem com os valores de `qualificar` em `llm_routing.yaml`.
7. `tests/test_llm_fumaca.py` (Ollama real — marcar com um `pytest.mark` próprio ou pular de saída com mensagem clara se `agente_nw verificar-ambiente` mostrar Ollama fora do ar, para não confundir queda de servidor com defeito de código):
   - 20 chamadas de `gerar_json` com um esquema e prompt fabricados para o teste (não um contrato de produto) devolvem instância válida do esquema nas 20.
   - `embeddar` de 100 textos curtos e distintos devolve 100 vetores de 1024 posições em menos de 30 segundos.
   - Uma chamada com esquema propositalmente impossível de satisfazer (campo que nenhuma instrução plausível preenche) levanta `FalhaJsonInvalido` e deixa uma linha nova em `fila_revisao` com `resolvido = 0` e o erro de validação no campo `erro`.
8. Rodar `scripts/verificar.sh` e corrigir até fechar (ruff, mypy, os testes que não dependem de Ollama).
9. Com o Ollama de pé (`OLLAMA_MAX_LOADED_MODELS=2 OLLAMA_KEEP_ALIVE=30m ollama serve` num terminal à parte, como na preparação da máquina), rodar os testes de fumaça manualmente uma vez para confirmar que passam antes de fechar o brief; não é o `scripts/verificar.sh` quem vai rodar isso de forma automática caso o Ollama não esteja no ar no momento em que Sidarta colar o comando — é por isso que o passo 7 exige que a ausência do Ollama vire um "pulado, motivo: Ollama fora do ar", nunca um erro genérico de conexão.
10. Atualizar `docs/PLAN.md`: brief 003 concluído; próximo é 006 (coleta RSS, antecipado à frente de 004/005 para acumular material antes da calibração, conforme a ordem de execução do plano).

---

## 7. Critérios de aceite

1. JSON válido em 20 de 20 chamadas do teste de fumaça de geração (passo 7).
2. Embedding de 100 textos em menos de 30 segundos, todos com 1024 posições (passo 7).
3. Um esquema propositalmente impossível de satisfazer produz `FalhaJsonInvalido` e uma linha nova em `fila_revisao` com o erro registrado (passo 7).
4. O teste do passo 6 confirma que `think: false` está no corpo de toda chamada a `/api/generate` — sem depender do Ollama estar no ar.
5. `cosseno` e `centroide` cobertos pelos casos do passo 5, incluindo os dois casos de borda (vetor nulo, lista vazia).
6. `container.llm()` não levanta mais `NotImplementedError`; chamado duas vezes no mesmo processo, devolve o mesmo objeto (cache).
7. `scripts/verificar.sh` verde nos testes que não dependem do Ollama estar no ar; os três testes de fumaça do passo 7 rodados manualmente ao menos uma vez com o Ollama real, com resultado relatado.

---

## 8. Riscos e como reverter

| Risco | Controle |
|---|---|
| Teste de fumaça quebra `scripts/verificar.sh` sempre que o Ollama não está rodando, confundindo Sidarta sobre o que falhou | passo 7: ausência de Ollama vira "pulado com motivo", nunca erro de conexão cru |
| Ollama muda o formato de erro de JSON entre versões e a validação para de disparar a fila de revisão | a validação é feita pelo Pydantic sobre o texto já recebido, não depende do formato de erro do Ollama |
| `embeddar` devolve vetor de dimensão diferente de 1024 por engano de modelo (ex.: perfil trocado sem querer) | conferência explícita de tamanho antes de devolver, no passo 3 |
| `fila_revisao` cresce sem que ninguém a leia | fora de escopo deste brief; fica registrado como dívida em `docs/PLAN.md` — um comando de leitura da fila é trabalho de brief futuro, só quando houver conteúdo real acumulado |
| Reverter | `agente_nw/nucleo/llm.py`, `agente_nw/nucleo/vetores.py` e `queries/fila_revisao.py` são arquivos novos — apagar os três desfaz o brief. A única alteração em arquivo existente é `container.llm()`, que volta a `raise NotImplementedError("brief 003")` |

---

## 9. Relatório final obrigatório

Preencher o bloco da seção 8 de `AGENTS.md` (já atualizado: a linha de testes virou "Script de verificação", porque a suíte não roda dentro da sessão do executor — só é escrita e mantida por ele). Sem esse bloco preenchido, o brief não está concluído.
