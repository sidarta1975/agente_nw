# Brief 077 — Consultar o porteiro antes de cada lote que usa o Ollama local

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Conjunto:** nenhum — brief único
**Arquivos-alvo:** `agente_nw/nucleo/llm.py` (classe `ClienteOllama`: construtor, `_chamar`, `embeddar`, funções novas de módulo), `config/container.py` (`selecionar_cliente_llm`, `llm()`), `agente_nw/console/app.py` (as três construções de cliente: `_cliente_llm`, `fabrica_llm` dentro de `_dependencias`, a de `_processar_whatsapp_em_fundo`), `tests/test_porteiro.py` (novo), `AGENTS.md` (§3, uma linha nova), `docs/ARQUITETURA.md` §8 (um parágrafo novo), `docs/docs/doc_077_integracao_com_o_porteiro_2026-11-06.md`, `logs/commit_077.txt`, `logs/arquivos_077.txt`
**Seções a ler:** `~/github/porteiro_local/docs/INTEGRACAO.md` inteiro — em especial §4 a 9, como Sidarta pediu; `agente_nw/nucleo/llm.py` inteiro, como ficou depois dos briefs 074-076 (`_ClienteLLMBase`, `ClienteOllama`, `_ClienteApiBase` e os três clientes de API); `config/container.py` inteiro, em especial `selecionar_cliente_llm` e `llm()`; as três construções de `agente_nw/console/app.py` (mesmas três dos briefs 064/076); `tests/test_llm_resiliente.py` (a fixture `_sem_sono`, para testar a espera sem dormir de verdade); `AGENTS.md` §3
**Modelo:** Opus — toca o único cliente usado pelas 15 tarefas de LLM do produto, com um subprocesso, timeouts e um laço de espera; um engano aqui trava um lote por até 15 minutos ou faz um teste dormir de verdade
**Esforço:** alto
**Teste de aceite:** `tests/test_porteiro.py`
**Depende de:** briefs 074, 075 e 076 (já executados — `_ClienteLLMBase`, os clientes de API e `selecionar_cliente_llm`)
**Data:** 2026-11-06

---

## 1. Objetivo em uma frase

Antes de carregar qualquer modelo no Ollama local, o projeto consulta uma vez o `porteiro` (o administrador do Ollama compartilhado da máquina, `~/github/porteiro_local`); se ele disser que não cabe, espera até 15 minutos e roda assim mesmo, registrando no log; se ele falhar ou não existir, o projeto roda exatamente como hoje.

---

## 2. Achados no código e no documento (conferidos, não supostos)

**2.1. A porta deste projeto é `11435`, já documentada.** `config/local.yaml:4` tem `ollama_url: http://127.0.0.1:11435`; `AGENTS.md §3` já diz que essa é "a instância compartilhada já existente..., mantida pelo `cervello`". O `INTEGRACAO.md §2` lista `11435` como a porta do servidor fixo (`cervello`, `sergio`) e confirma que o agente_nw "ainda não tem porta confirmada" no mapa dele — a porta já está decidida do lado do agente_nw, só falta o `porteiro` saber que também é consultado daquela porta. **Não é pedido, e não se faz aqui, mudar `ollama_url` nem cadastrar o agente_nw no mapa do `porteiro`** (isso é configuração do lado do `porteiro`, fora deste repositório).

**2.2. Existe só um lugar que constrói o `ClienteOllama` para os lotes, e três para o console interativo — já separados pelo brief 076.** `config/container.py::selecionar_cliente_llm` (linha 106) é a única função que constrói `ClienteOllama`; `config/container.py::llm()` (linha 140, `@functools.lru_cache(maxsize=1)`) é a única chamada a ela usada por `agente_nw/cli.py` — confirmado por `grep -n "llm()" agente_nw/cli.py`: todo comando de lote (`processar-fila`, `agrupar`, `calibrar-agrupamento`, `qualificar`, `cartao`, `cruzar`, `preparar`, `pedir`, `ler-rede-social`) chama o mesmo `llm()` memoizado, uma vez por processo. `agente_nw/console/app.py` tem suas três próprias chamadas a `selecionar_cliente_llm` (`_cliente_llm`, `fabrica_llm` em `_dependencias`, e dentro de `_processar_whatsapp_em_fundo`) — essas três servem o console Flask, de uso interativo (uma pessoa esperando, `INTEGRACAO.md §3`), nunca um lote agendado.

**2.3. Cada comando de lote da CLI já É o "lote" do `INTEGRACAO.md §3`.** Cada `agente_nw <comando>` é um processo que roda do início ao fim e termina — não um daemon. "Antes de começar um lote... consultar uma vez" cai exatamente no início de cada processo assim, não em cada item dentro dele. Como todos passam pelo mesmo `llm()` memoizado (2.2), um único ponto, dentro do próprio `ClienteOllama`, consultado uma vez por modelo e por instância, cobre todo comando de lote sem precisar mapear qual tarefa cada comando chama.

**2.4. O projeto não tem um logger genérico — dois mecanismos já existem, e o do porteiro bate com um deles.** `grep -rn "import logging"` não encontra nada no projeto. Avisos de produto vão para o terminal com `print(f"AVISO: ...")` (`agente_nw/cli.py`, várias linhas) — mas isso é da camada de apresentação da CLI; `agente_nw/nucleo/llm.py` não imprime nada hoje. O projeto já tem um log estruturado, `dados/logs/chamadas_llm.jsonl` (`caminho_log_chamadas_llm()`, escrito por `_registrar_log_chamada` em `_ClienteLLMBase`) — `ClienteOllama` já guarda `self._caminho_log` para ele. É esse arquivo, e não um novo, que recebe o aviso do `porteiro`: mesma pasta, mesmo padrão de escrita (JSONL, `try/except` que nunca derruba a chamada), vale tanto para a CLI quanto para o console, sem imprimir nada em lugar nenhum.

**2.5. `httpx` já dá a porta sem reimplementar o parser que `cli.py::_porta_de` já tem.** `httpx.URL(self._ollama_url).port` devolve `11435` a partir da própria `ollama_url` que `ClienteOllama` já recebe — evita duplicar `_porta_de` (que é privada de `cli.py`, outra camada) e garante que a porta do `porteiro` nunca diverge da porta real do projeto (item 3.6 abaixo).

**2.6. `INTEGRACAO.md §9` já dá a referência do laço de espera — 16 consultas, não 15.** O exemplo em Python do próprio documento faz `for _ in range(16)`, com `time.sleep(60)` *depois* de cada consulta que devolver código `1`: a primeira consulta é imediata, e são até 15 esperas de 60s depois dela — 16 consultas no total, cobrindo os "até 15 minutos" pedidos. Este brief segue esse número exatamente.

---

## 3. Decisões

**3.1. A consulta mora dentro de `ClienteOllama`, nos dois métodos que realmente carregam um modelo — `_chamar` e `embeddar` — não em cada comando da CLI.** Antes do `self._http.post(...)` de cada um, uma chamada a um novo método `self._verificar_porteiro_antes_de_carregar(modelo)`. Nenhum dos quinze comandos da CLI precisa saber do `porteiro`; a cobertura é automática, pelo motivo do achado 2.3. Os três clientes de API (`ClienteAnthropic`/`Gemini`/`OpenAI`) nunca tocam o Ollama para gerar texto — nenhuma consulta para eles —, mas `embeddar` deles é repasse ao `ClienteOllama` injetado (`_ClienteApiBase`, brief 075, item 3.5), então a consulta acontece automaticamente para o modelo de embedding, mesmo com um provedor de API cadastrado. Isso está certo: embeddings continuam sempre no Ollama local (brief 075), e é exatamente o Ollama local que o `porteiro` administra.

**3.2. Uma consulta por modelo, por instância de `ClienteOllama` — nunca por item.** Novo atributo `self._modelos_verificados_porteiro: set[str]` no `__init__`, vazio a cada novo cliente (cada processo de lote cria o seu, via `llm()`). `_verificar_porteiro_antes_de_carregar(modelo)` sai sem fazer nada se `modelo` já estiver no conjunto; senão, adiciona e consulta. Um comando que chama várias tarefas com modelos diferentes (ex.: extração usa um modelo, descrição de imagem usa outro) consulta cada modelo uma vez; um comando que chama a mesma tarefa centenas de vezes (ex.: `qualificar` sobre centenas de contatos) consulta uma vez só — exatamente "uma vez por lote" do jeito que o lote da CLI já funciona (achado 2.3), sem precisar de um conceito novo de "início do lote".

**3.3. Dois modos, escolhidos por quem constrói o cliente — `lote` (padrão) e `interativo` — porque a regra de espera de 15 minutos não pode valer para uma pessoa esperando no console.** Novo parâmetro `modo_porteiro: Literal["lote", "interativo"] = "lote"` em `ClienteOllama.__init__` e em `selecionar_cliente_llm` (repassado ao `ClienteOllama` que ela sempre constrói, passo 1 do brief 076). `config/container.py::llm()` não passa o parâmetro — fica no padrão `"lote"`, correto para todo comando da CLI (achado 2.2). As três construções de `agente_nw/console/app.py` passam `modo_porteiro="interativo"` explicitamente — são as únicas que servem o console Flask, de uso interativo segundo o próprio `INTEGRACAO.md §3` ("Opcional. Se consultar, nunca espere: use a resposta só para avisar").
  - **Modo `lote`:** consulta; se `codigo_de_saida == 1`, espera 60s e consulta de novo, até 16 consultas no total (achado 2.6); ao final, se o código ainda não for `0`, roda assim mesmo e registra o aviso no log (item 3.5). Nunca levanta exceção, nunca impede a chamada.
  - **Modo `interativo`:** uma consulta só, nunca espera; se o código não for `0`, registra o aviso no log; roda assim mesmo, sempre.
  - Em nenhum dos dois modos o `porteiro` jamais bloqueia a chamada em definitivo — ele só atrasa o modo `lote` por até 15 minutos; o resultado final é sempre rodar (`INTEGRACAO.md §6`: "um lote que nunca roda é pior que um lote que roda devagar").

**3.4. A chamada ao `porteiro` é um subprocesso com caminho fixo e completo, exatamente como o documento pede — nunca `sys.executable`, nunca um `porteiro` resolvido pelo `PATH`.** Duas constantes novas em `agente_nw/nucleo/llm.py`:
```python
_PORTEIRO_PYTHON = "/opt/homebrew/bin/python3"
_PORTEIRO_BIN = "/Users/sidarta48/github/porteiro_local/bin/porteiro"
```
(`INTEGRACAO.md §4.1`: "Sempre use o caminho completo, com o Python na frente" — um `LaunchAgent` ou ambiente virtual pode não ver `~/.local/bin` nem escolher um Python ≥ 3.11). Uma função nova, `_consultar_porteiro(modelo: str, porta: int) -> dict[str, object] | None`, roda:
```
subprocess.run([_PORTEIRO_PYTHON, _PORTEIRO_BIN, "cabe", modelo, "--porta", str(porta), "--json"],
               capture_output=True, text=True, timeout=30.0)
```
e devolve `None` — nunca levanta — em **qualquer** destas situações (`INTEGRACAO.md §6`, linha do código `3`): `OSError` (programa não encontrado), `subprocess.TimeoutExpired` (mais de 30s), `json.JSONDecodeError` (JSON ilegível), ou JSON que não é um dict com a chave `"codigo_de_saida"`. `None` é tratado pelo chamador exatamente como código `3`: "seguir como se o `porteiro` não existisse".

**3.5. O aviso vai para `chamadas_llm.jsonl` (achado 2.4), só quando há algo a avisar — nunca para o código `0`.** Novo método `_registrar_aviso_porteiro(modelo, resposta)` em `ClienteOllama`, no mesmo padrão `try/except Exception: pass` de `_registrar_log_chamada`, escrevendo uma linha JSON com `{"porteiro": True, "modelo", "porta", "quando", "codigo_de_saida", "razao", "aviso"}` no mesmo arquivo (`self._caminho_log`). `aviso` é uma frase fixa por código — `1` → "rodou com memória cheia segundo o porteiro" (texto do próprio `INTEGRACAO.md §6`); `2` → "servidor Ollama da porta consultada não respondeu"; `3` ou `None` (porteiro ausente/falhou) → "porteiro indisponível ou com erro, seguiu como se não existisse". Chamado ao final de `_verificar_porteiro_antes_de_carregar` só se o código final não for `0` — um lote que sempre recebe `0` nunca escreve uma linha de aviso.

**3.6. A porta vem de `self._ollama_url`, nunca de uma constante nova — nada aqui muda modelo ou porta do projeto (pedido explícito de Sidarta, e `INTEGRACAO.md §8`).** `porta = httpx.URL(self._ollama_url).port` (achado 2.5); se vier `None` (não é o caso hoje, `ollama_url` sempre tem porta explícita), `_verificar_porteiro_antes_de_carregar` sai sem consultar — degrada como se o `porteiro` não existisse, nunca inventa uma porta. O `porteiro` **nunca** decide ou troca o modelo: o `modelo` passado é sempre `tarefa.modelo` (geração) ou `perfil.embeddings.modelo` (embeddings), o mesmo que já ia para o Ollama antes deste brief — `_verificar_porteiro_antes_de_carregar` só pergunta e loga, nunca retorna um modelo diferente para `_chamar`/`embeddar` usarem.

**3.7. `AGENTS.md §3` ganha uma linha, depois da linha de `ia_api` (brief 076):**
```markdown
- Antes de carregar um modelo no Ollama local (geração ou embeddings), o projeto consulta o `porteiro` (`~/github/porteiro_local`, uma vez por modelo por processo) — se não couber, espera até 15 min e roda assim mesmo; se o `porteiro` falhar ou não existir, roda como sempre. Nunca usado para trocar modelo, porta, ou para subir/parar o Ollama.
```

**3.8. `docs/ARQUITETURA.md §8` ganha um parágrafo novo, ao final da seção**, descrevendo o mecanismo (consulta por modelo, os dois modos, o aviso em `chamadas_llm.jsonl`, a degradação) sem reescrever o que já existe sobre Ollama/perfis/provedores de API.

---

## 4. Testes (escritos antes do código)

Novo `tests/test_porteiro.py`, com `monkeypatch` em `subprocess.run` (nunca um `porteiro` real nem rede) e a mesma ideia da fixture `_sem_sono` de `tests/test_llm_resiliente.py` para não dormir de verdade:

- `_consultar_porteiro`: `subprocess.run` fake devolvendo um JSON válido com `codigo_de_saida` → dict devolvido igual ao JSON. `subprocess.run` levantando `FileNotFoundError`, `subprocess.TimeoutExpired`, devolvendo `stdout` que não é JSON, ou JSON sem a chave `"codigo_de_saida"` → `None` nos quatro casos.
- Modo `lote`, resposta código `0` → chama o Ollama normalmente; nenhuma linha nova em `chamadas_llm.jsonl` além da já existente de `_registrar_log_chamada`; `time.sleep` não chamado para o `porteiro`.
- Modo `lote`, código `1` em todas as 16 consultas → `time.sleep(60.0)` chamado 15 vezes (confirma o número do achado 2.6); ao final, a chamada ao Ollama acontece do mesmo jeito; uma linha de aviso com `codigo_de_saida: 1` em `chamadas_llm.jsonl`.
- Modo `lote`, código `1` nas duas primeiras consultas e `0` na terceira → só 2 esperas de 60s; chamada ao Ollama acontece; **nenhuma** linha de aviso (o código final foi `0`).
- Modo `lote`, `porteiro` ausente (`_consultar_porteiro` devolve `None`) → nenhuma espera; chamada ao Ollama acontece; uma linha de aviso "porteiro indisponível".
- Modo `interativo`, código `1` → zero chamadas a `time.sleep`; uma consulta só; chamada ao Ollama acontece; uma linha de aviso.
- Memoização: duas chamadas a `gerar_json` com a mesma tarefa (mesmo modelo) no mesmo `ClienteOllama` → `subprocess.run` (ou o mock que o substitui) chamado uma vez só. Duas tarefas com modelos diferentes → duas consultas, uma por modelo.
- `embeddar` também passa pela consulta (modelo de embedding), com a mesma memoização; e um `ClienteAnthropic`/`ClienteAPI` qualquer com um `ClienteOllama` injetado como `cliente_embeddings` dispara a consulta ao chamar `embeddar`, provando que a composição do brief 075 carrega o `porteiro` de graça.
- `selecionar_cliente_llm` aceita `modo_porteiro` e repassa ao `ClienteOllama` construído (teste simples, no estilo de `test_selecao_provedor.py`).
- Não regressão de camada (grep/leitura, estilo `test_selecao_provedor.py:209-210`): as três construções de `agente_nw/console/app.py` passam `modo_porteiro="interativo"`; `config/container.py::llm()` não passa `modo_porteiro` (fica no padrão `"lote"`).
- Nenhum teste chama o `porteiro` real, nem precisa dele instalado para passar.

---

## 5. Fora de escopo

- Cadastrar o agente_nw no mapa de portas do `porteiro` (`INTEGRACAO.md §2`) — é configuração do lado do `porteiro_local`, outro repositório; fora do fluxo de briefs deste projeto.
- Qualquer mudança em `ollama_url`, em qual modelo cada tarefa usa, ou em `config/llm_routing.yaml` — pedido explícito de Sidarta para não mudar, e o item 3.6 garante isso no código.
- Tornar os caminhos `_PORTEIRO_PYTHON`/`_PORTEIRO_BIN` configuráveis em `config/local.yaml` — não foi pedido; são a mesma convenção fixa que o próprio `INTEGRACAO.md §9/§10` usa nos exemplos dele. Se um dia esses caminhos mudarem nesta máquina, é ajuste de duas constantes, não de um brief novo.
- Qualquer consulta ao `porteiro` dentro de um laço por item — proibido pelo próprio documento (`§8`: "Chamar o porteiro dentro de um laço, item por item") e pela decisão 3.2.
- Usar o `porteiro status` ou qualquer comando além de `cabe` — `§4.1` do documento pede exatamente isso ("Use só o comando `cabe`").
- Mudar o comportamento de `verificar-ambiente` (`_verificar_ollama`, em `cli.py`) — esse já testa se o Ollama está no ar; `INTEGRACAO.md §3` diz explicitamente para não usar o `porteiro` para isso.

---

## 6. Passos e aceite

Executar com `/executar 077`. Aceite: `tests/test_porteiro.py` verde, `tests/test_llm_resiliente.py` e `tests/test_llm_api.py` continuando verdes sem edição de asserção (prova de que nada do comportamento anterior mudou), gate verde, commit e push pelo executor.

Pendência real para Sidarta, só depois do brief no ar: rodar um lote de verdade (ex.: `agente_nw qualificar`) nesta máquina com o `porteiro` instalado e conferir em `dados/logs/chamadas_llm.jsonl` que, se algum dia a memória estiver cheia, aparece a linha `"porteiro": true` com o aviso — e que em uso normal (memória com espaço) nenhuma linha nova aparece.
