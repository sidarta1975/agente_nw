-- 016_perfil_genero_gramatical — brief 048: gênero gramatical do contato, para a redação concordar
-- certo ("caro"/"cara", "advogado"/"advogada") ao adaptar uma mensagem-molde de outro contato. Inferido
-- pelo sistema a partir do nome, corrigível pelo usuário na ficha; sem certeza, fica "desconhecido" e a
-- redação usa forma neutra.

ALTER TABLE perfil ADD COLUMN genero_gramatical TEXT NOT NULL DEFAULT 'desconhecido'
  CHECK (genero_gramatical IN ('masculino', 'feminino', 'desconhecido'));

INSERT INTO schema_version (versao, aplicada_em) VALUES (16, strftime('%Y-%m-%dT%H:%M:%fZ','now'));
