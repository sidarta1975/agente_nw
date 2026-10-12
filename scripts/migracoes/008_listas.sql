-- 008_listas — brief 037. Cache local das listas do próprio usuário nas redes sociais
-- (conexões do LinkedIn, seguidos no Instagram e no X, amigos do Facebook).
-- `perfil_id` aponta para o contato quando o usuário confirma que aquela entrada é ele.

CREATE TABLE lista_rede_social (
  id               INTEGER PRIMARY KEY,
  rede             TEXT NOT NULL,
  nome             TEXT NOT NULL,
  nome_normalizado TEXT NOT NULL,   -- sem acento e sem caixa, para busca
  cabecalho        TEXT NOT NULL DEFAULT '',
  link             TEXT NOT NULL UNIQUE,
  foto_url         TEXT,
  lido_em          TEXT NOT NULL,
  perfil_id        INTEGER REFERENCES perfil(id)
);

CREATE INDEX lista_rede_social_rede ON lista_rede_social(rede);
CREATE INDEX lista_rede_social_nome ON lista_rede_social(nome_normalizado);

INSERT INTO schema_version (versao, aplicada_em) VALUES (8, strftime('%Y-%m-%dT%H:%M:%fZ','now'));
