# Brief 066 — Proveniência do que a IA produziu

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Conjunto:** camada_de_ia (064, 065 e 066)
**Arquivos-alvo:** `agente_nw/nucleo/llm.py`, todos os módulos de `agente_nw/nucleo/prompts/` (constante de versão), as consultas que gravam gancho, cartão, pontuação de relevância e extrações, `scripts/migracoes/019_proveniencia.sql` (nova — o executor confere `ls scripts/migracoes/` antes de numerar; a última hoje é 017, do brief 040, mas o 065 deste mesmo conjunto usa 018), `tests/test_proveniencia.py` (novo), `docs/docs/doc_066_proveniencia_da_ia_2026-11-02.md`, `logs/commit_066.txt`, `logs/arquivos_066.txt`
**Seções a ler:** ARQUITETURA §8 (camada de LLM) e §12 (banco); no PLAN, as armadilhas 16 e 28 (identidade e dimensão de vetor); `nucleo/llm.py` já com o brief 064 aplicado; pelo menos três módulos de `nucleo/prompts/` para ver o padrão atual (sem constante de versão)
**Modelo:** Opus — toca `nucleo/llm.py` outra vez depois do 064 e se espalha por todos os módulos de prompt; risco de esquecer um módulo ou uma tabela gerada por IA
**Esforço:** médio
**Teste de aceite:** `tests/test_proveniencia.py`
**Depende de:** brief 064 — altera o mesmo trecho de `nucleo/llm.py` (a chamada ao Ollama); precisa estar executado e mesclado antes deste, para não haver dois briefs reescrevendo a mesma função em paralelo
**Data:** 2026-11-02

---

## 1. Objetivo em uma frase

Para cada registro gerado pelo modelo, saber qual perfil, qual modelo e qual versão de prompt o produziram; para cada vetor armazenado, saber qual modelo de embedding o gerou.

---

## 2. Por que (achado no código, não só pensado)

Hoje nenhum módulo de `agente_nw/nucleo/prompts/` tem uma constante de versão. Nenhuma tabela ou consulta grava qual modelo, qual perfil (`air16`/`pro48`) ou qual versão de prompt produziu um gancho, um cartão, uma pontuação de relevância ou uma extração. Os vetores de tema, assunto e perfil também não guardam qual modelo de embedding os gerou. Sem isso, não há como saber depois, por exemplo, se uma mensagem ruim veio do modelo de 4B ou do de 14B, ou se uma mudança de prompt é a causa de uma piora — e trocar o modelo de embedding um dia misturaria vetores incompatíveis sem sinal nenhum do problema.

---

## 3. Decisões

**3.1. Versão obrigatória em cada módulo de prompt.** Todo módulo em `nucleo/prompts/` ganha, no topo, `VERSAO = "AAAA-MM-DD-n"` (data do último ajuste de conteúdo do prompt + um número sequencial, se mudar mais de uma vez no dia). Uma verificação na carga da aplicação (mesmo lugar que já valida a configuração) confere que todo módulo de prompt declara `VERSAO`; falta de uma delas impede o start, com o nome do módulo faltante na mensagem. É o mecanismo que o `cervello` já usa.

**3.2. O cliente registra o que usou.** `ClienteOllama.gerar_json` passa a registrar, junto do que já grava hoje (`_registrar_log_chamada`): perfil ativo (`air16`/`pro48`), nome do modelo, versão do prompt (recebida como parâmetro novo, opcional — tarefa que não a passa fica com `None`, sem quebrar nada) e a latência da chamada (já é possível medir, só não é gravada). Essas quatro informações entram na mesma linha do log de chamadas (`caminho_log_llm`), sem mudar seu formato além de acrescentar campos.

**3.3. Proveniência nos registros gerados.** As tabelas que guardam o resultado de uma geração — `gancho_uso`, as pontuações de relevância e as extrações (fila de extração e seus resultados) — recebem as colunas `gerado_por_modelo TEXT NULL`, `gerado_por_perfil TEXT NULL` e `gerado_por_prompt_versao TEXT NULL`. Preenchidas no momento da gravação, a partir do que o item 3.2 já tem disponível. Dado já existente nasce com as três colunas `NULL` — não se reconstrói proveniência do passado.

**3.4. Proveniência do vetor, sem sobrescrever.** As tabelas de centroide (`vetor_tema`, `vetor_assunto`, `vetor_perfil` — não os vetores de item individual, que já têm seu próprio ciclo de vida) recebem a coluna `modelo_embedding TEXT NOT NULL`, preenchida com o nome do modelo de embedding do perfil ativo no momento em que o vetor foi calculado. Trocar de modelo de embedding no futuro não limpa nem sobrescreve essas linhas — um vetor calculado por um modelo antigo fica marcado como tal, e passa a ser **inválido por chave** (o código que lê o centróide confere o nome do modelo atual contra essa coluna; se não bater, trata como ausente, nunca como inválido silenciosamente). Isso fica pronto para uso, não implementado neste brief: nenhuma rotina de recálculo automático entra aqui — é o que o item 3.5 deixa explícito.

**3.5. Fora de escopo deliberado.** Reprocessamento seletivo automático dos registros antigos, ou dos vetores de um modelo trocado. Este brief grava o dado que torna isso possível depois; decidir quando e como reprocessar é decisão de produto, não deste brief.

---

## 4. Testes (escritos antes do código)

- `tests/test_proveniencia.py`:
  - carregar a aplicação com um módulo de prompt sem `VERSAO` → falha explícita, citando o módulo;
  - `gerar_json` bem-sucedido → a linha do log de chamadas tem perfil, modelo, versão de prompt e latência;
  - um gancho gravado por `gancho_uso` tem as três colunas de proveniência preenchidas, coerentes com o que o cliente simulado reportou;
  - um vetor de tema calculado hoje grava o `modelo_embedding` do perfil ativo;
  - trocar o perfil ativo para um com outro modelo de embedding e comparar um centróide antigo → é tratado como ausente (não lido como se fosse do modelo novo), sem apagar a linha antiga.
- O LLM é sempre simulado.

---

## 5. Fora de escopo

- Reprocessar registros ou vetores antigos (3.5).
- Mudar o conteúdo de qualquer prompt — só a constante de versão é acrescentada.
- Expor proveniência em alguma tela do console — fica disponível no banco; uma tela que a mostre é brief futuro, se fizer falta.

---

## 6. Passos e aceite

Executar com `/executar 066`. Aceite: testes da seção 4 verdes, gate verde, commit e push pelo executor.

Sem pendência de teste real para Sidarta neste brief — é dado de bastidor, sem comportamento visível no console para conferir manualmente.
