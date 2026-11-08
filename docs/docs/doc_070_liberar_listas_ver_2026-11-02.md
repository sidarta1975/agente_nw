# DOC 070 — `listas ver` sai da trava (relatório do brief 070)

## RELATÓRIO FINAL
- Brief executado: 070. Dependência: nenhuma. Confirmei em `cli.py` que `listas_ver_cmd` só consulta o banco local (`queries_listas.listar_por_rede`/`filtrar_por_texto`) e `listas_atualizar_cmd` chama `atualizar_lista`, que acessa a rede.
- Arquivos criados: este relatório, `logs/commit_070.txt`, `logs/arquivos_070.txt`.
- Arquivos alterados (uma linha cada):
  - `.claude/hooks/guarda_comando.py`: `agente_nw listas ver …` passa; `listas atualizar` (e qualquer ação que não seja `ver`) continua bloqueado com `MOTIVO_REDE`; `ler-rede-social`, `pedir` e `extensao` não mudaram.
  - `tests/test_guarda_comando.py`: `listas ver --rede instagram --filtro a` e `listas ver --rede linkedin` passam; `listas atualizar`, `listas` sem ação e os comandos compostos com `ver` e `atualizar` bloqueiam. O caso antigo `listas ver --rede instagram` saiu da lista de bloqueios, porque contradizia o brief.
  - `docs/PLAN.md` (fora do git): saiu a decisão [057-3].
- Arquivos preservados literalmente na área afetada: `cli.py`, AGENTS §8 (o exemplo `agente_nw listas ver --rede instagram --filtro a` passa a funcionar como está escrito), `MOTIVO_REDE`.
- Script de verificação: `scripts/verificar.sh`, pelo `scripts/agente_entregar.sh`.
- Manifesto: `logs/arquivos_070.txt` (2 arquivos), `logs/commit_070.txt`.
- Resumo, Doing, Backlog e Done do `docs/PLAN.md` atualizados: sim.

## Conferências

```
$ pytest tests/test_guarda_comando.py -q
60 passed in 1.31s
```

## Lacunas

Sem lacunas.
