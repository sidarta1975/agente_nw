# Brief E1-009 — Regra do conector e menu por contato

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Depende de:** brief 008 (qualificação), certificado, e brief 005 (contatos ativos) — precisa de pelo menos um contato ativo com tema confirmado para a execução real.

---

## 1. Objetivo em uma frase

Para cada contato ativo, escolher os até cinco assuntos que valem a pena puxar, separados em conector e viável com esforço, com pontuação e classificação 100% determinísticas — o modelo só escreve a frase do "por quê".

---

## 2. Contexto e o que já existe

`assunto_contato` já existe no esquema exatamente como precisamos (`tipo`, `aderencia_contato`, `aderencia_usuario`, `conversavel`, `score`, `por_que`, `status`, `motivo`), e `agente_nw/nucleo/modelos/assunto_contato.py` já tem o contrato Pydantic. `config/limiares.yaml` já tem `conector.adjacencia_minima: 0.55`, `conector.conversavel_viavel: 0.8`, os três pesos de nível, os três pesos da fórmula (50/30/20) e `candidatos_por_contato: 10`/`itens_no_menu: 5`. `config/llm_routing.yaml` já roteia `cruzar_por_que` para `qwen3:4b`.

O brief 008 já deixou qualificados (com `substancial`/`conversavel`) uma parte real dos 283 assuntos do brief 007. Este brief consome esse resultado — não requalifica nada.

**Mudança em relação ao plano original, decidida agora, mesmo princípio já aplicado no brief 007:** o plano original pedia uma segunda calibração aqui — 30 linhas reais de `assunto_contato`, IA pré-classifica, você só corrige as discordâncias. Não vou fazer você repetir esse exercício. Ver seção 5.

---

## 3. Escopo

1. **`agente_nw/nucleo/database/queries/perfis.py`** (aditivo — nenhuma função existente tocada): `calcular_centroide(conexao, perfil_id) -> list[float] | None` (média ponderada dos embeddings dos temas **confirmados** desse perfil — peso efetivo = `peso` do vínculo (1–5) × peso do nível se houver nível, × 1,0 se não houver; devolve `None` se não houver nenhum tema confirmado com embedding), `gravar_centroide(conexao, perfil_id, centroide)` e `obter_centroide(conexao, perfil_id) -> list[float] | None` (mesmo padrão de `temas.gravar_embedding`, gravando em `vetor_perfil`).
2. **`agente_nw/nucleo/database/queries/assunto_contato.py`** (novo): `inserir` (idempotente — `INSERT ... ON CONFLICT (assunto_id, perfil_id, gerado_em) DO NOTHING`, a `UNIQUE` já existe no esquema), `listar_do_dia(conexao, perfil_id, data)`, `listar_assunto_ids_ja_vistos(conexao, perfil_id) -> set[int]` (qualquer dia, qualquer status — um assunto já mostrado a esse contato uma vez não volta a ser candidato).
3. **`agente_nw/nucleo/modelos/cruzamento.py`**: `RespostaCruzarPorQue` — `{"por_que": list[str]}`, `frozen=True`. Só isso — `sem_assunto`/`motivo` nunca vêm do modelo, são decisão 100% de Python antes de cogitar chamá-lo (seção 4).
4. **`agente_nw/nucleo/prompts/cruzar_por_que.py`**: `construir_prompt(apelido_ou_nome, temas_contato, temas_usuario_com_nivel, assuntos: list[tuple[titulo, tipo, ponto_de_apoio]]) -> str`. O modelo recebe os assuntos **numerados na ordem em que devem ser respondidos** (não por `assunto_id`) e devolve `por_que` como lista na mesma ordem — o vínculo com o `assunto_id` de cada posição é feito pelo Python que chamou, nunca pelo texto do modelo. Isso existe para que seja estruturalmente impossível o modelo inventar ou trocar um `assunto_id` (é um dos critérios do brief 013 de certificação: zero invenção de `assunto_id`).
5. **`agente_nw/nucleo/relevancia/pontuacao.py`**: `avaliar(centroide_assunto, centroide_contato, temas_usuario, conversavel, limiares) -> Avaliacao` (`aderencia_contato`, `aderencia_usuario`, `conversavel`, `score`, `tipo`). Pura, sem banco — ver seção 4.
6. **`agente_nw/nucleo/relevancia/candidatos.py`**: `selecionar(conexao, perfil_id, limite) -> list[Assunto]` — ver seção 4.
7. **`agente_nw/nucleo/relevancia/cruzamento.py`**: `cruzar_contato(cliente_llm, conexao, perfil_id, agora) -> ResumoContato` — orquestra tudo, um contato por vez.
8. **`agente_nw/cli.py`**: comando `cruzar` (novo — roda `cruzar_contato` para todo perfil `tipo='contato'` e `ativo=1`) e `menu <telefone>` (novo — prévia manual: imprime os `assunto_contato` de hoje daquele contato, título, tipo, score, `por_que`).

---

## 4. A regra, exatamente

**Centróide do contato**: recalculado do zero a cada execução de `cruzar_contato` (não fica em cache esperando alguém lembrar de atualizar — é a mesma lição do bug do embedding de tema que corrigimos no brief 008: o dado derivado se recalcula no ponto de uso, nunca depende de um segundo comando que dá pra esquecer). Se o contato não tem nenhum tema confirmado com embedding, `centroide` é `None` — vai direto para `sem_assunto`, `motivo="contato sem tema confirmado"`, sem chamar nada mais.

**Seleção de candidatos** (`candidatos.selecionar`): assuntos com `substancial >= qualificacao.substancial_minimo` e `conversavel >= qualificacao.conversavel_minimo` (o corte de qualificação do brief 008), que **nunca apareceram antes** para esse `perfil_id` (`listar_assunto_ids_ja_vistos`), ordenados por cosseno do centróide do assunto contra o centróide do contato, os `conector.candidatos_por_contato` (10) primeiros.

**Avaliação de cada candidato** (`pontuacao.avaliar`), para os até 10 candidatos:
- `aderencia_contato` = cosseno(centróide do assunto, centróide do contato). Negativo vira 0 (cosseno nunca é usado negativo nesta fórmula).
- Para cada tema **confirmado do usuário** com embedding: `cos_bruto` = cosseno(centróide do assunto, embedding do tema); `cos_ponderado` = `max(cos_bruto, 0) × peso_nivel[nivel]`.
- `aderencia_usuario` (a que entra na pontuação) = o maior `cos_ponderado` entre todos os temas do usuário.
- `melhor_dominio_ou_interesse` = o maior `cos_bruto` só entre os temas de nível `dominio`/`interesse` (ou `None`, se não houver nenhum).
- `melhor_qualquer` = o maior `cos_bruto` entre todos os temas do usuário, qualquer nível (ou `None`).
- `conversavel` = o valor já gravado no assunto pelo brief 008 (não recalcula, não chama modelo de novo).
- `score` = `50 × aderencia_contato + 30 × aderencia_usuario + 20 × conversavel` (0–100, já que as três parcelas são 0–1 e os pesos somam 100).
- `tipo`:
  - **`conector`** se `melhor_dominio_ou_interesse is not None` e `melhor_dominio_ou_interesse >= adjacencia_minima` (0,55).
  - **`viavel_com_esforco`** se não for conector, e (`melhor_qualquer is not None` e `melhor_qualquer >= adjacencia_minima`) **ou** `conversavel >= conversavel_viavel` (0,8). Repare: um tema de curiosidade com cosseno alto entra aqui, nunca em conector, mesmo que o número seja maior que 0,55 — é a correção explícita do plano ("curiosidade rende no máximo viável com esforço").
  - **`fora_do_dominio`** no resto.

**Depois da avaliação dos até 10**: os `fora_do_dominio` são gravados direto como `assunto_contato.status="descartado"`, `motivo="fora do domínio"` — nunca vão para o menu, nunca passam pelo modelo. Os demais são ordenados por tipo (conector antes de viável com esforço) e, dentro do tipo, por `score` decrescente; os `itens_no_menu` (5) primeiros seguem para o `cruzar_por_que`.

**`cruzar_por_que`**: só é chamado se sobrar pelo menos 1 assunto depois do corte acima. Prompt numera os assuntos selecionados na ordem final (1 a até 5); resposta `por_que` é lista na mesma ordem — o Python casa posição a posição com o `assunto_id` correto, o modelo nunca vê nem escreve um `assunto_id`. Se a lista devolvida tiver tamanho diferente do enviado, é `FalhaJsonInvalido` (mesmo tratamento de sempre — tenta de novo, depois `fila_revisao`; se falhar de vez, os `assunto_contato` são gravados com `por_que=None` em vez de travar o contato inteiro).

**`sem_assunto`**, sempre determinístico, nunca perguntado ao modelo: contato sem tema confirmado (`motivo="contato sem tema confirmado"`); zero candidatos depois da seleção (`motivo="nenhum assunto qualificado disponível"`); todos os até 10 candidatos deram `fora_do_dominio` (`motivo="nenhum candidato passou do piso"`).

---

## 5. Sobre a calibração que este brief não vai fazer

O plano original pedia uma segunda rodada de calibração aqui, no mesmo formato do brief 007 (amostra real, IA pré-classifica, você corrige as discordâncias). Não vou repetir esse pedido — você já deixou claro que esse tipo de exercício sintético não vale seu tempo, e aqui o argumento é ainda mais forte: julgar se um assunto é ou não um "bom conector" para você é uma opinião sua sobre sua própria vida, não um fato do mundo que um segundo modelo possa arbitrar como fez o `qwen3:8b` com "essas duas notícias são o mesmo fato".

**Decisão**: `adjacencia_minima` (0,55) e `conversavel_viavel` (0,8) ficam com o valor inicial da proposta, documentados como **não calibrados com dado real de uso**. A calibração de verdade vem de você aceitando ou recusando sugestões de verdade — o campo `assunto_contato.status` (`usado`/`nao_serve`) já existe exatamente para isso, e passa a ser preenchido a partir do brief 011 (leitura de marcação no Markdown). Quando houver histórico real suficiente (usado/não serve de dias reais, não uma amostra fabricada), reaproveito o mesmo mecanismo de varredura de limiar que já construí no brief 007 (`agrupamento/calibracao.py`) para recalibrar estes dois valores a partir desse dado real — provavelmente no brief 013 ou logo depois, nunca antes de existir uso real para medir.

Os "12 casos" que o plano pede como portão de aceite **não são um exercício de rotulagem** — `tipo` e `score` são aritmética pura, sem modelo envolvido; então em vez de pedir pra você julgar 12 casos, eu já escrevi os 12 na seção 6 com o resultado que a aritmética tem que dar. É teste automatizado, 12 de 12 esperado (não "10 de 12" — não tem por que errar conta).

---

## 6. Os 12 casos (teste automatizado, sem julgamento seu)

Vetores fabricados em baixa dimensão (não precisa de embedding real de verdade — a fórmula não liga pra quantas dimensões o vetor tem). Para atingir um cosseno-alvo `c` entre dois vetores, uso `u = (1, 0)` como referência e `v = (c, sqrt(1 - c²))` — cosseno entre os dois dá exatamente `c` por construção. `centroide_assunto` é sempre `u = (1, 0)`.

| # | aderência ao contato | temas do usuário (nível: cosseno bruto) | conversável | tipo esperado | por quê |
|---|---|---|---|---|---|
| 1 | 0,70 | domínio: 0,60 | 0,50 | `conector` | domínio ≥0,55 |
| 2 | 0,40 | interesse: 0,90 | 0,20 | `conector` | interesse ≥0,55, mesmo com aderência ao contato baixa |
| 3 | 0,55 | domínio: 0,55 | 0,60 | `conector` | exatamente no limiar (`>=`, não `>`) |
| 4 | 0,80 | domínio: 0,70; curiosidade: 0,95 | 0,40 | `conector` | domínio sozinho já garante, a curiosidade mais alta não muda nada |
| 5 | 0,50 | curiosidade: 0,60 | 0,30 | `viavel_com_esforco` | **único apoio é curiosidade** — nunca vira conector mesmo ≥0,55; conversável baixo prova que é a adjacência de curiosidade que sustenta, não a conversabilidade |
| 6 | 0,30 | domínio: 0,40 | 0,85 | `viavel_com_esforco` | domínio abaixo de 0,55, mas conversável ≥0,8 sustenta |
| 7 | 0,20 | nenhum tema do usuário | 0,90 | `viavel_com_esforco` | sem nenhum apoio de tema, só conversabilidade alta |
| 8 | 0,60 | interesse: 0,54 | 0,79 | `fora_do_dominio` | interesse abaixo do limiar por pouco (0,54 < 0,55) e conversável abaixo por pouco (0,79 < 0,8) — cada condição é checada isolada; dois "quase" não se somam, então nem o piso de viável passa |
| 9 | 0,10 | domínio: 0,20 | 0,10 | `fora_do_dominio` | nada bate piso nenhum |
| 10 | 0,50 | curiosidade: 0,45 | 0,50 | `fora_do_dominio` | curiosidade abaixo de 0,55 e conversável abaixo de 0,8 — nem o piso mínimo passa |
| 11 | 0,90 | nenhum tema do usuário | 0,30 | `fora_do_dominio` | aderência ao contato altíssima não importa nada sem apoio nenhum do usuário — é a regra do conector, não uma lista de temas globais |
| 12 | 0,0 | domínio: 0,0 | 0,0 | `fora_do_dominio` | caso degenerado, tudo zero |

O caso 8 é o mais importante de acertar: dois valores individualmente abaixo do limiar não se somam — cada regra é checada isolada (`>=`), nunca uma combinação ponderada dos dois "quase".

---

## 7. Fora de escopo, com justificativa

- **Calibração de `adjacencia_minima`/`conversavel_viavel` com dado real.** Seção 5 — depende de uso real que ainda não existe.
- **`assunto_contato.status` mudar de `novo` para `usado`/`nao_serve`.** É o brief 011 (leitura de marcação no Markdown) que escreve isso; aqui todo `assunto_contato` novo nasce com `status="novo"` (exceto os `descartado`, que nascem já fechados).
- **Requalificar um assunto que muda depois de já ter entrado num menu.** Mesmo raciocínio do brief 008: o valor de `substancial`/`conversavel` usado é o que já está gravado, não recalcula.

---

## 8. Passos de execução

1. `queries/perfis.py`: `calcular_centroide`, `gravar_centroide`, `obter_centroide`.
2. `tests/test_perfis_centroide.py`: contato com 2 temas confirmados (pesos e embeddings fabricados) dá o centróide esperado (conferir a conta à mão); contato sem tema confirmado devolve `None`; tema não confirmado não entra na conta.
3. `queries/assunto_contato.py`: as três funções da seção 3, item 2.
4. `tests/test_assunto_contato.py`: `inserir` duas vezes com a mesma tripla `(assunto_id, perfil_id, gerado_em)` não duplica; `listar_assunto_ids_ja_vistos` pega qualquer status.
5. `modelos/cruzamento.py` e `prompts/cruzar_por_que.py`.
6. `nucleo/relevancia/pontuacao.py`: `avaliar`, conforme seção 4.
7. `tests/test_pontuacao.py`: os 12 casos da seção 6, exatos — 12 de 12.
8. `nucleo/relevancia/candidatos.py`: `selecionar`, conforme seção 4.
9. `tests/test_candidatos.py`: assunto já visto antes (qualquer status) não volta a ser candidato; corte de qualificação (substancial/conversável) é respeitado; ordenação por aderência ao contato.
10. `nucleo/relevancia/cruzamento.py`: `cruzar_contato`, conforme seção 4.
11. `tests/test_cruzamento.py` (com `ClienteOllama` fake): contato sem tema confirmado dá `sem_assunto` sem chamar o modelo nenhuma vez; todos os candidatos fora do domínio dá `sem_assunto` sem chamar o modelo; resposta do modelo com lista de `por_que` de tamanho errado é tratada como falha (retry, depois grava sem `por_que`, não trava); `assunto_contato` gravado com o `assunto_id` certo em cada posição, nunca o que viria de um campo do modelo (o contrato nem tem esse campo — o teste conirma que não dá nem para o fake devolver um id errado, estruturalmente).
12. `cli.py`: comandos `cruzar` e `menu <telefone>`.
13. `tests/test_cli_cruzamento.py`: `menu` de um telefone sem `assunto_contato` hoje avisa claro, não trava; `cruzar` sem nenhum contato ativo não erra.
14. Rodar de verdade: `agente_nw cruzar` contra os contatos ativos reais (pelo menos um precisa ter tema confirmado — se nenhum tiver, ativar/confirmar um agora com os comandos do brief 005 antes de seguir); `agente_nw menu <telefone>` para conferir o resultado; confirmar manualmente que nenhum `fora_do_dominio` aparece na lista do `menu`, que os descartes têm motivo gravado, e que o `por_que` de um `viavel_com_esforco` cita de fato o ponto de apoio do usuário (ex.: cita o tema de curiosidade, não inventa outro).
15. Atualizar `docs/PLAN.md`: brief 009 concluído; registrar que os dois limiares do conector seguem não calibrados com dado real, e que a calibração virá do `status` real de `assunto_contato` depois do brief 011.

---

## 9. Critérios de aceite

1. Os 12 casos da seção 6 batem 12 de 12.
2. Rodando contra contato ativo real: nenhum `fora_do_dominio` aparece em `agente_nw menu`; todo descarte tem `motivo` gravado; o `por_que` de pelo menos um `viavel_com_esforco` real cita o ponto de apoio certo.
3. Contato ativo sem tema confirmado recebe `sem_assunto` com motivo, sem travar o comando `cruzar` para os demais contatos.
4. Nenhum `assunto_id` gravado em `assunto_contato` pode ter vindo de um campo escrito pelo modelo — estruturalmente garantido pelo contrato de `cruzar_por_que` não ter esse campo (critério verificado por teste, não por inspeção manual, é o precursor do "zero invenção de assunto_id" do brief 013).
5. `scripts/verificar.sh` verde nos testes automatizados.

---

## 10. Riscos e como reverter

| Risco | Controle |
|---|---|
| Modelo devolver `por_que` em quantidade diferente da enviada | tratado como falha de validação — retry, depois `fila_revisao`, `assunto_contato` grava sem `por_que` em vez de travar o contato |
| Nenhum contato ativo tem tema confirmado ainda (dado real insuficiente) | critério de aceite 2 fica bloqueado até isso existir — documentar em `docs/PLAN.md`, não fabricar dado sintético para fechar o número |
| Limiares não calibrados renderem poucos conectores reais no início | esperado e aceitável — é dado real de uso que vai decidir a recalibração, não uma suposição feita agora |
| Reverter | Todos os arquivos deste brief são novos, exceto as três funções aditivas em `queries/perfis.py` (nenhuma existente tocada) e os dois comandos novos em `cli.py` |

---

## 11. Relatório final obrigatório

Preencher o bloco da seção 8 de `AGENTS.md`, com o caminho do script de verificação para colar no terminal. Sem esse bloco preenchido, o brief não está concluído.
