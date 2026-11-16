-- 020_fila_revisao_destino — brief 087: destino do que foi para a fila de revisão.
--
-- Quatro pontos do código inserem em `fila_revisao` e nenhum a resolvia. Três colunas dizem o que
-- aconteceu com o item: `resolvido_em` (quando), `resolucao` ('descartado', 'reenviado_ok' ou
-- 'reenviado_falhou') e `motivo` (por que Sidarta descartou). `reenviado_falhou` deixa `resolvido`
-- em 0: o item continua na fila. Os itens que já existem ficam com as três colunas vazias.

ALTER TABLE fila_revisao ADD COLUMN resolvido_em TEXT NULL;
ALTER TABLE fila_revisao ADD COLUMN resolucao TEXT NULL;
ALTER TABLE fila_revisao ADD COLUMN motivo TEXT NULL;

INSERT INTO schema_version (versao, aplicada_em) VALUES (20, strftime('%Y-%m-%dT%H:%M:%fZ','now'));
