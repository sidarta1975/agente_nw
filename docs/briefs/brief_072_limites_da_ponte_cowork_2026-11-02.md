# Brief 072 — Documentar os limites da ponte do Cowork com o computador no AGENTS.md

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Conjunto:** nenhum (brief isolado, direto na `main`) — documentação, sem código
**Arquivos-alvo:** `AGENTS.md` (nova seção), `docs/docs/doc_072_limites_da_ponte_cowork_2026-11-02.md`, `logs/commit_072.txt`, `logs/arquivos_072.txt`
**Seções a ler:** `AGENTS.md` inteiro, para encaixar a nova seção na numeração e no tom das demais
**Modelo:** Sonnet
**Esforço:** baixo
**Teste de aceite:** nenhum (documentação; o gate roda só para confirmar que nada mais foi tocado)
**Depende de:** nada
**Data:** 2026-11-02

---

## 1. Objetivo em uma frase

Registrar no AGENTS.md, de forma precisa, o que a sessão do Cowork (Claude Code "virtual", pela ponte de dispositivo com o computador) pode e não pode fazer neste projeto — e por quê — para não reabrir a mesma investigação a cada tentativa.

---

## 2. Por quê (apurado nesta sessão, não só pensado)

Sidarta pediu para eu (Cowork) disparar a execução de um brief diretamente, sem passar pelo terminal dele. Testei três caminhos e todos batem numa parede diferente, apurada uma a uma:

1. **A ponte de arquivos (o que monta a pasta do projeto para o Cowork) roda numa VM Linux, não no Mac.** Os binários do ambiente do projeto (`.venv/bin/ruff`, por exemplo) são executáveis de macOS (Mach-O arm64); a VM Linux não consegue executá-los ("Exec format error"). Não é falta de instalação: é arquitetura/sistema incompatível.
2. **O projeto depende de um pacote exclusivo do macOS** (`pyobjc-framework-Contacts`, usado para ler a agenda de contatos do Mac) — nem recriando o ambiente do zero dentro dessa VM Linux ele instalaria, porque essa peça não existe para Linux.
3. **A ponte não tem as credenciais do GitHub de Sidarta** (sem chave SSH, sem `gh auth`, sem credential helper configurado) — mesmo que o código rodasse, não haveria como enviar o commit.
4. **O controle de tela (computer use) bloqueia digitação em Terminal e IDEs por categoria, não por permissão** — é uma trava de segurança da própria ferramenta, que nenhuma concessão de acesso remove.

A consequência prática: hoje, o único caminho confiável para gerar e validar código deste projeto é a sessão de terminal de Sidarta, com `/executar <NNN>`, exatamente como todos os briefs até aqui foram executados.

---

## 3. Decisão

Acrescentar uma seção nova ao AGENTS.md — sugestão de numeração **"11. Cowork: o que a ponte com o computador pode e não pode fazer"** (ajustar o número se outra seção tiver entrado entre a 10 e esta) — com o conteúdo abaixo (o executor pode ajustar a redação para o tom do arquivo, preservando os quatro motivos):

```markdown
## 11. Cowork: o que a ponte com o computador pode e não pode fazer

O Cowork (a sessão de planejamento que escreve os briefs) tem, por uma ponte de dispositivo, acesso de leitura
e escrita aos arquivos deste repositório no computador de Sidarta — mas essa ponte roda numa máquina virtual
Linux separada do Mac, não no Mac. Por isso:

- **Pode:** ler qualquer arquivo e o código; escrever e revisar briefs (`docs/briefs/`), documentos e o
  `docs/PLAN.md`; inspecionar o resultado de um brief já executado (git log, arquivos alterados, conteúdo).
- **Não pode:** rodar o gate (`scripts/verificar.sh`) nem a suíte de testes — os binários do `.venv` são de
  macOS e a VM Linux não os executa, e o projeto depende de um pacote exclusivo do macOS
  (`pyobjc-framework-Contacts`), então nem um ambiente novo dentro dessa VM resolveria. Sem rodar o gate de
  verdade, o Cowork nunca declara que um código "passou" ou "funciona" (viola o §8).
- **Não pode:** commitar nem publicar — a ponte não tem as credenciais do GitHub de Sidarta.
- **Não pode:** digitar comandos no terminal ou numa IDE de Sidarta por controle de tela — essa ferramenta
  bloqueia digitação em terminal/IDE por categoria, mesmo com toda permissão concedida.

**Conclusão prática:** gerar e validar código deste projeto continua sendo tarefa da sessão de terminal de
Sidarta, com `/executar <NNN>`. O Cowork prepara o brief; Sidarta executa. Isto só muda se um brief futuro
mudar alguma das quatro condições acima (por exemplo, um ambiente Linux equivalente dentro da ponte, ou
credenciais de git configuradas nela por decisão explícita de Sidarta).
```

---

## 4. Testes

Nenhum teste de código — é documentação. O executor confirma que o gate continua verde (nada de código foi tocado) e que a seção nova não contradiz nenhuma seção existente (em especial §5, Git, e §10, Briefs e numeração).

---

## 5. Fora de escopo

- Qualquer tentativa de montar um ambiente Linux equivalente dentro da ponte, ou de configurar credenciais de git nela — são decisões de Sidarta, não deste brief.
- Mudar `.claude/hooks/guarda_comando.py` ou qualquer mecanismo de execução — este brief só documenta o estado atual.

---

## 6. Passos e aceite

Executar com `/executar 072`. Aceite: gate verde (confirma que nada de código mudou), commit e push pelo executor.

Sem pendência de teste real para Sidarta — é documentação; a prova é o próprio texto do AGENTS.md.
