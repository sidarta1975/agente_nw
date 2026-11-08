# Brief 070 — `listas ver` sai da trava; `listas atualizar` continua bloqueada

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Conjunto:** nenhum (brief isolado, direto na `main`) — resolve a decisão [057-3], já registrada no PLAN
**Arquivos-alvo:** `.claude/hooks/guarda_comando.py`, `tests/test_guarda_comando.py` (casos novos), `docs/PLAN.md` (remover a linha `[057-3]` de "Decisões em aberto", já resolvida por este brief), `docs/docs/doc_070_liberar_listas_ver_2026-11-02.md`, `logs/commit_070.txt`, `logs/arquivos_070.txt`
**Seções a ler:** `.claude/hooks/guarda_comando.py` inteiro (a constante `REDE_SOCIAL` e `_decidir_segmento`); `agente_nw/cli.py` (`listas_ver_cmd` e `listas_atualizar_cmd`, para confirmar que `ver` só lê o banco local e `atualizar` é quem acessa a rede); AGENTS.md §8 (o trecho que cita `agente_nw listas ver --rede instagram --filtro a`); `tests/test_guarda_comando.py` para o padrão de teste já usado
**Modelo:** Sonnet
**Esforço:** baixo
**Teste de aceite:** `tests/test_guarda_comando.py`
**Depende de:** nada
**Data:** 2026-11-02

---

## 1. Objetivo em uma frase

`agente_nw listas ver` (lê só o cache local, sem rede) passa pela trava sem bloquear nem perguntar; `agente_nw listas atualizar` (lê a rede social de verdade) continua bloqueado, exatamente como hoje.

---

## 2. Por quê (achado no código, não só pensado)

`guarda_comando.py` bloqueia qualquer comando `agente_nw` cujo subcomando esteja em `REDE_SOCIAL = {"ler-rede-social", "listas", "pedir", "extensao"}` — o bloqueio olha só o nome do subcomando (`listas`), não a ação dentro dele. Mas `agente_nw/cli.py` mostra que `listas` tem duas ações bem diferentes: `listas_atualizar_cmd` chama `atualizar_lista` (acessa a rede social de verdade, com `_contexto_de_navegacao`) e `listas_ver_cmd` só lê `queries_listas.listar_por_rede`/`filtrar_por_texto` — consulta SQL no banco local, sem nenhum acesso de rede. O AGENTS §8 manda o executor rodar exatamente `agente_nw listas ver --rede instagram --filtro a` quando um critério de aceite depende da lista de uma rede social, mas esse comando é bloqueado hoje pela trava — a documentação descreve um caminho que não existe na prática.

---

## 3. Decisões

**3.1. Distinguir `listas ver` de `listas atualizar` na trava.** Em `_decidir_segmento`, quando `programa == "agente_nw"` e `subcomando == "listas"`, olhar a próxima palavra não-opção depois de `listas` (a ação: `ver` ou `atualizar`). Se for `ver`, `PASSAR` (não bloquear, não perguntar). Se for `atualizar` — ou qualquer coisa que não seja `ver` — manter o comportamento atual: `BLOQUEAR` com `MOTIVO_REDE`. Os outros três itens de `REDE_SOCIAL` (`ler-rede-social`, `pedir`, `extensao`) não mudam.

**3.2. Nenhuma mudança em `MOTIVO_REDE` nem nos outros comandos.** Este brief toca só o tratamento do subcomando `listas`; `ler-rede-social`, `pedir` e `extensao` continuam bloqueados por completo, como estão.

**3.3. Fechar a decisão [057-3] no PLAN.** A linha `- [057-3] AGENTS §8 ainda cita...` em "Decisões em aberto" sai do `docs/PLAN.md` — resolvida por este brief, não é mais pendência.

---

## 4. Testes (escritos antes do código)

- `tests/test_guarda_comando.py`, casos novos:
  - `agente_nw listas ver --rede instagram --filtro a` → `PASSAR`;
  - `agente_nw listas ver --rede linkedin` (sem `--filtro`) → `PASSAR`;
  - `agente_nw listas atualizar --rede instagram` → `BLOQUEAR`, `MOTIVO_REDE` (comportamento inalterado — conferir que o teste já existente para isto, se houver, continua verde);
  - `agente_nw listas` sem nenhuma ação (caso improvável, mas o parser exige `--help` ou falha antes) — não precisa de caso novo se o parser já recusa; só testar os dois caminhos reais (`ver`/`atualizar`);
  - um comando composto (`agente_nw listas ver --rede x && agente_nw listas atualizar --rede x`) → o segmento de `atualizar` ainda bloqueia o comando inteiro (confirma que a distinção não abre brecha quando os dois aparecem juntos).

---

## 5. Fora de escopo

- Qualquer mudança em `ler-rede-social`, `pedir` ou `extensao` na trava.
- Mudar `listas_ver_cmd`/`listas_atualizar_cmd` em `cli.py` — este brief só ajusta o hook.
- Reescrever o texto do AGENTS §8 — o exemplo que ele já cita passa a funcionar como está escrito, sem precisar de ajuste no texto.

---

## 6. Passos e aceite

Executar com `/executar 070`. Aceite: testes da seção 4 verdes, gate verde, commit e push pelo executor.

Sem pendência de teste real para Sidarta — é ajuste de trava de bastidor; a prova é toda nos testes da seção 4.
