# Brief NNN — título curto

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Conjunto:** nome do conjunto de briefs, ou "nenhum (brief isolado, direto na `main`)"
**Arquivos-alvo:** lista de caminhos que o brief cria ou altera; nada fora dela
**Seções a ler:** seções do PLANO e da ARQUITETURA, e números das armadilhas do PLAN da área tocada (as armadilhas não são leitura obrigatória; sem citação, o executor busca no PLAN o nome do módulo que vai editar)
**Modelo:** Sonnet | Opus
**Esforço:** baixo | médio | alto
**Teste de aceite:** arquivo ou comando que prova o critério; havendo teste, o executor o cria antes do código
**Depende de:** brief, commit ou ação de Sidarta que precisa existir antes; o executor confere literalmente e, se faltar, para
**Data:** AAAA-MM-DD

---

## 1. Objetivo em uma frase

Uma frase: o que muda para o usuário ou para o sistema.

## 2. Decisões

Decisões já tomadas por Sidarta que o executor não reabre. Cada uma com a razão em uma linha.

## 3. Escopo (arquivos)

| Arquivo | Criar / alterar | O que muda |
|---|---|---|

## 4. Testes

Casos de teste com entrada e resultado esperado. Teste que chama Ollama ou rede real usa banco isolado (`conexao.abrir(tmp_path/...)`), nunca `container.banco()`.

## 5. Fora de escopo

O que fica para outro brief, cada item com o número do brief ou "sem número".

## 6. Passos de execução

1. Conferir a seção "Depende de".
2. Escrever os testes (seção 4).
3. Implementar (seção 3).
4. Escrever o relatório em `docs/docs/doc_NNN_<slug>_<data>.md` e a mensagem do commit em `logs/commit_NNN.txt`.

O executor não roda `git` nem a suíte (`scripts/verificar.sh`); Sidarta roda.

## 7. Critérios de aceite

Cada critério verificável por comando, com a saída colada no relatório. Sem saída colada, não se escreve que passou.
