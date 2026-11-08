# Brief 059 — Terminal e console: unificar as 4 diferenças que importam

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Conjunto:** nenhum (brief isolado, direto na `main`)
**Arquivos-alvo:** `agente_nw/nucleo/orquestracao.py`, `agente_nw/nucleo/fluxo.py`, `agente_nw/cli.py`, `agente_nw/console/app.py` (só se a resposta à pergunta nova precisar de rota), `agente_nw/console/templates/_pedido.html`, `tests/test_orquestracao.py`, `tests/test_contato_divergente.py` (novo), `docs/docs/doc_059_unificar_quatro_diferencas_2026-10-25.md`, `logs/commit_059.txt`, `logs/arquivos_059.txt`
**Seções a ler:** o relatório do brief 056 (`docs/docs/doc_056_orquestrador_unico_2026-10-25.md`), seção "Diferenças de comportamento"; `nucleo/orquestracao.py` inteiro
**Modelo:** Sonnet
**Teste de aceite:** `tests/test_contato_divergente.py` e os casos novos em `tests/test_orquestracao.py` (seção 4)
**Depende de:** brief 056 (`caab38a`)
**Data:** 2026-10-25

---

## 1. Objetivo em uma frase

Das 8 diferenças entre terminal e console listadas no relatório do 056, unificar as 4 que podem dar resultado errado ou mensagem incoerente e manter as outras 4, que são só jeitos diferentes de cada canal perguntar.

---

## 2. Decisões de Sidarta (25/10)

Critério: o console é a interface principal (AGENTS §7) e, havendo dúvida sobre a pessoa, o sistema pergunta. O pior erro do produto é redigir para a pessoa errada.

| # | Diferença (numeração do relatório do 056) | Decisão | Motivo |
|---|---|---|---|
| 1 | Contato divergente: só o terminal confirma | **Unificar: o console também pergunta** | Seguir sem perguntar pode redigir com a ficha de outra pessoa |
| 2 | Homônimos: o terminal usa o palpite, o console pergunta | **Unificar: o terminal interativo também pergunta.** Com `--json`, `--sem-perguntar` ou `--preparar`, fica como hoje (palpite com aviso, ou pedido de `--contato <id>`) | Dúvida sobre a pessoa é sempre perguntada; os modos de script continuam sem pergunta |
| 3 | Redes: uma a uma × todas de uma vez | Manter | Forma de cada tela; o resultado é o mesmo |
| 4 | Correção (pedido filho) só no console | Manter | Recurso da tela única; o terminal não precisa |
| 5 | Opções só do terminal (`--menu`, `--json`, `--perfil`, `--trocar-perfil`) | Manter | Ferramentas de desenvolvimento; o console tem os equivalentes que usa |
| 6 | Falha de JSON dentro de `preparar` sobe como traceback no terminal | **Unificar: o terminal mostra `FALHA: …` e sai com código ≠ 0**, como já faz ao entender e ao redigir | Traceback não diz nada a quem usa |
| 7 | Texto do aviso de pedido sem pessoa diferente nos dois | **Unificar: um texto só**, "Pedido sem pessoa: não há contato para preparar.", definido uma vez no orquestrador | Cosmético; custo zero |
| 8 | Avisos na hora (terminal) × guardados no pedido (console) | Manter | Natureza de cada canal |

---

## 3. Como fazer

**3.1. Contato divergente no console (item 1).** A regra de quando há divergência é a mesma do terminal: o limiar `listas.similaridade_contato_forcado` e a mesma comparação. Ela passa a morar em `orquestracao.encaminhar_pedido`, e os dois canais a recebem dali.
- No console, a divergência vira uma pergunta pendente no mecanismo que já existe (`perguntas_pendentes`, como a de homônimos): "O pedido fala de **{nome do pedido}**, mas o contato escolhido é **{nome do contato}**. Seguir com {nome do contato}?". Opções: "Sim, é essa pessoa" e "Não, escolher outro contato".
  - **"Não"** leva à pergunta de contatos parecidos que já existe (`decidir_contato`).
  - **"Sim"** segue o pedido.
- Se uma rota nova for indispensável, usar o mesmo formato das rotas de resposta existentes. O template mostra a pergunta no mesmo bloco das outras perguntas.

**3.2. Homônimos no terminal interativo (item 2).** Mostrar a mesma lista que o console mostra (os contatos parecidos, com o que os distingue) e pedir o número. Com `--json`, `--sem-perguntar` ou `--preparar`, nada muda.

**3.3. Falha dentro de `preparar` no terminal (item 6).** Capturar no `CanalTerminal` a mesma família de falha que ele já captura ao redigir (`FalhaNaRedacao` / `FalhaJsonInvalido`). Imprimir `FALHA: <mensagem>` e sair com código ≠ 0.

**3.4. Texto único (item 7).** Constante no orquestrador; os dois canais a usam.

---

## 4. Testes (escritos antes do código)

- `tests/test_contato_divergente.py`:
  - console, contato forçado com nome que não bate → o pedido fica `aguardando_pessoa` com a pergunta nova;
  - "Sim" → o pedido segue até a redação;
  - "Não" → aparece a pergunta de contatos parecidos;
  - nome que bate → nenhuma pergunta;
  - terminal, mesmo caso → a confirmação `[s/N]` continua igual.
- `tests/test_orquestracao.py`, casos novos:
  - homônimos no terminal interativo → lista e escolha por número;
  - homônimos com `--json` ou `--sem-perguntar` → palpite com aviso, como hoje;
  - falha de JSON em `preparar` no terminal → `FALHA:` e código ≠ 0, sem traceback;
  - pedido sem pessoa → o mesmo texto nos dois canais.
- O LLM é sempre simulado.

---

## 5. Fora de escopo

As diferenças 3, 4, 5 e 8; os parâmetros de `consulta.preparar`; qualquer mudança no texto das perguntas que já existem.

---

## 6. Passos

Executar com `/executar 059`: testes primeiro, implementação, testes do brief, relatório e PLAN, `scripts/agente_entregar.sh 059`.

Pendência para Sidarta na resposta final: **um teste real só**, que cobre também o critério 5 do brief 056.
1. No console (`http://localhost:8765`): um pedido sobre uma pessoa conhecida, e um pedido só com um primeiro nome comum, para provocar homônimos.
2. No terminal: os mesmos dois pedidos com `agente_nw pedir "…"`.

Nos dois canais, a pergunta sobre a pessoa tem de aparecer só no segundo pedido.

---

## 7. Critérios de aceite

1. Testes da seção 4 verdes, e gate verde na entrega.
2. A regra de divergência existe num lugar só: `grep -n "similaridade_contato_forcado" agente_nw/` aponta só para o orquestrador e para a configuração.
3. O texto "Pedido sem pessoa" aparece uma vez só no código.
4. Commit e push feitos pelo executor; resposta final com a pendência do teste real e mais nada.
