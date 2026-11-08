# Doc 064 — Cliente Ollama resiliente, reproduzível e único no console

Brief: `docs/briefs/brief_064_cliente_ollama_resiliente_2026-11-02.md`.

## 1. Como ficou

**2.1 — backoff de transporte.** `ClienteOllama._chamar_generate_com_backoff` envolve `_chamar_generate`
numa segunda camada de nova tentativa, só para `httpx.HTTPStatusError`/`httpx.RequestError` (conexão,
timeout, 429, 503 — tudo que `raise_for_status()` ou a própria conexão pode levantar). `_GeracaoDegenerada`
continua subindo direto, sem passar pelo backoff — ela é falha de tentativa, não de transporte (armadilha
22). São 4 tentativas extras com espera de 2, 4, 8 e 16 segundos antes de cada uma (total de 5 chamadas
possíveis por nível de temperatura). Se as 4 se esgotam, `gerar_json` não tenta a segunda temperatura da
nova tentativa por conteúdo — um servidor fora do ar não melhora com `temperature` diferente — e vai direto
para `fila_revisao`, igual ao caminho de falha de conteúdo esgotada. O número de falhas de transporte entra
num campo novo, `falhas_transporte`, na mesma linha do log de chamadas (`_registrar_log_chamada`), separado
de `tentativas_usadas` (que continua contando só a nova tentativa por temperatura, como pedia a seção 2.1).

**2.2 — seed fixo.** `options.seed = 42` em toda chamada a `/api/generate`, ao lado de `num_ctx` e
`temperature` (armadilha 17: `num_ctx`/`temperature` vão dentro de `options`; `seed` e `num_predict` seguem
o mesmo lugar). `embeddar` não muda — não tem conceito de seed.

**2.3 — teto de tokens de saída.** `TarefaRoteamento` ganhou `num_predict: int` obrigatório (`Field(gt=0)`),
validado pelo Pydantic. Todas as 14 tarefas de `config/llm_routing.yaml`, nos dois perfis (`air16`/`pro48`),
ganharam o campo — valores escolhidos pelo tamanho esperado da saída de cada tarefa (256 para rótulos
curtos como `qualificar`/`rotular`/`desempatar_perfil`; 512 para extrações e avaliações de porte médio;
1024 para `cartao`/`extrair_de_texto`/`extrair_captura_rede_social`/`descrever_imagem`; 2048 para
`redigir_ganchos`, que é a saída mais longa do sistema). `_GeracaoDegenerada` não foi removida — continua
tratando o caso em que o teto não é suficiente para evitar o loop de repetição.

**2.4 — um cliente HTTP só no console.** `config/container.py::http()` sobe de `timeout=120.0` para
`timeout=600.0` (perfil `pro48`, modelo de 14B, pode precisar de mais tempo numa tarefa longa). As três
construções de `ClienteOllama` em `agente_nw/console/app.py` (`_cliente_llm`, `fabrica_llm` dentro de
`_dependencias`, e `conn_fundo` da extração de WhatsApp em segundo plano) passam a usar
`container.http()` em vez de abrir `httpx.Client(timeout=120.0)` a cada chamada — mesmo cliente,
mesmo cache (`functools.lru_cache`), para todo o processo do console. As linhas 137 e 688 (cliente de
coleta de notícia/página, não de Ollama) ficam como estavam, fora de escopo — confirmado pelo grep abaixo.

## 2. Fora do que o brief pediu, mas necessário

- O brief cita as três construções de `ClienteOllama` nas "linhas 97, 132 e 171" de `console/app.py`;
  o arquivo já tinha crescido um pouco desde a redação do brief, e as linhas reais eram 96/131/170 antes
  da edição (e mudaram de novo com os imports novos) — identificadas pelo conteúdo (`httpx.Client(timeout=`
  dentro de uma construção de `ClienteOllama`), não pelo número da linha.
- `_chamar_generate_com_backoff` e `_ir_para_fila_revisao` são métodos novos, não citados no brief —
  extração necessária para não duplicar a lógica de inserção em `fila_revisao` entre o caminho de
  transporte esgotado e o de conteúdo esgotado.
- Valores de `num_predict` por tarefa são estimativa de porte de saída, não um número do brief (que só
  pedia o campo e a validação de inteiro positivo) — ficam como ponto de calibração futura se algum deles
  se mostrar curto demais na prática (ligado ao papel que `_GeracaoDegenerada` continua cobrindo).

## 3. Inspeção (seção 3 do brief)

```
$ grep -n "httpx.Client(timeout" agente_nw/console/app.py
137:            fabrica_http=lambda: httpx.Client(timeout=120.0),
688:        with httpx.Client(timeout=120.0) as cliente_http:
```

Só as duas linhas de coleta (notícia/página) restam; as três de inferência (Ollama) somem, substituídas por
`container.http()`.

## RELATÓRIO FINAL
- Brief executado: 064 — Cliente Ollama resiliente, reproduzível e único no console.
- Arquivos criados: `tests/test_llm_resiliente.py`.
- Arquivos alterados (resumo de uma linha cada):
  - `agente_nw/nucleo/llm.py`: backoff de transporte (2/4/8/16s) separado da nova tentativa por
    temperatura, `seed: 42` e `num_predict` no corpo, campo `falhas_transporte` no log de chamadas.
  - `agente_nw/nucleo/modelos/configuracao.py`: `TarefaRoteamento.num_predict: int` obrigatório (`gt=0`).
  - `config/llm_routing.yaml`: `num_predict` em todas as 14 tarefas, nos dois perfis.
  - `config/container.py`: `http()` sobe de 120 para 600 segundos de timeout.
  - `agente_nw/console/app.py`: as três construções de `ClienteOllama` usam `container.http()` em vez
    de `httpx.Client(timeout=120.0)` próprio.
- Arquivos preservados literalmente na área afetada: `agente_nw/console/app.py` linhas 137 e 688 (cliente
  de coleta, fora de escopo); texto de todo prompt (fora de escopo, item 4 do brief).
- Script de verificação (gate, rodado por `scripts/agente_entregar.sh`; saída colada):
```
manifesto 064: 6 arquivo(s)
ruff check: ok
ruff format: ok
mypy: ok
pytest: ok (861 passed, 5 deselected in 22.90s)
```
- Comandos executados: `.venv/bin/ruff check .`; `.venv/bin/ruff format --check .`; `.venv/bin/mypy agente_nw`;
  `.venv/bin/python -m pytest -q`; `grep -n "httpx.Client(timeout" agente_nw/console/app.py` (seção 3);
  `scripts/agente_entregar.sh 064`.
- Manifesto do commit (`logs/arquivos_064.txt` e `logs/commit_064.txt`, conteúdo colado):
```
logs/arquivos_064.txt:
agente_nw/console/app.py
agente_nw/nucleo/llm.py
agente_nw/nucleo/modelos/configuracao.py
config/container.py
config/llm_routing.yaml
tests/test_llm_resiliente.py

logs/commit_064.txt:
feat(llm): backoff de transporte, seed fixo, teto de tokens e cliente unico no console (brief 064)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
```
- Pendências e decisões que ficaram abertas: nenhuma — o brief já previa que não há pendência de teste
  real para Sidarta (o comportamento só aparece sob falha transitória do Ollama, provada nos testes
  simulados).
- Resumo, Doing, Backlog e Done do `docs/PLAN.md` atualizados: sim.

## Lacunas
Sem lacunas.
