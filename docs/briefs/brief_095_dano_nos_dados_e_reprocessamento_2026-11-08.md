# Brief 095 — Dano nos dados já gravados e reprocessamento

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Conjunto:** correção do texto por inteiro (086 a 095) — último
**Arquivos-alvo:** `agente_nw/cli.py` (comandos `medir-dano` e `reprocessar`), `agente_nw/manutencao/reprocessamento.py` (novo), `tests/test_reprocessamento.py` (novo), `docs/docs/doc_095_...md`, mais o manifesto e o PLAN
**Seções a ler:** seção 2.1 do relatório do agente_nw em `referencias/relatorios_projetos` (medições feitas em 25/10); relatórios 087, 088, 089 e 090; relatórios do sergio e do cervello (coluna de cobertura); AGENTS §4 (dado externo, privacidade), §6 e §9
**Modelo:** Opus
**Esforço:** médio
**Teste de aceite:** `tests/test_reprocessamento.py`
**Depende de:** brief 094 executado
**Ordem em série:** depois de 094 (último do conjunto)
**Data:** 2026-11-08

---

## 1. Objetivo em uma frase

Medir quanto do que está gravado no banco foi produzido sob o critério antigo (texto cortado) e preparar o reprocessamento, que só grava por decisão de Sidarta.

## 2. Decisões (de Sidarta)

**2.1. `medir-dano` é somente leitura e roda sobre cópia do banco.** Informa **contagens**: itens com texto acima dos cortes antigos, cartões, ganchos, fatos e vetores produzidos sob versão antiga de prompt/critério, itens sem registro de cobertura, itens na fila de revisão. Nenhum texto de terceiros aparece na saída.

**2.2. `reprocessar` roda em modo simulação por padrão:** calcula o resultado novo, grava em tabela/arquivo à parte, e informa quantos itens mudariam (decisão de assunto, cartão, gancho). Gravar no banco real exige `--confirmo` e o comando **recusa gravar** quando chamado dentro de uma série (variável de ambiente que o `executar_serie.sh` define) ou contra o banco real sem autorização escrita no PLAN ("autorizado por Sidarta em AAAA-MM-DD").

**2.2b. `medir-dano` e `reprocessar` rodam contra a cópia do banco, com o caminho dado explicitamente** (`--banco <caminho da cópia>`, parâmetro obrigatório; a cópia vem do `agente_nw copiar-banco`). A liberação da trava para os dois — e, no caso do `reprocessar`, só com `--simular` e sem `--confirmo` — vem do **brief 086, item 2.10**; sem ela, a trava pergunta e, numa série sem acompanhamento, isso é recusa.

**2.3. Decisão sobre o texto bruto de rede social.** Hoje o texto bruto não é guardado, então a perda na entrada é irreversível: só se reprocessa o que está guardado. O relatório analisa, em uma página, **guardar ou não o texto bruto daqui para frente**: ganho (reprocessar sem recoletar), custo e risco de privacidade (texto de terceiros em disco). Não implementa; abre decisão do dono.

**2.4. Ordem de reprocessamento sugerida** (só proposta no relatório): vetores (089), resumos e cartões (090), ganchos. Cada etapa com sua comparação e sua autorização.

## 3. Escopo (arquivos)

Os da linha "Arquivos-alvo". Nenhum dado é alterado por este brief.

## 4. Testes (banco em `tmp_path`, LLM e embedding falsos)

1. `medir-dano` conta corretamente em banco sintético com itens de versões diferentes. 2. Saída sem nenhum trecho de texto de terceiros. 3. `reprocessar` em simulação não altera o banco (hash antes e depois). 4. `reprocessar --confirmo` com a variável de série ligada é recusado. 5. `reprocessar --confirmo` sem autorização no PLAN é recusado. 6. Banco real (caminho de `config`) recusado nos testes.

## 5. Fora de escopo

Gravar qualquer coisa no banco real; implementar a guarda do texto bruto; recoletar fontes.

## 6. Passos e critérios de aceite

Passos: conferir "Depende de"; testes; implementar; rodar `medir-dano` em cópia do banco e colar as contagens; relatório com a análise 2.3 e a resposta a "algum texto é analisado só em parte?"; manifesto; PLAN; `scripts/agente_entregar.sh 095`. Aceite: (1) `pytest tests/test_reprocessamento.py -q` verde; (2) hash do banco inalterado após `medir-dano` e `reprocessar` em simulação; (3) gate verde. Última linha: "Para você: decidir (a) regravar vetores, (b) regravar cartões, (c) guardar ou não o texto bruto de rede social".
