# Doc 048 — Conteúdo que já funcionou vira molde, escolhido e adaptado por contexto

Brief: `docs/briefs/brief_048_molde_por_contexto_2026-10-15.md`. Depende do brief 047 (`8c8ce64`).
Executado em 2026-10-30. O arquivo em disco estava numa versão antiga do brief (cabeçalho sem
Conjunto/Arquivos-alvo/Modelo/Esforço/Teste de aceite, ainda com "o executor não roda git nem a suíte"
no passo 8) — substituído pelo conteúdo colado no Projeto antes de executar (AGENTS §10: o executor só
executa brief no disco; o colado é a versão vigente, mesmo precedente do brief 049).

## 1. Como ficou

**Contexto de uma mensagem (4.1).** objetivo (categoria: `retomar`/`agradecer`/`pedir`/...) + registro +
cargo do contato. `ContextoConsulta` (gravada em `consulta_contato.contexto_json`) já guardava `registro`;
ganhou `objetivo_categoria` (`PedidoExtraido.objetivo`), porque o campo `objetivo` existente ali é o texto
livre (`objetivo_texto`), não a categoria — sem isso não havia como casar "mesmo objetivo" de forma
confiável entre pedidos.

**Recuperação por contexto (4.2).** `consulta_contato.moldes_por_contexto(perfil_id_atual,
objetivo_categoria, registro, cargo_atual, maximo)`: junta `gancho_uso` → `consulta_contato` → `perfil`,
filtra por mesmo `objetivo_categoria` e `registro` (via `json_extract` no `contexto_json`) e por cargo
igual ao do contato atual (comparação simples, sem acento/caixa — regra simples sobre a ficha, como o
brief permite); `nao_serve` nunca entra; `usado` vem antes de `entregue`, depois por recência; corta em
`maximo` (`moldes.maximo`, padrão 2). Carrega também o `comentario` do usuário sobre a mensagem (brief
050), quando houver — ponto que o próprio Backlog do PLAN já sinalizava ("lê `gancho_uso.comentario`").

**Adaptação — o prompt (4.3).** `redacao._moldes` monta uma linha por molde
(`[usei] "..." — comentário do usuário: "..."`) e `EntradaRedacao.moldes` as leva ao prompt num bloco
próprio, logo depois do PEDIDO: "MENSAGENS QUE JÁ FUNCIONARAM NESTE TIPO DE CONTEXTO [...]; adapte à
pessoa de agora — não copie: carregue o que serve [...], adapte nome e gênero gramatical, e troque ou
tire o detalhe que só cabia à pessoa de origem [...] nada pode ficar falso para quem recebe agora." Uma
regra irmã em `_regras()` reforça a concordância de gênero e a proibição de deixar resíduo da fonte. Sem
molde, o bloco não aparece (testado).

**Gênero gramatical do contato (4.4).** Migração 016: `perfil.genero_gramatical` (`masculino`/
`feminino`/`desconhecido`, `CHECK`, padrão `desconhecido`). Inferido por heurística simples do primeiro
nome em `queries/perfis.py::_inferir_genero_gramatical` (terminação + pequena lista de exceções comuns
em português — não é juízo sobre a pessoa, é concordância gramatical) nos dois pontos de criação de
contato (`inserir_ou_atualizar_contato`, `inserir_novo_contato`); sem certeza fica `desconhecido` e o
prompt usa forma neutra. Editável na ficha (`/contatos/<id>/editar`, campo `genero_gramatical`) —
sobrescreve sempre, como os demais campos de `atualizar_ficha_manual`.

**O usuário continua dono (4.5).** Nada disto grava automaticamente nada na mensagem final: o molde e o
gênero só entram no prompt como instrução; a mensagem sai como antes, rascunho para o usuário editar.

**Corte por tamanho.** `cortar_por_tamanho` ganhou um estágio: historico+fatos primeiro, moldes depois
(saem antes da conversa do WhatsApp — bônus de outro contato pesa menos que o tom com o próprio contato),
notas sempre protegidas.

## 2. Fora do que o brief pediu, mas necessário

`agente_nw/nucleo/modelos/contexto_consulta.py` e `agente_nw/nucleo/pedido.py` não estão nos
Arquivos-alvo do brief, mas precisaram do campo `objetivo_categoria` (ver seção 1) — sem ele, "mesmo
objetivo" do item 4.2 não tinha onde ser lido de volta no `contexto_json` já persistido.
`tests/test_migracao_comentarios.py` precisou do mesmo ajuste mecânico de versão que o brief 061 já fez
(14→15): com a migração 016, `migracoes.aplicar(banco)` sem pasta aplica tudo, então o teste que fixa o
`schema_version` esperado em 15 passou a falhar; corrigido para 16.

Não toquei `perfis.unir_contatos`/`_CAMPOS_MERGE_UNIAO`: a lógica de lá assume que "vazio" é `NULL`, e
`genero_gramatical` nunca é `NULL` (padrão `'desconhecido'`); nada no brief ou nos testes de aceite pede
o comportamento de merge, e eu não quis generalizar essa checagem sem necessidade comprovada. Registrado
como lacuna.

## RELATÓRIO FINAL
- Brief executado: 048 — conteúdo que já funcionou vira molde, escolhido e adaptado por contexto
- Arquivos criados: `scripts/migracoes/016_perfil_genero_gramatical.sql`, `tests/test_moldes_por_contexto.py`,
  `tests/test_molde_adapta_genero.py`, `tests/test_molde_atributo_compartilhado.py`,
  `tests/test_molde_verdade_046.py`, `tests/test_migracao_genero.py`,
  `docs/docs/doc_048_molde_por_contexto_2026-10-15.md`, `logs/commit_048.txt`, `logs/arquivos_048.txt`
- Arquivos alterados (resumo em uma linha cada):
  - `agente_nw/nucleo/modelos/perfil.py` — `GeneroGramatical` e o campo no `Perfil`
  - `agente_nw/nucleo/database/queries/perfis.py` — coluna, heurística de inferência, inserts, campo editável
  - `agente_nw/nucleo/modelos/contexto_consulta.py` — `objetivo_categoria` (ver seção 2)
  - `agente_nw/nucleo/pedido.py` — `para_contexto` preenche `objetivo_categoria` (ver seção 2)
  - `agente_nw/nucleo/database/queries/consulta_contato.py` — `moldes_por_contexto` e `MoldeParaRedacao`
  - `agente_nw/nucleo/modelos/configuracao.py` — `MoldesLimiares`
  - `config/limiares.yaml` — bloco `moldes`
  - `agente_nw/nucleo/redacao.py` — `_moldes`, `montar_entrada`/`redigir` ganham `maximo_moldes`
  - `agente_nw/nucleo/prompts/redigir_ganchos.py` — campo, bloco, regra de concordância, corte por tamanho
  - `agente_nw/nucleo/orquestracao.py` — `maximo_moldes=limiares.moldes.maximo`
  - `agente_nw/console/app.py` — `editar_ficha` aceita `genero_gramatical`
  - `agente_nw/console/templates/ficha.html` — campo de gênero gramatical na ficha
  - `tests/test_migracao_comentarios.py` — versão esperada 15→16 (ver seção 2)
- Arquivos preservados literalmente na área afetada: `agente_nw/nucleo/relevancia/cruzamento.py` (brief 049,
  intocado), `agente_nw/perfil/extrator.py`, `agente_nw/nucleo/database/queries/perfis.py::unir_contatos`
  (ver seção 2)
- Script de verificação (o gate, rodado pelo `scripts/agente_entregar.sh`; saída colada):
  ```
  manifesto 048: 19 arquivo(s)
  ruff check: ok
  ruff format: ok
  mypy: ok
  pytest: ok (841 passed, 5 deselected in 19.65s)
  lacunas do 048: 0 no Backlog, 5 em Pendências, 1 em Dívidas, 0 em Decisões
  ✓ brief 048: commit 0bdd9be, enviado ao GitHub
  ```
- Comandos executados: `scripts/agente_entregar.sh 048`
- Manifesto do commit: `logs/arquivos_048.txt` e `logs/commit_048.txt` (conteúdo abaixo)
- Pendências e decisões que ficaram abertas: as cinco do próprio brief (seção 7), teste real no Pro, só Sidarta:
  1. Depois de usar uma mensagem com um advogado, um pedido com o mesmo objetivo para outro advogado parte
     da mesma estrutura, adaptada ao novo contato.
  2. Luiz → Maria: a mensagem sai no feminino, sem resíduo masculino.
  3. O atributo compartilhado ("advogado", a eleição) é mantido; a peculiaridade que não cabe ao novo
     contato não aparece afirmada dele.
  4. O gênero gramatical do contato é editável na ficha, e a redação o respeita.
  5. Nada falso sobre o novo contato entra pela porta do molde (046 continua).
  E uma dívida: `unir_contatos` não funde `genero_gramatical` entre contatos unidos (ver seção 2) — sem
  teste nem pedido do brief, fica registrada para quando (se) incomodar.
- Resumo, Doing, Backlog e Done do `docs/PLAN.md` atualizados: sim

## Lacunas

| # | Lacuna | Destino | Impacto |
|---|---|---|---|
| 1 | Teste real, no Pro: depois de usar uma mensagem com um advogado, um pedido com o mesmo objetivo para outro advogado parte da mesma estrutura, adaptada ao novo contato | pendência | nice |
| 2 | Teste real: Luiz → Maria, a mensagem sai no feminino, sem resíduo masculino | pendência | nice |
| 3 | Teste real: o atributo compartilhado é mantido; a peculiaridade que não cabe ao novo contato não aparece afirmada dele | pendência | nice |
| 4 | Teste real: o gênero gramatical é editável na ficha e a redação o respeita | pendência | nice |
| 5 | Teste real: nada falso sobre o novo contato entra pela porta do molde (046 continua) | pendência | nice |
| 6 | `unir_contatos` não funde `genero_gramatical` entre contatos unidos (o merge assume "vazio" = NULL; o campo nunca é NULL) | dívida | nice |
