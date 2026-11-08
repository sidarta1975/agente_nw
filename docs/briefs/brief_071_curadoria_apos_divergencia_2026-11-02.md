# Brief 071 — Curadoria de redes sociais não pode pular depois do "Sim" na divergência

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Conjunto:** nenhum (brief isolado, direto na `main`) — resolve a decisão [059-3], já registrada no PLAN
**Arquivos-alvo:** `agente_nw/nucleo/fluxo.py` (`decidir_divergencia`, `executar_pedido`, `continuar_pedido`, `_entender`, `_escrever`), `agente_nw/console/app.py` (`responder_pessoa`, ramo `tipo == "divergencia"`), testes do fluxo do console (achar o arquivo certo — provavelmente `tests/test_fluxo.py` ou `tests/test_console_app.py`), `docs/PLAN.md` (remover a linha `[059-3]` de "Decisões em aberto"), `docs/docs/doc_071_curadoria_apos_divergencia_2026-11-02.md`, `logs/commit_071.txt`, `logs/arquivos_071.txt`
**Seções a ler:** `agente_nw/nucleo/fluxo.py` inteiro, em especial `_entender`, `_escrever`, `executar_pedido`, `continuar_pedido` e `decidir_divergencia`; `agente_nw/console/app.py`, a rota `/pedido/<id>/pessoa` inteira; `agente_nw/nucleo/orquestracao.py` (`entender_pedido`, `encaminhar_pedido`, `Desfecho`) para entender onde a pergunta de divergência nasce e o que seria pulado
**Modelo:** Opus — toca a máquina de estados do pedido (quando pausa, quando retoma, o que cada retomada pressupõe já resolvido); um engano aqui reabre o mesmo bug de outro jeito
**Esforço:** médio
**Teste de aceite:** o teste novo do fluxo (seção 4)
**Depende de:** nada
**Data:** 2026-11-02

---

## 1. Objetivo em uma frase

Depois que o usuário responde "Sim" à pergunta de divergência (o pedido fala de um nome, mas o contato escolhido é outro), o pedido volta a passar pela etapa que resolve a rede social da pessoa — hoje ele pula direto para a redação, sem nunca ter rodado essa etapa para este pedido.

---

## 2. Achado no código (a causa exata, não só o efeito)

**2.1. `_entender` é quem cuida de localização/redes sociais; `_escrever` não.** `_entender` monta `navegacao` (`ContextoNavegacao`) e chama `orquestracao.entender_pedido(..., navegacao=navegacao, ...)`, que resolve o contato e, para cada rede social da pessoa, decide se confirma, pergunta entre candidatos, pede o link ou pula — é aqui que a curadoria de rede social de um pedido acontece. Se `encaminhar_pedido` devolver `Desfecho.ESPERAR` (há pergunta pendente, de qualquer tipo, incluindo a de divergência), `_entender` retorna sem chamar `_escrever`. `_escrever`, por sua vez, não refaz nada disso: só grava o pedido como "sem pessoa" ou chama `orquestracao.preparar_e_redigir(..., ler_redes_sociais=not correcao, ...)`, que é outra coisa — relê posts/fatos de um perfil de rede social **já vinculado**, não decide **qual** perfil é o do contato.

**2.2. `continuar_pedido` pula `_entender` por completo.**
```python
def executar_pedido(deps, pedido_id):
    _com_conexao_propria(deps, pedido_id, lambda conexao: _entender(deps, conexao, pedido_id))

def continuar_pedido(deps, pedido_id):
    _com_conexao_propria(deps, pedido_id, lambda conexao: _escrever(deps, conexao, pedido_id))
```
Isso é correto quando a pergunta pendente era de localização (`decidir_rede`, em `fluxo.py`): aquele caminho já resolve a rede social diretamente (`localizacao_mod.confirmar`) antes de marcar `sem_perguntas`, então quando chega a vez de `continuar_pedido`, a localização já está feita e ir direto a `_escrever` está certo.

**2.3. A divergência é diferente: pausa antes de `_entender` chegar à localização.** A pergunta de divergência (`pergunta_de_divergencia`, disparada dentro de `entender_pedido`) nasce *durante* a mesma passada de `_entender` que resolveria a localização — e `encaminhar_pedido` devolve `ESPERAR` assim que há qualquer pergunta pendente, inclusive a de divergência, **antes** de a localização deste pedido ter sido alcançada. Quando o usuário responde "Sim" (`decidir_divergencia` com `aceita=True`), o código só remove a pergunta da lista — não resolve localização nenhuma. Em `console/app.py`, a rota então enxerga `sem_perguntas() == True` e despacha `continuar_pedido` → `_escrever` direto, pulando a passada de `_entender` que faria a curadoria de rede social deste pedido pela primeira vez. É exatamente o que o relatório anterior registrou: "o console segue direto à redação... as redes pendentes são perguntadas no próximo pedido".

---

## 3. Decisões

**3.1. "Sim" na divergência tem que reabrir `_entender`, não saltar para `_escrever`.** Depois de `decidir_divergencia(aceita=True)` remover a pergunta e não restarem outras pendentes, o pedido deve ser retomado por um caminho que passe de novo pela resolução de localização/rede social — não pelo atalho de `continuar_pedido`. Decisão de implementação do executor, escolhendo entre:
  (a) `console/app.py` chamar `_despachar_execucao(pedido_id)` (sem `continuar=True`, ou seja, `executar_pedido`/`_entender` de novo) neste ramo específico, já que o contato agora está certo (`contato_id_forcado=pedido.perfil_id` em `_entender` evita perguntar divergência de novo);
  (b) ou introduzir uma nova função em `fluxo.py` (`retomar_apos_divergencia` ou nome equivalente) que chama `_entender` continuando a partir da localização, se (a) se mostrar insuficiente por algum efeito colateral de `_entender` reprocessar partes já feitas (ex.: reextrair o pedido do zero).
  Ao decidir, o executor verifica no código se `_entender` reprocessar desde o início (reextrair com o LLM, por exemplo) é caro, redundante ou arriscado para este caso — se for, (b); senão, (a) é mais simples e já reaproveita a máquina existente.

**3.2. A pergunta de divergência não pode voltar a aparecer no mesmo pedido.** Depois do "Sim", `pedido.perfil_id` já está confirmado; a nova passada por `_entender`/`entender_pedido` com `contato_id_forcado=pedido.perfil_id` não deve recriar a pergunta de divergência (ela só nasce quando o contato ainda não está decidido). Confirmar isso no código antes de aceitar a solução — é a `_entender` que já usa `contato_id_forcado=pedido.perfil_id` quando chamada a partir de `executar_pedido`, então isso só vale se a decisão 3.1 reusar esse caminho (opção a) ou replicá-lo (opção b).

**3.3. Nenhuma mudança no caminho de `decidir_rede`/`decidir_contato`.** Esses dois continuam chamando `continuar_pedido` direto quando `sem_perguntas()`, porque localização já foi resolvida antes de chegar lá — comportamento correto, fora de escopo.

**3.4. Fechar a decisão [059-3] no PLAN.** A linha `- [059-3] Depois de "Sim" à divergência...` em "Decisões em aberto" sai do `docs/PLAN.md` — resolvida por este brief.

---

## 4. Testes (escritos antes do código)

No arquivo de teste do fluxo do console (achar o nome certo lendo `tests/`, provavelmente ao lado dos testes já existentes de `decidir_divergencia`/`decidir_rede`):
- cenário completo: pedido cujo nome diverge do contato escolhido, com o contato tendo uma rede social ainda sem perfil confirmado (localização pendente) → responder "Sim" à divergência → a pergunta de localização daquela rede aparece como pendente no pedido (prova de que `_entender` rodou de novo), em vez de o pedido ir direto para `concluido`/redação sem nunca ter perguntado;
- o mesmo cenário, mas o contato já tem todas as redes sociais já confirmadas de pedidos anteriores (nada a perguntar) → depois do "Sim", o pedido chega à redação normalmente, com a leitura de rede social relevante refletida no resultado (confirma que o caso "nada pendente" não regride: continua indo até o fim);
- a pergunta de divergência não volta a aparecer depois do "Sim" (o contato já está fixado) — mesmo havendo outra ambiguidade de nome possível no texto original;
- o caminho de `decidir_rede`/`decidir_contato` (localização resolvida antes de `sem_perguntas`) continua indo direto para `_escrever`, sem passar de novo por `_entender` — teste de não regressão do comportamento correto que já existe.
- O LLM é sempre simulado; a navegação/rede social é simulada (como os testes existentes de localização já fazem).

---

## 5. Fora de escopo

- Qualquer mudança no comportamento de `decidir_rede` ou `decidir_contato` quando a pergunta pendente já era de localização (3.3).
- Mudar como a pergunta de divergência é formulada ou quando ela nasce dentro de `entender_pedido` — este brief só corrige o que acontece depois do "Sim".
- `--preparar` da CLI e a opção [059-1] — já fechada, sem mudança de código (ver PLAN).

---

## 6. Passos e aceite

Executar com `/executar 071`. Aceite: teste da seção 4 verde, gate verde, commit e push pelo executor.

Pendência para Sidarta na resposta final — teste real, no Pro: um pedido que diverge do nome do contato, respondido "Sim", deve voltar com pergunta de rede social pendente quando a pessoa ainda não tem perfil confirmado — e a mensagem final deve citar um fato recente dela, não só a ficha básica.
