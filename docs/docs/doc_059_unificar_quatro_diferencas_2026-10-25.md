# DOC 059 — terminal e console: unificar as 4 diferenças que importam (relatório do brief 059)

## RELATÓRIO FINAL
- Brief executado: 059. Dependência: brief 056 (`caab38a`), conferida com `git log`.
- Arquivos criados: `tests/test_contato_divergente.py`, este relatório, `logs/commit_059.txt`, `logs/arquivos_059.txt`.
- Arquivos alterados (uma linha cada):
  - `agente_nw/nucleo/orquestracao.py`: `SEM_PESSOA` (texto único), `Desfecho.REINICIAR`, `entender_pedido` (os dois canais entendem o pedido por aqui, com o limiar `similaridade_contato_forcado` lido num lugar só).
  - `agente_nw/nucleo/fluxo.py`: `pergunta_de_divergencia`, `CanalWeb.contato_divergente` pergunta, `decidir_divergencia`; usa `entender_pedido` e `SEM_PESSOA`.
  - `agente_nw/console/app.py`: `responder_pessoa` trata `tipo=divergencia` (mesma rota das outras respostas).
  - `agente_nw/console/templates/_pedido.html`: bloco da pergunta nova, junto das outras.
  - `agente_nw/cli.py`: `pedir_cmd` com laço de recomeço; `CanalTerminal` pergunta o contato entre homônimos; `FALHA:` quando `preparar` falha; usa `SEM_PESSOA` e `entender_pedido`.
  - `tests/test_orquestracao.py`: casos novos (seção 4 do brief).
  - `tests/test_cli_pedir_redacao.py`: o teste `test_homonimos_nao_preparam_nem_gravam_rede_em_quem_pode_ser_outro` passou a usar `sem_perguntar=True`, o modo de script que o brief manda manter como está; o modo interativo agora pergunta. Arquivo fora da lista do brief, uma linha.
- Arquivos preservados literalmente na área afetada: `nucleo/pedido.py`, `nucleo/confirmacao.py`, `nucleo/consulta.py`, textos e formato das perguntas que já existiam, as diferenças 3, 4, 5 e 8.
- Script de verificação: `scripts/verificar.sh`, pelo `scripts/agente_entregar.sh`.
- Manifesto: `logs/arquivos_059.txt` (8 arquivos), `logs/commit_059.txt`.
- Resumo, Doing, Backlog e Done do `docs/PLAN.md` atualizados: sim.

## O que cada item ficou

1. **Divergência no console.** O orquestrador chama `canal.contato_divergente`; o console grava a pergunta "O pedido fala de X, mas o contato escolhido é Y. Seguir com Y?" (`tipo: divergencia`) em `perguntas_pendentes` e o pedido fica `aguardando_pessoa`.
   - **Sim:** a pergunta some e o pedido segue (`continuar_pedido`, direto à redação).
   - **Não:** com contatos parecidos com o nome do pedido, aparece a pergunta de contatos que já existe (`decidir_contato`); sem nenhum, o pedido recomeça sem contato escolhido (a pessoa do pedido vira contato, como hoje).
   - Nome que bate: nenhuma pergunta. Terminal: a confirmação `[s/N]` não mudou (testes `test_terminal_*`).
2. **Homônimos no terminal.** No terminal interativo o `CanalTerminal` lista os contatos (`#id nome — cargo, empresa, cidade`) e pede o número (`q` cancela); o pedido recomeça com o escolhido, reaproveitando o mesmo registro de pedido. Com `--json`, `--sem-perguntar` ou `preparar_depois=False` fica como hoje.
6. **Falha em `preparar`.** `FALHA: não consegui preparar a consulta (…)`, código 1, sem traceback.
7. **Texto único.** `orquestracao.SEM_PESSOA`, usado pelo terminal e pelo console.

## Interpretações e limites (para Sidarta ver)

- **"`--preparar`" do brief.** A opção `--preparar` da CLI é um não-faz-nada (o pedido sempre prepara) e a CLI sempre chama `pedir_cmd(..., preparar_depois=True, ...)`. Se "fica como hoje com `--preparar`" valesse para essa opção, a pergunta nunca apareceria no terminal. Li como o parâmetro `preparar_depois=False` (pedido que só entende, sem consulta): nele não há pergunta, porque não haveria redação depois dela.
- **Homônimos no terminal interativo, mudança visível:** quem rodava `agente_nw pedir "…"` com nome repetido e esperava o aviso "use --contato <id>" agora recebe a pergunta. Para o comportamento antigo: `--sem-perguntar` ou `--json`.
- **Critério 2, regra de divergência "num lugar só":** o limiar `similaridade_contato_forcado` agora só é lido em `orquestracao.entender_pedido` (e na configuração). A comparação de nomes em si continua em `pedido.processar`, que o orquestrador chama; movê-la exigiria inverter a dependência entre `pedido.py` e `orquestracao.py`.
- **"Sim" no console segue direto à redação** e não faz a curadoria das redes sociais daquele pedido (a localização já tinha sido pulada pela divergência); as redes pendentes são perguntadas no próximo pedido sobre o contato. No terminal, o "s" da confirmação continua a localização normalmente (comportamento que não mudei).
- **"Não" sem contatos parecidos** recomeça como pedido novo sobre a pessoa do pedido: o contato é criado, como já acontece quando ninguém tem esse nome.

## Conferências (saída)

```
$ grep -rn "similaridade_contato_forcado" agente_nw config
agente_nw/nucleo/orquestracao.py:99:  ...limiar `listas.similaridade_contato_forcado`) é aplicada aqui...   (docstring)
agente_nw/nucleo/orquestracao.py:111: similaridade_minima_contato=limiares_listas.similaridade_contato_forcado,
agente_nw/nucleo/modelos/configuracao.py:204: similaridade_contato_forcado: float = Field(default=0.5, ge=0, le=1)
config/limiares.yaml:53: similaridade_contato_forcado: 0.5 ...

$ grep -rn "Pedido sem pessoa" agente_nw
agente_nw/nucleo/orquestracao.py:33:SEM_PESSOA = "Pedido sem pessoa: não há contato para preparar."

$ ruff check / ruff format --check / mypy agente_nw -> ok   (rodados pelo gate na entrega)
$ pytest tests/test_contato_divergente.py tests/test_orquestracao.py tests/test_fluxo.py tests/test_cli_pedir*.py \
         tests/test_console_tela_unica.py tests/test_console_mensagem_base.py tests/test_pedido_resolver_contato.py -q
98 passed in 1.40s
```

## Pendência de Sidarta (um teste real só; cobre também o critério 5 do brief 056)

1. No console (`http://localhost:8765`): um pedido sobre uma pessoa conhecida e um só com um primeiro nome comum, para provocar homônimos.
2. No terminal: os mesmos dois pedidos com `agente_nw pedir "…"`.

Nos dois canais, a pergunta sobre a pessoa tem de aparecer só no segundo pedido.

## Lacunas

| # | Lacuna | Destino | Impacto |
|---|---|---|---|
| 1 | A opção `--preparar` da CLI é um não-faz-nada e a CLI sempre chama `pedir_cmd` com `preparar_depois=True`; li "fica como hoje com `--preparar`" como `preparar_depois=False` (sem consulta, sem pergunta). Com nome repetido, `agente_nw pedir` agora pergunta; o comportamento antigo é `--sem-perguntar` ou `--json` | decisão | degrada |
| 2 | A comparação de nomes que decide o contato divergente continua em `pedido.processar`; só o limiar mora no orquestrador. Movê-la exige inverter a dependência entre `pedido.py` e `orquestracao.py` | dívida | nice |
| 3 | Depois de "Sim" à divergência, o console segue direto à redação e não faz a curadoria das redes sociais daquele pedido; as redes pendentes são perguntadas no próximo pedido sobre o contato | decisão | degrada |
| 4 | "Não" à divergência, sem contatos parecidos, recomeça como pedido novo e cria o contato da pessoa do pedido | nenhum | nice |
| 5 | Teste real do 059 (console e terminal; pergunta sobre a pessoa só no segundo pedido) já está em Pendências de Sidarta | nenhum | nice |
