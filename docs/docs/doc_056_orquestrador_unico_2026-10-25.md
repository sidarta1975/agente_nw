# DOC 056 — orquestrador único pedido → ganchos (relatório do brief 056)

## RELATÓRIO FINAL
- Brief executado: 056. Dependência: `main` em `acb2a67` ou depois (confirmado: `243fb5b`).
- Arquivos criados: `agente_nw/nucleo/orquestracao.py` (nome escolhido pelo executor, como o brief permite), `tests/test_orquestracao.py`, este relatório, `logs/commit_056.txt`, `logs/arquivos_056.txt`.
- Arquivos alterados (uma linha cada):
  - `agente_nw/cli.py`: `pedir_cmd` chama o orquestrador; novo `CanalTerminal` (perguntas por `input`, andamento por `print`).
  - `agente_nw/nucleo/fluxo.py`: `_entender` e `_escrever` chamam o orquestrador; novo `CanalWeb` (perguntas e etapa gravadas no pedido); `marcar_interrompidos` virou chamada à query mais o commit.
  - `agente_nw/nucleo/confirmacao.py`: a escada claro/ambíguo/nenhum de `conduzir` passou a usar `orquestracao.encaminhar_localizacao`; os textos e prompts do terminal são os mesmos.
  - `agente_nw/nucleo/localizacao.py`: `opcao_do_link` usa `queries_listas.nome_e_cabecalho_do_link`.
  - `agente_nw/nucleo/database/queries/pedidos.py`: `marcar_interrompidos` (SQL movido, sem commit).
  - `agente_nw/nucleo/database/queries/listas.py`: `nome_e_cabecalho_do_link` (SQL movido).
  - `tests/test_fluxo.py` e `tests/test_console_mensagem_base.py`: o alvo do `monkeypatch` de `redigir` passou de `fluxo_mod.redacao_mod.redigir` para `agente_nw.nucleo.redacao.redigir`, porque `fluxo.py` não importa mais `redacao_mod`. Nada mais nesses testes mudou.
- Arquivos preservados literalmente na área afetada: `nucleo/pedido.py`, `nucleo/consulta.py`, `nucleo/redacao.py`, `console/app.py`, templates, `_imprimir_pedido`, `_imprimir_redacao`, `FilaDeTrabalho`, `decidir_rede`, `decidir_contato`, perguntas serializadas (`pergunta_de_rede`, `pergunta_de_contato`), fila e thread, `status` e `etapa`.
- Script de verificação: `scripts/verificar.sh`, rodado pelo `scripts/agente_entregar.sh`.
- Manifesto: `logs/arquivos_056.txt` (10 arquivos), `logs/commit_056.txt`.
- Resumo, Doing, Backlog e Done do `docs/PLAN.md` atualizados: sim.

## Decisões do executor

- **Módulo:** `nucleo/orquestracao.py`. **SQL:** `queries/pedidos.py: marcar_interrompidos` e `queries/listas.py: nome_e_cabecalho_do_link`.
- **O que o orquestrador guarda:** (1) `encaminhar_pedido`: a ordem das decisões depois de entender o pedido (mostrar, perguntar redes pendentes, parar sem redação se o canal pedir, contato divergente, contato ambíguo, pedido sem pessoa); (2) `encaminhar_localizacao`: o que fazer com cada resultado `claro`/`ambiguo`/`nenhum`; (3) `preparar_e_redigir`: consulta, redação e registro, com `FalhaNaRedacao` no lugar de `FalhaJsonInvalido` ao redigir.
- **O que continua em cada canal:** como pergunta e como avisa. O resolvedor entra como `Protocol` (`Canal`); a função de aviso é um método do canal. `preparar` entra como argumento, para os testes antigos (`monkeypatch` de `fluxo.preparar` e de `consulta.preparar`) continuarem valendo sem mudança.
- **Console:** a serialização das perguntas (`pergunta_de_rede`) não mudou; o template continua decidindo como mostrar.

## Diferenças de comportamento entre os dois caminhos antigos (passo 2, encontradas antes de escrever código; nenhuma foi decidida pelo executor, cada canal ficou como era)

Pendências de Sidarta (decisão de produto):

1. **Contato divergente** (o nome do pedido não bate com o contato forçado): só o terminal confirma (`[s/N]`) e, sem confirmar, termina com "Contato não confirmado". O console segue sem perguntar.
2. **Contato ambíguo (homônimos):** o terminal usa o mais provável, avisa e, com `--preparar`, termina pedindo `--contato <id>`; com `--json` ele segue com o palpite. O console pergunta qual contato e recomeça.
3. **Localização das redes:** o terminal pergunta uma a uma, com `--sem-perguntar` (aceita o claro, pula o resto), `l` (lista), `c` (colar link), `n` (sem perfil), `p` (pular). O console pergunta todas as redes pendentes de uma vez, sem equivalente de `--sem-perguntar`; o claro sempre pede confirmação.
4. **Correção (pedido filho):** só o console pula a localização e a leitura de rede social e reaproveita a coleta recente. O terminal não tem correção.
5. **Opções só do terminal:** `--menu`, `--json`, `--perfil`, `--trocar-perfil`. No console, trocar perfil é a rota `/pessoa/<id>/trocar-perfil`.
6. **Falhas:** o terminal trata `FalhaJsonInvalido` ao entender e ao redigir com uma mensagem `FALHA:`; uma falha de JSON dentro de `preparar` sobe como traceback (já era assim). O console grava qualquer exceção como `status = erro`.
7. **Texto do aviso de pedido sem pessoa:** terminal "pedido sem pessoa — não há contato para preparar."; console "Pedido sem pessoa: não há contato para preparar.".
8. **Avisos de etapa:** o terminal mostra os `AVISO` na hora; o console os guarda em `pedido.avisos_json`.

Mudança interna sem efeito visível: o terminal pegava o cliente do LLM três vezes (`llm()`); agora pega duas (entender; preparar e redigir).

## Conferências (saída)

```
$ grep -rn -E "(conexao|conn)\.execute\(" agente_nw/ | grep -v "nucleo/database/queries/\|nucleo/database/migracoes.py\|nucleo/database/conexao.py"
(nenhum resultado)   # antes: nucleo/localizacao.py:396 e nucleo/fluxo.py:157

$ ruff check agente_nw tests -> All checks passed!   |   ruff format --check -> 244 files already formatted
$ mypy agente_nw -> Success: no issues found in 113 source files
$ pytest tests/test_orquestracao.py tests/test_fluxo.py tests/test_cli_pedir*.py tests/test_console_tela_unica.py \
         tests/test_console_mensagem_base.py tests/test_pedido_resolver_contato.py -q
  antes da refatoração: 61 passed; depois, com os 23 testes novos: 84 passed in 1.26s
```

Critério 2: em `cli.pedir_cmd` e `fluxo._entender`/`_escrever` não há mais decisão claro/ambíguo/nenhum nem a sequência `preparar → redigir → registrar`; ambos chamam `orquestracao.encaminhar_pedido` e `orquestracao.preparar_e_redigir`.
Critério 5 (teste real no console e no terminal, pessoa conhecida e nome ambíguo): exige Sidarta e a máquina; fica pendente.

## Lacunas

| # | Lacuna | Destino | Impacto |
|---|---|---|---|
| 1 | Diferenças 1, 2, 6 e 7 entre terminal e console (contato divergente, homônimos, falha em `preparar`, texto de pedido sem pessoa) foram unificadas no brief 059 | nenhum | nice |
| 2 | Diferenças 3, 4, 5 e 8 (redes uma a uma × todas de uma vez, correção só no console, opções só do terminal, avisos na hora × guardados no pedido) foram mantidas por decisão de Sidarta no 059 | nenhum | nice |
| 3 | Teste real do critério 5 do 056 (console e terminal, pessoa conhecida e nome ambíguo) está coberto pelo teste real do 059, já em Pendências de Sidarta | nenhum | nice |
