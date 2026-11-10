# Brief 086 — Executor em série: rodar vários briefs, um depois do outro, sem acompanhamento

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Conjunto:** correção do texto por inteiro (086 a 095) — este é o primeiro; ele cria o meio de rodar os demais em série
**Arquivos-alvo:** `scripts/executar_serie.sh` (novo), `.claude/serie.settings.json` (novo), `scripts/agente_entregar.sh` (só a ordem entre o commit e as lacunas, item 2.4), `scripts/agente_lacunas.py` (só se o item 2.4 exigir), `.claude/hooks/guarda_comando.py` (só os itens 2.7 e 2.10), `AGENTS_agente_nw.md` (§10, uma frase), `tests/test_executar_serie.py` (novo), `tests/test_guarda_comando.py` (só os casos novos do item 2.10), mais o relatório, o manifesto e o PLAN
**Seções a ler:** `docs/docs/doc_084_viabilidade_execucao_em_serie_2026-11-08.md` e `doc_085_atestado_execucao_em_serie_2026-11-08.md` (inteiros: trazem as provas, as barreiras e o desenho); AGENTS §5, §6, §8, §10; `.claude/skills/executar/SKILL.md`; `scripts/agente_entregar.sh` inteiro; `scripts/agente_lacunas.py`; `.claude/settings.json`; `.claude/hooks/guarda_comando.py` e `tests/test_guarda_comando.py` (os dois inteiros, por causa do item 2.10); `agente_nw/cli.py` (a lista de subcomandos e quais aceitam `--banco`)
**Modelo:** Opus — o script decide, sem ninguém olhando, se um brief foi entregue e se a série pode seguir; um engano aqui deixa a série passar sobre base quebrada
**Esforço:** alto
**Teste de aceite:** `tests/test_executar_serie.py`
**Depende de:** o commit dos briefs 080 a 083, dos documentos canônicos e dos relatórios 084 e 085 (a árvore precisa estar limpa; o executor confere `git status --porcelain` vazio e, se não estiver, para)
**Ordem em série:** livre (é executado sozinho, com `/executar 086`, antes de qualquer série)
**Data:** 2026-11-08 (v2, 2026-11-10: item 2.10 — a trava libera o `agente_nw` de leitura em cópia)

---

## 1. Objetivo em uma frase

Um comando, `scripts/executar_serie.sh 080 081 087 ...`, roda os briefs da lista um depois do outro, cada um numa sessão nova do Claude Code, confere por conta própria se cada um foi mesmo entregue (commit, push e árvore limpa), **para na primeira falha** e avisa Sidarta.

## 2. Decisões (de Sidarta, já tomadas)

**2.1. O código de saída do Claude Code não conta.** Uma parada do `/executar` sai com 0 (provado no relatório 085, teste com o brief 999). O sucesso de cada brief é conferido pelos seis itens do relatório 085, seção 4.2: (a) `logs/entregue_<NNN>_commit.txt` e `logs/entregue_<NNN>_arquivos.txt` existem; (b) o commit mais novo menciona o número do brief; (c) `git rev-list --count origin/main..HEAD` é 0; (d) `git status --porcelain` está vazio; (e) a primeira das três linhas finais não começa com `PAROU:`; (f) no JSON da saída, `is_error` é falso e `subtype` é `success`. Falhou qualquer um: a série para, não tenta o brief seguinte.

**2.2. Parada é a regra, nunca adivinhação.** Em série não há ninguém para responder. O que exigir decisão de Sidarta (lista da seção 5 do relatório 085) termina o brief com "Para você: ..." e a série registra `PAROU PARA DECISÃO` no `STATUS.txt`. Pendência humana que não impede o commit (por exemplo, recarregar a extensão do Chrome) vira "pendência" no `STATUS.txt` e a série segue.

**2.3. Modelo, esforço e ordem vêm do cabeçalho de cada brief.** O script lê `**Modelo:**` (primeira palavra: sonnet ou opus), `**Esforço:**` (baixo, médio, alto → `low`, `medium`, `high`) e `**Ordem em série:**`. Sem os campos, a série para antes de começar. Formas de ordem aceitas: `livre`, `depois de NNN[, NNN...]`, `antes de NNN[, NNN...]`. Texto que não casa com essas formas (por exemplo "antes de qualquer brief que...") é impresso como aviso e não é aplicado. Lista que fira uma ordem é recusada antes de começar. Briefs já entregues (manifesto `entregue_*` existente) são pulados, o que permite retomar com a mesma lista.

**2.4. O PLAN não pode ficar sujo depois do commit (barreira A4).** Decisão: o `agente_lacunas.py` passa a rodar **antes** do commit, e o `docs/PLAN_agente_nw.md` entra no manifesto de todo brief. O executor lê `scripts/agente_entregar.sh` e `scripts/agente_lacunas.py` e faz a menor mudança que cumpra isto; a trava de manifesto (AGENTS §5) continua valendo. Se for impossível sem reescrever o fluxo, o executor para e descreve a alternativa no relatório; não fecha commit extra de `docs(plan)` por fora do `agente_entregar.sh` (git de escrita só ali).

**2.5. Permissões da série em arquivo próprio.** `.claude/serie.settings.json`, passado por `--settings`, com o que os briefs precisam e o `allow` atual não cobre (comandos de terminal como `mkdir`, `cp`, `mv`, `sed` e `python3` limitado a `scripts/*`), e o `deny` atual repetido. O `.claude/settings.json` da sessão interativa **não muda**. A escrita de arquivos já funciona sem esse arquivo (relatório 085, teste 3).

**2.6. Cuidados de ambiente no próprio script:** `caffeinate -dimsu` em volta da série; confere energia na tomada (`pmset -g batt`) e para se estiver na bateria; trava de instância (`logs/serie/TRAVA`, uma série por vez); aviso para fechar outras sessões do projeto; nunca passa `--simular` ao `agente_entregar.sh`; nenhuma palavra de git de escrita no script (o git continua só dentro do `agente_entregar.sh`). Compatível com o Bash 3.2 do macOS. `--max-turns` e `--max-budget-usd` por brief em constantes no topo do script, ajustáveis por variável de ambiente.

**2.7. A trava libera `git worktree list`** (leitura que hoje é bloqueada por estar inteiro na lista de git de escrita). O git de escrita continua proibido fora do `scripts/agente_entregar.sh`, aqui e no script da série (item 2.6).

**2.8. Notificação:** `STATUS.txt` em `logs/serie/<data>/` sempre (uma linha por brief: entregue com hash, ou PAROU e o motivo; custo somado lido dos JSON; lista de pendências humanas; o comando para retomar), e `osascript -e 'display notification ...'` ao terminar e ao parar. Sem hook novo do Claude Code.

**2.9. AGENTS §10** troca a frase "o script nasce no brief 086..." por uma que diga que o script existe e como se usa.

**2.10. A trava libera comando `agente_nw` somente de leitura que aponte explicitamente para uma cópia do banco.** Hoje, qualquer `agente_nw <subcomando>` na pasta principal recebe `permissionDecision: "ask"` da trava ("usa o banco real (AGENTS §6): confirme, ou trabalhe numa cópia"), e numa sessão sem acompanhamento *ask* é recusa — não há quem confirme. Isso barra o passo de medição dos briefs 089 e 095, que são medições em cópia e deveriam poder rodar. (A comparação do brief 090 não ganha comando próprio: ela roda pelo `comparar-vetores` do 089 ou dentro do Python, que a trava não intercepta.) **Decisão de Sidarta, dada ao aprovar esta saída: a trava passa a deixar passar, sem perguntar, só o que satisfizer as cinco condições abaixo, ao mesmo tempo.**

1. **O subcomando está na lista de leitura liberada**, que é exatamente esta: `comparar-vetores` (nasce no brief 089), `medir-dano` e `reprocessar` (nascem no brief 095). Mais os três que já passam hoje e não mudam: `verificar-ambiente`, `copiar-banco` e `listas ver`. **Nada além disto.** Subcomando novo só entra nesta lista por um brief que diga o nome dele e prove que é de leitura; o executor não acrescenta nome por conta própria.
2. **O comando traz `--banco <caminho>`** apontando para a cópia. Os três comandos novos nascem com esse parâmetro **obrigatório** (briefs 089 e 095); sem ele, o comando continua caindo no *ask* de hoje. É por isso que nenhum subcomando de leitura que já existe entra na lista: `ficha`, `menu`, `exportar-menu` e `ler-marcacoes` não têm como nomear uma cópia — leem sempre o caminho da configuração, que é o banco real. Um brief futuro que queira um deles na série acrescenta o `--banco` ao comando e o nome a esta lista, nessa ordem.
3. **O caminho não é o banco real.** A trava resolve o caminho (`Path.resolve()`, que já desfaz `..` e link simbólico) e compara com o caminho real resolvido; iguais, bloqueia. Bloqueia também qualquer comando que cite `agente.db` em qualquer argumento, mesmo junto de um `--banco` de cópia.
4. **O caminho é literal.** Se o argumento do `--banco` tiver `$`, `` ` ``, `~`, `*` ou `?`, a trava **bloqueia**: ela lê o texto do comando, não sabe no que uma variável vai se transformar na hora de rodar. Quando o último pedaço do caminho ainda não existe (a cópia é criada na mesma linha), a trava resolve a pasta que o contém — pasta que é link simbólico para dentro de `dados/` também bloqueia.
5. **`reprocessar` só passa em simulação:** com `--simular` e sem `--confirmo`. Com `--confirmo`, ou sem `--simular`, bloqueia — é gravação, e gravação não roda em série (brief 095, item 2.2).

Fora disso nada muda: `ler-rede-social`, `pedir`, `extensao` e `listas atualizar` continuam bloqueados; `sqlite3` sobre `agente.db` continua bloqueado; qualquer outro `agente_nw` na pasta principal continua perguntando, como hoje. **A proteção do banco real não é afrouxada: o que a regra abre é só o caminho da cópia, nomeada letra por letra.**

## 3. Escopo (arquivos)

| Arquivo | Criar / alterar | O que muda |
|---|---|---|
| `scripts/executar_serie.sh` | criar | Pré-voo (árvore limpa, nada pendente de envio, um arquivo por número de brief, campos do cabeçalho, ordem, energia, trava); laço por brief com `claude -p "/executar NNN"`, conferência de entrega dos seis itens; `STATUS.txt`; notificação. |
| `.claude/serie.settings.json` | criar | Permissões extras da série (2.5). |
| `scripts/agente_entregar.sh`, `scripts/agente_lacunas.py` | alterar | PLAN no manifesto e lacunas antes do commit (2.4). |
| `.claude/hooks/guarda_comando.py` | alterar | Libera `git worktree list` (2.7) e o `agente_nw` de leitura em cópia, com as cinco condições (2.10). Nada mais da trava muda. |
| `AGENTS_agente_nw.md` | alterar | §10 (2.9). |
| `tests/test_executar_serie.py` | criar | Seção 4. |
| `tests/test_guarda_comando.py` | alterar | Só os casos novos do 2.10 (seção 4); nenhuma asserção existente é editada. |

## 4. Testes

O teste monta, em `tmp_path`, um repositório git sintético com um remoto local, briefs de mentira e um `claude` falso (script no `PATH` que imprime um JSON configurável e cria ou não o manifesto e o commit). Casos: (1) lista de dois briefs entregues → STATUS "CONCLUÍDA", código 0; (2) saída 0 do `claude` mas sem manifesto → para no brief, código 1, não tenta o seguinte; (3) primeira linha com `PAROU:` → para; (4) `origin/main..HEAD` maior que zero → para, STATUS traz o comando `git push`; (5) árvore suja no pré-voo → nem começa; (6) ordem violada (`antes de`/`depois de`) → recusa; (7) campo de cabeçalho ausente → recusa; (8) brief já entregue → pulado; (9) trava de instância presente → recusa; (10) `is_error` verdadeiro → para; (11) "Para você" sem `PAROU:` → pendência no STATUS e segue; (12) o script não contém `git add`, `git commit`, `git push`, `--simular`; (13) `osascript` falso no `PATH` é chamado no fim e na parada. Nenhum teste chama o Claude Code, o Ollama, a rede ou o `osascript` reais.

**Testes da regra 2.10, em `tests/test_guarda_comando.py`** (mesmo jeito dos testes que já existem lá: JSON na entrada padrão da trava, `cwd` da pasta principal, e nenhum comando é de fato executado). Nenhuma asserção existente é editada; só entram casos novos:

1. **Libera a leitura em cópia:** `agente_nw comparar-vetores --banco /tmp/copia.db --amostra 50` → passa, sem `ask`. O mesmo para `medir-dano --banco <cópia>` e `reprocessar --simular --banco <cópia>`.
2. **Sem apontar para a cópia continua perguntando:** `agente_nw comparar-vetores --amostra 50`, sem `--banco`, → `ask` (a decisão de hoje, palavra por palavra).
3. **Cita o banco real → bloqueia:** `agente_nw medir-dano --banco dados/agente.db`, e também `agente_nw medir-dano --banco /tmp/copia.db --comparar dados/agente.db` (cópia no lugar certo e banco real em outro argumento) → bloqueados, com o motivo do banco.
4. **Subcomando de escrita mesmo em cópia → o que já valia:** `agente_nw coletar --banco /tmp/copia.db` e `agente_nw processar-fila --banco /tmp/copia.db` → `ask` (não entram na lista de leitura); `agente_nw ler-rede-social --banco /tmp/copia.db` e `agente_nw listas atualizar --banco /tmp/copia.db` → **bloqueados** (rede social nunca roda sozinha).
5. **`reprocessar` fora da simulação → bloqueia:** com `--confirmo`, ou sem `--simular`, mesmo apontando para a cópia.
6. **Tentativas de driblar, todas bloqueadas:** caminho relativo que chega ao banco real (`--banco ./dados/agente.db`); `..` (`--banco /tmp/../Users/sidarta48/github/agente_nw/dados/agente.db`); variável de ambiente ou expansão (`--banco $BANCO`, `--banco "$HOME/github/agente_nw/dados/agente.db"`, `--banco ~/github/agente_nw/dados/agente.db`, `--banco $(echo dados/agente.db)`); link simbólico criado em `tmp_path` apontando para o banco real (e também pasta que é link simbólico, com o arquivo ainda inexistente dentro dela). Em todos, o esperado é bloquear — nunca `ask`, nunca passar.
7. **A lista é fechada:** um subcomando inventado que não está na lista do 2.10, mesmo com `--banco <cópia>` e mesmo sendo de leitura, → `ask`.

## 5. Fora de escopo

Agendar a série (AGENTS §6: nada roda sozinho); e-mail ou push fora do Mac; mudar `.claude/settings.json`; reverter commits automaticamente; limite de uso da assinatura (o `STATUS.txt` registra a parada e a série retoma com a mesma lista).

## 6. Passos de execução

1. Conferir "Depende de". 2. Ler os arquivos da seção "Seções a ler". 3. Escrever os testes. 4. Implementar. 5. Relatório com a tabela `Barreira do relatório 085 | Como foi resolvida | Teste`, mais a resposta a "algum texto é analisado só em parte?" (não se aplica: o script não lê texto de conteúdo). 6. `scripts/agente_entregar.sh 086`. 7. Três linhas finais, com "Para você: fazer o ensaio com o brief 080 (comando no relatório) antes de soltar a série maior".

## 7. Critérios de aceite

1. `pytest tests/test_executar_serie.py -q` verde, saída colada.
2. `grep -nE "git (add|commit|push)|--simular" scripts/executar_serie.sh` sem resultado (saída colada).
3. `git status --porcelain` vazio depois da entrega do próprio 086 (prova de que o PLAN não fica sujo).
4. `pytest tests/test_guarda_comando.py -q` verde, saída colada, com os casos novos do 2.10 e **sem nenhuma asserção antiga editada** (provar com `git diff` do arquivo de teste, que só acrescenta).
5. No relatório, a tabela `Condição do 2.10 | Como a trava confere | Teste`, com as cinco condições, e a lista dos subcomandos liberados copiada do 2.10 — se o executor achar que falta um nome, ele **não acrescenta**: registra como lacuna de decisão.
6. Gate do `agente_entregar.sh` verde.
