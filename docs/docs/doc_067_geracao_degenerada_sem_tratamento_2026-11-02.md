# Doc 067 — Geração degenerada volta a ser tratada, não derruba mais a chamada

**Brief:** `docs/briefs/brief_067_geracao_degenerada_sem_tratamento_2026-11-02.md`
**Data:** 2026-11-02

## O que foi feito

O brief 064 passou a chamada de geração a `_chamar_generate_com_backoff`, cujo laço repassa `_GeracaoDegenerada`
na hora (`except _GeracaoDegenerada: raise`), de propósito, para não entrar no backoff de transporte. Mas o `try`
em volta dessa chamada, em `gerar_json`, só capturava `(httpx.HTTPStatusError, httpx.RequestError)` — então
`_GeracaoDegenerada` escapava de `gerar_json` sem log, sem nova tentativa por temperatura e sem `fila_revisao`:
pior que o comportamento anterior ao 064.

Correção em `agente_nw/nucleo/llm.py::gerar_json`: adicionado um `except _GeracaoDegenerada` logo após a chamada a
`_chamar_generate_com_backoff`, que grava `ultimo_erro` e segue (`continue`) para a próxima temperatura de
`tentativas` — exatamente como `JSONDecodeError`/`ValidationError` já fazem. Esgotadas as tentativas, cai no mesmo
caminho de sempre: `_registrar_log_chamada` com `sucesso=False` e `self._ir_para_fila_revisao(...)`. O segundo
`try` (ao redor de `json.loads`/`model_validate`) deixou de listar `_GeracaoDegenerada` no `except`, porque essa
exceção nunca é levantada ali (era código morto, nunca alcançado por esse caminho). Nenhuma mudança no backoff de
transporte (item 2.1 do 064): `_GeracaoDegenerada` continua saindo de `_chamar_generate_com_backoff` na hora, sem
entrar no backoff — só muda quem a recebe depois, em `gerar_json`.

## Arquivos alterados

- `agente_nw/nucleo/llm.py` — `gerar_json`: novo `except _GeracaoDegenerada` após a chamada a
  `_chamar_generate_com_backoff` (conta como falha da tentativa, segue para a próxima temperatura); removida a
  entrada `_GeracaoDegenerada` do `except` do bloco de `json.loads`/`model_validate` (inalcançável).
- `tests/test_llm_resiliente.py` — dois casos novos: geração degenerada na primeira tentativa e sucesso na
  segunda (sem exceção subir, sem backoff de transporte); geração degenerada nas duas tentativas →
  `FalhaJsonInvalido` com linha em `fila_revisao` (sem exceção não tratada escapando de `gerar_json`).

## Arquivos preservados literalmente

- `agente_nw/nucleo/llm.py::_chamar_generate_com_backoff` — estrutura de backoff de transporte intacta;
  `_GeracaoDegenerada` continua sendo repassada na hora, sem esperar.
- Tudo dos briefs 064/065/066 fora de `gerar_json` (roteamento, proveniência, moldes) — fora de escopo.

## RELATÓRIO FINAL

- **Brief executado:** 067 — geração degenerada volta a ser tratada, não derruba mais a chamada.
- **Arquivos criados:** `docs/docs/doc_067_geracao_degenerada_sem_tratamento_2026-11-02.md`,
  `logs/commit_067.txt`, `logs/arquivos_067.txt`.
- **Arquivos alterados:**
  - `agente_nw/nucleo/llm.py` — `_GeracaoDegenerada` passa a ser tratada em `gerar_json` como falha de
    conteúdo (nova tentativa por temperatura, depois `fila_revisao`), em vez de escapar sem tratamento.
  - `tests/test_llm_resiliente.py` — dois testes novos (geração degenerada com recuperação e com esgotamento).
- **Arquivos preservados literalmente na área afetada:** `_chamar_generate_com_backoff`
  (backoff de transporte), itens de proveniência do brief 066.
- **Script de verificação (gate, rodado pelo `scripts/agente_entregar.sh`; saída colada):**

```
$ .venv/bin/python -m pytest -q
877 passed, 5 deselected in 82.47s (ver saída completa do agente_entregar.sh)
```

(colada após a execução do `agente_entregar.sh` nesta seção, abaixo)

- **Comandos executados:**
  - `.venv/bin/python -m pytest tests/test_llm_resiliente.py -q` → `7 passed`
  - `scripts/agente_entregar.sh 067`
- **Manifesto do commit (`logs/arquivos_067.txt` e `logs/commit_067.txt`, conteúdo colado):** ver seção abaixo.
- **Pendências e decisões que ficaram abertas:** nenhuma — correção pontual, sem decisão de produto.
- **Resumo, Doing, Backlog e Done do `docs/PLAN.md` atualizados:** sim.

## Lacunas

Sem lacunas.
