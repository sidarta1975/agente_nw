-- 013_gancho_uso_sem_assunto — brief 047. A mensagem base nasce da pessoa e do objetivo, sem notícia:
-- `assunto_id` passa a aceitar nulo para ela ter `usei`/`não serve` como os demais ganchos. Uma só
-- mensagem base por consulta (índice parcial). Reconstrução da tabela porque o SQLite não tira NOT NULL.

CREATE TABLE gancho_uso_nova (
  id             INTEGER PRIMARY KEY,
  consulta_id    INTEGER NOT NULL REFERENCES consulta_contato(id),
  assunto_id     INTEGER REFERENCES assunto(id),
  status         TEXT NOT NULL CHECK (status IN ('entregue', 'usado', 'nao_serve')),
  gancho_json    TEXT NOT NULL,
  atualizado_em  TEXT NOT NULL,
  UNIQUE (consulta_id, assunto_id)
);

INSERT INTO gancho_uso_nova (id, consulta_id, assunto_id, status, gancho_json, atualizado_em)
  SELECT id, consulta_id, assunto_id, status, gancho_json, atualizado_em FROM gancho_uso;

DROP TABLE gancho_uso;
ALTER TABLE gancho_uso_nova RENAME TO gancho_uso;

CREATE INDEX gancho_uso_consulta ON gancho_uso(consulta_id);
CREATE INDEX gancho_uso_assunto ON gancho_uso(assunto_id, status);
CREATE UNIQUE INDEX gancho_uso_base ON gancho_uso(consulta_id) WHERE assunto_id IS NULL;

INSERT INTO schema_version (versao, aplicada_em) VALUES (13, strftime('%Y-%m-%dT%H:%M:%fZ','now'));
