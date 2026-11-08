# Brief 038 — Redação dos ganchos e das mensagens

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Depende de:** brief 036 (pedido extraído, contexto produzido pela IA). Funciona sem o 037 (sem perfil localizado, redige com o que houver).
**Plano:** v3.1, passo 5.
**Data:** 2026-10-11

---

## 1. Objetivo em uma frase

O que o sistema entrega deixa de ser um menu de assuntos e passa a ser conteúdo pronto: três ou quatro ganchos, cada um com a notícia em duas linhas, o motivo de servir para aquela pessoa e aquele objetivo, e a mensagem já redigida no registro da relação — ou, se o encontro é presencial, a forma de puxar o assunto.

---

## 2. O que já existe e é reaproveitado

- `consulta.preparar(...)`: coleta, extração, agrupamento, qualificação, leitura de rede social, cruzamento por consulta (034/035) e gravação em `consulta_contato`. Devolve `ResultadoConsulta` com `itens_menu` (título, `por_que`, tipo, score, `resumo_cartao`).
- `assuntos.obter_por_id` com `titulo_gerado`, `resumo_cartao`; os itens de notícia do assunto (`itens` com título, domínio, URL, teaser).
- `historico.historico_recente_para_prompt(...)` e `consulta_contato.listar_por_perfil`.
- `fatos.listar_recentes`; `perfil` (cargo, empresa, cidade, notas).
- `PedidoExtraido` (036): `objetivo`, `objetivo_texto`, `meio`, `registro`, `assunto_principal`, `interessa`, `evitar`, `continuacao`.

---

## 3. Decisões

**3.1. Tarefa nova `redigir_ganchos`.** Nos dois perfis: `air16` → `qwen3:4b`, `num_ctx: 8192`, `temperature: 0.5`; `pro48` → `qwen2.5:14b`, `num_ctx: 16384`, `temperature: 0.5`. `format: json`, `think: false`. Temperatura mais alta que as tarefas de julgamento, porque aqui a saída é texto para pessoas.

**3.2. Entrada do prompt (`nucleo/prompts/redigir_ganchos.py`).** Blocos, nesta ordem:
1. Quem escreve: nome do usuário e, se existirem (brief 040), seus temas com nível.
2. Para quem: nome, cargo/empresa/cidade, vínculo e tempo sem contato (das pistas e do perfil), até 10 fatos recentes, o cabeçalho da rede social se houver.
3. O pedido: objetivo, objetivo nas palavras do usuário, meio, registro, assunto principal, interessa, evitar, frase original.
4. Histórico: até 3 consultas anteriores resumidas (o que foi entregue e o que foi marcado como usado), para não repetir gancho já usado.
5. Os assuntos selecionados pelo motor (até `itens_no_menu`): para cada um, título gerado, `por_que` do cruzamento, resumo do cartão, até 3 manchetes com veículo e data, `ponto_de_apoio`.
6. Regras de redação (3.3).
7. Um exemplo resolvido com cenário distante de qualquer teste.

**3.3. Regras de redação, escritas no prompt e verificadas por validador.**
- Produzir entre 3 e 4 ganchos (2 se só houver 2 assuntos; 1 se só 1; nenhum assunto → saída com `ganchos: []` e `aviso` explicando — nunca inventar notícia).
- Cada gancho: `assunto_id`, `titulo` (até 12 palavras), `noticia` (duas frases, só com o que está nas manchetes/resumo — proibido inventar número, nome ou data), `por_que_para_esta_pessoa` (uma frase que cite o vínculo ou o objetivo), `mensagem` (texto pronto) e `abordagem_presencial` (uma ou duas frases de como puxar o assunto, só quando `meio = pessoalmente`).
- `mensagem` no registro: `proximo` → primeira pessoa, informal, sem saudação formal, até 60 palavras; `cordial` → cumprimento leve, até 80 palavras; `formal` → tratamento e fecho, até 110 palavras. Sempre em português do Brasil, sem emojis salvo registro `proximo`, nunca mais de um ponto de exclamação, nunca "espero que esta mensagem o encontre bem".
- Objetivo molda a mensagem: `retomar` → reconhece o tempo sem contato sem pedir desculpa; `agradecer` → o agradecimento vem antes do gancho; `pedir` → o pedido vem depois do gancho e é explícito; `responder` → continua o fio (brief 041 traz a última mensagem); `apresentar` → quem é o usuário em uma linha antes do gancho.
- Nada de `evitar` pode aparecer na mensagem (validador: correspondência sem acento/caixa; gancho que viola é descartado e o aviso registrado).
- Não repetir gancho marcado como usado no histórico (validador compara `assunto_id`).

**3.4. Saída (modelo `Redacao` em `nucleo/modelos/redacao.py`).** `ganchos: list[Gancho]`, `aviso: str | None`, `registro_usado`. Validadores: limites de palavras por registro; ausência de termos de `evitar`; `assunto_id` presente entre os selecionados; sem duplicata de `assunto_id`.

**3.5. Gravação.** `consulta_contato.assuntos_entregues_json` passa a conter também a redação (campo `redacao` ao lado do menu), preservando o formato atual para o histórico. Tabela nova `gancho_uso` (migração `009_gancho_uso.sql`): `consulta_id`, `assunto_id`, `status IN ('entregue','usado','nao_serve')`, `atualizado_em` — é o que "usei" (brief 039) altera e o que o histórico e o brief 042 leem.

**3.6. `agente_nw pedir` passa a entregar a redação por padrão.** Após extração (036) e localização (037, se houver), roda `preparar` e em seguida `redigir`. Impressão em texto corrido: cabeçalho com pessoa e objetivo; para cada gancho, título, notícia, por quê, mensagem entre aspas (e abordagem presencial quando houver); ao fim, `aviso` se existir. `--menu` imprime o menu antigo em vez da redação; `--json` imprime `Redacao`.

**3.7. Tempo.** A redação é uma chamada única ao modelo com todos os assuntos; no Pro, com 16k de contexto, a expectativa é de 20 a 40 segundos. No Air, com 8k, o prompt corta o histórico para 1 consulta e os fatos para 5 quando o texto montado exceder 6.000 tokens estimados (contagem aproximada por palavras × 1,4).

---

## 4. Escopo (arquivos)

1. `config/llm_routing.yaml`: `redigir_ganchos` nos dois perfis.
2. `nucleo/modelos/redacao.py`: `Gancho`, `Redacao`, validadores.
3. `nucleo/prompts/redigir_ganchos.py`: `construir_prompt(...)`, `ESQUEMA`, exemplo resolvido; função de corte por tamanho (3.7).
4. `nucleo/redacao.py`: `redigir(cliente_llm, conexao, pedido, resultado_consulta, perfil, usuario, agora) -> Redacao`; `registrar(conexao, consulta_id, redacao)`.
5. `scripts/migracoes/009_gancho_uso.sql` + `queries/gancho_uso.py` (`inserir_entregues`, `marcar`, `listar_por_consulta`, `assuntos_usados_do_perfil`).
6. `nucleo/historico.py`: `_formatar_assuntos` passa a mostrar a redação quando existir e o status de uso.
7. `cli.py`: `pedir` entrega redação; `--menu`, `--json`.
8. `AGENTS.md`, seção 3: tarefa `redigir_ganchos`; seção 7 já reescrita no 036.

---

## 5. Testes

- `tests/test_redacao_modelo.py`: limites por registro; termo de `evitar` na mensagem → gancho rejeitado e aviso; `assunto_id` desconhecido rejeitado; duplicata rejeitada; lista vazia aceita com aviso.
- `tests/test_redacao_prompt.py`: prompt contém os blocos na ordem; corte por tamanho ativa no `air16`; exemplo não contém nomes dos testes.
- `tests/test_redacao_redigir.py` (LLM falso): com 3 assuntos → 3 ganchos; com gancho já usado no histórico → não entregue; `meio = pessoalmente` → `abordagem_presencial` presente; `meio = whatsapp` → ausente.
- `tests/test_gancho_uso.py`: inserção na entrega, `marcar` muda status, `assuntos_usados_do_perfil` lista só `usado`.
- `tests/test_cli_pedir_redacao.py`: saída contém "Mensagem:" por gancho; `--menu` mantém o formato anterior.
- `tests/test_migracao_009.py`.

---

## 6. Fora de escopo

- Tela (brief 039). Correção em texto ("mais informal") é do 039 e reaproveita `redigir` com o pedido alterado.
- Continuação de conversa com a última mensagem do contato (brief 041).
- Envio de mensagem por qualquer canal — nunca.
- Ajuste fino de tom por pessoa ao longo do tempo (fica para depois da medição, brief 042).

---

## 7. Passos de execução

1. Migração 009 e `queries/gancho_uso.py`.
2. `llm_routing.yaml`, `AGENTS.md`.
3. `modelos/redacao.py`.
4. `prompts/redigir_ganchos.py`.
5. `nucleo/redacao.py`.
6. `historico.py`.
7. `cli.py`.
8. Testes da seção 5.
9. Lista para `git add` e mensagem: `feat(redacao): ganchos e mensagens prontas no registro da relação, a partir do pedido e dos assuntos selecionados (brief 038)`.

`scripts/verificar.sh`, o teste real e o commit são passos de Sidarta.

---

## 8. Critérios de aceite (Sidarta, no Pro)

1. Cinco pedidos reais, pessoas diferentes, objetivos diferentes (retomar, agradecer, pedir, manter, apresentar), meios diferentes. Em cada um, pelo menos um gancho é bom o bastante para ser usado como está ou com ajuste mínimo — e o usuário usa pelo menos um numa conversa real durante a semana.
2. Nenhuma mensagem contém termo de `evitar`; nenhuma inventa fato que não esteja nas manchetes.
3. Registro `proximo` sai informal e curto; `formal` sai com tratamento e fecho.
4. Pedido presencial traz a abordagem; pedido de WhatsApp traz só a mensagem.
5. Repetir o pedido para a mesma pessoa depois de marcar um gancho como usado não entrega o mesmo gancho.
