# Brief 046 — Quem decide o tema é o usuário; o motor não inventa nem foge do objetivo

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Depende de:** caminho da consulta (briefs 034/035), redação (038), tela (039) — tudo já em uso. Não depende de rede; complementa o brief 045 (coleta), não precisa dele para rodar.
**Plano:** v3.1 — confiança no conteúdo entregue.
**Data:** 2026-10-14

---

## 1. Objetivo em uma frase

O programa para de julgar por você quais temas são aceitáveis (política, saúde, religião…) e passa a confiar no seu juízo sobre o que cabe na mensagem; em troca, fica proibido de **afirmar sobre a pessoa o que ela não disse** e de **entregar assunto que não tem relação com o objetivo do pedido** — os dois defeitos que o teste com o Luiz escancarou.

---

## 2. Diagnóstico (o teste com o Luiz David, pedido #26)

O pedido era: pedir, por telefone, o apoio do Luiz para a chapa da OAB-SP 2027. Saíram cinco sugestões de notícia nacional solta (ato do Lula, debate da Band, manifestação, um projeto de câncer em Itaperuna) e um gancho afirmando "Ele apoia Lula" — enquanto o menu afirmava "ele apoia Flávio Bolsonaro". Três causas, no código:

- **Censura de tema.** Há sete "categorias perigosas" em `config/termos_sensiveis.yaml` (`saude, religiao, politica, sindicato, vida_sexual, origem_racial, menores`) e `nucleo/sensivel.verificar` corta o que bate nelas em sete pontos — inclusive ao ler os posts do Luiz. Para um advogado eleitoralista cujo pedido É político, isso joga fora o material do caso.
- **Afirmação inventada.** O "por quê" do menu nasce em `prompts/cruzar_por_que.py`, que recebe só o título do assunto, o tema que casou e o objetivo — **nunca os fatos da pessoa**. Sem fato, o modelo narra uma adesão ("apoia Flávio Bolsonaro") que nada sustenta. O "apoia Lula" do gancho veio de um "#BoraLula13" de quatro anos e de uma imagem "LAVA JATO VIVE".
- **Piso frouxo ao objetivo.** Em `relevancia/pontuacao.py` (`avaliar_por_consulta`), um assunto vira "conector" se **qualquer** sinal passa do limiar — inclusive só `aderencia_contato >= adjacencia_minima` (semelhança com os posts do contato), com `aderencia_consulta` (aderência ao objetivo) perto de zero. "Lula em Copacabana" casa com os posts de manifestação do Luiz, então entrou — sem relação com a eleição da OAB. As notas 45–49 raspam o piso de 0,45.

---

## 3. O que já existe e é reaproveitado

- `nucleo/sensivel.py` + `config/termos_sensiveis.yaml`; a query `queries/descarte_sensivel.py` e o modelo `modelos/descarte.py`.
- `prompts/redigir_ganchos.py` já tem a regra "afirme só o que está nos fatos" (acrescentada na sessão de 14/10) e recebe os fatos no formato `AAAA-MM-DD (tipo): conteúdo` — ou seja, já há data e tipo por fato.
- `relevancia/cruzamento.py` (`cruzar_contato_por_consulta`) já descarta tudo que não é "conector" e já tem o caminho de aviso (`sem_assunto`, motivo "nenhum candidato passou do piso").
- `relevancia/pontuacao.py` já calcula `aderencia_consulta` por assunto.
- `config/limiares.yaml`, bloco `conector.consulta` (`minima: 0.45`, pesos) e `ColetaLimiares`/`ConectorLimiares` em `modelos/configuracao.py`.

---

## 4. Decisões

### 4.1. Tirar a censura de tema — os sete pontos (movimento 1)

Remover a verificação de categoria sensível em:

1. `coleta/capturas/leitor.py` (descarte do bloco de rede).
2. `coleta/capturas/imagens.py` (descarte da descrição de imagem).
3. `perfil/extrator.py` — as três chamadas (texto, tag/trecho, fato).
4. `nucleo/termos_contato.py` (descarte do termo de busca).
5. `nucleo/modelos/redacao.py` → `validar_ganchos` (descarte do gancho; o item 4 da validação).

Em cada ponto, tirar **só** a parte do filtro de categoria; manter o resto da condição (em imagens, segue valendo `resposta.descartar or not descricao`; em `termos_contato`, segue a deduplicação). O programa passa a ler, guardar e usar o que está no post público — política, saúde, família —, porque quem julga o que cabe na mensagem é o usuário.

Limpeza (o executor resolve e registra no relatório): `nucleo/sensivel.py`, `config/termos_sensiveis.yaml`, `queries/descarte_sensivel.py`, `modelos/descarte.py` e os contadores de "descartado sensível" ficam sem uso → remover. A tabela `descarte_sensivel` pode ficar vazia; **sem migração destrutiva no banco real**.

### 4.2. Afiar a regra de verdade — e nos dois lugares (movimento 2)

A verdade sobre a pessoa não é tema; é qualidade. Mandar pro Luiz uma mensagem dizendo que ele apoia Lula, se ele não disse isso, é defeito — igual a um número errado numa petição.

- **`prompts/cruzar_por_que.py` (o "por quê" do menu).** Regra nova e explícita: *nunca atribuir ao contato opinião, posição, adesão, crença ou característica* ("ele apoia X", "ele é contra Y", "ele é de tal grupo"). O "por quê" liga o assunto ao **objetivo do pedido** e, quando cita o contato, cita só um dos temas da lista recebida (que vêm dos posts dele) — nunca uma posição inferida do título ou da foto. Ajustar o exemplo embutido para reforçar o padrão.
- **`nucleo/redacao.py` + `prompts/redigir_ganchos.py` (o gancho final).** Ao montar o bloco de fatos para o prompt, marcar cada linha: `[antigo]` quando a data for anterior a `redacao.meses_fato_antigo` (padrão 12) e `[de imagem]` quando o tipo for descrição de imagem. A regra do prompt passa a ser: *não afirme como posição atual nada marcado `[antigo]` ou `[de imagem]`; se usar, com ressalva ("há um tempo", "numa imagem que publicou"); nunca infira opinião ou posição da pessoa a partir de manchete ou foto.* A regra "afirme só o que está nos fatos" continua.
- **`validar_ganchos`** perde a checagem de categoria sensível (4.1) e segue estrutural (assunto válido, sem repetição, "evitar", tamanho). A verdade é garantida por prompt + a segunda tentativa que já existe, e verificada por teste.

### 4.3. Subir o piso ao objetivo (movimento 3)

Em `relevancia/pontuacao.py` → `avaliar_por_consulta`, a aderência ao objetivo passa a ser condição **necessária**, não uma entre várias suficientes:

- Só é `conector` se `aderencia_consulta >= consulta.minima`. Contato, temas do usuário e tags **enriquecem** (somam no `score` e fornecem `ponto_de_apoio`), mas **não promovem sozinhos** um assunto fora do objetivo. Abaixo do piso → `fora_do_dominio`, motivo "pouca relação com o pedido".
- `config/limiares.yaml`, bloco `conector.consulta`: avaliar subir `minima` para 0,50 (calibrar depois com a distribuição de `aderencia_consulta`, brief 042). **O ajuste principal é o piso virar necessário, não o número.**
- Efeito: sem notícia ligada ao pedido, `demais` fica vazio e o fluxo cai no aviso que já existe — melhor dizer "não achei nada sobre a eleição da OAB" do que entregar Lula disfarçado de convergência. Casa com o brief 045: o 045 aumenta a chance de a notícia certa ser coletada; o 046 recusa a errada.

---

## 5. Escopo (arquivos)

1. Movimento 1: os cinco arquivos dos sete pontos + a limpeza do módulo/yaml/descarte (4.1).
2. Movimento 2: `prompts/cruzar_por_que.py`; `nucleo/redacao.py` (marcação `[antigo]`/`[de imagem]`); `prompts/redigir_ganchos.py`; `config/limiares.yaml` + `Limiares` (bloco `redacao` com `meses_fato_antigo`).
3. Movimento 3: `relevancia/pontuacao.py` (`avaliar_por_consulta`); `config/limiares.yaml` (`conector.consulta.minima`).

---

## 6. Testes

- `tests/test_sem_censura_de_tema.py` (e inverter os testes atuais do filtro): post político e post de saúde públicos agora são lidos, guardados e podem virar fato e gancho; nenhum dos sete pontos descarta por categoria.
- `tests/test_cruzar_por_que_nao_atribui.py` (LLM falso): assunto político + contato sem fato de adesão → o "por quê" não afirma posição do contato; cita objetivo ou tema.
- `tests/test_redacao_fato_antigo_e_foto.py` (LLM falso): fato marcado `[antigo]` ou `[de imagem]` → não vira afirmação de posição atual (sai com ressalva ou não entra).
- `tests/test_piso_objetivo.py`: assunto com `aderencia_consulta` abaixo de `minima` mas `aderencia_contato` alta → `fora_do_dominio`, não `conector`.
- `tests/test_sem_objetivo_avisa.py`: todos os candidatos abaixo do piso de objetivo → `sem_assunto=True`, motivo "nenhum candidato passou do piso".
- Ajustar `test_configuracao.py` para o bloco `redacao` e qualquer mudança em `conector.consulta`.

---

## 7. Fora de escopo

- **Piso de privacidade sobre guardar dado privado de terceiro.** É decisão sua, e vira brief próprio se quiser. Este brief tira a censura; não a recoloca por outro nome.
- O caminho antigo `avaliar` (sem consulta): o fluxo em uso é o por-consulta. Se quiser o mesmo piso lá depois, é ajuste trivial.
- Reprocessar o que já foi descartado antes desta mudança — não há como; não foi guardado.
- Coleta e bloqueio do Google — é o brief 045.

---

## 8. Passos de execução

> AGENTS.md: o executor não roda `git` nem a suíte. Entrega a lista de arquivos tocados e o texto do commit; Sidarta autoriza. Proibido `git add -A`.

1. Movimento 1: remover os sete pontos e limpar o módulo/yaml/descarte.
2. Movimento 2: `cruzar_por_que`, marcação de fatos em `redacao.py`, regra em `redigir_ganchos`, bloco `redacao` nos limiares.
3. Movimento 3: piso necessário em `avaliar_por_consulta`, `conector.consulta.minima`.
4. Testes da seção 6.
5. Lista para `git add` (só os arquivos tocados) e mensagem:
   `feat(ganchos): usuario decide o tema; motor nao inventa atributo nem entrega assunto fora do objetivo (brief 046)`

`scripts/verificar.sh`, o teste com o pedido real refeito e o commit são passos de Sidarta.

---

## 9. Critérios de aceite (Sidarta, no Pro)

1. Um post político ou de saúde público do contato é lido e pode virar fato e gancho — nada é descartado por "tema perigoso".
2. Refazendo o pedido do Luiz, nenhuma sugestão afirma adesão política dele sem um post que diga isso; o "por quê" do menu não inventa "apoia X".
3. Quando não há notícia ligada à eleição da OAB-SP, a tela **avisa** em vez de entregar notícia nacional solta como "convergência".
4. Um fato de quatro anos atrás, ou lido de foto, não aparece como posição atual na mensagem.
