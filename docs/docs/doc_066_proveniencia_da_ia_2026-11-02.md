# Doc 066 — Proveniência do que a IA produziu

Brief: `docs/briefs/brief_066_proveniencia_da_ia_2026-11-02.md`. Depende do brief 064 (`4b0aefb`, já na
`main`). Conjunto `camada_de_ia` (064, 065, 066).

## 1. Como ficou

**3.1 — `VERSAO` em todo módulo de prompt.** Os onze módulos de `agente_nw/nucleo/prompts/`
(`avaliar_relacao_objetivo`, `cartao`, `cruzar_por_que`, `descrever_tema`, `desempatar_perfil`,
`extrair_de_texto`, `extrair_pedido`, `prerotular_calibracao`, `qualificar`, `redigir_ganchos`,
`rotular`) ganharam `VERSAO = "AAAA-MM-DD-1"` logo depois dos imports, antes de `ESQUEMA`. A data é a do
último commit que tocou o arquivo (`git log -1 --format=%ad --date=short`); para `qualificar` ela
coincide com a de `exemplos_conversavel.yaml` (2026-09-19), que faz parte do prompt. O conteúdo de
nenhum prompt mudou. `agente_nw/nucleo/prompts/__init__.py` ganhou `verificar_versoes()`: percorre o
pacote (`pkgutil.iter_modules(__path__)`), importa cada módulo e falha com `RuntimeError` citando cada
módulo sem `VERSAO` no formato `AAAA-MM-DD-n`. Ela roda em `config/container.py::configuracao()`, logo
depois da validação de `Roteamento` e `Limiares` (**escolha do "lugar que já valida a configuração"**:
`configuracao()` é por onde passam a CLI, o console e `verificar-ambiente` — este último já captura a
exceção e imprime `FALHA ao carregar configuração: ...`; pôr a checagem só em `verificar_ambiente`
não impediria o start do console nem dos outros comandos, que é o que o brief pede).

**3.2 — o cliente registra o que usou.** `ClienteOllama` ganhou:
- `gerar_json(..., imagens=None, versao_prompt=None)` — parâmetro novo, opcional;
- `proveniencia(tarefa_nome, versao_prompt=None) -> Proveniencia` — perfil ativo, modelo da tarefa e a
  versão recebida (o mesmo que vai para o log);
- `modelo_embedding` (propriedade) — o modelo de embedding do perfil ativo.

As três chamadas de `_registrar_log_chamada` (sucesso, conteúdo esgotado, transporte esgotado) gravam os
campos novos `perfil`, `modelo`, `versao_prompt` e `latencia_ms`, ao lado dos que já existiam (formato
da linha inalterado além disso). A latência é medida com `time.monotonic()` do início ao fim de
`gerar_json` — a chamada inteira, com a nova tentativa por conteúdo e as esperas do backoff de
transporte, que é o tempo que quem chamou esperou. Todo chamador cujo prompt vem de `nucleo/prompts/`
passa `versao_prompt=<modulo>.VERSAO` (redação, cartão, qualificar, rotular, cruzar_por_que,
avaliar_relacao_objetivo, extrair_de_texto, extrair_pedido, desempatar_perfil, prerotular_calibracao,
descrever_tema). Nos Protocols dos chamadores o parâmetro é só por palavra-chave (`*, versao_prompt`),
para não colidir com o `imagens` posicional do cliente real.

**3.3 — proveniência nos registros gerados.** Migração 019: `gerado_por_modelo`, `gerado_por_perfil` e
`gerado_por_prompt_versao` (`TEXT NULL`) em `gancho_uso`, `assunto`, `assunto_contato`, `fila_extracao` e
`fato`. Tudo o que já existe nasce `NULL`. Contrato novo `agente_nw/nucleo/modelos/proveniencia.py`
(`Proveniencia`, Pydantic `frozen`) e `colunas_gerado_por()` para as três colunas. Quem grava:

| Tabela | Gravado por | Tarefa cuja proveniência entra |
|---|---|---|
| `gancho_uso` | `gancho_uso.inserir_entregues(..., proveniencia=)` via `redacao.registrar` (a `Redacao` carrega `proveniencia`) | `redigir_ganchos` |
| `assunto` (cartão) | `assuntos.gravar_cartao(..., proveniencia=)` via `cartoes.gerar_cartao` | `cartao` |
| `assunto` (qualificação) | `assuntos.gravar_qualificacao(..., proveniencia=)` via `qualificador` | `qualificar` |
| `assunto_contato` | `assunto_contato.inserir(..., proveniencia=)` via `cruzamento` | `cruzar_por_que` (linha do menu com "por quê") ou `avaliar_relacao_objetivo` (descarte pelo juízo do objetivo) |
| `fila_extracao` | `fila_extracao.marcar_processado(..., proveniencia=)` via `perfil/extrator.processar_fila` | `extrair_de_texto` |
| `fato` | `fatos.inserir(..., proveniencia=)` (no próprio INSERT; os gatilhos de só-inserção seguem intactos) via `processar_fila` | `extrair_de_texto` |

**Decisão: o que é "pontuação de relevância".** As duas camadas receberam as colunas, por motivos
diferentes:
- `assunto_contato` é a pontuação de relevância propriamente dita: mora em `nucleo/relevancia/` (pasta e
  módulo `cruzamento`), é por contato e por consulta, e é ali que o modelo decide o que entra (o gate do
  049) e escreve o "por quê". A linha decidida só por embedding (piso, "fora do domínio", "evitado pelo
  contexto") fica com as três colunas `NULL` — nenhum modelo de geração a produziu (o vetor tem a
  própria proveniência, item 3.4). Se a chamada de `cruzar_por_que` falha e o "por quê" fica nulo, a
  linha também fica sem proveniência.
- `assunto` entra porque o brief pede o **cartão** (que vive em `assunto.resumo_cartao`), e as notas
  `substancial`/`conversavel` da qualificação, gravadas na mesma linha, também são pontuações geradas
  pelo modelo. **Limitação registrada:** é uma linha só e um trio de colunas só, escrito por duas tarefas
  em momentos diferentes (qualificar primeiro, cartão depois) — vale a proveniência do último gravador;
  depois do cartão, a da qualificação se perde. O título (`rotular`, `gravar_titulo`) não grava
  proveniência (ver lacuna 2).

**3.4 — proveniência do vetor, sem sobrescrever.** `vetor_tema`, `vetor_assunto` e `vetor_perfil` são
`vec0` e não aceitam `ALTER TABLE` (`virtual tables may not be altered`). E renomear uma `vec0` não
renomeia as tabelas-sombra (`<nome>_info`, `_chunks`, ...): testei `RENAME` + `CREATE` com o nome antigo
e deu `Could not create '_info' shadow table: table "vetor_tema_info" already exists`. A migração faz,
para cada uma: cópia para tabela `TEMP`, `DROP`, `CREATE VIRTUAL TABLE ... USING vec0(<id> INTEGER
PRIMARY KEY, <vetor> float[1024], +modelo_embedding TEXT NOT NULL)` e cópia de volta com
`modelo_embedding = 'bge-m3'` (backfill: os dois perfis de `config/llm_routing.yaml` usam `bge-m3`, e
`Roteamento.perfis_declaram_as_mesmas_tarefas` recusa perfis com modelos de embedding diferentes).
Validado num banco temporário populado antes da 019 e pela suíte. O `vec0` **não impõe** o `NOT NULL` de
coluna auxiliar (um INSERT sem a coluna grava `NULL`); quem impõe é a assinatura: `gravar_embedding`
(temas), `gravar_centroide` (assuntos, perfis) recebem `modelo_embedding: str` obrigatório.

Leitura: toda consulta que lê esses vetores recebe `modelo_embedding: str` obrigatório e filtra por ele
— `temas.listar_com_embedding`, `assuntos.obter_centroide`, `assuntos.listar_candidatos_qualificacao`,
`assuntos.listar_qualificados_nao_vistos`, `perfis.calcular_centroide`, `perfis.obter_centroide`,
`perfil_tema.listar_confirmados_com_embedding`, `perfil_tema.listar_do_contato_com_embedding` (esta sem
chamador hoje). Vetor de outro modelo é **ausente**: não aparece na lista, `obter_centroide` devolve
`None`, e a linha antiga fica no banco, intacta. Os chamadores pegam o modelo atual de
`cliente_llm.modelo_embedding` (Protocols de agrupador, configurador, inferência, cruzamento,
qualificador, redação e pedido ganharam a propriedade; `candidatos.selecionar*` recebem o valor do
cruzamento). Em `agrupador.agrupar`, os dois `assert centro is not None` viraram `continue`: com um
centróide de outro modelo, o candidato é pulado em vez de derrubar o agrupamento (é o "tratado como
ausente" do brief; antes da 019 o `None` era impossível ali). Nenhum recálculo automático (3.5).

## 2. Fora do que o brief pediu, mas necessário

- **Contrato novo** `agente_nw/nucleo/modelos/proveniencia.py` e campo `Redacao.proveniencia`
  (`nucleo/modelos/redacao.py`): sem eles a proveniência não chega de `redigir` a `registrar`. Efeito
  visível: `agente_nw pedir --json` passa a imprimir também `"proveniencia"` no JSON da redação.
- **Protocols dos chamadores** (`ClienteRedacao`, `ClienteCartao`, `ClienteQualificacao`,
  `ClienteCruzamento`, `ClientePedido`, `ClienteDesempate`, `ClientePrerrotulagem`, `ClienteInferencia`,
  `ClienteEmbeddagem` do agrupador e do configurador) ganharam `versao_prompt`, `proveniencia` e/ou
  `modelo_embedding`, conforme o que cada módulo usa.
- **Testes existentes (mecânico):** os clientes simulados de 42 arquivos de teste passaram a aceitar
  `versao_prompt` e herdar `tests/llm_falso.py::ProvenienciaFalsa` (que dá `modelo_embedding = "bge-m3"` e
  `proveniencia()`); as chamadas diretas a gravadores/leitores de vetor passaram
  `modelo_embedding="bge-m3"`; `test_migracao_comentarios.py`/`test_migracao_genero.py` 18→19. Nenhuma
  asserção de comportamento foi mudada. Rodei o ajuste em todos os testes e depois desfiz, arquivo a
  arquivo, o que não era preciso para a suíte passar (12 arquivos voltaram ao original).
- **Fora de `nucleo/prompts/` (leitura literal do brief):** `extrair_captura_rede_social`
  (`coleta/capturas/extrator.py`), `descrever_imagem` (`coleta/capturas/imagens.py`) e
  `extrair_termos_contato` (`nucleo/termos_contato.py`) montam o prompt fora do pacote, não ganharam
  `VERSAO` e não passam `versao_prompt` (o log registra `null` para eles, com perfil, modelo e latência
  normais). Os fatos que `coleta/capturas/leitor.py` e `nucleo/localizacao.py` gravam por esse caminho
  ficam com proveniência `NULL`. Ver lacuna 1.
- **Chamadas ao LLM sem resultado persistido próprio** (não ganharam colunas): `extrair_pedido` (só
  decide o fluxo do pedido), `desempatar_perfil` (escolhe um perfil; o vínculo gravado é decisão de
  localização), `prerotular_calibracao` (rótulo vai para o arquivo de calibração, não para tabela de
  resultado), `descrever_tema` (descrição de tema, catálogo e não resultado de geração por pedido). As
  quatro passam `versao_prompt`, então o log de chamadas as identifica.

## 3. Achado fora de escopo (não corrigido)

`ClienteOllama.gerar_json` (brief 064) deixa escapar `_GeracaoDegenerada` ("prediction aborted, token
repeat limit reached"): `_chamar_generate_com_backoff` a relança, mas o `try` em volta dela, em
`gerar_json`, só captura erro de `httpx`; o `except` que trata `_GeracaoDegenerada` está no segundo
`try`, que nunca a vê. Reproduzido num script à parte, com transporte simulado devolvendo 500 com essa
mensagem: a exceção sobe ao chamador como `_GeracaoDegenerada`, sem nova tentativa, sem `fila_revisao`
e sem linha no log — o contrário da armadilha 22. Não corrigi porque o brief 066 não cobre isso (AGENTS
§1, mudança cirúrgica): fica como dívida (lacuna 3). A correção é capturar `_GeracaoDegenerada` no
primeiro `try` e seguir para a próxima temperatura.

## RELATÓRIO FINAL
- Brief executado: 066 — Proveniência do que a IA produziu.
- Arquivos criados: `scripts/migracoes/019_proveniencia.sql`, `agente_nw/nucleo/modelos/proveniencia.py`,
  `tests/test_proveniencia.py`, `tests/llm_falso.py`.
- Arquivos alterados (com resumo da mudança em uma linha cada):
  - `agente_nw/nucleo/llm.py`: `versao_prompt` em `gerar_json`; `proveniencia()`; `modelo_embedding`;
    log com perfil, modelo, versão do prompt e latência nas três saídas.
  - `agente_nw/nucleo/prompts/__init__.py`: `verificar_versoes()`.
  - `agente_nw/nucleo/prompts/{avaliar_relacao_objetivo,cartao,cruzar_por_que,descrever_tema,desempatar_perfil,extrair_de_texto,extrair_pedido,prerotular_calibracao,qualificar,redigir_ganchos,rotular}.py`:
    só `VERSAO`.
  - `config/container.py`: `configuracao()` chama `prompts.verificar_versoes()`.
  - `agente_nw/nucleo/database/queries/gancho_uso.py`: `inserir_entregues(..., proveniencia=)`.
  - `agente_nw/nucleo/database/queries/assuntos.py`: proveniência em qualificação e cartão;
    `modelo_embedding` em `gravar_centroide`, `obter_centroide`, `listar_candidatos_qualificacao`,
    `listar_qualificados_nao_vistos`.
  - `agente_nw/nucleo/database/queries/assunto_contato.py`: `inserir(..., proveniencia=)`.
  - `agente_nw/nucleo/database/queries/fila_extracao.py`: `marcar_processado(..., proveniencia=)`.
  - `agente_nw/nucleo/database/queries/fatos.py`: `inserir(..., proveniencia=)` no INSERT.
  - `agente_nw/nucleo/database/queries/temas.py`: `modelo_embedding` em `gravar_embedding` e
    `listar_com_embedding`.
  - `agente_nw/nucleo/database/queries/perfis.py`: `modelo_embedding` em `calcular_centroide`,
    `gravar_centroide`, `obter_centroide`.
  - `agente_nw/nucleo/database/queries/perfil_tema.py`: `modelo_embedding` nas duas leituras com vetor.
  - `agente_nw/nucleo/modelos/redacao.py`: `Redacao.proveniencia`.
  - `agente_nw/nucleo/redacao.py`: passa `versao_prompt`, grava a proveniência da redação, lê temas pelo
    modelo atual.
  - `agente_nw/nucleo/relevancia/cruzamento.py`: proveniência do gate e do "por quê" em
    `assunto_contato`; modelo de embedding em todas as leituras/gravações de vetor.
  - `agente_nw/nucleo/relevancia/candidatos.py`: `modelo_embedding` nas duas seleções.
  - `agente_nw/nucleo/relevancia/qualificador.py`: `versao_prompt`, proveniência da qualificação,
    candidatos pelo modelo atual.
  - `agente_nw/nucleo/relevancia/cartoes.py`: `versao_prompt` e proveniência do cartão.
  - `agente_nw/nucleo/agrupamento/agrupador.py`: modelo de embedding nos centróides; centróide de outro
    modelo é pulado.
  - `agente_nw/nucleo/agrupamento/calibracao.py`, `agente_nw/nucleo/pedido.py`,
    `agente_nw/nucleo/localizacao.py`: só `versao_prompt` (e `modelo_embedding` no Protocol do pedido).
  - `agente_nw/perfil/extrator.py`: `versao_prompt`; proveniência no fato e no item da fila.
  - `agente_nw/perfil/configurador.py`, `agente_nw/perfil/inferencia.py`, `agente_nw/console/app.py`:
    modelo de embedding ao gravar/ler vetor de tema (`inferencia` também passa `versao_prompt`).
  - 42 arquivos `tests/test_*.py`: ajuste mecânico dos clientes simulados e das chamadas diretas
    (seção 2); `test_migracao_comentarios.py`/`test_migracao_genero.py` 18→19.
- Arquivos preservados literalmente na área afetada: conteúdo de todos os prompts (só a linha `VERSAO`);
  `vetor_item` e `itens.gravar_embedding`/`itens.listar_com_embedding`; gatilhos de `fato`;
  `coleta/capturas/*` e `nucleo/termos_contato.py`; os 12 arquivos de teste que o ajuste mecânico tocou
  e que voltaram ao original.
- Script de verificação (o gate, rodado pelo `scripts/agente_entregar.sh`; saída colada):
```
$ bash scripts/agente_entregar.sh 066
manifesto 066: 84 arquivo(s)
ruff check: ok
ruff format: ok
mypy: ok
pytest: ok (877 passed, 5 deselected in 24.87s)
lacunas do 066: 1 no Backlog, 0 em Pendências, 2 em Dívidas, 0 em Decisões
✓ brief 066: commit 18f405f, enviado ao GitHub
```
  Antes da entrega, rodado à mão:
```
$ .venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/mypy agente_nw && .venv/bin/python -m pytest -q
All checks passed!
283 files already formatted
Success: no issues found in 121 source files
877 passed, 5 deselected in 25.11s
```
- Comandos executados: os de cima; `.venv/bin/python -m pytest -q tests/test_proveniencia.py` (vermelho
  antes do código: 7 failed; depois 10 passed); scripts de validação da migração 019 e do vec0 num banco
  temporário do scratchpad; `bash scripts/agente_entregar.sh --simular 066`;
  `bash scripts/agente_entregar.sh 066`.
- Manifesto do commit (`logs/arquivos_066.txt` e `logs/commit_066.txt`, conteúdo colado; renomeados para `entregue_066_*` pela entrega):
```
logs/arquivos_066.txt:
agente_nw/console/app.py
agente_nw/nucleo/agrupamento/agrupador.py
agente_nw/nucleo/agrupamento/calibracao.py
agente_nw/nucleo/database/queries/assunto_contato.py
agente_nw/nucleo/database/queries/assuntos.py
agente_nw/nucleo/database/queries/fatos.py
agente_nw/nucleo/database/queries/fila_extracao.py
agente_nw/nucleo/database/queries/gancho_uso.py
agente_nw/nucleo/database/queries/perfil_tema.py
agente_nw/nucleo/database/queries/perfis.py
agente_nw/nucleo/database/queries/temas.py
agente_nw/nucleo/llm.py
agente_nw/nucleo/localizacao.py
agente_nw/nucleo/modelos/redacao.py
agente_nw/nucleo/pedido.py
agente_nw/nucleo/prompts/__init__.py
agente_nw/nucleo/prompts/avaliar_relacao_objetivo.py
agente_nw/nucleo/prompts/cartao.py
agente_nw/nucleo/prompts/cruzar_por_que.py
agente_nw/nucleo/prompts/descrever_tema.py
agente_nw/nucleo/prompts/desempatar_perfil.py
agente_nw/nucleo/prompts/extrair_de_texto.py
agente_nw/nucleo/prompts/extrair_pedido.py
agente_nw/nucleo/prompts/prerotular_calibracao.py
agente_nw/nucleo/prompts/qualificar.py
agente_nw/nucleo/prompts/redigir_ganchos.py
agente_nw/nucleo/prompts/rotular.py
agente_nw/nucleo/redacao.py
agente_nw/nucleo/relevancia/candidatos.py
agente_nw/nucleo/relevancia/cartoes.py
agente_nw/nucleo/relevancia/cruzamento.py
agente_nw/nucleo/relevancia/qualificador.py
agente_nw/perfil/configurador.py
agente_nw/perfil/extrator.py
agente_nw/perfil/inferencia.py
config/container.py
tests/test_agrupador.py
tests/test_assuntos.py
tests/test_assuntos_qualificacao.py
tests/test_calibracao.py
tests/test_candidatos.py
tests/test_candidatos_por_consulta.py
tests/test_cartoes.py
tests/test_cartoes_pendentes.py
tests/test_cli_pedir.py
tests/test_cli_pedir_confirmacao.py
tests/test_cli_pedir_redacao.py
tests/test_cli_qualificacao.py
tests/test_configurador.py
tests/test_console_configurar_perfil.py
tests/test_console_contatos.py
tests/test_console_eu.py
tests/test_console_temas.py
tests/test_contato_divergente.py
tests/test_cruzamento.py
tests/test_cruzamento_por_consulta.py
tests/test_evitar_implicito.py
tests/test_fluxo.py
tests/test_gate_lote_ordem.py
tests/test_gate_objetivo.py
tests/test_gate_zera_menu.py
tests/test_importar_temas.py
tests/test_inferencia_declaracoes.py
tests/test_inferencia_temas.py
tests/test_localizacao.py
tests/test_migracao_comentarios.py
tests/test_migracao_genero.py
tests/test_molde_adapta_genero.py
tests/test_molde_atributo_compartilhado.py
tests/test_moldes_so_confirmado.py
tests/test_orquestracao.py
tests/test_pedido_extrair.py
tests/test_pedido_resolver_contato.py
tests/test_perfis_centroide.py
tests/test_qualificador.py
tests/test_reconsulta_mesmo_dia.py
tests/test_redacao_redigir.py
tests/test_sem_censura_de_tema.py
tests/test_whatsapp_importador.py
tests/test_whatsapp_no_prompt.py
agente_nw/nucleo/modelos/proveniencia.py
scripts/migracoes/019_proveniencia.sql
tests/llm_falso.py
tests/test_proveniencia.py

logs/commit_066.txt:
feat(llm): proveniencia do que a IA produziu: versao de prompt, perfil, modelo e modelo de embedding (brief 066)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```
- Pendências e decisões que ficaram abertas: nenhuma pendência de Sidarta (o brief diz que não há teste
  real). Lacunas abaixo: uma de backlog, duas dívidas.
- Resumo, Doing, Backlog e Done do `docs/PLAN.md` atualizados: sim.

## Lacunas

| # | Lacuna | Destino | Impacto |
|---|---|---|---|
| 1 | `extrair_captura_rede_social`, `descrever_imagem` e `extrair_termos_contato` montam o prompt fora de `nucleo/prompts/`, sem `VERSAO` (brief 066 pediu só o pacote); os fatos gravados por `coleta/capturas/leitor.py` e `nucleo/localizacao.py` ficam com proveniência `NULL` | backlog | nice |
| 2 | `assunto` tem um trio só de colunas `gerado_por_*` para qualificação e cartão (vale o último gravador) e o título (`rotular`) não grava proveniência | dívida | nice |
| 3 | `ClienteOllama.gerar_json` (brief 064) deixa `_GeracaoDegenerada` ("token repeat limit") escapar ao chamador, sem nova tentativa, `fila_revisao` nem log — contrário da armadilha 22; o primeiro `try` só captura erro de `httpx` | dívida | degrada |
