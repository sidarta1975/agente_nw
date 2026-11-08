# Brief 045 — Coleta de notícias resiliente

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Depende de:** nada novo; mexe na coleta que já existe (briefs 034/035/038). Pode ser executado já.
**Plano:** v3.1 — desbloqueio do uso real. Não muda o que o produto entrega, só como ele busca notícia.
**Data:** 2026-10-13

---

## 1. Objetivo em uma frase

A etapa de coleta deixa de depender de martelar o Google News: não repete uma busca recente, faz poucas buscas por pedido, nunca insiste depois de um bloqueio (429/503) e cai numa fonte alternativa sem chave quando o Google recusa — de modo que um bloqueio **degrada** o resultado (ganchos a partir das publicações do contato e dos temas do usuário, como já acontece) em vez de **travar** o fluxo, e um pedido termina em bem menos que os 4 a 9 minutos de hoje.

---

## 2. Diagnóstico (por que o uso real está travado)

Lido no código em `coleta/rss/`:

- `coleta/rss/google_news.py` → `gerar_consultas_da_consulta` monta, por pedido, **uma busca para o assunto, até 5 de `interessa`, até 6 de `termos_busca` e até 3 do contato** — até 15 buscas.
- `coleta/rss/leitor.py` → para cada notícia de cada busca, o programa ainda **resolve o link pelo próprio `news.google.com`** (`url_canonica`) e depois baixa a página. Ou seja, um pedido vira **dezenas** de acessos ao Google.
- No bloqueio (429/503), `coletar` marca `ResumoColeta.bloqueio` e **para na hora** — mas só dentro daquele pedido. **Não há memória do bloqueio entre pedidos nem entre reinícios.** O pedido seguinte chama o Google de novo e **renova** o bloqueio, que dura horas.

Consequência: os cinco pedidos reais e a semana de uso que faltam para o aceite dos briefs 038/039 são impossíveis enquanto cada tentativa reacende o bloqueio.

---

## 3. O que já existe e é reaproveitado

- `coleta/rss/leitor.py`: `coletar(...)` lê `feeds_arquivo + feeds_google_news(temas do usuário) + feeds_extras`; já respeita `intervalo_google_news_segundos` (2 s) nos pedidos ao `news.google.com`; já para em 429/503 (`_CODIGOS_DE_BLOQUEIO`); já limita `maximo_itens_novos_por_feed` (15); já passa pelo filtro de ruído (`ruido.e_ruido`) e de duplicado por `hash_titulo`.
- `coleta/rss/google_news.py`: `gerar_consultas_da_consulta(contexto, termos_contato)` e `_feed_de_termo`.
- `coleta/rss/canonicalizar.py` (`url_canonica`, `hash_titulo`) e `coleta/rss/ruido.py`.
- `config/limiares.yaml`, bloco `coleta:`, mapeado em `ColetaLimiares` (`nucleo/modelos/configuracao.py`). Já tem `intervalo_google_news_segundos`, `maximo_itens_novos_por_feed`, `minutos_reaproveitamento` (hoje só usado pela correção em texto, brief 039).
- `nucleo/database/queries/sistema.py` (`progresso_obter`/`progresso_gravar`) — já grava estado de coleta no banco.
- `nucleo/consulta.py` / `nucleo/fluxo.py`: orquestram a coleta do pedido.
- Regra já vigente (briefs 038/044): sem assunto com relação ao pedido, ao contato ou aos temas, o programa **avisa em vez de inventar gancho**.

---

## 4. Decisões

**4.1. Nunca insistir num bloqueio (cooldown persistente).**
Guardar, por host, a hora até a qual aquele host está bloqueado. Antes de pedir a um host, se `agora < bloqueado_ate`, **não chama** — pula direto para a fonte alternativa (4.4) ou segue sem notícia. Ao receber 429/503 de um host, grava `bloqueado_ate = agora + coleta.cooldown_bloqueio_minutos` (padrão 180). O estado fica no banco (tabela `sistema`, chave/valor por host, ex. `coleta_bloqueio_ate_news.google.com`), para **atravessar pedidos e reinícios**. Se a tabela `sistema` não for chave/valor arbitrário, o executor acrescenta o menor armazenamento que sirva e registra no relatório. É esta decisão que corrige o "cada tentativa renova o bloqueio".

**4.2. Menos buscas por pedido (teto + junção + parada antecipada).**
Em `gerar_consultas_da_consulta`, antes de montar os feeds:
- normalizar (minúsculas, sem acento duplicado, sem espaços sobrando) e **deduplicar** os termos entre as quatro origens (assunto, contato, termos_busca, interessa);
- **ordem de prioridade**: assunto → termos do contato → termos_busca → interessa (o produto vale pelo que o contato publica);
- cortar no teto `coleta.max_consultas_por_pedido` (padrão 4).
E em `coletar`, parar de abrir novos feeds do pedido quando já houver `coleta.candidatos_suficientes` itens novos aproveitáveis (padrão: reusar `conector.candidatos_por_contato`, 10, se não quiser um número novo).

**4.3. Reaproveitar busca recente por termo.**
Antes de criar um feed (Google ou alternativa) para um termo, verificar se um termo equivalente já foi coletado dentro de `coleta.horas_reuso_termo` (padrão 24) — se já, **reaproveita** os itens guardados em vez de pedir à rede. Generaliza para todo pedido o que hoje só a correção em texto faz via `minutos_reaproveitamento`. Chave: o termo normalizado de 4.2. Um segundo pedido sobre o mesmo assunto no mesmo dia não refaz as buscas.

**4.4. Fonte alternativa sem chave.**
Novo `coleta/rss/fonte_alternativa.py`, espelhando `google_news.py`: gera `FeedFonte` a partir dos mesmos termos, de uma fonte **sem chave, sem conta e sem nuvem**. Candidata principal: Bing News RSS (`https://www.bing.com/news/search?q=<termo>&format=rss`). O executor **valida do IP do Pro** qual fonte sem chave devolve RSS utilizável (Bing, ou uma cesta de RSS de veículos pt-BR) e justifica a escolha no relatório. O mesmo `_processar_fonte` lê (interval, teto, ruído, duplicado idênticos). A alternativa é acionada quando o Google está em cooldown (4.1) **ou** bloqueia no meio do pedido. Notícia continua **melhor esforço**: se Google (cooldown) e alternativa não trouxerem nada, o pedido conclui com ganchos a partir das publicações do contato e dos temas, com o aviso que já existe. Mantém 100 % local: as duas fontes são HTTP público sem chave, mesma categoria do RSS do Google de hoje.

**4.5. Dizer de onde veio (ou não) a notícia.**
Acrescentar a `ResumoColeta` o campo `fonte_usada` (`google` / `alternativa` / `reaproveitada` / `nenhuma`) e levá-lo ao pedido. Mostrar uma linha em `/pedido/<id>` e na saída do CLI:
- "Notícias: Google"
- "Notícias: fonte alternativa (Google bloqueado até HH:MM)"
- "Notícias reaproveitadas da coleta de hoje"
- "Sem notícias agora — ganchos a partir das publicações e dos seus temas."
Nenhum gancho inventado (já é a regra).

---

## 5. Escopo (arquivos)

1. `config/limiares.yaml`, bloco `coleta:` + `ColetaLimiares` (`nucleo/modelos/configuracao.py`): `cooldown_bloqueio_minutos: 180`, `max_consultas_por_pedido: 4`, `horas_reuso_termo: 24`, `candidatos_suficientes` (ou reuso de um existente), `usar_fonte_alternativa: true`.
2. `nucleo/database/queries/sistema.py`: ler/gravar o cooldown por host (4.1).
3. `coleta/rss/google_news.py`: dedupe, ordem de prioridade e teto em `gerar_consultas_da_consulta` (4.2).
4. `coleta/rss/fonte_alternativa.py` (novo): consultas da fonte sem chave (4.4).
5. `coleta/rss/leitor.py`: respeitar o cooldown antes de cada host; reaproveitar termo dentro da janela (4.3); acionar a alternativa no bloqueio/cooldown (4.4); parar quando houver candidatos suficientes (4.2); preencher `ResumoColeta.fonte_usada` (4.5).
6. `nucleo/consulta.py` / `nucleo/fluxo.py`: propagar `fonte_usada` ao pedido.
7. `console/templates/pedido.html` + CLI (`cli.py`): a linha da fonte (4.5).

---

## 6. Testes (seção 5 dos briefs anteriores; tudo sem rede — `httpx` e `feedparser` falsos)

- `tests/test_coleta_cooldown.py`: um 503 grava `bloqueado_ate`; o pedido seguinte **não chama** o host e usa a alternativa; passado o cooldown, volta ao Google.
- `tests/test_coleta_teto_consultas.py`: pedido com muitos termos gera no máximo `max_consultas_por_pedido` feeds, com os termos certos na ordem de prioridade e sem repetição.
- `tests/test_coleta_reuso_termo.py`: termo coletado há menos de `horas_reuso_termo` não gera novo pedido de rede; mais antigo, gera.
- `tests/test_coleta_fonte_alternativa.py`: com o Google em cooldown, lê a alternativa e passa pelo mesmo ruído/duplicado.
- `tests/test_coleta_rotulo_fonte.py`: `ResumoColeta.fonte_usada` chega a `pedido.html` e ao CLI nos quatro casos.
- `tests/test_coleta_degradacao.py`: Google em cooldown e alternativa vazia → pedido conclui com ganchos de publicações/temas e aviso, **sem erro**.

---

## 7. Fora de escopo (viram brief próprio)

- Detecção de novidade nas redes por hash dos blocos (TODO do relatório de 14/10): ataca o tempo da leitura de redes, não o bloqueio. Fica para o brief seguinte.
- Qualquer fonte que exija chave, conta ou nuvem.
- Enviar mensagem, agendar, rodar sozinho: nada disso muda.

---

## 8. Passos de execução

> AGENTS.md: o executor não roda `git` nem a suíte. Entrega a lista de arquivos tocados e o texto do commit; Sidarta autoriza. Proibido `git add -A`.

1. Limiares + modelo (`ColetaLimiares`).
2. Cooldown por host no `sistema` (4.1).
3. Teto, dedupe e ordem das consultas (4.2).
4. Fonte alternativa (4.4), com a validação do IP do Pro no relatório.
5. Reaproveitamento por termo e acionamento da alternativa no `leitor.py` (4.3).
6. Rótulo da fonte na tela e no CLI (4.5).
7. Testes da seção 6.
8. Lista para `git add` (só os arquivos tocados) e mensagem:
   `feat(coleta): coleta de noticias resiliente — cooldown persistente, menos consultas, reaproveitamento por termo e fonte alternativa (brief 045)`

`scripts/verificar.sh`, o teste com rede real (`pytest -m rede_real`) e o commit são passos de Sidarta.

---

## 9. Critérios de aceite (Sidarta, no Pro)

1. Com o Google bloqueado, um pedido novo **conclui** em vez de travar, e a tela diz de onde vieram (ou não) as notícias.
2. Dez pedidos seguidos **não renovam** o bloqueio: depois do primeiro 503, o programa não volta a chamar o Google até passar o cooldown.
3. Um segundo pedido sobre o mesmo assunto no mesmo dia **reaproveita** — não refaz as buscas.
4. Com o Google liberado, o resultado é igual ou melhor que o de hoje, com menos consultas.
5. O tempo por pedido cai de forma perceptível (medir depois com `agente_nw medir`, brief 042).
