# Doc 074 — Orquestração de `gerar_json` comum a qualquer provedor

**Brief:** `docs/briefs/brief_074_base_comum_para_qualquer_provedor_2026-11-03.md`
**Data:** 2026-11-03

## Qual brief 074 foi executado

Havia **dois** arquivos `brief_074_*` no disco, de desenhos incompatíveis, gravados com 11 minutos de
diferença:

| | `brief_074_resposta_por_api_quando_local_falha` (04:11) | `brief_074_base_comum_para_qualquer_provedor` (04:22) |
|---|---|---|
| Conjunto | "1 de 2" (074 e 075, sem 076) | "ia_api" (074, 075 e 076) |
| Desenho | API é **fallback**: só entra quando o Ollama esgota | API é **par** do Ollama; a seleção é por chave cadastrada (076) |
| Código | novo `nucleo/api_externa.py`, `ClienteAnthropicFallback` | `_ClienteLLMBase` dentro de `llm.py` |

Executado o **trio `ia_api`** (04:22), por decisão explícita de Sidarta nesta sessão. Isso é também o que
o Backlog do `docs/PLAN.md` já registrava para 074/075/076 ("refatorar `gerar_json` numa base comum",
"clientes de API Anthropic/Gemini/OpenAI", "geração por API quando houver chave cadastrada"). O par de
04:11 ficou no disco, sem ser executado — ver a tabela de lacunas.

## O que foi feito

`agente_nw/nucleo/llm.py` passou a ter duas classes no lugar de uma:

- **`_ClienteLLMBase(ABC)`** — tudo que não fala com um provedor específico: `__init__(conexao_bd,
  roteamento, caminho_log)`, `_tarefa`, `proveniencia`, `_registrar_log_chamada`,
  `_ir_para_fila_revisao`, `_chamar_com_backoff` (era `_chamar_generate_com_backoff`) e `gerar_json`,
  com o corpo idêntico ao de antes. Declara um método abstrato `_chamar`.
- **`ClienteOllama(_ClienteLLMBase)`** — só o que é Ollama: `_chamar` (corpo idêntico ao
  `_chamar_generate` de antes, byte por byte do payload), `embeddar` e `modelo_embedding`. O
  `__init__` guarda `http_client` e `ollama_url` e chama `super().__init__(conexao_bd, roteamento,
  caminho_log)`.

A assinatura de `_chamar` é a do item 3.2 do brief, com o parâmetro `esquema` novo:

```python
@abstractmethod
def _chamar(
    self,
    tarefa: TarefaRoteamento,
    prompt: str,
    temperature: float,
    imagens: list[str] | None,
    esquema: type[BaseModel],
) -> str: ...
```

`ClienteOllama._chamar` implementa essa assinatura **exatamente** (sem valores padrão, sem alargar o
tipo de `esquema` para `| None`) e ignora `esquema`, com o motivo na docstring: o formato de saída do
Ollama vem do `format` da tarefa (a string `"json"` do YAML), não de um esquema no payload. Manter a
assinatura idêntica à abstrata é o que faz o brief 075 não precisar tocá-la de novo.

`gerar_json` repassa `esquema` para `_chamar_com_backoff`, que o repassa para `self._chamar(...)` — e
continua usando o mesmo `esquema` depois, no `model_validate`, como antes.

### Nada do comportamento observável mudou (item 3.5)

- Mesmo corpo HTTP no `POST {ollama_url}/api/generate`: `model`, `prompt`, `format`, `stream`,
  `options.num_ctx/temperature/seed/num_predict`, `images` só quando há imagem, `think` só quando o
  perfil tem `enviar_think`.
- Mesma detecção de geração degenerada (500 com `"token repeat limit"` no `error`), no mesmo lugar: o
  `_chamar` do Ollama. Quem a trata continua sendo `gerar_json`, na base.
- Mesmo backoff (`_INTERVALOS_BACKOFF_TRANSPORTE`, 2/4/8/16), mesma regra de re-levantar
  `_GeracaoDegenerada` sem esperar, mesmo `FalhaJsonInvalido`, mesma linha no `chamadas_llm.jsonl`,
  mesma escrita em `fila_revisao`.
- `embeddar` e `modelo_embedding` ficaram **fora** da base, por decisão do item 3.4 — não foram
  alterados em nada.

## Por que nenhum teste precisou de ajuste (item 4)

A conferência que o brief pediu foi refeita no disco antes de mexer no código:

```
$ grep -rn --include='*.py' -e '_chamar_generate' -e '_chamar_com_backoff' -e '_ClienteLLMBase' \
    -e '_registrar_log_chamada' -e '_ir_para_fila_revisao' -e '_GeracaoDegenerada' . \
    | grep -v '^./agente_nw/nucleo/llm.py'
(nenhuma)
```

Nenhum arquivo fora de `llm.py` — teste ou código — toca um nome privado que mudou de lugar. Dos 29
importadores de `nucleo.llm`, todos importam apenas `ClienteOllama` e/ou `FalhaJsonInvalido`, que
continuam existindo com o mesmo nome e a mesma assinatura pública:

```
$ grep -rn --include='*.py' -e 'nucleo\.llm' -e 'nucleo import llm' . | grep -v '^./agente_nw/nucleo/llm.py' | wc -l
29
```

Por isso a prova de aceite é a suíte continuar verde **sem nenhuma edição em teste**, e é o que
`git status` mostra: um único arquivo modificado.

```
$ git status --short
 M agente_nw/nucleo/llm.py
```

## Arquivos preservados literalmente na área afetada

- `tests/test_llm_resiliente.py` — não tocado (é o teste de aceite; nenhuma asserção editada).
- `tests/test_llm_payload.py`, `tests/test_llm_log_chamadas.py`, `tests/test_proveniencia.py`,
  `tests/test_llm_fumaca.py` — não tocados.
- `config/container.py`, `agente_nw/console/app.py`, `config/local.yaml`,
  `config/local.exemplo.yaml` — fora de escopo neste brief (item 5), não tocados.
- `embeddar` e `modelo_embedding` — sem uma linha de mudança.

## RELATÓRIO FINAL

- **Brief executado:** 074 — orquestração de `gerar_json` comum a qualquer provedor (refatoração, sem
  mudança de comportamento), do conjunto `ia_api`.
- **Arquivos criados:** `docs/docs/doc_074_base_comum_para_qualquer_provedor_2026-11-03.md`,
  `logs/commit_074.txt`, `logs/arquivos_074.txt`.
- **Arquivos alterados (resumo em uma linha cada):**
  - `agente_nw/nucleo/llm.py` — a orquestração de `gerar_json` (nova tentativa, backoff, validação,
    log, `fila_revisao`) virou `_ClienteLLMBase`, com `_chamar` abstrato; `ClienteOllama` herda dela e
    implementa só `_chamar`, `embeddar` e `modelo_embedding`.
- **Arquivos preservados literalmente na área afetada:** todos os testes de LLM (nenhuma asserção
  editada), `config/container.py`, `agente_nw/console/app.py`, `embeddar`/`modelo_embedding`.
- **Script de verificação (o gate, rodado pelo `scripts/agente_entregar.sh`; saída colada):** ver
  "Saída do gate" abaixo.
- **Comandos executados:**
  - `grep` pelos nomes privados e pelos importadores de `nucleo.llm` (saídas coladas acima)
  - `.venv/bin/python -m pytest tests/test_llm_resiliente.py tests/test_llm_payload.py tests/test_llm_log_chamadas.py tests/test_proveniencia.py -q` → `23 passed`
  - `.venv/bin/python -m ruff check agente_nw/nucleo/llm.py` → `All checks passed!`
  - `.venv/bin/python -m ruff format --check agente_nw/nucleo/llm.py` → `1 file already formatted`
  - `.venv/bin/python -m mypy agente_nw/nucleo/llm.py` → `Success: no issues found in 1 source file`
  - `git status --short` → só `M agente_nw/nucleo/llm.py`
  - `scripts/agente_entregar.sh 074`
- **Manifesto do commit (`logs/arquivos_074.txt` e `logs/commit_074.txt`):** ver abaixo.
- **Pendências e decisões que ficaram abertas:** o par de briefs 074/075 do desenho de fallback, que
  ficou no disco sem ser executado — na tabela de lacunas.
- **Resumo, Doing, Backlog e Done do `docs/PLAN.md` atualizados:** sim.

## Saída do gate

```
$ scripts/agente_entregar.sh 074
manifesto 074: 1 arquivo(s)
ruff check: ok
ruff format: ok
mypy: ok
pytest: ok (911 passed, 5 deselected in 22.97s)
lacunas do 074: 0 no Backlog, 0 em Pendências, 0 em Dívidas, 1 em Decisões
✓ brief 074: commit 9598a8e, enviado ao GitHub
```

911 testes, o mesmo número do commit anterior (`6141be1`): nenhum teste novo e nenhum teste perdido —
exatamente o que o item 4 do brief pede como prova de que a reorganização não mudou nada visível.

## Manifesto

`logs/arquivos_074.txt`:

```
agente_nw/nucleo/llm.py
```

`logs/commit_074.txt`:

```
refactor(llm): orquestracao de gerar_json vira base comum a qualquer provedor (brief 074)
```

## Lacunas

| # | Lacuna | Destino | Impacto |
|---|--------|---------|---------|
| 1 | `docs/briefs/brief_074_resposta_por_api_quando_local_falha_2026-11-03.md` e `docs/briefs/brief_075_fallback_gemini_e_gpt_2026-11-03.md` continuam no disco, do desenho de fallback que não foi escolhido. Enquanto estiverem lá, `brief_074_*` e `brief_075_*` casam com dois arquivos cada, e o passo 1 do `/executar` fica ambíguo para qualquer sessão futura. Apagar ou arquivar brief é de Sidarta, não do executor | decisão | degrada |
