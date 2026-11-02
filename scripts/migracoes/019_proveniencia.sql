-- 019_proveniencia — brief 066: proveniência do que a IA produziu.
--
-- 1. Registros gerados pelo modelo ganham perfil (air16/pro48), modelo e versão do prompt que os
--    produziram: `gancho_uso` (redação), `assunto` (qualificação e cartão: a mesma linha é escrita por
--    duas tarefas, vale a do último gravador), `assunto_contato` (pontuação de relevância e o "por quê"),
--    `fila_extracao` (item processado) e `fato` (resultado da extração; continua só inserção — as
--    colunas entram no INSERT). Tudo o que já existe nasce NULL: não se reconstrói o passado.
-- 2. Os centróides (`vetor_tema`, `vetor_assunto`, `vetor_perfil`) ganham `modelo_embedding`, coluna
--    auxiliar do vec0. Tabela virtual vec0 não aceita ALTER TABLE e, renomeada, não renomeia as tabelas
--    sombra; por isso: cópia para tabela temporária, DROP, CREATE com a coluna e cópia de volta.
--    Backfill 'bge-m3': os dois perfis de config/llm_routing.yaml sempre usaram esse modelo, e
--    `Roteamento` recusa perfis com modelos de embedding diferentes. O vec0 não impõe o NOT NULL da
--    coluna auxiliar; quem impõe é a assinatura das funções de gravação (parâmetro obrigatório).
--    `vetor_item` fica como está (fora do brief).

ALTER TABLE gancho_uso ADD COLUMN gerado_por_modelo TEXT NULL;
ALTER TABLE gancho_uso ADD COLUMN gerado_por_perfil TEXT NULL;
ALTER TABLE gancho_uso ADD COLUMN gerado_por_prompt_versao TEXT NULL;

ALTER TABLE assunto ADD COLUMN gerado_por_modelo TEXT NULL;
ALTER TABLE assunto ADD COLUMN gerado_por_perfil TEXT NULL;
ALTER TABLE assunto ADD COLUMN gerado_por_prompt_versao TEXT NULL;

ALTER TABLE assunto_contato ADD COLUMN gerado_por_modelo TEXT NULL;
ALTER TABLE assunto_contato ADD COLUMN gerado_por_perfil TEXT NULL;
ALTER TABLE assunto_contato ADD COLUMN gerado_por_prompt_versao TEXT NULL;

ALTER TABLE fila_extracao ADD COLUMN gerado_por_modelo TEXT NULL;
ALTER TABLE fila_extracao ADD COLUMN gerado_por_perfil TEXT NULL;
ALTER TABLE fila_extracao ADD COLUMN gerado_por_prompt_versao TEXT NULL;

ALTER TABLE fato ADD COLUMN gerado_por_modelo TEXT NULL;
ALTER TABLE fato ADD COLUMN gerado_por_perfil TEXT NULL;
ALTER TABLE fato ADD COLUMN gerado_por_prompt_versao TEXT NULL;

CREATE TEMP TABLE _copia_vetor_tema AS SELECT tema_id, embedding FROM vetor_tema;
DROP TABLE vetor_tema;
CREATE VIRTUAL TABLE vetor_tema USING vec0(
  tema_id INTEGER PRIMARY KEY, embedding float[1024], +modelo_embedding TEXT NOT NULL
);
INSERT INTO vetor_tema (tema_id, embedding, modelo_embedding)
  SELECT tema_id, embedding, 'bge-m3' FROM _copia_vetor_tema;
DROP TABLE _copia_vetor_tema;

CREATE TEMP TABLE _copia_vetor_assunto AS SELECT assunto_id, centroide FROM vetor_assunto;
DROP TABLE vetor_assunto;
CREATE VIRTUAL TABLE vetor_assunto USING vec0(
  assunto_id INTEGER PRIMARY KEY, centroide float[1024], +modelo_embedding TEXT NOT NULL
);
INSERT INTO vetor_assunto (assunto_id, centroide, modelo_embedding)
  SELECT assunto_id, centroide, 'bge-m3' FROM _copia_vetor_assunto;
DROP TABLE _copia_vetor_assunto;

CREATE TEMP TABLE _copia_vetor_perfil AS SELECT perfil_id, centroide FROM vetor_perfil;
DROP TABLE vetor_perfil;
CREATE VIRTUAL TABLE vetor_perfil USING vec0(
  perfil_id INTEGER PRIMARY KEY, centroide float[1024], +modelo_embedding TEXT NOT NULL
);
INSERT INTO vetor_perfil (perfil_id, centroide, modelo_embedding)
  SELECT perfil_id, centroide, 'bge-m3' FROM _copia_vetor_perfil;
DROP TABLE _copia_vetor_perfil;

INSERT INTO schema_version (versao, aplicada_em) VALUES (19, strftime('%Y-%m-%dT%H:%M:%fZ','now'));
