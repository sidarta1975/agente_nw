-- 007_pedido — brief 036. Histórico bruto dos pedidos em texto livre. A frase é gravada antes de
-- qualquer outra etapa (por isso `extraido_json` e `confianca` aceitam NULL até a extração terminar).

CREATE TABLE pedido (
  id               INTEGER PRIMARY KEY,
  perfil_id        INTEGER REFERENCES perfil(id),
  texto            TEXT NOT NULL,
  extraido_json    TEXT,
  confianca        REAL,
  contato_criado   INTEGER NOT NULL DEFAULT 0,
  contato_ambiguo  INTEGER NOT NULL DEFAULT 0,
  criado_em        TEXT NOT NULL
);

CREATE INDEX pedido_criado_em ON pedido(criado_em);

INSERT INTO schema_version (versao, aplicada_em) VALUES (7, strftime('%Y-%m-%dT%H:%M:%fZ','now'));
