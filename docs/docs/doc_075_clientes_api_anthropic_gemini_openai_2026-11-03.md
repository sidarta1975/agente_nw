# Doc 075 — Clientes de API: Anthropic, Gemini e OpenAI

**Brief:** `docs/briefs/brief_075_clientes_api_anthropic_gemini_openai_2026-11-03.md`
**Data:** 2026-11-03

> Executado o brief 075 do conjunto `ia_api` (04:22). O outro arquivo no disco,
> `brief_075_fallback_gemini_e_gpt_2026-11-03.md`, é do desenho de fallback que não foi escolhido —
> ver a lacuna 1 do doc 074.

## O que foi feito

Três classes públicas novas em `agente_nw/nucleo/llm.py`, cada uma falando REST com seu provedor por
`httpx` (sem SDK novo), todas herdando a orquestração do brief 074 e implementando só `_chamar`:

| Classe | Endpoint | Como o esquema é forçado | Onde a resposta é lida |
|---|---|---|---|
| `ClienteAnthropic` | `POST https://api.anthropic.com/v1/messages` | uma tool só, obrigatória por `tool_choice`, com `input_schema = esquema.model_json_schema()` | bloco `content[*].type == "tool_use"`, campo `input`, reserializado com `json.dumps` |
| `ClienteGemini` | `POST .../v1beta/models/{modelo}:generateContent` | `generationConfig.response_mime_type: application/json` + `response_schema` | `candidates[0].content.parts[*].text` |
| `ClienteOpenAI` | `POST https://api.openai.com/v1/chat/completions` | `response_format: {"type": "json_schema", ..., "strict": true}` | `choices[0].message.content` |

### Decisão de implementação: uma base privada `_ClienteApiBase`

O brief fala de "três classes novas" e não diz como organizá-las por dentro. O `__init__` (chave,
modelo, `cliente_embeddings`), a proveniência e os dois repasses de embedding do item 3.5 são
**idênticos** nos três — copiá-los três vezes é exatamente a duplicação que o brief 074 existiu para
acabar. Então: `_ClienteApiBase(_ClienteLLMBase)` guarda essa parte, e cada uma das três classes
públicas tem só o `_chamar` do seu provedor. As três continuam sendo classes públicas com a forma que
o brief pede; a base é privada e nenhum módulo a importa.

### Decisão de implementação: `proveniencia` sobrescrita nos clientes de API

`_ClienteLLMBase.proveniencia` devolve `self._tarefa(nome).modelo`, que é o modelo do Ollama no
`llm_routing.yaml` (`qwen3:4b`/`qwen2.5:14b`). Para um cliente de API isso registraria no
`chamadas_llm.jsonl` um modelo que não atendeu a chamada — e a pendência de aceite do brief 076 é
justamente "confirmar no log que o campo `modelo` registrado é o do provedor de API escolhido, não
mais `qwen3:4b`". `_ClienteApiBase.proveniencia` devolve `self._modelo`. Nada mudou na base (a
sobrescrita vive na subclasse, dentro do arquivo-alvo deste brief), e `gerar_json` continua chamando
`self._tarefa(tarefa_nome)` antes de tudo, então a conferência de tarefa declarada no YAML segue
valendo — tem teste (`test_tarefa_fora_do_perfil_continua_erro_claro`).

### Divergência deliberada do brief: a chave do Gemini vai no header, não em `?key=`

O item 3.1 do brief escreve a URL do Gemini como `...:generateContent?key=<chave>`. **Não foi feito
assim**, por um defeito concreto, não por preferência:

1. `str(httpx.HTTPStatusError)` inclui a URL completa — `Client error '400 Bad Request' for url '...'`.
2. `gerar_json` passa exatamente esse texto para `_ir_para_fila_revisao(tarefa_nome, prompt, str(erro))`.
3. `fila_revisao.inserir` grava o texto no banco.

Logo, com a chave na query string, **o primeiro 4xx do Gemini gravaria a chave de API de Sidarta numa
linha de `fila_revisao`** — e ela ficaria lá. O header `x-goog-api-key` é a forma oficialmente
suportada de autenticar a mesma API e não aparece em nenhuma mensagem de erro. É o AGENTS §4 aplicado
("restrições são estruturais, não procedurais: o que não deve ser visto a jusante é bloqueado na
origem"). Há teste dedicado, `test_gemini_nao_leva_a_chave_na_url`, que força um 500 e confere que a
chave não está nem na URL chamada nem na coluna `erro` do `fila_revisao` gravado.

### Conferência do item 3.2 (`image/jpeg`): a suposição do brief foi mantida, mas ela não é segura

O brief manda assumir `image/jpeg` e "conferir em `coleta/capturas/leitor.py` antes de aceitar isso
como certo". Conferido, e o achado é mais específico do que o brief supôs:

- `extensao/background.js:133` manda o mime **real** de cada imagem: `mime: resposta.headers.get("content-type")`.
- `coleta/capturas/extensao_backend.py:144` o guarda em `ImagemCapturada.mime`.
- `coleta/capturas/imagens.py:61` chama `gerar_json(..., imagens=[imagem.dados_base64])` — **só a
  base64**. O mime real é descartado antes de chegar ao cliente de LLM.

Ou seja: o mime verdadeiro existe no projeto, mas não chega até `_chamar`, porque a assinatura de
`gerar_json` (de `_ClienteLLMBase`, fechada pelo brief 074) só carrega `list[str]`. Então `image/jpeg`
foi mantido, como o brief pede, com a constante `_MEDIA_TYPE_IMAGEM` e o motivo escrito na docstring —
e a consequência (um PNG ou WebP do Instagram declarado como JPEG pode levar 400 de qualquer um dos
três provedores) está registrada como lacuna, porque consertar exige mudar a assinatura de
`gerar_json`, fora do escopo deste brief.

### Risco do item 3.1 (esquema do Gemini) e o mesmo risco na OpenAI

O brief já previa que o `response_schema` do Gemini aceita um subconjunto de JSON Schema mais estreito
que o que o Pydantic gera, com a queda documentada (manter `response_mime_type` e tirar
`response_schema`). Implementado como o brief pede, com o risco em aberto — não aconteceu aqui porque
nenhum teste chama a API real.

Conferindo o mesmo ponto para a OpenAI, o risco é **igual e não estava no brief**:
`response_format.json_schema.strict: true` exige, na API da OpenAI, `additionalProperties: false` em
todo objeto e todos os campos em `required`. `model_json_schema()` do Pydantic não põe
`additionalProperties: false`, e campo com valor padrão (como `descartar: bool = False` de
`RespostaDescricaoImagem`) não entra em `required`. Seguido o brief à letra (`strict: true`, esquema do
Pydantic sem transformação), com o risco registrado como lacuna junto com a mesma queda documentada
(tirar `strict`), porque a alternativa — reescrever o esquema para o dialeto estrito — mudaria a
semântica dos campos opcionais do produto e não foi pedida.

### Resposta 200 malformada é falha de conteúdo, nunca exceção nova

Os três `_chamar` leem a resposta por três funções (`_texto_da_resposta_anthropic`,
`_texto_da_resposta_gemini`, `_texto_da_resposta_openai`) que, diante de uma resposta 200 fora da forma
esperada, devolvem o texto que houver — ou string vazia. Nenhuma levanta exceção própria. O efeito é o
mesmo do Ollama devolvendo texto que não é JSON: `json.loads` falha, entra a nova tentativa por
temperatura e, esgotada, `fila_revisao`. Isso é deliberado: uma `ValueError` nova aqui escaparia de
`gerar_json` sem tratamento, que é exatamente a armadilha que o brief 067 corrigiu. Tem teste
(`test_anthropic_resposta_sem_tool_use_cai_na_fila_revisao_sem_subir_outra_excecao` e os dois
parametrizados de conteúdo inválido).

### O que não foi mandado para as APIs

- `tarefa.num_ctx` — é parâmetro do servidor Ollama; os três testes conferem que a string `num_ctx`
  não aparece em nenhum corpo enviado (item 3.3).
- `think` — sempre `false` no YAML, nenhum dos três liga raciocínio estendido (item 3.3); conferido no
  teste da Anthropic.
- `tarefa.modelo` — o modelo é o único do provedor, vindo do construtor (item 3.6 e fora de escopo do
  076: "um modelo só por provedor").

`num_predict` virou `max_tokens` (Anthropic, OpenAI) e `maxOutputTokens` (Gemini); `temperature` vem da
mesma `TarefaRoteamento`/`nova_tentativa` que o Ollama já usa.

## Testes (escritos antes do código)

`tests/test_llm_api.py`, 23 casos, no estilo de `tests/test_llm_resiliente.py` (`httpx.MockTransport`,
sem rede, sem chave real, com o mesmo fixture `_sem_sono`):

| Caso | Cobre |
|---|---|
| `test_anthropic_forca_o_esquema_por_tool_e_le_o_bloco_tool_use` | URL, `x-api-key`, `anthropic-version`, `input_schema` igual ao `model_json_schema()`, `tool_choice` forçado, `max_tokens`/`temperature`, ausência de `num_ctx`/`think` |
| `test_openai_forca_o_esquema_por_response_format_e_le_o_content` | URL, `Authorization: Bearer`, `json_schema.name/schema/strict`, `max_tokens`/`temperature` |
| `test_gemini_forca_o_esquema_por_response_schema_e_le_a_parte_de_texto` | URL, `x-goog-api-key`, `response_mime_type`, `response_schema`, `maxOutputTokens` |
| três casos de imagem | bloco `image`/`source.base64` (Anthropic), `image_url` com data URL (OpenAI), `inlineData` (Gemini) |
| `test_gemini_nao_leva_a_chave_na_url` | a chave não está na URL nem no `erro` gravado em `fila_revisao` |
| `test_anthropic_resposta_sem_tool_use_...` | 200 sem `tool_use` → `fila_revisao`, sem exceção nova |
| `test_erro_de_transporte_usa_o_backoff_da_base_e_cai_na_fila_revisao` (×3) | 5 tentativas, esperas `[2, 4, 8, 16]`, `FalhaJsonInvalido`, 1 linha em `fila_revisao` — prova de que a base do 074 é usada de verdade, não copiada |
| `test_json_invalido_aciona_a_nova_tentativa_por_temperatura_da_base` (×3) | as duas temperaturas do perfil, nenhuma espera de backoff, `fila_revisao` |
| `test_embeddar_e_modelo_embedding_so_repassam_ao_ollama_sem_chamar_a_api` (×3) | vetores de 1024 vindos do `ClienteOllama` injetado e **zero** requisições ao transporte da API |
| `test_proveniencia_registra_o_modelo_do_provedor_de_api` (×3) | `proveniencia.modelo` é o modelo da API e **não** o do `llm_routing.yaml` |
| `test_tarefa_fora_do_perfil_continua_erro_claro` (×3) | a conferência de tarefa declarada, que é da base, continua valendo |

Nenhum deles exige variável de ambiente, chave ou internet.

## Arquivos preservados literalmente na área afetada

- `_ClienteLLMBase` e `ClienteOllama` — não tocados: o `git diff` deste brief em `llm.py` é só
  acréscimo ao fim do arquivo.
- `tests/test_llm_resiliente.py` e os outros testes de LLM — não tocados.
- `config/container.py`, `agente_nw/console/app.py`, `config/local.yaml`,
  `config/local.exemplo.yaml` — fora de escopo (item 5), brief 076.
- `nucleo/prompts/*` — fora de escopo.

## RELATÓRIO FINAL

- **Brief executado:** 075 — clientes de API Anthropic, Gemini e OpenAI com a mesma forma do cliente
  Ollama (conjunto `ia_api`, 2/3).
- **Arquivos criados:** `tests/test_llm_api.py`,
  `docs/docs/doc_075_clientes_api_anthropic_gemini_openai_2026-11-03.md`, `logs/commit_075.txt`,
  `logs/arquivos_075.txt`.
- **Arquivos alterados (resumo em uma linha cada):**
  - `agente_nw/nucleo/llm.py` — acrescentadas `_ClienteApiBase` (chave, modelo único, embeddings por
    composição, proveniência do provedor) e as três classes públicas `ClienteAnthropic`,
    `ClienteGemini` e `ClienteOpenAI`, cada uma só com o `_chamar` do seu provedor, mais as três
    funções de leitura de resposta.
- **Arquivos preservados literalmente na área afetada:** `_ClienteLLMBase`, `ClienteOllama`,
  `tests/test_llm_resiliente.py`, `config/container.py`, `agente_nw/console/app.py`.
- **Script de verificação (o gate, rodado pelo `scripts/agente_entregar.sh`; saída colada):** ver
  "Saída do gate" abaixo.
- **Comandos executados:**
  - `grep` em `extensao/background.js`, `coleta/capturas/extensao_backend.py` e
    `coleta/capturas/imagens.py` (conferência do item 3.2, acima)
  - `.venv/bin/python -m pytest tests/test_llm_api.py -q` → `23 passed`
  - `.venv/bin/python -m pytest -q` → `934 passed, 5 deselected`
  - `.venv/bin/python -m ruff check` e `ruff format --check` nos dois arquivos → `All checks passed!`, `2 files already formatted`
  - `.venv/bin/python -m mypy agente_nw/nucleo/llm.py` → sem erro (o aviso de `llm_mod.time` em `tests/` é o mesmo que `test_llm_resiliente.py` já tinha e está fora do gate, que roda `mypy agente_nw`)
  - `scripts/agente_entregar.sh 075`
- **Manifesto do commit (`logs/arquivos_075.txt` e `logs/commit_075.txt`):** ver abaixo.
- **Pendências e decisões que ficaram abertas:** teste com chave real de cada provedor, que só faz
  sentido depois do 076 (seção 6 do brief) — fica para Sidarta; mais as três lacunas abaixo.
- **Resumo, Doing, Backlog e Done do `docs/PLAN.md` atualizados:** sim.

## Saída do gate

```
$ scripts/agente_entregar.sh 075
manifesto 075: 2 arquivo(s)
ruff check: ok
ruff format: ok
mypy: ok
pytest: ok (934 passed, 5 deselected in 23.30s)
lacunas do 075: 0 no Backlog, 0 em Pendências, 3 em Dívidas, 0 em Decisões
✓ brief 075: commit 8a5d7eb, enviado ao GitHub
```

934 testes: os 911 de antes mais os 23 de `tests/test_llm_api.py`, nenhum teste existente alterado.

## Manifesto

`logs/arquivos_075.txt`:

```
agente_nw/nucleo/llm.py
tests/test_llm_api.py
```

`logs/commit_075.txt`:

```
feat(llm): clientes de API Anthropic, Gemini e OpenAI com a forma do cliente Ollama (brief 075)
```

## Lacunas

| # | Lacuna | Destino | Impacto |
|---|--------|---------|---------|
| 1 | O mime real de cada imagem publicada existe (`ImagemCapturada.mime`, do `content-type` que a extensão leu) mas é descartado em `coleta/capturas/imagens.py:61`, que passa só a base64 para `gerar_json`; os três clientes de API declaram `image/jpeg` fixo. Um PNG ou WebP do Instagram declarado como JPEG pode levar 400 de qualquer um dos três provedores na tarefa `descrever_imagem`. Corrigir exige levar o mime até `_chamar`, isto é, mudar a assinatura de `gerar_json` (fechada pelo brief 074) | dívida | degrada |
| 2 | `ClienteOpenAI` manda `response_format.json_schema.strict: true` com o esquema do Pydantic sem transformação, como o brief pede, mas a API da OpenAI exige nesse modo `additionalProperties: false` em todo objeto e todos os campos em `required` — e `model_json_schema()` não gera nem um nem outro para campo com valor padrão (ex.: `RespostaDescricaoImagem.descartar`). A primeira chamada real pode voltar 400. Queda documentada, igual à do Gemini: tirar `strict` e confiar no `model_validate` que já existe depois | dívida | degrada |
| 3 | `ClienteGemini` manda `generationConfig.response_schema` com o esquema do Pydantic; o subconjunto de JSON Schema aceito pelo Gemini é mais estreito (`$defs`, `anyOf` com `null`) e pode voltar 400 (risco já previsto no item 3.1 do brief). Queda documentada: manter `response_mime_type: application/json` sem `response_schema` | dívida | degrada |
