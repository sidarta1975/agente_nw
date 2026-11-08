# Doc 060 — O pedido começa pela pessoa: lista de contatos na tela inicial

Brief: `docs/briefs/brief_060_pedido_comeca_pela_pessoa_2026-10-25.md`. Executado em 2026-10-30.

## 1. Como ficou

**Tela inicial (`/`).** `GET /` recebe `?q=` (formulário comum, sem JavaScript) e mostra a lista de `perfis.listar_para_inicio(conn, termo, limite)`: sem busca, os 20 contatos usados mais recentemente (último `pedido` ou `consulta_contato`), completando com os demais em ordem alfabética; com busca, até 50 contatos cujo nome ou apelido contém o termo, sem acento nem caixa. Cada linha linka para `/pessoa/<id>/pedir`. Abaixo, "Não está na lista" é uma âncora (`#texto-livre`) para a caixa de texto livre de hoje — sem JavaScript, como a tela única exige.

**Escolher a pessoa.** `GET /pessoa/<id>/pedir` (`pedir_pessoa.html`) pergunta "O que você quer com {nome}?" e envia para `POST /pedir` com `perfil_id` no formulário. `fluxo.criar_pedido` agora aceita `perfil_id` e grava o pedido já com o contato — o orquestrador (`nucleo/pedido.resolver_contato`, brief 059) já tratava `pedido.perfil_id` como contato forçado, então nenhuma mudança foi necessária em `nucleo/orquestracao.py` nem em `nucleo/pedido.py`: a pergunta de homônimos não aparece (contato já resolvido) e a pergunta de divergência aparece normalmente quando a frase cita outra pessoa. A página da pessoa ganhou o link "Fazer um pedido para {nome}".

**"Esta pessoa não tem redes sociais."** Nova `rede_sem_perfil.marcar_todas(conn, perfil_id, agora)` declara "sem perfil" em cada rede de `busca.REDES_SUPORTADAS`. A curadoria de redes em `nucleo/pedido._localizar_na_rede` já pula toda rede em `rede_sem_perfil.listar_redes` — com todas marcadas, nenhuma rede é procurada nem perguntada; nenhuma mudança foi necessária ali. "Trocar perfil" (`localizacao.confirmar`) já chama `rede_sem_perfil.remover` para a rede do link gravado — desfaz a marcação daquela rede, sem mudança de código. A página mostra "Sem redes sociais" no lugar da lista de redes quando `sem_nenhuma_rede` (nenhuma rede social gravada e todas as suportadas marcadas "sem perfil").

## 2. Fora do que o brief pediu, mas necessário para o gate

`tests/test_console_tela_unica.py`: a asserção `"Pessoas recentes" in inicio` do teste `test_inicio_lista_as_pessoas_recentes_e_as_telas_antigas_seguem_no_ar` dependia do cabeçalho antigo, substituído pela nova lista (que não usa mais esse rótulo). Ajustada para checar o nome do contato na lista nova (renomeado para `test_inicio_lista_os_contatos_e_as_telas_antigas_seguem_no_ar`); o resto do teste (telas de bastidores no ar) não mudou.

## RELATÓRIO FINAL
- Brief executado: 060 — o pedido começa pela pessoa
- Arquivos criados: `agente_nw/console/templates/pedir_pessoa.html`, `tests/test_inicio_lista_contatos.py`, `tests/test_sem_redes_sociais.py`, `docs/docs/doc_060_pedido_comeca_pela_pessoa_2026-10-25.md`, `logs/commit_060.txt`, `logs/arquivos_060.txt`
- Arquivos alterados (resumo em uma linha cada):
  - `agente_nw/console/app.py` — `/` passa a listar contatos (`perfis.listar_para_inicio`); `/pedir` aceita `perfil_id`; novas rotas `/pessoa/<id>/pedir` e `/pessoa/<id>/sem-redes-sociais`; `/pessoa/<id>` calcula `sem_nenhuma_rede`
  - `agente_nw/console/templates/inicio.html` — lista de contatos com busca no topo, "Não está na lista" como âncora para a caixa de texto livre
  - `agente_nw/console/templates/pessoa.html` — link "Fazer um pedido para {nome}", botão "Esta pessoa não tem redes sociais", "Sem redes sociais" quando todas marcadas
  - `agente_nw/nucleo/database/queries/perfis.py` — nova `listar_para_inicio` (+ `ContatoParaInicio`, `_ultimo_uso_por_contato`)
  - `agente_nw/nucleo/database/queries/rede_sem_perfil.py` — nova `marcar_todas`
  - `agente_nw/nucleo/fluxo.py` — `criar_pedido` aceita `perfil_id` opcional
  - `tests/test_console_tela_unica.py` — uma asserção trocada (ver seção 2); nada mais tocado
- Arquivos preservados literalmente na área afetada: `agente_nw/nucleo/orquestracao.py`, `agente_nw/nucleo/pedido.py`, `agente_nw/nucleo/localizacao.py` (o suporte a contato forçado e a "desfazer sem perfil" já existiam, do brief 059/037)
- Script de verificação (o gate, rodado pelo `scripts/agente_entregar.sh`; saída colada): ver "Comandos executados"
- Comandos executados: `scripts/agente_entregar.sh 060`
- Manifesto do commit: `logs/arquivos_060.txt` e `logs/commit_060.txt` (conteúdo abaixo)
- Pendências e decisões que ficaram abertas: as três do próprio brief (§6), só Sidarta pode rodar o console de verdade:
  1. Abrir o console, escolher um contato da lista e fazer um pedido.
  2. Usar "Não está na lista" uma vez.
  3. Marcar o amigo sem redes sociais.
- Resumo, Doing, Backlog e Done do `docs/PLAN.md` atualizados: sim

## Lacunas

| # | Lacuna | Destino | Impacto |
|---|---|---|---|
| 1 | Teste real: escolher um contato da lista e fazer um pedido pelo console | pendência | nice |
| 2 | Teste real: usar "Não está na lista" uma vez | pendência | nice |
| 3 | Teste real: marcar o amigo sem redes sociais pelo console | pendência | nice |
