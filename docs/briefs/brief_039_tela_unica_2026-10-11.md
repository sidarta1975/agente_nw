# Brief 039 — Tela única: a frase entra, o conteúdo sai

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Depende de:** briefs 036, 037 e 038.
**Plano:** v3.1, decisão 4.2. É o brief em que o produto passa a ser o do plano.
**Data:** 2026-10-11

---

## 1. Objetivo em uma frase

O console abre numa caixa de texto; o usuário escreve a frase, confirma a pessoa quando perguntado, recebe os ganchos com as mensagens prontas, marca o que usou e corrige em texto livre — sem abrir nenhum formulário; as telas antigas ficam num menu "bastidores".

---

## 2. O que já existe e é reaproveitado

- Console Flask (`console/app.py`, Jinja2 puro, `<style>` inline em `base.html`, sem JavaScript de framework, `127.0.0.1` fixo, `--banco` obrigatório).
- `nucleo/pedido.processar` (036), `nucleo/localizacao.localizar/confirmar` (037), `consulta.preparar`, `nucleo/redacao.redigir` (038), `queries/gancho_uso.marcar` (038), `queries/pedidos` (036).
- Templates existentes: `contatos.html`, `ficha.html`, `menu.html`, `temas.html`, `eu.html`, `preparar.html`, `sem_usuario.html`, `confirmar_*.html`.

---

## 3. Decisões

**3.1. Rota inicial `/` é a tela única (`inicio.html`).** Três áreas, de cima para baixo:
1. **Caixa de texto** (`textarea`, 4 linhas, foco automático) e botão "Preparar". Abaixo, três exemplos curtos de frase em cinza, só na primeira visita (sem pedido gravado).
2. **Resultado do último pedido**: cabeçalho (pessoa, objetivo, meio, registro, assunto principal, confiança quando < 0,5 com aviso), ganchos (título, notícia, por quê, mensagem num bloco com botão "copiar" — o único JavaScript permitido neste brief é `navigator.clipboard.writeText`, com fallback de seleção do texto), abordagem presencial quando houver, botões "usei" e "não serve" por gancho (formulários `POST`, sem JavaScript), e o **campo de correção** (3.4).
3. **Histórico**: lista das últimas 20 pessoas com data do último pedido e contagem de ganchos usados; clicar leva a `/pessoa/<perfil_id>` (3.6).

**3.2. Processamento longo sem travar o navegador.** O pedido é demorado (coleta, embeddings, modelo, eventualmente navegador). O `POST /pedir` grava o pedido com `status='processando'` e devolve imediatamente `/pedido/<id>`, que mostra a etapa atual (lida de `pedido.etapa`, atualizada pelo fluxo: "entendendo o pedido", "localizando a pessoa", "buscando notícia", "lendo rede social", "selecionando assuntos", "escrevendo") e recarrega a cada 5 segundos com `<meta http-equiv="refresh">` — sem JavaScript. O trabalho roda numa `threading.Thread` do processo do console, uma por vez (fila simples em memória; segundo pedido enquanto um roda fica "na fila"). SQLite: a thread abre a própria conexão; a regra "SQLite nunca compartilhado entre processos" continua respeitada — é o mesmo processo.

**3.3. Confirmação da pessoa na tela.** Quando `localizar` devolve `ambiguo` ou `nenhum`, o fluxo para em `pedido.status='aguardando_pessoa'` e `/pedido/<id>` mostra as opções (foto quando a rede fornece URL pública, nome, cabeçalho, rede, link) com botões; mais "mostrar a lista" (`/pedido/<id>/lista?rede=X&filtro=...`, 20 por página, escolha por botão) e "colar link" (campo + botão) e "seguir sem rede social". `claro` mostra "É esta pessoa?" com "sim" / "não, mostrar opções" e um prazo: se o usuário não responder, nada acontece — o pedido fica aguardando até ele voltar. Resposta registrada → `localizacao.confirmar` → o fluxo continua da etapa seguinte.

**3.4. Correção em texto livre.** Campo "Corrigir" abaixo dos ganchos: o usuário escreve *"mais informal"*, *"ele é do Rio, não de SP"*, *"não fala de política"*, *"troca o segundo gancho"*. O `POST /pedido/<id>/corrigir` cria um pedido novo com `texto = frase original + "\nCorreção: " + correção` e `pedido_pai_id` (coluna nova), e o fluxo roda de novo **pulando a localização** (pessoa já confirmada) e reaproveitando a coleta do dia (o `preparar` já reconsulta sem coletar de novo quando a coleta do dia existe — se não existir esse atalho, criar `rodar_coleta=False` quando a última coleta foi há menos de `coleta.minutos_reaproveitamento` = 120). A extração (036) recebe a correção e o prompt diz explicitamente que ela prevalece sobre a frase. A redação (038) recebe o pedido corrigido.

**3.5. "Usei" e "não serve".** `POST /pedido/<id>/gancho/<assunto_id>/<usado|nao_serve>` → `gancho_uso.marcar` + `assunto_contato.marcar_usado/marcar_nao_serve` (para o motor não repetir). Volta à mesma página.

**3.6. Página da pessoa (`/pessoa/<perfil_id>`).** O que a IA sabe (cargo, empresa, cidade, vínculo, rede social confirmada, fatos recentes), em texto, não em formulário; histórico de pedidos com os ganchos usados; caixa "contar algo sobre esta pessoa" (texto livre → `fila_extracao.inserir(origem="manual")`, como a ficha faz hoje); botão "trocar o perfil na rede social" (reabre 3.3). Nada aqui é obrigatório para usar o sistema.

**3.7. Bastidores.** As rotas atuais (`/contatos`, `/contatos/<id>`, `/menu`, `/temas`, `/eu`, `/contatos/<id>/preparar`) continuam funcionando, agrupadas num link "bastidores" no rodapé. Nenhum link do fluxo principal aponta para elas.

**3.8. Sem usuário.** `sem_usuario.html` deixa de ser necessário: a primeira frase cria o usuário (036, 3.5). A rota `/` nunca redireciona para cadastro.

**3.9. Erros.** Modelo fora do ar, Google News sem resposta, sessão de rede social ausente — cada um vira uma linha de aviso no resultado ("não consegui ler o LinkedIn: sessão não aberta; os ganchos vieram só da notícia"), nunca uma página de erro. Exceção não tratada grava `pedido.status='erro'` com a mensagem e a página mostra "deu errado em <etapa>: <mensagem>" com botão "tentar de novo".

---

## 4. Escopo (arquivos)

1. `scripts/migracoes/010_pedido_fluxo.sql`: em `pedido`, colunas `status` (`processando|aguardando_pessoa|na_fila|concluido|erro`), `etapa`, `erro`, `pedido_pai_id`, `consulta_id`, `localizacao_json`.
2. `queries/pedidos.py`: `atualizar_status`, `atualizar_etapa`, `obter_ultimo`, `listar_por_perfil`, `pessoas_recentes(limite)`.
3. `nucleo/fluxo.py`: `executar_pedido(pedido_id, caminho_banco, ...)` — orquestra 036 → 037 → preparar → 038, atualizando `etapa`; `retomar_apos_confirmacao(pedido_id, escolha)`; fila em memória e thread.
4. `console/app.py`: rotas `/`, `/pedir`, `/pedido/<id>`, `/pedido/<id>/pessoa` (confirmação), `/pedido/<id>/lista`, `/pedido/<id>/corrigir`, `/pedido/<id>/gancho/<assunto_id>/<acao>`, `/pessoa/<perfil_id>`, `/pessoa/<perfil_id>/contar`; rodapé "bastidores".
5. Templates novos: `inicio.html`, `pedido.html` (processando / aguardando pessoa / concluído / erro, num só template com blocos condicionais), `pedido_lista.html`, `pessoa.html`. `base.html`: navegação reduzida a "Início" e "Bastidores".
6. `console/__init__.py` ou `app.py`: a fábrica recebe `abrir_pagina` e `pasta_navegador` para o fluxo (hoje `preparar_acao` já os recebe — reaproveitar).
7. `consulta.preparar`: parâmetro `rodar_coleta` passa a ser decidido por `fluxo` (3.4).
8. `AGENTS.md`, seção 2 (estrutura: `console/` com a tela única) e seção 7 (uma frase: "a interface principal é a tela única; as demais telas são bastidores").

---

## 5. Testes (cliente de teste do Flask, LLM falso, `abrir_pagina` falso, fluxo síncrono em teste via `executar_pedido` direto)

- `/` sem pedido → caixa e exemplos; com pedido → resultado e histórico.
- `POST /pedir` → redireciona para `/pedido/<id>` com `status='processando'`.
- `executar_pedido` com localização `claro` + `--sem-perguntar` equivalente → `concluido` com ganchos; `ambiguo` → `aguardando_pessoa` e a página mostra opções; `POST` da escolha → retoma e conclui.
- Correção cria pedido filho com `pedido_pai_id`, pula localização, reaproveita coleta, e a redação recebe o texto com "Correção:".
- "usei" marca `gancho_uso` e `assunto_contato`.
- `/pessoa/<id>` mostra fatos, rede confirmada e histórico; "contar algo" enfileira extração.
- Erro simulado no modelo → `status='erro'`, página com "tentar de novo".
- Rotas antigas continuam respondendo 200.

---

## 6. Fora de escopo

- JavaScript além do "copiar" (3.1) — o projeto mantém a regra de HTML puro.
- Temas do usuário inferidos e tela Eu reescrita (brief 040).
- Continuação de conversa (brief 041) — a tela já comporta: a frase "Marcos de novo, ele respondeu X" é só mais um pedido.
- Remoção das telas antigas.
- Autenticação, HTTPS, uso remoto — segue local, loopback.

---

## 7. Passos de execução

1. Migração 010 e `queries/pedidos.py`.
2. `nucleo/fluxo.py` (orquestração, fila, thread, retomada).
3. `consulta.preparar` (reaproveitamento de coleta).
4. Rotas e templates.
5. `AGENTS.md`.
6. Testes da seção 5.
7. Lista para `git add` e mensagem: `feat(console): tela única — frase, confirmação da pessoa, ganchos com mensagens, usei/não serve, correção em texto (brief 039)`.

`scripts/verificar.sh`, o teste real e o commit são passos de Sidarta.

---

## 8. Critérios de aceite (Sidarta, no Pro, uma semana de uso)

1. Todo uso começa em `/` com uma frase; nenhum formulário é aberto em nenhum momento da semana.
2. A página de progresso mostra as etapas e termina com os ganchos sem o usuário recarregar à mão.
3. Confirmação da pessoa funciona nos três desfechos, inclusive "mostrar a lista" e "colar link".
4. Uma correção em texto ("mais informal") produz ganchos novos no registro pedido, sem reler rede social nem recoletar notícia.
5. "Usei" some com o gancho das próximas entregas para aquela pessoa.
6. Erro de modelo ou de rede social aparece como aviso ou como "tentar de novo", nunca como página em branco.
