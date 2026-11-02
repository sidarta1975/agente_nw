-- 018_molde_rastreio — brief 065: rastro de proveniência do molde. Quando uma mensagem é redigida a
-- partir de uma mensagem-molde de outro contato (brief 048), a linha nova de `gancho_uso` grava o `id`
-- do molde usado. Não muda a seleção de moldes (`consulta_contato.moldes_por_contexto`) — só permite,
-- depois, contar quantos passos separam uma mensagem de outra efetivamente `usado` (066, medição do 042).
-- Nasce NULL para tudo que já existe.

ALTER TABLE gancho_uso ADD COLUMN molde_origem_id INTEGER NULL REFERENCES gancho_uso(id);

INSERT INTO schema_version (versao, aplicada_em) VALUES (18, strftime('%Y-%m-%dT%H:%M:%fZ','now'));
