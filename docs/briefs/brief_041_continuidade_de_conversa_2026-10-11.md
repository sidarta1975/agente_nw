# Brief 041 — Continuidade de conversa

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Depende de:** briefs 036, 038 e 039.
**Plano:** v3.1, último passo do ciclo de uso.
**Data:** 2026-10-11

---

## 1. Objetivo em uma frase

*"Marcos de novo. Ele respondeu que anda ocupado com a reforma tributária. Continua a conversa."* — o sistema reconhece que é continuação, carrega o histórico daquela pessoa e a mensagem que o usuário enviou, entende o que o contato respondeu e redige a próxima mensagem, mantendo o fio e o registro.

---

## 2. O que já existe e é reaproveitado

- `PedidoExtraido.continuacao` e `objetivo='responder'` (036) — extraídos e gravados, ainda não consumidos.
- `gancho_uso` com status `usado` (038) — diz qual mensagem o usuário efetivamente mandou.
- `consulta_contato` (histórico permanente, só inserção) e `historico.historico_recente_para_prompt`.
- `redacao.redigir` (038) com regra de objetivo `responder` já prevista no prompt.
- Reaproveitamento de coleta do dia (039, 3.4).

---

## 3. Decisões

**3.1. Reconhecimento.** Continuação é `pedido.continuacao = True` ou `objetivo = 'responder'`, ou a frase começa com o nome de uma pessoa com pedido concluído nos últimos `continuidade.dias_janela` = 30 dias seguido de "de novo", "outra vez", "respondeu", "voltou", "me mandou". A extração (036) já captura; aqui o fluxo passa a agir sobre isso.

**3.2. O que a IA recebe a mais no prompt de redação (038, bloco 4 ampliado).**
- A última mensagem **enviada** (o gancho `usado` mais recente daquela pessoa, texto integral) e a data.
- O que o contato respondeu, nas palavras do usuário (campo novo `resposta_do_contato: str` no schema de extração — a IA separa "ele respondeu que anda ocupado com a reforma tributária" do resto da frase).
- Os ganchos anteriores entregues e não usados (para não repetir nem contradizer).
- O registro da relação usado da última vez, a menos que o usuário peça mudança.

**3.3. O que muda na redação para `responder`.**
- Um gancho principal que responde diretamente ao que o contato disse (sem notícia, se o conteúdo da resposta já basta) e, no máximo, dois ganchos com notícia **relacionada ao que o contato trouxe** — os termos de busca do pedido passam a ser gerados a partir da resposta do contato, não só do assunto original.
- A mensagem não reapresenta o usuário, não repete a abertura anterior, não agradece de novo se já agradeceu.
- Se a resposta do contato encerra a conversa ("vamos marcar mês que vem"), a IA devolve uma única mensagem curta de fecho e `aviso = "a conversa parece encerrada por ora"`.

**3.4. Histórico legível na página da pessoa (039, 3.6).** A sequência vira uma linha do tempo: pedido → mensagem enviada → resposta do contato (como o usuário contou) → próxima mensagem. `consulta_contato.contexto_json` já guarda o pedido; a resposta do contato entra em `resumo_redes_sociais`? Não — campo próprio: coluna nova `resposta_do_contato TEXT NULL` em `consulta_contato` (migração `012_resposta_contato.sql`; a tabela é só inserção, e a coluna é preenchida na inserção do pedido de continuação).

**3.5. Sem pessoa identificável.** "Ele respondeu…" sem nome e sem pedido recente único → a tela pergunta "continuar com quem?" listando as três pessoas mais recentes (mesmo mecanismo de `aguardando_pessoa` do 039, com fonte `historico`).

---

## 4. Escopo (arquivos)

1. `scripts/migracoes/012_resposta_contato.sql`.
2. `nucleo/modelos/pedido.py` + `prompts/extrair_pedido.py` (036): campo `resposta_do_contato`; regra de reconhecimento de continuação no prompt.
3. `nucleo/pedido.py`: `resolver_contato` com fonte `historico` para continuação sem nome.
4. `nucleo/redacao.py` + `prompts/redigir_ganchos.py` (038): bloco de continuidade; regras 3.3; termos de busca derivados da resposta do contato quando `responder`.
5. `queries/consulta_contato.py`: `inserir` aceita `resposta_do_contato`; `ultima_mensagem_enviada(perfil_id)` cruzando `gancho_uso` e `consulta_contato`.
6. `nucleo/historico.py`: linha do tempo.
7. `nucleo/fluxo.py` (039): pula localização em continuação; `aguardando_pessoa` com fonte `historico`.
8. `console/templates/pessoa.html`: linha do tempo; `pedido.html`: pergunta "continuar com quem?".
9. `config/limiares.yaml` + `Limiares`: bloco `continuidade` (`dias_janela`).

---

## 5. Testes

- `tests/test_continuidade_extracao.py`: "Marcos de novo, ele respondeu X" → `continuacao=True`, `resposta_do_contato="X"`, `objetivo='responder'`.
- `tests/test_continuidade_redacao.py` (LLM falso): prompt contém a última mensagem enviada e a resposta; `responder` → no máximo 1 principal + 2 com notícia; resposta de encerramento → 1 mensagem e aviso.
- `tests/test_continuidade_fluxo.py`: continuação pula localização; sem nome e com três pessoas recentes → `aguardando_pessoa` com fonte `historico`.
- `tests/test_historico_linha_do_tempo.py`: ordem e campos.
- `tests/test_migracao_012.py`.

---

## 6. Fora de escopo

- Ler a resposta do contato diretamente do WhatsApp ou do e-mail — o usuário conta, em texto.
- Mais de um fio de conversa simultâneo com a mesma pessoa.
- Lembretes de "faz tempo que não fala com X" — nada roda sozinho.

---

## 7. Passos de execução

1. Migração 012; `limiares.yaml`.
2. Extração (campo e regra).
3. `queries/consulta_contato.py`, `historico.py`.
4. Redação (bloco e regras).
5. Fluxo e tela.
6. Testes da seção 5.
7. Lista para `git add` e mensagem: `feat(continuidade): pedido de continuação carrega a última mensagem e a resposta do contato e redige a próxima (brief 041)`.

`scripts/verificar.sh`, o teste real e o commit são passos de Sidarta.

---

## 8. Critérios de aceite (Sidarta, no Pro)

1. Depois de usar um gancho com uma pessoa real e receber resposta, escrever "<nome> de novo, respondeu que …" produz uma mensagem que continua o fio, sem reapresentação nem repetição.
2. A página da pessoa mostra a linha do tempo completa.
3. "Ele respondeu…" sem nome, com mais de uma pessoa recente, pergunta com quem continuar.
4. Resposta de encerramento gera só o fecho curto.
