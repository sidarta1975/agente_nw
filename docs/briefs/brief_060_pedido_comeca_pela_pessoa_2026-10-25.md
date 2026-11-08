# Brief 060 — O pedido começa pela pessoa: lista de contatos na tela inicial

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Conjunto:** nenhum (brief isolado, direto na `main`)
**Arquivos-alvo:** `agente_nw/console/app.py`, `agente_nw/console/templates/inicio.html`, `agente_nw/console/templates/pessoa.html`, `agente_nw/console/templates/pedir_pessoa.html` (novo), `agente_nw/nucleo/database/queries/perfis.py`, `agente_nw/nucleo/database/queries/rede_sem_perfil.py`, `agente_nw/nucleo/fluxo.py` (só se o contato escolhido ainda não chegar ao orquestrador), `tests/test_inicio_lista_contatos.py` (novo), `tests/test_sem_redes_sociais.py` (novo), `docs/docs/doc_060_pedido_comeca_pela_pessoa_2026-10-25.md`, `logs/commit_060.txt`, `logs/arquivos_060.txt`
**Seções a ler:** ARQUITETURA §10 (console); `nucleo/orquestracao.py` (contato forçado e divergência, brief 059)
**Modelo:** Sonnet
**Teste de aceite:** `tests/test_inicio_lista_contatos.py` e `tests/test_sem_redes_sociais.py`
**Depende de:** brief 059 (`19dc3f4`)
**Data:** 2026-10-25

---

## 1. Objetivo em uma frase

A tela inicial do console passa a começar pela lista de contatos. Sidarta escolhe a pessoa e só depois escreve o que quer. Um botão "Não está na lista" leva à caixa de texto livre de hoje. A página da pessoa ganha a opção "Esta pessoa não tem redes sociais".

---

## 2. Decisões de Sidarta (25/10)

- **A lista de contatos é o primeiro passo.** Escolher a pessoa antes evita a dúvida de "quem é", que hoje só aparece depois.
- **A lista tem a opção "Não está na lista".** Ela leva ao fluxo de hoje: frase livre, e o sistema reconhece ou cria o contato. Pedido sobre um grupo também vai por aí.
- **Existe amigo sem nenhuma rede social.** Para ele, o sistema não deve procurar perfil nem perguntar sobre redes.

---

## 3. Como fica

**3.1. Tela inicial (`/`).**
- No topo, um campo de busca. É um formulário comum que envia `?q=`, sem JavaScript, como manda a regra da tela única.
- Abaixo dele, a lista:
  - sem busca: os 20 contatos usados mais recentemente (último pedido ou consulta) e, completando, os demais em ordem alfabética, até 20;
  - com busca: até 50 contatos cujo nome ou apelido contém o termo, sem diferença de acento ou maiúsculas.
- Cada linha mostra o nome e a data do último pedido, ou "nunca".
- Abaixo da lista, o botão **"Não está na lista"**. Ele mostra a caixa de texto livre de hoje, que continua enviando para `/pedir` como agora.
- A consulta da lista mora em `queries/perfis.py` (`listar_para_inicio(conn, termo, limite)`).

**3.2. Escolher a pessoa.**
- Clicar num contato abre `/pessoa/<id>/pedir` (página nova `pedir_pessoa.html`): "O que você quer com **{nome}**?", com uma caixa de texto e o botão "Pedir".
- O envio vai para `/pedir`, com `perfil_id` no formulário, e cria o pedido com esse contato já escolhido. A extração do pedido continua tirando da frase o objetivo, o meio e o registro, mas a pessoa é a escolhida.
- Se a frase citar outro nome, vale a pergunta de contato divergente do brief 059.
- A página da pessoa (`/pessoa/<id>`) ganha o link "Fazer um pedido para {nome}", que leva à mesma página.

**3.3. "Esta pessoa não tem redes sociais."**
- Botão na página da pessoa. Grava "sem perfil" (`rede_sem_perfil`) em todas as redes que o sistema procura, numa função só: `rede_sem_perfil.marcar_todas(conn, perfil_id, agora)`.
- Depois disso, o pedido dessa pessoa não procura perfil nem pergunta sobre redes. A curadoria de hoje já respeita "sem perfil".
- Para desfazer, usa-se o "trocar perfil" que já existe. Conferir que ele reabre as redes marcadas.
- A página mostra "Sem redes sociais" no lugar da lista de redes quando todas estão marcadas.

---

## 4. Testes (escritos antes do código)

- `tests/test_inicio_lista_contatos.py`:
  - sem busca → no máximo 20 contatos, os recentes primeiro;
  - busca "jose" encontra "José";
  - o botão "Não está na lista" está na página;
  - `POST /pedir` com `perfil_id` cria o pedido com esse contato, sem pergunta de homônimos;
  - com `perfil_id` e uma frase que cita outro nome → pergunta de divergência (brief 059).
- `tests/test_sem_redes_sociais.py`:
  - o botão grava "sem perfil" em todas as redes;
  - um pedido em seguida não gera pergunta de rede;
  - "trocar perfil" desfaz.
- O LLM é sempre simulado.

---

## 5. Fora de escopo

Importar conversa do WhatsApp (brief 061); paginação além de 50 resultados; mudar as telas de "bastidores".

---

## 6. Passos e aceite

Executar com `/executar 060`. Aceite: testes da seção 4 verdes, gate verde, commit e push pelo executor.

Pendência para Sidarta na resposta final:
1. Abrir o console, escolher um contato da lista e fazer um pedido.
2. Usar "Não está na lista" uma vez.
3. Marcar o amigo sem redes sociais.
