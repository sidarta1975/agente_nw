-- 006_aderencia_consulta — brief 034. Instrumentação para calibrar `consulta_minima`:
-- o cosseno entre o assunto e o centroide da consulta passa a ser gravado em cada linha
-- gerada pelo caminho por consulta. NULL nas linhas geradas pelo caminho antigo.

ALTER TABLE assunto_contato ADD COLUMN aderencia_consulta REAL;

INSERT INTO schema_version (versao, aplicada_em) VALUES (6, strftime('%Y-%m-%dT%H:%M:%fZ','now'));
