# DOC 087 — Destino da fila de revisão: ver, reenviar e descartar o que o modelo não conseguiu

**Brief:** `docs/briefs/brief_087_destino_da_fila_de_revisao_2026-11-08.md`
**Data:** 2026-11-16
**Executor:** Claude Sonnet 5.5, `/executar 087` em série

---

## 1. O que foi feito

Todo item que foi para `fila_revisao` agora pode ser visto, reenviado ou descartado.

- **Migração 020** (`scripts/migracoes/020_fila_revisao_destino.sql`): `resolvido_em`, `resolucao` (`descartado`, `reenviado_ok`, `reenviado_falhou`) e `motivo`. Os itens antigos ficam com as três vazias (teste 5).
- **`queries/fila_revisao.py`**: `listar` (por tarefa, classe de erro e idade, **sem** a `entrada`), `contar`, `obter` (a única que devolve a `entrada`), `descartar`, `reenviar` e `classe_do_erro` (`json_invalido`, `geracao_degenerada`, `transporte`, `outro`).
- **CLI** `agente_nw revisao ver [--inteiro ID] [--todos] [--banco CAMINHO]`, `revisao descartar ID --motivo "..."`, `revisao reenviar ID`. `--banco` só existe em `ver`, para ler uma cópia.
- **Console**: tela `/revisao` (lista sem a entrada, descarta com motivo, reenvia), link "Revisão" nos bastidores. O padrão do console permitiu.
- **Regra do reenvio (3.2)**: só `extrair_de_texto` tem caminho de repetição. A linha de `fila_extracao` que falhou guarda `(fila_revisao id=N)` no `erro`; é por esse texto que o reenvio a acha, zera o erro e reprocessa só ela. `extrair_pedido` e `redigir_ganchos` guardam só o prompt montado, sem apontar para o pedido ou a consulta de origem: o comando diz isso e não faz nada. O item só vira `reenviado_ok` depois de o reprocessamento gravar resultado válido; com novo erro fica `reenviado_falhou`, continua na fila, e a linha que a nova falha abriu em `fila_revisao` é removida (não duplica a entrada). O vínculo é reescrito para o id original, então dá para reenviar de novo.

## 2. Desvios do escopo (a decidir se ficam)

O brief lista os arquivos-alvo; cinco arquivos fora da lista tiveram de mudar, sem mudar comportamento de produção:

| Arquivo | Mudança | Por quê |
|---|---|---|
| `agente_nw/perfil/extrator.py` | `processar_fila` passou a chamar `processar_item` (o corpo, intacto) e ganhou `reprocessador_de_item` | o reenvio precisa reprocessar **uma** linha; `processar_fila` só pega o lote pendente. Os testes do extrator são `llm_real` (pulados), então a refatoração está coberta só pelos meus testes de reenvio. |
| `agente_nw/nucleo/database/queries/fila_extracao.py` | `obter(id)` | ler uma linha |
| `tests/test_migracao_comentarios.py`, `tests/test_migracao_genero.py` | `MAX(versao) == 19` virou `== 20` | toda migração nova move esse número; nada mais foi mexido |
| `tests/test_executar_serie.py` | o `ambiente()` deixa de herdar `SERIE_DENTRO_DO_CAFFEINATE` | **defeito real da série**: rodando dentro de uma série o gate herda a marca, o `executar_serie.sh` pula o `caffeinate` e `test_caffeinate_e_osascript_sao_chamados` falha (`assert '-dimsu' in ''`). Sem isso nenhum brief entregaria em série. Com a variável tirada do ambiente: 24 passed. |
| `agente_nw/console/templates/base.html` | link para `/revisao` | acesso à tela |

## 3. Diagnóstico dos erros de `extrair_de_texto` (3.4)

**A cópia de 2026-10-25 não existe**: `dados/backups/` está vazio e o único banco daquela data é `dados/agente.db`, o real, que o executor não toca. `copiar-banco` respondeu `FALHA: nenhum backup encontrado`. O diagnóstico foi feito, só leitura, em três cópias de desenvolvimento de 13 a 15 de outubro (copiadas para `/tmp`). Só contagens e classes; nenhum texto.

| Cópia | Tarefa | itens | classe de erro | tem caminho de repetição |
|---|---|---|---|---|
| teste047 | `extrair_de_texto` | 181 | `json_invalido` | sim (133 com a linha de origem em `fila_extracao`) |
| teste047 | `redigir_ganchos` | 2 | `json_invalido` | não |
| teste047 | `extrair_pedido` | 1 | `json_invalido` | não |
| testeedy | `extrair_de_texto` | 197 | `json_invalido` | sim (133 com origem) |
| testeedy | `redigir_ganchos` | 2 | `json_invalido` | não |
| testeedy | `extrair_pedido` | 1 | `json_invalido` | não |
| console | `extrair_de_texto` | 126 | `json_invalido` | sim (126 com origem) |
| console | `extrair_pedido` | 1 | `json_invalido` | não |

Tipo do erro de validação do Pydantic (campo e `type=`), nas mesmas cópias:

| Cópia | `campos` · `model_type` | `campos.linguas` · `list_type` | outros |
|---|---|---|---|
| teste047 | 178 | 3 | `ganchos.N.por_que_para_esta_pessoa` · `string_too_short` 2; `objetivo` · `literal_error` 1 |
| testeedy | 194 | 3 | idem |
| console | 124 | 2 | `objetivo` · `literal_error` 1 |

Leitura: cerca de 98% dos erros de `extrair_de_texto` são o mesmo, o modelo devolve `campos` como algo que não é objeto (`model_type`), e o resto é `linguas` que não é lista. Não é janela, e nenhum é transporte nem geração degenerada. A maior `entrada` nas cópias é 12.687 caracteres (teste047/testeedy). Não corrigi: mexer no prompt ou no esquema muda `VERSAO` e o comportamento (Lacuna 1, destino "decisão"). `entrada` guarda o prompt inteiro, ou seja, texto de terceiros (3.5; Lacuna 4); a privacidade não mudou.

## 4. Algum texto é analisado só em parte?

**Não.** Este brief não monta prompt nem corta texto: a listagem esconde a `entrada` por privacidade, mas `obter`/`--inteiro` devolve o prompt inteiro, e o reenvio reconstrói o prompt com `construir_prompt(item.texto)` sobre o texto inteiro da linha de `fila_extracao`. A prova está em `tests/test_fila_revisao_destino.py` (`test_obter_devolve_a_entrada_inteira_so_quando_pedido`). Nenhuma ocorrência nova da varredura é corte de texto (apêndice A do relatório 079, grupo "Brief 087").

## 5. Relatório 079 (autorização de Sidarta, 2026-11-16)

Atualizados só para os arquivos que o brief criou ou alterou, sem ponto novo e sem exceção aprovada: seção 6 (linhas de `020_fila_revisao_destino.sql` e `test_fila_revisao_destino.py`; contagens de `cli.py`, `console/app.py`, `extrator.py`, `fila_extracao.py`, `fila_revisao.py` e `test_executar_serie.py`; `fila_revisao.py` deixou de ser "só INSERT"); todas as citações `arquivo:linha` desses arquivos renumeradas pela correspondência entre a versão anterior e a atual; apêndice A com o grupo "Brief 087" para as 8 ocorrências novas; texto corrido 320→322 arquivos e 1.290→1.295 ocorrências.

## RELATÓRIO FINAL

- Brief executado: 087
- Arquivos criados: `scripts/migracoes/020_fila_revisao_destino.sql`, `agente_nw/console/templates/revisao.html`, `tests/test_fila_revisao_destino.py`, este relatório
- Arquivos alterados: `agente_nw/nucleo/database/queries/fila_revisao.py` (listar, contar, obter, descartar, reenviar); `agente_nw/cli.py` (comando `revisao`); `agente_nw/console/app.py` (rotas `/revisao`); `agente_nw/console/templates/base.html` (link); `agente_nw/perfil/extrator.py` (`processar_item`, `reprocessador_de_item`); `agente_nw/nucleo/database/queries/fila_extracao.py` (`obter`); `tests/test_migracao_comentarios.py`, `tests/test_migracao_genero.py` (versão 19→20); `tests/test_executar_serie.py` (ambiente hermético); `docs/docs/doc_079_...md` (seção 6 e apêndice A, seção 5 acima); `docs/PLAN_agente_nw.md`
- Arquivos preservados literalmente na área afetada: `agente_nw/nucleo/llm.py` (`FalhaJsonInvalido`, `_ir_para_fila_revisao`), `relevancia/cartoes.py`, `relevancia/cruzamento.py`, `agrupamento/agrupador.py`, `scripts/verificar_auditoria_texto.py`, `.claude/hooks/guarda_comando.py`, os prompts e o esquema `RespostaExtracaoTexto`
- Script de verificação (o gate, rodado pelo `scripts/agente_entregar.sh`; a saída dele fica em `logs/entregar_ultimo.txt`). Antes dele, rodei os mesmos passos à mão:

```
$ .venv/bin/pytest tests/test_fila_revisao_destino.py -q
..................                                                       [100%]
18 passed in 1.34s
$ .venv/bin/ruff check . ; .venv/bin/ruff format --check . ; .venv/bin/mypy agente_nw
All checks passed!
293 files already formatted
Success: no issues found in 122 source files
$ .venv/bin/pytest -q
1121 passed, 5 deselected in 95.25s (0:01:35)
$ .venv/bin/python scripts/verificar_auditoria_texto.py
322 arquivos, 261 certificados, 54 cortam, 7 não analíticos, 0 não conferidos, 22 ponto(s) aguardando decisão de Sidarta
1295 ocorrência(s) da varredura mecânica, todas com destino no relatório
$ env -u SERIE_DENTRO_DO_CAFFEINATE .venv/bin/pytest -q tests/test_executar_serie.py
24 passed
```

- Critério 2 do brief (`agente_nw revisao ver --help`): **a trava recusou** o comando (`agente_nw nesta pasta usa o banco real`; `revisao` não está na lista `AGENTE_NW_LEITURA_EM_COPIA`, que só um brief altera) e não tentei contornar. A prova é o teste `test_ajuda_mostra_os_tres_subcomandos` (passou: `ver`, `descartar`, `reenviar` na ajuda de `revisao`) e `test_ver_aceita_banco_explicito_e_nao_abre_o_de_config`.
- Comandos executados: `pytest`, `ruff`, `mypy` e `verificar_auditoria_texto.py` como acima; consultas só de leitura (`sqlite3`, `mode=ro` ou cópia em `/tmp`) nas três cópias de desenvolvimento; `scripts/agente_entregar.sh 087`. Nenhum comando tocou `dados/agente.db`.
- Manifesto do commit: `logs/commit_087.txt` e `logs/arquivos_087.txt` (conteúdo no commit)
- Pendências e decisões que ficaram abertas: Lacunas abaixo
- Resumo, Doing, Backlog e Done do `docs/PLAN_agente_nw.md` atualizados: sim

## Lacunas

| # | Lacuna | Destino | Impacto |
|---|---|---|---|
| 1 | Cerca de 98% dos erros de `extrair_de_texto` nas cópias (178 de 181, 194 de 197, 124 de 126) são `campos` com `model_type`: o modelo devolve `campos` que não é objeto; o resto é `campos.linguas` que não é lista. A correção é no prompt ou no esquema, o que muda `VERSAO` e o comportamento; este brief não corrigiu | decisão | degrada |
| 2 | A cópia de 2026-10-25 não existe (`dados/backups/` vazio; `agente.db` é o banco real). O diagnóstico usou cópias de 13 a 15 de outubro; vale repetir `agente_nw revisao ver` na cópia que Sidarta fizer do banco atual | pendência | nice |
| 3 | A trava não deixa o executor rodar `agente_nw revisao ver --banco <cópia>` (nome fora de `AGENTE_NW_LEITURA_EM_COPIA`); só um brief libera nome novo | decisão | nice |
| 4 | A coluna `entrada` guarda o prompt inteiro, ou seja, texto de terceiros, no banco e agora também em `revisao ver --inteiro`; a privacidade não mudou (3.5) | backlog | nice |
| 5 | Parte dos itens antigos de `extrair_de_texto` não tem a linha de origem em `fila_extracao` (133 de 197 em testeedy): `reenviar` recusa esses com a mensagem de falta de vínculo e eles só podem ser descartados | nenhum | nice |
| 6 | `extrair_pedido` e `redigir_ganchos` não guardam o pedido ou a consulta de origem: sem caminho de repetição; guardar o vínculo na hora de inserir na fila exigiria mexer em `nucleo/llm.py` e nos três pontos que inserem | backlog | nice |
| 7 | `processar_item` (refatoração do `extrator.py`, fora dos arquivos-alvo) só tem cobertura nos testes de reenvio, porque os testes do extrator são `llm_real` e ficam fora do gate | nenhum | nice |
