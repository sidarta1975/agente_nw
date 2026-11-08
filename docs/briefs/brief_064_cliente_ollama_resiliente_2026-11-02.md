# Brief 064 — Cliente Ollama resiliente, reproduzível e único no console

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Conjunto:** camada_de_ia (064, 065 e 066 — um conjunto coerente, pode ser construído num worktree só e mesclado à `main` quando os três estiverem prontos)
**Arquivos-alvo:** `agente_nw/nucleo/llm.py`, `config/container.py`, `agente_nw/console/app.py` (linhas 97, 132 e 171 — as três construções de `ClienteOllama`), `config/llm_routing.yaml`, `agente_nw/nucleo/modelos/configuracao.py`, `tests/test_llm_resiliente.py` (novo), `docs/docs/doc_064_cliente_ollama_resiliente_2026-11-02.md`, `logs/commit_064.txt`, `logs/arquivos_064.txt`
**Seções a ler:** ARQUITETURA §8 (camada de LLM); no PLAN, as armadilhas 1, 7, 17, 21, 22 e 23; `agente_nw/nucleo/llm.py` e `config/container.py` inteiros; `agente_nw/console/app.py`, as três funções que constroem `ClienteOllama` (`_cliente_llm`, a função dentro de `_dependencias` e a do `conn_fundo`)
**Modelo:** Sonnet
**Esforço:** baixo
**Teste de aceite:** `tests/test_llm_resiliente.py`
**Depende de:** nada — é o primeiro do conjunto `camada_de_ia`
**Data:** 2026-11-02

---

## 1. Objetivo em uma frase

Nenhuma chamada ao modelo local se perde por indisponibilidade transitória do Ollama, toda geração passa a ser reproduzível, e o console — a interface principal do produto — para de abrir uma conexão nova a cada chamada.

---

## 2. Decisões

**2.1. Backoff para falha de transporte.** Hoje `_chamar_generate` só trata o status 500 com "token repeat limit" (geração degenerada); qualquer outro erro — conexão recusada, timeout de rede, 429, 503 — sobe pelo `raise_for_status()` e `gerar_json` não o captura (seu `except` só cobre `JSONDecodeError`, `ValidationError` e `_GeracaoDegenerada`), derrubando a operação inteira. Passa a existir uma segunda camada de nova tentativa, só para esses erros de transporte: backoff de 2, 4, 8 e 16 segundos (4 tentativas). A inclusão do erro de conexão é deliberada — o Ollama é local, compartilhado com os outros projetos do computador, e pode estar carregando ou descarregando um modelo no momento exato da chamada. A nova tentativa por temperatura que já existe (`nova_tentativa`, 1 tentativa extra a 0.1) continua exatamente como está e passa a contar **só falha de conteúdo** — as duas camadas não se misturam: transporte tenta de novo com backoff; conteúdo tenta de novo com temperatura mais baixa.

**2.2. Seed fixo.** `options` ganha `seed: 42` em toda chamada a `/api/generate`, alinhado com os outros projetos que dividem o mesmo servidor Ollama. Não muda `embeddar` (não tem o conceito de seed).

**2.3. Teto de tokens de saída.** Cada tarefa em `config/llm_routing.yaml` ganha um campo `num_predict` (nome do parâmetro do Ollama); `TarefaRoteamento` valida que é um inteiro positivo. Hoje não existe teto nenhum — é por isso que a classe `_GeracaoDegenerada` existe: ela trata o sintoma (o Ollama aborta sozinho ao entrar em loop) depois que a geração já rodou tempo demais. O teto não substitui essa classe — continua existindo para quando ela falhar mesmo com teto — mas reduz a frequência com que isso acontece.

**2.4. Um cliente HTTP só, para todo o console — não só para o terminal.** `config/container.py` já tem uma fábrica única e guardada em cache (`http()`, `llm()`) — mas hoje só o caminho do terminal (`cli.py`) passa por ela. O console (`agente_nw/console/app.py`) nunca usa essa fábrica: ele mesmo escreve `httpx.Client(timeout=120.0)` direto, em três pontos que constroem `ClienteOllama` — dentro de `_cliente_llm` (linha 97), dentro da função que `_dependencias` monta como `fabrica_llm` (linha 132) e na conexão de fundo `conn_fundo` (linha 171) — cada um abrindo conexão nova a cada chamada, sem o backoff dos itens 2.1 a 2.3. Os três passam a construir o `ClienteOllama` a partir da mesma fábrica de `container.py`. O timeout dessa fábrica sobe de 120 para 600 segundos: o perfil `pro48` usa um modelo de 14B, que pode levar mais tempo numa tarefa longa do que o Air com o modelo de 4B, e 120 segundos já se mostrou curto o bastante para justificar o teto de tokens do item 2.3.
Dois outros pontos do mesmo arquivo (linha 138, o `fabrica_http` de `_dependencias`, e linha 691, dentro da rota que chama `consulta_mod.preparar`) também criam `httpx.Client(timeout=120.0)` — mas são o cliente usado para buscar notícia e página (coleta), não para falar com o Ollama. Cada requisição de coleta já tem seu próprio limite de 15 segundos (`coleta/rss/leitor.py`), então esses dois pontos ficam como estão, fora deste brief.

---

## 3. Testes (escritos antes do código)

- `tests/test_llm_resiliente.py`:
  - um servidor Ollama simulado que responde 503 e depois 200 → `gerar_json` conclui com sucesso, uma falha de transporte contabilizada no log de chamadas (não entra na contagem de `nova_tentativa` por temperatura);
  - erro de conexão (sem resposta) nas três primeiras chamadas e sucesso na quarta → conclui, respeitando o backoff (medir que o teste não leva menos que a soma dos intervalos, com os sonos mockados para não deixar o teste lento);
  - as quatro tentativas de transporte se esgotam → `FalhaJsonInvalido`/caminho de `fila_revisao`, igual ao que já acontece hoje para falha de conteúdo esgotada;
  - o corpo da requisição a `/api/generate` contém `seed: 42` e o `num_predict` da tarefa, lido de `llm_routing.yaml`;
  - falha de conteúdo (JSON inválido) continua tentando de novo só com a temperatura de `nova_tentativa`, sem acionar o backoff de transporte.
- Inspeção (não precisa de teste automatizado, cabe no relatório): `grep -n "httpx.Client(timeout" agente_nw/console/app.py` mostra só as linhas 138 e 691 (coleta); as três de inferência somem, substituídas pela chamada à fábrica de `container.py`.
- O Ollama é sempre simulado; nenhum teste chama o servidor real.

---

## 4. Fora de escopo

- As linhas 138 e 691 de `console/app.py` (cliente de coleta) — já têm seu próprio limite por chamada.
- Proveniência (modelo, perfil, versão de prompt por registro) — brief 066, que depende deste.
- Qualquer mudança no texto dos prompts.

---

## 5. Passos e aceite

Executar com `/executar 064`. Aceite: testes da seção 3 verdes, gate verde, commit e push pelo executor.

Sem pendência de teste real para Sidarta neste brief — o comportamento só aparece sob falha transitória do Ollama, que não se provoca de propósito; a prova é toda nos testes simulados da seção 3.
