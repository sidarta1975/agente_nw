# Brief 044 — Extensão do Chrome substitui o navegador separado: a leitura de redes sociais acontece no navegador do usuário

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Base:** `main` em `57b52ad` (brief 037 concluído).
**Posição na sequência:** executa **antes** do brief 038 (redação). Numerado 044 para não renumerar os briefs já entregues; a ordem passa a ser 036 → 037 → **044** → 038 → 039 → 040 → 041 → 042 → 043.
**Data:** 2026-10-12

---

## 1. Objetivo em uma frase

Toda leitura de rede social — listas de conexões, busca de pessoas, leitura de perfil — passa a ser feita pelo Chrome que o usuário já usa, logado, por meio de uma extensão do projeto comandada pelo programa; o navegador separado (Playwright) é removido, e X e Instagram voltam a ser lidos automaticamente.

---

## 2. Por que

O teste real do brief 037 mostrou o custo do navegador separado: o X bloqueou o acesso por navegador automatizado; o Instagram restringe do mesmo modo e sua lista de seguidos é uma janela sobreposta que a rolagem não lê com segurança; o usuário tem de fazer login duas vezes (no Chrome dele e no do programa) e vê uma janela estranha abrir. O usuário rejeitou qualquer solução que envolva ele copiar e colar texto. A única saída que lê sozinha, sem bloqueio e sem segundo login, é a extensão: para a rede, é o usuário navegando no próprio Chrome.

---

## 3. O que já existe e é reaproveitado

- `Pagina` (`coleta/capturas/navegador.py`): `ir_para`, `estado() -> (url, texto)`, `rolar`, `fechar`; `PaginaLista`/`PaginaBusca` acrescentam `coletar_links() -> [(href, texto)]`. **Toda a lógica de parse, listas, busca e leitura de perfil consome só essa interface** — por isso a troca de backend não toca `listas.py`, `busca.py`, `navegador.ler`, `localizacao.py` nem os testes deles, que já injetam páginas falsas.
- `playwright_backend.py`: a única implementação atual; é o que sai.
- Console Flask em `127.0.0.1:8765` (`console/app.py`).
- `REDES_SO_POR_LINK` (`busca.py`), `ListasLimiares`, `config/local.yaml`.

---

## 4. Decisões

**4.1. Arquitetura: página-ponte + extensão.** Três peças:
1. **Ponte** (`agente_nw/ponte/servidor.py`): servidor HTTP mínimo (`http.server` da biblioteca padrão, em thread), em `127.0.0.1:8766`, iniciado por quem precisa do navegador (o comando `pedir`, `listas`, o fluxo do console). Gera um **token aleatório por execução**. Serve a página `/ponte?token=…` e dois endpoints: `GET /tarefa` (long-poll de até 25 s, devolve a próxima tarefa ou vazio) e `POST /resultado`. Tudo exige o token.
2. **Página-ponte** (`agente_nw/ponte/ponte.html` + JS inline): aberta no navegador padrão do usuário com `webbrowser.open`. Fica numa aba com o título "agente_nw — ponte (não feche enquanto estiver em uso)". O JS faz o long-poll de `/tarefa`, repassa cada tarefa à extensão por `chrome.runtime.sendMessage(ID_DA_EXTENSAO, …)` e devolve a resposta em `/resultado`. É a peça viva: evita depender do ciclo de vida do service worker da extensão.
3. **Extensão** (`extensao/`, manifest v3): `background.js` (service worker) recebe as tarefas da página-ponte (via `externally_connectable` restrito a `http://127.0.0.1:8766/*`) e executa com `chrome.tabs` e `chrome.scripting`; `conteudo.js` é injetado na aba alvo para rolar, clicar em "mostrar mais", ler `document.body.innerText` e coletar links. Permissões: `tabs`, `scripting`, `activeTab`, e `host_permissions` só para `linkedin.com`, `instagram.com`, `facebook.com`, `x.com`. Sem acesso a nenhum outro site.

**4.2. Backend novo `PaginaExtensao` (`coleta/capturas/extensao_backend.py`).** Implementa `Pagina`, `PaginaLista` e `PaginaBusca` traduzindo cada método em uma tarefa para a ponte:
- `ir_para(url)` → `{"acao":"abrir","url":…}` → a extensão abre (ou reaproveita) uma aba e devolve `aba_id`; a aba abre **em segundo plano** (`active: false`) para não roubar o foco do usuário.
- `estado()` → `{"acao":"estado","aba_id":…}` → `(url, texto)`; texto limitado a `maximo_caracteres_pagina` (padrão 200.000).
- `rolar()` → `{"acao":"rolar","aba_id":…}`: rola a janela e todo elemento rolável interno, clica em botões cujo texto case com "mostrar mais|ver mais|carregar mais|show more" (lista em `limiares.yaml`), espera `pausa_rolagem_s`.
- `coletar_links()` → `{"acao":"links","aba_id":…}` → `[(href absoluto, texto do elemento ancestral mais próximo que pareça um cartão)]` — mesmo formato que `listas.parse_links` consome hoje.
- `fechar()` → `{"acao":"fechar","aba_id":…}`.
Tempo limite por tarefa: `tempo_limite_tarefa_s` (padrão 60). Sem resposta → `PonteIndisponivel`, tratada pelos chamadores como "sem sessão/indisponível" (já existe esse caminho em todos eles).

**4.3. Sessão e login.** Não há mais espera de login pelo programa: a aba abre no Chrome do usuário; se a rede pedir login, a extensão devolve `estado` com a URL de login e o leitor registra "sem sessão em X — entre no seu Chrome e repita". `--aguardar-login` e a espera de 3 minutos do brief 037 saem. Um único Chrome, uma única sessão.

**4.4. Ritmo humano.** A extensão nunca abre mais de uma aba de rede social por vez e respeita `pausa_entre_paginas_s` (padrão 2,0) entre abrir páginas da mesma rede. `maximo_entradas` das listas continua valendo. Nenhuma tarefa roda sem um pedido do usuário — regra do `AGENTS.md` mantida.

**4.5. X e Instagram voltam ao automático.** `REDES_SO_POR_LINK` passa a vir de `limiares.yaml` (`redes_so_por_link: []`), vazio por padrão. Se o teste real mostrar bloqueio mesmo pela extensão, a rede volta para a lista por configuração, sem código. Instagram: a leitura da lista de seguidos passa a rolar o elemento interno da janela sobreposta (4.2 já cobre "todo elemento rolável").

**4.6. Instalação da extensão (uma vez).** `agente_nw extensao instalar` imprime o caminho da pasta `extensao/` e as instruções: `chrome://extensions` → "Modo do desenvolvedor" → "Carregar sem compactação" → escolher a pasta. O ID da extensão é fixo por chave no `manifest.json` (`key` gerado uma vez e versionado), para que a página-ponte saiba a quem enviar. Navegadores com motor Chrome (Chrome, Brave, Edge, Arc, Vivaldi) servem; Firefox e Safari ficam fora de escopo.

**4.7. `verificar-ambiente`.** O item "Playwright + Chromium" sai. Entra "Extensão do navegador": o comando sobe a ponte, abre a página-ponte, espera até 20 s por um `{"acao":"ola"}` da extensão com a versão; OK com a versão, FALHA com "extensão não respondeu — rode `agente_nw extensao instalar`". Também disponível isolado como `agente_nw extensao testar`.

**4.8. Playwright sai por completo.** `playwright_backend.py`, a dependência em `pyproject.toml`, o `playwright install chromium` do `instalar_macos.sh`, o override de mypy, a pasta `dados/navegador/` (perfis do navegador separado — movida para `dados/_navegador_antigo/` na primeira execução, não apagada). `abrir_pagina_playwright` é substituído por `abrir_pagina_extensao` nos cinco pontos de uso.

**4.9. Segurança.** Ponte só em `127.0.0.1`; token por execução; a extensão só aceita mensagens da origem `http://127.0.0.1:8766`; a página-ponte só aceita tarefas com o token da sua própria URL; `host_permissions` restritas às quatro redes; nenhuma tarefa executa JavaScript arbitrário vindo do Python — o conjunto de ações é fixo (`abrir`, `estado`, `rolar`, `links`, `fechar`, `ola`).

---

## 5. Escopo (arquivos)

1. `extensao/manifest.json` (v3, `key` fixa, `externally_connectable`, `host_permissions`), `extensao/background.js`, `extensao/conteudo.js`, `extensao/icone.png`, `extensao/LEIAME.md` (instalação).
2. `agente_nw/ponte/servidor.py` (servidor, token, fila de tarefas, long-poll), `agente_nw/ponte/ponte.html`, `agente_nw/ponte/__init__.py` (`abrir_ponte() -> Ponte` com `enviar(tarefa, tempo_limite) -> resultado` e `fechar()`; abre o navegador só na primeira tarefa).
3. `agente_nw/coleta/capturas/extensao_backend.py`: `PaginaExtensao`, `abrir_pagina_extensao(pasta_ignorada: Path) -> Pagina` (mesma assinatura do antigo para troca direta), `PonteIndisponivel`.
4. `config/limiares.yaml` + `Limiares`: bloco `extensao` (`tempo_limite_tarefa_s`, `pausa_entre_paginas_s`, `maximo_caracteres_pagina`, `textos_botao_mostrar_mais`); `redes_so_por_link` movido para `listas`.
5. `coleta/capturas/busca.py`: `REDES_SO_POR_LINK` lido dos limiares; `listas.py` e `localizacao.py`: remoção da espera de login; `cli.py`: `--aguardar-login` sai; comandos `extensao instalar` e `extensao testar`; `verificar-ambiente` (4.7); os cinco pontos de `abrir_pagina_playwright`.
6. `console/app.py`: o fluxo de rede social do console usa a mesma ponte; a página-ponte pode ser aberta a partir do console ("abrir ponte") para quem usa só o navegador.
7. Remoções de 4.8. `pyproject.toml` sem `playwright`.
8. `scripts/instalar_macos.sh`: passo da extensão no lugar do `playwright install`.
9. `AGENTS.md`: seção 2 (`extensao/`, `ponte/`), seção 3 (coleta em rede social: "extensão do Chrome do usuário, comandada pelo programa por uma ponte local; nunca navegador separado"), seção 6 (regras de ritmo e de disparo mantidas).

---

## 6. Testes

- `tests/test_ponte_servidor.py`: long-poll devolve a tarefa enfileirada; `POST /resultado` libera `enviar`; token errado → 403; tempo limite → `PonteIndisponivel`.
- `tests/test_extensao_backend.py`: `PaginaExtensao` traduz cada método na tarefa certa (ponte falsa que registra as tarefas e responde fixo); `estado` corta em `maximo_caracteres_pagina`; `fechar` é idempotente.
- `tests/test_extensao_manifest.py`: manifest válido, v3, `key` presente, `host_permissions` restritas às quatro redes, `externally_connectable` só `127.0.0.1:8766`.
- Testes existentes de `listas`, `busca`, `navegador`, `localizacao` e `cli` continuam passando sem alteração de lógica (só a troca de `abrir_pagina_playwright` pelo falso já usado).
- JS da extensão: sem suíte automatizada neste brief (sem Node no projeto); `conteudo.js` é escrito como funções puras e documentado; o teste é o real (seção 8).

---

## 7. Fora de escopo

- Firefox e Safari.
- Publicar a extensão na Chrome Web Store.
- Importação das exportações oficiais de dados das redes (possível brief futuro, opcional).
- Qualquer ação na rede além de abrir, rolar e ler: nada de curtir, seguir, enviar.

---

## 8. Passos de execução

1. Extensão (`extensao/`) e página-ponte.
2. `ponte/servidor.py` e `ponte/__init__.py`.
3. `extensao_backend.py`.
4. Limiares e configuração.
5. Troca dos pontos de uso; remoção do Playwright; `cli.py` (`extensao instalar|testar`, `verificar-ambiente`).
6. `instalar_macos.sh`, `AGENTS.md`, `extensao/LEIAME.md`.
7. Testes da seção 6.
8. Relatório final com: lista para `git add` (inclui `extensao/`), mensagem `feat(extensao): leitura de redes sociais pelo Chrome do usuário via extensão e ponte local; Playwright removido (brief 044)`; e o resultado de `agente_nw extensao testar` — este o executor **não** consegue rodar (exige a extensão carregada no Chrome de Sidarta), e é a única pendência admitida.

`scripts/verificar.sh`, a instalação da extensão no Chrome, o teste real e o commit são passos de Sidarta.

---

## 9. Critérios de aceite (Sidarta, no Pro, no seu Chrome de sempre)

1. `agente_nw extensao instalar` → carregar a pasta no Chrome → `agente_nw extensao testar` responde OK com a versão. `verificar-ambiente` sem item de Playwright.
2. `agente_nw listas atualizar --rede linkedin --forcar` lê as conexões no seu Chrome (abas em segundo plano), sem janela separada e sem pedir login; contagem igual ou maior que as 554 do navegador separado.
3. `agente_nw listas atualizar --rede instagram --forcar` e `--rede x --forcar` leem entradas reais (não vazio, não "Popular").
4. `agente_nw pedir "<frase sobre alguém das suas conexões>"` localiza, confirma e lê o perfil no seu Chrome; nenhuma rede bloqueia.
5. Fechar a aba da ponte no meio de uma leitura → o programa termina com aviso claro, sem travar.
6. Nenhuma aba de rede social é aberta sem um comando seu.
