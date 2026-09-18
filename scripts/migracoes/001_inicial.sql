-- 001_inicial — Etapa 1. Aplicado por agente_nw.nucleo.database.migracoes dentro de uma transação.
CREATE TABLE schema_version (
  versao      INTEGER PRIMARY KEY,
  aplicada_em TEXT NOT NULL
);

CREATE TABLE tema (
  id         INTEGER PRIMARY KEY,
  nome       TEXT NOT NULL UNIQUE,
  descricao  TEXT NOT NULL,
  sinonimos  TEXT NOT NULL DEFAULT '[]',        -- JSON: lista de strings
  criado_em  TEXT NOT NULL
);

CREATE TABLE perfil (
  id            INTEGER PRIMARY KEY,
  tipo          TEXT NOT NULL CHECK (tipo IN ('usuario','contato')),
  nome          TEXT NOT NULL,
  apelido       TEXT,
  email         TEXT,
  telefone      TEXT,                            -- E.164; chave de identidade entre fontes
  empresa       TEXT,
  cargo         TEXT,
  setor         TEXT,
  cidade        TEXT,
  naturalidade  TEXT,
  linguas       TEXT NOT NULL DEFAULT '[]',      -- JSON
  formacao      TEXT,
  tem_filhos    INTEGER,                         -- NULL desconhecido, 0/1
  faixa_etaria  TEXT,
  notas         TEXT,
  ativo         INTEGER NOT NULL DEFAULT 0,
  gerar_agora   INTEGER NOT NULL DEFAULT 0,
  ultima_coleta TEXT,
  criado_em     TEXT NOT NULL,
  atualizado_em TEXT NOT NULL
);
CREATE UNIQUE INDEX perfil_telefone ON perfil(telefone) WHERE telefone IS NOT NULL;
CREATE INDEX perfil_email ON perfil(email) WHERE email IS NOT NULL;
CREATE UNIQUE INDEX perfil_usuario_unico ON perfil(tipo) WHERE tipo = 'usuario';

CREATE TABLE perfil_tema (
  perfil_id     INTEGER NOT NULL REFERENCES perfil(id),
  tema_id       INTEGER NOT NULL REFERENCES tema(id),
  peso          INTEGER NOT NULL DEFAULT 3 CHECK (peso BETWEEN 1 AND 5),
  origem        TEXT NOT NULL CHECK (origem IN ('declarada','sugerida','importada','captura','imagem','conversa')),
  confirmado    INTEGER NOT NULL DEFAULT 0,
  nivel         TEXT CHECK (nivel IN ('dominio','interesse','curiosidade')),  -- só no perfil do usuário
  registrado_em TEXT NOT NULL,
  UNIQUE (perfil_id, tema_id)
);

CREATE TABLE fonte (
  id             INTEGER PRIMARY KEY,
  nome           TEXT NOT NULL,
  url_feed       TEXT NOT NULL UNIQUE,
  dominio        TEXT NOT NULL,
  tipo           TEXT NOT NULL,                  -- veiculo | blog | oficial | agregador
  confiabilidade INTEGER NOT NULL DEFAULT 5 CHECK (confiabilidade BETWEEN 0 AND 10),
  ativa          INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE assunto (
  id                     INTEGER PRIMARY KEY,
  titulo_gerado          TEXT,
  primeiro_visto         TEXT NOT NULL,
  ultimo_visto           TEXT NOT NULL,
  n_itens                INTEGER NOT NULL DEFAULT 0,
  n_fontes_independentes INTEGER NOT NULL DEFAULT 0,
  status                 TEXT NOT NULL CHECK (status IN ('novo','em_curso','encerrado')),
  temas                  TEXT NOT NULL DEFAULT '[]',   -- JSON: ids de tema
  substancial            REAL,
  conversavel            REAL,
  justificativa          TEXT,
  resumo_cartao          TEXT                          -- JSON do contrato cartao
);

CREATE TABLE item (
  id           INTEGER PRIMARY KEY,
  fonte_id     INTEGER NOT NULL REFERENCES fonte(id),
  url_canonica TEXT NOT NULL UNIQUE,
  titulo       TEXT NOT NULL,
  texto        TEXT,                                   -- vive 90 dias
  publicado_em TEXT,
  coletado_em  TEXT NOT NULL,
  hash_titulo  TEXT NOT NULL,
  assunto_id   INTEGER REFERENCES assunto(id)
);
CREATE INDEX item_hash ON item(hash_titulo);
CREATE INDEX item_assunto ON item(assunto_id);

CREATE TABLE assunto_contato (
  id                INTEGER PRIMARY KEY,
  assunto_id        INTEGER NOT NULL REFERENCES assunto(id),
  perfil_id         INTEGER NOT NULL REFERENCES perfil(id),
  gerado_em         TEXT NOT NULL,                     -- data do ciclo, AAAA-MM-DD
  tipo              TEXT NOT NULL CHECK (tipo IN ('conector','viavel_com_esforco','fora_do_dominio')),
  aderencia_contato REAL NOT NULL,
  aderencia_usuario REAL NOT NULL,
  conversavel       REAL NOT NULL,
  score             REAL NOT NULL,
  por_que           TEXT,
  status            TEXT NOT NULL CHECK (status IN ('novo','usado','nao_serve','descartado')),
  motivo            TEXT,
  UNIQUE (assunto_id, perfil_id, gerado_em)
);

CREATE TABLE fato (
  id            INTEGER PRIMARY KEY,
  perfil_id     INTEGER NOT NULL REFERENCES perfil(id),
  data_do_fato  TEXT,
  tipo          TEXT NOT NULL,
  conteudo      TEXT NOT NULL,
  fonte         TEXT,
  registrado_em TEXT NOT NULL
);
CREATE TRIGGER fato_sem_update BEFORE UPDATE ON fato BEGIN SELECT RAISE(ABORT, 'fato é só inserção'); END;
CREATE TRIGGER fato_sem_delete BEFORE DELETE ON fato BEGIN SELECT RAISE(ABORT, 'fato é só inserção'); END;

CREATE TABLE fila_extracao (
  id         INTEGER PRIMARY KEY,
  perfil_id  INTEGER NOT NULL REFERENCES perfil(id),
  texto      TEXT NOT NULL,
  origem     TEXT NOT NULL,                            -- cadastro | notas_agenda | colado | captura
  criado_em  TEXT NOT NULL,
  processado INTEGER NOT NULL DEFAULT 0,
  erro       TEXT
);

CREATE TABLE descarte_sensivel (
  id            INTEGER PRIMARY KEY,
  perfil_id     INTEGER,
  origem_texto  TEXT NOT NULL,
  categoria     TEXT NOT NULL,                         -- nunca o trecho, nunca o termo
  registrado_em TEXT NOT NULL
);

CREATE TABLE fila_revisao (
  id        INTEGER PRIMARY KEY,
  tarefa    TEXT NOT NULL,
  entrada   TEXT NOT NULL,
  erro      TEXT NOT NULL,
  criado_em TEXT NOT NULL,
  resolvido INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE progresso (
  etapa         TEXT PRIMARY KEY,                     -- coleta | embeddings | agrupamento | ...
  ultimo_id     INTEGER,
  data_ciclo    TEXT,
  atualizado_em TEXT NOT NULL
);

-- Vetores (sqlite-vec). bge-m3 = 1024 dimensões.
CREATE VIRTUAL TABLE vetor_tema    USING vec0(tema_id    INTEGER PRIMARY KEY, embedding float[1024]);
CREATE VIRTUAL TABLE vetor_item    USING vec0(item_id    INTEGER PRIMARY KEY, embedding float[1024]);
CREATE VIRTUAL TABLE vetor_assunto USING vec0(assunto_id INTEGER PRIMARY KEY, centroide float[1024]);
CREATE VIRTUAL TABLE vetor_perfil  USING vec0(perfil_id  INTEGER PRIMARY KEY, centroide float[1024]);

INSERT INTO schema_version (versao, aplicada_em) VALUES (1, strftime('%Y-%m-%dT%H:%M:%fZ','now'));
