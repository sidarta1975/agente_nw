# Brief 040 — Perfil do usuário inferido, não cadastrado

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Conjunto:** nenhum (brief isolado, direto na `main`)
**Arquivos-alvo:** `scripts/migracoes/011_preferencias_usuario.sql` (nova), `agente_nw/perfil/inferencia.py` (novo), `agente_nw/nucleo/prompts/extrair_pedido.py`, `agente_nw/nucleo/modelos/pedido.py`, `agente_nw/nucleo/prompts/descrever_tema.py` (novo, só se necessário), `config/llm_routing.yaml`, `config/limiares.yaml`, `agente_nw/nucleo/fluxo.py`, `agente_nw/relevancia/cruzamento.py` (bloco `evitar`), `agente_nw/console/app.py`, `agente_nw/console/templates/eu.html`, `scripts/instalar_macos.sh`, `AGENTS.md` (seções 2, 3 e 7), `agente_nw/cli.py` (`verificar-ambiente`), `tests/test_inferencia_temas.py`, `tests/test_inferencia_declaracoes.py`, `tests/test_console_eu.py`, `tests/test_evitar_implicito.py`, `tests/test_migracao_011.py` (novos), `tests/test_configuracao.py` (ajuste), `docs/docs/doc_040_perfil_do_usuario_inferido_2026-10-11.md`, `logs/commit_040.txt`, `logs/arquivos_040.txt`
**Seções a ler:** `perfil/configurador.py` e `perfil/extrator.py` inteiros; `queries/pedidos.py` (036); a tela `eu.html` e a rota `/eu` atuais (brief 024); `relevancia/pontuacao.py` (034/035, como o enriquecimento por tema do usuário entra hoje)
**Modelo:** Opus: módulo novo de inferência com decaimento e três gatilhos diferentes (pedido, declaração, tempo); risco de regressão na tela Eu e no enriquecimento do motor
**Esforço:** alto
**Teste de aceite:** `tests/test_inferencia_temas.py`, `tests/test_inferencia_declaracoes.py`, `tests/test_console_eu.py`, `tests/test_evitar_implicito.py` e `tests/test_migracao_011.py`
**Depende de:** brief 036 (`322341c`) — usuário criado automaticamente, pedidos gravados. Independente do 039 (`e9564bd`, já concluído) — não precisa dele para rodar.
**Data:** 2026-10-11

---

## 1. Objetivo em uma frase

Os temas do usuário — o que ele domina, acompanha ou tem curiosidade — deixam de ser cadastrados num formulário ou num YAML e passam a ser acumulados pelo sistema a partir dos pedidos que ele faz; a tela "Eu" mostra o que foi inferido e aceita correção em texto; `importar-temas` sai da instalação.

---

## 2. O que já existe e é reaproveitado

- `perfil_tema` com `peso`, `origem IN ('declarada','sugerida','importada','captura','imagem','conversa')`, `confirmado`, `nivel`; `tema` com `nome`, `descricao`, `sinonimos`, embedding em `vetor_tema`.
- `perfil/configurador.py`: `salvar_perfil_usuario`, `adicionar_tema_do_usuario`, `remover_tema_do_usuario`.
- `perfil/extrator.py`: extração de temas de texto livre (fila de extração) — já produz `perfil_tema` com `origem='sugerida'`.
- `queries/pedidos.py` (036): todos os pedidos com `extraido_json`.
- Tela `eu.html` e rota `/eu` (brief 024).
- O motor (034/035) usa `listar_confirmados_com_embedding` do usuário como enriquecimento, nunca como bloqueio.

---

## 3. Decisões

**3.1. Fonte dos temas: os pedidos.** Após cada pedido concluído, `perfil/inferencia.py` lê `assunto_principal`, `interessa` e `termos_busca` do pedido e atualiza os temas do usuário:
- Termo que casa um tema existente (nome, sinônimo, ou cosseno do embedding ≥ `temas_usuario.similaridade_mesmo_tema` = 0,85) → `peso` sobe 1 (teto 5), `origem='conversa'`.
- Termo novo → tema criado com `descricao` gerada pela IA (tarefa já existente de rotulagem ou, se não houver uma adequada, `descrever_tema` — nova, `num_ctx: 2048`, saída `{descricao, sinonimos}`), `peso=1`, `origem='conversa'`, `confirmado=1`, `nivel='interesse'`.
- `nivel` evolui pela frequência: 1 uso → `curiosidade`; 3 usos em 30 dias → `interesse`; 6 em 90 dias ou qualquer pedido com `objetivo='apresentar'` citando o tema → `dominio`. Limiares em `limiares.yaml`, bloco `temas_usuario`.
- Decaimento: tema sem uso há 180 dias perde 1 de peso por mês até 1; nunca é apagado sozinho.

**3.2. O que o usuário disse sobre si vale mais.** Frases do tipo *"sou advogado tributarista"*, *"não entendo nada de futebol"*, *"gosto de vela"* na caixa de texto (ou na tela Eu, 3.4) são extraídas pela tarefa `extrair_pedido` (036) — campo novo `sobre_o_usuario: list[str]` no schema, normalmente vazio — e viram temas `origem='declarada'`, `nivel='dominio'` para afirmações positivas, ou entram numa lista `nao_me_interessa` do perfil (coluna nova `perfil.preferencias_json`) que o motor usa como `evitar` implícito em todos os pedidos.

**3.3. Nome do usuário.** Continua vindo do sistema (036). Se um pedido disser "me chamo X" ou "sou o X", a extração preenche `sobre_o_usuario` e `perfis.upsert_usuario` atualiza o nome.

**3.4. Tela Eu reescrita (`eu.html`).** Sem formulário de temas. Mostra: nome; os temas inferidos agrupados por nível, cada um com peso e última menção; a lista "não me interessa"; e uma única caixa de texto — "conte algo sobre você" — que passa pela extração (3.2). Para remover um tema, o usuário escreve "não tenho mais interesse em X"; a IA aplica (`remover_tema_do_usuario` ou mover para `nao_me_interessa`). Botão "esquecer tudo o que você inferiu sobre mim" com confirmação, que zera `perfil_tema` do usuário com `origem='conversa'` e mantém `declarada`.

**3.5. Instalação.** `importar-temas` deixa de ser passo do `instalar_macos.sh` e do `AGENTS.md`; continua existindo como comando de bastidor (importa `temas.yaml` se alguém quiser). `temas.yaml` e `temas.exemplo.yaml` permanecem no repositório, sem obrigação de existir: `verificar-ambiente` passa a tratar "temas.yaml existe" como informativo, não como aviso.

**3.6. Uso no motor.** Nada muda no 034/035: os temas do usuário já entram como enriquecimento com `peso_nivel`. O ganho é que agora existem sem cadastro.

---

## 4. Testes (escritos antes do código)

- `tests/test_inferencia_temas.py` (LLM simulado, embeddings controlados): termo novo cria tema `conversa`/`curiosidade`; terceiro uso em 30 dias → `interesse`; sexto em 90 → `dominio`; termo que casa sinônimo soma peso em vez de criar; decaimento após 180 dias; `declarada` nunca decai nem é apagada por "esquecer".
- `tests/test_inferencia_declaracoes.py`: "sou advogado tributarista" → tema `declarada`/`dominio`; "não me interessa futebol" → `preferencias_json.nao_me_interessa`; "me chamo Sidarta" → nome atualizado.
- `tests/test_console_eu.py`: tela mostra temas por nível; "contar" aplica; "esquecer" zera só `conversa`.
- `tests/test_evitar_implicito.py`: termo em `nao_me_interessa` descarta candidato como `evitar`.
- `tests/test_migracao_011.py`.
- Ajuste de `test_configuracao.py` para o bloco `temas_usuario`.

---

## 5. Fora de escopo

- Apagar `importar-temas`, `temas.yaml` ou a tela de temas antiga (viram bastidores).
- Inferir temas a partir do LinkedIn do próprio usuário (possível depois; aqui só pedidos e declarações).
- Qualquer tela além de Eu.

---

## 6. Passos e aceite

Executar com `/executar 040`. Aceite: testes da seção 4 verdes, gate verde, commit e push pelo executor.

Se nenhuma tarefa existente servir para `descrever_tema` (item 3.1), a criação da tarefa nova fica a critério do executor, com a justificativa no relatório.

Pendência para Sidarta na resposta final — teste real, no Pro:
1. Após dez pedidos reais, a tela Eu mostra temas coerentes com o que foi pedido, com níveis plausíveis, sem nenhum cadastro.
2. "Conte algo sobre você: sou advogado tributarista e velejo" cria dois temas `declarada`; "não me interessa política partidária" passa a excluir esse assunto dos ganchos.
3. "Não tenho mais interesse em X" remove X.
4. Instalação do zero (`instalar_macos.sh` lido, não necessariamente executado) não menciona `importar-temas`; `verificar-ambiente` não avisa sobre `temas.yaml`.
