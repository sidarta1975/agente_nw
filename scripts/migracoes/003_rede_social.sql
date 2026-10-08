-- 003_rede_social — cadastro de redes sociais por perfil. Um perfil pode ter zero, uma ou várias.
CREATE TABLE rede_social (
  id        INTEGER PRIMARY KEY,
  perfil_id INTEGER NOT NULL REFERENCES perfil(id),
  rede      TEXT NOT NULL,                                  -- texto curto livre: instagram | linkedin | facebook | x | outro | ...
  link      TEXT NOT NULL,
  criado_em TEXT NOT NULL
);
CREATE INDEX rede_social_perfil ON rede_social(perfil_id);

INSERT INTO schema_version (versao, aplicada_em) VALUES (3, strftime('%Y-%m-%dT%H:%M:%fZ','now'));
