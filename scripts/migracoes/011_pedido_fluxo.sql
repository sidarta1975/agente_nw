-- 011_pedido_fluxo — brief 039 (tela única). O pedido passa a ter um andamento: o console grava o
-- pedido e responde na hora; o trabalho roda por trás e atualiza `status` e `etapa`. `localizacao_json`
-- guarda as perguntas "é esta pessoa?" que esperam o usuário; `consulta_id` liga o pedido à consulta e
-- aos ganchos; `pedido_pai_id` liga a correção em texto ao pedido que ela corrige.

ALTER TABLE pedido ADD COLUMN status TEXT NOT NULL DEFAULT 'concluido'
  CHECK (status IN ('na_fila', 'processando', 'aguardando_pessoa', 'concluido', 'erro'));
ALTER TABLE pedido ADD COLUMN etapa TEXT;
ALTER TABLE pedido ADD COLUMN erro TEXT;
ALTER TABLE pedido ADD COLUMN avisos_json TEXT;
ALTER TABLE pedido ADD COLUMN pedido_pai_id INTEGER REFERENCES pedido(id);
ALTER TABLE pedido ADD COLUMN consulta_id INTEGER REFERENCES consulta_contato(id);
ALTER TABLE pedido ADD COLUMN localizacao_json TEXT;

CREATE INDEX pedido_perfil ON pedido(perfil_id, criado_em);

INSERT INTO schema_version (versao, aplicada_em) VALUES (11, strftime('%Y-%m-%dT%H:%M:%fZ','now'));
