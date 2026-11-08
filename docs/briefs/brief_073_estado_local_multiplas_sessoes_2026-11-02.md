# Brief 073 — Estado local do projeto não atravessa sessão nem worktree: documentar no AGENTS.md

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Conjunto:** nenhum (brief isolado, direto na `main`) — documentação, sem código
**Arquivos-alvo:** `AGENTS.md` (nova seção, depois da que o brief 072 acrescentou), `docs/docs/doc_073_estado_local_multiplas_sessoes_2026-11-02.md`, `logs/commit_073.txt`, `logs/arquivos_073.txt`
**Seções a ler:** `AGENTS.md` inteiro (para encaixar a numeração); `.gitignore`; `config/container.py` (`caminho_banco`, `RAIZ`)
**Modelo:** Sonnet
**Esforço:** baixo
**Teste de aceite:** nenhum (documentação; o gate roda só para confirmar que nada de código foi tocado)
**Depende de:** nada — mas usa o mesmo lugar no arquivo que o brief 072 abriu; se os dois forem executados fora de ordem, o executor confere a numeração das seções antes de escrever
**Data:** 2026-11-02

---

## 1. Objetivo em uma frase

Registrar no AGENTS.md que o banco (`dados/agente.db`) e toda a pasta `docs/` (PLAN, briefs, relatórios) são estado local de uma árvore de trabalho só — nunca compartilhados entre uma sessão de terminal, uma sessão do aplicativo Desktop, ou uma worktree separada — para que ninguém trabalhe por engano contra uma cópia desatualizada ou perca o estado achando que ele "está no projeto".

---

## 2. Achado no código, não só pensado

Sidarta trouxe um material sobre as quatro superfícies do Claude Code (terminal, aplicativo Desktop, Remote Control, Dispatch): todas rodam a mesma engine e leem a mesma configuração do projeto, mas **não compartilham histórico de conversa**, e só compartilham disco **dentro da mesma árvore de trabalho** — uma sessão aberta numa worktree (cópia separada do repositório, em outra pasta) tem sua própria cópia de qualquer estado local não versionado, desconectada da árvore principal.

Apurei dois pontos exatos onde isso se aplica a este projeto:

**2.1. O banco é por árvore, não por projeto.** `config/container.py`:
```python
def caminho_banco() -> Path:
    caminho = Path(configuracao().local.banco)
    return caminho if caminho.is_absolute() else RAIZ / caminho
```
`configuracao().local.banco` é `dados/agente.db` (`config/local.yaml`), um caminho relativo — resolvido contra `RAIZ`, que é a raiz da árvore de trabalho em que o processo está rodando. Uma sessão aberta numa worktree separada (já aconteceu neste projeto: `git worktree list` mostra `agente_nw_040`, da época do brief 040, com a pasta já apagada mas o registro ainda vivo no git) teria seu **próprio banco**, vazio ou desatualizado — sem nenhum aviso de que é outro banco.

**2.2. `docs/` inteiro nunca é versionado — nem hoje, nem nunca foi.** `.gitignore`:
```
docs/*
!docs/.gitkeep
```
`git ls-files docs/` devolve vazio: nem um arquivo de `docs/` jamais entrou num commit. Isso inclui `docs/PLAN.md`, todo `docs/briefs/*.md` e todo `docs/docs/doc_*.md` — ou seja, o estado vivo do projeto (o que está em andamento, o que já foi decidido, o histórico de cada brief) só existe como arquivo local da árvore de trabalho onde foi escrito. Uma worktree nova nasce **sem nada disso**: sem PLAN, sem histórico de brief, sem relatório algum — mesmo que o código dentro dela esteja no commit mais recente da `main`.

Combinando os dois achados: uma sessão do aplicativo Desktop ou de Dispatch que abrisse (ou tivesse aberto) este projeto numa worktree estaria, ao mesmo tempo, sem o PLAN real, sem o histórico de briefs real, e gravando num banco próprio — um ambiente que parece o projeto mas não é, sem nenhum sinal visível da diferença.

---

## 3. Decisão

Acrescentar uma seção ao AGENTS.md — sugestão de numeração **"12. Estado local: uma árvore de trabalho só"** (o executor confere qual número está livre, considerando o que o brief 072 já tiver acrescentado) — com este conteúdo (o executor pode ajustar a redação ao tom do arquivo, preservando os dois achados e a regra prática):

```markdown
## 12. Estado local: uma árvore de trabalho só

Este projeto guarda estado que não é código nem está no git: o banco (`dados/agente.db`, resolvido contra
a raiz da árvore de trabalho onde o processo roda) e a pasta `docs/` inteira (`docs/PLAN.md`,
`docs/briefs/`, `docs/docs/`) — `.gitignore` exclui `docs/*` de propósito; nada dali nunca foi commitado.

Isso só se comporta como "o projeto" dentro de uma única árvore de trabalho. Uma sessão aberta numa
**worktree** separada (`git worktree add`) tem sua própria cópia de disco, desconectada: seu próprio banco
(vazio ou desatualizado) e sua própria pasta `docs/` (sem PLAN, sem briefs, sem relatório nenhum), mesmo
rodando o mesmo código da `main`. Já existiu uma worktree deste tipo neste projeto (`agente_nw_040`).

**Regra prática:** todo trabalho deste projeto — terminal, aplicativo Desktop ou Dispatch — roda na árvore
de trabalho principal, nunca numa worktree. Para continuar, de outro aparelho, uma tarefa já em andamento,
usar Remote Control (controla a sessão que já existe, com o mesmo estado) — nunca abrir uma sessão nova
apontando para este projeto, porque ela não vai saber o que a sessão anterior já decidiu ou estava fazendo,
e, se cair numa worktree, nem vai ver o banco ou o PLAN reais.
```

---

## 4. Testes

Nenhum teste de código — é documentação. O executor confirma que o gate continua verde (nada de código foi tocado) e que a seção nova não contradiz nenhuma seção existente, inclusive a que o brief 072 acrescentou.

---

## 5. Fora de escopo

- Decidir se `docs/` deveria passar a ser versionada pelo git (isso mudaria o que `scripts/commitar.sh` e `scripts/agente_entregar.sh` consideram parte do commit) — é decisão de produto de Sidarta, não deste brief; fica registrada como decisão em aberto no relatório.
- Limpar o registro da worktree `agente_nw_040` (`git worktree prune`) — inofensivo deixar como está (a pasta já não existe), mas também fora de escopo aqui; se Sidarta quiser, é um comando isolado, não um brief.
- Qualquer mudança em `config/container.py` ou em como o banco é resolvido — este brief só documenta o comportamento atual.

---

## 6. Passos e aceite

Executar com `/executar 073`. Aceite: gate verde (confirma que nada de código mudou), commit e push pelo executor.

Sem pendência de teste real para Sidarta — é documentação; a prova é o próprio texto do AGENTS.md.

## Lacunas

| # | Lacuna | Destino | Impacto |
|---|---|---|---|
| 1 | `docs/` nunca é versionado pelo git — todo o histórico de PLAN, briefs e relatórios existe só como arquivo local, sem backup pelo git. Sidarta decide se isso deve mudar | decisão | degrada |
