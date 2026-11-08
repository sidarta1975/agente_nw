# Brief 056 — Um único orquestrador para "pedido → ganchos", usado pelo terminal e pelo console web

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Conjunto:** nenhum (brief isolado, direto na `main`)
**Arquivos-alvo:** `agente_nw/nucleo/orquestracao.py` (novo; o executor pode escolher outro nome, registrando no relatório), `agente_nw/nucleo/fluxo.py`, `agente_nw/nucleo/confirmacao.py`, `agente_nw/nucleo/localizacao.py`, `agente_nw/cli.py`, arquivo(s) em `agente_nw/nucleo/database/queries/` que recebem o SQL movido, `tests/test_orquestracao.py` (novo), `docs/docs/doc_056_orquestrador_unico_2026-10-25.md` (relatório), `logs/commit_056.txt`
**Seções a ler:** ARQUITETURA §1 (fluxo), §4 (contratos do motor), §10 (console); armadilhas do PLAN que citem `fluxo`, `confirmacao`, `localizacao` ou `pedir` (busca)
**Modelo:** Opus — refatoração com risco de mudar comportamento sem perceber; exige ler dois caminhos lado a lado
**Teste de aceite:** `tests/test_orquestracao.py` — os três desfechos de localização (claro, ambíguo, nenhum) pelos dois canais, com a mesma pergunta e o mesmo resultado de hoje
**Depende de:** nada; `main` em `acb2a67` ou depois
**Data:** 2026-10-25

> Este brief foi escrito no Projeto em 24/10 com o número 051, que no disco já pertence à avaliação de skills. Renumerado para 056 em 25/10, com cabeçalho no modelo novo; o conteúdo técnico é o mesmo. Uma correção: o aceite antigo pedia testes "passando na execução do próprio Claude Code", o que contraria o AGENTS §6 (o executor não roda a suíte). Agora os testes são escritos pelo executor e rodados por Sidarta.

---

## 1. Objetivo em uma frase

Unificar, num único ponto do código, a sequência "entender o pedido → resolver o contato → resolver a ambiguidade de rede social → preparar a consulta → redigir os ganchos", hoje escrita duas vezes, uma para o terminal e outra para o console web, sem mudar nada do que o usuário vê em nenhum dos dois canais.

---

## 2. O que já existe (lido no código em 24/10; confirmar no passo 2, porque o brief 050 mexeu em `console/app.py` e `redacao.py` depois disso)

**Já compartilhado, não muda.** `nucleo/pedido.py: processar` é chamado tanto por `cli.pedir_cmd` (terminal) quanto por `nucleo/fluxo.py: _entender` (console). Essa função faz a extração do pedido e a resolução do contato.

**Duplicado, ponto 1: resolução de ambiguidade.** Quando a localização do perfil na rede social dá `ambiguo` ou `nenhum`, cada canal resolve a pergunta "qual é a pessoa ou a rede certa?" com seu próprio código:
- Terminal: `cli.pedir_cmd` chama `nucleo/confirmacao.py: conduzir` para cada localização (menu por `input()`, opção de colar link, opção de pular).
- Console: `fluxo._entender` monta `pergunta_de_contato` e `pergunta_de_rede`, grava em `perguntas_pendentes` e espera a resposta por `POST`, resolvida por `decidir_rede` e `decidir_contato`.

**Duplicado, ponto 2: montagem de `preparar` + `redigir`.** Depois de resolvida a pessoa, os dois canais montam à mão a chamada de `nucleo/consulta.py: preparar` e `nucleo/redacao.py: redigir`: o terminal no fim de `cli.pedir_cmd`, o console em `fluxo._escrever`. Cada um avisa o progresso do seu jeito (`print` no terminal; `status` e `etapa` no banco no console).

**SQL fora de `queries/`, correção trivial incluída.** Existem dois pontos de SQL de domínio fora de `nucleo/database/queries/`, contrariando a ARQUITETURA:
- `nucleo/fluxo.py: marcar_interrompidos` (`UPDATE pedido SET status = 'erro' …`);
- `nucleo/localizacao.py: opcao_do_link` (`SELECT nome, cabecalho FROM lista_rede_social WHERE link = ?`).

**Fora deste brief:** `consulta.preparar` tem 16 parâmetros nomeados. Enxugá-lo é mais seguro depois que só o orquestrador o chamar, e vira brief próprio.

---

## 3. Decisões

- **O orquestrador não absorve a fila em thread do console nem o laço de `input()` do terminal.** Cada canal continua dono do seu jeito de perguntar e receber resposta. O que se unifica é a sequência de etapas e a decisão de qual resultado de localização (`claro`, `ambiguo`, `nenhum`) dispara o quê.
- **O resolvedor de ambiguidade entra como `Protocol` passado ao orquestrador**, nunca como `if/else` dentro dele. A função de aviso de progresso entra do mesmo jeito.
- **As duas funções com SQL são só movidas**, sem alterar a consulta.
- **Divergência de comportamento entre os dois caminhos antigos** (uma validação, uma mensagem, uma ordem de checagem que só um lado tinha) **não é decidida pelo executor**: vai para o relatório como pendência de Sidarta, e o comportamento de cada canal fica como está hoje.
- **Nome do módulo e destino do SQL em `queries/`:** decisão do executor, registrada no relatório.

---

## 4. Testes (`tests/test_orquestracao.py`, escrito antes do código)

- Desfecho **claro**: terminal e console chegam a `redigir` sem pergunta.
- Desfecho **ambíguo**: terminal mostra o mesmo menu de hoje; console grava a mesma pergunta pendente de hoje; com a resposta, os dois chegam ao mesmo resultado.
- Desfecho **nenhum**: opção de colar link ou pular, igual a hoje, nos dois canais.
- `marcar_interrompidos` e `opcao_do_link` continuam devolvendo o mesmo resultado no lugar novo.
- O LLM é sempre simulado; nenhum teste deste brief chama o Ollama real.

---

## 5. Fora de escopo

- Enxugar os parâmetros de `consulta.preparar`.
- Os demais candidatos do relatório de arquitetura: regras de ficha e menu dentro de `criar_app`, o tamanho do `cli.py`, a montagem do contexto de redação, a página de navegador.
- Qualquer mudança visível ao usuário, qualquer migração, qualquer prompt.

---

## 6. Passos de execução

> AGENTS.md: o executor não roda `git` nem a suíte.

1. Ler as seções citadas no cabeçalho e este brief.
2. Ler inteiros `nucleo/pedido.py`, `nucleo/fluxo.py`, `nucleo/confirmacao.py`, `nucleo/localizacao.py`, `console/app.py` e a função `pedir_cmd` de `cli.py`. Pôr os dois caminhos lado a lado e listar, no relatório, toda diferença de comportamento encontrada **antes** de escrever código.
3. Escrever `tests/test_orquestracao.py` (seção 4).
4. Criar o orquestrador e as duas implementações do resolvedor (terminal e web).
5. Reescrever `cli.pedir_cmd` e `fluxo._entender`/`fluxo._escrever` para chamarem o orquestrador, preservando fila, thread, `status` e `etapa`.
6. Mover `marcar_interrompidos` e `opcao_do_link` para `queries/`.
7. Rodar a busca do aceite 3 e colar a saída no relatório.
8. Relatório em `docs/docs/doc_056_orquestrador_unico_2026-10-25.md` (bloco do relatório final do AGENTS); mensagem de commit em `logs/commit_056.txt`:
   `refactor(nucleo): orquestrador unico para pedido -> ganchos, usado por terminal e console; move SQL cru para queries/ (brief 056)`
9. Atualizar no `docs/PLAN.md` as seções Resumo, Doing e Done.

O gate (`!scripts/verificar.sh`), o teste real e o commit são de Sidarta.

---

## 7. Critérios de aceite

1. Os três desfechos de localização produzem, nos dois canais, exatamente a mesma pergunta e o mesmo resultado final de hoje (teste de aceite).
2. Nenhuma lógica de decisão "claro/ambíguo/nenhum" fora do orquestrador: `cli.pedir_cmd` e `fluxo._entender`/`_escrever` chamam o orquestrador, não reimplementam a sequência.
3. `grep -rn -E "(conexao|conn)\.execute\(" agente_nw/` fora de `nucleo/database/queries/`, `nucleo/database/migracoes.py` e `nucleo/database/conexao.py`: nenhum resultado.
4. Gate completo verde, rodado por Sidarta.
5. Teste real de Sidarta no console e no terminal: um pedido com pessoa conhecida (desfecho claro) e um com nome ambíguo; a tela e o terminal se comportam como antes.

---

## 8. Riscos e reversão

**Risco principal:** uma diferença pequena entre os dois caminhos antigos passar despercebida. A mitigação é o passo 2 (lado a lado, antes de escrever) e a regra de não decidir sozinho.
**Reversão:** sem migração; `git revert` do commit basta, sem efeito sobre dados gravados.
