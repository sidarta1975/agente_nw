# Brief 035 — Reconsulta no mesmo dia substitui o menu; `evitar` antes da seleção; pesos no YAML; coleta sem `fontes.yaml`

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Base:** `main` após o commit do brief 034.
**Origem:** pendências b, d, e, f do relatório final do brief 034. A pendência a (vetores extras na qualificação) está aceita e já faz parte do commit do 034; a pendência c (exibir `ponto_de_apoio` na tela) fica recusada — o "por quê" já o incorpora pelo prompt.
**Data:** 2026-10-08

---

## 1. Objetivo em uma frase

Permitir que o usuário repita a consulta sobre o mesmo contato no mesmo dia — mudando o contexto, acrescentando `evitar` ou uma tag — e receba um menu recalculado, sem itens presos nem assuntos escondidos para sempre; e tirar do código os pesos que são calibração.

---

## 2. O que está errado hoje (verificado no código após o brief 034)

1. **`assunto_contato.listar_assunto_ids_ja_vistos`** devolve todo `assunto_id` que já apareceu para o contato, em qualquer status, em qualquer dia. Consequência: um assunto que apareceu no menu de hoje (status `novo`) ou foi descartado por `evitar` nunca mais é candidato para aquele contato. Repetir a consulta no mesmo dia não recalcula nada — e os critérios de aceite 2 e 3 do brief 034 ficam impossíveis.
2. **`cruzamento.cruzar_contato_por_consulta`** aplica `_termo_evitado` depois de `selecionar_por_consulta` já ter escolhido os 10 candidatos: os evitados ocupam vaga, e o menu encolhe.
3. **Pesos como constantes de código**: `_PESO_CONSULTA_NO_SCORE`, `_PESO_CONTATO_NO_SCORE`, `_PESO_USUARIO_NO_SCORE`, `_PESO_CONVERSAVEL_NO_SCORE` em `pontuacao.py` e `_PESO_CONSULTA`, `_PESO_CONTATO` em `candidatos.py`. Contraria a regra do `AGENTS.md` ("valores calibrados nunca no código").
4. **`consulta.preparar`** só coleta se `fontes.yaml` existir (`if rodar_coleta and caminho_fontes.exists()`), mesmo tendo as consultas do Google News geradas a partir do contexto.

---

## 3. Decisões

**3.1. "Já visto" passa a significar "o usuário já decidiu sobre ele".** `listar_assunto_ids_ja_vistos` passa a considerar só `status IN ('usado', 'nao_serve')`. Assuntos mostrados e não marcados (`novo`) e assuntos descartados pelo motor (`descartado`, inclusive por `evitar`) voltam a ser candidatos em consultas futuras — a decisão de esconder é do usuário, não do motor. O comando `cruzar` legado usa a mesma função e herda o comportamento; isso é intencional e fica registrado no `AGENTS.md`.

**3.2. Reconsulta no mesmo dia substitui o menu do dia.** No início de `cruzar_contato_por_consulta`, apagar as linhas de `assunto_contato` do contato com `gerado_em = hoje` e `status IN ('novo', 'descartado')`. Linhas `usado` e `nao_serve` do dia permanecem (e continuam fora dos candidatos por 3.1). Com isso a restrição `UNIQUE (assunto_id, perfil_id, gerado_em)` nunca é violada e o menu reflete o último contexto digitado. A consulta anterior continua no histórico permanente (`consulta_contato`), que não é tocado.

**3.3. `evitar` filtra antes da seleção.** Mover `_termo_evitado` para dentro do fluxo de candidatos: `selecionar_por_consulta` recebe `evitar: list[str]` e exclui os evitados **antes** de cortar em `candidatos_por_contato`. Os evitados continuam sendo gravados como `descartado`, `motivo="evitado pelo contexto"`, para o contador da tela — mas não ocupam vaga.

**3.4. Pesos vão para `config/limiares.yaml`.** Bloco `conector` ganha:

```yaml
  consulta:
    peso_consulta: 50
    peso_contato: 25
    peso_usuario: 10
    peso_conversavel: 15
    selecao_peso_consulta: 0.7
    selecao_peso_contato: 0.3
```

`ConectorLimiares` ganha o submodelo `ConsultaLimiares` com esses seis campos (validador: os quatro primeiros somam 100; os dois últimos somam 1). As constantes de código são removidas; `avaliar_por_consulta` e `selecionar_por_consulta` leem de `limiares.conector.consulta`. `consulta_minima` (brief 034) migra para dentro do mesmo bloco, como `minima`.

**3.5. Coleta roda com ou sem `fontes.yaml`.** Em `preparar`: se `rodar_coleta`, chamar `leitor_rss.coletar` com os feeds do arquivo quando ele existir mais os `feeds_extras` do contexto; sem o arquivo, só os extras. `leitor.coletar` aceita `caminho_fontes: Path | None`.

---

## 4. Escopo (arquivos)

1. `agente_nw/nucleo/database/queries/assunto_contato.py`: `listar_assunto_ids_ja_vistos` (3.1); nova `apagar_nao_decididos_do_dia(conexao, perfil_id, data) -> int` (3.2).
2. `agente_nw/nucleo/relevancia/cruzamento.py`: chamar `apagar_nao_decididos_do_dia` no início de `cruzar_contato_por_consulta`; passar `contexto.evitar` para a seleção; remover o filtro pós-seleção.
3. `agente_nw/nucleo/relevancia/candidatos.py`: `selecionar_por_consulta(..., evitar, limiares_consulta)`; filtro antes do corte; pesos do YAML; devolver também a lista dos evitados para gravação.
4. `agente_nw/nucleo/relevancia/pontuacao.py`: pesos do YAML; constantes removidas.
5. `agente_nw/nucleo/modelos/configuracao.py` + `config/limiares.yaml`: `ConsultaLimiares` (3.4), com `minima` absorvendo `consulta_minima`.
6. `agente_nw/coleta/rss/leitor.py` + `agente_nw/nucleo/consulta.py`: coleta sem `fontes.yaml` (3.5).
7. `AGENTS.md`, seção 7: "Um assunto só deixa de ser candidato para um contato quando o usuário o marca como usado ou como não serve; reconsultar no mesmo dia substitui o menu do dia."
8. Testes existentes que montam `ConectorLimiares` (os 18 do brief 034): atualizar para o submodelo.

---

## 5. Testes novos

- `tests/test_reconsulta_mesmo_dia.py`: (1) duas chamadas de `cruzar_contato_por_consulta` no mesmo dia com contextos diferentes → segunda chamada substitui as linhas `novo`/`descartado` do dia, mantém uma linha `usado` criada entre as duas, e não viola o UNIQUE; (2) assunto descartado por `evitar` na primeira chamada volta ao menu na segunda, sem `evitar`; (3) assunto `nao_serve` de ontem não aparece hoje.
- `tests/test_candidatos_por_consulta.py` (acrescentar): com 12 candidatos e 3 evitados, a seleção devolve 10 não evitados (não 7).
- `tests/test_configuracao.py` (acrescentar): `ConsultaLimiares` rejeita pesos que não somam 100 / 1; `limiares.yaml` versionado valida.
- `tests/test_consulta_preparar.py` (acrescentar): `preparar` com `caminho_fontes` inexistente e `rodar_coleta=True` chama a coleta com os feeds do contexto.

---

## 6. Fora de escopo

- Exibir `ponto_de_apoio` na tela (pendência c do 034): recusado.
- Calibrar os pesos: continuam os valores do brief 034, agora no YAML; calibração vem do uso.
- Qualquer mudança em `avaliar`, `cruzar_contato` e `candidatos.selecionar` além do efeito de 3.1 em `listar_assunto_ids_ja_vistos`.

---

## 7. Passos de execução

1. `ConsultaLimiares` + `limiares.yaml`; atualizar os testes que montam `ConectorLimiares`.
2. `assunto_contato`: 3.1 e 3.2.
3. `candidatos`/`pontuacao`/`cruzamento`: 3.3 e pesos do YAML.
4. `leitor`/`consulta`: 3.5.
5. `AGENTS.md` seção 7.
6. Testes da seção 5.
7. Entregar lista para `git add` e mensagem: `fix(consulta): reconsulta no mesmo dia substitui o menu, evitar antes da seleção, pesos em limiares.yaml, coleta sem fontes.yaml (brief 035)`.

`scripts/verificar.sh`, o teste no navegador (critérios 1–4 do brief 034, agora viáveis no mesmo dia) e o commit são passos de Sidarta, no terminal dele.
