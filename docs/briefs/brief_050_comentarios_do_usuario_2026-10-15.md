# Brief 050 — Comentário do usuário: a nota que vira contexto

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Depende de:** brief 047 (a mensagem base existe e também é comentável) e 039 (tela única, `_pedido.html`). Integra com o 048 (molde) e o 042 (medição) — pontos de contato, não pré-requisitos.
**Plano:** v3.1 — o juízo do usuário, nas palavras dele, alimenta a próxima geração.
**Data:** 2026-10-15

---

## 1. Objetivo em uma frase

O usuário pode escrever, em texto livre, por que uma mensagem serviu ou não e o que mudar — e essa nota vira **contexto da próxima mensagem para aquele contato**, **sinal para o molde** entre contatos e **matéria para calibrar** depois; sem estrelas, sem categorias, por cima do "usei / não serve" que já existe.

---

## 2. Decisões

**2.1. Dois lugares, texto livre, sempre opcional.**
- **Na mensagem:** cada mensagem entregue (gancho de notícia ou mensagem base) ganha um campo de comentário — "por que serviu", "não serve porque é política nacional, queria da OAB", "essa peculiaridade foi ótima".
- **No contato/pedido:** um campo de nota sobre o pedido ou o contato em geral — "o Luiz trocou de escritório", "da próxima vez foca na OAB".
- O "usei / não serve" fica como está. O comentário é o **porquê**, à parte. Nada de nota de 1 a 5, nada de categoria para escolher — o usuário fala com as palavras dele.

**2.2. Onde cada um mora.**
- Comentário de mensagem: coluna `comentario TEXT NULL` em `gancho_uso` (tabela já mutável — é a que `marcar` atualiza). Função `comentar(consulta_id, assunto_id, texto, agora)`. Vale também para a mensagem base (assunto nulo, 047).
- Nota de contato/pedido: `consulta_contato` é **só inserção** (tem gatilho que proíbe update), então não serve para uma nota escrita depois. Tabela nova, append-only: `nota_contato(id, perfil_id, pedido_id NULL, texto, criado_em)` — `pedido_id` preenchido quando a nota é sobre aquele pedido, nulo quando é sobre o contato em geral.

**2.3. A nota vira contexto da próxima mensagem (Uso 1).** `nucleo/redacao.py` (`montar_entrada`/`_historico`): o bloco HISTÓRICO do prompt passa a incluir, por consulta recente daquela pessoa, os comentários das mensagens e as notas de contato recentes — dentro do orçamento de tokens que já existe (corta como já corta sob pressão). Assim o próximo pedido sobre o Luiz já "sabe" o que você anotou.

**2.4. A nota viaja com a mensagem no molde (Uso 2).** Quando o 048 recuperar uma mensagem passada como molde, leva junto o `comentario` dela ("o usuário anotou: …"), para o modelo aprender não só o texto que funcionou, mas o porquê. Ponto de integração: deixar o `comentario` disponível na mesma leitura que o molde usa.

**2.5. A nota é sinal de calibração (042).** O `medir` passa a mostrar os comentários ao lado de "usei/não serve" — é com eles, e não com um número meu, que você decide ajustar prompt ou gate depois. Ponto de integração com o 042.

**2.6. O usuário é o dono.** A nota é dele, opcional, editável; o software não a classifica nem a transforma em juízo.

---

## 3. Escopo (arquivos)

1. `scripts/migracoes/0XX_comentarios.sql` — `gancho_uso.comentario`; tabela `nota_contato`.
2. `nucleo/database/queries/gancho_uso.py` — `comentar(...)`; incluir `comentario` nas leituras (`listar_por_consulta`).
3. `nucleo/database/queries/nota_contato.py` (novo) — `inserir`, `listar_por_perfil`, `listar_por_pedido`.
4. `nucleo/redacao.py` — comentários e notas recentes no bloco de histórico do prompt.
5. `console/app.py` + `console/templates/_pedido.html` (e a ficha do contato, se couber) — caixas de texto e rotas `POST` para gravar o comentário da mensagem e a nota do contato/pedido.

Integração (não implementar aqui, só deixar o gancho): 048 (molde leva o `comentario`), 042 (medição mostra comentários).

---

## 4. Testes

- `tests/test_comentario_mensagem.py`: comentar uma mensagem (inclusive a base, assunto nulo) → persiste; `listar_por_consulta` devolve o texto.
- `tests/test_nota_contato.py`: nota com `pedido_id` e nota geral (nulo) → ambas recuperáveis por contato.
- `tests/test_comentario_no_prompt.py`: um comentário e uma nota recentes do contato aparecem no bloco de histórico do prompt da próxima redação.
- `tests/test_comentario_sob_orcamento.py`: com o prompt perto do limite de tokens, os comentários entram sem estourar (o corte existente vale).
- `tests/test_migracao_comentarios.py`.

---

## 5. Fora de escopo (vira brief se quiser)

- Extrair fato estruturado do comentário (ex.: "trocou de escritório" atualizar a ficha). Por ora a nota entra como contexto em texto, não como fato.
- Nota de 1 a 5, categorias, tags.
- Implementar o molde (048) e a medição (042): aqui só os pontos de integração.

---

## 6. Passos de execução

> AGENTS.md: o executor não roda `git` nem a suíte. Entrega a lista de arquivos tocados e o texto do commit; Sidarta autoriza.

1. Migração (`gancho_uso.comentario`, `nota_contato`).
2. Queries (`comentar`, `nota_contato`).
3. Histórico no prompt (`redacao.py`).
4. Tela e rotas (`_pedido.html`, `app.py`).
5. Testes da seção 4.
6. Lista para `git add` e mensagem:
   `feat(comentarios): nota de texto livre na mensagem e no contato, que vira contexto da proxima geracao (brief 050)`

`scripts/verificar.sh`, o teste real e o commit são passos de Sidarta.

---

## 7. Critérios de aceite (Sidarta, no Pro)

1. Em cada mensagem dá para escrever um comentário; ele é salvo e é opcional (sem ele, nada muda).
2. Um comentário feito num pedido sobre o Luiz aparece como contexto no próximo pedido sobre o Luiz.
3. Uma nota "trocou de escritório" influencia a próxima mensagem para ele.
4. Um "não serve" com comentário fica guardado para a medição ler depois.
5. Não há estrelas nem categorias — só o texto, nas suas palavras.
