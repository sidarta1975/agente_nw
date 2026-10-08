-- 005_perfil_id_reatribuivel — brief 025. Ajuste cirúrgico dos gatilhos de
-- imutabilidade de `fato` e `consulta_contato` para permitir exclusivamente
-- a reatribuição da coluna `perfil_id` (necessária para unir dois contatos
-- duplicados sem perder histórico). Nenhuma outra coluna dessas tabelas
-- passa a ser alterável — os novos gatilhos usam `BEFORE UPDATE OF <colunas>`
-- listando explicitamente todas as demais colunas.

DROP TRIGGER fato_sem_update;
CREATE TRIGGER fato_sem_update
  BEFORE UPDATE OF id, data_do_fato, tipo, conteudo, fonte, registrado_em ON fato
  BEGIN SELECT RAISE(ABORT, 'fato é só inserção'); END;

DROP TRIGGER consulta_contato_sem_update;
CREATE TRIGGER consulta_contato_sem_update
  BEFORE UPDATE OF id, criado_em, contexto_json, resumo_redes_sociais, assuntos_entregues_json
  ON consulta_contato
  BEGIN SELECT RAISE(ABORT, 'consulta_contato é só inserção'); END;

INSERT INTO schema_version (versao, aplicada_em) VALUES (5, strftime('%Y-%m-%dT%H:%M:%fZ','now'));
