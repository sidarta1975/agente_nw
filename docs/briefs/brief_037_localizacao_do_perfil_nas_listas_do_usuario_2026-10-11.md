# Brief 037 — Localização da pessoa nas listas do usuário nas redes sociais, com confirmação

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Depende de:** brief 036 (pedido extraído com `pessoa_nome` e `pessoa_pistas`).
**Plano:** v3.1, passo 1a.
**Data:** 2026-10-11

---

## 1. Objetivo em uma frase

Quando o pedido menciona uma pessoa, o sistema a procura primeiro nas listas do próprio usuário (conexões do LinkedIn, seguidos no Instagram e no X, amigos do Facebook), desempata com as pistas da frase, mostra "é esta pessoa?" quando há um candidato claro, apresenta opções quando há dúvida, oferece a lista inteira ou um link colado quando nada serve, e grava a escolha no contato para nunca mais perguntar.

---

## 2. O que já existe e é reaproveitado

- `coleta/capturas/busca.py` (brief 023): `buscar(pagina, rede, nome, empresa)` na busca geral de pessoas da rede; `Candidato`, `ResultadoBusca`, `REDES_SUPORTADAS` (facebook, instagram, linkedin, x), `_parece_pagina_de_login`. Passa a ser o **segundo caminho** (busca geral), intacto.
- `coleta/capturas/playwright_backend.py`: contexto persistente por rede (`pasta_perfil`), `headless=False`, sessão do usuário preservada entre chamadas.
- `coleta/capturas/navegador.py`: `ler(...)` com rolagem e extração de blocos; `_extrair_blocos`.
- `queries/redes_sociais.py`: `inserir`, `listar_por_perfil`, `remover`.
- `ResultadoPedido.contato_ambiguo` e candidatos (brief 036).

---

## 3. Decisões

**3.1. Leitura das listas do usuário, por rede, com cache local.** Módulo novo `coleta/capturas/listas.py`:
- URLs de lista por rede: LinkedIn `https://www.linkedin.com/mynetwork/invite-connect/connections/`; Instagram `https://www.instagram.com/<usuario>/following/` (o `<usuario>` da rede é lido uma vez da página inicial logada e gravado em `config/local.yaml` como `redes.instagram.usuario`, idem para X); X `https://x.com/<usuario>/following`; Facebook `https://www.facebook.com/friends/list`.
- Rolagem até o fim ou até `maximo_entradas` (padrão 2000, em `limiares.yaml`, bloco novo `listas`), com pausa configurável entre rolagens (`pausa_rolagem_s: 1.5`) — automação visível, nunca headless.
- Cada entrada vira `EntradaLista(rede, nome, cabecalho, link, foto_url)`; cabeçalho é o texto curto que a rede mostra sob o nome (cargo/empresa no LinkedIn, bio no Instagram/X).
- Gravação em tabela nova `lista_rede_social` (migração `008_listas.sql`): `rede`, `nome`, `cabecalho`, `link UNIQUE`, `foto_url`, `lido_em`. Cache válido por `validade_dias: 30`; `agente_nw listas atualizar [--rede X]` força releitura; a primeira consulta de uma rede sem cache dispara a leitura e avisa que vai demorar.
- Sessão ausente: mesmo tratamento do brief 017 (abre a rede, espera login até o limite, descarta a rede nesta consulta se recusado) — nunca bloqueia o pedido.

**3.2. Casamento nome + pistas (`nucleo/localizacao.py`).**
1. Candidatos por nome: normalização sem acento/caixa; casa quando o primeiro nome bate e, havendo sobrenome na frase, o sobrenome bate (prefixo). "Marcos" sozinho casa todos os Marcos.
2. Pontuação por pistas: cada pista de `pessoa_pistas` (profissão, empresa, cidade) encontrada no cabeçalho soma 1; a IA é chamada **só quando há mais de um candidato com a mesma pontuação** (tarefa `desempatar_perfil`, schema: `indice_escolhido | null`, `confianca`, `motivo`), recebendo nome, pistas e os cabeçalhos dos empatados.
3. Desfechos:
   - **Um claro**: um único candidato com pontuação máxima e, se houver pistas, pelo menos uma casada; ou a IA devolve `confianca ≥ 0,7`. Resultado `claro`.
   - **Vários**: mais de um candidato e nenhum destacado. Resultado `ambiguo` com até 5 opções ordenadas.
   - **Nenhum** nas listas: resultado `nenhum`; o sistema roda `busca.buscar` (busca geral) em cada rede com sessão e devolve os candidatos dessa busca marcados como `fonte="busca_geral"`.
4. Nunca escolhe sozinho sem confirmação quando `ambiguo`; nunca grava no contato sem a confirmação do usuário (3.4), exceto quando o pedido trouxe `link_rede_social` — aí grava direto.

**3.3. Confirmação no terminal (até a tela do brief 039).** `agente_nw pedir` passa a, após a extração:
- `claro`: imprime `É esta pessoa? [S/n]` com nome, cabeçalho e link; `S` ou Enter confirma; `n` cai no caso `ambiguo` com a lista completa de candidatos por nome.
- `ambiguo`: imprime as opções numeradas (nome, cabeçalho, link, rede); aceita número, `l` para "mostrar a lista" (pagina a lista inteira da rede, 20 por vez, com filtro por texto), `c` para colar um link, `p` para pular (segue sem rede social nesta consulta).
- `nenhum`: diz que não achou nas listas, mostra o que a busca geral trouxe com as mesmas opções `número / l / c / p`.
- `--sem-perguntar`: aceita o `claro` e pula nos demais casos (para scripts e testes).

**3.4. Gravação.** Confirmado → `redes_sociais.inserir(perfil_id, rede, link)` e `perfil.notas` recebe o cabeçalho se vazio; `lista_rede_social.perfil_id` (coluna nova) aponta para o contato. Nas consultas seguintes, contato com rede gravada **não pergunta**; `agente_nw pedir --trocar-perfil "<frase>"` reabre a escolha.

**3.5. Ordem das redes.** LinkedIn primeiro para pedidos de registro `cordial`/`formal` ou com pista de profissão/empresa; Instagram primeiro para `proximo`; demais na ordem de `REDES_SUPORTADAS`. Para quando a primeira rede der `claro` e o usuário confirmar; as outras ficam para a leitura do perfil (brief 017) se já tiverem link.

**3.6. Fatos da lista.** O cabeçalho da entrada confirmada vira um `fato` do contato (`origem="lista_rede_social"`), alimentando o centroide flexível do brief 034 sem leitura adicional.

---

## 4. Escopo (arquivos)

1. `scripts/migracoes/008_listas.sql`: `lista_rede_social` (+ `perfil_id NULL`), índices por `rede` e `nome` normalizado.
2. `queries/listas.py`: `substituir_lista(rede, entradas, agora)`, `listar_por_rede`, `buscar_por_nome(rede | None, nome)`, `vincular(link, perfil_id)`, `cache_valido(rede, validade_dias)`.
3. `coleta/capturas/listas.py`: leitura por rede sobre a interface `Pagina` (como `navegador.ler`); funções puras de parse por rede, testáveis com HTML fixo.
4. `nucleo/localizacao.py`: `localizar(conexao, cliente_llm, pedido, abrir_pagina, pasta_navegador, limiares, agora) -> Localizacao` (`status`, `escolhido`, `opcoes`, `fonte`); `confirmar(conexao, perfil_id, entrada, agora)`.
5. `nucleo/prompts/desempatar_perfil.py` + tarefa `desempatar_perfil` nos dois perfis do `llm_routing.yaml` (`num_ctx: 2048`, `temperature: 0.1`).
6. `config/limiares.yaml`: bloco `listas` (`maximo_entradas`, `pausa_rolagem_s`, `validade_dias`); `Limiares` ganha `ListasLimiares`.
7. `config/local.exemplo.yaml`: bloco `redes:` comentado (`instagram.usuario`, `x.usuario`).
8. `cli.py`: fluxo de confirmação em `pedir`; `--sem-perguntar`, `--trocar-perfil`; comando `listas atualizar [--rede]` e `listas ver --rede X [--filtro texto]`.
9. `nucleo/pedido.py`: `processar` chama `localizar` quando há `pessoa_nome` e o contato não tem rede gravada.
10. `AGENTS.md`, seção 3: tarefa `desempatar_perfil`; seção 6: "leitura das listas do usuário é sob demanda e com cache; nunca periódica".

---

## 5. Testes

- `tests/test_listas_parse.py`: HTML fixo de cada rede (fixtures em `tests/fixtures/listas/`) → entradas corretas; página de login → `sem_sessao`.
- `tests/test_listas_queries.py`: substituição da lista preserva `perfil_id` dos links já vinculados; `cache_valido` por data.
- `tests/test_localizacao.py` (LLM falso): um candidato com pista casada → `claro`; dois com mesma pontuação e LLM confiante → `claro` com o escolhido pela LLM; LLM insegura → `ambiguo`; nenhum nas listas → `nenhum` e `fonte="busca_geral"`; link no pedido → grava sem perguntar; contato com rede já gravada → não chama `localizar`.
- `tests/test_cli_pedir_confirmacao.py`: entrada simulada `S`, `n`, número, `l`, `c <link>`, `p`; `--sem-perguntar` aceita `claro` e pula `ambiguo`.
- `tests/test_migracao_008.py`.

---

## 6. Fora de escopo

- Tela de confirmação no navegador (brief 039 reaproveita `Localizacao` e as mesmas opções).
- Leitura do conteúdo do perfil (já existe, brief 017) — aqui só se localiza e grava o link.
- Redes além das quatro suportadas.
- Qualquer automação periódica de releitura das listas.

---

## 7. Passos de execução

1. Migração 008 e `queries/listas.py`.
2. `limiares.yaml`/`Limiares`, `local.exemplo.yaml`.
3. `coleta/capturas/listas.py` com parse por rede e fixtures.
4. Tarefa e prompt `desempatar_perfil`.
5. `nucleo/localizacao.py`.
6. `cli.py` (`pedir` com confirmação, `listas`).
7. `nucleo/pedido.py`.
8. `AGENTS.md`.
9. Testes da seção 5.
10. Lista para `git add` e mensagem: `feat(localizacao): pessoa localizada nas listas do usuário nas redes, com confirmação e cache (brief 037)`.

`scripts/verificar.sh`, o teste real e o commit são passos de Sidarta.

---

## 8. Critérios de aceite (Sidarta, no Pro, com sessões abertas no LinkedIn e no Instagram)

1. `agente_nw listas atualizar --rede linkedin` lê as conexões e informa a contagem; segunda execução no mesmo dia usa o cache.
2. Dez pedidos sobre dez pessoas reais das suas conexões: a certa é a primeira opção (ou o `claro`) em pelo menos 7; em nenhuma delas uma pessoa errada é gravada sem confirmação.
3. Pedido sobre alguém fora das listas → "não achei nas suas listas" e opções da busca geral.
4. Opção `l` mostra a lista com filtro e permite escolher; `c` aceita link colado.
5. Repetir o pedido sobre a mesma pessoa não pergunta de novo; `--trocar-perfil` reabre.
