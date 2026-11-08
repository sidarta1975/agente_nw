# Brief 075 — Clientes de API: Anthropic, Gemini e OpenAI, com a mesma forma do cliente Ollama

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Conjunto:** ia_api (074, 075 e 076 — este é o segundo; depende do 074)
**Arquivos-alvo:** `agente_nw/nucleo/llm.py` (três classes novas), `tests/test_llm_api.py` (novo)
**Seções a ler:** o 074 já executado (classe `_ClienteLLMBase` e o método abstrato `_chamar`); `agente_nw/nucleo/llm.py` inteiro, como ficou depois do 074; `docs/ARQUITETURA.md` §8; `tests/test_llm_resiliente.py` (para repetir o mesmo estilo de teste com `httpx.MockTransport`, agora contra cada provedor novo)
**Modelo:** Opus — três integrações externas novas, cada uma com seu jeito de forçar formato de saída; um engano aqui é dado real indo para o provedor errado ou chegando malformado
**Esforço:** alto
**Teste de aceite:** `tests/test_llm_api.py`
**Depende de:** brief 074 (`_ClienteLLMBase` e `_chamar` com o parâmetro `esquema`)
**Data:** 2026-11-03

---

## 1. Objetivo em uma frase

Três classes novas em `nucleo/llm.py` — `ClienteAnthropic`, `ClienteGemini`, `ClienteOpenAI` — cada uma falando com a API REST do seu provedor por `httpx` (sem SDK novo: o projeto já só usa `httpx` para o Ollama), com a mesma forma pública que `ClienteOllama` já tem (`gerar_json`, `embeddar`, `modelo_embedding`, `proveniencia`), para que nenhum dos módulos que já usam um "cliente_llm" precise saber qual provedor está por trás.

---

## 2. Por que a forma pública tem que ficar idêntica (achado no código)

Nenhum módulo além de `config/container.py`, `agente_nw/console/app.py` e `agente_nw/perfil/extrator.py` importa `ClienteOllama` pelo nome — todo o resto (`agente_nw/nucleo/relevancia/*.py`, `agente_nw/nucleo/redacao.py`, `agente_nw/nucleo/agrupamento/agrupador.py`, `agente_nw/perfil/*.py`, `agente_nw/nucleo/pedido.py`) já declara, cada um no seu arquivo, um `Protocol` local só com os métodos que usa (`gerar_json`, `.proveniencia(...)`, `.modelo_embedding`). Isso significa que qualquer classe nova com esses mesmos métodos já serve para todo o resto do produto sem tocar nenhum desses arquivos — é por isso que este brief só muda `nucleo/llm.py` e o teste novo.

---

## 3. Decisões

**3.1. Cada provedor é forçado a devolver JSON no formato do esquema pela via nativa dele — não pelo texto do prompt.** Diferente do Ollama (que usa `format: "json"`, um sinal genérico, e confia no texto do prompt para descrever a forma esperada), as três APIs têm mecanismo próprio para **forçar** a saída a bater com um esquema:

- **Anthropic** (`POST https://api.anthropic.com/v1/messages`, headers `x-api-key` e `anthropic-version: 2023-06-01`): uma `tool` só, forçada por `tool_choice`, com `input_schema = esquema.model_json_schema()`. A resposta vem no bloco de conteúdo `type: "tool_use"`, campo `input` — já é o dict validado contra o schema, não precisa de `json.loads` (mas `_chamar` continua devolvendo `str`; serializar esse `input` de volta para texto com `json.dumps` antes de devolver, para a base do 074 fazer `json.loads` de novo sem precisar saber que veio de um dict).
- **OpenAI** (`POST https://api.openai.com/v1/chat/completions`, header `Authorization: Bearer <chave>`): `response_format: {"type": "json_schema", "json_schema": {"name": esquema.__name__, "schema": esquema.model_json_schema(), "strict": true}}`. A resposta vem em `choices[0].message.content`, já uma string JSON — devolver direto.
- **Gemini** (`POST https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key=<chave>`): `generationConfig.response_mime_type: "application/json"` e `generationConfig.response_schema: esquema.model_json_schema()`. A resposta vem em `candidates[0].content.parts[0].text`, string JSON — devolver direto.
  - Risco conhecido, sem solução de código antecipada: o subconjunto de JSON Schema que o Gemini aceita em `response_schema` é mais estreito que o que o Pydantic gera (`$defs`, `anyOf` com `null` para campo opcional, etc. podem não ser aceitos, respondendo 400). Se isso acontecer na prática, a saída é manter `response_mime_type: "application/json"` **sem** `response_schema` (ainda força JSON, só não trava a forma) e confiar na mesma validação por `model_validate` que já existe depois — igual ao Ollama. Documentar essa queda no relatório do brief se for necessário; não é motivo para não entregar.

**3.2. `imagens` (base64) entram no formato de cada provedor.** `tarefa` `descrever_imagem` manda `imagens` não vazio; cada cliente converte para o formato de conteúdo multimodal do seu provedor (Anthropic: bloco `{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": ...}}`; OpenAI: `{"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}}`; Gemini: `{"inlineData": {"mimeType": "image/jpeg", "data": ...}}`). Assumir `image/jpeg` como `media_type`/`mimeType` (é o que a extensão do Chrome já entrega, conferir em `coleta/capturas/leitor.py` antes de aceitar isso como certo).

**3.3. `num_predict` da tarefa vira o limite de tokens de saída de cada provedor; `num_ctx` e `think` não valem para eles.** `num_predict` → `max_tokens` (Anthropic e OpenAI) / `maxOutputTokens` (Gemini). `num_ctx` é um parâmetro do servidor Ollama (tamanho da janela de contexto que ele aloca) — as três APIs administram isso sozinhas, não tem para onde mandar, então os três `_chamar` **ignoram** `tarefa.num_ctx`. `think` já é sempre `false` no YAML (AGENTS §3) e nenhum dos três liga modo de raciocínio estendido — não é pedido aqui, mesmo a Anthropic tendo essa opção: ligar "thinking" mudaria o formato da resposta e nenhuma tarefa deste produto precisa disso.

**3.4. Falha de transporte (rede, HTTP 4xx/5xx) sobe para a base exatamente como já sobe do Ollama.** Cada `_chamar` usa `self._http.post(...)` e `resposta.raise_for_status()` sem capturar nada além do que já é tratado por fora, em `_chamar_com_backoff` (do 074) — `httpx.HTTPStatusError`/`httpx.RequestError` continuam acionando o mesmo backoff e, esgotado, a mesma `fila_revisao`. Nenhum dos três provedores tem um equivalente de `_GeracaoDegenerada` conhecido — não criar um; se um dia aparecer um caso real, é brief novo com o caso em mãos, não suposição agora.

**3.5. `embeddar`/`modelo_embedding` por composição com um `ClienteOllama` injetado — nunca reimplementados.** Cada uma das três classes novas recebe, no construtor, um `cliente_embeddings: ClienteOllama` (a mesma instância que o `container.py`/`console/app.py` já cria para o perfil ativo) e só repassa: `modelo_embedding` devolve `self._cliente_embeddings.modelo_embedding`; `embeddar(textos)` devolve `self._cliente_embeddings.embeddar(textos)`. Dois motivos, nenhum deles é falta de tempo:
  - A Anthropic **não tem** endpoint de embeddings — não existe "chamar a Anthropic para embeddar" para implementar.
  - Trocar o modelo de embedding trocaria silenciosamente `modelo_embedding` de todo centróide gravado (`vetor_assunto`, `vetor_tema`, perfis) — o brief 066 já trata um embedding de modelo diferente como **ausente** na leitura (`WHERE ... modelo_embedding = ?`). Usar a API para gerar embeddings, mesmo que a OpenAI e a Gemini tenham API própria para isso, apagaria de fato (por descasamento, não por `DELETE`) todo o histórico de perfil/tema já calculado localmente. Nenhum brief deveria fazer isso sem ser pedido de propósito.
  - Consequência prática, dita sem rodeio: **o Ollama continua precisando estar de pé mesmo com uma chave de API cadastrada** — só a geração de texto estruturado (`gerar_json`) vai para a API; embeddings continuam 100% locais sempre. Isso é diferente da frase "não usar LLM offline" como foi pedida; o brief 076 deixa essa fronteira escrita no AGENTS.

**3.6. Chamadas às três APIs, de resto, iguais entre si no que a base já pede.** `temperature` vem da mesma `TarefaRoteamento`/`NovaTentativaRoteamento` que o Ollama já usa — a mesma tabela de temperaturas por tarefa do `llm_routing.yaml` continua valendo (não existe um `llm_routing.yaml` separado por provedor; é decisão deliberada, evita manter quatro tabelas de doze tarefas cada uma).

---

## 4. Testes (escritos antes do código)

Novo `tests/test_llm_api.py`, no mesmo estilo de `tests/test_llm_resiliente.py` (`httpx.MockTransport`, sem rede real, sem chave real — qualquer string serve de chave nos testes):

- `ClienteAnthropic.gerar_json`: o handler fake confere que a requisição tem `tool_choice` forçando a tool certa e `input_schema` batendo com `esquema.model_json_schema()`; a resposta fake devolve um bloco `tool_use` com `input` já no formato esperado; o resultado de `gerar_json` é a instância validada do esquema.
- `ClienteOpenAI.gerar_json`: o handler confere `response_format.json_schema.schema` batendo com o esquema; a resposta fake devolve `choices[0].message.content` como string JSON; mesmo resultado esperado.
- `ClienteGemini.gerar_json`: o handler confere `generationConfig.response_mime_type` e `response_schema`; a resposta fake devolve `candidates[0].content.parts[0].text` como string JSON; mesmo resultado.
- Para cada um dos três: um teste com imagem (`imagens=["base64fake"]`) confirmando que o corpo da requisição leva o bloco de imagem no formato daquele provedor.
- Para cada um dos três: erro de transporte (handler fake devolve 500 de propósito) aciona o mesmo backoff que `test_llm_resiliente.py` já teve (reaproveitar o fixture `_sem_sono` de lá, ou equivalente) e, esgotado, levanta `FalhaJsonInvalido` com uma entrada em `fila_revisao` — prova de que a base do 074 está sendo usada de verdade, não uma cópia.
- `embeddar`/`modelo_embedding` de cada uma das três: um `ClienteOllama` fake (ou real, com `MockTransport`, como já existe) injetado como `cliente_embeddings`; confirmar que `embeddar`/`modelo_embedding` só repassam, sem nenhuma chamada às URLs da Anthropic/OpenAI/Gemini.
- Não testar com rede real nem com chave real de nenhum provedor — nenhum destes testes pode exigir variável de ambiente nem acesso à internet para passar.

---

## 5. Fora de escopo

- Decidir qual provedor é usado quando — isso é seleção, do brief 076.
- Qualquer mudança em `config/local.yaml`, `config/container.py` ou `agente_nw/console/app.py` — brief 076.
- Resolver de fato o risco do item 3.1 (schema do Gemini) além da queda documentada — só se acontecer de verdade, com o relatório descrevendo.
- Mudar `ClienteOllama` ou `_ClienteLLMBase` (já fechados pelo 074) além do que a composição do item 3.5 exige.

---

## 6. Passos e aceite

Executar com `/executar 075`. Aceite: `tests/test_llm_api.py` verde, gate verde, commit e push pelo executor.

Pendência real para Sidarta, depois do 076 (quando a seleção por chave estiver ligada): testar de verdade com uma chave sua de cada provedor que quiser usar — os testes deste brief só provam a forma da chamada, nunca uma resposta real do provedor.
