-- 010_rede_sem_perfil — curadoria dos perfis. Quando o usuário declara que o contato não tem conta
-- numa rede, a decisão fica registrada e o programa não procura mais ali. Sai quando um perfil é
-- gravado nessa rede.

CREATE TABLE rede_sem_perfil (
  perfil_id    INTEGER NOT NULL REFERENCES perfil(id),
  rede         TEXT NOT NULL,
  declarado_em TEXT NOT NULL,
  PRIMARY KEY (perfil_id, rede)
);

INSERT INTO schema_version (versao, aplicada_em) VALUES (10, strftime('%Y-%m-%dT%H:%M:%fZ','now'));
