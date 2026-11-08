# Doc 049 — Só vira gancho a notícia que o modelo julga ligada ao objetivo

Brief: `docs/briefs/brief_049_juizo_de_relacao_com_o_objetivo_2026-10-15.md`. Depende do brief 047 (`8c8ce64`). Executado em 2026-10-30. O arquivo em disco estava numa versão antiga do brief (cabeçalho sem Conjunto/Arquivos-alvo/Modelo/Esforço/Teste de aceite, ainda com "o executor não roda git nem a suíte" no passo 8) — substituído pelo conteúdo colado no Projeto antes de executar (AGENTS §10: o executor só executa brief no disco; o colado é a versão vigente).

## 1. Como ficou

**O gate.** `nucleo/relevancia/cruzamento.py` → `cruzar_contato_por_consulta`: depois de formar `demais`
(os candidatos que o piso por embedding — brief 046 — já marcou `conector`) e antes de ordenar para o
menu, `_aplicar_gate_objetivo` chama o modelo em lote: para cada candidato, objetivo do pedido + frase
original + ficha do contato (cargo/empresa/cidade) + título e resumo da notícia. O modelo devolve
`{relaciona: bool, motivo: str}` por candidato, na mesma ordem. `relaciona=False` vira
`fora_do_dominio`, gravado como descartado com `motivo="sem relação com o objetivo (juízo do modelo)"`
— o mesmo mecanismo já usado para `fora_do_dominio` do piso por embedding. Só `relaciona=True`
continua `conector` e segue para `cruzar_por_que` e o menu.

**Lote e casamento por posição.** `_chamar_gate_objetivo` (mesmo padrão de `_chamar_cruzar_por_que`):
até 2 tentativas; resposta com quantidade diferente da esperada cai para `fila_revisao` (tarefa
`avaliar_relacao_objetivo`) e o gate **não filtra nada** — `demais` segue inteiro, exatamente como
antes do brief 049, e `resumo.erros` é incrementado. O casamento candidato-a-candidato é testado por
posição (`test_gate_lote_ordem.py`), não por conteúdo.

**O menu pode zerar.** Se o gate reprova todos os candidatos, `demais` fica vazio:
`resumo.sem_assunto = True`, `resumo.motivo = "nenhum candidato com relação ao objetivo (juízo do
modelo)"`. `cruzar_por_que` não é chamado (não há com o quê). A entrega segue para a mensagem base do
brief 047 — nenhum gancho de notícia forçado; esse encadeamento (047) já está provado pela suíte
existente, não foi re-testado aqui.

**Prompt e contrato novos.** `nucleo/prompts/avaliar_relacao_objetivo.py` (exemplo resolvido distante
de qualquer caso real, armadilha 24) e `RespostaAvaliarRelacaoObjetivo`/`AvaliacaoRelacaoObjetivo` em
`nucleo/modelos/cruzamento.py`, ao lado de `RespostaCruzarPorQue`. Tarefa `avaliar_relacao_objetivo`
em `config/llm_routing.yaml`, nos dois perfis (`air16`: `qwen3:4b`, `num_ctx: 4096`; `pro48`:
`qwen2.5:14b`, `num_ctx: 16384`; `temperature: 0.1` nos dois — julgamento factual, mesmo padrão de
`extrair_pedido`).

**O que o gate não faz.** Pergunta só "tem relação com o objetivo?" — nunca "este tema é adequado?".
Nenhuma palavra de tema sensível, LGPD ou censura entra no prompt (`avaliar_relacao_objetivo.py`); a
regra de verdade (nunca atribuir posição ao contato) é do `cruzar_por_que`, que continua intocado.

**Flag opcional (`usar_gate_objetivo`) não criada.** O item 5 da seção 5 do brief original era
explicitamente opcional, e nada nos testes de aceite (seção 5 do brief vigente) exige um
interruptor — o próprio mecanismo de `fila_revisao` já é a salvaguarda (resposta ruim do modelo não
derruba candidato nenhum). `config/limiares.yaml` não foi tocado.

## 2. Fora do que o brief pediu, mas necessário para o gate

`tests/test_cruzamento_por_consulta.py` e `tests/test_reconsulta_mesmo_dia.py` (não listados em
Arquivos-alvo) tinham um `_ClienteFalso.gerar_json` que respondia com `RespostaCruzarPorQue`
independente de `tarefa_nome` — com o gate chamando `gerar_json("avaliar_relacao_objetivo", ...)`
antes de `cruzar_por_que`, esses falsos quebravam (schema errado, ou `"Assuntos:\n"` ausente do
prompt do gate). Ajustados para despachar por `tarefa_nome` (gate sempre `relaciona=True`, preservando
o comportamento anterior ao brief 049); uma asserção em `test_cruzamento_por_consulta.py` que lia
`cliente.prompts[0]` (agora o prompt do gate, não mais o de `cruzar_por_que`) passou a ler
`prompts[-1]`. `tests/test_sem_objetivo_avisa.py` e `tests/test_consulta_preparar.py` não precisaram de
ajuste: o primeiro nunca chega ao gate (candidatos vazios antes dele) e o segundo usa
`cruzar_contato_por_consulta` inteiramente mockado.

## RELATÓRIO FINAL
- Brief executado: 049 — só vira gancho a notícia que o modelo julga ligada ao objetivo
- Arquivos criados: `agente_nw/nucleo/prompts/avaliar_relacao_objetivo.py`, `tests/test_gate_objetivo.py`,
  `tests/test_gate_zera_menu.py`, `tests/test_gate_lote_ordem.py`,
  `docs/docs/doc_049_juizo_de_relacao_com_o_objetivo_2026-10-15.md`, `logs/commit_049.txt`,
  `logs/arquivos_049.txt`
- Arquivos alterados (resumo em uma linha cada):
  - `agente_nw/nucleo/modelos/cruzamento.py` — `AvaliacaoRelacaoObjetivo` e `RespostaAvaliarRelacaoObjetivo`
  - `agente_nw/nucleo/relevancia/cruzamento.py` — gate entre o piso por embedding e o corte para o menu
  - `config/llm_routing.yaml` — tarefa `avaliar_relacao_objetivo` nos dois perfis
  - `tests/test_cruzamento_por_consulta.py`, `tests/test_reconsulta_mesmo_dia.py` — ver seção 2
- Arquivos preservados literalmente na área afetada: `relevancia/pontuacao.py`, `nucleo/prompts/cruzar_por_que.py`,
  `relevancia/cruzamento.py::cruzar_contato` (a função sem consulta, fora do pedido do brief 4.3)
- Script de verificação (o gate, rodado pelo `scripts/agente_entregar.sh`; saída colada):
  ```
  manifesto 049: 9 arquivo(s)
  ruff check: ok
  ruff format: ok
  mypy: ok
  pytest: ok (825 passed, 5 deselected in 17.88s)
  lacunas do 049: 0 no Backlog, 4 em Pendências, 0 em Dívidas, 0 em Decisões
  ✓ brief 049: commit d2a1a54, enviado ao GitHub
  ```
- Comandos executados: `scripts/agente_entregar.sh 049`
- Manifesto do commit: `logs/arquivos_049.txt` e `logs/commit_049.txt` (conteúdo abaixo)
- Pendências e decisões que ficaram abertas: as quatro do próprio brief (§7/seção 7), teste real no Pro, só Sidarta:
  1. Refazer o pedido do Luiz: o menu não deve trazer Lula, Bolsonaro, manifestação nem o Sicoob.
  2. Sem notícia ligada à OAB, a entrega é a mensagem base, sem gancho de notícia.
  3. Havendo notícia de verdade sobre a OAB (ou o mundo profissional dele), ela entra como gancho.
  4. O gate pergunta só sobre relação com o objetivo — nunca sobre o tema ser aceitável.
- Resumo, Doing, Backlog e Done do `docs/PLAN.md` atualizados: sim

## Lacunas

| # | Lacuna | Destino | Impacto |
|---|---|---|---|
| 1 | Teste real, no Pro: refazer o pedido do Luiz e conferir que Lula/Bolsonaro/manifestação/Sicoob não aparecem mais no menu | pendência | nice |
| 2 | Teste real: sem notícia ligada à OAB, a entrega é só a mensagem base | pendência | nice |
| 3 | Teste real: notícia de verdade sobre a OAB (ou a área profissional do contato) entra como gancho | pendência | nice |
| 4 | Teste real: o gate pergunta só sobre relação com o objetivo, nunca sobre o tema ser aceitável | pendência | nice |
