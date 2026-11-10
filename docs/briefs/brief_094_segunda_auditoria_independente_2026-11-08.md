# Brief 094 — Segunda auditoria independente do texto por inteiro

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Conjunto:** correção do texto por inteiro (086 a 095)
**Arquivos-alvo:** `docs/docs/doc_094_...md` (relatório), `tests/test_texto_extremo_ponta_a_ponta.py` (novo, permanente), mais o manifesto e o PLAN. Código de produção só muda se a auditoria achar defeito pequeno e claro; defeito maior vira lacuna
**Seções a ler:** **não ler o relatório 079 antes de terminar a auditoria** (a independência é o ponto). Depois de terminada, comparar com o 079. Ler: `AGENTS_agente_nw.md` §4 e a regra do texto por inteiro; `docs/EXCECOES_TEXTO_INTEGRAL.md`; relatórios do advogada_parceira_free (segunda auditoria cega) e do lex_hub em `referencias/relatorios_projetos`
**Modelo:** Opus
**Esforço:** alto
**Teste de aceite:** `tests/test_texto_extremo_ponta_a_ponta.py`
**Depende de:** brief 093 executado
**Ordem em série:** depois de 093; antes de 095
**Data:** 2026-11-08

---

## 1. Objetivo em uma frase

Alguém que não viu a primeira auditoria procura de novo, no código de produção, qualquer lugar onde um texto de terceiros é analisado só em parte, e prova com textos extremos que o sistema agora lê tudo.

## 2. Decisões (de Sidarta)

**2.1. Auditoria cega.** O executor não lê o doc_079 até terminar a lista dele. Para isso a lista é escrita primeiro, no relatório, e só depois comparada.

**2.2. Cobertura.** Ler **inteiros** os arquivos de maior risco: os que montam prompt, chamam LLM ou embedding e leem a coleta. Os demais, por amostra com semente fixa registrada, dos 256 arquivos que o 079 certificou limpos (a semente e a lista da amostra vão no relatório).

**2.3. Prova com extremos reais.** Teste permanente, com cliente de LLM e embedding falsos: (a) item de 34.195 caracteres; (b) texto sintético de 5.000.000 caracteres com marcador único no **último** caractere; (c) cada tarefa das 15 de `llm_routing.yaml` que recebe texto de terceiros. Para cada uma, o marcador chega a pelo menos uma chamada ou a tarefa se recusa em voz alta (erro registrado); jamais passa em silêncio.

**2.4. Relatório de divergências em relação ao 079:** `Achado desta auditoria | Estava no 079? | Estado`. Achado novo vira ponto P-046 em diante, com brief proposto.

## 3. Escopo (arquivos)

Os da linha "Arquivos-alvo".

## 4. Testes

O teste permanente da seção 2.3, parametrizado pelas 15 tarefas (as que não recebem texto de terceiros ficam fora com a razão escrita no teste).

## 5. Fora de escopo

Corrigir achados grandes (viram briefs); reprocessar dados (095).

## 6. Passos e critérios de aceite

Passos: conferir "Depende de"; auditoria cega; escrever lista; **só então** ler o doc_079 e comparar; escrever o teste; relatório; manifesto; PLAN; `scripts/agente_entregar.sh 094`. Aceite: (1) `pytest tests/test_texto_extremo_ponta_a_ponta.py -q` verde; (2) tabela de divergências completa; (3) semente e lista da amostra no relatório; (4) gate verde. Última linha: "Para você: ver se há achados novos (P-046 em diante)".
