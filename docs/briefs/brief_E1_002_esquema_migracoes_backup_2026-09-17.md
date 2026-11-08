# brief_E1_002_esquema_migracoes_backup — Esquema da Etapa 1, migrações numeradas, WAL, backup e importação dos temas

**Data:** 17 de setembro de 2026
**Etapa:** 1 (MVP), brief 002 de 14 — dia 3 (qua 23/09/2026)
**Executor:** Claude Code
**Repositório:** `/Users/sidarta48/github/agente_nw`
**Leia antes, nesta ordem:** `AGENTS.md` → `docs/PLANO.md` → `docs/ARQUITETURA.md` → `docs/PLAN.md` → este brief → `config/container.py` e `agente_nw/cli.py` do brief 001
**Depende de:** brief 001 concluído com `scripts/verificar.sh` verde.

---

## 1. Objetivo em uma frase

Criar o banco da Etapa 1 por migração numerada, em modo WAL e com `sqlite-vec`, com os modelos Pydantic e a camada de consultas isolada, o backup diário com restauração e cópia para desenvolvimento, e completar `importar-temas` para gravar os temas do usuário no banco.

## 2. Contexto e o que já existe no repositório

Esqueleto do brief 001: pacote, configuração validada, `container.configuracao()`, `container.banco()` levantando `NotImplementedError`, `cli.py` com `importar-temas --simular`. **Investigue** `agente_nw/nucleo/modelos/configuracao.py` e `config/container.py` antes de escrever; reutilize os modelos de configuração, não os duplique. O `temas.yaml` do usuário existe desde ontem; se não existir, o comando falha com instrução, e o brief segue com `temas.exemplo.yaml` nos testes.

O modelo de dados é o da seção 3 de `docs/ARQUITETURA.md` (seção 4.1 da Proposta v5). **Só as tabelas da Etapa 1 entram na migração 001.** As das Etapas 2 e 4 (`conta`, `captura`, `midia_processada`, `conversa_tema`, `pacote_troca`) ficam para migrações próprias quando as funcionalidades chegarem.

## 3. Escopo

### 3.1 `scripts/migracoes/001_inicial.sql` — literal

```sql
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
```

Se o `sqlite-vec` instalado não aceitar `INTEGER PRIMARY KEY` declarado em `vec0`, usar `rowid` implícito e mapear `tema_id = rowid`; registrar no relatório qual forma foi usada e a versão do `sqlite-vec`.

### 3.2 `agente_nw/nucleo/database/conexao.py`

`abrir(caminho) -> sqlite3.Connection`: `enable_load_extension(True)`, `sqlite_vec.load()`, `enable_load_extension(False)`, `PRAGMA journal_mode=WAL`, `PRAGMA foreign_keys=ON`, `PRAGMA busy_timeout=5000`, `PRAGMA synchronous=NORMAL`, `row_factory = sqlite3.Row`. É a única função do pacote que chama `sqlite3.connect`; `container.banco()` passa a devolvê-la (cache por processo).

### 3.3 `agente_nw/nucleo/database/migracoes.py`

`aplicar(conn)`: lê `scripts/migracoes/*.sql` em ordem numérica; se `schema_version` não existe, versão atual é 0; aplica cada script de versão maior que a atual dentro de `BEGIN … COMMIT` (falha desfaz tudo daquele script); confere ao fim que a última linha de `schema_version` bate com o maior número de arquivo. Chamado por `container.banco()` na primeira abertura. `agente_nw migrar` expõe o mesmo com saída legível.

### 3.4 Modelos Pydantic — `agente_nw/nucleo/modelos/`

Um módulo por entidade, `ConfigDict(frozen=True)`: `tema.py`, `perfil.py`, `perfil_tema.py`, `fonte.py`, `item.py`, `assunto.py`, `assunto_contato.py`, `fato.py`, `fila.py` (extração e revisão), `descarte.py`. Enums em `str` para `tipo`, `origem`, `nivel`, `status`. Listas (`sinonimos`, `linguas`, `temas`) como `list[str]`/`list[int]` com conversão de e para JSON nas consultas, não nos modelos.

### 3.5 Camada de consultas — `agente_nw/nucleo/database/queries/`

Todo SQL do pacote fica aqui, funções puras que recebem `conn`. Neste brief: `temas.py` (inserir ou obter por nome, listar, gravar embedding), `perfis.py` (obter usuário, inserir/atualizar por telefone ou e-mail, ativar, listar ativos), `perfil_tema.py` (vincular com peso/origem/nível, confirmar, listar por perfil), `sistema.py` (versão do esquema, progresso). As demais chegam com os briefs que as usam.

### 3.6 Backup e cópia — `agente_nw/nucleo/database/backup.py`

- `fazer_backup(conn, pasta)`: `conn.backup(destino)` para `dados/backups/agente_AAAA-MM-DD.db`; apaga os mais antigos que 7 dias; devolve o caminho. Comando `agente_nw backup`.
- `agente_nw copiar-banco <destino>`: restaura o backup mais recente em `<destino>` (para desenvolvimento do console sobre cópia, regra 5 do plano). Recusa destino igual ao banco real.
- `agente_nw restaurar-backup <arquivo> --confirmo`: substitui `dados/agente.db` pelo arquivo, depois de fazer um backup do atual. Sem `--confirmo`, só mostra o que faria.

### 3.7 `importar-temas` completo

Grava: o perfil do usuário (`tipo = 'usuario'`, único; cria se não existir, atualiza `nome`); cada tema por `nome` (UNIQUE; reimportar atualiza `descricao` e `sinonimos`, não duplica); `perfil_tema` do usuário com `peso`, `nivel`, `origem = 'declarada'`, `confirmado = 1`. A lista `ignorar` fica no YAML e é lida pela coleta (brief 006); este brief só a valida. Embeddings de tema **não** são calculados aqui (o brief 003 cria `agente_nw embeddar-temas`, e a coleta o chama).

### 3.8 Testes

- `tests/test_migracoes.py`: banco em arquivo temporário criado do zero; `schema_version = 1`; `journal_mode` responde `wal`; `SELECT vec_version()` funciona; as quatro tabelas vetoriais existem; segunda chamada de `aplicar` não faz nada.
- `tests/test_restricoes.py`: inserir o mesmo tema duas vezes → uma linha; o mesmo `(perfil_id, tema_id)` duas vezes → uma linha; segundo perfil `usuario` → erro; `UPDATE fato` → erro; `perfil_tema.nivel = 'outro'` → erro.
- `tests/test_backup.py`: backup gerado; restauração numa cópia temporária com contagem de linhas igual em todas as tabelas; retenção apaga arquivo com data forjada de 8 dias.
- `tests/test_concorrencia.py`: um processo mantém uma transação de escrita aberta por 2 s enquanto outro lê `tema` — a leitura responde sem erro e antes de 2 s (WAL).
- `tests/test_importar_temas.py`: importa `temas.exemplo.yaml` → 1 perfil usuário, 2 temas, 2 `perfil_tema` com nível; importa de novo → mesmas contagens.

## 4. Fora de escopo, com justificativa

- Tabelas das Etapas 2 e 4: entram nas migrações 002 em diante, quando houver código que as use. É o motivo de existir migração numerada.
- Embeddings: brief 003 (precisam do cliente do Ollama).
- Importação da agenda, consultas de item/assunto/menu: briefs 005 a 009, cada um traz as suas.

## 5. Decisões tomadas e decisões deixadas abertas

Tomadas:
- WAL desde a criação, `synchronous=NORMAL`: seguro para um banco local com backup diário e necessário para o console e os comandos de linha lerem enquanto o ciclo escreve.
- `fato` protegida por gatilhos, não só por convenção: "só inserção" vira erro de banco.
- Um único perfil `usuario`, garantido por índice parcial.
- `descarte_sensivel` guarda categoria e origem, nunca o termo nem o trecho.
- `progresso` e `fila_revisao` entram já na 001 porque os briefs 003 e 006 dependem delas e ambas são Etapa 1.
- Retenção de backup por data no nome do arquivo, 7 dias; Time Machine cobre o resto.

Abertas: nenhuma. A forma de chave primária no `vec0` é verificada em execução e registrada, não decidida no papel.

## 6. Passos de execução

1. Ler `configuracao.py`, `container.py`, `cli.py` do brief 001. Confirmar `scripts/verificar.sh` verde antes de tocar em qualquer coisa.
2. Escrever `scripts/migracoes/001_inicial.sql` literalmente como em 3.1.
3. Escrever `conexao.py` (3.2) e `migracoes.py` (3.3); ligar `container.banco()`.
4. Escrever os modelos (3.4) e as consultas deste brief (3.5).
5. Escrever `backup.py` e os três comandos (3.6).
6. Completar `importar-temas` (3.7); manter `--simular`.
7. Escrever os cinco arquivos de teste (3.8). Rodar `scripts/verificar.sh`.
8. Rodar contra o banco real: `agente_nw migrar`, `agente_nw importar-temas`, `agente_nw backup`, `agente_nw copiar-banco /tmp/agente_dev.db`. Colar as saídas no relatório. Se `temas.yaml` não existir, registrar como pendência do usuário e rodar com o exemplo num banco temporário.
9. Atualizar `docs/PLAN.md` (brief 002 concluído; próximo 003; versão do `sqlite-vec` e forma da chave no `vec0` registradas em armadilhas se tiver havido desvio).
10. Relatório final.

## 7. Critérios de aceite

1. Banco criado do zero por migração; `SELECT versao FROM schema_version` = 1; `PRAGMA journal_mode` = `wal`; `SELECT vec_version()` responde.
2. Reimportar `temas.yaml` não altera a contagem de `tema` nem de `perfil_tema`.
3. Backup gerado em `dados/backups/`; restaurado num banco temporário com contagem de linhas igual em todas as tabelas; retenção testada.
4. Leitura por um segundo processo durante uma escrita não bloqueia nem falha (teste de concorrência verde).
5. `grep -rn "sqlite3.connect(" agente_nw/` retorna só `conexao.py`; `grep -rln "SELECT\|INSERT\|UPDATE" agente_nw/ --include=*.py` retorna só arquivos em `database/queries/`, `migracoes.py`, `backup.py` e testes.
6. `scripts/verificar.sh` verde.

## 8. Riscos e como reverter

- **`vec0` recusa a chave declarada:** usar `rowid`, registrar. Nenhum outro módulo depende do nome da coluna além das consultas.
- **Migração parcial por erro no SQL:** transação por script desfaz; o banco fica na versão anterior; corrigir o SQL e reaplicar. Nunca editar um script já aplicado — criar 002.
- **Reversão do brief:** apagar `dados/agente.db*` e os arquivos criados devolve ao estado do brief 001. O `temas.yaml` do usuário não é tocado.

## 9. Relatório final obrigatório

```
## RELATÓRIO FINAL
- Brief executado: brief_E1_002_esquema_migracoes_backup_2026-09-17
- Arquivos criados:
- Arquivos alterados (com resumo da mudança em uma linha cada):
- Arquivos preservados literalmente na área afetada:
- Testes rodados e resultado: (saídas de verificar.sh e dos quatro comandos do passo 8)
- Versão do sqlite-vec e forma da chave usada no vec0:
- Comandos executados:
- Lista de arquivos para `git add` e texto sugerido do commit:
- Pendências e decisões que ficaram abertas:
- `docs/PLAN.md` atualizado: sim/não
```
