# Brief 048 — Conteúdo que já funcionou vira molde, escolhido e adaptado por contexto

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Conjunto:** nenhum (brief isolado, direto na `main`)
**Arquivos-alvo:** `scripts/migracoes/0XX_perfil_genero_gramatical.sql` (nova), `agente_nw/nucleo/database/queries/perfis.py`, `agente_nw/nucleo/database/queries/gancho_uso.py`, `agente_nw/nucleo/database/queries/consulta_contato.py`, `agente_nw/nucleo/redacao.py`, `agente_nw/nucleo/prompts/redigir_ganchos.py`, `config/limiares.yaml` (bloco `moldes`), `agente_nw/console/templates/pessoa.html` (ou a ficha do contato, campo `genero_gramatical`), `tests/test_moldes_por_contexto.py`, `tests/test_molde_adapta_genero.py`, `tests/test_molde_atributo_compartilhado.py`, `tests/test_molde_verdade_046.py`, `tests/test_migracao_genero.py` (novos), `docs/docs/doc_048_molde_por_contexto_2026-10-15.md`, `logs/commit_048.txt`, `logs/arquivos_048.txt`
**Seções a ler:** o relatório do brief 047 (a mensagem já nasce da pessoa + objetivo); `nucleo/redacao.py` inteiro; `queries/gancho_uso.py` e `queries/consulta_contato.py` (histórico permanente e status `usado`/`nao_serve`)
**Modelo:** Opus: toca o prompt de redação e a regra de verdade do brief 046 ao mesmo tempo — risco de regressão em comportamento já calibrado
**Esforço:** alto
**Teste de aceite:** `tests/test_moldes_por_contexto.py`, `tests/test_molde_adapta_genero.py`, `tests/test_molde_atributo_compartilhado.py`, `tests/test_molde_verdade_046.py` e `tests/test_migracao_genero.py`
**Depende de:** brief 047 (`8c8ce64`) — o molde entra como mais uma fonte na mensagem que já nasce da pessoa e do objetivo. Convive com o 049 (gate de relação com o objetivo, já em produção) e o 046 (verdade sobre o contato).
**Data:** 2026-10-15

---

## 1. Objetivo em uma frase

Num pedido novo, o programa recupera as mensagens que já gerou cujo **contexto** se parece com o atual (objetivo + tipo de contato + registro), usa a melhor — de preferência uma que o usuário marcou "usei" — como **molde**, e a **adapta ao novo contato** (nome, gênero, o que couber), mantendo o que serve e trocando ou tirando o que não serve. O que decide é o contexto, nunca a origem do texto.

---

## 2. Princípio (nas palavras do Sidarta)

A mensagem do Luiz vira base para o João **se for boa para o João**. Ter ou não ter um dado pessoal do Luiz não é o relevante — o relevante é o ajuste ao contexto do João:

- **Dado compartilhado vai direto.** Luiz e João são advogados → "você é advogado", o enquadramento da eleição da OAB-SP e o convite ao jantar servem aos dois sem mexer.
- **O que difere, adapta.** Nome e **gênero**: Luiz → Maria vira concordância no feminino ("caro"→"cara", "advogado"→"advogada", pronomes).
- **O que só cabia à fonte, troca ou sai.** A peculiaridade do Luiz é substituída pelo equivalente do João, se houver, ou retirada — porque não cabe no contexto, não porque "é do Luiz".
- **Teste único:** a mensagem final é boa e verdadeira para o contexto do novo contato. Não há regra de proveniência.

A verdade do 046 continua: o que a mensagem afirma do João tem que ser verdade do João — e um atributo compartilhado ("advogado") é verdade dos dois, então entra.

---

## 3. O que já existe e é reaproveitado

- Mensagens geradas ficam em `gancho_uso` (status `entregue`/`usado`/`nao_serve`) e em `consulta_contato` (histórico permanente, com o pedido/contexto da geração).
- O `pedido` (brief 036) tem objetivo, meio, registro, assunto principal, interessa, vínculo.
- A ficha do contato (`perfil`) tem cargo, empresa, cidade.
- Logo, já temos a tríade que o molde precisa: **a mensagem**, **o contexto em que foi gerada** e **o desfecho** (`usei`/`não serve`). Falta recuperar por semelhança de contexto e alimentar a redação.

---

## 4. Decisões

**4.1. O que é o "contexto" de uma mensagem.** objetivo (convidar/pedir/retomar…) + tipo de contato (profissão/cargo e vínculo) + registro + o assunto/tema do pedido. É isso que define se uma mensagem passada serve a um pedido novo. Garantir que o contexto fica consultável junto da mensagem (quase tudo já está em `pedido`/`consulta_contato`; o executor confirma e completa o que faltar).

**4.2. Recuperação por contexto.** No pedido novo, antes de redigir, buscar as mensagens passadas de contexto parecido:
- mesmo objetivo;
- perfil de contato parecido — mesma profissão/cargo (ex.: advogado↔advogado), por regra simples sobre a ficha e/ou embedding do cargo;
- mesmo registro.

Ordenar por desfecho (as `usei` primeiro, as `nao_serve` nunca entram como molde bom) e por recência. Pegar as melhores (`moldes.maximo`, padrão 2–3).

**4.3. Adaptação ao novo contexto — o coração.** As mensagens-molde entram no prompt de redação (do 047) num bloco próprio — "MENSAGENS QUE JÁ FUNCIONARAM NESTE TIPO DE CONTEXTO; adapte à pessoa de agora" — com as regras:
- **carregue o que serve** ao novo contato: o objetivo e os atributos compartilhados (os dois são advogados → "você é advogado", a eleição, o convite);
- **adapte o que difere**: nome, **gênero gramatical**, cidade, cargo específico;
- **troque ou tire** o detalhe que só cabia à fonte: pelo equivalente do novo contato, se houver, ou nada;
- o molde dá **estrutura e tom**; a mensagem é escrita para o novo contato, não copiada;
- vale a verdade do 046: nada que seja falso para o novo contato.

**4.4. Gênero gramatical do contato.** Para adaptar Luiz→Maria o programa precisa do gênero gramatical do contato. Inferir do nome/perfil, **guardar no perfil** (migração: campo `genero_gramatical` em `perfil`, valores `masculino`/`feminino`/`desconhecido`), e deixar **corrigível pelo usuário** na ficha. Sem certeza, a redação usa forma neutra; o usuário ajusta. É campo de escrita (concordância), não juízo sobre a pessoa.

**4.5. O usuário é o dono.** O molde é sugestão, não gabarito. A mensagem sai como rascunho; o usuário adapta, muda e envia. Sem portão de qualidade no lugar dele.

---

## 5. Testes (escritos antes do código)

- `tests/test_moldes_por_contexto.py`: dois advogados; a mensagem `usei` do primeiro é recuperada como molde para o segundo; uma `nao_serve` não entra; registro diferente não casa.
- `tests/test_molde_adapta_genero.py` (LLM simulado): molde masculino + contato feminino → a saída concorda no feminino.
- `tests/test_molde_atributo_compartilhado.py`: "advogado" (compartilhado) permanece; a peculiaridade só da fonte não aparece afirmada do novo contato.
- `tests/test_molde_verdade_046.py`: nada falso sobre o novo contato entra, mesmo vindo do molde.
- `tests/test_migracao_genero.py`.

---

## 6. Fora de escopo

- **Leitura incremental das redes a cada pedido** (complementar o que já foi lido, sem reprocessar bloco já visto) — ataca o tempo e a duplicação de fatos; é o próximo brief.
- **Reaproveitamento do acervo comum de notícias entre contatos** — já está no 045 (acervo global + `horas_reuso_termo`); se faltar algo, entra no brief da leitura incremental.
- Enviar mensagem; nada disso muda.

---

## 7. Passos e aceite

Executar com `/executar 048`. Aceite: testes da seção 5 verdes, gate verde, commit e push pelo executor.

Pendência para Sidarta na resposta final — teste real, no Pro:
1. Depois de usar uma mensagem com um advogado, um pedido com o mesmo objetivo para outro advogado parte da mesma estrutura, adaptada ao novo contato.
2. Luiz → Maria: a mensagem sai no feminino, sem resíduo masculino.
3. O atributo compartilhado ("advogado", a eleição) é mantido; a peculiaridade que não cabe ao novo contato não aparece afirmada dele.
4. O gênero gramatical do contato é editável na ficha, e a redação o respeita.
5. Nada falso sobre o novo contato entra pela porta do molde (046 continua).
