-- 002_coleta_historico — Etapa 1. Histórico de execução por fonte, para o alerta de feed vazio.
CREATE TABLE fonte_execucao (
  fonte_id      INTEGER NOT NULL REFERENCES fonte(id),
  data          TEXT NOT NULL,
  n_itens_novos INTEGER NOT NULL,
  PRIMARY KEY (fonte_id, data)
);

INSERT INTO schema_version (versao, aplicada_em) VALUES (2, strftime('%Y-%m-%dT%H:%M:%fZ','now'));
