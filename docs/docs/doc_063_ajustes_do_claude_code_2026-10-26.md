# Doc 063 — Ajustes do próprio Claude Code: memória limpa, respostas curtas, opções futuras registradas

Brief: `docs/briefs/brief_063_ajustes_do_claude_code_2026-10-26.md`. Executado em 2026-10-30.

## 1. Memória automática (3.1)

Backup do conteúdo original (os três arquivos de `~/.claude/projects/-Users-sidarta48-github-agente-nw/memory/`, antes de qualquer edição): `logs/memoria_antes_063.md`.

Página lida: [How Claude remembers your project](https://code.claude.com/docs/en/memory) — seção "Auto memory". Confirma que a memória automática deste repositório fica em `~/.claude/projects/<project>/memory/` (um `MEMORY.md` índice + um arquivo por anotação), que é exatamente a pasta usada aqui.

Tabela de cada anotação encontrada e a decisão:

| Anotação (resumo) | Decisão | Motivo |
|---|---|---|
| Fluxo de briefs numerados; condição "Depende de" verificada literalmente antes de codar | Manter | Não contradiz o AGENTS vigente; reforça a skill `/executar` |
| "Executor NUNCA roda `scripts/verificar.sh`/`pytest`/`ruff`/`mypy`; quem roda é Sidarta" + elaboração de escopo + "reimplementar teste manualmente é o mesmo gasto disfarçado" | Apagar | Contradiz o AGENTS §6 vigente: o executor roda a suíte dentro de `scripts/agente_entregar.sh` desde o brief 058 |
| Comando de `git` sempre em arquivo `.sh` em `/tmp` para Sidarta colar; "git nunca roda de forma autônoma" | Apagar | Contradiz o AGENTS §5 vigente: o executor commita e dá push pelo `scripts/agente_entregar.sh` desde o brief 057/058 |
| Ancorar regra de diretório no `.gitignore` com `/` na frente (bug achado no fechamento do brief 002) | Manter | Lição técnica específica, ainda útil, não registrada no PLAN (armadilhas) |
| Parar e perguntar antes de ajustar config/limiar exposto por um comando real fora do escopo literal do brief | Manter | Prática ainda válida, evita decisão silenciosa fora de escopo |
| Seguir mudança de desenho pedida pelo usuário no meio do brief por inteiro, sem vestígio do desenho antigo | Manter | Prática ainda válida e específica deste usuário |
| Não fabricar dado real para satisfazer critério de aceite quando a base é só dado de desenvolvimento; perguntar antes | Manter | Prática ainda válida, evita simulação silenciosa |
| "Relatório"/"resumo" pedido em texto livre = resposta em texto na conversa, nunca Artifact/arquivo não pedido | Manter | Ainda vale; complementar (não conflita) com o relatório formal em arquivo do AGENTS §8 |
| Ações de nível de sistema operacional (LaunchAgents/`launchctl load`) pedem confirmação explícita mesmo com autorização literal no brief | Apagar | A situação concreta (ciclo diário via launchd) não existe mais — AGENTS §6: "Agendamento: não existe" |
| "How to apply" (síntese numerada 1–7, citando "nunca rodar pytest/git") | Apagar | Repetia as regras já removidas acima; reescrita (ver `feedback_fluxo_briefs.md` atual) para apontar ao AGENTS/skill vigentes em vez de duplicá-los |
| `project_produto_e_estado.md` inteiro: "o sistema... não escreve mensagem, não pontua relacionamento, não envia nada" + "estado corrente sempre em docs/PLAN.md" | Apagar (arquivo inteiro) | A descrição central contradiz o AGENTS §7 vigente (o sistema redige mensagem base e ganchos desde os briefs 038/047); o resto repete o AGENTS §1 sem acrescentar nada |

O que ficou, reescrito em `feedback_fluxo_briefs.md` (mesmo arquivo, conteúdo trimado): verificação literal de dependência; ancorar `/` em regra de `.gitignore`; parar e perguntar antes de ajuste fora de escopo; seguir mudança de desenho pedida pelo usuário; não fabricar dado real; "relatório" em texto livre pede resposta em texto; e um "How to apply" novo que aponta para o AGENTS/skill vigentes em vez de repetir regra antiga. `project_produto_e_estado.md` foi removido por inteiro; `MEMORY.md` foi atualizado para não apontar mais para ele.

### Critério de aceite 2 — busca por `git`, `pytest`, `commit`, `Sidarta roda`

```
$ cd ~/.claude/projects/-Users-sidarta48-github-agente-nw/memory && grep -rn -i "git" *.md
MEMORY.md:1:- [Fluxo de briefs](feedback_fluxo_briefs.md) — gate de dependência literal, pausa antes de decisão fora de escopo, relatório em texto na conversa; git/testes seguem o AGENTS vigente (revisado no brief 063)
feedback_fluxo_briefs.md:3:description: "... git/testes seguem o AGENTS vigente (revisado no brief 063: removidas as regras antigas de 'executor nunca roda git/pytest', incompatíveis desde o brief 058)"
feedback_fluxo_briefs.md:15:**Ao editar `.gitignore`, ancorar toda regra de diretório com `/` na frente.** [...] git só avisa quando o arquivo é passado explicitamente pro `add` [...]
feedback_fluxo_briefs.md:25:**How to apply:** [...] Fluxo de git, testes e entrega: seguir o `AGENTS.md` vigente (§5, §6, §8) [...] **não** as regras antigas de "executor nunca roda git/pytest, quem roda é Sidarta", que valiam antes do brief 058 e foram removidas desta memória no brief 063 [...]

$ grep -rn -i "pytest" *.md
feedback_fluxo_briefs.md:3:description: "... (revisado no brief 063: removidas as regras antigas de 'executor nunca roda git/pytest' ...)"
feedback_fluxo_briefs.md:25:**How to apply:** [...] — **não** as regras antigas de "executor nunca roda git/pytest, quem roda é Sidarta" [...]

$ grep -rn -i "commit" *.md
(nenhum resultado)

$ grep -rn -i "Sidarta roda" *.md
(nenhum resultado)
```

Nenhuma ocorrência restante afirma que o executor não roda git/pytest/suíte ou que Sidarta é quem commita — as únicas menções a "git"/"pytest" são a nota explícita de que a regra antiga foi removida e a lição (ainda válida) sobre ancorar `.gitignore`.

## 2. Respostas curtas por configuração (3.2)

Página lida: [Output styles](https://code.claude.com/docs/en/output-styles) — seção "Change your output style". A chave é `outputStyle`, em `.claude/settings.json` (nível de projeto), com o valor exato `"Concise"` (sensível a maiúscula/minúscula; o nome tem que ser escrito assim, nunca `"concise"`). Aplicado:

```json
{
  "outputStyle": "Concise"
}
```

A regra das três linhas do AGENTS §8 continua sendo a entrega formal de todo brief; o estilo Concise só reforça respostas mais curtas no dia a dia da sessão.

## 3. Esforço no cabeçalho do brief (3.3)

`docs/briefs/_modelo.md` ganhou a linha `**Esforço:** baixo | médio | alto`, entre `**Modelo:**` e `**Teste de aceite:**`. Nenhum esforço padrão global foi alterado — Sidarta ajusta com `/effort` ao abrir a sessão, brief a brief.

## 4. Como usar, para Sidarta (3.4)

**1. Acompanhar e iniciar pelo celular.** Páginas lidas: [Remote Control](https://code.claude.com/docs/en/remote-control) e [Claude Code on mobile](https://code.claude.com/docs/en/mobile). No Mac, dentro de uma sessão aberta, rode `/remote-control` (ou `claude remote-control` no terminal) — aparece um link/QR. No celular, abra o app Claude, aba **Code**, e toque na sessão (ícone de computador com ponto verde). De lá, mandar `/executar 63` funciona como uma mensagem normal — ela chega à sessão do Mac e roda lá.
**Ressalva:** a documentação não confirma "iniciar pelo celular" no sentido de criar do zero uma sessão local no Mac a partir do telefone — é preciso primeiro rodar `/remote-control` (ou ligar "Enable Remote Control for all sessions" em `/config`) no próprio Mac; o celular então conecta/retoma essa sessão, não a cria sem o Mac.

**2. Retomada automática depois do limite de uso.** Página lida: [Interactive mode](https://code.claude.com/docs/en/interactive-mode), seção "Wait for a usage limit to reset". Quando o limite de uso para a sessão no meio de uma tarefa, o Claude Code já espera e continua sozinho quando o limite reseta — isso vem **ligado por padrão** em sessão interativa com login claude.ai (Claude Code 2.1.234+), sem precisar configurar nada. Para desligar: `/config` → "Continue automatically at usage limit", ou a chave `autoContinueAtUsageLimit`.
**Ressalva:** a página não confirma a premissa do brief de que isso "precisa do app desktop" — funciona também no terminal comum, desde que o Mac continue ligado e a sessão aberta; só não inicia a espera sozinha em sessão de Remote Control ou de colega de equipe (lá é preciso rodar `/rate-limit-options` manualmente).

**3. `/rewind`.** Página lida: [Checkpointing](https://code.claude.com/docs/en/checkpointing). Usar quando uma mudança (de código ou de rumo da conversa) saiu errada e vale voltar a um ponto anterior — `/rewind` (ou duplo `Esc` com o campo vazio) abre o menu de prompts anteriores para restaurar código, conversa, ou os dois.

## 5. Opções para depois (3.5)

As quatro opções abaixo foram levadas ao Backlog do `docs/PLAN.md` pela tabela de lacunas deste relatório (seção `## Lacunas`), via `scripts/agente_lacunas.py` dentro do `scripts/agente_entregar.sh` — não copiadas à mão.

## RELATÓRIO FINAL
- Brief executado: 063 — ajustes do próprio Claude Code (memória limpa, estilo Concise, campo Esforço, opções futuras no Backlog)
- Arquivos criados: `docs/docs/doc_063_ajustes_do_claude_code_2026-10-26.md`, `logs/commit_063.txt`, `logs/arquivos_063.txt`, `logs/memoria_antes_063.md`
- Arquivos alterados:
  - `.claude/settings.json` — acrescentada a chave `"outputStyle": "Concise"`
  - `docs/briefs/_modelo.md` — acrescentado o campo `**Esforço:**` no cabeçalho, ao lado de `**Modelo:**`
  - `~/.claude/projects/-Users-sidarta48-github-agente-nw/memory/feedback_fluxo_briefs.md` — removidas as anotações que contradiziam o AGENTS vigente (git/pytest nunca rodados pelo executor); mantidas as que ainda valem; "How to apply" reescrito para apontar ao AGENTS/skill atuais (fora do git, pasta de usuário)
  - `~/.claude/projects/-Users-sidarta48-github-agente-nw/memory/MEMORY.md` — índice atualizado para refletir a limpeza (fora do git, pasta de usuário)
- Arquivos removidos: `~/.claude/projects/-Users-sidarta48-github-agente-nw/memory/project_produto_e_estado.md` (descrição do produto desatualizada desde os briefs 038/047; fora do git, pasta de usuário)
- Arquivos preservados literalmente na área afetada: `AGENTS.md`, `.claude/hooks/guarda_comando.py`, `.claude/hooks/lint_arquivo.py`, `.claude/skills/executar/SKILL.md`
- Script de verificação (o gate, rodado pelo `scripts/agente_entregar.sh`; saída colada):
  ```
  manifesto 063: 1 arquivo(s)
  ruff check: ok
  ruff format: ok
  mypy: ok
  pytest: ok (790 passed, 5 deselected in 19.34s)
  lacunas do 063: 4 no Backlog, 0 em Pendências, 0 em Dívidas, 0 em Decisões
  ✓ brief 063: commit b09df33, enviado ao GitHub
  ```
  (Primeira tentativa falhou no commit: `docs/briefs/_modelo.md` está dentro de `docs/*`, ignorado pelo `.gitignore` — corrigido tirando-o do manifesto, já que `docs/` fica fora do git por desenho, só `AGENTS.md` é rastreado.)
- Comandos executados: `scripts/agente_entregar.sh 063` (duas vezes; a primeira parou antes de tocar no git, por manifesto com arquivo fora do git)
- Manifesto do commit:
  - `logs/entregue_063_commit.txt`: `feat(claude-code): estilo Concise padrao e campo Esforco no modelo de brief (brief 063)`
  - `logs/entregue_063_arquivos.txt`: `.claude/settings.json`
- Pendências e decisões que ficaram abertas: nenhuma pendência de Sidarta gerada por este brief; as duas ressalvas da seção 4 (iniciar pelo celular sem o Mac já ligado; "app desktop" não confirmado para a retomada automática) já estão registradas no texto acima, não exigem decisão
- Resumo, Doing, Backlog e Done do `docs/PLAN.md` atualizados: sim

## Lacunas

| # | Lacuna | Destino | Impacto |
|---|---|---|---|
| 1 | `.worktreeinclude` para cobrir banco/ambiente quando o projeto passar a usar git worktree (não resolve o banco, que vem do `copiar-banco`, nem o ambiente Python editável) | backlog | nice |
| 2 | `/goal` no lugar das "até 3 tentativas" da skill `/executar` | backlog | nice |
| 3 | `/code-review` local ao fim de cada fase do produto, comparado com a auditoria de 12 passes | backlog | nice |
| 4 | Regras por caminho (`.claude/rules/` com `paths`) para as regras de migração, prompts e extensão hoje no AGENTS | backlog | nice |
