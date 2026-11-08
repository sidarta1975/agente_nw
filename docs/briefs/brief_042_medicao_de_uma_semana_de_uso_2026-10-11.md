# Brief 042 — Medição de uma semana de uso real

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Depende de:** briefs 036 a 041 implementados e em uso no Pro por pelo menos sete dias corridos.
**Plano:** v3.1, último brief de código. Só leitura e relatório; nenhuma alteração de comportamento do produto.
**Data:** 2026-10-11

---

## 1. Objetivo em uma frase

Medir, com os dados que o próprio sistema gravou, se o produto do plano v3.1 funciona no uso real — e decidir, com número, os ajustes de prompt, a calibração dos limiares e se o modelo de 4 B do Air sustenta a redação.

---

## 2. O que já existe e é lido

- `pedido` (036/039): texto, `extraido_json`, `confianca`, `status`, `etapa`, `erro`, `pedido_pai_id` (correções), `criado_em`.
- `localizacao_json` (037/039): desfecho (`claro`/`ambiguo`/`nenhum`), fonte, escolha do usuário.
- `consulta_contato` + `gancho_uso` (038): ganchos entregues, `usado`, `nao_serve`.
- `dados/logs/chamadas_llm.jsonl`: por tarefa, tentativas e sucesso (brief 013).
- `assunto_contato.aderencia_consulta` (034/035): distribuição dos cossenos, para calibrar `consulta.minima`.
- `perfil_tema` do usuário (040): temas inferidos.

---

## 3. O relatório (`agente_nw medir --desde AAAA-MM-DD --ate AAAA-MM-DD`)

Imprime e grava em `saidas/medicao_<desde>_<ate>.md`. Seções, cada uma com o número e, quando houver, a leitura automática em uma linha:

1. **Uso.** Pedidos por dia; pessoas distintas; pedidos de continuação; correções (pedidos com `pedido_pai_id`) e motivo mais comum (as 10 correções mais recentes, texto integral).
2. **Extração.** Distribuição de `confianca`; proporção de pedidos corrigidos em menos de 5 minutos (proxy de extração errada); campos mais corrigidos (comparação entre `extraido_json` do pai e do filho).
3. **Localização da pessoa.** Desfechos por tipo; proporção em que a primeira opção foi a escolhida; quantas vezes "mostrar a lista" e "colar link" foram usados; tempo médio entre `aguardando_pessoa` e a resposta.
4. **Ganchos.** Entregues, usados, não serve, ignorados; **taxa de uso** (usados ÷ pedidos concluídos) — o número principal do produto; por registro (`proximo/cordial/formal`) e por objetivo.
5. **Tempo.** Duração por etapa (diferença entre atualizações de `etapa`): extração, localização, coleta, leitura de rede, seleção, redação; p50 e p90.
6. **Modelo.** Por tarefa (`extrair_pedido`, `desempatar_perfil`, `redigir_ganchos`, `qualificar`, `cruzar_por_que`, …): chamadas, sucesso em 1 tentativa, em 2, falhas para `fila_revisao`.
7. **Calibração.** Histograma de `aderencia_consulta` dos itens entregues × usados × não serve; sugestão de `consulta.minima` como o percentil 20 dos usados (só sugestão, impressa, não aplicada).
8. **Temas inferidos.** Lista com nível e peso; quantos vieram de declaração × de pedidos.
9. **Erros.** Pedidos com `status='erro'` por etapa e mensagem.

---

## 4. Decisões que o relatório alimenta (tomadas por Sidarta, registradas em um brief seguinte)

- Taxa de uso abaixo de 40 % → revisar prompt de redação (038) com os 10 ganchos "não serve" mais recentes como contraexemplos.
- Mais de 30 % dos pedidos corrigidos em menos de 5 minutos → revisar prompt de extração (036) com as correções como exemplos.
- Primeira opção certa em menos de 70 % das localizações → revisar pontuação de pistas (037).
- Falha de JSON acima de 5 % em qualquer tarefa → ajustar `num_ctx`/temperatura ou dividir o prompt.
- Percentil sugerido para `consulta.minima` distante de 0,45 → ajustar `limiares.yaml`.
- Se o mesmo relatório rodado no Air (`air16`) mostrar taxa de uso inferior à metade da do Pro → redação no Air passa a `qwen3:8b` (perfil) ou fica restrita ao Pro.

---

## 5. Escopo (arquivos)

1. `nucleo/medicao.py`: funções puras de agregação sobre as tabelas e o log; sem chamada a modelo.
2. `cli.py`: comando `medir --desde --ate [--saida caminho]`.
3. `tests/test_medicao.py`: banco de fixture com 20 pedidos sintéticos cobrindo todos os status, desfechos e marcações → números esperados por seção; `chamadas_llm.jsonl` de fixture.
4. `AGENTS.md`, seção 9 (certificação): "a medição de uso é `agente_nw medir`; o `certificar` continua para a validade de JSON".

---

## 6. Fora de escopo

- Qualquer alteração de prompt, limiar ou modelo — vira brief próprio depois do relatório.
- Telemetria fora da máquina. Tudo fica em `dados/` e `saidas/`.

---

## 7. Passos de execução

1. `nucleo/medicao.py`.
2. `cli.py`.
3. Teste com fixture.
4. `AGENTS.md`.
5. Lista para `git add` e mensagem: `feat(medicao): relatório de uso real — extração, localização, ganchos, tempo, modelo, calibração (brief 042)`.

`scripts/verificar.sh`, a execução do relatório após sete dias de uso e o commit são passos de Sidarta.

---

## 8. Critérios de aceite

1. `agente_nw medir --desde <D> --ate <D+7>` roda sobre o banco real do Pro e produz o arquivo em `saidas/` com as nove seções preenchidas.
2. Os números batem com uma conferência manual de três deles (pedidos por dia, ganchos usados, chamadas por tarefa) feita por consulta direta ao banco.
3. Sidarta consegue, só com o relatório, decidir cada item da seção 4 sem abrir o código.
