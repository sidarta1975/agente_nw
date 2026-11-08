# agente_nw — Plano v3: a IA trabalha para o usuário

**Data:** 2026-10-11
**Substitui:** o plano do MVP (v3, 2026-09-17) e a proposta ao comitê (v5) no que diz respeito à experiência de uso e à geração de conteúdo. A infraestrutura descrita naqueles documentos permanece.
**Base de código:** `main` em `a874326` — arquitetura sob demanda, perfil de hardware por máquina, motor de cruzamento dirigido pelo contexto (briefs 034 e 035).

---

## 1. O princípio

O usuário escreve uma frase. A IA faz todo o resto.

Nenhum cadastro é pré-requisito para nada. Contato, perfil do usuário, temas, tags, fatos — tudo isso continua existindo no banco, mas passa a ser **criado e mantido pelo sistema**, a partir do que o usuário escreveu e do que a IA leu. O usuário nunca preenche; no máximo corrige o que a IA inferiu errado, e mesmo isso em linguagem natural, não em formulário.

O que o produto entrega deixa de ser um "menu de assuntos" para o usuário decidir o que fazer. Passa a ser **conteúdo pronto**: ganchos de conversa com a notícia por trás e a mensagem já redigida, no registro certo para aquela relação.

---

## 2. O que o usuário faz

Uma caixa de texto. Exemplos do que ele escreve, exatamente assim:

- *"Almoço quinta com o Marcos, sócio de escritório tributarista em SP. Faz uns dois anos que não nos falamos. Quero retomar sem parecer que estou pedindo algo."*
- *"Preciso mandar uma mensagem para a Cláudia, do clube de vela, agradecendo a ajuda no fim de semana e puxando assunto para um próximo encontro."*
- *"Vou encontrar o pessoal da Parceira na sexta. Me dá assunto de IA e tecnologia que não seja o óbvio."*
- *"Marcos de novo. Ele respondeu que anda ocupado com a reforma tributária. Continua a conversa."*

Opcionalmente, e só se quiser: colar um link de LinkedIn ou Instagram, ou dizer "lê o LinkedIn dele". Nada mais.

---

## 3. O que a IA faz, na ordem, sem perguntar nada

1. **Entende o pedido.** Extrai do texto livre: quem é a pessoa (nome e o que der para saber: profissão, cidade, vínculo com o usuário, há quanto tempo não se falam), qual é o objetivo (retomar, agradecer, pedir, manter, apresentar-se), qual é o meio (encontro presencial, WhatsApp, e-mail), o registro da relação (próximo, cordial, formal) e os assuntos que o usuário quer ou não quer. Se já existe contato com esse nome no banco, reconhece e carrega o histórico; se não existe, cria.
2. **Decide o que procurar.** A partir do que extraiu, a própria IA monta os termos de busca de notícia — não o usuário, não um cadastro de temas. "Sócio de escritório tributarista" vira consultas sobre reforma tributária, Carf, transação tributária, o que estiver acontecendo nesta semana.
3. **Busca a notícia de hoje.** Google News e feeds, na hora, pelos termos que ela montou. É este passo que compensa o fato de o modelo offline não saber de atualidade.
4. **Lê a rede social, se houver.** Com o navegador local e a sessão do usuário, se o link foi dado ou se o contato já tem rede cadastrada de uma consulta anterior. O que ler vira fatos sobre a pessoa, gravados por trás.
5. **Escolhe e escreve.** Com o motor dos briefs 034/035 por baixo (contexto como sinal principal, contato e fatos como reforço), seleciona três ou quatro ganchos e, para cada um, escreve: a notícia em duas linhas, por que serve para aquela pessoa e aquele objetivo, e **a mensagem pronta** no registro da relação — ou, se o meio é presencial, a forma de puxar o assunto.
6. **Guarda.** Contato criado ou atualizado, fatos novos, temas inferidos, o que foi gerado e o que o usuário marcou como usado. Na próxima vez, "Marcos de novo" já vem com tudo isso.

O usuário lê, copia a mensagem que quiser e, se quiser, diz em texto o que corrigir: *"o Marcos não é de SP, é do Rio"*, *"mais informal"*, *"não fala de política"*. A IA refaz.

---

## 4. Decisões de produto tomadas neste plano

**4.1. Geração de conteúdo passa a existir.** A proposta ao comitê e o `AGENTS.md` dizem "não existe geração nem envio de mensagem". Geração passa a existir; envio continua não existindo — o usuário copia e manda por onde quiser. A objeção original ("a IA não sabe qual é o relacionamento") é respondida pelo passo 1: o registro da relação vem da própria frase do usuário, e ele corrige em uma linha se a IA errar. Decisão de produto do proprietário do projeto, registrada aqui; o documento do comitê é atualizado em sua próxima versão.

**4.2. Nenhum formulário no caminho principal.** As telas Eu, Temas, Contatos, Ficha e Preparar deixam de ser a porta de entrada. Ficam acessíveis como "bastidores" para inspeção e correção, mas o uso normal não passa por elas. A tela inicial é a caixa de texto e o histórico.

**4.3. Perfil do usuário é inferido, não cadastrado.** Nome vem do sistema operacional ou da primeira frase. Temas do usuário são acumulados pelo que ele pede ao longo do tempo ("me dá assunto de IA" cria o tema IA com peso crescente a cada uso). A tela Eu mostra o que a IA inferiu e permite corrigir em texto.

**4.4. Tags e temas deixam de ser vocabulário da interface.** Internamente continuam (são os vetores do motor), mas o usuário nunca vê a palavra "tag" nem é convidado a classificar nada. A IA classifica.

**4.5. O modelo faz a extração e a redação; a coleta traz os fatos.** `qwen2.5:14b` no Pro, `qwen3:4b` no Air. Extração de contexto e redação de mensagem são tarefas novas no `llm_routing.yaml`, declaradas nos dois perfis. A qualidade da redação no 4b será menor; o plano aceita isso e mede.

**4.6. 100% local, sem API.** Inalterado.

**4.7. Sob demanda, sem agendamento.** Inalterado.

---

## 5. O que fica, o que muda, o que sai

**Fica, sem alteração:** cliente do Ollama e perfis por máquina; coleta RSS e Google News; leitura de rede social por navegador; banco SQLite com embeddings; histórico permanente por contato; motor de seleção e pontuação dirigido pelo contexto (034/035); console Flask local.

**Muda:**
- `ContextoConsulta` deixa de ser preenchido por formulário e passa a ser **produzido pela IA** a partir do texto livre (tarefa `extrair_pedido`).
- A busca de notícia passa a usar termos gerados pela IA, não só os do contexto literal.
- A saída do motor deixa de ser "menu" e passa a alimentar a tarefa de redação (`redigir_ganchos`).
- Contato e perfil do usuário passam a ser criados/atualizados automaticamente pelo fluxo.
- `AGENTS.md`, seção 7: reescrita conforme a seção 4 deste plano.

**Sai do caminho principal (continua no código como bastidor):** formulário de Preparar; cadastro manual de contato; telas de temas e tags; `importar-temas` como passo de instalação; `temas.yaml` como pré-requisito.

**Sai de vez:** nada é apagado neste plano. Remoções ficam para depois que o fluxo novo estiver em uso.

---

## 6. Sequência de briefs

Cada brief é pequeno, entrega algo usável sozinho, e segue as regras do `AGENTS.md` (o executor não roda a suíte nem o git; isso é do usuário, no terminal).

**Brief 036 — Extração do pedido em texto livre.** Tarefa `extrair_pedido` nos dois perfis; prompt e schema JSON (pessoa, vínculo, objetivo, meio, registro, assuntos desejados, assuntos a evitar, link de rede social se houver); reconhecimento ou criação automática do contato; geração dos termos de busca pela IA. Entrega: um comando `agente_nw pedir "<texto>"` que imprime o que foi entendido e cria o contato. Critério: dez frases reais do usuário, extração correta em pelo menos oito, sem nenhum formulário.

**Brief 037 — Redação dos ganchos e mensagens.** Tarefa `redigir_ganchos`; prompt que recebe o pedido extraído, os assuntos selecionados pelo motor com suas notícias, os fatos do contato e o histórico; saída estruturada: por gancho, notícia em duas linhas, por quê, mensagem pronta no registro da relação (ou abordagem presencial). Entrega: `agente_nw pedir` passa a imprimir o conteúdo completo. Critério: o usuário usa pelo menos um dos ganchos numa conversa real.

**Brief 038 — Tela única.** Console passa a abrir na caixa de texto; abaixo, o resultado do último pedido e o histórico por pessoa; botão "usei" por gancho; campo de correção em texto livre que refaz o pedido com a correção aplicada. Telas antigas viram menu "bastidores". Entrega: uso diário sem terminal.

**Brief 039 — Perfil do usuário inferido.** Nome automático; temas do usuário acumulados a partir dos pedidos; tela Eu mostra o inferido e aceita correção em texto. Remove `importar-temas` da instalação.

**Brief 040 — Continuidade de conversa.** "Marcos de novo, ele respondeu X": o pedido reconhece continuação, carrega o histórico e a última mensagem, e redige a resposta. Fecha o ciclo de uso real.

**Brief 041 — Medição.** Uma semana de uso real no Pro: quantos pedidos, quantos ganchos usados, quantas correções, tempo por pedido, taxa de JSON válido por tarefa. Decide os ajustes de prompt e a calibração dos limiares, e se o 4b do Air sustenta a redação.

---

## 7. Como se sabe que deu certo

- O usuário usa o programa a partir de uma frase e nunca abre um formulário.
- Em cada pedido, pelo menos um gancho é bom o bastante para ser usado como está ou com ajuste mínimo.
- O contato, seus fatos e o histórico existem no banco sem que o usuário os tenha cadastrado.
- A correção em texto ("mais informal", "não é de SP") muda o resultado sem mexer em nenhum campo.

---

## 8. Riscos aceitos

- O modelo de 14b vai errar extrações em frases ambíguas. A correção em texto é o mecanismo de recuperação; o brief 041 mede a taxa.
- Redação no 4b do Air pode sair genérica. Se o uso real mostrar isso, o Air passa a um modelo maior (8b) ou a redação fica reservada ao Pro — decisão com dado, no brief 041.
- Notícia de hoje depende do Google News responder; sem rede, o sistema redige a partir do histórico e dos fatos, e diz que não há notícia nova.
