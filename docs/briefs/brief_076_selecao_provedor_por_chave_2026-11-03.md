# Brief 076 — Com chave cadastrada, o programa usa a API; sem chave, continua no Ollama

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Conjunto:** ia_api (074, 075 e 076 — este é o terceiro e último; depende dos dois anteriores)
**Arquivos-alvo:** `agente_nw/nucleo/modelos/configuracao.py` (novo bloco de config), `config/local.exemplo.yaml` (documentar o bloco novo, comentado), `config/container.py` (`llm()`), `agente_nw/console/app.py` (as três construções de cliente: `_cliente_llm`, a de dentro de `_dependencias`/`fabrica_llm`, e a do `conn_fundo`), `AGENTS.md` (§3, uma regra nova — a próxima seção livre depois da §12 do brief 073 é a §13, mas aqui é um acréscimo dentro da §3 existente, não seção nova), `docs/ARQUITETURA.md` §8 (um parágrafo novo), `tests/test_selecao_provedor.py` (novo), `docs/docs/doc_076_selecao_provedor_por_chave_2026-11-03.md`, `logs/commit_076.txt`, `logs/arquivos_076.txt`
**Seções a ler:** briefs 074 e 075 já executados; `config/container.py` inteiro; `agente_nw/console/app.py`, as três funções que hoje constroem `ClienteOllama` (mesmas três que o brief 064 já tinha listado); `agente_nw/nucleo/modelos/configuracao.py` inteiro (para encaixar o novo modelo Pydantic sem quebrar `model_config = ConfigDict(frozen=True)`); AGENTS §12 (não usar worktree para este conjunto)
**Modelo:** Sonnet
**Esforço:** médio
**Teste de aceite:** `tests/test_selecao_provedor.py`
**Depende de:** briefs 074 e 075
**Data:** 2026-11-03

---

## 1. Objetivo em uma frase

Um bloco novo e opcional em `config/local.yaml` registra a chave e o modelo de cada provedor de API (Anthropic, Gemini, OpenAI); com qualquer uma cadastrada, o programa gera texto por aquela API em vez do Ollama local — sem nenhuma chave (o caso de hoje, de todo instalador existente), nada muda.

---

## 2. Por que a leitura "não usar LLM offline" precisa de uma correção, dita de forma decisiva, não como pergunta

Pedido original: "quando tiver cadastrado chaves, o programa irá usar IA via api e não usar llm offline". Os briefs 074/075 já deixaram uma peça fixa: embeddings (`embeddar`/`modelo_embedding`) continuam **sempre** no Ollama local, qualquer que seja o provedor de geração — a Anthropic não tem endpoint de embedding, e trocar de modelo de embedding invalidaria (por descasamento, brief 066) todo centróide de perfil/tema já gravado. Decisão já tomada no 075, só repetida aqui porque é este brief que a torna visível no `AGENTS.md`: "não usar LLM offline" passa a valer para a **geração de texto estruturado**; o Ollama continua rodando, sempre, só para embeddings.

---

## 3. Decisões

**3.1. Novo bloco em `config/local.yaml`, opcional, de nome `ia_api`:**
```yaml
ia_api:
  provedor: auto   # auto (padrão) | ollama | anthropic | gemini | openai
  anthropic:
    chave: "sk-ant-..."
    modelo: "claude-..."   # confirme o nome atual do modelo com a Anthropic antes de usar
  gemini:
    chave: "..."
    modelo: "gemini-..."   # confirme o nome atual do modelo com o Google antes de usar
  openai:
    chave: "..."
    modelo: "gpt-..."      # confirme o nome atual do modelo com a OpenAI antes de usar
```
Todo o bloco é opcional; qualquer sub-bloco (`anthropic`/`gemini`/`openai`) também — só precisa existir o que for usado. Sem `ia_api` no arquivo (o caso de `config/local.yaml` hoje, e de `config/local.exemplo.yaml`), o comportamento é **idêntico ao de antes deste conjunto**: Ollama, perfil de `perfil_llm`, como sempre foi.

Modelo Pydantic novo em `agente_nw/nucleo/modelos/configuracao.py` (`frozen=True`, como todo o resto do arquivo):
```python
class ProvedorApi(BaseModel):
    model_config = ConfigDict(frozen=True)
    chave: str
    modelo: str

class ConfiguracaoIaApi(BaseModel):
    model_config = ConfigDict(frozen=True)
    provedor: Literal["auto", "ollama", "anthropic", "gemini", "openai"] = "auto"
    anthropic: ProvedorApi | None = None
    gemini: ProvedorApi | None = None
    openai: ProvedorApi | None = None
```
`Configuracao` (a classe já existente) ganha `ia_api: ConfiguracaoIaApi = Field(default_factory=ConfiguracaoIaApi)` — com tudo ausente do YAML, vira o `ConfiguracaoIaApi()` padrão (`provedor: "auto"`, os três `None`), e a seleção (3.2) cai no Ollama sem nenhuma chave para achar.

**3.2. Ordem de prioridade quando mais de uma chave está cadastrada: Anthropic, depois Gemini, depois OpenAI.** Com `provedor: auto` (o padrão), a primeira das três, nesta ordem fixa, que tiver `chave` e `modelo` preenchidos é a usada; nenhuma cadastrada → Ollama. Com `provedor` explícito (`anthropic`/`gemini`/`openai`/`ollama`), usa exatamente o que foi pedido — se o sub-bloco daquele provedor não estiver preenchido, erro claro na inicialização (`ValueError`, não uma falha silenciosa na primeira chamada).

Essa ordem é decisão deste brief, não teve critério técnico além de ser previsível e documentada — se Sidarta preferir outra ordem, é só mudar `provedor` para o nome explícito do que ele quer, sem depender da prioridade automática.

**3.3. Função nova, `selecionar_cliente_llm`, substitui as quatro construções diretas de `ClienteOllama`.** Em `config/container.py` (a função `llm()`) e nas três de `agente_nw/console/app.py` (`_cliente_llm`, a de dentro de `_dependencias`/`fabrica_llm`, a do `conn_fundo` — as mesmas três do brief 064), a chamada direta a `ClienteOllama(...)` é trocada por `selecionar_cliente_llm(http_client, conexao_bd, cfg, caminho_log)`, que:
  1. Sempre constrói um `ClienteOllama` (é o cliente de embeddings, precisa existir de qualquer forma — item 3.4 do brief 075).
  2. Decide o provedor de geração pela regra do item 3.2.
  3. Se o provedor decidido for `ollama`, devolve esse mesmo `ClienteOllama`.
  4. Senão, constrói o `ClienteAnthropic`/`ClienteGemini`/`ClienteOpenAI` correspondente, passando o `ClienteOllama` do passo 1 como `cliente_embeddings`, e devolve esse.

Local sugerido: `agente_nw/nucleo/llm.py` (fica ao lado das classes que constrói) ou `config/container.py` (fica ao lado de quem cuida de configuração) — decisão de implementação do executor; o que importa é existir uma função só, chamada nos quatro lugares, para nunca haver um quinto lugar decidindo o provedor de outro jeito.

**3.4. `AGENTS.md` §3 ganha uma linha nova**, depois da linha do `think: false` (ajustar a redação ao tom das demais, preservando os dois fatos):
```markdown
- Geração de texto por API (Anthropic, Gemini ou OpenAI) é opcional e só liga com uma chave cadastrada em `ia_api` (`config/local.yaml`) — sem chave, Ollama, como sempre. Embeddings continuam **sempre** no Ollama local, qualquer que seja o provedor de geração (a Anthropic não tem endpoint de embedding, e trocar de modelo invalidaria os centróides já gravados, brief 066).
```

**3.5. `docs/ARQUITETURA.md` §8 ganha um parágrafo novo**, ao fim da seção, descrevendo o mecanismo de seleção (provedor, ordem de prioridade, a invariante de embeddings) — sem reescrever o que já está lá sobre o Ollama/perfis.

**3.6. Dado de terceiro continua cercado por `cercar_dado_externo` mesmo indo para uma API externa.** Nenhuma mudança é pedida aqui nos módulos de `nucleo/prompts/` (o brief 068 já cerca o que entra nos nove prompts) — o aviso que vale é de produto, não de código: a partir deste brief, com uma chave de API cadastrada, o texto desses prompts (que inclui fatos sobre o contato, trechos de WhatsApp, posts de rede social) passa a sair da máquina de Sidarta e ir para o servidor do provedor escolhido. Isso é o que foi pedido; só fica dito aqui com todas as letras, uma vez, para não ficar implícito.

---

## 4. Testes (escritos antes do código)

Novo `tests/test_selecao_provedor.py`:
- sem `ia_api` no YAML (ou com o bloco todo ausente) → `selecionar_cliente_llm` devolve um `ClienteOllama` — comportamento de hoje, inalterado;
- `ia_api.provedor: auto` com só `anthropic` preenchido → devolve `ClienteAnthropic`;
- `ia_api.provedor: auto` com `anthropic` e `openai` preenchidos → devolve `ClienteAnthropic` (prioridade, item 3.2);
- `ia_api.provedor: openai` com `anthropic` também preenchido → devolve `ClienteOpenAI` (override explícito vence a prioridade automática);
- `ia_api.provedor: gemini` sem o sub-bloco `gemini` preenchido → `ValueError` claro na inicialização, não uma falha tardia;
- o `ClienteOllama` interno (passo 1 da seleção) é sempre construído, mesmo quando o provedor escolhido é um de API — confirmar que ele é exatamente o que vira `cliente_embeddings` do cliente de API devolvido;
- as quatro construções de cliente em `container.py`/`app.py` usam a mesma função `selecionar_cliente_llm` (teste de não regressão simples: grep ou leitura do código, confirmando que não sobrou nenhum `ClienteOllama(...)` direto fora dela e de dentro da própria função).

---

## 5. Fora de escopo

- Qualquer mudança nos módulos de `nucleo/prompts/` — o cerco de dado de terceiro (brief 068) já existe e não precisa de ajuste para valer também para as chamadas de API.
- Variável de ambiente para a chave em vez de `config/local.yaml` — o arquivo já é o lugar usado para o resto do que é específico da máquina (`ollama_url`, `redes.*.usuario`) e já é ignorado pelo git (`.gitignore`); não há ganho em abrir um segundo mecanismo de segredo para só isso.
- Granularidade por tarefa para os provedores de API (um modelo diferente por tarefa, como o Ollama tem) — um modelo só por provedor, decidido no brief 075, e não revisto aqui.
- Testar com chave real de qualquer provedor — fora de escopo de teste automatizado; é a pendência real do brief 075 para Sidarta.

---

## 6. Passos e aceite

Executar com `/executar 076`. Aceite: `tests/test_selecao_provedor.py` verde, gate verde, commit e push pelo executor.

Pendência real para Sidarta, só depois dos três (074/075/076) estarem no ar: cadastrar uma chave de verdade (a que ele quiser usar primeiro) em `config/local.yaml`, rodar um pedido de teste, e confirmar no log (`dados/logs/chamadas_llm.jsonl`) que o campo `modelo` registrado é o do provedor de API escolhido, não mais `qwen3:4b`/`qwen2.5:14b` do Ollama.
