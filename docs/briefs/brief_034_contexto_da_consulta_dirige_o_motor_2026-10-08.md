# Brief 034 — O contexto da consulta dirige o motor: menu sem exigir tag do contato nem tema do usuário

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Base:** `main` em `5d46d73` (origin/main sincronizado em 2026-10-08).
**Substitui:** brief 029 (escrito em 2026-09-21, nunca implementado) e dispensa o brief 030 (auditoria), porque a investigação que o 030 pedia foi feita e está na seção 2 deste brief.
**Data:** 2026-10-08

---

## 1. Objetivo em uma frase

No fluxo sob demanda (`preparar`, pela CLI ou pela tela do console), o que o usuário digita na hora — assunto, objetivo, o que interessa, o que evitar — é suficiente, sozinho, para o sistema buscar notícia, selecionar assuntos e montar o menu com o "por quê" de cada item; tags do contato, fatos lidos da rede social e temas do usuário entram como enriquecimento quando existirem, nunca como pré-requisito.

---

## 2. Diagnóstico verificado no código (por que o menu sai vazio hoje)

Lido em `5d46d73`. Quatro pontos, todos confirmados por trecho:

1. **`agente_nw/nucleo/relevancia/cruzamento.py`, `cruzar_contato`:** a primeira coisa que faz é `perfis.calcular_centroide(conexao, perfil_id, ...)`, que só considera linhas de `perfil_tema` com `confirmado = 1`. Sem tag confirmada, devolve `None` e a função retorna `sem_assunto=True, motivo="contato sem tema confirmado"`. É o bloqueio direto.
2. **`agente_nw/nucleo/consulta.py`, `preparar`:** o docstring diz literalmente: "O `contexto` inteiro é serializado em `contexto_json`; hoje não é lido pelo motor". `cruzamento.cruzar_contato(...)` é chamado sem o contexto. O modelo `ContextoConsulta` (`assunto`, `meio`, `objetivo`, `interessa`, `evitar`, `livre`) existe e chega até ali, mas para no histórico.
3. **`agente_nw/coleta/rss/leitor.py` + `google_news.py`:** as consultas ao Google News são geradas por `gerar_consultas(temas_usuario)` — só temas do usuário. Nem o `assunto` da consulta nem as tags/fatos do contato entram na busca. Com usuário sem tema, a coleta é só o `fontes.yaml` genérico.
4. **`agente_nw/coleta/capturas/leitor.py`:** a leitura de rede social grava `fatos` (`fatos.inserir`), não `perfil_tema`. O motor de cruzamento não lê `fatos`. Logo, mesmo depois de ler o LinkedIn do contato, o centroide do contato continua `None`.

Conclusão: o diagnóstico do brief 029 estava correto e incompleto — além do piso da regra do conector, o contexto não participa de nenhuma etapa (busca, seleção, pontuação, "por quê"), e os fatos da rede social não alimentam o cruzamento.

---

## 3. Decisões

**3.1. O contexto vira um vetor e é o sinal principal.** Em `preparar`, antes da coleta, monta-se o texto da consulta: `assunto` + `objetivo` + termos de `interessa` + `livre`, e gera-se o embedding (`bge-m3`, mesmo cliente de sempre) — o **centroide da consulta**. Esse vetor é obrigatório; os outros são opcionais.

**3.2. Centroide do contato passa a ter três fontes, em ordem de preferência, sem bloquear.** (a) tags confirmadas, como hoje; (b) na ausência, tags sugeridas e não confirmadas (`confirmado = 0`), com peso 0,5; (c) na ausência de qualquer tag, o embedding do texto concatenado dos `fatos` do contato (rede social + textos adicionados na ficha), limitado aos 20 fatos mais recentes. Se nenhuma das três existir, o centroide do contato é `None` e o fluxo **continua** — a aderência ao contato vale 0 e o menu se apoia no contexto.

**3.3. A busca de notícia usa o contexto e o contato.** Em `google_news.py`, nova função `gerar_consultas_da_consulta(contexto, termos_contato)`: uma consulta Google News para `assunto`, uma por termo de `interessa` (até 5), e uma por tag/fato-chave do contato (até 3, só se existirem). As consultas dos temas do usuário continuam sendo geradas quando houver temas. Mantém-se o intervalo entre chamadas ao Google News já configurado em `limiares.coleta`.

**3.4. `evitar` filtra.** Candidato cujo título ou texto gerado contenha um termo de `evitar` (comparação sem acento e sem caixa) é descartado antes da pontuação, com `motivo="evitado pelo contexto"` gravado em `assunto_contato` (`status="descartado"`). Não é cosseno: é correspondência literal, previsível para o usuário.

**3.5. Seleção de candidatos pelo contexto.** `candidatos.selecionar_por_consulta(conexao, perfil_id, centroide_consulta, centroide_contato | None, ...)`: ordena os assuntos qualificados e não vistos pelo cosseno ao centroide da consulta; quando houver centroide do contato, a chave de ordenação é `0,7 × cos_consulta + 0,3 × cos_contato`. Mesmos filtros de substância e conversabilidade de hoje.

**3.6. Nova pontuação, função nova, sem tocar na antiga.** Em `pontuacao.py`, `avaliar_por_consulta(centroide_assunto, centroide_consulta, centroide_contato | None, temas_usuario, conversavel, limiares)`:
- `aderencia_consulta` = cosseno ao centroide da consulta (≥ 0).
- `aderencia_contato` = cosseno ao centroide do contato, ou 0 se `None`.
- `aderencia_usuario` = como em `avaliar` hoje (melhor tema ponderado), ou 0 sem temas.
- `score = 50 × aderencia_consulta + 25 × aderencia_contato + 10 × aderencia_usuario + 15 × conversavel`.
- `tipo`: `conector` quando `aderencia_consulta ≥ consulta_minima` **ou** houver tema do usuário/tag do contato acima de `adjacencia_minima`; `viavel_com_esforco` quando `conversavel ≥ conversavel_viavel`; senão `fora_do_dominio`.
- `ponto_de_apoio`: o termo do contexto (assunto ou item de `interessa`) mais próximo do assunto, ou o tema/tag quando for ele que sustentou o `conector`.

`avaliar` e `cruzar_contato` atuais ficam intactos (ainda servem ao comando `cruzar` legado e aos testes antigos). O caminho novo é `cruzar_contato_por_consulta(cliente_llm, conexao, perfil_id, contexto, centroide_consulta, limiares, agora)` em `cruzamento.py`, e `preparar` passa a chamar só ele.

**3.7. Limiar novo, com valor inicial declarado.** `config/limiares.yaml`, bloco `conector`: `consulta_minima: 0.45`. Justificativa: o centroide da consulta vem de um texto curto digitado pelo usuário, enquanto os temas têm descrição de oito ou mais palavras — o cosseno típico contra um assunto relacionado é menor que o de um tema bem descrito. 0,45 é ponto de partida; a calibração vem do uso (3.9).

**3.8. O "por quê" recebe o contexto.** O prompt de `cruzar_por_que` ganha o bloco "Contexto da consulta: assunto X; objetivo Y; interessa: ...; evitar: ...". Sem tag nem tema, o `por_que` deve dizer por que o assunto serve **para aquela consulta** ("você quer retomar contato falando de X; esta notícia traz Y sobre X"). Com tag/tema, cita a conexão adicional. Schema JSON da resposta não muda.

**3.9. Instrumentação para calibrar depois.** Cada linha de `assunto_contato` gerada pelo caminho novo grava também `aderencia_consulta` (coluna nova, migração `006_aderencia_consulta.sql`, `REAL NULL`). É o dado que permite ajustar `consulta_minima` com uso real, em vez de chute.

**3.10. Perfil do usuário continua necessário, temas não.** `perfis.obter_usuario` precisa existir (a tela "Eu" do console cria em um passo: nome). Temas do usuário passam a ser opcionais em todo o caminho novo: `listar_confirmados_com_embedding` vazio → `aderencia_usuario = 0`, sem `assert`.

---

## 4. Escopo (arquivos)

1. `agente_nw/nucleo/consulta.py`: montar texto e embedding da consulta; centroide do contato pelas três fontes (3.2); gerar consultas Google News do contexto (3.3) e passá-las à coleta; filtro `evitar` (3.4); chamar `cruzar_contato_por_consulta`; atualizar o docstring ("o contexto é lido pelo motor desde o brief 034").
2. `agente_nw/coleta/rss/google_news.py`: `gerar_consultas_da_consulta`.
3. `agente_nw/coleta/rss/leitor.py`: `coletar(...)` aceita lista extra de feeds (parâmetro opcional `feeds_extras`, padrão vazio) — sem mudar o comportamento do comando `coletar` da CLI.
4. `agente_nw/nucleo/database/queries/perfis.py`: `calcular_centroide_flexivel(conexao, perfil_id, peso_nivel, cliente_llm)` implementando 3.2; `calcular_centroide` atual intacto.
5. `agente_nw/nucleo/database/queries/fatos.py`: `listar_recentes(conexao, perfil_id, limite)` se não existir.
6. `agente_nw/nucleo/relevancia/candidatos.py`: `selecionar_por_consulta`.
7. `agente_nw/nucleo/relevancia/pontuacao.py`: `avaliar_por_consulta`; `Avaliacao` ganha `aderencia_consulta: float | None = None`.
8. `agente_nw/nucleo/relevancia/cruzamento.py`: `cruzar_contato_por_consulta`.
9. `agente_nw/nucleo/prompts/` (prompt do `cruzar_por_que`): bloco de contexto.
10. `scripts/migracoes/006_aderencia_consulta.sql` + `queries/assunto_contato.py` (coluna nova, leitura e escrita).
11. `config/limiares.yaml` + `ConectorLimiares`: `consulta_minima`.
12. `agente_nw/console/templates/preparar.html`: nenhuma mudança de formulário; apenas, no resultado, mostrar o `ponto_de_apoio` ao lado do "por quê" (já existe o campo).
13. `AGENTS.md`, seção 7: acrescentar uma frase — "O contexto digitado na consulta é o sinal principal do cruzamento; tags, fatos e temas enriquecem quando existem e nunca bloqueiam."

---

## 5. Testes (novos; os antigos continuam passando porque o caminho antigo fica intacto)

- `tests/test_cruzamento_por_consulta.py`, com cliente LLM falso e embeddings controlados:
  1. contexto preenchido, contato **sem** tag, usuário **sem** tema → menu com pelo menos 1 item, `tipo="conector"`, `aderencia_contato == 0`, `por_que` presente;
  2. contexto + tag confirmada no contato → mesmo assunto recebe score maior do que no caso 1 e `ponto_de_apoio` cita a tag;
  3. contexto + contato sem tag mas com 3 fatos gravados → `centroide_contato` não é `None` e `aderencia_contato > 0`;
  4. termo em `evitar` presente no título de um candidato → candidato gravado como `descartado`, `motivo="evitado pelo contexto"`, fora do menu;
  5. `avaliar` antigo com os mesmos vetores → resultado idêntico ao de antes (regressão).
- `tests/test_google_news_consulta.py`: `gerar_consultas_da_consulta` produz 1 + len(interessa) + len(termos_contato) feeds, nomes distintos, URL com os termos entre aspas.
- `tests/test_candidatos_por_consulta.py`: ordenação 0,7/0,3 quando há centroide do contato; só cosseno da consulta quando não há.
- `tests/test_migracao_006.py`: coluna `aderencia_consulta` existe após `migracoes.aplicar`.

---

## 6. Fora de escopo, com justificativa

- **Reescrever ou remover `avaliar`/`cruzar_contato`/comando `cruzar`.** Ficam como estão: o caminho novo é adicional e o commit deste brief é reversível removendo as funções novas e a chamada em `preparar`.
- **Calibrar `consulta_minima` agora.** Sem dado real não há calibração; a coluna `aderencia_consulta` existe para isso.
- **Confirmação automática de tags a partir de fatos.** Os fatos entram no centroide (3.2c), o que resolve o problema sem criar tags que o usuário não pediu.
- **Qualquer modo automático ou em lote.** Fora desde o brief 016.

---

## 7. Passos de execução

1. Migração 006 e modelo/queries de `assunto_contato`.
2. `ConectorLimiares.consulta_minima` + `limiares.yaml`.
3. `google_news.gerar_consultas_da_consulta`; `leitor.coletar(feeds_extras=...)`.
4. `perfis.calcular_centroide_flexivel`; `fatos.listar_recentes`.
5. `candidatos.selecionar_por_consulta`; `pontuacao.avaliar_por_consulta`; `cruzamento.cruzar_contato_por_consulta`; prompt do `por_que` com contexto.
6. `consulta.preparar` religado ao caminho novo (3.1, 3.3, 3.4).
7. Template `preparar.html` (ponto de apoio) e `AGENTS.md` seção 7.
8. Testes da seção 5.
9. Entregar a lista para `git add` e a mensagem de commit sugerida: `feat(consulta): contexto da consulta dirige busca, seleção e pontuação; tags, fatos e temas viram enriquecimento (brief 034)`.

`scripts/verificar.sh`, o teste manual no navegador (seção 8) e o commit são passos de Sidarta, no terminal dele — o executor não roda a suíte nem o git.

---

## 8. Critérios de aceite (verificação manual de Sidarta, no console do Pro)

Com banco recém-criado (`agente_nw migrar`), perfil do usuário criado na tela "Eu" **sem nenhum tema**, um contato real cadastrado **sem nenhuma tag** e sem rede social cadastrada:

1. Tela "Preparar" com assunto, objetivo e dois itens em "interessa" → menu com pelo menos 1 item, cada um com "por quê" que cita o assunto/objetivo digitado. Nunca mais "contato sem tema confirmado".
2. Repetir com um termo de "evitar" que apareça no título de um item do passo 1 → esse item some, e o contador de descartados sobe.
3. Cadastrar uma tag no contato e repetir → o item relacionado sobe de posição e o "por quê" cita a tag.
4. `scripts/verificar.sh` verde.
