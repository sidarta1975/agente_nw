# PLAN.md — estado vivo do agente_nw

Atualizado a todo commit. Quem executa lê este arquivo depois de `PLANO.md` e `ARQUITETURA.md`, antes de tocar em código.

**Última atualização:** 2026-09-12
**Fase atual:** Fase 1 — Núcleo, não iniciada
**Estado do repositório:** não inspecionado nesta sessão (a pasta não estava conectada). Quem executar a Fase 1 investiga o que já existe antes de criar qualquer arquivo.

---

## Próximo passo

Brief de execução da Fase 1 — Núcleo. Escopo:

1. `.gitignore` com a regra de documentos e a de dado pessoal (lista em `PLANO.md`, seção 7), e `temas.exemplo.yaml` versionado.
2. Esquema SQLite completo em `scripts/esquema.sql`, cobrindo todos os contratos de `ARQUITETURA.md` seção 3.
3. Modelos Pydantic v2 `frozen=True`, um módulo por entidade, em `nucleo/modelos/`.
4. `config/container.py` e `config/llm_routing.yaml` com o roteamento da seção 3.1 do `PLANO.md`.
5. Cliente único de LLM com `num_ctx` obrigatório por chamada, `format: json` nas tarefas estruturadas, uma nova tentativa em JSON inválido e fila de revisão na segunda falha.
6. Camada de consultas SQL isolada em `nucleo/database/queries/`.
7. Testes: contratos, cliente de LLM contra um Ollama real, e criação do esquema em banco temporário.

Fora do escopo da Fase 1: qualquer coleta, qualquer interface, qualquer prompt de produto.

---

## Decisões em aberto

| # | Decisão | Situação |
|---|---|---|
| 1 | `AGENTS.md` commitado ou não | Aberta. A regra geral manda não commitar. O custo é que o repositório, numa segunda máquina, chega sem as regras do executor. Alternativa: bootstrap copiando o `AGENTS.md` da aba Saídas. Mesma tensão não resolvida em `advogada_parceira_free`. |
| 2 | Origem dos briefs | Aberta. As instruções do Projeto dizem `~/Meu Drive/briefs/agente_relacionamento/briefs/`; o `AGENTS.md` do repositório diz `docs/briefs/`. Proposta: Drive é origem, `docs/briefs/` é cópia do que foi executado, ambos fora do git. Exige corrigir uma linha do `AGENTS.md`. |
| 3 | Nome do pacote no código | Aberta. O `AGENTS.md` fala em `agente_relacionamento/`; a pasta real é `agente_nw`. Decidir antes de criar o primeiro módulo, para não renomear depois. |
| 4 | Processamento das capturas | Aberta. Na hora (30–60 s de CPU com o navegador aberto) ou na fila da madrugada. Recomendação registrada: fila, com botão "processar agora" no console. |
| 5 | Quantização do 14b para síntese de perfil | Aberta. `qwen2.5:14b` instalado é Q4_K_M. Com 48 GB cabe `q8_0` (~16 GB), que rende onde importa — a síntese roda poucas vezes por semana. Testar antes de fixar. |
| 6 | Comparar com a geração 3 do Qwen | Aberta. `qwen3:14b` é melhor em seguir formato e produzir JSON válido, que são os dois gargalos deste pipeline. Manter o 2.5 como linha de base e medir. |

---

## Protocolo de medição 7b × 14b

A decidir por medida, não por impressão. Separar 20 blocos capturados e 10 assuntos formados, rodar os dois modelos no mesmo material e registrar:

- percentual de JSON válido na primeira tentativa;
- concordância de nota com o 14b (diferença menor que 10 pontos);
- tempo por chamada.

O 7b é promovido para uma tarefa apenas com **JSON válido acima de 98%** e **concordância acima de 85%**. Abaixo disso, reprocessamento e nota errada custam mais que os segundos economizados. Resultado registrado em ADR.

---

## Dívidas conhecidas

Nenhuma. Repositório no início.

---

## Armadilhas já identificadas — não redescobrir

1. **`num_ctx` padrão do Ollama trunca a entrada em silêncio.** Devolve resposta plausível sobre metade do material, sem erro. Explícito em toda chamada.
2. **Aba em segundo plano no Chrome renderiza pela metade.** Uma aba só, em foco, reaproveitada em sequência.
3. **Seletor de CSS de rede social quebra em quinze dias.** Captura de texto visível genérico; a interpretação é do modelo.
4. **Release distribuído a quinze portais parece assunto denso.** Fonte só é independente com domínio diferente e divergência de texto acima de 30%.
5. **Visita a perfil no LinkedIn é visível para o dono do perfil.** Registrar data da última coleta e avisar em recoleta antes de 30 dias.
6. **`nomic-embed-text` tem foco em inglês.** Em português, `bge-m3`. A recomendação anterior de evitar o `bge-m3` valia para máquina de 8 GB e não se aplica aqui.
7. **Dado pessoal de terceiros no repositório.** `git add -A` é proibido; `.gitignore` nasce com `dados/`, `capturas/`, `*.db`, `temas.yaml`, `*.csv`.

---

## Histórico de decisões desta sessão

| Data | Decisão |
|---|---|
| 2026-09-12 | Geração de mensagem, tom, cadência e aprovação de envio saem do escopo em definitivo. O produto é coletor de assuntos com fichas de contato. |
| 2026-09-12 | Projeto é 100% local. As frentes de ChatGPT, Gemini e Claude em nuvem do plano original ficam canceladas. |
| 2026-09-12 | Coleta em rede social é sob demanda, contato por contato, pela extensão, na sessão do usuário. Nunca periódica, nunca em laço sobre a lista. |
| 2026-09-12 | Interface é console web local em `localhost:8765`, no lugar da entrega em arquivo Markdown com caixa de marcação. |
| 2026-09-12 | Roteamento fixado: `qwen2.5:7b` para tarefas simples, `qwen2.5:14b` para complexas, `bge-m3` para embeddings. |
| 2026-09-12 | Histórico de fatos é só-inserção; cargo, empresa e cidade são versionados. A recoleta entrega diferença, não fotografia. |
