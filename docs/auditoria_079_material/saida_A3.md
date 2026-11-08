# Auditoria "texto por inteiro" — parte A3 (CLI, console, ponte)

Prefixo de ponto: `A3`. Linhas conferidas com `wc -l` (2.903 no total, igual ao pedido).

## 1. Tabela de certificação

| Arquivo | Linhas lidas/total | Resultado | Evidência (uma linha) | Ponto |
| --- | --- | --- | --- | --- |
| `agente_nw/__init__.py` | 0/0 | CERTIFICADO | Arquivo vazio (0 bytes de conteúdo): não manipula texto de conteúdo, só marca o pacote. | — |
| `agente_nw/cli.py` | 1494/1494 | CORTA | Entrega ao núcleo a frase do pedido inteira (`orquestracao.entender_pedido(..., frase, ...)`, l. 860-873) e o texto do arquivo de temas inteiro, mas dois parâmetros que ela mesma calcula limitam o que o núcleo analisa: o teto diário de qualificação (l. 442) e o orçamento de tokens do prompt de redação (l. 921). | A3-001, A3-002, A3-003, A3-004, A3-005 |
| `agente_nw/console/__init__.py` | 0/0 | CERTIFICADO | Arquivo vazio (0 bytes): não manipula texto de conteúdo, só marca o pacote. | — |
| `agente_nw/console/app.py` | 1043/1043 | CORTA | O texto do pedido, a nota, o comentário e o `.txt`/`.zip` do WhatsApp vão inteiros ao núcleo (`fluxo_mod.criar_pedido`, `fila_extracao.inserir`, `whatsapp_leitor.ler_arquivo(arquivo.filename, dados)`), mas: o envio de WhatsApp acima de 20 MB é recusado (l. 465), o formulário de temas só lê 20 blocos (l. 1005), o embedding do tema deixa os sinônimos de fora (l. 947) e o `num_ctx` repassado ao fluxo é o que vira o orçamento de 73% do prompt (l. 164). | A3-006, A3-007, A3-008, A3-009, A3-010, A3-011, A3-012, A3-013, A3-014, A3-015 |
| `agente_nw/ponte/__init__.py` | 84/84 | CERTIFICADO | Não manipula texto de conteúdo: só infraestrutura (monta o comando que abre a URL da ponte no Chrome e guarda a ponte única do processo). | — |
| `agente_nw/ponte/servidor.py` | 282/282 | CERTIFICADO | O corpo do `POST /resultado` é lido por inteiro pelo `Content-Length` (`self.rfile.read(tamanho)`, l. 129-131) e o `dict` de `dados` é devolvido ao chamador sem tocar em nada dentro dele: não há limite de bytes de corpo, nem limite de leitura de socket, nem teto de número de blocos, nem recorte de texto em lugar nenhum do arquivo. | — |

### Observações de leitura em `ponte/servidor.py` (não são pontos)

- l. 129: `int(self.headers.get("Content-Length", "0"))` — sem o cabeçalho (p. ex. `Transfer-Encoding: chunked`) a leitura seria de 0 byte, mas isso perderia o corpo **inteiro** e cairia no `json.JSONDecodeError`/resposta 400, não analisaria uma parte. A extensão e a página-ponte usam `fetch` com corpo em string, que sempre manda `Content-Length`.
- l. 281-282: `dados = resposta.get("dados"); return dados if isinstance(dados, dict) else {}` — descarta a resposta inteira quando não é objeto; perda total, não parcial.
- Nenhum teto de quantidade de blocos, de tamanho de página ou de caracteres de texto capturado existe neste arquivo: o `LONG_POLL_S`, `SEM_CONTATO_S` e `_LIMITE_DO_AQUECIMENTO_S` são tempos de espera da ponte, não limites de conteúdo.

## 2. Pontos encontrados

#### A3-001 — agente_nw/cli.py:442 — `qualificar_cmd`
- Classe: C
- O que é cortado e quanto: o número de assuntos pendentes que entram na qualificação por execução — `--limite`, ou, sem ele, `limiares.qualificacao.teto_por_dia`. O resto dos pendentes não é analisado nessa rodada.
- Qual decisão do produto depende desse corte: prompt da tarefa de LLM de qualificação (`qualificador.qualificar_pendentes`, que gera título e decide se o assunto é qualificado); o que fica fora não recebe título nem entra no cruzamento daquela rodada.
- Trecho de código (1 a 3 linhas, copiado):
```
    limite_efetivo = limite if limite is not None else cfg.limiares.qualificacao.teto_por_dia
    resumo = qualificador.qualificar_pendentes(llm(), banco(), limite_efetivo)
```
- Justificativa existente no código/comentário (cite o lugar) ou "nenhuma": nenhuma em `cli.py`; o nome do limiar (`qualificacao.teto_por_dia`, em `config/limiares.yaml`) é a única pista, e nome não é justificativa escrita.
- Por que isto é analítico (T/C/R/P) ou só apresentação/log/identificador (NA): é corte de coleção decidido na camada de apresentação e passado ao núcleo como argumento — nada é impresso aqui, o `limite` governa quantos itens o LLM vê. Atenuante a registrar: o item não qualificado continua pendente e pode ser qualificado numa execução seguinte, então é um teto de lote, não um descarte definitivo.

#### A3-002 — agente_nw/cli.py:921 — `pedir_cmd` (chamada de `orquestracao.preparar_e_redigir`)
- Classe: C (com componente P)
- O que é cortado e quanto: o orçamento do prompt de redação é fixado em 73% do `num_ctx` da tarefa `redigir_ganchos` (`FRACAO_DO_CONTEXTO_NO_PROMPT = 0.73`, `agente_nw/nucleo/fluxo.py:34`). Com esse orçamento estourado, `agente_nw/nucleo/prompts/redigir_ganchos.py:280-298` (`cortar_por_tamanho`) reduz o histórico a **1 consulta** e os fatos a **5**, e depois tira os moldes.
- Qual decisão do produto depende desse corte: o prompt da tarefa de LLM `redigir_ganchos` — a mensagem base, a peculiaridade e os ganchos são escritos sem o histórico e sem os fatos que ficaram fora.
- Trecho de código (1 a 3 linhas, copiado):
```
    num_ctx = config.roteamento.perfis[config.roteamento.perfil_ativo].tarefas["redigir_ganchos"].num_ctx
...
            limite_tokens=int(num_ctx * FRACAO_DO_CONTEXTO_NO_PROMPT),
```
- Justificativa existente no código/comentário (cite o lugar) ou "nenhuma": comentário em `agente_nw/nucleo/fluxo.py:34` — `FRACAO_DO_CONTEXTO_NO_PROMPT = 0.73  # 8192 de contexto → ~6000 tokens estimados de prompt`; e a docstring de `cortar_por_tamanho` (`redigir_ganchos.py:281-283`) descreve o corte ("fica com 1 consulta de histórico e 5 fatos"). Nenhum dos dois é aprovação escrita do dono.
- Por que isto é analítico (T/C/R/P) ou só apresentação/log/identificador (NA): `cli.py` é a origem do número que faz o núcleo descartar histórico e fatos antes do prompt; o corte material está nos dois arquivos do núcleo citados (outra parte da auditoria), mas o parâmetro nasce aqui. Nada disso é tela ou log.

#### A3-003 — agente_nw/cli.py:501 — `menu_cmd`
- Classe: NA
- O que é cortado e quanto: os registros com `status == "descartado"` saem da lista antes do `print`.
- Qual decisão do produto depende desse corte: só a tela (o que o terminal imprime no `menu`); nenhum LLM, embedding ou gravação depende dessa lista.
- Trecho de código (1 a 3 linhas, copiado):
```
    registros = [r for r in assunto_contato.listar_do_dia(conn, perfil.id, hoje) if r.status != "descartado"]
```
- Justificativa existente no código/comentário (cite o lugar) ou "nenhuma": nenhuma.
- Por que isto é analítico (T/C/R/P) ou só apresentação/log/identificador (NA): apresentação. A lista filtrada só alimenta os `print` das linhas 506-511 e a função devolve 0; o estado `descartado` já foi decidido antes, no banco.

#### A3-004 — agente_nw/cli.py:1068 — `_ler_chamadas_llm`
- Classe: NA
- O que é cortado e quanto: `[:10]` sobre o campo `quando` de cada linha do JSONL de chamadas de LLM — pega o dia de um ISO 8601.
- Qual decisão do produto depende desse corte: só o relatório impresso por `certificar_cmd` (contagem de chamadas e de sucesso na primeira tentativa).
- Trecho de código (1 a 3 linhas, copiado):
```
        dia = str(registro.get("quando", ""))[:10]
        if desde <= dia <= ate:
```
- Justificativa existente no código/comentário (cite o lugar) ou "nenhuma": nenhuma.
- Por que isto é analítico (T/C/R/P) ou só apresentação/log/identificador (NA): identificador/data — é exatamente o caso que as regras citam (`data[:10]` para pegar o dia). O arquivo é lido linha por linha, todas as linhas (`.splitlines()`, l. 1066), e nenhum texto de conteúdo é tocado.

#### A3-005 — agente_nw/cli.py:1010-1014 — `listas_ver_cmd`
- Classe: NA
- O que é cortado e quanto: com `--filtro`, só as entradas da lista da rede que casam com o texto digitado são buscadas (`filtrar_por_texto`) em vez de todas (`listar_por_rede`).
- Qual decisão do produto depende desse corte: só a tela — as entradas são impressas e o total é impresso (l. 1015-1018).
- Trecho de código (1 a 3 linhas, copiado):
```
        queries_listas.filtrar_por_texto(conn, rede, filtro)
        if filtro
        else queries_listas.listar_por_rede(conn, rede)
```
- Justificativa existente no código/comentário (cite o lugar) ou "nenhuma": nenhuma (é o próprio `--filtro` pedido pelo usuário).
- Por que isto é analítico (T/C/R/P) ou só apresentação/log/identificador (NA): apresentação, e o recorte é o que o usuário digitou. Nada aqui alimenta prompt, embedding ou gravação.

#### A3-006 — agente_nw/console/app.py:164 — `_dependencias`
- Classe: C (com componente P)
- O que é cortado e quanto: o `num_ctx` da tarefa `redigir_ganchos` é entregue ao fluxo em `Dependencias.num_ctx_redacao`, e `agente_nw/nucleo/fluxo.py:364` o multiplica por `FRACAO_DO_CONTEXTO_NO_PROMPT` (0,73), orçamento que faz `cortar_por_tamanho` reduzir o histórico a 1 consulta e os fatos a 5.
- Qual decisão do produto depende desse corte: o prompt da tarefa de LLM `redigir_ganchos` de todo pedido feito pelo console (o caminho normal do produto, brief 039).
- Trecho de código (1 a 3 linhas, copiado):
```
            num_ctx_redacao=perfil_llm.tarefas["redigir_ganchos"].num_ctx,
```
- Justificativa existente no código/comentário (cite o lugar) ou "nenhuma": nenhuma em `app.py`; só o comentário de `fluxo.py:34` já citado em A3-002.
- Por que isto é analítico (T/C/R/P) ou só apresentação/log/identificador (NA): mesmo caso de A3-002 pelo lado do console — é o parâmetro de onde sai o corte de histórico e de fatos antes do prompt. É o gêmeo de `cli.py:921`; o corte material fica em `fluxo.py`/`redigir_ganchos.py`.

#### A3-007 — agente_nw/console/app.py:465 (constante na l. 64) — `pessoa_whatsapp_enviar`
- Classe: C
- O que é cortado e quanto: cada `.zip`/`.txt` de conversa acima de `_MAXIMO_BYTES_WHATSAPP = 20 * 1024 * 1024` é recusado — a conversa inteira daquele arquivo não é lida nem importada, e o usuário recebe "maior que 20 MB".
- Qual decisão do produto depende desse corte: o importador de WhatsApp (`whatsapp_leitor.ler_arquivo` → `whatsapp_importador.importar` → `enfileirar_extracao` → `extrator.processar_fila`, isto é, extração de fatos por LLM a partir das mensagens). Um histórico longo com mídia pode passar de 20 MB e então nenhum fato dele é extraído.
- Trecho de código (1 a 3 linhas, copiado):
```
            if len(dados) > _MAXIMO_BYTES_WHATSAPP:
                return redirect(
                    url_for("pessoa", perfil_id=perfil_id, erro=f"{arquivo.filename}: maior que 20 MB.")
```
- Justificativa existente no código/comentário (cite o lugar) ou "nenhuma": comentário na l. 64 — `_MAXIMO_BYTES_WHATSAPP = 20 * 1024 * 1024  # cada .zip ou .txt enviado (brief 061)`. Cita o brief, mas não é aprovação escrita de exceção ao princípio.
- Por que isto é analítico (T/C/R/P) ou só apresentação/log/identificador (NA): é a porta de entrada do texto de WhatsApp para o núcleo, não tela nem log. Dúvida registrada: o arquivo é **recusado por inteiro**, com erro visível, e não analisado em parte — não há truncamento silencioso; o que se perde é a possibilidade de analisar aquela conversa, não um pedaço dela.

#### A3-008 — agente_nw/console/app.py:474 — `pessoa_whatsapp_enviar`
- Classe: NA
- O que é cortado e quanto: conversa com mais de 2 participantes é recusada inteira ("Por enquanto só conversa individual.").
- Qual decisão do produto depende desse corte: o importador de WhatsApp — uma conversa de grupo não gera mensagem nem fato nenhum.
- Trecho de código (1 a 3 linhas, copiado):
```
        if len(conversa.participantes) > 2:
            return redirect(
                url_for("pessoa", perfil_id=perfil_id, erro="Por enquanto só conversa individual.")
```
- Justificativa existente no código/comentário (cite o lugar) ou "nenhuma": nenhuma no código (o texto do erro diz "por enquanto").
- Por que isto é analítico (T/C/R/P) ou só apresentação/log/identificador (NA): não é T/C/R/P porque nada é analisado em parte — é um escopo de produto (só conversa individual) recusado por inteiro e com aviso na tela. Fica listado porque decide o que entra na análise.

#### A3-009 — agente_nw/console/app.py:947 — `atualizar_tema`
- Classe: R
- O que é cortado e quanto: o tema é embeddado como `"{nome}: {descricao}"`; os sinônimos que o usuário acabou de gravar na linha anterior (l. 944-945) ficam fora do texto embeddado.
- Qual decisão do produto depende desse corte: o embedding do tema (`cliente.embeddar`, modelo de embedding do perfil) gravado em `temas.embedding` — é o vetor usado no agrupamento/cruzamento para decidir se um assunto casa com um tema do usuário. O vetor passa a representar o tema sem os sinônimos pelos quais o assunto costuma aparecer na notícia.
- Trecho de código (1 a 3 linhas, copiado):
```
        vetor = cliente.embeddar([f"{tema.nome}: {descricao}"])[0]
        queries_temas.gravar_embedding(conn, tema_id, vetor, cliente.modelo_embedding)
```
- Justificativa existente no código/comentário (cite o lugar) ou "nenhuma": nenhuma.
- Por que isto é analítico (T/C/R/P) ou só apresentação/log/identificador (NA): é representação parcial antes de uma análise — o texto que o usuário forneceu sobre o tema (nome, descrição e sinônimos) é trocado por um subconjunto e o vetor é usado como se representasse o tema todo. O mesmo recorte aparece em `agente_nw/perfil/configurador.py:29` (`embeddar([f"{tema.nome}: {tema.descricao}"])`), arquivo de outra parte da auditoria — vale como prova de que o padrão é o mesmo nos dois caminhos.

#### A3-010 — agente_nw/console/app.py:1005 — `configurar_perfil_usuario`
- Classe: C
- O que é cortado e quanto: o formulário é lido com `range(20)`: só os 20 primeiros blocos `tema_<i>_` são considerados; um 21º tema enviado seria ignorado em silêncio.
- Qual decisão do produto depende desse corte: `configurador.salvar_perfil_usuario`, que embedda cada tema e grava o centróide — ou seja, os temas que definem o que interessa ao usuário no cruzamento.
- Trecho de código (1 a 3 linhas, copiado):
```
            for i in range(20):
                tema = _monta_tema_usuario_do_form(f"tema_{i}_")
```
- Justificativa existente no código/comentário (cite o lugar) ou "nenhuma": nenhuma.
- Por que isto é analítico (T/C/R/P) ou só apresentação/log/identificador (NA): corte de coleção de entrada do usuário imediatamente antes de uma etapa que embedda cada item; não há aviso ao usuário de que o 21º tema caiu. Atenuante: o formulário servido (`sem_usuario.html`, ver A3-011) oferece 5 blocos, então na prática o teto de 20 só é alcançável por envio fora da tela.

#### A3-011 — agente_nw/console/app.py:133 — `_sem_usuario`
- Classe: NA
- O que é cortado e quanto: a tela de primeira configuração é renderizada com `quantidade_slots=5` — cinco campos de tema, embora o handler leia até 20 (A3-010).
- Qual decisão do produto depende desse corte: quantos temas o usuário consegue digitar nessa tela; o que ele digita vai inteiro ao `salvar_perfil_usuario`.
- Trecho de código (1 a 3 linhas, copiado):
```
        return render_template("sem_usuario.html", quantidade_slots=5, erro=erro)
```
- Justificativa existente no código/comentário (cite o lugar) ou "nenhuma": nenhuma.
- Por que isto é analítico (T/C/R/P) ou só apresentação/log/identificador (NA): apresentação — é o número de campos do formulário, não um recorte de texto já existente; nada que o usuário escreveu é descartado por essa constante, e temas adicionais podem ser criados depois em `/temas/novo`.

#### A3-012 — agente_nw/console/app.py:248 — `inicio`
- Classe: NA
- O que é cortado e quanto: a lista de contatos da tela inicial traz 50 resultados com busca e 20 sem busca.
- Qual decisão do produto depende desse corte: só a tela única (`inicio.html`) — a lista de onde o usuário clica para escolher um contato.
- Trecho de código (1 a 3 linhas, copiado):
```
        contatos = perfis.listar_para_inicio(conn, termo, 50 if termo else 20)
```
- Justificativa existente no código/comentário (cite o lugar) ou "nenhuma": nenhuma.
- Por que isto é analítico (T/C/R/P) ou só apresentação/log/identificador (NA): apresentação. Dúvida registrada: quem escolhe é o usuário, e um contato fora dos 50 primeiros não aparece para ele — mas o programa não decide nada com essa lista (o reconhecimento do contato acontece no núcleo, a partir do texto do pedido, não desta lista).

#### A3-013 — agente_nw/console/app.py:316-326 — `lista_do_pedido`
- Classe: NA
- O que é cortado e quanto: paginação de 20 entradas por página da lista da rede social; a página mostra o total e se há mais.
- Qual decisão do produto depende desse corte: só a tela de escolha do perfil na lista (`pedido_lista.html`).
- Trecho de código (1 a 3 linhas, copiado):
```
        por_pagina = 20
            entradas=entradas[inicio_pagina : inicio_pagina + por_pagina],
            total=len(entradas),
```
- Justificativa existente no código/comentário (cite o lugar) ou "nenhuma": nenhuma.
- Por que isto é analítico (T/C/R/P) ou só apresentação/log/identificador (NA): apresentação — a coleção inteira vem de `fluxo_mod.entradas_da_lista` e continua acessível pelas páginas seguintes; o recorte não entra em prompt nem em filtro do programa.

#### A3-014 — agente_nw/console/app.py:409 — `pessoa`
- Classe: NA
- O que é cortado e quanto: `fatos.listar_recentes(conn, perfil_id, 15)` — só os 15 fatos mais recentes do contato vão ao template.
- Qual decisão do produto depende desse corte: só a tela `pessoa.html`.
- Trecho de código (1 a 3 linhas, copiado):
```
            fatos=fatos.listar_recentes(conn, perfil_id, 15),
```
- Justificativa existente no código/comentário (cite o lugar) ou "nenhuma": nenhuma.
- Por que isto é analítico (T/C/R/P) ou só apresentação/log/identificador (NA): apresentação — o valor só é passado a `render_template`. Os fatos que entram no prompt de redação são lidos no núcleo (`nucleo/`), não aqui, então este 15 não afeta nenhuma decisão do programa.

#### A3-015 — agente_nw/console/app.py:492-493 — `pessoa_whatsapp_enviar`
- Classe: NA
- O que é cortado e quanto: a tela de confirmação mostra só a data da primeira e da última mensagem (`mensagens[0]`, `mensagens[-1]`), além do total.
- Qual decisão do produto depende desse corte: só a tela `whatsapp_confirmar.html`; a conversa inteira fica em `pendentes_whatsapp[pending_id]` e é essa que vai ao importador na confirmação (l. 500-508).
- Trecho de código (1 a 3 linhas, copiado):
```
            total_mensagens=len(conversa.mensagens),
            primeira_data=conversa.mensagens[0].quando.date().isoformat() if conversa.mensagens else None,
            ultima_data=conversa.mensagens[-1].quando.date().isoformat() if conversa.mensagens else None,
```
- Justificativa existente no código/comentário (cite o lugar) ou "nenhuma": comentário nas l. 181-183 explica que a conversa pendente fica em memória no processo do console.
- Por que isto é analítico (T/C/R/P) ou só apresentação/log/identificador (NA): apresentação/identificador de data — nada da conversa é descartado; `_mesclar_conversas` (l. 185-190) ordena e mantém **todas** as mensagens de **todos** os arquivos enviados, e é esse objeto que o importador recebe.
