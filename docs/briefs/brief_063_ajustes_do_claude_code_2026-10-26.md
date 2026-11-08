# Brief 063 — Ajustes do próprio Claude Code: memória limpa, respostas curtas, opções futuras registradas

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Conjunto:** nenhum (brief isolado, direto na `main`)
**Arquivos-alvo:** `.claude/settings.json`, `docs/briefs/_modelo.md`, a memória automática do Claude Code para este repositório (pasta do usuário, fora do git), `docs/docs/doc_063_ajustes_do_claude_code_2026-10-26.md`, `logs/commit_063.txt`, `logs/arquivos_063.txt`
**Seções a ler:** AGENTS inteiro (é a referência contra a qual a memória é conferida); as páginas da documentação oficial citadas em cada item
**Modelo:** Sonnet
**Teste de aceite:** as conferências da seção 4
**Depende de:** brief 062 (a tabela de lacunas deste relatório entra no PLAN sozinha)
**Data:** 2026-10-26

---

## 1. Objetivo em uma frase

Aplicar as opções do Claude Code que Sidarta aprovou em 26/10:
- tirar da memória automática as regras antigas que contradizem o AGENTS;
- deixar as respostas curtas por configuração;
- registrar no PLAN as opções que só vão servir mais tarde.

---

## 2. Decisões de Sidarta (26/10)

Aprovadas as sugestões da sessão do Projeto: aplicar agora a limpeza da memória automática, o estilo de saída Concise, o `/rewind` (só uso), o acompanhamento pelo celular e a retomada automática depois do limite de uso. Usar o `/effort` com cuidado. Deixar para depois o `.worktreeinclude`, o `/goal`, o `/code-review` por fase e as regras por caminho. Não aplicar: pyright, visão de agentes, mensagens entre sessões, mods, modo restrito, workflows, tarefas agendadas e modo auto.

---

## 3. O que fazer

**3.1. Memória automática (o item mais importante).** Antes de mexer, ler a página [How Claude remembers your project](https://code.claude.com/docs/en/memory), parte de memória automática, e achar onde ficam os arquivos de memória deste repositório (pasta do usuário, fora do git). Depois, para cada anotação:
- **apagar** a que contradiz o AGENTS vigente. Exemplos prováveis: "o executor nunca roda git", "nunca rodar pytest", "Sidarta faz o commit", caminhos ou passos de antes do brief 055;
- **apagar** a que repete o AGENTS ou o PLAN sem acrescentar nada;
- **manter** a que é aprendizado útil e não está em lugar nenhum. Listar cada uma no relatório, para Sidarta saber o que ficou.

Antes de apagar, copiar o arquivo original para `logs/memoria_antes_063.md`. No relatório, uma tabela: anotação, decisão (apagar / manter), motivo em uma frase.

**3.2. Respostas curtas por configuração.** Ler a página de estilos de saída (Output styles) e pôr o estilo **Concise** como padrão deste repositório em `.claude/settings.json`, com a chave que a documentação indicar. A regra das três linhas do AGENTS §8 continua; o estilo só reforça.

**3.3. Esforço no cabeçalho do brief.** Em `docs/briefs/_modelo.md`, acrescentar ao cabeçalho o campo `**Esforço:** baixo / médio / alto` ao lado de `**Modelo:**`. A regra:
- **baixo** para brief mecânico;
- **médio** como padrão;
- **alto** para brief de Opus ou com risco de mudar comportamento.

Sidarta ajusta com `/effort` ao abrir a sessão. Não mudar o esforço padrão global.

**3.4. Como usar, para Sidarta (sem configurar nada).** Ler as páginas e escrever no relatório, em até 5 linhas cada e em linguagem simples, como fazer:
1. **acompanhar e iniciar pelo celular** ([Remote Control](https://code.claude.com/docs/en/remote-control) / [Claude Code on mobile](https://code.claude.com/docs/en/mobile)): como mandar `/executar NNN` do celular para a sessão no Mac;
2. **retomada automática depois do limite de uso**: o que precisa para ela acontecer (app desktop) e como ligar, se houver ajuste;
3. **`/rewind`** ([Checkpointing](https://code.claude.com/docs/en/checkpointing)): quando usar, em uma linha.

Se uma página não confirmar o recurso como descrito, dizer isso no relatório. Não inventar o passo.

**3.5. Opções para depois → Backlog, pela tabela de lacunas (brief 062).** Uma linha cada, destino `backlog`:
- `.worktreeinclude`, quando houver worktree. Não serve para o banco, que vem do `copiar-banco`, nem resolve o ambiente Python editável.
- `/goal` no lugar do "até 3 tentativas" da skill `/executar`.
- `/code-review` local ao fim de cada fase do produto, comparado com a auditoria de 12 passes.
- Regras por caminho (`.claude/rules/` com `paths`) para as regras de migração, prompts e extensão hoje no AGENTS.

---

## 4. Critérios de aceite

1. `logs/memoria_antes_063.md` existe, e o relatório traz a tabela de cada anotação com a decisão.
2. Nenhuma anotação que sobrou na memória contradiz o AGENTS. Para conferir, buscar na memória `git`, `pytest`, `commit` e `Sidarta roda`, e colar o resultado.
3. `.claude/settings.json` tem o estilo Concise, com a chave que a documentação indica (citar a página).
4. `_modelo.md` tem o campo Esforço.
5. As quatro opções futuras entraram no Backlog do PLAN pela entrega, e não à mão.
6. Commit e push pelo executor. Resposta final: "Nada para você.", ou o que a seção 3.4 não conseguiu confirmar.

---

## 5. Fora de escopo

Instalar plugin, ligar modo auto, criar tarefa agendada, mexer na memória de outros repositórios.
