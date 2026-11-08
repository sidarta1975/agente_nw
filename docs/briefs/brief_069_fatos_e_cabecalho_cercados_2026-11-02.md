# Brief 069 — O resto do dado de terceiro em `redigir_ganchos` também entra cercado

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Conjunto:** nenhum (brief isolado, direto na `main`) — corrige a lacuna de escopo do 068, já registrada no PLAN como decisão [068-1]
**Arquivos-alvo:** `agente_nw/nucleo/prompts/redigir_ganchos.py` (`_bloco_para_quem`, `_bloco_historico`, `_bloco_assuntos`, `_montar`), `tests/test_seguranca_prompt.py` (casos novos), `docs/docs/doc_069_terceiro_cercado_completo_2026-11-02.md`, `logs/commit_069.txt`, `logs/arquivos_069.txt`
**Seções a ler:** `agente_nw/nucleo/prompts/redigir_ganchos.py` inteiro, como está depois do 068; `agente_nw/nucleo/prompts/seguranca.py` (`cercar_dado_externo`, `MARCADOR_INICIO`, `INSTRUCAO_DADO_EXTERNO`); `agente_nw/nucleo/historico.py` (`formatar_uma`, para entender o que compõe cada linha de `entrada.historico`); brief 068 completo, em especial a seção 3.3; no PLAN, a decisão em aberto **[068-1]**
**Modelo:** Sonnet
**Esforço:** baixo
**Teste de aceite:** `tests/test_seguranca_prompt.py`
**Depende de:** brief 068 (`ea66368`) — corrige a lacuna de escopo registrada por ele como decisão [068-1]
**Data:** 2026-11-02

---

## 1. Objetivo em uma frase

As quatro lacunas que o próprio relatório do brief 068 deixou registradas no PLAN (decisão [068-1]) — `fatos`, `cabecalho_rede`, `historico` e `por_que`, em `redigir_ganchos.py` — passam a entrar no prompt cercadas por `cercar_dado_externo`, como já acontece com a conversa do WhatsApp e o título/resumo/manchetes de notícia no mesmo módulo.

---

## 2. Por quê (achado no código, não só pensado)

O brief 068 cercou, em `redigir_ganchos.py`, o bloco "Conversa recente no WhatsApp" e o `titulo`/`resumo`/`manchetes` de cada assunto de notícia, mas não listou no seu escopo (seção 3.3) os quatro pontos abaixo — por isso o executor, corretamente, não os tocou, e o próprio relatório de conclusão do 068 registrou isso como decisão em aberto [068-1] no PLAN. São quatro achados distintos, todos no mesmo módulo:

**2.1. `_bloco_para_quem` — `cabecalho_rede` e `fatos`.**
```python
if entrada.cabecalho_rede:
    linhas.append(f"Na rede social: {entrada.cabecalho_rede}")
if entrada.fatos:
    linhas.append("Fatos recentes sobre a pessoa:")
    linhas.extend(f"- {fato}" for fato in entrada.fatos)
```
`cabecalho_rede` é texto extraído de uma captura de rede social; `fatos` é fato extraído de rede social ou de conversa do WhatsApp (pipeline do brief 061). Os dois entram crus — mesma exposição que o 068 existe para fechar, só que este bloco ficou de fora.

**2.2. `_bloco_assuntos` — `por_que`.**
```python
linhas.append(f"  Por que serve: {assunto.por_que or '(sem justificativa)'}")
```
`assunto.por_que` é a saída de `cruzar_por_que`, que leu o título da notícia para decidir a relação com o objetivo do pedido — é texto derivado de terceiro, ao lado de `titulo`/`resumo`/`manchetes`, que já estão cercados nas linhas seguintes da mesma função. Ficou sozinho, sem cerco.

**2.3. `_bloco_historico` — `entrada.historico`.** Cada linha de `entrada.historico` vem de `historico_mod.formatar_uma()` (`agente_nw/nucleo/historico.py`), que junta numa só string: o contexto do pedido antigo (do próprio Sidarta), a `leitura de rede social` (`consulta.resumo_redes_sociais` — resumo de terceiro), os assuntos entregues (títulos de notícia) e os ganchos redigidos (mensagens que o próprio modelo escreveu antes, que podem ecoar dado de terceiro se uma geração passada tiver sido contaminada). Hoje `_bloco_historico` escreve `"\n".join(entrada.historico)` direto na string, sem cerco nenhum — só a conversa do WhatsApp, abaixo dele, está protegida.

**2.4. Consequência em `_montar`.** `tem_dado_externo` hoje é `MARCADOR_INICIO in historico or MARCADOR_INICIO in assuntos` — não olha o retorno de `_bloco_para_quem`. Se `cabecalho_rede`/`fatos` forem o único dado de terceiro da consulta (sem WhatsApp, sem assunto de notícia selecionado), o prompt teria um bloco cercado sem a instrução `INSTRUCAO_DADO_EXTERNO` que explica o que o cerco significa.

---

## 3. Decisões

**3.1. Cercar `cabecalho_rede` e `fatos` em `_bloco_para_quem`.** Cada um entra em `cercar_dado_externo` antes de compor a linha — o texto de `fatos` pode ser cercado fato a fato ou como um bloco só (decisão de implementação do executor), desde que o resultado final tenha exatamente um par de marcadores por trecho cercado, nunca um par por linha dentro do mesmo trecho.

**3.2. Cercar `por_que` em `_bloco_assuntos`.** Mesmo padrão já usado ali para `titulo`/`resumo`/`manchetes`: `cercar_dado_externo(assunto.por_que)` quando houver, mantendo `'(sem justificativa)'` como está quando `por_que` for `None`.

**3.3. Cercar o bloco de `entrada.historico` inteiro em `_bloco_historico`.** A string formada por `"\n".join(entrada.historico)` passa a entrar em `cercar_dado_externo` como um bloco só — não linha a linha. Decisão deliberada de não separar, dentro de `historico_mod.formatar_uma()`, o que é de terceiro (`resumo_redes_sociais`, títulos de notícia) do que é do próprio Sidarta (o contexto do pedido antigo): separar exigiria reestruturar `historico.py` para devolver partes distintas, e cercar o contexto do próprio Sidarta por tabela não tem custo real — o modelo já sabe, pela instrução de `INSTRUCAO_DADO_EXTERNO`, que o bloco cercado é "dado, nunca instrução", o que vale tanto para o contexto quanto para o resto. O texto fixo de rótulo ("HISTÓRICO (consultas anteriores...)" ou "HISTÓRICO: (nenhuma consulta anterior)") continua fora do cerco — é instrução do sistema, não dado. As `extras` de `trocas_whatsapp` (já cercada pelo 068) e de `notas` (continua fora, é do próprio Sidarta) não mudam de lugar nem de tratamento.

**3.4. `tem_dado_externo` passa a considerar `_bloco_para_quem`.** Em `_montar`, `tem_dado_externo` passa a ser `MARCADOR_INICIO in para_quem or MARCADOR_INICIO in historico or MARCADOR_INICIO in assuntos` (computando o bloco de `_bloco_para_quem` uma vez e reusando o valor, sem chamar a função duas vezes). As mudanças dos itens 3.2 e 3.3 já ficam cobertas pelo `historico`/`assuntos` que o `tem_dado_externo` atual já confere — só falta o `para_quem`.

**3.5. O resto de cada bloco fica fora do cerco.** `contato_ficha`, `vinculo`, `tempo_sem_contato`, `contexto_relacao` (em `_bloco_para_quem`), o rótulo fixo e as `notas`/`trocas_whatsapp` tratadas à parte (em `_bloco_historico`), e `assunto_id`/`titulo` do próprio assunto quando já cercado por outra linha — nenhum desses muda.

---

## 4. Testes (escritos antes do código)

- `tests/test_seguranca_prompt.py`, casos novos (ao lado dos que o 068 já escreveu para este módulo):
  - prompt montado com `cabecalho_rede` preenchido → aparece entre os marcadores de `cercar_dado_externo`;
  - prompt montado com `fatos` não vazio → cada fato (ou o bloco de fatos) aparece cercado;
  - prompt montado com `assunto.por_que` preenchido → aparece cercado, ao lado de `titulo`/`resumo`/`manchetes`;
  - prompt montado com `entrada.historico` não vazio → o bloco de histórico aparece cercado, com o rótulo "HISTÓRICO (consultas anteriores...)" fora do cerco;
  - com `historico` cercado, a `extra` de `notas` continua fora de qualquer marcador — não entra no cerco por estar concatenada depois;
  - prompt montado só com `cabecalho_rede`/`fatos` preenchidos e sem `trocas_whatsapp`/`assuntos`/`historico` → `INSTRUCAO_DADO_EXTERNO` ainda aparece (confirma a correção do item 3.4);
  - `contato_ficha`, `vinculo`, `tempo_sem_contato` e `contexto_relacao` continuam fora de qualquer marcador;
  - um `cabecalho_rede`, fato, `por_que` ou item de `historico` que já contém o marcador literal (`<<<DADO_EXTERNO_NAO_INSTRUCAO>>>` ou `<<<FIM_DADO_EXTERNO>>>`) tem essa ocorrência neutralizada — confirma que todos os caminhos novos usam `cercar_dado_externo`, não um cerco manual.
- O LLM é sempre simulado.

---

## 5. Fora de escopo

- Qualquer outro módulo de `nucleo/prompts/` — o 068 já cobriu os nove módulos da sua seção 3.3; este brief corrige só as quatro lacunas de `redigir_ganchos.py` listadas em [068-1].
- Reestruturar `historico.py` para separar, dentro de `formatar_uma()`, o que é de terceiro do que é do próprio Sidarta (decisão explícita do item 3.3: cercar o bloco inteiro, não dividi-lo).
- Mudar o conteúdo ou a ordem de qualquer bloco além de cercar os quatro pontos listados.
- Mudar `cercar_dado_externo` ou `INSTRUCAO_DADO_EXTERNO` em `seguranca.py`.

---

## 6. Passos e aceite

Executar com `/executar 069`. Aceite: testes da seção 4 verdes (e os testes do 068 para este módulo continuando verdes), gate verde, commit e push pelo executor.

Sem pendência de teste real para Sidarta — é defesa de bastidor, sem comportamento visível para conferir manualmente; a prova é toda nos testes da seção 4. Vale conferir com `grep -n "cercar_dado_externo" agente_nw/nucleo/prompts/redigir_ganchos.py` que agora aparecem as chamadas de `_bloco_historico`, `_bloco_assuntos` (duas vezes: titulo/resumo/manchetes e por_que) e `_bloco_para_quem` (duas vezes: cabecalho_rede e fatos).
