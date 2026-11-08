# Doc 065 — O molde vem só do que funcionou

Brief: `docs/briefs/brief_065_molde_so_do_que_funcionou_2026-11-02.md`. Depende do brief 048 (`0bdd9be`).

## 1. Como ficou

**3.1/3.2 — seleção.** `consulta_contato.moldes_por_contexto` busca os candidatos como antes (`usado`/
`entregue`, mesmo objetivo/registro/cargo), mas separa em dois grupos depois do filtro de cargo: se há
algum `usado`, devolve só os `usado` (até `maximo`) — nenhuma `entregue` entra, mesmo com espaço de sobra.
Sem nenhum `usado`, devolve no máximo **uma** `entregue` — a primeira da lista, que já vem ordenada por
recência dentro do grupo sem `usado` (`ORDER BY ... c.criado_em DESC`). Isso fecha a realimentação: texto
nunca confirmado não se empilha como molde de outro texto nunca confirmado.

**3.3 — marca no prompt.** `redacao._moldes` troca a marca `"entreguei"` por
`"entreguei, ainda não confirmado se funcionou"` para moldes com `bom=False`. `"usei"` continua igual.

**3.4 — rastro.** Migração 018: `gancho_uso.molde_origem_id INTEGER NULL REFERENCES gancho_uso(id)`.
`consulta_contato.MoldeParaRedacao` ganhou o campo `id` (o `id` da linha de `gancho_uso` de origem).
`redacao._moldes` devolve agora `(linhas, molde_origem_id)` — o `id` do primeiro candidato da lista (o
mais relevante: `usado` antes de `entregue`, depois por recência) — que viaja em
`EntradaRedacao.molde_origem_id` e, dali, em `Redacao.molde_origem_id`. `redacao.registrar` passa esse
valor para `gancho_uso.inserir_entregues(..., molde_origem_id=...)`, que grava em todas as linhas
daquela entrega (a mensagem base e os ganchos de notícia, se houver — o molde influencia a redação como
um todo, não um gancho isolado). Se o molde sair do prompt por corte de tamanho
(`cortar_por_tamanho`, que agora limpa `moldes` e `molde_origem_id` juntos), a mensagem não grava
proveniência de um molde que o modelo nunca viu — por isso `redacao.redigir` recalcula
`cortar_por_tamanho(entrada, limite_tokens).molde_origem_id` antes de montar o prompt, em vez de usar o
`molde_origem_id` de `entrada` sem olhar o corte.

## 2. Fora do que o brief pediu, mas necessário

- `MoldeParaRedacao` ganhou o campo `id` (não citado no brief) — necessário para `molde_origem_id`
  apontar para algo; sem ele não havia como saber qual `gancho_uso` deu origem ao molde escolhido.
- `gancho_uso.inserir_entregues` ganhou o parâmetro `molde_origem_id: int | None = None` (compatível com
  todo chamador existente, que não passa o argumento e mantém `NULL` — comportamento inalterado onde o
  brief não pediu mudança).
- `redigir()` chama `cortar_por_tamanho` uma segunda vez (além da que já acontece dentro de
  `construir_prompt`) só para ler `molde_origem_id` depois do corte — chamada pura e barata (estimativa
  de tokens sobre um dataclass), não haveria como obter esse dado sem duplicar o corte ou expor uma API
  nova no módulo de prompts; optei pelo primeiro, mais simples.
- Os testes de versão de migração (`test_migracao_comentarios.py`, `test_migracao_genero.py`) tiveram o
  número esperado bumped 17→18 — mesmo ajuste mecânico recorrente de todo brief que acrescenta migração.

## RELATÓRIO FINAL
- Brief executado: 065 — O molde vem só do que funcionou.
- Arquivos criados: `scripts/migracoes/018_molde_rastreio.sql`, `tests/test_moldes_so_confirmado.py`.
- Arquivos alterados (resumo de uma linha cada):
  - `agente_nw/nucleo/database/queries/consulta_contato.py`: `MoldeParaRedacao.id`;
    `moldes_por_contexto` só devolve `entregue` quando não há `usado`, e no máximo uma.
  - `agente_nw/nucleo/database/queries/gancho_uso.py`: `inserir_entregues` ganha `molde_origem_id`.
  - `agente_nw/nucleo/redacao.py`: `_moldes` devolve `(linhas, molde_origem_id)` com a marca nova de
    não confirmado; `redigir`/`registrar` propagam `molde_origem_id`.
  - `agente_nw/nucleo/modelos/redacao.py`: `Redacao.molde_origem_id`.
  - `agente_nw/nucleo/prompts/redigir_ganchos.py`: `EntradaRedacao.molde_origem_id`; `cortar_por_tamanho`
    limpa junto com `moldes`.
  - `tests/test_migracao_comentarios.py`, `tests/test_migracao_genero.py`: versão esperada 17→18.
- Arquivos preservados literalmente na área afetada: `agente_nw/nucleo/database/queries/gancho_uso.py`
  (demais funções); fluxo de "usei"/"não serve" (`marcar`), fora de escopo.
- Script de verificação (gate, rodado por `scripts/agente_entregar.sh`; saída colada):
```
manifesto 065: 9 arquivo(s)
ruff check: ok
ruff format: ok
mypy: ok
pytest: ok (867 passed, 5 deselected in 22.44s)
```
- Comandos executados: `.venv/bin/ruff check .`; `.venv/bin/ruff format --check .`;
  `.venv/bin/mypy agente_nw`; `.venv/bin/python -m pytest -q`; `scripts/agente_entregar.sh 065`.
- Manifesto do commit (`logs/arquivos_065.txt` e `logs/commit_065.txt`, conteúdo colado):
```
logs/arquivos_065.txt:
agente_nw/nucleo/database/queries/consulta_contato.py
agente_nw/nucleo/database/queries/gancho_uso.py
agente_nw/nucleo/modelos/redacao.py
agente_nw/nucleo/prompts/redigir_ganchos.py
agente_nw/nucleo/redacao.py
scripts/migracoes/018_molde_rastreio.sql
tests/test_migracao_comentarios.py
tests/test_migracao_genero.py
tests/test_moldes_so_confirmado.py

logs/commit_065.txt:
feat(redacao): molde so entra do que foi confirmado; rastro de proveniencia do molde (brief 065)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
```
- Pendências e decisões que ficaram abertas: as duas do próprio brief (seção 7 do brief), teste real no Pro:
  1. Depois de marcar "usei" numa mensagem, um pedido novo de contexto parecido usa só ela como molde,
     mesmo havendo mensagens `entregue` mais recentes.
  2. Sem nenhuma "usei" ainda para aquele tipo de contexto, o molde usado é a mensagem mais recente, e
     ela aparece identificada como não confirmada.
- Resumo, Doing, Backlog e Done do `docs/PLAN.md` atualizados: sim.

## Lacunas

| # | Lacuna | Destino | Impacto |
|---|---|---|---|
| 1 | Teste real, no Pro: depois de marcar "usei", um pedido novo de contexto parecido usa só essa mensagem como molde, mesmo havendo `entregue` mais recente | pendência | nice |
| 2 | Teste real: sem nenhuma "usei" para o tipo de contexto, o molde usado é a mensagem mais recente, identificada como não confirmada | pendência | nice |
