# Brief 047 — A mensagem nasce da pessoa e do objetivo; a notícia é opcional

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Depende de:** brief 046 (regra de verdade e marcas `[antigo]`/`[de imagem]`, já no working tree).
**Plano:** v3.1 — o produto deixa de ser buscador de notícia e passa a ser gerador de comunicação.
**Data:** 2026-10-15

---

## 1. Objetivo em uma frase

O software para de exigir uma notícia para escrever: toda mensagem nasce do **objetivo do pedido** e de **quem é a pessoa** (ficha + fatos coletados das redes), com **uma peculiaridade dela** para criar vínculo; a notícia, quando há uma que se liga de verdade ao pedido, entra como gancho adicional — nunca como espinha. O usuário é o dono e o editor; o software entrega o melhor rascunho e não julga tema, LGPD nem "qualidade" no lugar dele.

---

## 2. O que prende hoje (no código)

- `nucleo/redacao.py` → `redigir()` tem o atalho: `if not disponiveis: return Redacao(ganchos=[], aviso=...)` — **o modelo não é chamado quando não há assunto** (notícia). Sem notícia, não há mensagem.
- `nucleo/modelos/redacao.py` → `Gancho` exige `assunto_id: int`, `titulo` e `noticia` não vazios. Toda mensagem é obrigatoriamente ancorada a uma notícia.
- Consequência: no caso do Luiz, sem notícia boa sobre a eleição da OAB o programa ou não escreve nada ou força notícia nacional. A melhor mensagem — "Luiz, você é advogado, a eleição da OAB-SP está chegando, queria te convidar para um jantar com colegas; [peculiaridade dele]" — não precisa de notícia e hoje é impossível de gerar.

A ficha (`_ficha`), os fatos (`_fatos`, já com as marcas do 046), o vínculo, o tempo sem contato e o contexto de relação **já vão no prompt** (`montar_entrada`). O dado está lá; falta soltar a trava.

---

## 3. Decisões

**3.1. Uma mensagem sempre, com ou sem notícia.** Remover o atalho de `redigir()`. O modelo é sempre chamado. A saída tem sempre pelo menos **uma mensagem base**, construída de objetivo + ficha + fatos + peculiaridade, sem notícia. Havendo assuntos ligados de verdade ao pedido, entram também como ganchos com notícia (0..N), como já é hoje.

**3.2. A mensagem base.**
- Fonte: `pedido` (objetivo, registro, meio, assunto principal, interessa, evitar, frase original), `_ficha(contato)`, `_fatos(...)`, vínculo, tempo sem contato, contexto de relação.
- **Regra de ofício:** a mensagem base cita **uma peculiaridade concreta** da pessoa — um fato específico dos que estão no prompt —, não só o cargo. É o detalhe que cria o vínculo. Sem nenhum fato utilizável, usa o que a ficha dá (cargo/cidade/vínculo) e o aviso informa "pouca informação sobre a pessoa; mensagem mais geral" — **nunca inventa**.
- Respeita registro (limites de palavras do 038), objetivo e `evitar`.

**3.3. Esquema (`nucleo/modelos/redacao.py`).**
- `Gancho`: `assunto_id: int | None = None`; `titulo` e `noticia` passam a `str | None`. Acrescentar `peculiaridade: str | None` (o fato usado como vínculo — serve de transparência e de ponto de teste). `assunto_id is None` ⇒ é a mensagem base; com `assunto_id` ⇒ gancho com notícia.
- `RespostaRedacao` continua `ganchos` + `aviso`; agora um dos itens pode ser a base. (O executor pode preferir um campo `mensagem_base` separado; prefiro `assunto_id` opcional para reaproveitar `gancho_uso` e a tela — decisão do executor, registrada no relatório.)

**3.4. Validação (`validar_ganchos`).** Para a mensagem base (`assunto_id is None`): pular as checagens de assunto (válido / repetido / já usado); manter `evitar`, limite de palavras e a verdade do 046. Para ganchos com notícia: tudo como hoje. Limite: 1 base + até `MAXIMO_GANCHOS` com notícia.

**3.5. Gravação e tela.**
- `gancho_uso` passa a aceitar `assunto_id` nulo (migração) para a mensagem base ter `usei`/`não serve` como os demais; `assuntos_usados_do_perfil` ignora nulos.
- `console/templates/_pedido.html`: a mensagem base aparece **primeiro, sempre**; os ganchos com notícia abaixo, quando houver. Cada um com `usei`/`não serve`.

**3.6. Fluxo e aviso.** `nucleo/fluxo.py`/`redigir`: "sem notícia" deixa de ser fim de linha. O aviso vira informativo ("sem notícia relevante agora; mensagem a partir do perfil"), não um beco. **Reverte a regra do 038 "sem assunto, não escreve"** — registrar a reversão. O "não inventar" permanece: nenhuma notícia falsa, nenhuma afirmação sobre a pessoa fora dos fatos (046).

**3.7. Prompt (`prompts/redigir_ganchos.py`).** Reescrever para sempre pedir a mensagem base + ganchos opcionais, e trocar o exemplo resolvido por um que mostre a **base sem notícia, com a peculiaridade**. Deixar explícito no texto: a notícia é opcional; a espinha é objetivo + pessoa.

**3.8. O que o software não faz.** Sem juízo de LGPD, sem orientação jurídica, sem portão de qualidade no lugar do usuário. Ele entrega o rascunho; o usuário adapta e envia. (Alinhado ao movimento 1 do 046, que já tirou a censura de tema.)

---

## 4. Escopo (arquivos)

1. `nucleo/modelos/redacao.py` — `Gancho` (campos opcionais + `peculiaridade`), `validar_ganchos`.
2. `nucleo/redacao.py` — tirar o atalho; `redigir` sempre chama o modelo; `montar_entrada` com `assuntos=[]`.
3. `nucleo/prompts/redigir_ganchos.py` — prompt + exemplo resolvido.
4. `nucleo/fluxo.py` — "sem notícia" não é fim; aviso informativo.
5. `scripts/migracoes/0XX_gancho_uso_sem_assunto.sql` + `queries/gancho_uso.py` — `assunto_id` nulo.
6. `console/templates/_pedido.html` — mensagem base em primeiro, ganchos abaixo.

---

## 5. Testes

- `tests/test_mensagem_base_sem_noticia.py`: pedido sem assunto disponível → uma mensagem base com objetivo + peculiaridade; **sem** aviso de beco; o modelo é chamado.
- `tests/test_base_mais_ganchos.py`: com assuntos relevantes → base + ganchos com notícia.
- `tests/test_peculiaridade.py`: a base cita um fato concreto; sem fato utilizável → mensagem da ficha + aviso informativo, sem invenção.
- `tests/test_validacao_base.py`: base pula a checagem de assunto; gancho com notícia mantém todas.
- `tests/test_gancho_uso_base.py` + migração: `usei`/`não serve` na mensagem base (assunto nulo).
- Ajustar os testes do 038 que esperavam `ganchos=[]` quando não havia assunto.

---

## 6. Fora de escopo (é o brief seguinte, 048)

- A memória que alimenta a próxima geração: leitura incremental das redes a cada pedido, reaproveitamento do acervo comum de notícias entre contatos, e conteúdos gerados virando molde para contatos parecidos (o Luiz como base para outros advogados).
- Coleta e bloqueio do Google (brief 045).

---

## 7. Passos de execução

> AGENTS.md: o executor não roda `git` nem a suíte. Entrega a lista de arquivos tocados e o texto do commit; Sidarta autoriza. Proibido `git add -A`.

1. Esquema e validação (3.3, 3.4).
2. `redigir`/`montar_entrada` sem o atalho (3.1, 3.2).
3. Prompt e exemplo (3.7).
4. Migração e `gancho_uso` (3.5).
5. Tela (3.5).
6. Fluxo e aviso (3.6).
7. Testes da seção 5.
8. Lista para `git add` e mensagem:
   `feat(redacao): a mensagem nasce da pessoa e do objetivo; a noticia vira opcional (brief 047)`

`scripts/verificar.sh`, o teste com o pedido real refeito e o commit são passos de Sidarta.

---

## 8. Critérios de aceite (Sidarta, no Pro)

1. Refazendo o pedido do Luiz **sem** notícia boa sobre a OAB, sai a mensagem que você escreveria — advogado, OAB-SP, convite para o jantar, com uma peculiaridade dele — sem notícia e sem aviso de beco.
2. Havendo notícia relevante, ela entra como gancho **adicional**, não como espinha.
3. Toda mensagem base traz um detalhe específico da pessoa, não só o cargo.
4. Nada é afirmado sobre a pessoa fora dos fatos (a regra do 046 continua valendo).
