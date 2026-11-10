# Brief 092 — Pequenos ajustes de texto por inteiro

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Conjunto:** correção do texto por inteiro (086 a 095)
**Arquivos-alvo:** os de cada item da seção 2 (o executor localiza pelo número P-xxx no relatório 079), `tests/test_pequenos_ajustes_texto.py` (novo), mais o relatório, o manifesto e o PLAN
**Seções a ler:** relatório 079 (pontos P-005, P-009, P-015, P-018, P-020, P-021, P-032, P-035, P-036, P-044) e `docs/EXCECOES_TEXTO_INTEGRAL.md` (o que o brief 080 já registrou); relatórios 083 e 087
**Modelo:** Sonnet
**Esforço:** médio
**Teste de aceite:** `tests/test_pequenos_ajustes_texto.py`
**Depende de:** briefs 083 e 087 executados
**Ordem em série:** depois de 083 e 087; antes de 093
**Data:** 2026-11-08

---

## 1. Objetivo em uma frase

Fechar os pontos pequenos da auditoria que não pedem a divisão em partes, cada um com seu teste.

## 2. Itens (cada um é uma correção mínima)

1. **P-032** — descarte de ganchos fica visível (conta e motivo na tela/saída), sem mudar o que é descartado.
2. **P-035** — filtrar contatos por semelhança de nome **antes** de montar o prompt do pedido, de modo que a lista enviada ao modelo traga todos os contatos candidatos e não uma fatia arbitrária.
3. **P-036** — `aplicar_declaracoes` mostra a frase que foi ignorada, em vez de ignorá-la em silêncio.
4. **P-005 / P-015** — quando a coleta ou a leitura de rede social para por teto, a tela avisa (quantos itens ficaram de fora e por quê).
5. **P-020** — a confirmação de identidade mostra o cabeçalho inteiro, não o corte.
6. **P-044** — `csv.field_size_limit` ajustado na leitura da agenda, para campo longo não derrubar a leitura.
7. **P-009** — medir quantos dos 10 candidatos passam o gate; só medir e registrar o número no relatório.
8. **P-021** — teto de 200 na deduplicação: registrar a condição de validade do brief 080 e, se o teto for atingido, avisar.
9. **P-018** — descrição de imagem com texto legível passa a ter limite maior (valor proposto no relatório; vale após aprovação do dono, sem aprovação o item vira lacuna "decisão").

Se algum item já foi resolvido por 081 ou 083, o executor o marca `JÁ RESOLVIDO (brief N)` e passa ao seguinte.

## 3. Regras

Nenhum corte novo. Item que mexe em comportamento visível a Sidarta (3, 4, 5) só acrescenta aviso. Itens de decisão (9 sem aprovação) não são decididos aqui.

## 4. Testes

Um teste por item (1 a 8), com banco em `tmp_path` e LLM falso. Item 2: contato com nome parecido fora das 10 primeiras chega ao prompt. Item 3: frase ignorada aparece na saída. Item 6: campo de 300.000 caracteres lido sem erro.

## 5. Fora de escopo

Qualquer mudança que precise de divisão em partes (088), vetores (089), cartão (090).

## 6. Passos e critérios de aceite

Passos: conferir "Depende de"; testes; implementar item por item; relatório `doc_092_...` com a tabela `Ponto | Resolvido / já resolvido / lacuna | Teste` e a resposta a "algum texto é analisado só em parte?"; manifesto; PLAN; `scripts/agente_entregar.sh 092`. Aceite: (1) `pytest tests/test_pequenos_ajustes_texto.py -q` verde; (2) tabela completa no relatório; (3) gate verde; (4) pontos do 079 atualizados.
