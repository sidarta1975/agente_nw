# Brief 065 — O molde vem só do que funcionou

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Conjunto:** camada_de_ia (064, 065 e 066)
**Arquivos-alvo:** `agente_nw/nucleo/database/queries/consulta_contato.py` (`moldes_por_contexto`), `agente_nw/nucleo/redacao.py`, `scripts/migracoes/018_molde_rastreio.sql` (nova — a última hoje é 017, do brief 040; o executor confere `ls scripts/migracoes/` antes de numerar, caso outro brief tenha entrado antes deste), `tests/test_moldes_so_confirmado.py` (novo), `docs/docs/doc_065_molde_so_do_que_funcionou_2026-11-02.md`, `logs/commit_065.txt`, `logs/arquivos_065.txt`
**Seções a ler:** o relatório do brief 048 (`docs/docs/doc_048_molde_por_contexto_2026-10-15.md`); `consulta_contato.moldes_por_contexto` e `redacao.py` (bloco de moldes) inteiros; ARQUITETURA §3 (contratos de dados)
**Modelo:** Sonnet
**Esforço:** baixo
**Teste de aceite:** `tests/test_moldes_so_confirmado.py`
**Depende de:** brief 048 (`0bdd9be`) — já na `main`; é a função que este brief altera
**Data:** 2026-11-02

---

## 1. Objetivo em uma frase

Interromper a realimentação: texto que o modelo escreveu e que ninguém confirmou não retorna ao prompt como molde, a não ser uma vez, só quando não existe nenhuma mensagem confirmada para o mesmo contexto.

---

## 2. Por que (achado no código, não só pensado)

`moldes_por_contexto` hoje seleciona `status IN ('usado', 'entregue')`, ordena por `usado` primeiro e devolve até `maximo` (2–3, do brief 048) — sem limitar quantas mensagens `entregue` (não confirmadas) entram, nem restringir isso a quando não existe nenhuma `usado` para a mesma tríade. Nada impede que, sem nenhuma `usado` ainda, duas ou três mensagens nunca confirmadas sirvam de molde ao mesmo tempo — e que o resultado disso também não seja confirmado, e vire molde de novo. É esse encadeamento sem controle que este brief fecha.

---

## 3. Decisões

**3.1. `usado` primeiro, sempre.** Se existe ao menos uma mensagem `usado` para a tríade (objetivo, registro, cargo), só `usado` entra como molde — nenhuma `entregue` participa, mesmo que `maximo` ainda tenha espaço.

**3.2. `entregue` só no arranque a frio, e só uma.** Sem nenhuma `usado` para a tríade, no máximo **uma** mensagem `entregue` entra como molde — a mais recente. Isso preserva a utilidade do molde desde a primeira mensagem de cada tipo de contexto, sem deixar várias não confirmadas se empilharem.

**3.3. Marcação explícita de "não confirmado" no prompt.** `redacao.py` já escreve `"usei"` ou `"entreguei"` ao lado de cada molde (função que monta o bloco de moldes). Esse texto passa a ser mais direto: para `entregue`, a marca é **"entreguei, ainda não confirmado se funcionou"** — para que o modelo não trate aquele exemplo como prova de sucesso.

**3.4. Rastro de proveniência do molde.** Migração nova: `gancho_uso.molde_origem_id INTEGER NULL REFERENCES gancho_uso(id)`. Quando uma mensagem é redigida a partir de um molde, a linha de `gancho_uso` dessa mensagem nova grava o `id` do molde usado. Isso não muda a seleção do item 3.1/3.2 — é só o registro que depois permite contar quantos passos separam uma mensagem de outra efetivamente `usado` (útil para o 066 e para a medição do 042). Nenhum dado existente é apagado ou reescrito; a coluna nova nasce `NULL` para tudo que já existe.

---

## 4. Testes (escritos antes do código)

- `tests/test_moldes_so_confirmado.py`:
  - tríade com uma `usado` e duas `entregue` → só a `usado` volta;
  - tríade só com `entregue` (duas ou mais) → só a mais recente volta, marcada como não confirmada;
  - tríade sem nenhuma mensagem anterior → lista vazia, como hoje;
  - uma mensagem redigida a partir de um molde grava `molde_origem_id` apontando para ele;
  - mensagem redigida sem molde (nenhum candidato) → `molde_origem_id` fica `NULL`;
  - o texto do prompt distingue "usei" de "entreguei, ainda não confirmado se funcionou" (conferir a string montada, não só o dado).
- O LLM é sempre simulado.

---

## 5. Fora de escopo

- Mudar `gancho_uso.status` ou o fluxo de "usei/não serve" — este brief só muda o que alimenta o molde.
- Apagar ou reprocessar moldes já usados antes desta mudança.
- Proveniência de modelo/prompt (brief 066) — `molde_origem_id` é só o rastro específico de qual molde gerou qual mensagem, não a proveniência geral.

---

## 6. Passos e aceite

Executar com `/executar 065`. Aceite: testes da seção 4 verdes, gate verde, commit e push pelo executor.

Pendência para Sidarta na resposta final — teste real, no Pro:
1. Depois de marcar "usei" numa mensagem, um pedido novo de contexto parecido usa só ela como molde, mesmo havendo mensagens `entregue` mais recentes.
2. Sem nenhuma "usei" ainda para aquele tipo de contexto, o molde usado é a mensagem mais recente, e ela aparece identificada como não confirmada.
