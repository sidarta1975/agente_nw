-- 015_conversa_whatsapp — brief 061. Mensagens importadas de uma exportação do WhatsApp (zip ou txt):
-- fonte de fatos sobre o contato (fila_extracao) e de tom para a redação. O arquivo enviado não é
-- gravado, só o texto das mensagens. UNIQUE(perfil_id, hash) evita duplicar mensagem já importada.

CREATE TABLE conversa_mensagem (
  id           INTEGER PRIMARY KEY,
  perfil_id    INTEGER NOT NULL REFERENCES perfil(id),
  autor        TEXT NOT NULL CHECK (autor IN ('contato', 'usuario')),
  enviada_em   TEXT NOT NULL,
  texto        TEXT NOT NULL,
  hash         TEXT NOT NULL,
  importada_em TEXT NOT NULL,
  UNIQUE (perfil_id, hash)
);

CREATE INDEX conversa_mensagem_perfil ON conversa_mensagem(perfil_id, enviada_em);

INSERT INTO schema_version (versao, aplicada_em) VALUES (15, strftime('%Y-%m-%dT%H:%M:%fZ','now'));
