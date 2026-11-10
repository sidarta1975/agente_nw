# Brief 090 — Cartão e qualificação passam a ler o corpo de todos os itens

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Conjunto:** correção do texto por inteiro (086 a 095)
**Arquivos-alvo:** `agente_nw/relevancia/cartoes.py` (300 caracteres por item, 5 itens), `agente_nw/relevancia/qualificador.py` (`_itens_recentes_resumidos`), o prompt do cartão e do gate de objetivo em `agente_nw/nucleo/prompts/`, uma migração para o resumo por item (coluna versionada), `config/llm_routing.yaml` (`num_ctx`, só com medida), `tests/test_cartao_corpo_inteiro.py` (novo), mais o relatório, o manifesto e o PLAN
**Seções a ler:** relatório 079 (pontos de cartão/qualificação); seções 2.1 e 7 do relatório do agente_nw em `referencias/relatorios_projetos`; relatório do sergio (consolidação por partes) e do cervello (coluna de cobertura); relatórios 082, 088 e 089 (inteiros); `config/llm_routing.yaml`; perfis de hardware (`air16`, `pro48`)
**Modelo:** Opus
**Esforço:** alto
**Teste de aceite:** `tests/test_cartao_corpo_inteiro.py`
**Depende de:** brief 089 executado
**Ordem em série:** depois de 089; antes de 091
**Data:** 2026-11-08

---

## 1. Objetivo em uma frase

O cartão do assunto e a qualificação de relevância passam a ser produzidos a partir do que **todos** os itens do assunto dizem, não dos 300 primeiros caracteres de 5 itens.

## 2. Decisões (de Sidarta)

**2.1. Resumo por item, depois cartão dos resumos.** Cada item ganha um resumo guardado (coluna versionada, gerado com o texto inteiro pela peça do brief 088 quando o texto é longo). O cartão do assunto é montado a partir dos resumos de **todos** os itens do assunto dentro do orçamento da janela. Se nem os resumos cabem, aplica-se a mesma divisão em partes do brief 088 sobre a lista de resumos (consolidação em dois níveis), nunca corte.

**2.2. `qualificador._itens_recentes_resumidos`** usa os mesmos resumos em vez do corte; o gate de objetivo e a redação melhoram junto, porque leem o cartão.

**2.3. `num_ctx`.** Só muda com medida (prompt real medido pelo brief 082) e respeitando o perfil `air16` (16 GB, produção): se o valor necessário não cabe no `air16`, o relatório diz e a tarefa usa a divisão em partes nesse perfil. O valor ajustado vai no `llm_routing.yaml`, não no código.

**2.4. Versões.** Prompts e resumos ganham versão nova; cartões antigos ficam válidos até a regravação autorizada pelo dono (095). Nenhum cartão existente é regravado aqui.

**2.5. Comparação em simulação** (sobre cópia do banco, sem gravar): para uma amostra de assuntos, mostra o cartão antigo e o novo lado a lado e quantas decisões de relevância mudam. Só contagens e identificadores no relatório, sem copiar texto de terceiros.

**2.6. Medição real.** Se houver Ollama local ligado, rodar uma amostra pequena (10 assuntos) e registrar tempo e tokens do prompt (campo do 082). Se não houver, dizer no relatório e deixar como "Para você".

## 3. Escopo (arquivos)

| Arquivo | O que muda |
|---|---|
| `cartoes.py`, `qualificador.py`, prompts | Usam resumos de todos os itens; sem corte de 300 e sem teto de 5. |
| migração | Coluna de resumo por item com versão. |
| `llm_routing.yaml` | `num_ctx` apenas se medido. |
| `tests/test_cartao_corpo_inteiro.py` | Seção 4. |

## 4. Testes (LLM falso)

1. Marcador no último caractere do corpo do 6º item chega ao prompt do cartão (via resumo). 2. Assunto com 40 itens: os 40 aparecem representados, nenhum descartado. 3. Resumos que excedem o orçamento disparam consolidação em dois níveis e todos os itens continuam cobertos. 4. Texto curto: prompt do resumo idêntico ao texto original. 5. Versão antiga de cartão não é confundida com a nova. 6. `qualificador` recebe os resumos, não o corte.

## 5. Fora de escopo

Regravar cartões existentes (095); vetores (089); redação e busca do "evitar" (091).

## 6. Passos e critérios de aceite

Passos: conferir "Depende de"; testes; implementar; comparação em simulação; relatório `doc_090_...` com a resposta a "algum texto é analisado só em parte?" por ponto tocado; manifesto; PLAN; `scripts/agente_entregar.sh 090`. Aceite: (1) `pytest tests/test_cartao_corpo_inteiro.py -q` verde; (2) `grep` sem `[:300]` nem `[:5]` em `cartoes.py` e `qualificador.py`; (3) gate verde; (4) pontos do 079 marcados `CORRIGIDO (brief 090)`. Última linha: "Para você: decidir a regravação dos cartões (brief 095) depois de ver a comparação".
