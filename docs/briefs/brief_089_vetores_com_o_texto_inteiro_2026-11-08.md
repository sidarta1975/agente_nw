# Brief 089 — Vetores calculados com o texto inteiro

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Conjunto:** correção do texto por inteiro (086 a 095)
**Arquivos-alvo:** `agente_nw/agrupamento/agrupador.py` (linha ~88, corte de 2.000 caracteres), `agente_nw/perfil/perfis.py` (linha ~629, centróide do contato), `agente_nw/perfil/configurador.py` (linha ~29, vetor do tema), `agente_nw/perfil/calibracao.py` (`_trecho`, só se for entrada de embedding), a constante de versão de vetor (mecanismo do brief 066), um comando de comparação em simulação na CLI, `tests/test_vetores_texto_inteiro.py` (novo), mais o relatório, o manifesto e o PLAN
**Seções a ler:** relatório 079 (pontos de vetor); seção 2.1 e 7 do relatório do agente_nw em `referencias/relatorios_projetos` (74% dos itens têm texto acima do corte); relatório do trf6 (média ponderada); brief 066 e seu relatório; relatórios dos briefs 082 e 088 (inteiros); AGENTS §4 e §9
**Modelo:** Opus — muda o critério que decide o assunto de cada item
**Esforço:** alto
**Teste de aceite:** `tests/test_vetores_texto_inteiro.py`
**Depende de:** briefs 082 e 088 executados
**Ordem em série:** depois de 082 e 088; antes de 090
**Data:** 2026-11-08

---

## 1. Objetivo em uma frase

Os vetores que decidem o assunto de um item, o perfil de um contato e o tema de um interesse passam a ser calculados com o texto inteiro (via `embeddar_em_partes` do brief 088), e Sidarta vê, em simulação e antes de qualquer gravação, quantos itens mudariam de assunto.

## 2. Decisões (de Sidarta)

**2.1. Usar a peça única do brief 088.** Nenhum corte novo. Item que cabe numa chamada continua com o mesmo vetor de antes, bit a bit; item longo passa a ser a média ponderada das partes.

**2.2. Os três pontos:** (a) vetor do item no agrupador: texto inteiro em vez dos primeiros 2.000 caracteres; (b) centróide do contato: cada texto que entra no centróide entra inteiro; (c) vetor do tema do configurador: hoje só o nome; passa a ser nome + descrição + sinônimos, quando existirem, juntos como um texto. Se `_trecho` de `calibracao.py` for só exibição, fica como está e o relatório diz isso, com a linha que prova.

**2.3. Versão de vetor.** O critério novo ganha versão nova pelo mecanismo do brief 066: vetor de versão antiga continua válido para leitura mas é tratado como ausente quando a etapa pedir vetor atual. **Nenhum vetor existente é regravado por este brief.**

**2.4. Comando de comparação em simulação** (`agente_nw comparar-vetores --amostra N`, sempre sobre cópia do banco, sem gravar): para cada item, calcula o vetor novo e o antigo e informa quantos itens trocariam de assunto, quantos assuntos se fundiriam ou se separariam, quantos itens já republicados mudariam de decisão de publicação. Sem mudar nenhum limiar (a calibração dos limiares é decisão do dono, depois de ver a comparação).

**2.4b. O `comparar-vetores` roda contra a cópia do banco, com o caminho dado explicitamente** (`--banco <caminho da cópia>`, parâmetro obrigatório; a cópia vem do `agente_nw copiar-banco`). A liberação da trava para esse comando vem do **brief 086, item 2.10** — sem ela, a trava pergunta e, numa série sem acompanhamento, isso é recusa.

**2.5. Regravação real só com autorização de Sidarta.** O executor não roda nada no banco real. O comando de gravação, se existir, exige `--confirmo` e recusa o banco real quando executado dentro de uma série.

## 3. Escopo (arquivos)

| Arquivo | O que muda |
|---|---|
| `agrupador.py`, `perfis.py`, `configurador.py` | Chamam `embeddar_em_partes`; sem corte. |
| constante de versão | Versão nova do critério de vetor. |
| `cli.py` | `comparar-vetores` (somente leitura). |
| `tests/test_vetores_texto_inteiro.py` | Seção 4. |

## 4. Testes (embedding falso e banco em `tmp_path`)

1. Texto curto: vetor idêntico ao de antes. 2. Marcador no último caractere de um texto de 20.000 chega a uma chamada de embedding (agrupador e centróide). 3. O vetor do tema inclui descrição e sinônimos. 4. Versão antiga é tratada como ausente onde o brief 066 já faz isso. 5. `comparar-vetores` não escreve no banco (conferir por hash do arquivo antes e depois) e recusa o caminho do banco real. 6. Falha numa parte invalida o vetor do item (nunca parcial) e o item fica sem vetor, não com vetor errado.

## 5. Fora de escopo

Mudar limiares de similaridade; regravar vetores; cartão e qualificação (090); coleta (083).

## 6. Passos e critérios de aceite

Passos: conferir "Depende de"; ler os relatórios 082 e 088; testes; implementar; rodar `comparar-vetores` numa cópia do banco com amostra e colar as contagens no relatório `doc_089_...` (só números), com a resposta a "algum texto é analisado só em parte?" por ponto tocado; manifesto; PLAN; `scripts/agente_entregar.sh 089`. Aceite: (1) `pytest tests/test_vetores_texto_inteiro.py -q` verde; (2) hash do banco inalterado após a comparação (saída colada); (3) gate verde; (4) pontos do 079 correspondentes marcados `CORRIGIDO (brief 089)`. Última linha: "Para você: ver as contagens da comparação e decidir se autoriza regravar os vetores".
