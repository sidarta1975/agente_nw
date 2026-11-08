# DOC 068 — Defesa contra injeção de prompt no texto coletado

**Brief:** `docs/briefs/brief_068_defesa_injecao_prompt_2026-11-02.md`
**Data:** 2026-11-02
**Executor:** Claude Code (Opus, por indicação do cabeçalho do brief)

## 1. O que mudou

- `agente_nw/nucleo/prompts/seguranca.py` (novo): `MARCADOR_INICIO = "<<<DADO_EXTERNO_NAO_INSTRUCAO>>>"`, `MARCADOR_FIM = "<<<FIM_DADO_EXTERNO>>>"`, `INSTRUCAO_DADO_EXTERNO` (a frase fixa da seção 3.1, citando os dois marcadores) e `cercar_dado_externo(texto) -> str`, que devolve `MARCADOR_INICIO\n<texto>\nMARCADOR_FIM`. Antes de cercar, toda ocorrência de um dos dois marcadores dentro do texto (em qualquer caixa) tem os `<` e `>` trocados por espaços (seção 3.2): o bloco final tem exatamente um marcador de abertura e um de fechamento.
- **Forma da "instrução uma vez só":** a função só cerca; a instrução é a constante `INSTRUCAO_DADO_EXTERNO`, que cada módulo põe uma vez no próprio template, logo antes da seção com o primeiro bloco cercado. Em `redigir_ganchos`, ela entra como bloco próprio antes do HISTÓRICO e só quando o HISTÓRICO ou os ASSUNTOS trazem algum bloco cercado; sem dado externo, o prompt não muda além disso.
- Os nove módulos, cada um conferido no código:

| Módulo | Cercado | Não cercado (e por quê) |
|---|---|---|
| `extrair_de_texto.py` | `texto` | — |
| `cartao.py` | `titulo`; de cada item, `item_titulo` e `trecho` | `dominio` (nome do veículo, não texto livre) |
| `cruzar_por_que.py` | `titulo` de cada assunto | `tipo` (enum), `ponto_de_apoio`, temas e contexto (do usuário) |
| `avaliar_relacao_objetivo.py` | `titulo` e `resumo` de cada candidato | `objetivo`, `frase` (do usuário), `ficha_contato` (fora da enumeração "título e resumo") |
| `qualificar.py` | `titulo`; `item_titulo` de cada item | `dominio`, `temas_conhecidos` |
| `rotular.py` | `titulo` de cada item | `dominio` |
| `prerotular_calibracao.py` | `titulo_a`, `trecho_a`, `titulo_b`, `trecho_b` | — |
| `desempatar_perfil.py` | cada cabeçalho de candidato (nome + bio lidos da rede, `localizacao.py:104`) | `nome` e `pistas` (o que o usuário digitou/sabe) |
| `redigir_ganchos.py` | `titulo`, `resumo` e manchetes (unidas por " \| ", um bloco) de cada assunto; a conversa do WhatsApp inteira (um bloco) | notas e comentários do usuário (brief 050), `por_que`, `historico`, fatos, `cabecalho_rede`, ficha, moldes, pedido — fora do texto literal do brief (ver Lacunas 1) |

- `redigir_ganchos.py`: o cerco é aplicado na montagem (`_bloco_historico`, `_bloco_assuntos`, chamados por `_montar`), nunca guardado em `EntradaRedacao`. `cortar_por_tamanho` continua cortando as listas cruas (`historico`, `fatos`, `moldes`, `trocas_whatsapp`) e mede `_montar(...)`, ou seja, o prompt já com os marcadores, que é exatamente o texto que vai ao modelo.
- `VERSAO` dos nove módulos atualizada para `2026-11-02-1` (`redigir_ganchos`: `2026-11-02-2`, já tinha `-1` hoje), pela regra do brief 066 ("data do último ajuste de conteúdo do prompt"). `seguranca.py` também declara `VERSAO`, porque `verificar_versoes()` (brief 066) exige `VERSAO` de todo módulo do pacote `nucleo/prompts/` e o brief põe o arquivo novo nesse pacote.
- O texto cercado perde as aspas que o envolviam na linha (`"{titulo}"` virou o bloco cercado): os marcadores fazem o papel de delimitador. O exemplo resolvido de cada prompt ficou como estava (seção 5 do brief: nada muda além de envolver o texto de terceiro).
- Testes: `tests/test_seguranca_prompt.py` (novo, 15 testes). Os clientes de LLM simulados de seis testes existentes contavam candidatos e assuntos pela forma antiga da linha (`'" — '`, `'" — tipo:'`, uma linha por candidato); passaram a usar dois ajudantes novos em `tests/llm_falso.py` (`candidatos_do_prompt`, `quantidade_assuntos_do_prompt`). `tests/test_redacao_prompt.py` passa a esperar o título cercado.

## 2. Verificação

Teste de aceite (criado antes do código):

```
$ .venv/bin/pytest tests/test_seguranca_prompt.py -q
...............                                                          [100%]
15 passed in 0.08s
```

Teste com o Ollama real (fora do gate, marcador `llm_real`), o único `llm_real` sobre um dos nove prompts (`extrair_de_texto`, já cercado), contra `127.0.0.1:11435`, banco isolado em `tmp_path`:

```
$ .venv/bin/pytest tests/test_extrator.py -m llm_real -q
.                                                                        [100%]
1 passed in 17.20s
```

Cobertura dos nove módulos (seção 6 do brief):

```
$ grep -rl "cercar_dado_externo" agente_nw/nucleo/prompts/ | sort
agente_nw/nucleo/prompts/avaliar_relacao_objetivo.py
agente_nw/nucleo/prompts/cartao.py
agente_nw/nucleo/prompts/cruzar_por_que.py
agente_nw/nucleo/prompts/desempatar_perfil.py
agente_nw/nucleo/prompts/extrair_de_texto.py
agente_nw/nucleo/prompts/prerotular_calibracao.py
agente_nw/nucleo/prompts/qualificar.py
agente_nw/nucleo/prompts/redigir_ganchos.py
agente_nw/nucleo/prompts/rotular.py
agente_nw/nucleo/prompts/seguranca.py
```

Gate e entrega (primeira tentativa, verde):

```
$ scripts/agente_entregar.sh 068
manifesto 068: 19 arquivo(s)
ruff check: ok
ruff format: ok
mypy: ok
pytest: ok (894 passed, 5 deselected in 25.87s)
lacunas do 068: 2 no Backlog, 0 em Pendências, 0 em Dívidas, 1 em Decisões
✓ brief 068: commit ea66368, enviado ao GitHub
```

```
To https://github.com/sidarta1975/agente_nw.git
   bedee71..ea66368  main -> main
```

## RELATÓRIO FINAL
- Brief executado: 068 — defesa contra injeção de prompt no texto coletado.
- Arquivos criados: `agente_nw/nucleo/prompts/seguranca.py`, `tests/test_seguranca_prompt.py`, `docs/docs/doc_068_defesa_injecao_prompt_2026-11-02.md`, `logs/commit_068.txt`, `logs/arquivos_068.txt`.
- Arquivos alterados (com resumo da mudança em uma linha cada):
  - `agente_nw/nucleo/prompts/extrair_de_texto.py`: texto a processar cercado; instrução antes dele; `VERSAO` 2026-11-02-1.
  - `agente_nw/nucleo/prompts/cartao.py`: título do assunto, título e trecho de cada item cercados; instrução; `VERSAO`.
  - `agente_nw/nucleo/prompts/cruzar_por_que.py`: título de cada assunto cercado; instrução antes de "Assuntos:"; `VERSAO`.
  - `agente_nw/nucleo/prompts/avaliar_relacao_objetivo.py`: título e resumo de cada candidato cercados; instrução antes de "Candidatos:"; `VERSAO`.
  - `agente_nw/nucleo/prompts/qualificar.py`: título do assunto e de cada item cercados; instrução; `VERSAO`.
  - `agente_nw/nucleo/prompts/rotular.py`: título de cada item cercado; instrução; `VERSAO`.
  - `agente_nw/nucleo/prompts/prerotular_calibracao.py`: os dois títulos e os dois trechos cercados; instrução; `VERSAO`.
  - `agente_nw/nucleo/prompts/desempatar_perfil.py`: cabeçalho de cada candidato real cercado (`_linhas_cercadas`; o exemplo segue em `_linhas`); instrução; `VERSAO`.
  - `agente_nw/nucleo/prompts/redigir_ganchos.py`: título, resumo e manchetes de cada assunto e a conversa do WhatsApp cercados na montagem; notas do usuário não; instrução só havendo bloco cercado; `VERSAO` 2026-11-02-2.
  - `tests/llm_falso.py`: ajudantes `candidatos_do_prompt` e `quantidade_assuntos_do_prompt` para os clientes simulados lerem o prompt cercado.
  - `tests/test_cruzamento_por_consulta.py`, `tests/test_evitar_implicito.py`, `tests/test_gate_lote_ordem.py`, `tests/test_gate_objetivo.py`, `tests/test_gate_zera_menu.py`, `tests/test_reconsulta_mesmo_dia.py`: cliente simulado conta candidatos/assuntos pelos ajudantes, em vez da forma antiga da linha.
  - `tests/test_redacao_prompt.py`: espera o título do assunto cercado.
- Arquivos preservados literalmente na área afetada: `agente_nw/nucleo/prompts/__init__.py`, `extrair_pedido.py`, `descrever_tema.py` (seção 3.4), `exemplos_conversavel.yaml`; `agente_nw/nucleo/redacao.py`, `agente_nw/nucleo/localizacao.py`, `agente_nw/nucleo/relevancia/cruzamento.py` (chamadores, sem mudança de assinatura).
- Script de verificação (o gate, rodado pelo `scripts/agente_entregar.sh`; saída colada): ver seção 2.
- Comandos executados: `.venv/bin/pytest tests/test_seguranca_prompt.py -q`; `.venv/bin/pytest -q`; `.venv/bin/ruff format`; `.venv/bin/ruff check .`; `.venv/bin/mypy agente_nw`; `.venv/bin/pytest tests/test_extrator.py -m llm_real -q`; `grep -rn "cercar_dado_externo" agente_nw/nucleo/prompts/`; `scripts/agente_entregar.sh 068`.
- Manifesto do commit (`logs/arquivos_068.txt` e `logs/commit_068.txt`, conteúdo colado):

```
agente_nw/nucleo/prompts/seguranca.py
agente_nw/nucleo/prompts/extrair_de_texto.py
agente_nw/nucleo/prompts/cartao.py
agente_nw/nucleo/prompts/cruzar_por_que.py
agente_nw/nucleo/prompts/avaliar_relacao_objetivo.py
agente_nw/nucleo/prompts/qualificar.py
agente_nw/nucleo/prompts/rotular.py
agente_nw/nucleo/prompts/prerotular_calibracao.py
agente_nw/nucleo/prompts/desempatar_perfil.py
agente_nw/nucleo/prompts/redigir_ganchos.py
tests/test_seguranca_prompt.py
tests/llm_falso.py
tests/test_cruzamento_por_consulta.py
tests/test_evitar_implicito.py
tests/test_gate_lote_ordem.py
tests/test_gate_objetivo.py
tests/test_gate_zera_menu.py
tests/test_reconsulta_mesmo_dia.py
tests/test_redacao_prompt.py
```

```
feat(prompts): texto de terceiro entra no prompt cercado como dado, nunca como instrucao (brief 068)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
```

- Pendências e decisões que ficaram abertas: ver Lacunas (a 1 é decisão de Sidarta).
- Resumo, Doing, Backlog e Done do `docs/PLAN.md` atualizados: sim.

## Lacunas

| # | Lacuna | Destino | Impacto |
|---|---|---|---|
| 1 | Em `redigir_ganchos`, continuam sem cerco textos que também vêm de terceiro, mas que o brief 068 não lista para esse módulo: `fatos` (extraídos de captura de rede e do WhatsApp), `cabecalho_rede` (bio lida da rede), `historico` (ganchos antigos) e `por_que` (saída do `cruzar_por_que`, que leu o título da notícia). Sidarta decide se entram no cerco | decisão | degrada |
| 2 | `extrair_captura_rede_social`, `descrever_imagem` e `extrair_termos_contato` montam prompt com texto de terceiro fora de `nucleo/prompts/` e não usam `cercar_dado_externo` (o brief 068 cobriu só os nove módulos) | backlog | degrada |
| 3 | O exemplo resolvido de cada prompt ficou sem cerco enquanto o dado real está cercado (seção 5 do brief); só `extrair_de_texto` tem teste `llm_real` e passou, os outros oito prompts não têm teste com o modelo real que confirme a saída depois do cerco | backlog | nice |
