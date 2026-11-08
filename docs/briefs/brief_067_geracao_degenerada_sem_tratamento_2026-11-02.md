# Brief 067 — Geração degenerada volta a ser tratada, não derruba mais a chamada

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Conjunto:** nenhum (brief isolado, direto na `main`) — correção pontual sobre o 064, não parte do conjunto `camada_de_ia`
**Arquivos-alvo:** `agente_nw/nucleo/llm.py` (`gerar_json`, `_chamar_generate_com_backoff`), `tests/test_llm_resiliente.py` (caso novo), `docs/docs/doc_067_geracao_degenerada_sem_tratamento_2026-11-02.md`, `logs/commit_067.txt`, `logs/arquivos_067.txt`
**Seções a ler:** `agente_nw/nucleo/llm.py` inteiro, como está depois do 064/065/066; no PLAN, a armadilha 22 (geração degenerada é falha de tentativa, não de rede)
**Modelo:** Sonnet
**Esforço:** baixo
**Teste de aceite:** o caso novo em `tests/test_llm_resiliente.py`
**Depende de:** brief 064 (`4b0aefb`) — é a correção de uma regressão que ele introduziu
**Data:** 2026-11-02

---

## 1. Objetivo em uma frase

Quando o Ollama aborta a geração por loop de repetição, `gerar_json` volta a tentar de novo com temperatura mais baixa e, se continuar falhando, grava em `fila_revisao` — em vez de deixar o erro subir sem tratamento e derrubar o chamador.

---

## 2. Achado (regressão do brief 064)

Antes do 064, `_GeracaoDegenerada` era levantada dentro do mesmo `try` que já tratava `JSONDecodeError`/`ValidationError` em `gerar_json`, então caía na nova tentativa por temperatura normalmente. O 064 colocou a chamada atrás de `_chamar_generate_com_backoff`, cujo laço tem `except _GeracaoDegenerada: raise` — repassa a exceção na hora, de propósito, para não entrar no backoff de transporte. O problema é o que recebe essa exceção: em `gerar_json`, o `try` em volta de `self._chamar_generate_com_backoff(...)` só tem `except (httpx.HTTPStatusError, httpx.RequestError)`. `_GeracaoDegenerada` não é nenhum dos dois, então não é capturada ali — e o `except` que trata `_GeracaoDegenerada` junto com `JSONDecodeError`/`ValidationError` só existe depois dessa chamada, no bloco que processa o texto da resposta, nunca alcançado nesse caminho. A exceção escapa de `gerar_json` sem log, sem nova tentativa e sem `fila_revisao` — pior do que o comportamento anterior ao 064, não só igual.

---

## 3. Decisão

`_GeracaoDegenerada` levantada por `_chamar_generate_com_backoff` tem que ser tratada no mesmo lugar e do mesmo jeito que `JSONDecodeError`/`ValidationError` já são: conta como falha desta tentativa, segue para a próxima temperatura de `tentativas`, e, esgotadas as tentativas, vai para `fila_revisao` pelo caminho que já existe (`_ir_para_fila_revisao`). Isso é refazer a estrutura de `try`/`except` dentro do laço de `gerar_json` para que as duas famílias de falha de conteúdo — JSON/validação e geração degenerada — fiquem sob o mesmo `except`, com a falha de transporte continuando tratada à parte, exatamente como está hoje (vai direto para `fila_revisao`, sem tentar a próxima temperatura, porque falha de transporte já esgotou seu próprio backoff). Nenhuma mudança na camada de backoff de transporte (item 2.1 do brief 064): `_GeracaoDegenerada` continua saindo dali na hora, sem entrar no backoff — só muda quem a recebe depois.

---

## 4. Testes (escritos antes do código)

- `tests/test_llm_resiliente.py`, caso novo:
  - Ollama simulado responde geração degenerada (500, "token repeat limit") na primeira chamada e sucesso na segunda (temperatura de `nova_tentativa`) → `gerar_json` devolve o resultado, sem subir exceção;
  - geração degenerada nas duas tentativas → `FalhaJsonInvalido`, com linha em `fila_revisao` (não uma exceção não tratada escapando de `gerar_json`);
  - o teste que já existe (503 seguido de 200, falha de transporte) continua passando sem mudança — confirma que a separação entre as duas famílias de falha não se perdeu.

---

## 5. Fora de escopo

- Qualquer mudança no comportamento de falha de transporte (064) ou nos itens de proveniência (066) — este brief toca só a estrutura interna de `gerar_json`.
- O item 067 do plano original (defesa contra injeção de prompt) passa a ser o **068**, por este ter tomado o número antes dele.

---

## 6. Passos e aceite

Executar com `/executar 067`. Aceite: teste da seção 4 verde (e o teste de transporte do 064 continuando verde), gate verde, commit e push pelo executor.

Sem pendência de teste real para Sidarta — o comportamento só aparece sob uma falha específica do Ollama que não se provoca de propósito; a prova é toda no teste simulado.
