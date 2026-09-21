-- 004_consulta_contato — histórico permanente por contato. Só inserção,
-- imutável no banco, mesmo padrão da tabela fato. Cada linha registra uma
-- consulta sob demanda: contexto usado, o que foi lido em rede social e o
-- menu de assuntos entregue.
CREATE TABLE consulta_contato (
  id                      INTEGER PRIMARY KEY,
  perfil_id               INTEGER NOT NULL REFERENCES perfil(id),
  criado_em               TEXT NOT NULL,
  contexto_json           TEXT NOT NULL,                 -- ContextoConsulta serializado
  resumo_redes_sociais    TEXT,                          -- texto do que foi lido em rede social, ou NULL
  assuntos_entregues_json TEXT NOT NULL                  -- menu de assuntos daquela consulta, serializado
);
CREATE INDEX consulta_contato_perfil ON consulta_contato(perfil_id, criado_em DESC);

CREATE TRIGGER consulta_contato_sem_update BEFORE UPDATE ON consulta_contato BEGIN SELECT RAISE(ABORT, 'consulta_contato é só inserção'); END;
CREATE TRIGGER consulta_contato_sem_delete BEFORE DELETE ON consulta_contato BEGIN SELECT RAISE(ABORT, 'consulta_contato é só inserção'); END;

INSERT INTO schema_version (versao, aplicada_em) VALUES (4, strftime('%Y-%m-%dT%H:%M:%fZ','now'));
