-- 009_gancho_uso — brief 038. Um gancho redigido por consulta e assunto, com o texto entregue e o
-- que o usuário fez com ele. `consulta_contato` é só inserção (gatilhos da 004), por isso a redação
-- vive aqui: `gancho_json` guarda o gancho inteiro, `status` muda quando o usuário usa ou descarta.

CREATE TABLE gancho_uso (
  id             INTEGER PRIMARY KEY,
  consulta_id    INTEGER NOT NULL REFERENCES consulta_contato(id),
  assunto_id     INTEGER NOT NULL REFERENCES assunto(id),
  status         TEXT NOT NULL CHECK (status IN ('entregue', 'usado', 'nao_serve')),
  gancho_json    TEXT NOT NULL,
  atualizado_em  TEXT NOT NULL,
  UNIQUE (consulta_id, assunto_id)
);

CREATE INDEX gancho_uso_consulta ON gancho_uso(consulta_id);
CREATE INDEX gancho_uso_assunto ON gancho_uso(assunto_id, status);

INSERT INTO schema_version (versao, aplicada_em) VALUES (9, strftime('%Y-%m-%dT%H:%M:%fZ','now'));
