# Brief E1-012 — Ciclo diário, LaunchAgents e agendamento

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Depende de:** brief 011 (exportação Markdown) e 009 (regra do conector), ambos certificados. **Não depende do console** (brief 010).

---

## 1. Objetivo em uma frase

Um comando único (`agente_nw ciclo`) que faz tudo sozinho todo dia, retomando de onde parou se for interrompido, e dois LaunchAgents que o disparam de manhã cedo sem você precisar abrir o terminal.

---

## 2. Contexto e o que já existe

Todo passo do ciclo já existe como comando isolado e testado: `coletar`, `processar-fila`, `agrupar` (já inclui os embeddings), `qualificar`, `cruzar`, `exportar-menu`, `backup`. Falta só um passo novo — geração de cartão em lote (hoje só existe `cartao <assunto_id>`, um de cada vez) — e a orquestração que os encadeia com retomada.

`agente_nw ciclo` já está reservado em `COMANDOS_RESERVADOS` (`cli.py`), apontando para este brief. A tabela `progresso` (`etapa`, `ultimo_id`, `data_ciclo`, `atualizado_em`) já existe e já é usada internamente por `coleta/rss/leitor.py` para sua própria retomada fina dentro do passo de coleta — este brief usa a mesma tabela, com nomes de etapa diferentes (prefixo `ciclo:`), para saber quais macro-passos do dia já terminaram. O arquivo sentinela (`caminho_sentinela()`, `dados/PARE`) já existe e já é respeitado por `coletar`/`agrupar` internamente.

`scripts/launchd/` já existe, vazio, esperando os dois `.plist`.

---

## 3. Escopo

1. **`config/limiares.yaml`** (aditivo): nova seção `cartao: teto_por_dia: 40` (mesmo valor da qualificação, mesmo raciocínio — teto para limitar o tempo do passo, não uma regra de produto).
2. **`agente_nw/nucleo/database/queries/assuntos.py`** (aditivo): `listar_qualificados_sem_cartao(conexao, limite) -> list[Assunto]` (`substancial IS NOT NULL AND conversavel IS NOT NULL AND resumo_cartao IS NULL`, ordenado por `id`, até `limite`).
3. **`agente_nw/nucleo/relevancia/cartoes.py`** (aditivo): `ResumoCartoes` (`candidatos`, `gerados`, `erros`) e `gerar_pendentes(cliente_llm, conexao, limite) -> ResumoCartoes` — mesmo padrão de `qualificador.qualificar_pendentes`, chamando `gerar_cartao` para cada candidato de `listar_qualificados_sem_cartao`.
4. **`agente_nw/cli.py`**: implementar `ciclo` de verdade (tirar de `COMANDOS_RESERVADOS`), com `ciclo_cmd()` conforme seção 4; adicionar log por execução conforme seção 5.
5. **`scripts/launchd/br.agente_nw.ollama.plist`** (novo).
6. **`scripts/launchd/br.agente_nw.ciclo.plist`** (novo) + **`scripts/rodar_ciclo.sh`** (novo, wrapper — seção 6).
7. **Verificação real no Mac** (não é código, é auditoria — seção 7).

---

## 4. `ciclo_cmd()` — a orquestração, exatamente

Etapas, nesta ordem, cada uma com seu nome de progresso:

| # | Nome de progresso | O que roda |
|---|---|---|
| 0 | *(sem progresso próprio)* | `ler-marcacoes` do arquivo de **ontem**, se existir — decisão tomada agora, seção 4.1 |
| 1 | `ciclo:coleta` | `leitor.coletar` |
| 2 | `ciclo:extracao` | `extrator.processar_fila` |
| 3 | `ciclo:agrupamento` | `agrupador.agrupar` |
| 4 | `ciclo:qualificacao` | `qualificador.qualificar_pendentes` |
| 5 | `ciclo:cruzamento` | `cruzamento.cruzar_contato` para cada contato ativo |
| 6 | `ciclo:cartoes` | `cartoes.gerar_pendentes` (novo, item 3 do escopo) |
| 7 | `ciclo:exportacao` | `markdown.gerar` + escrever `menu_<hoje>.md` |
| 8 | `ciclo:backup` | `backup.fazer_backup` |

**No início, antes de tudo**: ler `sistema.progresso_obter(conexao, "ciclo:backup")`; se `data_ciclo == hoje`, imprimir "Ciclo já rodou hoje (concluído às <atualizado_em>)." e sair com código 0, sem tocar em mais nada. É essa checagem que resolve o segundo gatilho (login) não rodar de novo.

**Antes de cada etapa 1 a 8**: checar `caminho_sentinela().exists()` — se existir, imprimir "Sentinela encontrada, parando antes de <etapa>." e sair com código 0 (não é falha, é parada pedida). Checar também `sistema.progresso_obter(conexao, nome_da_etapa)`; se `data_ciclo == hoje`, pular a etapa (já feita, idempotente) e ir para a próxima.

**Depois de cada etapa concluir sem lançar exceção**: `sistema.progresso_gravar(conexao, nome_da_etapa, None, hoje, agora)` e seguir para a próxima.

**Se uma etapa lançar exceção**: registrar no log (seção 5) o erro completo, **não** gravar progresso daquela etapa, sair com código 1. Uma próxima execução (recuperação do LaunchAgent, ou você rodando `agente_nw ciclo` na mão) vai pular as etapas já concluídas hoje e retomar exatamente da que falhou — é isso que cumpre "interrupção e reexecução completam sem duplicar assunto ou menu": cada etapa já é idempotente por construção própria (mesmo raciocínio dos briefs 007–011: `agrupar` só processa o que está pendente, `cruzar`/`inserir` tem `UNIQUE` por dia, `exportar-menu` sobrescreve o arquivo do dia de forma determinística), então nem precisaria da tabela de progresso para não duplicar — a tabela existe para não *reprocessar à toa* uma etapa já feita, o que economiza minutos reais no critério de aceite de 20 minutos.

### 4.1 Decisão tomada agora, fora do texto literal do plano: `ler-marcacoes` de ontem como etapa 0

O plano não lista leitura de marcação na cadeia do ciclo — mas sem isso, ninguém roda `ler-marcacoes` a não ser que você lembre de rodar na mão todo dia, o que contraria o próprio objetivo deste brief (operação sem you precisar lembrar de nada). Etapa 0: se `saidas/menu_<ontem>.md` existir, roda `ler_marcacoes` nele antes de gerar o menu de hoje. Sem progresso próprio na tabela (é barato, idempotente por natureza — reler o mesmo arquivo de ontem de novo não faz mal, `marcar_usado`/`marcar_nao_serve` só afetam linha `status='novo'`) e sem travar o ciclo se o arquivo não existir ou tiver avisos de formato (mesmo comportamento já construído no brief 011).

---

## 5. Log por execução

Cada chamada de `agente_nw ciclo` grava um arquivo novo em `dados/logs/ciclo_<timestamp ISO com hífen no lugar de dois-pontos>.log` (criar a pasta se não existir). Para cada etapa: linha de início com hora, linha de fim com duração em segundos e o resumo que o comando já imprime hoje no terminal (reaproveitar o texto — não inventar um formato novo). Em caso de falha, a linha final da etapa é o traceback completo. O mesmo conteúdo também vai para o `stdout` (para quando você roda na mão e quer ver na hora) — o log em arquivo é o que sobra depois, para quando o LaunchAgent rodou sem ninguém olhando.

---

## 6. Os dois LaunchAgents

### `br.agente_nw.ollama.plist`
`ProgramArguments`: caminho real do binário `ollama` (rodar `which ollama` no terminal de verdade para descobrir — não adivinhar; normalmente `/usr/local/bin/ollama` ou `/opt/homebrew/bin/ollama` num Mac M-series) + `serve`. `EnvironmentVariables`: `OLLAMA_MAX_LOADED_MODELS=2`, `OLLAMA_KEEP_ALIVE=30m`. `RunAtLoad=true`, `KeepAlive=true`. `StandardOutPath`/`StandardErrorPath` para `dados/logs/ollama.log`.

### `br.agente_nw.ciclo.plist` + `scripts/rodar_ciclo.sh`
**Decisão tomada agora, simplificação deliberada em relação ao texto literal do plano**: o plano pede "`StartCalendarInterval` às 05h00 (...) e segundo gatilho no login com 5 minutos de atraso". O `launchd` não tem um jeito nativo de atrasar só o gatilho de login dentro do mesmo `.plist` sem atrasar também o de calendário. Em vez de um terceiro LaunchAgent (o plano pede dois, não três), uso **um único `.plist`** com `StartCalendarInterval={Hour:5, Minute:0}` **e** `RunAtLoad=true`, os dois apontando para o mesmo wrapper `scripts/rodar_ciclo.sh`, que **sempre** dorme 5 minutos antes de chamar `agente_nw ciclo`. Efeito prático: o disparo de calendário passa a rodar às 05h05 em vez de 05h00 (sem exigência de precisão ao segundo em lugar nenhum do plano) e o disparo de login espera os mesmos 5 minutos pedidos; a checagem "já rodou hoje" da seção 4 resolve os dois gatilhos tentando rodar no mesmo dia sem duplicar nada. `scripts/rodar_ciclo.sh`: `cd` para a raiz do repositório, `sleep 300`, chama `.venv/bin/agente_nw ciclo`, com `set -euo pipefail` e log de início/fim do próprio wrapper (separado do log interno do ciclo, só para diagnosticar se o LaunchAgent sequer chegou a chamar o script).

`KeepAlive` **não** vai neste segundo `.plist` — o ciclo é uma tarefa que termina, não um servidor.

---

## 7. Verificação real no Mac (não é código — é auditoria, faça e reporte)

1. `launchctl list | grep -i ollama` — antes de instalar os LaunchAgents deste brief, confirmar que não há nenhum outro serviço `ollama` já carregado (do próprio instalador do Ollama.app, se você ativou "iniciar no login" nas preferências dele).
2. `brew services list | grep -i ollama` — confirmar que não há serviço do Homebrew ativo (se houver, `brew services stop ollama` antes de prosseguir, e registrar isso no relatório).
3. Conferir manualmente em Preferências do Sistema → Geral → Itens de Login que o `Ollama.app` não está lá (se estiver, remover, e registrar).
4. Só depois de 1–3 resolvidos: instalar os dois `.plist` em `~/Library/LaunchAgents/`, `launchctl load` os dois, reiniciar (ou pelo menos deslogar/logar) para confirmar que ambos sobem sozinhos.

Essa checagem existe porque um segundo servidor Ollama na mesma porta, sem as variáveis de ambiente do projeto, é exatamente a falha silenciosa que o plano quer evitar — os dois modelos brigando por memória e descarregando um ao outro a cada chamada, do jeito que já aconteceu de verdade no brief 007 antes de identificarmos a causa.

---

## 8. Fora de escopo, com justificativa

- **Console web e seu botão "gerar menu agora".** Brief 010, explicitamente não é dependência deste.
- **Calibração dos limiares do conector com dado real.** Ainda sem histórico suficiente — mesma situação carregada desde o brief 009/011.
- **Alertar você (notificação, e-mail) se o ciclo falhar.** Não está no plano deste brief; o log em arquivo é o mecanismo de diagnóstico previsto. Se quiser isso depois, é uma ampliação pontual, não um brief novo.

---

## 9. Passos de execução

1. `config/limiares.yaml`: seção `cartao`.
2. `queries/assuntos.py`: `listar_qualificados_sem_cartao`.
3. `tests/test_assuntos_sem_cartao.py`: assunto qualificado sem cartão aparece; com cartão já gravado não aparece; não qualificado não aparece.
4. `nucleo/relevancia/cartoes.py`: `ResumoCartoes`, `gerar_pendentes`.
5. `tests/test_cartoes_pendentes.py` (com `ClienteOllama` fake): gera cartão para cada candidato; candidato cujo `gerar_cartao` devolve `None` (cartão inválido, foi para `fila_revisao`) conta como erro mas não trava os demais.
6. `cli.py`: `ciclo_cmd()` conforme seção 4, log conforme seção 5.
7. `tests/test_ciclo.py` (com fakes/stubs para LLM e coleta HTTP): etapa já feita hoje é pulada (progresso não muda); etapa que levanta exceção não grava progresso e o comando sai com código 1; segunda chamada no mesmo dia depois de um ciclo completo sai imediato sem rodar nada; sentinela presente para o ciclo antes da próxima etapa sem erro.
8. `scripts/launchd/br.agente_nw.ollama.plist`, `scripts/launchd/br.agente_nw.ciclo.plist`, `scripts/rodar_ciclo.sh`.
9. Rodar `agente_nw ciclo` manualmente contra o estado real e cronometrar (`time agente_nw ciclo`) — critério de aceite exige menos de 20 minutos com os 10 contatos ativos reais de hoje.
10. Fazer a verificação real da seção 7, instalar os dois LaunchAgents, e testar de verdade: deslogar/logar (ou reiniciar) e confirmar pelo `launchctl list` e pelo log que o Ollama subiu sozinho com as variáveis certas.
11. Se possível testar o cenário de sono/despertar dentro da janela desta sessão (colocar o Mac para dormir e acordar depois das 05h00 já é um teste real de dias, não de uma sessão — documentar como pendência de observação nos próximos dias reais, não bloquear o fechamento deste brief por isso).
12. Atualizar `docs/PLAN.md`.

---

## 10. Critérios de aceite

1. `agente_nw ciclo` completo com os contatos ativos reais de hoje roda em menos de 20 minutos (medir e registrar o tempo real).
2. Depois de instalar os LaunchAgents e reiniciar/relogar: `ollama serve` está no ar só pelo LaunchAgent do projeto (nenhum outro processo Ollama concorrente), com `OLLAMA_MAX_LOADED_MODELS=2` e `OLLAMA_KEEP_ALIVE=30m` confirmadas no ambiente do processo (`launchctl print` ou similar).
3. Interromper o ciclo no meio (matar o processo, ou usar a sentinela) e rodar de novo completa sem duplicar `assunto` nem gerar um segundo bloco do mesmo contato no menu do dia.
4. Segunda chamada de `agente_nw ciclo` no mesmo dia, depois de um ciclo já concluído, sai imediatamente sem reprocessar nada.
5. `scripts/verificar.sh` verde.
6. Item pendente de observação real (não bloqueia certificação): confirmar em um dia real de sono/despertar que o disparo de calendário se recupera — registrar em `docs/PLAN.md` como acompanhamento dos próximos dias, já que a medição de aceite formal do produto (brief 013) vai rodar exatamente cinco dias seguidos e serve como essa confirmação.

---

## 11. Riscos e como reverter

| Risco | Controle |
|---|---|
| `which ollama` devolver um caminho diferente do esperado, ou o Ollama ter sido instalado por um método que não deixa binário fixo | resolver na hora, com o caminho real da máquina — nunca hardcodar um caminho de outra máquina |
| macOS não recuperar o `StartCalendarInterval` perdido do jeito esperado (comportamento pode variar entre "dormindo" e "desligado") | o `RunAtLoad` com atraso de 5 min cobre o caso de o Mac ter sido desligado e religado depois — os dois gatilhos juntos cobrem os dois cenários |
| Ciclo passar de 20 minutos com volume real maior no futuro | não é motivo para travar este brief agora — registrar o tempo medido hoje em `docs/PLAN.md` como referência, revisitar se o volume crescer |
| Reverter | Todos os arquivos são novos, exceto as duas funções aditivas em `queries/assuntos.py`/`relevancia/cartoes.py`, a seção nova em `limiares.yaml`, e a remoção de `ciclo` de `COMANDOS_RESERVADOS`. Os `.plist` instalados podem ser removidos com `launchctl unload` + apagar de `~/Library/LaunchAgents/` sem afetar o resto do sistema |

---

## 12. Relatório final obrigatório

Preencher o bloco da seção 8 de `AGENTS.md`, com o caminho do script de verificação para colar no terminal. Sem esse bloco preenchido, o brief não está concluído.
