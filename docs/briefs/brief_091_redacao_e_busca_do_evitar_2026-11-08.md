# Brief 091 — Redação e busca do "evitar" com os fatos e os itens inteiros

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Conjunto:** correção do texto por inteiro (086 a 095)
**Arquivos-alvo:** `agente_nw/nucleo/prompts/redigir_ganchos.py` (fatos e itens dentro do orçamento), `agente_nw/perfil/termos.py` ou onde estiver `termos_do_contato` (corte de 300), `termo_evitado` (busca em título/resumo/manchetes de todos os itens do assunto), `tests/test_evitar_e_fatos_inteiros.py` (novo), mais o relatório, o manifesto e o PLAN
**Seções a ler:** relatório 079 (pontos de redação/evitar, inclusive P-039); brief 081 e seu relatório (comentários do usuário inteiros, `evitar` sem teto); relatório do agente_nw em `referencias/relatorios_projetos`; AGENTS §4 e §9
**Modelo:** Sonnet
**Esforço:** médio
**Teste de aceite:** `tests/test_evitar_e_fatos_inteiros.py`
**Depende de:** brief 081 executado
**Ordem em série:** depois de 081
**Data:** 2026-11-08

---

## 1. Objetivo em uma frase

O que Sidarta pede para evitar é procurado em todo o texto de todos os itens do assunto, e os fatos do contato entram inteiros na redação.

## 2. Decisões (de Sidarta)

**2.1. Fatos inteiros.** Cada fato do contato entra na redação sem corte. Se o conjunto passar do orçamento (estimador do brief 082), entram primeiro os fatos mais recentes (os 4 mais recentes têm prioridade) e a ordem é por data; o que não couber é **listado como não incluído** no registro da chamada, nunca omitido em silêncio.

**2.2. `termos_do_contato`** deixa de cortar em 300 caracteres.

**2.3. `termo_evitado`** passa a procurar em título, resumo e manchetes de **todos** os itens do assunto (hoje só de parte). Sem mudar a regra de decisão: achou o termo, o gancho é evitado.

**2.4. P-039** (ponto de apoio com 5 interesses): fica registrado como inalterado e redundante enquanto `interessa` for 5 por contrato; o executor não muda o código, acrescenta a lacuna "decisão: o número 5 continua sendo o desejado?" ao PLAN.

## 3. Escopo (arquivos)

Os da linha "Arquivos-alvo". Nenhum arquivo fora deles.

## 4. Testes (LLM falso)

1. Fato longo (3.000 caracteres) chega inteiro ao prompt. 2. Excesso de fatos: os 4 mais recentes entram e os demais aparecem na lista de "não incluídos". 3. Termo evitado que só aparece na manchete do 9º item é encontrado. 4. `termos_do_contato` de 1.000 caracteres devolve os termos do texto inteiro. 5. Entrada curta: prompt idêntico ao de antes.

## 5. Fora de escopo

Subir o número de interesses; regravar ganchos antigos (095).

## 6. Passos e critérios de aceite

Passos: conferir "Depende de"; testes; implementar; relatório `doc_091_...` com a resposta a "algum texto é analisado só em parte?" por ponto tocado; manifesto; PLAN; `scripts/agente_entregar.sh 091`. Aceite: (1) `pytest tests/test_evitar_e_fatos_inteiros.py -q` verde; (2) `grep` sem corte fixo restante nos três pontos; (3) gate verde.
