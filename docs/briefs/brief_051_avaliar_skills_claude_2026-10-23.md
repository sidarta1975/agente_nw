# Avaliar skills e plugins do Claude para o agente_nw

**Tipo:** audit
**Trilha:** exploratória — nenhum arquivo de código é tocado; a saída é um DOC. Sem gate: não há `.py` alterado.
**Duração máxima:** 1 h na sessão no Claude App + 3 h na sessão no Claude Code. Estourou, para e entrega o DOC parcial com `## Lacunas` preenchida.
**Pré-requisitos:** nenhum. Não instalar nada antes do passo 10.

## Objetivo

Decidir, com evidência e não por opinião, quais skills e plugins do ecossistema Claude Code entram neste repositório. A sessão que escreveu este brief leu os `SKILL.md` de sete repositórios de skills e propõe as hipóteses abaixo para **agente_nw (agente de relacionamento)**; a tarefa confirma ou derruba cada uma contra o repositório real e o AGENTS.md vigente, procura o que ficou de fora, e sai com veredito por item e até 5 briefs fixos. O resultado muda o que a sessão no Claude Code carrega em toda tarefa deste projeto — por isso custo de contexto é critério, não detalhe.

Estado lido em 22/10/2026: 241 arquivos `.py`, 125 de teste, `AGENTS.md` com 138 linhas (já curto), gate por `scripts/verificar.sh` sempre pelo usuário, frente E1 (ciclo diário via launchd) e briefs sem prefixo, Flask + `httpx` + `pydantic`, busca de notícias e geração de conteúdo para WhatsApp. Não existe `docs/docs/`: criar na primeira entrega. Dado real: perfis de pessoas — nenhuma skill lê os dados, só código.

## Arquivos-alvo

- `docs/docs/doc_051_avaliar_skills_claude_<data>.md` (o DOC, saída única)
- `.claude/skills/_avaliacao/` (instalação temporária; removida no passo 14 — o diretório não pode existir ao final)

Fora disso, nada: nenhum `.py`, nenhum `pyproject.toml`, nenhum `.claude/settings*.json`, nenhum `AGENTS.md`/`CLAUDE.md`. Alteração nesses arquivos é violação de escopo, mesmo que a skill testada a proponha.

## Hipóteses a verificar

| Skill / plugin | Origem | Tipo | Para quê neste projeto | Alvo de teste (somente leitura) |
|---|---|---|---|---|
| grilling / grill-me (App) | mattpocock/skills | skill manual | O produto ainda está sendo desenhado (briefs 048–050 são de juízo de produto): entrevista antes do próximo brief de escopo | — |
| secret-serialization | getsentry/skills | skill | Chaves de API de busca e de envio vazando por `repr`/log; perfis pessoais em log | Módulos de integração externa |
| firecrawl / agent-browser | firecrawl/skills / vercel-labs/agent-browser | skills de fornecedor | Busca e leitura de notícias com extração estruturada — comparar com o que o código faz hoje | Módulo de busca de notícias (só leitura) |
| property-based-testing | trailofbits/skills | skill (Hypothesis) | Normalização de nomes e datas de perfis | Módulo de perfis (propor casos, não gravar) |
| to-questionnaire (App) | mattpocock/skills | skill manual | Decisões de produto que dependem de terceiros viram questionário | — |
| claude-code-setup | anthropics/claude-plugins-official | plugin (skill sob demanda) | Analisa o repositório e recomenda hooks, skills, MCP e subagentes; serve de contraprova a esta tabela | Raiz do repositório; comparar a saída com esta tabela no DOC |
| claude-settings-audit | getsentry/skills | skill | Gera a lista de comandos somente-leitura para `permissions.allow`, acabando com prompts repetidos | Raiz; registrar a lista proposta no DOC, não aplicar |
| supply-chain-risk-auditor | trailofbits/skills | skill | Audita `uv.lock` inteiro contra advisories e pacotes abandonados | `uv.lock` |
| hookify / git-guardrails-claude-code | anthropics/claude-plugins-official / mattpocock/skills | plugin com hooks / skill que gera hooks | Transformar em hook `PreToolUse` as regras de texto do AGENTS.md sobre git e gate na sessão | Só leitura do que gerariam; não gravar hook |

Sessão: "App" = avaliada pela sessão no Claude App (skills de planejamento, sem instalação); as demais pela sessão no Claude Code.

## Fontes e critérios para candidatas novas

Fontes a cobrir, nesta ordem (todas lidas em 22/10/2026 pela sessão que escreveu este brief):
1. Marketplace oficial — `github.com/anthropics/claude-plugins-official` (`plugins/` e `external_plugins/`; no Claude Code, `/plugin` → Discover).
2. `github.com/anthropics/skills` (skills de documento, `webapp-testing`, `mcp-builder`, `skill-creator`).
3. Repositórios de fornecedor no formato Agent Skills: `trailofbits/skills`, `getsentry/skills`, `huggingface/skills`, `docker/skills`, `firecrawl/skills`, `microsoft/playwright-cli`, `tursodatabase/agent-skills`.
4. Repositórios de autor: `mattpocock/skills`, `obra/superpowers`.
5. Índices: `skills.sh`, `vibeindex.ai`, `claudemarketplaces.com` — só para descobrir nomes; a avaliação é sempre sobre o `SKILL.md` lido no repositório de origem.
Critérios de corte para candidata nova: (a) Python ou agnóstica de linguagem; (b) não exige ferramenta que o projeto não usa (ty, pnpm, Poetry, Django); (c) não contraria o AGENTS.md vigente (gate fora da sessão, git do usuário, dado real sob ordem explícita); (d) repositório com commit nos últimos 90 dias; (e) licença permissiva. Candidata que falha em (c) é descartada sem teste.

## Aceite

Existe um DOC em `docs/docs/doc_051_avaliar_skills_claude_<data>.md` com: tabela de hipóteses completa (toda linha com veredito `adotar`, `testar em 1 brief` ou `descartar` e uma evidência verificável — trecho do `SKILL.md`, regra do AGENTS.md citada, ou saída do teste seco); seção `## Candidatas novas` com até 10 itens vindos das fontes listadas, cada um com origem e tipo; `## Lacunas`; `## Próximos briefs` com até 5 itens. `git status --short` do repositório não mostra nada em `.claude/`, nenhum `.py`, nenhum `pyproject.toml`, nenhum `settings.json` alterado, e `~/skills_eval/` é o único lugar onde os repositórios de skills foram clonados. Nenhuma skill ou plugin permanece instalado ao final — a adoção é decisão do usuário sobre o DOC, não desta tarefa.

## Passos — sessão no Claude App (pesquisa; nada é instalado)

1. Ler este brief inteiro e o `AGENTS.md` do repositório (as regras de gate, git e dado real são o critério (c) acima).
2. Percorrer as cinco fontes da lista. Para cada skill ou plugin com nome que sugira encaixe, abrir o `SKILL.md` ou `plugin.json` no repositório de origem e ler a descrição e o procedimento — não a página do índice.
3. Montar a seção `## Candidatas novas` do DOC: no máximo 10 linhas, cada uma com nome, origem (`owner/repo`), tipo (skill, plugin com hooks, servidor MCP), para que serviria neste projeto em uma frase, critério de corte que a eliminaria se houver.
4. Para cada hipótese da tabela acima que seja de uso na sessão no App (marcada "App"), avaliar pelo mesmo critério e registrar o veredito na tabela, com a evidência: trecho do `SKILL.md` ou regra do AGENTS.md que conflita.
5. Entregar o DOC parcial na aba Saídas e passar o caminho para a sessão no Claude Code.

## Passos — sessão no Claude Code (viabilidade; instalação só temporária)

6. Ler `AGENTS.md` e o CONTEXT (seção em execução). Criar `docs/docs/` se não existir — é o único diretório novo permitido.
7. Criar `~/skills_eval/` fora do repositório e clonar ali, raso (`git clone --depth 1`), cada repositório de origem citado na tabela e nas candidatas novas. Nada é clonado dentro do repositório.
8. Para cada skill (hipótese ou candidata): ler o `SKILL.md` inteiro e anotar quatro coisas no DOC — (a) tamanho em caracteres (custo de contexto quando carregada); (b) se é skill sob demanda, hook ou servidor MCP (hook e MCP custam contexto em toda sessão); (c) ferramentas que ela pressupõe e se existem aqui (`uv`, `ruff`, `mypy`, `pytest`, Playwright, etc.); (d) a frase do AGENTS.md que ela contraria, se houver.
9. Skill que contraria o AGENTS.md ou pressupõe ferramenta ausente: veredito `descartar`, sem teste. Registrar o motivo em uma linha.
10. Para as demais, teste seco: copiar a pasta da skill para `.claude/skills/_avaliacao/<nome>/`, iniciar nova sessão (`/reload-skills` basta se a sessão já estiver aberta) e invocar `/<nome>` sobre o alvo real indicado na coluna "alvo de teste" da tabela. A skill roda em modo leitura: qualquer proposta de edição em arquivo de código é anotada no DOC e recusada. Plugin oficial é testado com `/plugin install <nome>@claude-plugins-official` e desinstalado no passo 14.
11. Registrar por teste: o que a skill produziu (3 linhas), se o resultado era obtível sem ela, e o consumo informado por `/cost` antes e depois da invocação.
12. Servidor MCP (`context7`, `serena`, `telegram`, `playwright`): não instalar nesta tarefa. Registrar apenas o número de ferramentas que expõe (lido no README) e se o `settings` permite `alwaysLoad: false`; a decisão de instalar é brief próprio.
13. Veredito por item, um de três: `adotar` (entra no AGENTS/CLAUDE deste repo como skill nomeada), `testar em 1 brief` (vale um brief fixo de uso real), `descartar`. Cada veredito com uma evidência dos passos 8–11.
14. Remover `.claude/skills/_avaliacao/` e desinstalar qualquer plugin instalado no passo 10. `git status --short` não pode mostrar nada em `.claude/` nem em código.
15. Escrever `## Lacunas` (tabela Lacuna | Impacto bloqueia/degrada/nice | Esforço) com o que foi visto e não feito, e `## Próximos briefs`: até 5 briefs fixos, um por skill `adotar` ou `testar`, cada um em uma linha com objetivo e arquivos-alvo prováveis.
16. Fechar conforme o `AGENTS.md` vigente (`scripts/verificar.sh` é do usuário e não precisa rodar: nenhum `.py` tocado). O DOC é a entrega.

## Fora de escopo

Instalar qualquer coisa em definitivo; editar AGENTS.md/CLAUDE.md para citar skills (é o brief seguinte); configurar servidor MCP; migrar este repositório para a metodologia do piloto do pandora_96.

## Recomendação de execução

Modelo: Sonnet na sessão no Claude Code — leitura de `SKILL.md`, clone, teste seco e `/cost` são mecânicos e o aceite é verificável por comando. Opus na sessão no Claude App — a pesquisa e o julgamento de encaixe são onde o erro custa caro.
