# Vale a pena uma skill do Claude Code no agente_nw? — relatório para o Projeto que analisa as skills de todos os repositórios

**Data:** 2026-10-25 · **Origem:** sessão do Projeto agente_nw, com leitura direta do repositório (`/Users/sidarta48/github/agente_nw`) em 23, 24 e 25/10 · **Tipo:** relatório, nada aplicado.
**Escopo:** só o agente_nw. A pergunta chegou mencionando o lex_hub. Esta sessão não tem acesso a ele, e a resposta sobre o lex_hub precisa sair da sessão do próprio lex_hub.
**Base:** avaliação de skills de terceiros (doc 051), proposta de skill do repositório (doc 053), avaliação item a item da proposta comum de simplificação (resposta de 25/10) e as medições abaixo.

---

## 1. Resposta curta

**Sim, vale, com uma ressalva que importa para os sete repositórios: quase todo o ganho vem de mecanismos que não são a skill.**

| De onde vem o ganho | Precisa de skill? | Peso no agente_nw |
|---|---|---|
| Ler menos antes de cada brief (resumo gerado em vez de PLAN.md inteiro; só as seções citadas) | Não: é uma regra do AGENTS mais um script | ~20 mil tokens por brief, a maior parte do ganho |
| Comandos digitados por você com `!` (gate, fechar, entregar), sem copiar e colar | Não: são scripts | Elimina todo o copia-e-cola; zero token |
| Regras como trava automática (git, suíte, banco real, rede social) | Não: são hooks | Zero token; garante a regra |
| Relatório mecânico e manifesto de commit gerados por script | Não: são scripts | ~1 a 2 mil tokens de saída por brief |
| **A skill em si** (`/iniciar`, `/encerrar`) | É a skill | Junta os scripts num roteiro igual toda vez e começa a tarefa sem rodada extra: ~1 a 3 mil tokens por brief, mais consistência |

Conclusão para o agente_nw: **fazer a skill, mas como uma casca fina** (até 40 linhas cada) sobre scripts e hooks. Se só desse para fazer uma coisa, a escolha seria a **regra de leitura reduzida mais os hooks**. A skill sozinha, sem eles, economiza pouco.

---

## 2. Os números do agente_nw

### 2.1 Ficha do repositório (para comparar com os outros seis)

| Medida | Valor em 25/10 |
|---|---|
| Arquivos `.py` / arquivos de teste | 241 / 125 |
| `AGENTS.md` | 13.627 caracteres, 138 linhas; as seções de estrutura e de stack são 43% dele |
| Arquivo de estado (`docs/PLAN.md`) | 57.951 caracteres, 178 linhas, entradas narrativas por data; não há formato de uma linha por tarefa |
| Leitura obrigatória antes de cada brief | 100.796 caracteres (~25 a 29 mil tokens): AGENTS + PLANO + ARQUITETURA + PLAN |
| `CLAUDE.md` | não existe |
| `.claude/` | vazio, e ignorado pelo git (`.gitignore`, linha 24) |
| Scripts | `verificar.sh` (gate completo), `commitar.sh` (add arquivo por arquivo + commit, sem push), `instalar_macos.sh` |
| Ambiente Python | `.venv` editável apontando para a pasta principal |
| Fora do git | `docs/*` inteiro (briefs, PLAN, DOCs), `dados/`, `config/local.yaml`, `temas.yaml`, `fontes.yaml`, `saidas/`, `logs/` |
| Dado real | `dados/agente.db` (perfis de pessoas); qualquer comando do programa rodado na pasta principal usa esse banco |
| Testes com nome do módulo (`test_<módulo>.py`) | 35 de 96 módulos (36%) |
| Cadência | cerca de 8 a 10 briefs ou DOCs por semana, em rajadas (semanas 38 e 42 com ~30 commits; 39 e 41 com 4 a 8) |
| Numeração | 051 e 052 usados duas vezes cada; dois briefs do Projeto não existem no disco |
| Trabalho pendente | 16 arquivos sem commit; o último commit é do brief 047 |

### 2.2 Ganho estimado

Base: caracteres medidos divididos por 4, mais cerca de 9 briefs por semana. Não é medição de sessão; a confirmação vem do `docs/custos.csv` nas primeiras tarefas.

| Item | Por brief | Por semana (~9 briefs) |
|---|---|---|
| Leitura reduzida | −20 mil tokens de entrada | −180 mil |
| Relatório mecânico | −1 a 2 mil de saída | −9 a 18 mil de saída |
| Gate que falha lido por resumo | −2 a 5 mil, quando falha | variável |
| Skill (sem rodada extra para começar) | −1 a 3 mil | −9 a 27 mil |
| Copia-e-cola do terminal | 2 a 3 operações a menos | 20 a 30 operações a menos |
| Custo de construir | 3 briefs, entregues como um conjunto só | uma vez |

---

## 3. O que é comum e o que é do agente_nw

**Comum aos sete:**
- O texto da skill: o roteiro de início e de encerramento.
- Os nomes dos scripts e dos comandos.
- A guarda de git e de suíte.
- A regra de três linhas na resposta final.

**Específico do agente_nw:** fica nos scripts e na configuração, nunca no texto da skill.
- **Banco real por pasta, não por comando.** Na pasta principal, o programa usa o banco real; na worktree, a cópia. A guarda precisa olhar em que pasta o comando roda.
- **Comandos que leem rede social nunca rodam sozinhos** (`ler-rede-social`, `listas`, `pedir`, `extensao`), e a ficha de contato nunca é alterada sem você. Isso vira bloqueio no hook, não confirmação.
- **`docs/` fora do git.** A worktree precisa de um link para a pasta `docs/` principal, ou a sessão não acha o brief.
- **Duas máquinas.** O desenvolvimento roda no Pro, que usa o Ollama compartilhado do cervello, e essa instância nunca pode ser parada nem reiniciada por este projeto. A produção roda no Air, com o seu próprio Ollama. A skill e os hooks têm de chegar às duas pelo git, e por isso o `.claude/` tem de sair do `.gitignore`.
- **Aceite real** com o modelo, a rede e uma pessoa real continua sendo seu, no Pro. O teste de aceite escrito no brief cobre só a parte mecânica.

**Recomendação para os sete:** **uma fonte comum** do texto da skill (`~/github/_comum`), **copiada e versionada em cada repositório**. Uma skill instalada só no usuário (`~/.claude/skills`) não chegaria à outra máquina nem ficaria registrada no histórico do repositório. Atualizar a fonte comum e recopiar é um passo de uma linha, feito numa sessão própria: mudar skill no meio de uma execução invalida o cache.

---

## 4. Skills de terceiros: estado atual para o agente_nw

Revisão do doc 051, com as decisões tomadas depois.

| Skill | Veredito agora | Motivo |
|---|---|---|
| `grilling`, `to-questionnaire` (mattpocock) | **Já disponíveis**, nada a instalar | A conta já oferece o `grilling` nas sessões do Projeto; servem à sessão de planejamento |
| `claude-settings-audit` (getsentry) | **Usar uma vez** para gerar a lista de leitura liberada do `settings.json` | Só propõe leitura; você aprova item a item |
| `skill-scanner` (getsentry) | **Usar antes de copiar** qualquer `SKILL.md` de terceiro | Barato, só leitura |
| `secret-serialization` (getsentry) | Testar em 1 brief | Nenhum vazamento ativo encontrado; é preventivo |
| `property-based-testing` (trailofbits) | Testar em 1 brief | `perfil/normalizacao.py` e `coleta/rss/canonicalizar.py` |
| `git-guardrails` (mattpocock) | **Substituída** por guarda escrita à mão | A lista de bloqueio daqui é maior: commit, `add -A`, suíte, banco, rede social |
| `hookify` (oficial) | **Não usar** | Quatro hooks sempre ligados, ~176 KB, para o que um script de 30 linhas faz |
| `claude-code-setup` (oficial) | Só como contraprova | As sugestões padrão dela (lint e teste automáticos, liberar `git commit`) contrariam o AGENTS |
| `firecrawl`, `agent-browser` | **Não usar** | Exigem Node e serviço pago; contrariam as decisões de busca sem chave e de não usar navegador automatizado |
| `supply-chain-risk-auditor` | Depois de existir `uv.lock` | Sem lockfile não há árvore de dependências para auditar |

---

## 5. Condições antes de construir

1. **Os três testes técnicos** rodados uma vez no pandora valem para os sete:
   - um comando digitado com `!` passa pela guarda?
   - o argumento é substituído antes do comando embutido na skill?
   - o hook de mensagem barra mesmo a palavra combinada?
   Se um falhar, a skill muda de forma; por isso ela vem depois.
2. **Commitar os 16 arquivos pendentes** antes da primeira worktree.
3. **Decisões únicas** já tomadas, principalmente lint por hook e quem commita no ramo do conjunto.
4. **Numeração única** entre o disco e o Projeto antes do primeiro brief novo.

---

## 6. Próximos passos no agente_nw

Os três passos formam um conjunto só, entregue de uma vez:

1. **Travas e entrega:**
   - `.claude/settings.json` com os hooks;
   - `.claude/` fora do `.gitignore`;
   - `verificar.sh` gravando o resumo em `logs/`;
   - `commitar.sh` lendo o manifesto;
   - os comandos `agente_fechar.sh` e `agente_entregar.sh`, digitados por você com `!`.
2. **Skills e leitura reduzida:**
   - `/iniciar` e `/encerrar`;
   - resumo gerado no `PLAN.md`;
   - cabeçalho fixo de brief;
   - script de numeração;
   - `CLAUDE.md` de uma linha;
   - mudanças no AGENTS: ordem de leitura, regra de commit, lint, relatório final no DOC.
3. **Worktree por conjunto:** ambiente Python próprio, cópia do `local.yaml`, `copiar-banco`, link para `docs/`, cópia de `temas.yaml` e `fontes.yaml`.

---

## 7. Lacunas

| Lacuna | Impacto | Esforço |
|---|---|---|
| O tempo da suíte não foi medido: rodá-la é seu (AGENTS §6). Ele define se o gate rápido cabe em um minuto | degrada | baixo: medir na primeira entrega |
| Os ganhos são estimativa por tamanho de arquivo, não medição de sessão | degrada | baixo: `docs/custos.csv` desde a primeira tarefa |
| A cadência de briefs mistura briefs executados e documentos de avaliação | nice | — |
| O lex_hub, citado na pergunta, não foi avaliado nesta sessão | — | sessão do lex_hub |
