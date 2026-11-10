# Brief 093 — Guarda permanente: o gate acusa todo corte novo de texto

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Conjunto:** correção do texto por inteiro (086 a 095)
**Arquivos-alvo:** `tests/test_sem_corte_de_texto.py` (novo, teste estático), `docs/EXCECOES_TEXTO_INTEGRAL.md` (tabela de cortes não analíticos, só por brief de Sidarta — este é um deles), testes existentes que fixam cortes como corretos, `scripts/verificar_auditoria_texto.py` (se precisar ler a nova tabela), mais o relatório, o manifesto e o PLAN
**Seções a ler:** relatório 079 inteiro (principalmente a seção 4, cortes não analíticos); `docs/EXCECOES_TEXTO_INTEGRAL.md`; relatórios do lex_hub e do trf6 em `referencias/relatorios_projetos` (teste estático de fatiamento); AGENTS §4
**Modelo:** Opus
**Esforço:** alto
**Teste de aceite:** `tests/test_sem_corte_de_texto.py`
**Depende de:** brief 092 executado
**Ordem em série:** depois de 092; antes de 094
**Data:** 2026-11-08

---

## 1. Objetivo em uma frase

Depois deste brief, ninguém (nem eu, nem o Claude Code) consegue entregar um corte novo de texto sem que o gate de `agente_entregar.sh` pare.

## 2. Decisões (de Sidarta)

**2.1. Teste estático.** Percorre o código de produção (`agente_nw/`), por AST, e acusa fatiamento (`[:N]`, `[-N:]`, `[a:b]` de string), `textwrap.shorten`, `truncate`, `.split()[:N]`, `head`/`limit` de listas de texto e `max_chars`/`max_len` aplicados a conteúdo de terceiros.

**2.2. Chave estável** do achado: `arquivo + texto normalizado da linha` (sem número de linha), para o teste não quebrar a cada edição.

**2.3. Três estados possíveis para cada achado:** (a) **exceção aprovada**: consta no registro `EXCECOES_TEXTO_INTEGRAL.md` com valor e condição; (b) **corte não analítico** (nome de arquivo, id, rótulo curto, log): consta na tabela de cortes não analíticos, copiada da seção 4 do relatório 079; (c) **violação conhecida pendente**: consta numa lista no próprio teste, com o P-id e o brief que vai corrigir. Achado fora dos três estados falha o teste. Violação (c) cujo brief já foi entregue também falha.

**2.4. Testes antigos que fixam cortes como corretos** (por exemplo, afirmam que o resultado tem 300 caracteres) são reescritos para afirmar o comportamento novo; cada reescrita é listada no relatório.

**2.5. O registro ganha a tabela de cortes não analíticos.** É Sidarta quem aprova este brief e, com ele, essa tabela.

## 3. Escopo (arquivos)

Os da linha "Arquivos-alvo". Código de produção não muda neste brief.

## 4. Testes

O próprio teste estático (roda no gate) mais testes do teste: arquivo sintético com fatiamento novo → acusa; com fatiamento em exceção aprovada → passa; fatiamento não analítico → passa; violação pendente com brief entregue → falha.

## 5. Fora de escopo

Corrigir cortes (0xx anteriores); auditoria independente (094).

## 6. Passos e critérios de aceite

Passos: conferir "Depende de"; escrever o teste; rodar e classificar cada achado nos três estados; reescrever testes antigos; relatório `doc_093_...` com contagem por estado e a resposta a "algum texto é analisado só em parte?"; manifesto; PLAN; `scripts/agente_entregar.sh 093`. Aceite: (1) `pytest tests/test_sem_corte_de_texto.py -q` verde, saída colada; (2) inserir temporariamente `x[:100]` em um arquivo de produção faz o gate falhar (prova colada, depois desfeita e o arquivo conferido limpo); (3) lista (c) vazia ou só com pontos cujo brief ainda não foi entregue; (4) gate verde.
