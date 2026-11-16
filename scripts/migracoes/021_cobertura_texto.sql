-- 021_cobertura_texto — brief 088: em quantas partes cada item de `fila_extracao` foi lido.
--
-- `partes_lidas`: 1 = texto inteiro numa chamada; maior que 1 = lido em partes que cobrem o texto todo
-- (`nucleo/texto_integral.py`); NULL = processado antes deste brief, ou ainda não processado. A versão do
-- processamento já tem coluna desde a migração 019 (`gerado_por_prompt_versao`), e o prompt de
-- `extrair_de_texto` subiu de versão neste brief: as duas colunas juntas dizem como o item foi lido.
-- Coluna e não tabela: um item da fila é lido uma vez por processamento, e o reenvio regrava a linha.

ALTER TABLE fila_extracao ADD COLUMN partes_lidas INTEGER NULL;

INSERT INTO schema_version (versao, aplicada_em) VALUES (21, strftime('%Y-%m-%dT%H:%M:%fZ','now'));
