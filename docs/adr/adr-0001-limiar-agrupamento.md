# ADR-0001 — Limiar de agrupamento (cosseno_mesmo_assunto)

Data: 2026-09-19

Valor anterior: 0.82
Valor novo: 0.77

## Composição da amostra

- Pares na banda de dúvida (0.70–0.92) amostrados: 35
- Pares de controle amostrados: 3 de cosseno alto (>0.92), 12 de cosseno baixo (<0.70)
- Pares avaliados com sucesso pelo qwen3:8b: 48
- Erros de JSON inválido (par descartado): 2

## Distribuição dos cossenos da banda de dúvida

mínimo 0.703, máximo 0.863, média 0.763, mediana 0.756

## Revisão humana

Calibração sem revisão humana, por decisão do Sidarta — curadoria real vem de uso real
(aceitar/recusar sugestão de verdade, já previsto em assunto_contato.status), não de rotulagem
sintética. Se a medição real do brief 013 mostrar limiar errado, recalibra com dado de uso real.

## Acurácia do limiar escolhido sobre a amostra

38/48 (79.2%)
