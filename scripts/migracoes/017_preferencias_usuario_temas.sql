-- 017_preferencias_usuario_temas — brief 040: perfil do usuário inferido dos pedidos, sem cadastro.
-- `perfil.preferencias_json` guarda o que o usuário disse não lhe interessar
-- ({"nao_me_interessa": [...]}); vira `evitar` implícito em todo pedido (relevancia/cruzamento.py).
-- `tema_uso` registra cada reforço de um tema do usuário (uma linha por pedido que tocou o tema), para
-- calcular o nível por frequência (3 usos em 30 dias, 6 em 90) e a "última menção" na tela Eu, sem
-- reprocessar o histórico de pedidos a cada vez. `perfil_tema.peso_decaido_em` guarda o mês ("AAAA-MM")
-- do último decaimento de peso por inatividade (180 dias sem uso), para o decaimento não aplicar duas
-- vezes no mesmo mês.
--
-- O brief original (2026-10-11) numerava esta migração como "011"; esse número já foi usado pelo brief
-- 039 (`011_pedido_fluxo.sql`). Segue a sequência real do repositório (próximo número livre: 17).

ALTER TABLE perfil ADD COLUMN preferencias_json TEXT NOT NULL DEFAULT '{}';
ALTER TABLE perfil_tema ADD COLUMN peso_decaido_em TEXT;

CREATE TABLE tema_uso (
  id         INTEGER PRIMARY KEY,
  perfil_id  INTEGER NOT NULL REFERENCES perfil(id),
  tema_id    INTEGER NOT NULL REFERENCES tema(id),
  usado_em   TEXT NOT NULL
);

CREATE INDEX tema_uso_perfil_tema ON tema_uso(perfil_id, tema_id, usado_em);

INSERT INTO schema_version (versao, aplicada_em) VALUES (17, strftime('%Y-%m-%dT%H:%M:%fZ','now'));
