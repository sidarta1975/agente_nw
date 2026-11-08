# Brief 055 — Documentos canônicos: ler menos, nada desatualizado, regras novas valendo

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Conjunto:** nenhum (brief isolado, direto na `main`)
**Arquivos-alvo:** `AGENTS.md`, `docs/PLAN.md`, `docs/PLANO.md`, `docs/ARQUITETURA.md`, `docs/briefs/_modelo.md` (novo), `docs/historico/PLAN_historico_ate_2026-10-25.md` (novo), `docs/historico/2026-10-25_pre_055/` (cópias de segurança, novo), `docs/docs/doc_055_documentos_canonicos_2026-10-25.md` (relatório, novo), `logs/commit_055.txt` (novo)
**Seções a ler:** este brief inteiro; `AGENTS.md` inteiro; os quatro documentos inteiros, uma vez (este é o brief que os reorganiza)
**Modelo:** Sonnet
**Teste de aceite:** as conferências por comando da seção 8 (não há `.py` tocado; não há gate de código)
**Depende de:** o commit, por Sidarta, dos 16 arquivos pendentes do brief 050 (comentários do usuário). O diff pendente do `AGENTS.md` já foi conferido: é a frase do brief 050 na seção 7, legítima. Sem esse commit, a alteração deste brief no `AGENTS.md` se mistura com a do 050.
**Data:** 2026-10-25

---

## 1. Objetivo em uma frase

Fazer os quatro documentos lidos antes de cada brief dizerem só o que é verdade hoje e caberem em cerca de 25 mil caracteres de leitura obrigatória, contra 100.796 hoje. O histórico vai para fora da leitura obrigatória sem perder uma linha, e as regras já decididas em 24 e 25/10 entram no `AGENTS.md`, exceto as que dependem de ferramentas ainda não construídas.

---

## 2. Por que agora (o que foi medido em 25/10)

| Documento | Hoje | Problema |
|---|---|---|
| `AGENTS.md` | 13.627 caracteres | §2 (estrutura, 2.712) repete a §2 da ARQUITETURA; §3 (stack, 3.110) mistura regra com descrição |
| `docs/PLAN.md` | 57.951 caracteres | O topo diz "Última atualização: 2026-09-19", "Etapa 1 — MVP", "ciclo 5 dias", "Próximos passos: briefs 007 a 013": tudo superado. Armadilhas: 13.423 caracteres. Histórico e atualizações: 34.308 |
| `docs/ARQUITETURA.md` | 17.316 caracteres | §9 descreve o filtro de categorias sensíveis, removido no brief 046. §10 lista as rotas antigas do console, anteriores à tela única do brief 039. §11 descreve dois agendadores do macOS (LaunchAgents) e um ciclo às 05h00, removidos no brief 016; o AGENTS diz "Agendamento: não existe" |
| `docs/PLANO.md` | 11.902 caracteres | §6 (governança) não tem a numeração única nem a regra de brief gravado no disco |

O executor lê tudo isso antes de cada brief e encontra afirmações que se contradizem. Corrigir isso é o maior ganho de token do projeto: cerca de 20 mil tokens por brief.

**`docs/` está fora do git.** PLAN, PLANO e ARQUITETURA não têm versão anterior para voltar. Por isso o primeiro passo é a cópia de segurança (seção 7, passo 1), seguindo a convenção já usada em `docs/historico/2026-09-17_pre_v5/`.

---

## 3. `docs/PLAN.md` — nova forma

**3.1. Estrutura nova, nesta ordem:**

```
# PLAN.md — estado vivo do agente_nw

## Resumo                      (até 40 linhas)
## Doing                       (uma linha por brief em execução)
## Backlog                     (uma linha por brief escrito e não executado)
## Done — últimos 30 dias      (uma linha por brief concluído)
## Pendências de Sidarta       (o que exige a máquina ou a presença dele)
## Decisões em aberto          (só as abertas)
## Dívidas conhecidas          (só as abertas)
## Armadilhas já identificadas — não redescobrir   (inalterada, texto literal)
```

Formato de linha nas seções Doing, Backlog e Done:
`- NNN · título curto · estado (concluído/sem commit/não iniciado) · commit (hash curto ou —) · data`

**3.2. O Resumo** tem fase atual, último brief concluído, o que está em execução, os três próximos, o último commit e os bloqueios. Quem o escreve é o executor, neste brief. Um brief posterior fará um script gerá-lo no fechamento.

**3.3. Conteúdo inicial**, conferido em 25/10. Confirme cada linha contra o `git log` antes de gravar e corrija se divergir:
- **Done:** 036, 037, 038, 039, 044, 045, 046, 047 com commit; 050 concluído e sem commit até o pré-requisito (depois do commit de Sidarta, registrar o hash).
- **Backlog, não iniciados:** 040 perfil do usuário inferido; 041 continuidade de conversa; 042 medição de uma semana de uso; 043 documentação e comitê; 048 molde por contexto; 049 juízo de relação com o objetivo.
- **Backlog, escritos no Projeto e ainda fora do disco:** unificação do pedido e dos ganchos; auditoria de contaminação externa. O Projeto numerou esses dois como 051 e 052, números que no disco já são de outros documentos. Registrar pelo título, sem número, e marcar "número a reatribuir pelo Projeto".
- **Pendências de Sidarta:** teste real das dez frases do brief 036 e de um `pedir` com pessoa real pela extensão (linha atual do PLAN).
- **Decisões em aberto e Dívidas:** manter só o que ainda está aberto. Item riscado ou marcado "Resolvida" vai literalmente para o arquivo de histórico.

**3.4. Histórico.** Tudo a partir de `## Histórico de decisões` (linha 82 até o fim), mais os itens resolvidos ou superados do topo, vai **literalmente**, sem reescrever uma palavra, para `docs/historico/PLAN_historico_ate_2026-10-25.md`. No fim do PLAN fica uma única linha apontando para esse arquivo. A partir daí, o histórico é consultado por busca (`grep`), não lido inteiro.

**3.5. As armadilhas ficam no PLAN, inalteradas, mas saem da leitura obrigatória.** Cada brief cita no cabeçalho, em "Seções a ler", as armadilhas da área que toca. Sem citação, o executor procura no PLAN, por busca, o nome do módulo que vai editar.

---

## 4. `AGENTS.md` — alterações

O texto de regra existente não se perde em nenhuma hipótese. A seção 8 lista as frases que precisam continuar lá.

**4.1. §1, ordem de leitura.** A frase "Leia, nesta ordem… o código já existente na área afetada" é substituída por:

> O Claude Code carrega este arquivo sozinho no início da sessão (versão 2.1.277 ou posterior; sem `CLAUDE.md` na pasta). Antes de alterar qualquer coisa, leia: `docs/PLAN.md` até o fim de `## Dívidas conhecidas`; as seções do PLANO, da ARQUITETURA e das armadilhas citadas em "Seções a ler" no cabeçalho do brief; o brief; o código existente da área afetada. O histórico (`docs/historico/`) é consultado por busca, nunca lido inteiro. Não criar `CLAUDE.md` nem `CLAUDE.local.md` neste repositório: com eles, o Claude Code deixa de ler este arquivo.

**4.2. §2, estrutura.** Antes de mexer, compare a árvore da §2 do AGENTS com a §2 da ARQUITETURA e com o disco (`ls` das pastas citadas). Leve para a ARQUITETURA o que só o AGENTS tem (por exemplo `ponte/`, `extensao/`, `coleta/capturas/`, a tela única em `console/`). Corrija o que não existe mais no disco. No AGENTS, a §2 vira duas linhas:

> Estrutura do repositório: `docs/ARQUITETURA.md` §2. Nome do pacote e da pasta é sempre `agente_nw`; desvio de nomenclatura é corrigido imediatamente.

**4.3. §3, stack.** Fica no AGENTS só o que é regra. O resto (lista de tarefas de LLM com o modelo de cada perfil, dimensões do embedding, `memoria_minima_gb`, detalhes dos perfis `air16`/`pro48`) vai para a ARQUITETURA §8 (Camada de LLM), e o que for de hardware vai para o PLANO §5. Continuam no AGENTS, com a redação atual:
- Python 3.12 do Homebrew.
- SQLite em WAL, nunca compartilhado entre processos.
- Ollama nunca pelo Ollama.app nem por `brew services`.
- No Pro, nunca subir servidor próprio nem parar ou reiniciar a instância compartilhada `http://127.0.0.1:11435` do cervello.
- Rodar `ollama list` antes de sugerir download.
- `think: false` em toda tarefa, e `enviar_think: false` para modelos sem raciocínio.
- `format: json` com esquema e `num_ctx` explícito em toda chamada.
- Pydantic v2 `frozen=True`.
- Dependências via `config/container.py`.
- Console e ponte só em `127.0.0.1`.
- As regras da extensão: uma rede por vez, ações fixas, imagem nunca gravada, nunca navegador separado.
- Agendamento não existe.
- Suíte só por Sidarta.

**4.4. §5, git.** Acrescentar, sem tirar nada:

> Sidarta roda o git com `scripts/commitar.sh <arquivo_de_mensagem> <arquivos…>`, no terminal ou digitando `!scripts/commitar.sh …` dentro do Claude Code. O executor grava a mensagem do commit em `logs/commit_<NNN>.txt` e lista os arquivos no relatório. Push só por Sidarta.

**4.5. §6, suíte.** Acrescentar, sem tirar nada:

> O gate completo é `scripts/verificar.sh`, digitado por Sidarta no terminal ou com `!scripts/verificar.sh` dentro do Claude Code. O executor nunca o roda, nem em segundo plano.

**4.6. §8, relatório final.** O bloco `## RELATÓRIO FINAL` continua igual no conteúdo, mas passa a ser escrito no relatório do brief, `docs/docs/doc_<NNN>_<slug>_<data>.md`, e não na resposta da conversa. A resposta final da sessão tem três linhas: o caminho do relatório, uma linha do que foi feito e o comando que Sidarta roda. Acrescentar: "Sem saída de comando colada no relatório, não se escreve que algo passou."

**4.7. Nova seção "§10. Briefs e numeração"**, curta:
- Briefs e DOCs seguem uma única sequência numérica. O próximo número é o maior encontrado em `docs/briefs/` e `docs/docs/`, mais um.
- Todo brief escrito no Projeto é gravado em `docs/briefs/` antes de ser executado. O executor não executa brief que não esteja no disco.
- O cabeçalho do brief segue `docs/briefs/_modelo.md`: Conjunto, Arquivos-alvo, Seções a ler, Modelo, Teste de aceite.
- Havendo teste de aceite, o executor cria o teste antes do código.
- Não editar este arquivo, regra ou skill numa sessão de execução, salvo quando o brief tiver esse arquivo como alvo.

**4.8. §9, certificação.** Trocar "`docs/PLAN.md` atualizado" por "Resumo, Doing, Backlog e Done do `docs/PLAN.md` atualizados". No relatório final, a linha correspondente muda igual.

---

## 5. `docs/ARQUITETURA.md` — o que está desatualizado

O executor confere cada item no código antes de escrever e cita, no relatório, o arquivo e a linha que usou como fonte.

| Seção | Fazer |
|---|---|
| §2 Estrutura | Juntar com a §2 do AGENTS (item 4.2), conferida contra o disco |
| §8 Camada de LLM | Receber a parte descritiva da §3 do AGENTS (item 4.3) e conferir contra `config/llm_routing.yaml` |
| §9 Filtro de categorias sensíveis | Substituir pelo estado do brief 046: o programa não descarta conteúdo por tema; as regras de verdade ficam nos prompts (nunca atribuir opinião, posição ou adesão; fatos `[antigo]` e `[de imagem]`; piso `conector.consulta.minima`). Fonte: a entrada do brief 046 no PLAN e `nucleo/prompts/` |
| §10 Console web | Trocar a tabela de rotas pelas rotas reais, listadas a partir de `@app.route` em `agente_nw/console/app.py`. Tela única em `/`; telas antigas em "bastidores" |
| §11 Agendamento | Substituir por: "Não existe agendamento (brief 016). Toda execução é disparada por Sidarta pelo console ou pela CLI." Manter a parte de progresso retomável e do sentinela `dados/PARE` só se o código ainda a tiver (conferir com `grep`); se não tiver, retirar |
| Demais seções | Ler e, se houver afirmação que contradiga o AGENTS vigente ou o código, registrar no relatório como lacuna. Não reescrever além disso |

---

## 6. `docs/PLANO.md` e `docs/briefs/_modelo.md`

- **PLANO §5 (perfis de hardware):** receber o que vier da §3 do AGENTS sobre `air16`/`pro48`, se ainda não estiver lá.
- **PLANO §6 (governança):** acrescentar a numeração única e o brief gravado no disco (os mesmos itens da 4.7), o relatório de cada brief em `docs/docs/` e o histórico em `docs/historico/` consultado por busca. A lista do `.gitignore` não muda neste brief.
- **`docs/briefs/_modelo.md` (novo):** um modelo de brief com o cabeçalho fixo (Repositório, Conjunto, Arquivos-alvo, Seções a ler, Modelo, Teste de aceite, Depende de, Data) e as seções que os briefs atuais já usam: objetivo em uma frase, decisões, escopo (arquivos), testes, fora de escopo, passos, critérios de aceite. Até 60 linhas.

---

## 7. Passos de execução

> AGENTS.md: o executor não roda `git` nem a suíte. Nenhum `.py` é tocado neste brief.

1. **Cópia de segurança:** copiar `docs/PLAN.md`, `docs/PLANO.md` e `docs/ARQUITETURA.md` para `docs/historico/2026-10-25_pre_055/`. Conferir com `cmp` que as cópias são idênticas. Registrar o tamanho (`wc -c`) de cada original.
2. **PLAN:** histórico movido literalmente (3.4), depois a estrutura nova (3.1 a 3.3). Provar a mudança com a contagem de linhas: as linhas do PLAN antigo têm de aparecer no PLAN novo ou no arquivo de histórico (`diff` do trecho movido contra o intervalo original), sem nenhuma alteração de texto.
3. **ARQUITETURA:** itens da seção 5, cada um com a fonte no código.
4. **AGENTS:** itens 4.1 a 4.8.
5. **PLANO e modelo de brief:** seção 6.
6. **Conferências da seção 8**, com a saída colada no relatório.
7. **Relatório** `docs/docs/doc_055_documentos_canonicos_2026-10-25.md`: o bloco do relatório final do AGENTS, a tabela de tamanhos antes e depois e as lacunas.
8. **Mensagem de commit** em `logs/commit_055.txt`:
   `docs(agents): leitura reduzida, regras de git/gate/relatorio/numeracao; estrutura e stack para a ARQUITETURA (brief 055)`
   O commit é só do `AGENTS.md`; os outros documentos estão fora do git.

---

## 8. Critérios de aceite (todos por comando, saída colada no relatório)

1. **Leitura obrigatória ≤ 25.000 caracteres:** soma de `wc -c AGENTS.md` com o PLAN até o fim de `## Dívidas conhecidas`. Hoje são 100.796.
2. **Nenhuma linha de histórico perdida:** a prova do passo 2.
3. **Nada desatualizado descrito como atual:** `grep -n -i -E "launchd|LaunchAgent|StartCalendarInterval|sensivel\.py|ciclo diário|05h00"` em `AGENTS.md`, `docs/ARQUITETURA.md`, `docs/PLANO.md` e no PLAN novo. Cada ocorrência que restar está explicitamente no passado ("removido no brief 016").
4. **Regras preservadas:** cada uma das frases abaixo continua no `AGENTS.md` (`grep -c` ≥ 1 para cada):
   - `git add -A`
   - `Git nunca roda de forma autônoma`
   - `Ollama.app`
   - `11435`
   - `think: false`
   - `127.0.0.1`
   - `copiar-banco`
   - `banco real só é tocado`
   - `Nunca rodam sozinhos`
   - `Mudança cirúrgica`
   - `isso funcionava antes`
   - `migração numerada`
   - `Restrições são estruturais`
   - `Quem decide que tema cabe`
5. **Sem `CLAUDE.md` nem `CLAUDE.local.md`** no repositório (`ls`).
6. **Cópias de segurança** existem e são idênticas aos originais (`cmp`, passo 1).
7. **`git status --short`** mostra só `AGENTS.md` modificado e nenhum outro arquivo rastreado alterado. Os documentos em `docs/` não aparecem, porque estão fora do git.

---

## 9. Fora de escopo (cada item é de outro brief, que acrescenta a sua própria linha ao AGENTS quando a ferramenta existir)

- `.gitignore` (tirar `.claude/`), `.claude/settings.json`, hooks, lint e teste por arquivo.
- Scripts novos (`agente_fechar.sh`, `agente_entregar.sh`, número automático, resumo gerado), skills `/iniciar` e `/encerrar`.
- Worktree persistente `../agente_nw-dev`, troca de pip por `uv`, trava do banco no código.
- Qualquer `.py`, qualquer prompt, qualquer limiar.
- Renumerar os documentos já entregues com número repetido (051 e 052). Eles ficam como estão; a sequência única vale daqui em diante.
