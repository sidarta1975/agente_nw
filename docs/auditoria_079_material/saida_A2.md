# Auditoria "texto por inteiro" — parte A2

Lista: `scratchpad/079/parte_A2.txt` (57 arquivos). Prefixo dos pontos: `A2`.
Total de linhas conferido com `wc -l` arquivo por arquivo: 3.660 linhas, todas lidas.

Resumo: 57 arquivos — **41 CERTIFICADO**, **14 CORTA**, **2 NÃO ANALÍTICO**, **0 NÃO CONFERIDO**.
32 pontos (classe C: 23; T: 2; R: 2; P: 1; NA: 4).

## 1. Tabela de certificação

| Arquivo | Linhas lidas/total | Resultado | Evidência (uma linha) | Ponto |
| --- | --- | --- | --- | --- |
| agente_nw/integracoes/__init__.py | 0/0 | CERTIFICADO | Arquivo vazio (0 bytes): só marca o pacote; não manipula texto de conteúdo. | — |
| agente_nw/nucleo/database/__init__.py | 0/0 | CERTIFICADO | Arquivo vazio (0 bytes): só marca o pacote. | — |
| agente_nw/nucleo/database/backup.py | 55/55 | CERTIFICADO | Não manipula texto de conteúdo: só infraestrutura (cópia do arquivo .db, retenção de 7 dias de arquivos de backup, `arquivos[-1]` escolhe o backup mais recente — arquivo, não texto). | — |
| agente_nw/nucleo/database/conexao.py | 26/26 | CERTIFICADO | Não manipula texto de conteúdo: só infraestrutura (abre o SQLite, carrega `sqlite_vec`, PRAGMAs). | — |
| agente_nw/nucleo/database/migracoes.py | 48/48 | NÃO ANALÍTICO | Só infraestrutura de esquema; o único corte é o número da migração extraído do nome do arquivo. | A2-001 |
| agente_nw/nucleo/database/queries/__init__.py | 0/0 | CERTIFICADO | Arquivo vazio (0 bytes): só marca o pacote. | — |
| agente_nw/nucleo/database/queries/assunto_contato.py | 150/150 | CERTIFICADO | Grava e lê linhas de cruzamento inteiras (`por_que`, `motivo` sem corte); nenhum LIMIT nem slice em consulta nenhuma. | — |
| agente_nw/nucleo/database/queries/assuntos.py | 257/257 | CORTA | Grava título/justificativa/resumo e centróides inteiros, mas dois seletores decidem **quais** assuntos o modelo vê. | A2-002, A2-003 |
| agente_nw/nucleo/database/queries/consulta_contato.py | 124/124 | CORTA | Grava `contexto_json`/`resumo_redes_sociais` inteiros; corta o histórico de consultas e as mensagens-molde que alimentam o prompt de redação. | A2-004, A2-005 |
| agente_nw/nucleo/database/queries/fatos.py | 56/56 | CORTA | `inserir` grava `conteudo` inteiro; `listar_recentes` escolhe só os N fatos mais recentes que vão ao prompt e aos termos de busca. | A2-006 |
| agente_nw/nucleo/database/queries/fila_extracao.py | 66/66 | CORTA | Enfileira e devolve `texto` inteiro (nenhum corte de caractere); o lote de pendentes é limitado por `LIMIT`. | A2-007 |
| agente_nw/nucleo/database/queries/fila_revisao.py | 15/15 | CERTIFICADO | Só INSERT de tarefa/entrada/erro, gravados por inteiro; nenhuma leitura, nenhum limite. | — |
| agente_nw/nucleo/database/queries/fontes.py | 75/75 | CORTA | Cadastro de feeds, sem texto de conteúdo; único corte de coleção é o `LIMIT 2` da regra "dois dias vazios". | A2-008 |
| agente_nw/nucleo/database/queries/gancho_uso.py | 107/107 | CERTIFICADO | Grava e lê `gancho_json` e `comentario` inteiros (só `.strip()`, que não é corte de conteúdo); nenhum LIMIT. | — |
| agente_nw/nucleo/database/queries/itens.py | 104/104 | CORTA | Grava `titulo`/`texto` inteiros e lê todos os itens de um assunto; o lote do agrupador é limitado por `LIMIT`. | A2-009 |
| agente_nw/nucleo/database/queries/listas.py | 138/138 | CORTA | Grava nome/cabeçalho inteiros; a busca por nome usa só o primeiro nome e as "parecidas" são cortadas em `maximo`. | A2-010, A2-011 |
| agente_nw/nucleo/database/queries/nota_contato.py | 59/59 | CORTA | Grava `texto` da nota inteiro; a leitura por perfil aceita `limite`, usado para o prompt de redação. | A2-012 |
| agente_nw/nucleo/database/queries/pedidos.py | 191/191 | NÃO ANALÍTICO | Grava `texto` do pedido e os JSON inteiros; os três `LIMIT` servem a listagens de tela (duas sem chamador em produção hoje). | A2-013 |
| agente_nw/nucleo/database/queries/perfil_tema.py | 170/170 | CERTIFICADO | Vínculos tema↔perfil e embeddings inteiros; a escolha "confirmadas, ou todas se não houver confirmada" é filtro por status, não corte de conjunto; nenhum LIMIT. | — |
| agente_nw/nucleo/database/queries/rede_sem_perfil.py | 30/30 | CERTIFICADO | Não manipula texto de conteúdo: marca/desmarca "sem perfil" por rede; itera `REDES_SUPORTADAS` inteira. | — |
| agente_nw/nucleo/database/queries/redes_sociais.py | 42/42 | CERTIFICADO | Só links de rede do contato, gravados e lidos inteiros, sem limite. | — |
| agente_nw/nucleo/database/queries/sistema.py | 63/63 | CERTIFICADO | Não manipula texto de conteúdo: versão de esquema, progresso, bloqueio por host e termo buscado (chave = prefixo + valor inteiro). | — |
| agente_nw/nucleo/database/queries/temas.py | 105/105 | CERTIFICADO | Nome, descrição e sinônimos gravados e lidos inteiros; `listar_com_embedding` devolve **todos** os temas com vetor do modelo atual. | — |
| agente_nw/nucleo/modelos/__init__.py | 0/0 | CERTIFICADO | Arquivo vazio (0 bytes): só marca o pacote. | — |
| agente_nw/nucleo/modelos/assunto_contato.py | 26/26 | CERTIFICADO | Contrato Pydantic frozen de campos escalares e textos livres, sem validador que corte. | — |
| agente_nw/nucleo/modelos/assunto.py | 24/24 | CERTIFICADO | Contrato frozen; `titulo_gerado`, `justificativa` e `resumo_cartao` sem limite de tamanho. | — |
| agente_nw/nucleo/modelos/calibracao.py | 9/9 | CERTIFICADO | Contrato de resposta booleana da comparação de par; nenhum texto. | — |
| agente_nw/nucleo/modelos/cartao.py | 9/9 | CERTIFICADO | Contrato de um campo `resumo: str`, sem validador que corte. | — |
| agente_nw/nucleo/modelos/configuracao.py | 383/383 | CORTA | É onde moram os tetos do produto: tamanho de página e de bloco de texto, blocos/imagens por rede, meses de conversa, trocas no prompt, moldes, candidatos e tetos por dia. | A2-014 … A2-025 |
| agente_nw/nucleo/modelos/consulta_contato.py | 14/14 | CERTIFICADO | Contrato frozen; guarda os JSON de contexto e o resumo como texto, sem limite. | — |
| agente_nw/nucleo/modelos/contexto_consulta.py | 30/30 | CERTIFICADO | Contrato frozen do contexto do pedido; listas sem corte **neste** arquivo (o corte está em `modelos/pedido.py`). | — |
| agente_nw/nucleo/modelos/cruzamento.py | 26/26 | CERTIFICADO | Contratos de resposta (`por_que`, `avaliacoes`) sem limite de itens nem de tamanho. | — |
| agente_nw/nucleo/modelos/extracao.py | 50/50 | CERTIFICADO | Contrato de `extrair_de_texto`: campos, tags e fatos em listas sem corte; `trecho` e `conteudo` sem limite. | — |
| agente_nw/nucleo/modelos/fato.py | 15/15 | CERTIFICADO | Contrato frozen; `conteudo` é `str` sem limite. | — |
| agente_nw/nucleo/modelos/fila.py | 26/26 | CERTIFICADO | Contratos das duas filas; `texto`/`entrada` sem limite. | — |
| agente_nw/nucleo/modelos/fonte.py | 15/15 | CERTIFICADO | Contrato de cadastro de feed; não manipula texto de conteúdo. | — |
| agente_nw/nucleo/modelos/item.py | 17/17 | CERTIFICADO | Contrato frozen; `titulo` e `texto` sem limite de tamanho. | — |
| agente_nw/nucleo/modelos/lista_rede_social.py | 21/21 | CERTIFICADO | Contrato de entrada de lista (nome, cabeçalho, link) sem corte. | — |
| agente_nw/nucleo/modelos/localizacao.py | 41/41 | CERTIFICADO | `Localizacao.opcoes` é declarada "todas, da mais para a menos provável" (linha 28); nenhum corte aqui. | — |
| agente_nw/nucleo/modelos/marcacao.py | 15/15 | CERTIFICADO | Contrato da marcação do usuário; `motivo` sem limite. | — |
| agente_nw/nucleo/modelos/pedido.py | 116/116 | CORTA | Dois `field_validator` cortam listas vindas do pedido do usuário antes de qualquer análise (5 itens; 6 termos de busca). | A2-026, A2-027 |
| agente_nw/nucleo/modelos/perfil_tema.py | 23/23 | CERTIFICADO | Contrato do vínculo tema↔perfil; nenhum texto de conteúdo. | — |
| agente_nw/nucleo/modelos/perfil.py | 35/35 | CERTIFICADO | Ficha do contato; `notas` é `str | None` sem limite. | — |
| agente_nw/nucleo/modelos/proveniencia.py | 23/23 | CERTIFICADO | Só metadado de quem gerou a linha; não manipula texto de conteúdo. | — |
| agente_nw/nucleo/modelos/qualificacao.py | 12/12 | CERTIFICADO | Contrato da qualificação; `temas` e `justificativa` sem corte. | — |
| agente_nw/nucleo/modelos/redacao.py | 141/141 | CORTA | `validar_ganchos` lê a mensagem inteira (termos de evitar, contagem de palavras), mas entrega no máximo `MAXIMO_GANCHOS` ganchos de notícia. | A2-028 |
| agente_nw/nucleo/modelos/rede_social.py | 13/13 | CERTIFICADO | Contrato de link de rede; nenhum texto de conteúdo. | — |
| agente_nw/nucleo/modelos/rotulo.py | 9/9 | CERTIFICADO | Contrato de um campo `titulo: str`, sem validador que corte. | — |
| agente_nw/nucleo/modelos/tema.py | 23/23 | CERTIFICADO | Contratos de tema e de `descrever_tema`; descrição e sinônimos sem corte. | — |
| agente_nw/perfil/__init__.py | 0/0 | CERTIFICADO | Arquivo vazio (0 bytes): só marca o pacote. | — |
| agente_nw/perfil/agenda_google_csv.py | 46/46 | CORTA | `notas` do CSV vai inteira para `ContatoBruto`, mas só o primeiro telefone/e-mail/organização (coluna "1") e só a primeira coluna que casa o prefixo. | A2-029 |
| agente_nw/perfil/agenda_macos.py | 107/107 | CORTA | A nota do contato é lida inteira (`str(completo.note())`), mas só o primeiro telefone e o primeiro e-mail entram no `ContatoBruto`. | A2-030 |
| agente_nw/perfil/configurador.py | 73/73 | CERTIFICADO | O texto do tema vai inteiro ao embedding: `embeddar([f"{tema.nome}: {tema.descricao}"])[0]` — o `[0]` é o único resultado do lote de um item, não corte. | — |
| agente_nw/perfil/importador.py | 111/111 | CERTIFICADO | `bruto.notas` entra inteira na fila de extração (linha 106) e todos os `marcadores` são percorridos; o contato sem telefone nem e-mail é ignorado (filtro de identidade, não de texto). | — |
| agente_nw/perfil/inferencia.py | 283/283 | CORTA | Percorre todos os termos do pedido e todos os temas com embedding, mas cada frase de `sobre_o_usuario` só é lida por três expressões regulares e, sem padrão, é descartada. | A2-031, A2-032 |
| agente_nw/perfil/lacunas.py | 25/25 | CERTIFICADO | Percorre `ORDEM_IMPACTO` inteira e devolve todos os campos vazios; não manipula texto de conteúdo. | — |
| agente_nw/perfil/normalizacao.py | 18/18 | CERTIFICADO | Normaliza telefone para E.164 com `phonenumbers`; não há corte de texto de conteúdo. | — |

## 2. Pontos encontrados

#### A2-001 — agente_nw/nucleo/database/migracoes.py:21 — `_migracoes_disponiveis`
- Classe: NA
- O que é cortado e quanto: o nome do arquivo de migração é reduzido ao trecho antes do primeiro `_` (o número de versão).
- Qual decisão do produto depende desse corte: a ordem e o filtro "migração já aplicada"; nenhuma análise de texto de conteúdo.
- Trecho de código:
  ```python
  migracoes = [(int(caminho.name.split("_", 1)[0]), caminho) for caminho in pasta.glob("*.sql")]
  ```
- Justificativa existente no código/comentário: nenhuma.
- Por que isto é analítico ou NA: NA — é identificador (número de versão no nome do arquivo). O conteúdo do `.sql` é lido inteiro na linha 33 (`caminho.read_text`) e executado inteiro.

#### A2-002 — agente_nw/nucleo/database/queries/assuntos.py:179 — `listar_candidatos_qualificacao`
- Classe: C
- O que é cortado e quanto: dos assuntos ainda sem qualificação (todos lidos e pontuados por cosseno contra os temas), só os `limite` mais parecidos seguem; o resto é descartado nesta rodada.
- Qual decisão do produto depende desse corte: quais assuntos vão à tarefa de LLM `qualificar` (chamador `nucleo/relevancia/qualificador.py:54`); assunto fora do corte não é qualificado e portanto nunca chega ao menu nem à redação.
- Trecho de código:
  ```python
  candidatos.sort(key=lambda par: par[0], reverse=True)
  return [assunto for _, assunto in candidatos[:limite]]
  ```
- Justificativa existente no código/comentário: nenhuma neste arquivo (o teto vem de `limiares.qualificacao.teto_por_dia`, ver A2-023).
- Por que isto é analítico: é um "top N" sobre o conjunto de assuntos candidatos, e o descartado não é analisado por modelo nenhum. O ranqueamento usa centróide (representação do texto), mas o ponto aqui é o corte de coleção.

#### A2-003 — agente_nw/nucleo/database/queries/assuntos.py:250-257 — `listar_qualificados_sem_cartao`
- Classe: C
- O que é cortado e quanto: `ORDER BY id LIMIT ?` — só os `limite` assuntos mais antigos sem cartão entram na rodada.
- Qual decisão do produto depende desse corte: quais assuntos recebem o resumo do cartão (tarefa de LLM `cartao`, chamador `nucleo/relevancia/cartoes.py:91`).
- Trecho de código:
  ```python
  "WHERE substancial IS NOT NULL AND conversavel IS NOT NULL AND resumo_cartao IS NULL "
  "ORDER BY id LIMIT ?",
  ```
- Justificativa existente no código/comentário: nenhuma.
- Por que isto é analítico: decide quais itens o modelo vê. É lote com retomada (quem ficou fora continua com `resumo_cartao IS NULL` e entra na próxima rodada), mas numa única execução o restante não é analisado.

#### A2-004 — agente_nw/nucleo/database/queries/consulta_contato.py:45-58 — `listar_por_perfil`
- Classe: C
- O que é cortado e quanto: com `limite`, só as N consultas mais recentes do contato (`ORDER BY criado_em DESC, id DESC LIMIT ?`); as anteriores não são lidas.
- Qual decisão do produto depende desse corte: o bloco HISTÓRICO do prompt da tarefa `redigir_ganchos` — `nucleo/redacao.py:153` chama com `_CONSULTAS_NO_HISTORICO + 1`, e `nucleo/historico.py:85` (`historico_recente_para_prompt`) também passa `limite`.
- Trecho de código:
  ```python
  f"SELECT {_COLUNAS} FROM consulta_contato WHERE perfil_id = ? "
  "ORDER BY criado_em DESC, id DESC LIMIT ?",
  ```
- Justificativa existente no código/comentário: nenhuma neste arquivo (a constante está no chamador, fora desta parte da auditoria).
- Por que isto é analítico: o que foi dito antes à pessoa alimenta o prompt; consulta mais antiga que o limite simplesmente não é vista pelo modelo. Com `limite=None` a função lê tudo — o corte é escolha do chamador.

#### A2-005 — agente_nw/nucleo/database/queries/consulta_contato.py:121-124 — `moldes_por_contexto`
- Classe: C
- O que é cortado e quanto: de todas as mensagens já entregues a outros contatos com a mesma tríade de contexto, ficam no máximo `maximo` marcadas `usado`; não havendo nenhuma `usado`, fica **uma só** `entregue` (`candidatos[:1]`).
- Qual decisão do produto depende desse corte: quais mensagens-molde entram no prompt de `redigir_ganchos` (`nucleo/redacao.py:182`) e qual `molde_origem_id` é gravado.
- Trecho de código:
  ```python
  usados = [molde for molde in candidatos if molde.bom]
  if usados:
      return usados[:maximo]
  return candidatos[:1]
  ```
- Justificativa existente no código/comentário: docstring das linhas 80-85 — "Havendo ao menos uma `usado` para a tríade, só `usado` participa (até `maximo`) … Sem nenhuma `usado`, no máximo uma `entregue` participa — a mais recente, arranque a frio" (brief 065).
- Por que isto é analítico: texto de mensagem anterior que o corte descarta não entra no prompt. A docstring explica o critério, mas explicação não é aprovação.

#### A2-006 — agente_nw/nucleo/database/queries/fatos.py:31-36 — `listar_recentes`
- Classe: C
- O que é cortado e quanto: só os `limite` fatos mais recentes do contato (`ORDER BY COALESCE(data_do_fato, registrado_em) DESC, id DESC LIMIT ?`); fato mais antigo que isso não é lido.
- Qual decisão do produto depende desse corte: o conjunto de fatos candidatos do prompt de redação (`nucleo/redacao.py:136`, `_FATOS_CANDIDATOS`), os termos de busca de notícia do contato (`nucleo/termos_contato.py:57`, `_FATOS_LIDOS`), a localização em rede social (`nucleo/localizacao.py:376`, 200) e a tela da pessoa (`console/app.py:409`, 15).
- Trecho de código:
  ```python
  "WHERE perfil_id = ? ORDER BY COALESCE(data_do_fato, registrado_em) DESC, id DESC LIMIT ?",
  ```
- Justificativa existente no código/comentário: nenhuma.
- Por que isto é analítico: fato é o que o sistema sabe da pessoa; o que o `LIMIT` deixa de fora não alimenta prompt, nem termo de busca, nem localização. Só a chamada de `console/app.py` é de tela.

#### A2-007 — agente_nw/nucleo/database/queries/fila_extracao.py:32-37 — `listar_pendentes`
- Classe: C
- O que é cortado e quanto: `ORDER BY id LIMIT ?` — a rodada de extração pega só os `limite` primeiros itens pendentes.
- Qual decisão do produto depende desse corte: quantos blocos de texto (nota de agenda, bloco de conversa de WhatsApp) vão à tarefa de LLM `extrair_de_texto` numa execução (`perfil/extrator.py:75`).
- Trecho de código:
  ```python
  f"SELECT {_COLUNAS} FROM fila_extracao WHERE processado = 0 AND erro IS NULL ORDER BY id LIMIT ?",
  ```
- Justificativa existente no código/comentário: nenhuma.
- Por que isto é analítico (dúvida registrada): é lote com retomada — o não processado continua `processado = 0` e entra na próxima execução, então o descarte não é permanente. Mas numa execução o texto que ficou fora não é analisado, e nada neste arquivo garante que a próxima execução aconteça (não há tarefa periódica no projeto, AGENTS §6).

#### A2-008 — agente_nw/nucleo/database/queries/fontes.py:67-75 — `dois_dias_vazios`
- Classe: C
- O que é cortado e quanto: `ORDER BY data DESC LIMIT 2` — só as duas execuções mais recentes do feed são olhadas.
- Qual decisão do produto depende desse corte: o alerta/desativação de feed vazio (`coleta/rss/leitor.py:267`), isto é, se aquela fonte continua sendo consultada.
- Trecho de código:
  ```python
  "SELECT n_itens_novos FROM fonte_execucao WHERE fonte_id = ? AND data <= ? "
  "ORDER BY data DESC LIMIT 2",
  ```
- Justificativa existente no código/comentário: nenhuma (o nome da função é a regra).
- Por que isto é analítico (dúvida registrada): não há texto de conteúdo aqui, são contagens; o `LIMIT 2` é a própria definição da regra "dois dias vazios", não a redução de um conjunto que se queria analisar inteiro. Registrado por ser um corte de coleção que decide um filtro (quais fontes são lidas).

#### A2-009 — agente_nw/nucleo/database/queries/itens.py:66-71 — `listar_sem_assunto`
- Classe: C
- O que é cortado e quanto: `ORDER BY id LIMIT ?` — só os `limite` itens mais antigos ainda sem assunto entram na rodada.
- Qual decisão do produto depende desse corte: quais notícias são embeddadas e agrupadas em assunto (`nucleo/agrupamento/agrupador.py:83`); item fora do lote não é agrupado nesta execução.
- Trecho de código:
  ```python
  f"SELECT {_COLUNAS} FROM item WHERE assunto_id IS NULL ORDER BY id LIMIT ?",
  ```
- Justificativa existente no código/comentário: nenhuma.
- Por que isto é analítico: decide quais textos de notícia vão ao embedding e ao agrupamento. Também é lote com retomada (`assunto_id IS NULL` persiste), mesma dúvida de A2-007.

#### A2-010 — agente_nw/nucleo/database/queries/listas.py:73-87 — `buscar_por_nome`
- Classe: R
- O que é cortado e quanto: o nome procurado é reduzido ao **primeiro token** (`split()[:1]`); o SQL só casa `nome_normalizado = <primeiro>` ou `LIKE '<primeiro> %'`. O resto do nome só é usado depois, por `casa_nome`, sobre as linhas que esse prefixo já trouxe.
- Qual decisão do produto depende desse corte: a localização do contato nas listas das redes (`nucleo/localizacao.py:253`) — quem está gravado com o nome em outra ordem, com inicial ("J. Silva") ou só pelo sobrenome nunca entra no conjunto avaliado.
- Trecho de código:
  ```python
  primeiro = sem_acento_e_caixa(nome).split()[:1]
  ...
  f"WHERE (nome_normalizado = ? OR nome_normalizado LIKE ?){filtro_rede} "
  ```
- Justificativa existente no código/comentário: docstring da linha 74 — "Entradas cujo nome casa com `nome` (primeiro nome inteiro, sobrenome por prefixo), sem acento".
- Por que isto é analítico: o texto do nome é substituído por um pedaço menor antes da busca, e a decisão seguinte (achou/não achou a pessoa) é tomada como se a lista toda tivesse sido comparada. `buscar_parecidos` (A2-011) é o paliativo quando isto não acha ninguém.

#### A2-011 — agente_nw/nucleo/database/queries/listas.py:130-138 — `buscar_parecidos`
- Classe: C
- O que é cortado e quanto: a lista inteira da rede é pontuada por similaridade, mas só as `maximo` melhores acima de `minimo` são devolvidas.
- Qual decisão do produto depende desse corte: quais opções de pessoa são oferecidas ao desempate (`nucleo/localizacao.py:259`) e, portanto, à confirmação do usuário ou à tarefa `desempatar_perfil`.
- Trecho de código:
  ```python
  aprovadas = sorted((par for par in pontuadas if par[0] >= minimo), key=lambda par: -par[0])
  return [e for _, e in aprovadas[:maximo]]
  ```
- Justificativa existente no código/comentário: docstring das linhas 133-135 — "da mais provável para a menos, no máximo `maximo`".
- Por que isto é analítico: é um "top N" que descarta candidatas; o valor vem de `listas.maximo_parecidas` (A2-021). A pontuação em si vê o nome inteiro de cada entrada.

#### A2-012 — agente_nw/nucleo/database/queries/nota_contato.py:38-50 — `listar_por_perfil`
- Classe: C
- O que é cortado e quanto: com `limite`, só as N notas mais recentes do contato (`ORDER BY criado_em DESC, id DESC LIMIT ?`).
- Qual decisão do produto depende desse corte: o bloco de notas do prompt de `redigir_ganchos` (`nucleo/redacao.py:163`, `_NOTAS_NO_PROMPT`) — nota mais antiga que o limite não vira contexto da redação (brief 050).
- Trecho de código:
  ```python
  linhas = conexao.execute(consulta + " LIMIT ?", (perfil_id, limite)).fetchall()
  ```
- Justificativa existente no código/comentário: nenhuma (só a docstring "Mais recentes primeiro").
- Por que isto é analítico: a nota é texto escrito pelo usuário sobre a pessoa e serve para a redação; o que o limite corta não é analisado. Com `limite=None` lê tudo, e `listar_por_pedido` não tem limite.

#### A2-013 — agente_nw/nucleo/database/queries/pedidos.py:153, 159, 180 — `obter_ultimo`, `listar_recentes`, `pessoas_recentes`
- Classe: NA
- O que é cortado e quanto: `LIMIT 1` em `obter_ultimo` (é a definição de "o último"), `LIMIT ?` nos pedidos recentes e `GROUP BY ... ORDER BY ultimo DESC LIMIT ?` nas pessoas recentes.
- Qual decisão do produto depende desse corte: só a tela/CLI. Busca em `agente_nw/` mostra que `listar_recentes` e `pessoas_recentes` não têm chamador em produção hoje (`pessoas_recentes` só aparece em `tests/test_fluxo.py:351`); `listar_por_perfil` (linha 164), que alimenta o histórico da página da pessoa (`console/app.py:399`), **não tem limite**.
- Trecho de código:
  ```python
  "FROM pedido p JOIN perfil f ON f.id = p.perfil_id "
  "WHERE p.perfil_id IS NOT NULL GROUP BY p.perfil_id ORDER BY ultimo DESC LIMIT ?",
  ```
- Justificativa existente no código/comentário: docstring das linhas 173-174 — "As últimas pessoas de quem o usuário pediu algo".
- Por que isto é NA: nenhum desses resultados alimenta prompt, embedding, deduplicação ou filtro; é listagem de tela. O `texto` do pedido é gravado e devolvido inteiro em todas as funções.

#### A2-014 — agente_nw/nucleo/modelos/configuracao.py:190-195 — `ColetaLimiares` (leitura de rede social)
- Classe: C
- O que é cortado e quanto: `maximo_blocos_por_rede = 10` (blocos de texto de cada rede que vão ao modelo), `maximo_imagens_por_rede = 0` (por padrão **nenhuma** imagem publicada é descrita), `largura_minima_imagem = 250` (imagem menor é descartada antes de ser descrita).
- Qual decisão do produto depende desse corte: o que o modelo lê da rede social do contato — prompts de extração sobre captura e a tarefa de visão `descrever_imagem`.
- Trecho de código:
  ```python
  maximo_blocos_por_rede: int = Field(default=10, ge=1)
  """Blocos de texto de cada rede social do contato que vão para o modelo (cada um é uma chamada)."""
  maximo_imagens_por_rede: int = Field(default=0, ge=0)
  ```
- Justificativa existente no código/comentário: as próprias docstrings das linhas 191, 193 e 195 descrevem o corte ("0 = não lê imagens"; "abaixo da qual a imagem é ícone ou foto de perfil e não publicação").
- Por que isto é analítico: a página capturada tem mais de dez blocos com frequência, e o 11º não é analisado por ninguém; com o padrão 0, nenhuma publicação em imagem é lida. O corte é aplicado no código de coleta (outra parte da auditoria), mas o valor que o define está aqui.

#### A2-015 — agente_nw/nucleo/modelos/configuracao.py:196-210 — `ColetaLimiares` (coleta de notícia)
- Classe: C
- O que é cortado e quanto: `max_consultas_por_pedido = 4` (buscas por pedido, mesmo que haja mais termos), `candidatos_suficientes = 10` (com dez notícias novas, as buscas seguintes **não são abertas**), `maximo_itens_novos_por_feed = 15` (só as mais recentes de cada feed), `horas_reuso_termo = 24` e `minutos_reaproveitamento = 120` (não busca de novo / reaproveita coleta anterior), `cooldown_bloqueio_minutos = 180`, `tempo_maximo_segundos = 240` (a coleta pode terminar antes de ler tudo).
- Qual decisão do produto depende desse corte: quais notícias existem para agrupar, qualificar, cruzar e virar gancho. Notícia não coletada nunca é analisada.
- Trecho de código:
  ```python
  candidatos_suficientes: int = Field(default=10, ge=1)
  """Com tantas notícias novas na coleta do pedido, as buscas seguintes não são abertas."""
  maximo_itens_novos_por_feed: int = Field(default=15, ge=1)
  ```
- Justificativa existente no código/comentário: docstrings das linhas 197-210; o AGENTS §6 registra os tetos como resiliência a bloqueio (brief 045).
- Por que isto é analítico: todos decidem **quais** itens entram no conjunto analisado. É o corte mais a montante do produto: o resto do pipeline nem sabe que existiam outros.

#### A2-016 — agente_nw/nucleo/modelos/configuracao.py:185, 187 — `ColetaLimiares.teaser_minimo_caracteres`, `retencao_texto_dias`
- Classe: C
- O que é cortado e quanto: `teaser_minimo_caracteres` separa o que conta como texto aproveitável do que é só teaser; `retencao_texto_dias` define por quantos dias o texto do item é guardado — depois disso ele deixa de existir para qualquer análise futura.
- Qual decisão do produto depende desse corte: se um item entra com texto ou só com título (ligado à classe R do pipeline de coleta) e se o texto integral ainda está no banco quando o item é reavaliado.
- Trecho de código:
  ```python
  teaser_minimo_caracteres: int
  dias_max_primeira_aparicao: int
  retencao_texto_dias: int
  ```
- Justificativa existente no código/comentário: nenhuma (são os únicos campos de `ColetaLimiares` sem docstring).
- Por que isto é analítico (dúvida registrada): o efeito exato depende do código de coleta/limpeza, que está em outra parte da auditoria; aqui fica registrado que os dois valores decidem a presença do texto na análise, não a apresentação.

#### A2-017 — agente_nw/nucleo/modelos/configuracao.py:244 — `ExtensaoLimiares.maximo_caracteres_pagina`
- Classe: T
- O que é cortado e quanto: o texto de uma página lida pela extensão é limitado a 200.000 caracteres (mínimo configurável 1.000).
- Qual decisão do produto depende desse corte: tudo o que é extraído da rede social do contato — prompt de extração de fatos/tags a partir da captura.
- Trecho de código:
  ```python
  maximo_caracteres_pagina: int = Field(default=200000, ge=1000)
  ```
- Justificativa existente no código/comentário: nenhuma (campo sem docstring).
- Por que isto é analítico: é truncamento do texto de um item; o que passa de 200.000 caracteres não chega a análise nenhuma. O valor é alto, mas o corte existe e não há aviso de que ocorreu.

#### A2-018 — agente_nw/nucleo/modelos/configuracao.py:276 — `WhatsappLimiares.maximo_caracteres_bloco`
- Classe: T
- O que é cortado e quanto: a conversa é partida em blocos de no máximo 6.000 caracteres, cada bloco uma chamada ao modelo.
- Qual decisão do produto depende desse corte: a extração de fatos da conversa do WhatsApp (tarefa `extrair_de_texto`).
- Trecho de código:
  ```python
  maximo_caracteres_bloco: int = Field(default=6000, ge=1)
  """Tamanho máximo de cada bloco de texto enviado à extração (cada bloco é uma chamada ao modelo)."""
  ```
- Justificativa existente no código/comentário: a docstring da linha 277.
- Por que isto é analítico: é fatiamento, não descarte — somados, os blocos cobrem o texto todo —, mas nenhuma chamada vê a conversa inteira, então fato que só se entende entre dois blocos se perde. Registrado como T por ser corte no texto de um item antes do prompt.

#### A2-019 — agente_nw/nucleo/modelos/configuracao.py:278 — `WhatsappLimiares.trocas_no_prompt`
- Classe: C
- O que é cortado e quanto: só as 10 últimas mensagens trocadas entram no bloco HISTÓRICO da redação.
- Qual decisão do produto depende desse corte: o tom da mensagem redigida (tarefa `redigir_ganchos`).
- Trecho de código:
  ```python
  trocas_no_prompt: int = Field(default=10, ge=1)
  """Últimas mensagens trocadas que entram no HISTÓRICO da redação, para acertar o tom."""
  ```
- Justificativa existente no código/comentário: a docstring da linha 279.
- Por que isto é analítico: decide quais mensagens o modelo lê; o resto da conversa não entra no prompt.

#### A2-020 — agente_nw/nucleo/modelos/configuracao.py:274 — `WhatsappLimiares.meses_extraidos`
- Classe: C
- O que é cortado e quanto: só os 24 meses mais recentes de mensagens do contato entram na fila de extração de fatos.
- Qual decisão do produto depende desse corte: quais fatos existem sobre a pessoa (conversa mais antiga nunca é lida).
- Trecho de código:
  ```python
  meses_extraidos: int = Field(default=24, ge=1)
  """Meses mais recentes de mensagens do contato que entram na fila de extração de fatos."""
  ```
- Justificativa existente no código/comentário: a docstring da linha 275.
- Por que isto é analítico: é corte de coleção por janela de tempo (os "meses" que as regras citam explicitamente).

#### A2-021 — agente_nw/nucleo/modelos/configuracao.py:224, 228, 231, 233 — `ListasLimiares`
- Classe: C
- O que é cortado e quanto: `maximo_entradas` (teto de entradas lidas da lista de uma rede), `maximo_parecidas = 5` (candidatas por similaridade, ver A2-011), `rodadas_sem_novidade = 3` (a lista é dada por lida depois de três rolagens sem entrada nova), `redes_so_por_link` (redes que não são lidas nem buscadas).
- Qual decisão do produto depende desse corte: quem existe no universo onde o contato é procurado; pessoa fora da parte lida da lista é invisível para a localização.
- Trecho de código:
  ```python
  maximo_entradas: int = Field(ge=1)
  ...
  rodadas_sem_novidade: int = Field(default=3, ge=1)
  """Rodadas de rolagem seguidas sem entrada nova antes de dar a lista por lida."""
  ```
- Justificativa existente no código/comentário: docstrings das linhas 230, 232 e 234 (brief 037/044).
- Por que isto é analítico: define o conjunto de entradas de lista efetivamente analisado — exatamente o caso "entradas de lista" apontado no pedido desta auditoria.

#### A2-022 — agente_nw/nucleo/modelos/configuracao.py:178-179 — `ConectorLimiares.candidatos_por_contato`, `itens_no_menu`
- Classe: C
- O que é cortado e quanto: quantos assuntos candidatos são cruzados por contato e quantos itens chegam ao menu.
- Qual decisão do produto depende desse corte: quais assuntos passam pelo cruzamento (tarefas `cruzar_por_que` / `avaliar_relacao_objetivo`) e quais são entregues.
- Trecho de código:
  ```python
  candidatos_por_contato: int
  itens_no_menu: int
  ```
- Justificativa existente no código/comentário: nenhuma (campos sem docstring).
- Por que isto é analítico: `candidatos_por_contato` decide quais assuntos o modelo julga; `itens_no_menu` corta o que é entregue depois de analisado (mais perto de apresentação, registrado junto por serem o mesmo bloco de configuração).

#### A2-023 — agente_nw/nucleo/modelos/configuracao.py:141, 216 — `QualificacaoLimiares.teto_por_dia`, `CartaoLimiares.teto_por_dia`
- Classe: C
- O que é cortado e quanto: o número de assuntos qualificados e de cartões gerados por dia; é o `limite` que chega a A2-002 e A2-003.
- Qual decisão do produto depende desse corte: quais assuntos recebem qualificação e cartão por LLM.
- Trecho de código:
  ```python
  substancial_minimo: float
  conversavel_minimo: float
  teto_por_dia: int
  ```
- Justificativa existente no código/comentário: nenhuma.
- Por que isto é analítico: é o valor do corte de coleção que decide quais itens o modelo vê (mesma cadeia de A2-002/A2-003).

#### A2-024 — agente_nw/nucleo/modelos/configuracao.py:302 — `MoldesLimiares.maximo`
- Classe: C
- O que é cortado e quanto: no máximo 2 mensagens-molde oferecidas à redação (o `maximo` de A2-005); `0` desliga os moldes.
- Qual decisão do produto depende desse corte: o prompt de `redigir_ganchos` (brief 048/065).
- Trecho de código:
  ```python
  maximo: int = Field(default=2, ge=0)
  """Máximo de mensagens-molde oferecidas à redação (preferência pelas marcadas 'usado')."""
  ```
- Justificativa existente no código/comentário: a docstring da linha 303.
- Por que isto é analítico: define quanto texto de mensagem anterior é analisado pela redação.

#### A2-025 — agente_nw/nucleo/modelos/configuracao.py:63, 67 — `TarefaRoteamento.num_ctx`, `num_predict`
- Classe: P
- O que é cortado e quanto: cada tarefa declara seu `num_ctx` (janela de entrada) e `num_predict` (teto da resposta); o contrato exige que existam e que `num_predict > 0`, mas não há nada aqui — nem validador, nem relação com o tamanho do prompt — que garanta que o prompt caiba em `num_ctx`.
- Qual decisão do produto depende desse corte: toda tarefa de LLM; prompt maior que `num_ctx` é truncado em silêncio pelo Ollama, e o mesmo vale para o limite de entrada das APIs e para o `bge-m3` (8.192 tokens) nos embeddings.
- Trecho de código:
  ```python
  num_ctx: int
  temperature: float
  format: str
  think: bool
  num_predict: int = Field(gt=0)
  ```
- Justificativa existente no código/comentário: nenhuma; há validador só para `think` (linhas 69-74) e para a coerência entre perfis (linhas 106-123), inclusive exigindo o mesmo modelo de embeddings.
- Por que isto é analítico: é exatamente a classe P — o texto vai inteiro ao prompt e ninguém confere se cabe. A conferência poderia estar no cliente de LLM (outra parte da auditoria); aqui registra-se que o contrato não a exige.

#### A2-026 — agente_nw/nucleo/modelos/pedido.py:88-91 — `PedidoExtraido.lista_sem_duplicatas`
- Classe: C
- O que é cortado e quanto: `interessa`, `evitar` e `sobre_o_usuario` são cortadas em 5 itens (`_MAXIMO_INTERESSA = 5`), depois da remoção de duplicatas.
- Qual decisão do produto depende desse corte: `interessa` entra nos termos do pedido (`perfil/inferencia.py::_termos_do_pedido`) e no contexto da consulta; `evitar` é a lista conferida contra cada mensagem em `modelos/redacao.py::validar_ganchos`; `sobre_o_usuario` alimenta `aplicar_declaracoes` (temas do usuário, brief 040).
- Trecho de código:
  ```python
  @field_validator("interessa", "evitar", "sobre_o_usuario")
  @classmethod
  def lista_sem_duplicatas(cls, valor: list[str]) -> list[str]:
      return _sem_duplicatas(valor)[:_MAXIMO_INTERESSA]
  ```
- Justificativa existente no código/comentário: nenhuma para o corte (o nome do validador fala só da deduplicação; a constante `_MAXIMO_INTERESSA` da linha 18 não tem comentário).
- Por que isto é analítico: descarta entrada do usuário antes de qualquer análise. O caso de `evitar` é o mais grave: o sexto termo que o usuário mandou evitar deixa de ser conferido na mensagem. O corte reutiliza a constante de `interessa` para três campos de sentido diferente.

#### A2-027 — agente_nw/nucleo/modelos/pedido.py:93-101 — `PedidoExtraido.termos_pelo_menos_um_no_maximo_seis`
- Classe: C
- O que é cortado e quanto: `termos_busca` fica com no máximo 6 termos (`_MAXIMO_TERMOS_BUSCA = 6`).
- Qual decisão do produto depende desse corte: o que é buscado em notícia (e, via `_termos_do_pedido`, quais temas do usuário são reforçados ou criados).
- Trecho de código:
  ```python
  unicos = _sem_duplicatas(valor)
  if not unicos:
      raise ValueError("termos_busca precisa de pelo menos um termo")
  return unicos[:_MAXIMO_TERMOS_BUSCA]
  ```
- Justificativa existente no código/comentário: docstring das linhas 96-97 — "acima de seis, corta em vez de rejeitar — o modelo tende a listar demais, e uma nova tentativa custa mais do que o corte".
- Por que isto é analítico: termo cortado nunca vira busca; combina-se com `max_consultas_por_pedido = 4` (A2-015), que corta de novo mais adiante. A justificativa no código explica a escolha, mas não é aprovação.

#### A2-028 — agente_nw/nucleo/modelos/redacao.py:141 — `validar_ganchos`
- Classe: C
- O que é cortado e quanto: depois de todas as validações, ficam uma mensagem base e no máximo `MAXIMO_GANCHOS = 4` ganchos de notícia; o excedente cai sem entrar nos `motivos`. No mesmo caminho, mensagem acima do limite de palavras do registro (60/80/110) e título acima de 12 palavras são descartados inteiros (linhas 126-132).
- Qual decisão do produto depende desse corte: o que é entregue ao usuário na tela de ganchos e gravado em `gancho_uso` — portanto também o que realimenta moldes e histórico.
- Trecho de código:
  ```python
  return [*base, *aceitos[:MAXIMO_GANCHOS]], motivos
  ```
- Justificativa existente no código/comentário: docstring das linhas 98-104 — "fica uma base e até `MAXIMO_GANCHOS` ganchos de notícia".
- Por que isto é analítico: corta uma coleção de textos já produzidos. É corte de saída, não de entrada: cada mensagem é lida inteira pelas checagens (`sem_acento_e_caixa(gancho.mensagem)` cobre o texto todo). Registrado por ser "top N que descarta o resto" e por o descarte do 5º gancho não aparecer nos motivos mostrados.

#### A2-029 — agente_nw/perfil/agenda_google_csv.py:9-13, 37-40 — `_campo`, `ler_contatos`
- Classe: C
- O que é cortado e quanto: `_campo` devolve o **primeiro** valor de coluna que casa o prefixo e ignora os demais; a chamada pede explicitamente "phone 1 - value" e "e-mail 1 - value", descartando telefones e e-mails 2, 3, …
- Qual decisão do produto depende desse corte: a identificação e a deduplicação do contato na importação (`importador.py` casa por `telefone_ou_email`); um contato cujo número conhecido está em "phone 2" entra como pessoa diferente ou é ignorado.
- Trecho de código:
  ```python
  telefone=_campo(linha, "phone 1 - value"),
  email=_campo(linha, "e-mail 1 - value"),
  ```
- Justificativa existente no código/comentário: nenhuma.
- Por que isto é analítico: alimenta deduplicação/casamento de identidade, que as regras contam como análise. Não é truncamento de texto de conteúdo — as `notas` do CSV vão inteiras (linha 41) e os marcadores todos são lidos (linhas 28-32).

#### A2-030 — agente_nw/perfil/agenda_macos.py:91-93 — `ler_contatos.processar`
- Classe: C
- O que é cortado e quanto: dos telefones e e-mails do contato na agenda do Mac, só o primeiro de cada (`telefones[0]`, `emails[0]`) vai para o `ContatoBruto`.
- Qual decisão do produto depende desse corte: mesma cadeia de A2-029 (casamento e deduplicação de contato na importação).
- Trecho de código:
  ```python
  telefone=telefones[0] if telefones else None,
  email=emails[0] if emails else None,
  ```
- Justificativa existente no código/comentário: nenhuma.
- Por que isto é analítico: idem A2-029. A nota do contato, que é o texto de conteúdo deste arquivo, é lida inteira (linhas 78-83) e o aviso de notas não lidas (linha 105) é só `print` — apresentação.

#### A2-031 — agente_nw/perfil/inferencia.py:220-243 — `aplicar_declaracoes`
- Classe: R
- O que é cortado e quanto: cada frase que o usuário disse sobre si é lida só por três expressões regulares ancoradas no início (`_PADRAO_NOME`, `_PADRAO_NEGATIVO`, `_PADRAO_POSITIVO`, linhas 35-40); o que vale é apenas o `group(1)` capturado, e **frase que não casa nenhum padrão é ignorada por inteiro**.
- Qual decisão do produto depende desse corte: o perfil inferido do usuário — nome (`upsert_usuario`), "não me interessa" e temas `declarada`/`dominio`, que entram depois no cruzamento e na redação.
- Trecho de código:
  ```python
  casamento_positivo = _PADRAO_POSITIVO.match(limpa)
  termo = casamento_positivo.group(1).strip() if casamento_positivo is not None else ""
  if not termo or getattr(cliente_llm, "embeddar", None) is None:
      continue
  ```
- Justificativa existente no código/comentário: comentário das linhas 33-34 — "As frases de `sobre_o_usuario` chegam curtas e separadas (o prompt de extrair_pedido já pede isso); aqui só classificamos cada uma em nome / negativa / positiva por palavras-chave comuns em português" — e a docstring da linha 219: "frase sem padrão reconhecido é ignorada".
- Por que isto é analítico: o texto do usuário é substituído por um pedaço casado por regex (representação parcial) e o que não casa não é analisado por ninguém — nem por LLM, nem por embedding — embora o sistema siga como se tivesse lido o que ele disse. Soma-se ao corte em 5 frases de A2-026.

#### A2-032 — agente_nw/perfil/inferencia.py:262, 269 — `decair`
- Classe: NA
- O que é cortado e quanto: `hoje.strftime("%Y-%m")` guarda o mês do decaimento e `ultimo_uso_texto[:10]` pega a parte de data de um timestamp ISO 8601.
- Qual decisão do produto depende desse corte: o decaimento de peso de tema por inatividade (uma vez por mês, por calendário).
- Trecho de código:
  ```python
  ultimo_uso = datetime.fromisoformat(ultimo_uso_texto[:10]).date()
  ```
- Justificativa existente no código/comentário: docstring das linhas 256-258 ("no máximo um decaimento por tema por mês de calendário").
- Por que isto é NA: `[:10]` sobre um ISO 8601 é a data, e `%Y-%m` é o mês — identificadores de tempo, não texto de conteúdo cortado. A regra das linhas 79-83 das regras de auditoria cobre exatamente este caso.
