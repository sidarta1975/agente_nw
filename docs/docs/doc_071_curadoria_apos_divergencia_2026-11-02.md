# Doc 071 — Curadoria de redes sociais não pode pular depois do "Sim" na divergência

**Brief:** `docs/briefs/brief_071_curadoria_apos_divergencia_2026-11-02.md`
**Data:** 2026-11-02

## A causa, confirmada no código

A divergência pausa o pedido **antes** de a curadoria de rede social acontecer, e isso é de propósito:
`agente_nw/nucleo/pedido.py::_localizar_na_rede` desiste logo no começo quando o contato é divergente
(`if resultado.contato_divergente: return  # o contato dado em --contato não é a pessoa do pedido: não
grava rede social nele`). Com isso `resultado.localizacoes` fica vazio, `encaminhar_pedido` nem entra no
ramo das perguntas de rede (que exige `resultado.localizacoes` cheio) e levanta a divergência.

Quando o usuário responde "Sim", `decidir_divergencia` só retira a pergunta da lista — não resolve
localização nenhuma. A rota `/pedido/<id>/pessoa` então via `sem_perguntas() == True` e despachava
`_despachar_execucao(pedido_id, continuar=True)` → `continuar_pedido` → `_escrever`, que não faz curadoria
de rede (só relê posts de um perfil **já vinculado**, via `ler_redes_sociais`). A curadoria daquele pedido
nunca rodava.

## A decisão de implementação (o brief deixou a escolha ao executor, item 3.1)

A opção (a) pura — a rota chamar `executar_pedido` de novo — **não** resolve: na segunda passada
`pedido.perfil_id` e o texto do pedido são os mesmos, então `pedido.py` recalcularia
`divergente = True` (a similaridade entre "Marta Quintela" e "Joaquim Bastos" não mudou) e a mesma
pergunta voltaria a cada passada — o bug reaberto de outro jeito, exatamente o risco que o cabeçalho do
brief aponta.

Escolhido um (b) enxuto: `fluxo.retomar_apos_divergencia` chama `_entender` com
`divergencia_aceita=True`, que repassa o gancho que `entender_pedido` **já** tem para esse fim
(`confirmar_contato`, usado pelo terminal com a confirmação `[s/N]`) devolvendo `True`. Com isso
`divergente` vira `False`, `_localizar_na_rede` deixa de desistir e a curadoria roda pela primeira vez
neste pedido; a pergunta de divergência não nasce de novo. Nada mudou em `orquestracao.py` nem em
`pedido.py` — os dois estão em "Seções a ler", não em "Arquivos-alvo".

O caminho de `decidir_rede`/`decidir_contato` continua em `continuar_pedido` (item 3.3), com teste de
não regressão que conta as passadas de `_entender` pelas chamadas ao LLM de extração.

## Arquivos alterados

- `agente_nw/nucleo/fluxo.py` — novo `retomar_apos_divergencia`; `_entender` ganhou
  `divergencia_aceita` e passa `confirmar_contato` quando ele é verdadeiro; `continuar_pedido` ganhou na
  docstring a fronteira entre os dois caminhos de retomada.
- `agente_nw/console/app.py` — `_despachar_execucao` ganhou `apos_divergencia`; o ramo
  `tipo == "divergencia"` usa `apos_divergencia=True` em vez de `continuar=True`.
- `tests/test_contato_divergente.py` — quatro casos novos (curadoria depois do "Sim", divergência que
  não se repete, despacho da rota, não regressão de `decidir_rede`); o caso que já existia
  (`test_console_sim_segue_o_pedido_ate_a_redacao`) passou a retomar pelo caminho novo.
- `docs/PLAN.md` — a linha `[059-3]` saiu de "Decisões em aberto" (item 3.4).

## Arquivos preservados literalmente na área afetada

- `agente_nw/nucleo/pedido.py` e `agente_nw/nucleo/orquestracao.py` — lidos, não tocados.
- `decidir_rede`, `decidir_contato` e `decidir_divergencia` em `fluxo.py` — sem mudança de comportamento.

## Prova de que o teste da rota pega o bug

Com o despacho antigo (`continuar=True`) no lugar, só o caso novo da rota quebra:

```
$ .venv/bin/python -m pytest tests/test_contato_divergente.py -q
E        +  where [] = <tests.test_fluxo.Cenario object at 0x10dd0efc0>.redes_localizadas
tests/test_contato_divergente.py:121: AssertionError
FAILED tests/test_contato_divergente.py::test_rota_do_console_apos_o_sim_despacha_a_curadoria_de_rede
1 failed, 12 passed in 1.34s
```

Com o despacho corrigido:

```
$ .venv/bin/python -m pytest tests/test_contato_divergente.py -q
.............                                                            [100%]
13 passed in 1.06s
```

## Complemento, depois de reconferir o brief contra o entregue

Numa segunda leitura da seção 4 do brief contra o teste entregue, o segundo cenário ("o contato já tem
todas as redes confirmadas → depois do 'Sim' chega à redação normalmente") estava provado só pela metade:
`test_console_sim_segue_o_pedido_ate_a_redacao` conferia `status == "concluido"` e uma chamada a
`preparar`, mas não o que o brief pede literalmente — "com a leitura de rede social relevante refletida no
resultado". Acrescentadas duas asserções ao mesmo teste:

- `cenario.chamadas_preparar[0]["ler_redes_sociais"] is True` — a leitura de rede social acontece (a
  retomada não é tratada como correção, que a desligaria);
- `cenario.redes_localizadas == []` — a curadoria já feita em pedidos anteriores não é refeita, isto é, a
  passada nova por `_entender` não repergunta o que já está curado.

As duas passaram sem tocar em código: o comportamento já estava certo, o teste é que não o provava.

## RELATÓRIO FINAL

- **Brief executado:** 071 — curadoria de redes sociais não pode pular depois do "Sim" na divergência.
- **Arquivos criados:** `docs/docs/doc_071_curadoria_apos_divergencia_2026-11-02.md`,
  `logs/commit_071.txt`, `logs/arquivos_071.txt`.
- **Arquivos alterados (resumo em uma linha cada):**
  - `agente_nw/nucleo/fluxo.py` — retomada do "Sim" passa de novo por `_entender`, com a divergência
    marcada como já confirmada.
  - `agente_nw/console/app.py` — o ramo da divergência despacha a retomada nova, não o atalho.
  - `tests/test_contato_divergente.py` — quatro casos novos e um atualizado.
  - `docs/PLAN.md` — `[059-3]` resolvida, linha removida.
- **Arquivos preservados literalmente na área afetada:** `agente_nw/nucleo/pedido.py`,
  `agente_nw/nucleo/orquestracao.py`, os outros `decidir_*` de `fluxo.py`.
- **Script de verificação (o gate, rodado pelo `scripts/agente_entregar.sh`; saída colada):** ver
  "Saída do gate" abaixo.
- **Comandos executados:**
  - `.venv/bin/python -m pytest tests/test_contato_divergente.py -q` → `13 passed`
  - `.venv/bin/python -m pytest -q` → `911 passed, 5 deselected`
  - `scripts/agente_entregar.sh 071`
- **Manifesto do commit (`logs/arquivos_071.txt` e `logs/commit_071.txt`):** ver abaixo.
- **Pendências e decisões que ficaram abertas:** teste real no Pro, para Sidarta (seção 6 do brief).
- **Resumo, Doing, Backlog e Done do `docs/PLAN.md` atualizados:** sim.

## Saída do gate

```
$ scripts/agente_entregar.sh 071
manifesto 071: 3 arquivo(s)
ruff check: ok
ruff format: ok
mypy: ok
pytest: ok (911 passed, 5 deselected in 31.61s)
lacunas do 071: 0 no Backlog, 0 em Pendências, 1 em Dívidas, 0 em Decisões
✓ brief 071: commit 80b9bbe, enviado ao GitHub
```

## Manifesto

`logs/arquivos_071.txt`:

```
agente_nw/nucleo/fluxo.py
agente_nw/console/app.py
tests/test_contato_divergente.py
```

`logs/commit_071.txt`:

```
fix(fluxo): depois do "Sim" na divergencia o pedido volta a curar as redes sociais (brief 071)
```

## Lacunas

| # | Lacuna | Destino | Impacto |
|---|--------|---------|---------|
| 1 | A retomada depois do "Sim" repassa por `_entender` inteiro, então reextrai o pedido com o LLM (`extrair_pedido`) embora `extraido_json` já esteja gravado e o texto não tenha mudado — uma chamada de modelo redundante por "Sim". Evitar isso pede que `pedido.processar` aceite um pedido já extraído, fora dos arquivos-alvo deste brief | dívida | nice |
