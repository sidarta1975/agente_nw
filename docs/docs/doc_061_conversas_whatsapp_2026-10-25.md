# Doc 061 — Conversas do WhatsApp como fonte sobre a pessoa

Brief: `docs/briefs/brief_061_conversas_whatsapp_2026-10-25.md`. Depende do brief 060 (`cadf946`). Executado em 2026-10-30.

## 1. Como ficou

**Leitor (`coleta/whatsapp/leitor.py`), função pura.** Reconhece os formatos iPhone (`[25/10/2026,
14:03:12] Nome: texto`) e Android (`25/10/2026 14:03 - Nome: texto`), ano com 2 ou 4 dígitos, segundos
opcionais, o caractere invisível de direção (`‎`) no começo da linha e mensagem de várias linhas
(linha sem data emenda à anterior). Descarta aviso do sistema (sem "Nome: " depois da data —
criptografia, mudança de número, ligação), `<Mídia oculta>`, "imagem/áudio/figurinha omitida" e
mensagem apagada. `ler_zip` lê, na memória, o `.txt` da conversa dentro do `.zip` (`_chat.txt` no
iPhone; senão o primeiro `.txt`), ignorando fotos e outros arquivos; `ler_arquivo` escolhe `ler_zip`
ou leitura direta pela extensão. Nada do arquivo enviado é gravado em disco — só o texto, depois,
no banco.

**Envio e confirmação (página da pessoa).** Bloco novo "Conversas do WhatsApp" com campo de arquivo
`multiple` (`.zip`/`.txt`, até 20 MB cada). `POST /pessoa/<id>/whatsapp/enviar` lê todos os arquivos
enviados na mesma submissão, mescla participantes e mensagens (ordenadas por data) e, com mais de 2
participantes, volta para a página da pessoa com "Por enquanto só conversa individual". Senão, guarda
a conversa lida num dicionário em memória do próprio processo do console (`pendentes_whatsapp`, chave
aleatória de `secrets.token_urlsafe`; reiniciar o console descarta) e mostra `whatsapp_confirmar.html`:
participantes, quantidade de mensagens, período (primeira a última data) e "Qual destes é você?" — com
o nome que bate com o perfil do usuário (`perfis.obter_usuario`, comparado sem acento/caixa) já marcado.
`POST /pessoa/<id>/whatsapp/confirmar` lê a conversa pendente pelo `pending_id`, chama
`importador.importar` com o nome escolhido como "você" e despacha o processamento de fatos na
`FilaDeTrabalho` que já existe (`despachar`, a mesma dos pedidos) — não bloqueia a resposta porque pode
levar dezenas de chamadas ao modelo. A página da pessoa volta mostrando "N mensagens novas, M já
estavam" e, enquanto a extração não termina, "processando conversa… (x de y blocos)"
(`fila_extracao.contar_whatsapp`, nova).

**Banco (migração 015).** Tabela `conversa_mensagem` (`perfil_id`, `autor` ∈ {contato, usuario},
`enviada_em`, `texto`, `hash`, `importada_em`), `UNIQUE(perfil_id, hash)`. `conversa.calcular_hash` usa
autor + data/hora + texto com espaços repetidos colapsados — reenviar a mesma exportação, ou uma mais
nova que repete mensagens antigas, não duplica nada (`inserir_mensagem` usa `INSERT OR IGNORE` e devolve
se gravou). `apagar_contato_completo` e `unir_contatos` (`nucleo/database/queries/perfis.py`) ganharam a
mesma cascata que `nota_contato` e `rede_sem_perfil` já tinham — apagar ou unir contato leva as mensagens
junto, como o brief pede.

**Fatos.** `conversa.blocos_por_mes` agrupa as mensagens **do contato** (nunca as do usuário) por mês,
do mais recente para o mais antigo, até `whatsapp.meses_extraidos` (24) meses, em blocos de até
`whatsapp.maximo_caracteres_bloco` (6000) caracteres; `importador.enfileirar_extracao` enfileira
(`fila_extracao`, origem `whatsapp:AAAA-MM`) só os meses que ainda não entraram na fila — reenviar não
reprocessa mês já extraído. `perfil/extrator.processar_fila` (não listado nos arquivos-alvo; ver seção 2)
agora grava o fato com a data do **mês** (primeiro dia), não o palpite do modelo sobre o dia exato,
quando `item.origem` começa com `whatsapp:` — é o que faz a marca `[antigo]` (brief 046) valer sozinha,
como o brief pede.

**Tom da relação na redação.** `nucleo/prompts/redigir_ganchos.py`: `EntradaRedacao` ganhou
`trocas_whatsapp`; o bloco HISTÓRICO passa a trazer, sob o título "Conversa recente no WhatsApp (para o
tom; não é fato atual)", as últimas `whatsapp.trocas_no_prompt` (10) mensagens, "você"/nome do contato,
em ordem. `cortar_por_tamanho` ganhou um segundo estágio: se o corte de histórico/fatos já existente
(brief 046) não bastar, `trocas_whatsapp` esvazia — as notas do usuário (brief 050) continuam
protegidas, nunca cortadas. `redacao.montar_entrada`/`redigir` ganharam o parâmetro
`trocas_whatsapp_no_prompt` (default 10, igual ao limiar), lido de `conversa.ultimas_trocas`.

**Limiares.** `WhatsappLimiares` (`meses_extraidos=24`, `maximo_caracteres_bloco=6000`,
`trocas_no_prompt=10`) em `nucleo/modelos/configuracao.py`, bloco `whatsapp` em `config/limiares.yaml`.
Nenhum número das três regras fica hardcoded no código.

## 2. Fora do que o brief pediu, mas necessário para o gate

O cabeçalho do brief não lista estes arquivos em "Arquivos-alvo", mas a própria seção 3 do brief exige
o comportamento que eles implementam, e a seção "Seções a ler" já apontava para dois deles como leitura
obrigatória — tratei como parte do pedido, não como iniciativa própria:

1. **`agente_nw/perfil/extrator.py`** — `processar_fila` agora sobrescreve `data_do_fato` com o mês
   (`item.origem.removeprefix("whatsapp:") + "-01"`) quando a origem é `whatsapp:AAAA-MM` (seção 3.5:
   "O fato fica com a data do mês"). Testado em
   `test_whatsapp_importador.py::test_fato_extraido_de_bloco_whatsapp_fica_com_a_data_do_mes`.
2. **`agente_nw/nucleo/database/queries/fila_extracao.py`** — nova `contar_whatsapp` (pendentes/total
   dos blocos de origem `whatsapp:*`), para o "processando conversa… (x de y blocos)" da seção 3.5.
3. **`agente_nw/nucleo/database/queries/perfis.py`** — `apagar_contato_completo` e `unir_contatos`
   ganharam a cascata de `conversa_mensagem` (seção 3.4: "Apagar ou unir contato leva as mensagens
   junto"); a própria seção 4 do brief pede o teste "unir contato leva as mensagens".
4. **`agente_nw/nucleo/orquestracao.py`** — uma linha (`trocas_whatsapp_no_prompt=limiares.whatsapp
   .trocas_no_prompt`) na chamada existente a `redacao_mod.redigir`, no mesmo padrão de
   `meses_fato_antigo=limiares.redacao.meses_fato_antigo` já ali. Sem essa linha, o tom do WhatsApp
   nunca chegaria à redação de verdade — ficaria só no parâmetro default da função.

Além disso, dois testes pré-existentes precisaram de ajuste, nenhum deles causado por lógica nova de
produto:

5. **`tests/test_migracao_comentarios.py`** — a asserção fixa `schema_version == 14` dependia de 14
   ser a última migração; com a 015 nova, a segunda chamada a `migracoes.aplicar(banco)` (sem pasta
   fixada) chega a 15. Ajustada para 15 — mesma classe de ajuste que o próprio brief 050 deve ter feito
   quando criou a migração 014.
6. **`tests/test_coleta_bloqueio.py`** — achado ao rodar a suíte inteira: o teste usa
   `datetime.now(UTC)` real para a segunda chamada a `coletar()` (hora da execução + cooldown de 180
   min); rodando perto de 22h UTC, a soma cai no dia seguinte, zera o progresso do ciclo
   (`data_ciclo`) e reprocessa a Fonte1 — nada a ver com este brief (arquivo e teste sem nenhuma
   mudança desde o brief 045, `agente_nw/coleta/rss/leitor.py` intocado). Perguntei a Sidarta como
   proceder (teste falhava de forma determinística, reproduzido 3x); ele decidiu que eu corrigisse o
   teste agora, fora do brief 061. Ajustei para usar `agora=` fixo (`coletar()` já aceita o parâmetro)
   nas duas chamadas, garantindo que ambas caem no mesmo dia — sem tocar `coleta/rss/leitor.py`.

## RELATÓRIO FINAL
- Brief executado: 061 — conversas do WhatsApp como fonte sobre a pessoa
- Arquivos criados: `agente_nw/coleta/whatsapp/__init__.py`, `agente_nw/coleta/whatsapp/leitor.py`,
  `agente_nw/coleta/whatsapp/importador.py`, `scripts/migracoes/015_conversa_whatsapp.sql`,
  `agente_nw/nucleo/database/queries/conversa.py`, `agente_nw/console/templates/whatsapp_confirmar.html`,
  `tests/fixtures/whatsapp_ios.txt`, `tests/fixtures/whatsapp_android.txt`,
  `tests/fixtures/whatsapp_ios.zip`, `tests/test_whatsapp_leitor.py`, `tests/test_whatsapp_importador.py`,
  `tests/test_whatsapp_no_prompt.py`, `docs/docs/doc_061_conversas_whatsapp_2026-10-25.md`,
  `logs/commit_061.txt`, `logs/arquivos_061.txt`
- Arquivos alterados (resumo em uma linha cada):
  - `agente_nw/console/app.py` — rotas `/pessoa/<id>/whatsapp/enviar` e `/confirmar`, dicionário em
    memória das conversas pendentes, processamento em segundo plano na `FilaDeTrabalho`
  - `agente_nw/console/templates/pessoa.html` — bloco de envio, aviso de progresso e resumo da importação
  - `agente_nw/nucleo/database/queries/fila_extracao.py` — nova `contar_whatsapp` (ver seção 2)
  - `agente_nw/nucleo/database/queries/perfis.py` — cascata de `conversa_mensagem` em apagar/unir (seção 2)
  - `agente_nw/nucleo/modelos/configuracao.py` — novo bloco `WhatsappLimiares`
  - `agente_nw/nucleo/orquestracao.py` — uma linha passando `trocas_whatsapp_no_prompt` (seção 2)
  - `agente_nw/nucleo/prompts/redigir_ganchos.py` — `trocas_whatsapp` no HISTÓRICO e no corte por tamanho
  - `agente_nw/nucleo/redacao.py` — `_trocas_whatsapp`, parâmetro novo em `montar_entrada`/`redigir`
  - `agente_nw/perfil/extrator.py` — data do fato fixada no mês para origem `whatsapp:*` (seção 2)
  - `config/limiares.yaml` — bloco `whatsapp`
  - `tests/test_migracao_comentarios.py`, `tests/test_coleta_bloqueio.py` — ver seção 2, itens 5 e 6
- Arquivos preservados literalmente na área afetada: `agente_nw/nucleo/pedido.py`,
  `agente_nw/nucleo/localizacao.py` (nenhuma rede social envolvida neste brief)
- Script de verificação (o gate, rodado pelo `scripts/agente_entregar.sh`; saída colada):
  ```
  manifesto 061: 24 arquivo(s)
  ruff check: ok
  ruff format: ok
  mypy: ok
  pytest: ok (820 passed, 5 deselected in 18.17s)
  lacunas do 061: 0 no Backlog, 3 em Pendências, 1 em Dívidas, 0 em Decisões
  ✓ brief 061: commit 4366f01, enviado ao GitHub
  ```
  Primeira tentativa falhou no commit: `docs/docs/doc_061_...md`, `logs/commit_061.txt` e
  `logs/arquivos_061.txt` estavam no manifesto, mas `docs/*` e `/logs/` ficam fora do git por desenho
  (só `AGENTS.md` é rastreado em `docs/`, nenhum arquivo em `logs/`) — corrigido tirando os três do
  manifesto, mesma causa do que já acontecera no brief 063.
- Comandos executados: `scripts/agente_entregar.sh 061`
- Manifesto do commit: `logs/arquivos_061.txt` e `logs/commit_061.txt` (conteúdo abaixo)
- Pendências e decisões que ficaram abertas: as três do próprio brief (§6), só Sidarta pode rodar o
  console de verdade com o Ollama local e exportações reais:
  1. Na página do amigo, enviar as duas exportações.
  2. Conferir na confirmação que "você" e o amigo estão certos e que a segunda exportação não duplicou.
  3. Depois que os fatos aparecerem, fazer um pedido para ele.
- Resumo, Doing, Backlog e Done do `docs/PLAN.md` atualizados: sim

## Lacunas

| # | Lacuna | Destino | Impacto |
|---|---|---|---|
| 1 | Teste real: enviar as duas exportações do mesmo amigo pelo console e conferir que a segunda não duplicou mensagem | pendência | nice |
| 2 | Teste real: confirmar "quem é você" e ver os fatos aparecerem (extração real pelo Ollama local) | pendência | nice |
| 3 | Teste real: fazer um pedido para o amigo depois dos fatos extraídos e ver o tom do WhatsApp na mensagem | pendência | nice |
| 4 | `tests/test_coleta_bloqueio.py` usava `datetime.now(UTC)` real e falhava perto da virada do dia em UTC; corrigido fora do brief 061 por decisão de Sidarta (ver seção 2, item 6) — vale conferir se outros testes de `coleta/` têm o mesmo padrão de hora real não fixada | dívida | nice |
