# DOC 077 — Consultar o porteiro antes de cada lote que usa o Ollama local

**Brief:** `docs/briefs/brief_077_integracao_com_o_porteiro_2026-11-06.md`
**Data:** 2026-11-06
**Commit:** `af2a09f`

---

## O que passou a existir

`ClienteOllama` pergunta ao `porteiro` (`~/github/porteiro_local`, o administrador do Ollama
compartilhado desta máquina) se o modelo cabe na memória antes de carregá-lo — nos dois únicos
métodos que carregam modelo, `_chamar` (geração) e `embeddar` (embeddings). Uma consulta por modelo,
por instância do cliente: cada comando de lote da CLI cria o seu via `container.llm()`, então isso é
exatamente a "uma vez no início do lote" que o `INTEGRACAO.md §3` pede, sem um conceito novo de
"início de lote" e sem nenhum dos quinze comandos saber que o `porteiro` existe.

Dois modos, escolhidos por quem constrói o cliente (`selecionar_cliente_llm`):

- `lote` (padrão, e `container.llm()` não passa nada, então é o de toda a CLI): código `1` ("não
  cabe sem tirar outro modelo") espera 60 s e consulta de novo, até 16 consultas — os 15 minutos do
  documento — e ao final roda assim mesmo;
- `interativo` (as três construções de `agente_nw/console/app.py`, com uma pessoa esperando):
  consulta uma vez, nunca espera, roda sempre.

Em nenhum dos dois o `porteiro` impede a chamada: ele só atrasa o modo `lote`. Programa ausente,
timeout de 30 s, JSON ilegível, JSON sem `codigo_de_saida`, código `2` ou código `3` degradam para
o comportamento de antes deste brief — rodar na hora. Toda resposta diferente de `0` vira uma linha
`{"porteiro": true, ...}` em `dados/logs/chamadas_llm.jsonl`, com modelo, porta, código, razão e o
aviso; em uso normal (memória com espaço) nenhuma linha nova aparece.

A porta vem de `httpx.URL(self._ollama_url).port`, isto é, da `ollama_url` que o cliente já recebe —
nunca de uma constante nova, e `ollama_url` não foi tocada. Sem porta explícita na URL, nem consulta
acontece (degrada em vez de inventar porta). O modelo consultado é sempre o que já ia para o Ollama
(`tarefa.modelo` ou `perfil.embeddings.modelo`): o `porteiro` pergunta e loga, nunca troca modelo,
porta ou estado do serviço.

Com um provedor de API cadastrado (`ia_api`, brief 076), a geração não consulta nada — não toca o
Ollama —, mas `embeddar` é repasse ao `ClienteOllama` injetado (brief 075, item 3.5), então os
embeddings, que são sempre locais, continuam passando pelo `porteiro`. Está provado por teste.

---

## RELATÓRIO FINAL

- **Brief executado:** 077 — consultar o porteiro antes de cada lote que usa o Ollama local
  (`docs/briefs/brief_077_integracao_com_o_porteiro_2026-11-06.md`).

- **Arquivos criados:**
  - `tests/test_porteiro.py` — 23 testes, escritos antes do código: a forma exata do comando do
    `porteiro` (caminho completo com o Python na frente, `cabe`, `--porta`, `--json`), as cinco
    degradações de `_consultar_porteiro` para `None`, o modo `lote` (código `0` sem espera e sem
    aviso; código `1` nas 16 consultas com 15 esperas de 60 s e aviso; liberação na terceira
    consulta com 2 esperas e **nenhum** aviso; `porteiro` ausente; códigos `2` e `3` rodando na
    hora com aviso), o modo `interativo` (zero esperas, uma consulta, aviso), a memoização por
    modelo (mesma tarefa duas vezes = uma consulta; duas tarefas de modelos diferentes = uma
    consulta cada; o backoff de transporte do brief 064 não reconsulta), `embeddar` consultando pelo
    `bge-m3`, o cliente de API disparando a consulta ao repassar `embeddar`, a porta vindo da
    `ollama_url`, a URL sem porta não consultando, `selecionar_cliente_llm` repassando o modo, e a
    não-regressão de camada (console interativo nos três pontos, `container.llm()` no padrão `lote`).
    Nenhum teste chama o `porteiro` real, nem precisa dele instalado.
  - `docs/docs/doc_077_integracao_com_o_porteiro_2026-11-06.md` (este arquivo).
  - `logs/commit_077.txt`, `logs/arquivos_077.txt`.

- **Arquivos alterados (com resumo da mudança em uma linha cada):**
  - `agente_nw/nucleo/llm.py` — constantes `_PORTEIRO_PYTHON`/`_PORTEIRO_BIN`/timeout/espera/16
    consultas, os três textos de aviso, o alias `ModoPorteiro`, a função de módulo
    `_consultar_porteiro` (subprocesso que nunca levanta) e, em `ClienteOllama`, o parâmetro
    `modo_porteiro`, o conjunto `_modelos_verificados_porteiro`,
    `_verificar_porteiro_antes_de_carregar`, `_registrar_aviso_porteiro` e uma linha de chamada
    antes de cada `post` (geração e embeddings).
  - `config/container.py` — `selecionar_cliente_llm` recebe `modo_porteiro: ModoPorteiro = "lote"` e
    o repassa ao `ClienteOllama` que sempre constrói; `llm()` não passa nada, ficando no padrão.
  - `agente_nw/console/app.py` — as três construções de cliente (`_cliente_llm`, `fabrica_llm` em
    `_dependencias` e a de `_processar_whatsapp_em_fundo`) passam `modo_porteiro="interativo"`.
  - `AGENTS.md` — §3, uma linha nova antes da linha de saída estruturada, com o texto do item 3.7 do
    brief.
  - `docs/ARQUITETURA.md` — §8, um parágrafo novo ao final ("Porteiro, o admin do Ollama
    compartilhado"), sem reescrever nada do que já havia sobre Ollama, perfis ou provedores de API.

- **Arquivos preservados literalmente na área afetada:** `_ClienteLLMBase` inteiro (nenhuma linha de
  `gerar_json`, `_chamar_com_backoff`, `_registrar_log_chamada`, `_tarefa`, `proveniencia` ou
  `_ir_para_fila_revisao` mudou — o `porteiro` é só do `ClienteOllama`, o único que carrega modelo);
  `_ClienteApiBase`, `ClienteAnthropic`, `ClienteGemini`, `ClienteOpenAI` e as três funções
  `_texto_da_resposta_*`; `config/local.yaml`, `config/llm_routing.yaml` e `config/limiares.yaml`
  (nenhum modelo, porta ou URL tocado, como o brief e o `INTEGRACAO.md §8` exigem);
  `agente_nw/cli.py` (nenhuma linha: `criar_app` não ganhou parâmetro e `llm()` não mudou de
  assinatura); `tests/test_llm_resiliente.py` e `tests/test_llm_api.py` — nenhuma asserção editada,
  como o aceite do brief pede.

- **Script de verificação (o gate, rodado pelo `scripts/agente_entregar.sh`; saída colada):**

```
$ scripts/agente_entregar.sh 077
manifesto 077: 5 arquivo(s)
ruff check: ok
ruff format: ok
mypy: ok
pytest: ok (979 passed, 5 deselected in 21.51s)
lacunas do 077: 0 no Backlog, 0 em Pendências, 3 em Dívidas, 1 em Decisões
✓ brief 077: commit af2a09f, enviado ao GitHub
```

- **Comandos executados:**

```
$ .venv/bin/python -m pytest tests/test_porteiro.py -q
.......................                                                  [100%]
23 passed in 0.79s

$ .venv/bin/python -m pytest -q
[...]
979 passed, 5 deselected in 22.72s

$ .venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/mypy agente_nw
All checks passed!
288 files already formatted
Success: no issues found in 122 source files

$ git status --short
 M AGENTS.md
 M agente_nw/console/app.py
 M agente_nw/nucleo/llm.py
 M config/container.py
?? tests/test_porteiro.py
```

  Os 979 testes são os 956 do brief 076 mais os 23 novos: nenhum teste anterior foi editado nem
  removido, o que é a prova pedida de que o comportamento de antes não mudou.

- **Manifesto do commit (`logs/arquivos_077.txt` e `logs/commit_077.txt`, conteúdo colado):**

`logs/arquivos_077.txt`:

```
agente_nw/nucleo/llm.py
config/container.py
agente_nw/console/app.py
tests/test_porteiro.py
AGENTS.md
```

`logs/commit_077.txt`:

```
feat(llm): consulta o porteiro antes de carregar modelo no Ollama local (brief 077)

ClienteOllama pergunta ao porteiro (admin do Ollama compartilhado da maquina) se o
modelo cabe antes de _chamar e de embeddar, uma vez por modelo por instancia, pela
porta da propria ollama_url. Modo lote (padrao, toda a CLI) espera 60s e reconsulta
enquanto o codigo for 1, ate 16 consultas, e roda assim mesmo; modo interativo (as
tres construcoes do console) consulta uma vez e nunca espera. Ausencia, timeout de
30s, JSON ilegivel ou erro do porteiro degradam para o comportamento de antes. O que
nao for "cabe" vira linha {"porteiro": true, ...} em chamadas_llm.jsonl. O porteiro
nunca troca modelo ou porta, nunca sobe ou para o Ollama e nunca impede a chamada.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

  `docs/` é ignorado pelo git (`.gitignore`: `docs/*`, só `docs/.gitkeep` exempto; `git ls-files
  docs/` devolve vazio), então este relatório e o parágrafo novo da ARQUITETURA não entram no
  manifesto — por isso o brief pede a ARQUITETURA como arquivo-alvo e ela não aparece na lista
  acima. `AGENTS.md`, que é rastreado, entra.

- **Pendências e decisões que ficaram abertas:** só a do próprio brief, que exige a máquina de
  Sidarta com o `porteiro` instalado: rodar um lote de verdade (ex.: `agente_nw qualificar`) e
  conferir em `dados/logs/chamadas_llm.jsonl` que, em uso normal, nenhuma linha nova aparece, e que,
  com a memória cheia, aparece a linha `"porteiro": true` com o aviso. Nada do que ficou aberto é
  defeito ou verificação ao alcance do executor. O cadastro do agente_nw no mapa de portas do
  `porteiro` é do outro repositório (ver Lacunas).

- **Resumo, Doing, Backlog e Done do `docs/PLAN.md` atualizados:** sim.

---

## Duas conferências que o brief pedia e que valem registro

**A consulta não acontece dentro do laço do backoff.** `_chamar` é chamado até cinco vezes por
`_chamar_com_backoff` (brief 064) e até dez vezes por `gerar_json` (duas temperaturas). A memoização
por modelo faz com que, nesse pior caso, haja **uma** consulta ao `porteiro`, não dez — está provado
por `test_a_nova_tentativa_por_transporte_nao_reconsulta_o_porteiro`, que força um 503 e confere uma
só consulta.

**A chave de API, quando houver, não passa pelo subprocesso.** `_consultar_porteiro` recebe só
`modelo` e `porta`; a linha de comando montada tem sete itens fixos e nada do prompt, da chave ou do
texto do contato. Uma lista de argumentos de subprocesso é visível no `ps` da máquina, e é por isso
que nada além do nome do modelo vai nela.

---

## Lacunas

| # | Lacuna | Destino | Impacto |
|---|---|---|---|
| 1 | `_PORTEIRO_PYTHON` e `_PORTEIRO_BIN` são caminhos absolutos desta máquina, fixos em `nucleo/llm.py` — o brief pede exatamente isso (item 3.4, e torná-los configuráveis está no fora de escopo), mas contraria o "sem hardcode de caminhos" do AGENTS §4. Noutra máquina, ou se o prefixo do Homebrew mudar, o `porteiro` simplesmente não é encontrado e o projeto roda como antes | dívida | nice |
| 2 | O console Flask constrói um cliente por requisição (`_cliente_llm` vive no `g`), e a memoização é por instância: no console a consulta ao `porteiro` acontece uma vez por requisição que use LLM, não uma por sessão. É o modo `interativo` (uma consulta, sem espera nenhuma), então o custo é de 1 a alguns segundos por requisição. Um cache por processo resolveria, mas contrariaria a decisão 3.2 do brief | dívida | nice |
| 3 | O agente_nw não está no mapa de portas do `porteiro` (`INTEGRACAO.md §2`: "ainda não tem porta confirmada"). A consulta funciona porque a porta `11435` já é uma das configuradas lá, mas o mapa do outro repositório não registra este projeto; cadastrar é do lado do `porteiro_local`, fora do fluxo de briefs daqui | decisão | nice |
| 4 | No modo `lote`, a espera de até 15 min é um `time.sleep` dentro de `_chamar`: enquanto ela corre, o lote não lê a sentinela `dados/PARE` nem imprime nada, então um `Ctrl-C` é a única saída. É o comportamento que o brief pede (e o lote sempre termina rodando), mas é uma janela em que o processo parece travado | dívida | nice |
