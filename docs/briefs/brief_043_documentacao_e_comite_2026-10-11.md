# Brief 043 — Documentação alinhada ao plano v3.1 e proposta ao comitê v6

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Depende de:** brief 039 (tela única em uso). Pode ser executado a qualquer momento depois dele, em paralelo com 040–042. Sem código.
**Plano:** v3.1.
**Data:** 2026-10-11

---

## 1. Objetivo em uma frase

Os documentos canônicos do repositório e a proposta ao comitê passam a descrever o produto que existe — uma frase entra, conteúdo pronto sai, nenhum cadastro é pré-requisito — e registram, com data, a reversão da regra "não existe geração de mensagem".

---

## 2. Documentos e o que muda em cada um

**2.1. `AGENTS.md`** (fonte da verdade para o executor; revisão integral, não remendo):
- Seção 2 (estrutura): acrescentar `nucleo/pedido.py`, `nucleo/localizacao.py`, `nucleo/redacao.py`, `nucleo/fluxo.py`, `nucleo/medicao.py`, `perfil/inferencia.py`, `coleta/capturas/listas.py`, `prompts/extrair_pedido.py`, `prompts/desempatar_perfil.py`, `prompts/redigir_ganchos.py`, `prompts/descrever_tema.py` (se existir), templates `inicio.html`, `pedido.html`, `pedido_lista.html`, `pessoa.html`; migrações 006–012.
- Seção 3 (stack): lista completa de tarefas de LLM por perfil; menção de que a redação é a única tarefa com temperatura 0,5.
- Seção 6 (tarefas não assistidas): acrescentar "leitura das listas do usuário nas redes: sob demanda, com cache de 30 dias, nunca periódica"; manter "nunca rodam sozinhos: git, leitura de rede social, alteração de ficha de contato, suíte de testes".
- Seção 7 (comportamento): o texto do brief 036 (3.11), mais uma linha sobre continuidade (041) e uma sobre temas inferidos (040). Registrar explicitamente: "Decisão de 2026-10-11 (plano v3.1): geração de conteúdo passa a existir; envio continua não existindo."
- Seção 9 (certificação): `verificar.sh` para código; `certificar` para validade de JSON; `medir` para uso.
- Remover qualquer referência a ciclo, agendamento, LaunchAgent, tags como conceito de interface, `importar-temas` como passo de instalação.

**2.2. `ARQUITETURA.md`** (no Projeto e no repositório, se existir cópia):
- Fluxo do pedido em um diagrama de texto: frase → extração → localização (listas / busca geral / link) → coleta dirigida → seleção (034/035) → redação → gravação → tela. Com os pontos em que o usuário intervém (confirmação da pessoa, usei/não serve, correção em texto).
- Tabelas: `pedido`, `lista_rede_social`, `gancho_uso`, colunas novas de `perfil`, `consulta_contato`, `assunto_contato`.
- Perfis de hardware e instância do Ollama por máquina (031/032).

**2.3. `PLAN.md` / `PLANO.md`**: substituir o conteúdo pelo plano v3.1 com a tabela de briefs 036–043 e o status de cada um (implementado em `<commit>` / pendente). Os planos anteriores vão para `docs/historico/`.

**2.4. Proposta ao comitê, v6** (`docs/proposta_comite_v6_<data>.md`, e no Projeto): a partir da v5, com:
- Seção nova "O que mudou desde a v5 e por quê": modo sob demanda (brief 016), contexto como sinal principal (034), texto livre e geração de conteúdo (plano v3.1), com a justificativa em uma frase cada — a v5 descrevia um sistema em que o usuário classificava; o uso mostrou que isso transferia o trabalho ao usuário.
- Roteiro em quatro etapas da v5 mantido, com a etapa 1 atualizada para "MVP em uso no Pro com Qwen 2.5 14B; versão Air com Qwen3 4B em avaliação (medição do brief 042)".
- Regras inalteradas destacadas: 100 % local, sem API, sem agendamento, sem envio de mensagem, sem nuvem.
- Nenhuma seção jurídica.

**2.5. `README` de instalação** (se não existir, criar `docs/instalacao.md`): passos para Pro (instância compartilhada, `perfil_llm: pro48`) e Air (`ollama serve` manual, `air16`); primeira frase como todo o onboarding; `playwright install chromium`; nenhuma menção a temas ou cadastro.

---

## 3. Critérios de aceite

1. `grep -rn "ciclo\|launchd\|LaunchAgent\|importar-temas\|tag" AGENTS.md` só devolve ocorrências em contexto de "não existe mais" ou de bastidor.
2. Um executor que leia só o `AGENTS.md` consegue descrever o fluxo do pedido de ponta a ponta sem abrir código.
3. A proposta v6 tem a seção "o que mudou e por quê" com data e referência ao plano v3.1.
4. `PLAN.md` lista os briefs 036–043 com status.

---

## 4. Passos de execução

1. `AGENTS.md`.
2. `ARQUITETURA.md`.
3. `PLAN.md`/`PLANO.md` e movimentação dos planos antigos para `docs/historico/`.
4. Proposta v6.
5. `docs/instalacao.md`.
6. Lista para `git add` (só os arquivos versionados: `AGENTS.md`; os demais ficam fora do git por `docs/*` estar ignorado — entregar também os caminhos para Sidarta publicar no Projeto) e mensagem: `docs: AGENTS.md alinhado ao plano v3.1 — texto livre, geração de conteúdo, sem cadastro (brief 043)`.

O commit e a publicação dos documentos no Projeto são passos de Sidarta.
