# Brief 087 — Destino da fila de revisão: ver, reenviar e descartar o que o modelo não conseguiu

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Conjunto:** correção do texto por inteiro (086 a 095)
**Arquivos-alvo:** `agente_nw/nucleo/database/queries/fila_revisao.py`, uma migração nova em `agente_nw/nucleo/database/` (seguir a convenção das migrações do projeto), `agente_nw/cli.py` (comandos novos), `agente_nw/console/app.py` e seu template (uma tela, se o padrão do console permitir), `tests/test_fila_revisao_destino.py` (novo), mais o relatório, o manifesto e o PLAN
**Seções a ler:** relatório 079 e a seção 5.1 do relatório do agente_nw em `referencias/relatorios_projetos`; `nucleo/llm.py` (`FalhaJsonInvalido`, `_ir_para_fila_revisao`); os quatro pontos que inserem na fila (`relevancia/cartoes.py`, `relevancia/cruzamento.py`, `agrupamento/agrupador.py`, `nucleo/llm.py`); `docs/ARQUITETURA_agente_nw.md` (console e CLI); PLAN: armadilhas sobre o console e sobre migrações
**Modelo:** Sonnet
**Esforço:** médio
**Teste de aceite:** `tests/test_fila_revisao_destino.py`
**Depende de:** brief 079 executado
**Ordem em série:** livre; antes de 082
**Data:** 2026-11-08

---

## 1. Objetivo em uma frase

Todo item que o modelo não conseguiu processar e foi para `fila_revisao` passa a poder ser visto, reenviado ou descartado por Sidarta, em vez de ficar parado sem ninguém que o leia.

## 2. Achados no código e no banco (conferidos em 2026-11-08)

- Quatro pontos do código **inserem** na fila e nenhum a lê ou resolve; a coluna `resolvido` existe e nada a muda.
- Na cópia do banco de 2026-10-25 há 232 itens sem resolução: 229 da tarefa `extrair_de_texto`, 2 de `redigir_ganchos` e 1 de `extrair_pedido`. Quase todos são erro de validação do JSON (`RespostaExtracaoTexto`), não de janela. A causa **não foi investigada**.
- A coluna `entrada` guarda o prompt inteiro (até 12.687 caracteres na cópia), ou seja, texto de terceiros.
- O brief 082 vai mandar para essa fila os itens cujo prompt não cabe na janela; sem este brief, eles somem.

## 3. Decisões (de Sidarta)

**3.1.** Três comandos novos na CLI: `revisao ver` (lista por tarefa, tipo de erro e idade, **sem** mostrar o texto da entrada por padrão; `--inteiro <id>` mostra), `revisao descartar <id> --motivo "..."` e `revisao reenviar <id>`. O console ganha uma tela com a mesma lista se o padrão do console permitir; se não permitir, o executor diz isso no relatório e a tela vira lacuna.

**3.2.** `reenviar` só existe para a tarefa que tem caminho de repetição no código (o executor descobre qual: `extrair_de_texto` pelo fluxo de `fila_extracao`, `extrair_pedido` pelo pedido de origem, `redigir_ganchos` pela consulta). Para a tarefa sem caminho, o comando diz isso e não faz nada. Reenviar marca o item como resolvido apenas depois de o reprocessamento gravar resultado válido.

**3.3.** Uma migração acrescenta `resolvido_em` e `resolucao` (`descartado`, `reenviado_ok`, `reenviado_falhou`) e o motivo. Itens antigos ficam com esses campos vazios.

**3.4.** Diagnóstico dos 229 erros de `extrair_de_texto`: o executor trabalha **só numa cópia** (`agente_nw copiar-banco`; nunca o banco real) e no relatório informa **contagens e classes de erro**, sem copiar texto de terceiros. Se a causa for um defeito pequeno no esquema ou no prompt da tarefa, o executor **não corrige aqui**: registra em Lacunas com destino "decisão", porque mexer no prompt muda a versão e o comportamento.

**3.5.** A privacidade do prompt guardado em `entrada` não muda neste brief; o executor só registra, se achar, que a coluna guarda texto de terceiros.

## 4. Escopo (arquivos)

| Arquivo | O que muda |
|---|---|
| `queries/fila_revisao.py` | `listar`, `obter`, `marcar_resolvido` e contagens por tarefa/erro. |
| migração nova | Colunas de 3.3. |
| `cli.py` | Comando `revisao` com os três subcomandos. |
| `console/app.py` e template | Tela de lista, descarte e reenvio (se couber). |
| `tests/test_fila_revisao_destino.py` | Seção 5. |

## 5. Testes (banco isolado em `tmp_path`, cliente de LLM falso)

1. `listar` agrupa por tarefa e erro, ordena por idade e não devolve a entrada por padrão. 2. `descartar` marca `resolvido`, `resolvido_em` e o motivo; descartar duas vezes é recusado. 3. `reenviar` de `extrair_de_texto` com resultado válido marca `reenviado_ok`; com novo erro, o item continua na fila como `reenviado_falhou` e uma nova linha não duplica a entrada. 4. Tarefa sem caminho de repetição: mensagem clara, nada muda. 5. A migração aplica em banco com itens antigos sem perder linha. 6. O comando não abre o banco real (usa o caminho de `config`; teste com `tmp_path`).

## 6. Fora de escopo

Corrigir a causa dos erros de validação (decisão); apagar fisicamente linhas da fila; qualquer mudança em `num_ctx`.

## 7. Passos de execução e critérios de aceite

Passos: conferir "Depende de"; testes; implementar; diagnóstico da seção 3.4; relatório `doc_087_...` com a tabela `Tarefa | itens | classe de erro | tem caminho de repetição`, e a resposta a "algum texto é analisado só em parte?" (não: este brief não monta prompt nem corta texto); manifesto; PLAN; `scripts/agente_entregar.sh 087`. Aceite, com saída colada: (1) `pytest tests/test_fila_revisao_destino.py -q` verde; (2) `agente_nw revisao ver --help` mostra os três subcomandos; (3) o diagnóstico traz contagens por classe de erro e nenhum texto de terceiros; (4) gate verde. Última linha: "Para você: rodar `agente_nw revisao ver` na cópia do banco e decidir o destino dos itens antigos".
