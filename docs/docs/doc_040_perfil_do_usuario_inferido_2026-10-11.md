# Doc 040 — Perfil do usuário inferido, não cadastrado

Brief: `docs/briefs/brief_040_perfil_do_usuario_inferido_2026-10-11.md`. Depende do brief 036
(`322341c`). Executado em 2026-10-31. O arquivo em disco estava numa versão antiga do brief (cabeçalho
sem Conjunto/Arquivos-alvo/Modelo/Esforço/Teste de aceite, ainda com "Sidarta roda `scripts/verificar.sh`,
o teste real e o commit" no passo 7) — substituído pelo conteúdo colado no Projeto antes de executar
(AGENTS §10, mesmo precedente dos briefs 048/049).

## 1. Como ficou

**Fonte dos temas: os pedidos (3.1).** `perfil/inferencia.py::atualizar_temas_do_usuario`, chamada ao
fim de `nucleo/pedido.py::processar`, lê `assunto_principal`, `interessa` e `termos_busca` do pedido.
Cada termo casa com um tema existente por nome, sinônimo ou cosseno do embedding ≥
`temas_usuario.similaridade_mesmo_tema` (0,85) — senão cria um tema novo (`descrever_tema`, tarefa nova,
ver seção 2). Cada toque grava uma linha em `tema_uso` (migração 017) e soma 1 ao peso (teto 5); o nível
sobe pela frequência na janela (`usos_para_interesse`=3 em 30 dias, `usos_para_dominio`=6 em 90) e nunca
desce aqui — só `decair()` reduz, por inatividade. Pedido com `objetivo='apresentar'` leva o tema direto
a `dominio`. **Leitura do brief 3.1:** o item diz "termo novo... `nivel='interesse'`", mas a própria
seção de testes do brief descreve "termo novo cria tema `conversa`/`curiosidade`" — segui a regra de
frequência (bullet seguinte do mesmo item, e o que o teste de aceite pede): 1 uso é `curiosidade`, nunca
`interesse` direto.

**O que o usuário disse sobre si vale mais (3.2/3.3).** `PedidoExtraido.sobre_o_usuario: list[str]`
(novo campo; o prompt de `extrair_pedido` já pede frases curtas e separadas, uma por afirmação, para não
precisar interpretar sentença composta). `perfil/inferencia.py::aplicar_declaracoes` classifica cada
frase por padrão: "me chamo X"/"sou o X"/"sou a X" atualiza o nome (`perfis.upsert_usuario`); "não me
interessa X"/"não entendo nada de X"/"não gosto de X"/"não tenho mais interesse em X" grava X em
`perfil.preferencias_json.nao_me_interessa` (coluna nova, migração 017) **e** remove o tema se ele já
existia (por nome/sinônimo exato — nunca por similaridade, para não apagar por aproximação); o resto
("sou X", "gosto de X", "curto X", "pratico X", ou a frase inteira sem prefixo reconhecido) vira tema
`origem='declarada'`, `nivel='dominio'`, peso 5. Frase sem nenhum padrão reconhecido é ignorada, sem
erro. Chamada de dois lugares: `nucleo/pedido.py::processar` (toda vez que `sobre_o_usuario` não é
vazio) e a nova rota `/eu/contar`.

**Decaimento (3.1, último bullet).** `decair(conexao, hoje, limiares)`: tema `origem != 'declarada'` sem
uso (via `tema_uso`, ou `registrado_em` se nunca foi tocado) há mais que `dias_para_decair` (180) perde 1
de peso, nunca abaixo de 1. Idempotente por **mês de calendário** (coluna nova
`perfil_tema.peso_decaido_em`, migração 017) — mais forte que "idempotente por dia", que é o que o brief
pede. **Limite assumido:** a cada chamada decai no máximo 1 ponto, mesmo que o usuário fique muitos
meses sem nenhum pedido (sem agendamento — AGENTS §6 — não há como "passar" `decair()` nos meses vazios);
o ponto perdido recupera-se com qualquer uso novo do tema, então o efeito prático é pequeno (peso 1–5).

**Tela Eu (3.4).** `eu.html` perdeu o formulário de temas; mostra os temas por nível (peso e última
menção, de `tema_uso`), a lista "não me interessa", uma caixa "conte algo sobre você" (`POST
/eu/contar` → `pedido.extrair` seguido de `aplicar_declaracoes`; não grava `pedido` nenhum, é extração
pura) e o botão "esquecer tudo o que você inferiu sobre mim" (`POST /eu/esquecer` →
`inferencia.esquecer_inferidos`, que zera só `origem='conversa'`; `confirm()` no JS do próprio botão). A
rota antiga `/eu/configurar` (cadastro manual com formulário) e a tela `/temas` continuam existindo, só
sem link a partir de `eu.html` — bastidor, como o brief já previa para `importar-temas`/`temas.yaml`.

**`nao_me_interessa` como evitar implícito (item 7).** `relevancia/cruzamento.py::cruzar_contato_por_consulta`
(o caminho por consulta do pedido, brief 034) junta `perfis.listar_nao_me_interessa(usuário)` ao
`contexto.evitar` antes de `candidatos.selecionar_por_consulta`. `cruzar_contato` (a função sem
consulta, de um fluxo mais antigo) não tem noção de `evitar` nenhuma hoje — fora do escopo deste brief,
que fala em "todo pedido" e o caminho por pedido é o por consulta.

**Instalação (3.5).** `scripts/instalar_macos.sh` e `AGENTS.md` já não mencionam `importar-temas` nem
`temas.yaml` — conferido por busca antes de tocar; nenhum dos dois foi editado (provavelmente já
atualizados por um brief posterior, executado antes deste por decisão do Sidarta). Só
`cli.py::verificar_ambiente` precisou de ajuste: `ItemVerificacao` ganhou `informativo: bool = False`
(nunca gera AVISO/FALHA mesmo com `ok=False`); "temas.yaml existe" passa a imprimir `INFO` em vez de
`AVISO` quando o arquivo não existe. "fontes.yaml existe" continua como estava (`AVISO`), por não ser
pedido do brief.

**Resiliência do cliente sem `embeddar`** (não pedida, necessária para não quebrar testes existentes —
ver seção 2).

## 2. Fora do que o brief pediu, mas necessário

- **Migração renumerada.** O brief (escrito em 2026-10-11) chamava o arquivo de `011_...sql`; esse
  número já pertence a `011_pedido_fluxo.sql` (brief 039). Usei `017_preferencias_usuario_temas.sql`,
  o próximo livre, e documentei isso no cabeçalho do próprio SQL.
- **Caminho do cruzamento.** O brief cita `agente_nw/relevancia/cruzamento.py`; o caminho real é
  `agente_nw/nucleo/relevancia/cruzamento.py`.
- **`ClientePedido` (nucleo/pedido.py) ganhou `embeddar`** no protocolo, ao lado de `gerar_json` — a
  inferência de temas precisa de embeddings e é chamada de dentro de `processar`.
- **Resiliência sem `embeddar`/sem resposta boa do modelo.** `atualizar_temas_do_usuario` devolve sem
  fazer nada se o cliente não tem `embeddar` (mesmo padrão de `redacao._escolher_fatos`); `_criar_tema`
  cai para `descricao=termo, sinonimos=[]` se `descrever_tema` falhar, e ignora falha ao gravar o
  embedding. Sem isso, várias suítes de CLI (`test_cli_pedir*.py`, `test_orquestracao.py`,
  `test_coleta_rotulo_fonte.py`) quebrariam: `cli.pedir_cmd` agora sempre passa
  `limiares_temas_usuario` real (não `None`), e os clientes falsos dessas suítes não implementam
  `embeddar`.
- **`orquestracao.entender_pedido` e `pedido.processar` ganharam `limiares_temas_usuario` opcional**
  (`None` desliga a inferência) — mesmo padrão já usado por `navegacao=None` na mesma função, para não
  forçar todo teste existente de `pedido.processar`/`entender_pedido` a passar o bloco novo.
- **`queries/temas.py::listar_com_embedding` e `queries/perfil_tema.py` (`registrar_uso`,
  `contar_usos_desde`, `ultima_mencao`, `atualizar_peso_por_decaimento`, `remover_por_origem`)** — não
  estão nos Arquivos-alvo (só `perfil/inferencia.py` é citado como "novo"), mas a lógica de casar tema
  por embedding e de contar uso por janela de tempo precisa de consulta própria; ficaram nos módulos de
  consulta já existentes, mesmo padrão do brief 048 (`consulta_contato.moldes_por_contexto`).
- **`tests/test_cli_pedir_confirmacao.py`** — a fixture `_ambiente` monta um `SimpleNamespace` falso
  para `configuracao()`; precisou de `temas_usuario=TemasUsuarioLimiares()` para não quebrar com o
  `AttributeError` do item anterior.
- **`tests/test_migracao_comentarios.py` e `tests/test_migracao_genero.py`** — ajuste mecânico de
  versão (16→17), mesma classe de fix já feita nos briefs 048/061 a cada migração nova.

## RELATÓRIO FINAL
- Brief executado: 040 — perfil do usuário inferido, não cadastrado
- Arquivos criados: `agente_nw/perfil/inferencia.py`, `agente_nw/nucleo/prompts/descrever_tema.py`,
  `scripts/migracoes/017_preferencias_usuario_temas.sql`, `tests/test_inferencia_temas.py`,
  `tests/test_inferencia_declaracoes.py`, `tests/test_console_eu.py`, `tests/test_evitar_implicito.py`,
  `docs/docs/doc_040_perfil_do_usuario_inferido_2026-10-11.md`, `logs/commit_040.txt`, `logs/arquivos_040.txt`
- Arquivos alterados (resumo em uma linha cada):
  - `agente_nw/nucleo/modelos/pedido.py` — campo `sobre_o_usuario`
  - `agente_nw/nucleo/modelos/tema.py` — `RespostaDescreverTema`
  - `agente_nw/nucleo/modelos/perfil_tema.py` — campo `peso_decaido_em`
  - `agente_nw/nucleo/modelos/configuracao.py` — `TemasUsuarioLimiares`
  - `agente_nw/nucleo/prompts/extrair_pedido.py` — instrução e exemplo de `sobre_o_usuario`
  - `agente_nw/nucleo/database/queries/perfil_tema.py` — uso por janela, decaimento, remover por origem
  - `agente_nw/nucleo/database/queries/temas.py` — `listar_com_embedding`
  - `agente_nw/nucleo/database/queries/perfis.py` — `preferencias_json`/`nao_me_interessa`
  - `agente_nw/nucleo/pedido.py` — chama a inferência ao fim de `processar` (ver seção 2)
  - `agente_nw/nucleo/orquestracao.py` — `limiares_temas_usuario` passante
  - `agente_nw/nucleo/fluxo.py` — passa `deps.limiares.temas_usuario`
  - `agente_nw/nucleo/relevancia/cruzamento.py` — `nao_me_interessa` como evitar implícito
  - `agente_nw/cli.py` — `pedir_cmd` passa o limiar; `verificar_ambiente` trata temas.yaml como informativo
  - `agente_nw/console/app.py` — `/eu` reescrita, `/eu/contar`, `/eu/esquecer`
  - `agente_nw/console/templates/eu.html` — tela sem formulário de temas
  - `config/limiares.yaml`, `config/llm_routing.yaml` — bloco `temas_usuario`, tarefa `descrever_tema`
  - `tests/test_cli_pedir_confirmacao.py`, `tests/test_configuracao.py`,
    `tests/test_migracao_comentarios.py`, `tests/test_migracao_genero.py` — ver seção 2
- Arquivos preservados literalmente na área afetada: `agente_nw/perfil/configurador.py`,
  `agente_nw/perfil/extrator.py`, `/eu/configurar` e `/temas` (bastidores, brief não pede apagar),
  `relevancia/cruzamento.py::cruzar_contato` (sem consulta; sem `evitar` hoje, fora de escopo),
  `scripts/instalar_macos.sh`, `AGENTS.md` (já sem `importar-temas`/`temas.yaml`, ver seção 1)
- Script de verificação (o gate, rodado pelo `scripts/agente_entregar.sh`; saída colada):
  ```
  manifesto 040: 28 arquivo(s)
  ruff check: ok
  ruff format: ok
  mypy: ok
  pytest: ok (856 passed, 5 deselected in 19.89s)
  lacunas do 040: 0 no Backlog, 4 em Pendências, 1 em Dívidas, 0 em Decisões
  ✓ brief 040: commit ef532fc, enviado ao GitHub
  ```
- Comandos executados: `scripts/agente_entregar.sh 040`
- Manifesto do commit: `logs/arquivos_040.txt` e `logs/commit_040.txt` (conteúdo abaixo)
- Pendências e decisões que ficaram abertas: as quatro do próprio brief (seção 6/8), teste real no Pro,
  só Sidarta:
  1. Depois de dez pedidos reais, a tela Eu mostra temas coerentes, com níveis plausíveis, sem cadastro.
  2. "Conte algo sobre você: sou advogado tributarista e velejo" cria dois temas `declarada`; "não me
     interessa política partidária" passa a excluir esse assunto dos ganchos.
  3. "Não tenho mais interesse em X" remove X.
  4. Instalação do zero não menciona `importar-temas`; `verificar-ambiente` não avisa sobre `temas.yaml`.
  E uma dívida: decaimento perde no máximo 1 ponto por chamada, mesmo com muitos meses sem pedido (ver
  seção 1) — baixo impacto (peso 1–5), registrada para o caso de incomodar.
- Resumo, Doing, Backlog e Done do `docs/PLAN.md` atualizados: sim

## Lacunas

| # | Lacuna | Destino | Impacto |
|---|---|---|---|
| 1 | Teste real, no Pro: depois de dez pedidos reais, a tela Eu mostra temas coerentes, níveis plausíveis, sem cadastro | pendência | nice |
| 2 | Teste real: "sou advogado tributarista e velejo" cria dois temas `declarada`; "não me interessa política partidária" exclui o assunto dos ganchos | pendência | nice |
| 3 | Teste real: "não tenho mais interesse em X" remove X | pendência | nice |
| 4 | Teste real: instalação do zero não menciona `importar-temas`; `verificar-ambiente` não avisa sobre `temas.yaml` | pendência | nice |
| 5 | `decair()` perde no máximo 1 ponto por chamada mesmo com muitos meses sem pedido nenhum (sem agendamento, AGENTS §6); baixo impacto (peso entre 1 e 5) | dívida | nice |
