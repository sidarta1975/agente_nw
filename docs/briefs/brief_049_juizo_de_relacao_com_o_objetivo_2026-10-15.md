# Brief 049 — Só vira gancho a notícia que o modelo julga ligada ao objetivo

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Conjunto:** nenhum (brief isolado, direto na `main`)
**Arquivos-alvo:** `nucleo/prompts/avaliar_relacao_objetivo.py` (novo), `nucleo/modelos/` (modelo de resposta do gate), `relevancia/cruzamento.py`, `config/llm_routing.yaml`, `config/limiares.yaml` (flag opcional), `tests/test_gate_objetivo.py`, `tests/test_gate_zera_menu.py`, `tests/test_gate_lote_ordem.py` (novos), `docs/docs/doc_049_juizo_de_relacao_com_o_objetivo_2026-10-15.md`, `logs/commit_049.txt`, `logs/arquivos_049.txt`
**Seções a ler:** `relevancia/pontuacao.py` (`avaliar_por_consulta`) e `relevancia/cruzamento.py` (`cruzar_contato_por_consulta`) inteiros; `nucleo/prompts/cruzar_por_que.py`; o relatório do brief 047 (mensagem base sempre sai)
**Modelo:** Sonnet
**Esforço:** médio
**Teste de aceite:** `tests/test_gate_objetivo.py`, `tests/test_gate_zera_menu.py` e `tests/test_gate_lote_ordem.py`
**Depende de:** brief 047 (`8c8ce64`) — a mensagem base sai sempre, então o gate pode zerar o menu sem deixar o usuário sem nada. Convive com o 046 (piso por embedding, já em produção) e o 048 (molde, ainda não executado).
**Data:** 2026-10-15

---

## 1. Objetivo em uma frase

Depois da pré-seleção barata por embedding, um **julgamento sim/não do modelo** decide, assunto por assunto, se a notícia tem relação real com o objetivo do pedido; só o "sim" entra no menu e pode virar gancho de notícia. A mensagem base do 047 sai sempre, com ou sem gancho.

---

## 2. Por que (o teste do 047 com o Luiz)

O pedido era apoio para a chapa da OAB-SP. A mensagem base saiu certa, mas ainda veio junto um gancho sobre "Apoiadores de Lula ocupam Copacabana", com a justificativa vazia "pode ser relevante para discutir a importância do apoio em eleições".

O piso do 046 (`conector.consulta.minima = 0,45`) derrubou de cinco candidatos para um, mas não derruba esse: o embedding **não separa "eleição da OAB" de "política nacional"**. No teste, o item do Lula tirou 0,471 (acima do piso) e o único item certo — processo da OAB contra uma startup — tirou a **menor** nota, 0,451. O piso está no teto do que o vetor consegue.

O modelo, porém, separa: no `cruzar_por_que` ele escreveu "eleição da OAB-SP é **o objetivo**" só para o item da OAB, e "eleição é um **ponto de interesse**" para os demais. Falta tornar esse juízo explícito e usá-lo para cortar.

---

## 3. O que já existe e é reaproveitado

- `relevancia/pontuacao.py` → `avaliar_por_consulta` classifica cada candidato em `conector` / `viavel_com_esforco` / `fora_do_dominio`, com `aderencia_consulta`.
- `relevancia/cruzamento.py` → `cruzar_contato_por_consulta` já: seleciona por embedding, descarta o que não é `conector` (gravando `fora_do_dominio` com motivo), ordena e corta para o menu, e tem o caminho de aviso (`sem_assunto`).
- `prompts/cruzar_por_que.py` já faz o modelo olhar objetivo + candidatos — a infraestrutura de chamada em lote está pronta.
- Brief 047: a mensagem base garante entrega mesmo com o menu vazio.

---

## 4. Decisões

**4.1. O gate.** Entre a classificação por embedding e o corte para o menu, rodar um julgamento do modelo sobre os candidatos que o embedding marcou `conector`. Para cada um: **tem relação real com o objetivo do pedido, para este contato? sim/não + motivo curto.** Só "sim" permanece `conector`; "não" vira `fora_do_dominio`, motivo "sem relação com o objetivo (juízo do modelo)".

**4.2. Uma chamada, em lote.** Os candidatos (até `conector.candidatos_por_contato`, ~10) vão num prompt só. Entrada: objetivo + frase do pedido + ficha do contato (cargo, vínculo) + lista de candidatos (título + resumo). Saída: por candidato, `{relaciona: bool, motivo: str}`, na mesma ordem. Prompt novo `nucleo/prompts/avaliar_relacao_objetivo.py`; modelo de resposta em `nucleo/modelos/`.

**4.3. Onde entra.** `relevancia/cruzamento.py` → `cruzar_contato_por_consulta`, depois de montar `avaliacoes` e antes de formar `demais`/`selecionados_para_menu`. Os reprovados são gravados como descartados, com o motivo do gate — o mesmo mecanismo já usado para `fora_do_dominio`.

**4.4. A base sempre sai.** Se o gate derruba todos, o menu fica vazio: `sem_assunto = True`, e a entrega é a mensagem base do 047 — nenhum gancho de notícia forçado. É exatamente o caso do Luiz: base, zero gancho.

**4.5. Papel dos filtros.** O piso por embedding (046) continua como primeiro filtro, barato, que corta o grosso. O gate é o segundo, semântico, que decide o que o vetor não consegue. Não substitui o 046; fecha a porta que ele deixa aberta.

**4.6. O software não julga tema.** O gate pergunta "tem relação com o objetivo?", não "este tema é adequado?". Nada de LGPD, nada de censura de assunto — isso continua decisão do usuário (046, movimento 1).

---

## 5. Testes (escritos antes do código)

- `tests/test_gate_objetivo.py` (LLM simulado): candidatos Lula/Bolsonaro/manifestação/Sicoob → `relaciona=False` → `fora_do_dominio`; item sobre a OAB → `relaciona=True` → fica no menu.
- `tests/test_gate_zera_menu.py`: gate reprova todos → `sem_assunto=True`; combinado com o 047, a entrega é a mensagem base.
- `tests/test_gate_lote_ordem.py`: a resposta do gate casa candidato a candidato na ordem; resposta de tamanho errado cai para `fila_revisao` e o pedido segue (sem gate, como está hoje).

---

## 6. Fora de escopo

- Molde entre contatos (brief 048).
- Leitura incremental das redes e o tempo da etapa de qualificação (brief próprio).
- Coleta e bloqueio do Google (045).

---

## 7. Passos e aceite

Executar com `/executar 049`. Aceite: testes da seção 5 verdes, gate verde, commit e push pelo executor.

Pendência para Sidarta na resposta final — teste real, no Pro:
1. Refazendo o pedido do Luiz, o menu **não** traz mais Lula, Bolsonaro, manifestação nem o Sicoob.
2. Sem notícia ligada à OAB, a entrega é a mensagem base, sem gancho de notícia.
3. Havendo notícia de verdade sobre a OAB (ou o mundo profissional dele), ela entra como gancho.
4. O gate pergunta só sobre relação com o objetivo — nunca sobre o tema ser aceitável.
