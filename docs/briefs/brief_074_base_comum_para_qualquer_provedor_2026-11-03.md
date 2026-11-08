# Brief 074 — Orquestração de `gerar_json` comum a qualquer provedor (refatoração, sem mudança de comportamento)

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Conjunto:** ia_api (074, 075 e 076 — 074 só reorganiza o código existente; 075 traz os clientes de API; 076 liga a seleção pela chave cadastrada em `config/local.yaml`. Sequencial, direto na `main`, sem worktree — AGENTS §12)
**Arquivos-alvo:** `agente_nw/nucleo/llm.py`
**Seções a ler:** `docs/ARQUITETURA.md` §8 (Camada de LLM); `agente_nw/nucleo/llm.py` inteiro; `tests/test_llm_resiliente.py` inteiro (a prova de que nada mudou é ele continuar passando sem editar nenhuma asserção)
**Modelo:** Opus — toca o cliente usado pelas 15 tarefas de LLM do produto; uma regressão aqui não aparece num teste isolado, aparece em produção
**Esforço:** médio
**Teste de aceite:** `tests/test_llm_resiliente.py` (sem editar nenhuma asserção existente)
**Depende de:** nada — primeiro do conjunto `ia_api`
**Data:** 2026-11-03

---

## 1. Objetivo em uma frase

Separar, dentro de `ClienteOllama`, o que é específico do Ollama (montar o payload do `/api/generate`, detectar geração degenerada) do que não é (a nova tentativa por temperatura, validar o JSON contra o esquema, mandar para `fila_revisao`, logar) — para que os clientes de API do brief 075 reaproveitem essa segunda parte sem duplicá-la.

---

## 2. Achado no código (o que já é genérico, o que não é)

Em `agente_nw/nucleo/llm.py`, `ClienteOllama.gerar_json` hoje:

```python
def gerar_json(self, tarefa_nome, prompt, esquema, imagens=None, versao_prompt=None):
    ...
    for indice, temperatura in enumerate(tentativas, start=1):
        try:
            texto, falhas_transporte = self._chamar_generate_com_backoff(tarefa, prompt, temperatura, imagens)
        except (httpx.HTTPStatusError, httpx.RequestError) as erro:
            ...
            raise self._ir_para_fila_revisao(...) from erro
        except _GeracaoDegenerada as erro:
            ultimo_erro = str(erro)
            continue
        try:
            bruto = json.loads(texto)
            resultado = esquema.model_validate(bruto)
            self._registrar_log_chamada(...)
            return resultado
        except (json.JSONDecodeError, ValidationError) as erro:
            ultimo_erro = str(erro)
    ...
    raise self._ir_para_fila_revisao(tarefa_nome, prompt, ultimo_erro)
```

Nada disso fala com o Ollama: é a mesma lógica de retomada (temperatura da tarefa, depois a de `nova_tentativa`), validação de JSON contra o esquema Pydantic e escrita em `fila_revisao` que qualquer provedor vai precisar. O único ponto que sabe que existe um Ollama é `_chamar_generate_com_backoff` → `_chamar_generate`: monta o corpo específico (`model`, `format`, `options.num_ctx/temperature/seed/num_predict`, `think` condicional), faz o POST em `{ollama_url}/api/generate`, e só ali que nasce `_GeracaoDegenerada` (checando `"token repeat limit"` na resposta 500).

`_registrar_log_chamada`, `_tarefa`, `proveniencia` e `_ir_para_fila_revisao` também não têm nada de Ollama — leem `self._roteamento` (perfil/tarefa) e `self._conexao`/`self._caminho_log`, que qualquer cliente vai ter.

`embeddar` e a propriedade `modelo_embedding` são Ollama de ponta a ponta (chamam `/api/embed`) — ficam de fora desta separação; o brief 075 decide como os clientes de API os obtêm (adianto a decisão: por composição, nunca reimplementados).

---

## 3. Decisões

**3.1. Nova classe `_ClienteLLMBase`, com tudo que não fala com um provedor específico.** Move para ela: `__init__` (recebe `conexao_bd`, `roteamento`, `caminho_log` — os três campos que não são do Ollama), `_tarefa`, `proveniencia`, `_registrar_log_chamada`, `_ir_para_fila_revisao`, `_chamar_com_backoff` (hoje `_chamar_generate_com_backoff`, com o nome generalizado) e `gerar_json`, com o corpo **idêntico** ao de hoje. O nome leva `_` porque não é parte do contrato público que os outros módulos esperam (eles importam `ClienteOllama` ou duck-type um Protocol com `gerar_json`/`proveniencia`/`modelo_embedding` — nenhum importa `_ClienteLLMBase`).

**3.2. Um método abstrato novo, `_chamar`, no lugar de `_chamar_generate`.** Assinatura:
```python
def _chamar(
    self, tarefa: TarefaRoteamento, prompt: str, temperature: float,
    imagens: list[str] | None, esquema: type[BaseModel],
) -> str: ...
```
`_chamar_com_backoff` (na base) chama `self._chamar(...)` em vez de `self._chamar_generate(...)`; o resto do backoff (os mesmos `_INTERVALOS_BACKOFF_TRANSPORTE`, a mesma captura de `_GeracaoDegenerada`/`httpx.HTTPStatusError`/`httpx.RequestError`) não muda de lugar nem de comportamento.

O parâmetro `esquema` é novo na assinatura e **não existia** em `_chamar_generate`. Adiciono-o agora, embora `ClienteOllama` vá ignorá-lo (ver 3.3), para o brief 075 não precisar tocar essa assinatura de novo: os três clientes de API vão usar `esquema.model_json_schema()` para forçar o formato de saída do próprio provedor, e só têm acesso ao esquema se ele chegar até `_chamar`. `gerar_json`, na base, passa `esquema` para `self._chamar(...)` (hoje ele só usa `esquema` depois, no `model_validate` — continua usando lá também).

**3.3. `ClienteOllama` implementa só `_chamar` — corpo idêntico ao `_chamar_generate` de hoje, ignorando o parâmetro `esquema` novo.** Nenhuma linha do payload do Ollama muda: `format: tarefa.format` continua sendo a string `"json"` fixa do YAML, não o esquema — mudar isso é decisão de outro brief, fora de escopo aqui (ver seção 5). `ClienteOllama.__init__` ganha `http_client` e `ollama_url` **além** do que a base já pede, e chama `super().__init__(conexao_bd, roteamento, caminho_log)`.

**3.4. `embeddar` e `modelo_embedding` continuam só em `ClienteOllama`, fora da base.** Não ficam abstratos nem a base os declara — é decisão explícita, não esquecimento: o 075 decide como os clientes de API os obtêm, e adiantar essa decisão aqui sem o 075 no ar deixaria a interface pela metade.

**3.5. Nada do comportamento observável muda.** Mesmos logs (`_registrar_log_chamada`), mesmo formato de linha no `chamadas_llm.jsonl`, mesmo corpo HTTP enviado ao Ollama, mesma exceção (`FalhaJsonInvalido`) e mesmo conteúdo de `fila_revisao` em caso de esgotamento. `tests/test_llm_resiliente.py` não muda nenhuma asserção — só prova, ao continuar verde, que a reorganização não alterou nada visível de fora.

---

## 4. Testes

Nenhum teste novo neste brief — a prova é `tests/test_llm_resiliente.py` continuar passando **sem editar nenhuma asserção existente**. Se algum teste depender de nome de método privado que mudou de lugar (confirmado nesta sessão: a conferência atual — `grep` por `_chamar_generate`, `_registrar_log_chamada`, `_ir_para_fila_revisao`, `._tarefa(` no arquivo de teste — não achou nenhum acesso direto; os testes só passam pela interface pública `gerar_json`/`embeddar` com `httpx.MockTransport`), então não deveria haver nenhum ajuste a fazer. Se o executor encontrar algum, ajusta só o nome acessado, nunca o valor esperado.

---

## 5. Fora de escopo

- Mudar o que `ClienteOllama` manda no `format` do payload do Ollama (continua a string `"json"` fixa do YAML; usar o esquema para forçar formato no próprio Ollama é outra decisão, não pedida aqui).
- Qualquer cliente de API nova (Anthropic, Gemini, OpenAI) — brief 075.
- Qualquer mudança em `config/container.py`, `agente_nw/console/app.py` ou `config/local.yaml` — brief 076.
- Mudar `embeddar`/`modelo_embedding` de qualquer forma.

---

## 6. Passos e aceite

Executar com `/executar 074`. Aceite: `tests/test_llm_resiliente.py` verde sem edição de asserção, gate verde, commit e push pelo executor.

Sem pendência de teste real para Sidarta — é refatoração interna sem comportamento novo; a prova é a suíte continuar idêntica.
