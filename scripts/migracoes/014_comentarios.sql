-- 014_comentarios — brief 050. Texto livre do usuário: comentário em cada mensagem entregue
-- (`gancho_uso.comentario`) e nota sobre o contato ou sobre um pedido (`nota_contato`, só inserção).
-- A nota vira contexto da próxima redação para o contato; nada é classificado nem pontuado.

ALTER TABLE gancho_uso ADD COLUMN comentario TEXT;

CREATE TABLE nota_contato (
  id         INTEGER PRIMARY KEY,
  perfil_id  INTEGER NOT NULL REFERENCES perfil(id),
  pedido_id  INTEGER REFERENCES pedido(id),
  texto      TEXT NOT NULL CHECK (length(trim(texto)) > 0),
  criado_em  TEXT NOT NULL
);

CREATE INDEX nota_contato_perfil ON nota_contato(perfil_id, criado_em DESC);

INSERT INTO schema_version (versao, aplicada_em) VALUES (14, strftime('%Y-%m-%dT%H:%M:%fZ','now'));
