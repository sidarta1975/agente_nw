# Brief E1-004 — Filtro de categorias sensíveis e extrator de texto

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Depende de:** brief 003 (concluído e certificado)

---

## 1. Objetivo em uma frase

Dar ao projeto a segunda camada de proteção contra dado sensível de terceiro (o filtro determinístico) e o contrato que transforma texto livre sobre um contato em campos, tags e fatos — sem nenhum dos dois deixar passar o que não deveria.

---

## 2. Contexto e o que já existe

`descarte_sensivel` (`id, perfil_id, origem_texto, categoria, registrado_em`) e `fila_extracao` (`id, perfil_id, texto, origem, criado_em, processado, erro`) já estão na migração 001, com os modelos Pydantic `DescarteSensivel` e `FilaExtracao` já escritos — este brief não altera nenhuma tabela. `perfil` já tem todos os campos guiados da ficha (`cidade, naturalidade, linguas, formacao, cargo, setor, empresa, tem_filhos, faixa_etaria`) e `fato` já existe com os gatilhos `fato_sem_update`/`fato_sem_delete` que impedem edição — inserção é a única operação possível, então este brief nunca tenta atualizar um fato.

`queries/temas.py` já tem `obter_por_nome` e `obter_ou_criar`; `queries/perfil_tema.py` já tem `vincular`, que aceita `origem="sugerida"` (já é um dos valores válidos de `OrigemTema`) e `confirmado=False`. Este brief usa as duas sem alterá-las. `queries/fila_extracao.py`, `queries/descarte_sensivel.py`, `queries/fatos.py` e a atualização seletiva de campos guiados em `queries/perfis.py` ainda não existem — nasce aqui.

`agente_nw/perfil/` (importação de agenda, extração de texto, lacunas, centróide) e `agente_nw/nucleo/prompts/` já existem como pastas vazias — este brief é o primeiro a colocar algo dentro de `nucleo/prompts/`.

---

## 3. Escopo

1. **`config/termos_sensiveis.yaml`**: lista de termos por categoria, versionada (não é dado pessoal — é a regra de filtro em si, auditável, no mesmo grupo de `llm_routing.yaml` e `limiares.yaml`). Conteúdo completo no passo 1 da execução.
2. **`agente_nw/nucleo/sensivel.py`**: `verificar(texto: str) -> str | None` — devolve o nome da categoria encontrada (a primeira, se houver mais de uma) ou `None` se o texto estiver limpo. Comparação por palavra/expressão inteira, sem diferenciar maiúscula de minúscula, ignorando acentuação.
3. **`agente_nw/nucleo/modelos/extracao.py`**: `CamposExtraidos`, `TagSugerida`, `FatoDatado`, `RespostaExtracaoTexto` — o esquema do contrato `extrair_de_texto`.
4. **`agente_nw/nucleo/prompts/extrair_de_texto.py`**: o texto do prompt (instrução, o guia de campos da ficha, a proibição explícita das sete categorias, um exemplo resolvido) e o vínculo com o esquema do passo 3.
5. **`agente_nw/nucleo/database/queries/fila_extracao.py`**: `listar_pendentes`, `marcar_processado`, `marcar_erro`.
6. **`agente_nw/nucleo/database/queries/descarte_sensivel.py`**: `registrar(conexao, perfil_id, origem_texto, categoria, agora) -> int`.
7. **`agente_nw/nucleo/database/queries/fatos.py`**: `inserir(conexao, fato: Fato) -> int` — só inserção, nada mais (o gatilho já impediria, mas o módulo nem oferece a função).
8. **`agente_nw/nucleo/database/queries/perfis.py`**, função nova `atualizar_campos_guiados(conexao, perfil_id, campos: dict, agora)`: grava só os campos vazios — nunca sobrescreve um valor que já exista.
9. **`agente_nw/perfil/extrator.py`**: `processar_fila(cliente_llm, conexao, limite=20) -> ResumoProcessamento` — o orquestrador que liga tudo: lê pendentes, chama `extrair_de_texto`, passa cada campo/tag/fato pelo filtro, grava o que passar, descarta e registra o que não passar, marca o item como processado ou com erro.
10. **`agente_nw/cli.py`**: novo comando `agente_nw processar-fila`, que roda o processador do passo 9 e imprime o resumo (itens processados, tags gravadas, campos gravados, fatos gravados, descartes por categoria, erros). Fica disponível antes do ciclo diário (brief 012) existir, no mesmo espírito dos comandos-ponte do brief 005.

---

## 4. Fora de escopo, com justificativa

- **O prompt e o esquema de `qualificar`, `cruzar`, `rotular`, `cartao`.** Contratos de outros briefs (008 e 009).
- **Origem `notas_agenda` de verdade chegando em `fila_extracao`.** Isso é o brief 005 (importação da agenda), que ainda não existe — este brief testa o processador com itens inseridos manualmente na fila, não com uma agenda real.
- **Reprocessar item que já deu erro.** `fila_extracao.erro` fica registrado; decidir se e quando reprocessar automaticamente é comportamento do ciclo (brief 012), não deste brief.
- **Filtro sensível rodando sobre a saída dos assistentes pagos (Etapa 4) ou sobre o texto do WhatsApp (Etapa 2).** A proposta pede o mesmo filtro nesses dois pontos, mas nenhum dos dois existe ainda; quando existirem, os módulos correspondentes importam e chamam `nucleo/sensivel.verificar` — a função já nasce genérica o bastante para isso, mas ligar não é trabalho deste brief.

---

## 5. Decisões tomadas e deixadas abertas

**Tomadas:**

- **Lista de termos em YAML, não em código.** Mesma razão dos limiares: adicionar ou remover um termo não deveria exigir tocar em `.py`. Fica em `config/termos_sensiveis.yaml`, versionado — é a regra de proteção em si, não dado de ninguém.
- **O filtro roda sobre a saída do modelo, item por item — nunca sobre o texto de entrada inteiro.** É a saída (cada campo, cada tag, cada fato) que vai para o banco; é ela que precisa estar limpa. Isso também significa que um texto de entrada que mencione, de passagem, algo sensível sem que isso vire tag ou fato não é bloqueado na entrada — a proposta desenha o filtro para a saída, e barrar a entrada inteira derrubaria informação legítima só porque estava perto de uma informação sensível na mesma frase.
- **Campo guiado só é gravado se estiver vazio.** Se o usuário já preencheu `cidade` à mão, a extração automática nunca sobrescreve — o dado que a pessoa digitou é sempre mais confiável do que o que o modelo inferiu de uma nota.
- **Tag sugerida de contato usa o próprio trecho de lastro como descrição do tema, só na criação.** `tema.descricao` (a frase que vira embedding) não existe ainda para uma tag nova como "cabotagem"; o trecho que a justifica ("publicou sobre o novo terminal de cabotagem") já é uma frase corrida e serve bem. Se o tema já existir (por exemplo, já é tema do usuário), a descrição existente não é tocada — só o vínculo `perfil_tema` novo é criado.
- **`agente_nw processar-fila` existe desde já, como comando manual**, porque a proposta só amarra o processamento ao ciclo diário (brief 012) e ao botão do console (brief 010) — nenhum dos dois existe hoje, e sem um jeito de rodar isso à mão o brief não seria testável fora de teste automatizado.

**Deixadas abertas:**

- Reprocessamento automático de itens com erro — decisão do brief 012.
- Uso do mesmo filtro em Etapa 2 (WhatsApp) e Etapa 4 (assistentes pagos) — a função já serve para isso; ligar é trabalho desses briefs futuros.

---

## 6. Passos de execução

1. Escrever `config/termos_sensiveis.yaml` com este conteúdo (base para o filtro; Sidarta pode ampliar depois, mas o conjunto abaixo já cobre os 30 casos de teste do passo 7):

```yaml
saude:
  - diabetes
  - depressão
  - depressao
  - câncer
  - cancer
  - hipertensão
  - hipertensao
  - ansiedade
  - transtorno bipolar
  - cirurgia
  - tratamento psiquiátrico
  - tratamento psiquiatrico
religiao:
  - evangélico
  - evangelico
  - católico
  - catolico
  - espírita
  - espirita
  - umbanda
  - candomblé
  - candomble
  - muçulmano
  - muculmano
  - judeu
  - ateu
  - igreja
  - pastor
  - padre
politica:
  - PT
  - PL
  - Bolsonaro
  - Lula
  - petista
  - bolsonarista
  - de esquerda
  - de direita
  - filiado ao partido
  - votou em
sindicato:
  - sindicato
  - sindicalizado
  - sindical
  - greve
vida_sexual:
  - orientação sexual
  - orientacao sexual
  - homossexual
  - heterossexual
  - bissexual
  - gay
  - lésbica
  - lesbica
  - vida sexual
origem_racial:
  - pessoa negra
  - é negro
  - é branco
  - é pardo
  - é indígena
  - e indigena
  - raça
  - raca
  - etnia
menores:
  - filha de
  - filho de
  - anos de idade
  - menor de idade
```

2. `agente_nw/nucleo/sensivel.py`: carregar o YAML uma vez (`functools.lru_cache`), normalizar (minúsculas, sem acento) tanto os termos quanto o texto recebido, procurar cada termo como substring da versão normalizada; devolver a primeira categoria cujo algum termo bater, ou `None`.
3. `agente_nw/nucleo/modelos/extracao.py`, conforme a seção 3, item 3. `peso` de `TagSugerida` com `Field(ge=1, le=5)`, igual ao peso de `perfil_tema`.
4. `agente_nw/nucleo/prompts/extrair_de_texto.py`: prompt com o guia de campos (a tabela da seção 2.2 da proposta — só os nove campos que existem em `perfil`), a lista das sete categorias proibidas por nome (sem exemplo de termo, para não ensinar o modelo a citar o termo em vez de evitá-lo), instrução de que toda tag precisa vir com o trecho que a justifica, e o exemplo resolvido da proposta (Ricardo, `cidade: Santos`, tag `cabotagem`).
5. `queries/fila_extracao.py`, `queries/descarte_sensivel.py`, `queries/fatos.py`, e a função nova em `queries/perfis.py`, conforme a seção 3, itens 5 a 8. `atualizar_campos_guiados` usa `COALESCE(coluna, ?)` por campo, uma coluna de cada vez, só para os campos presentes no dicionário recebido.
6. `agente_nw/perfil/extrator.py`: `processar_fila`, conforme o fluxo descrito na seção 3, item 9. Cada campo, cada `tag.tag` e `tag.trecho`, e cada `fato.conteudo` passam por `sensivel.verificar` antes de qualquer gravação; uma detecção descarta só aquela peça (não o item inteiro) e chama `descarte_sensivel.registrar`. `FalhaJsonInvalido` do cliente de LLM marca o item com erro e segue para o próximo, sem travar o lote.
7. `tests/test_sensivel.py`: as 30 frases abaixo, 15 que devem passar e 15 que devem ser descartadas — literal, para não depender de critério do executor:

**Devem passar (15):**
1. "Trabalha com logística de cabotagem"
2. "Gosta de corrida de rua, já fez duas maratonas"
3. "Formado em engenharia civil pela Poli"
4. "Mora em Santos, litoral de São Paulo"
5. "Fala inglês e espanhol fluentes"
6. "Sócio de uma empresa de tecnologia"
7. "Gosta de vinho e de cozinha italiana"
8. "Torce para o Corinthians"
9. "Viajou para Portugal em 2025"
10. "Trabalha há cinco anos na mesma empresa"
11. "Tem MBA em finanças pela FGV"
12. "Gosta de fotografia de paisagem"
13. "Pratica vela nos fins de semana"
14. "Mudou de cargo recentemente, agora é diretor comercial"
15. "Estudou na USP, no campus de São Carlos"

**Devem ser descartadas (15, com a categoria esperada):**
1. "Tem diabetes tipo 2" — saúde
2. "Está em tratamento para depressão" — saúde
3. "Fez uma cirurgia de coluna recentemente" — saúde
4. "É evangélico praticante" — religião
5. "Frequenta um terreiro de umbanda" — religião
6. "É filiado ao PT desde jovem" — política
7. "Votou no Bolsonaro nas últimas eleições" — política
8. "Milita pela causa de esquerda no trabalho" — política
9. "É sindicalizado no sindicato da categoria" — sindicato
10. "Participou da greve geral do mês passado" — sindicato
11. "É homossexual assumido" — vida sexual
12. "Comentou sobre a orientação sexual do primo" — vida sexual
13. "É uma pessoa negra e fala sobre isso abertamente" — origem racial
14. "Comentou sobre a própria etnia indígena" — origem racial
15. "Tem uma filha de 9 anos que estuda perto do escritório" — menores

Teste confere 100% de acerto (as 15 primeiras devolvem `None`; as 15 seguintes devolvem a categoria indicada).
8. `tests/test_extrator.py`: insere manualmente um item de teste em `fila_extracao` com este texto — "Ricardo é diretor comercial numa empresa de logística em Santos. Fala inglês fluente. Estudou administração na FGV. Gosta de vela nos fins de semana e é sócio de um clube náutico. Tem dois filhos pequenos." — roda `processar_fila` (Ollama real) e confere: pelo menos 4 tags gravadas (esperadas: logística, vela, clube náutico ou náutica, administração — aceitar variação razoável de redação do modelo) e pelo menos 2 campos guiados corretos (`cidade = "Santos"`, `cargo` contendo "comercial", `setor` contendo "logística", `formacao` contendo "administração" — qualquer 2 já cobre o critério); item marcado como processado.
9. `tests/test_extrator_sensivel.py`: fabrica uma resposta de `extrair_de_texto` (sem depender do modelo real — usando um stub do cliente de LLM) que inclui uma tag com termo sensível e um fato limpo; confere que a tag é descartada, registrada em `descarte_sensivel` sem o trecho, e não aparece em `perfil_tema`; o fato limpo é gravado normalmente.
10. `tests/test_perfis_campos_guiados.py`: perfil com `cidade` já preenchida recebe `atualizar_campos_guiados` com uma `cidade` diferente — a original permanece; um perfil com `cidade` vazia recebe o mesmo campo — passa a valer.
11. `cli.py`: registrar `processar-fila`, sem argumento, chamando `extrator.processar_fila` com o cliente e o banco do container.
12. Rodar `agente_nw processar-fila` de verdade contra o item de teste do passo 8, uma vez, para confirmar o caminho completo fora do teste automatizado.
13. Atualizar `docs/PLAN.md`: brief 004 concluído; próximo é o brief 005 (importação da agenda).

---

## 7. Critérios de aceite

1. As 30 frases do passo 7: 100% de acerto (15 passam, 15 descartadas na categoria certa).
2. O texto de exemplo do passo 8 produz pelo menos 4 tags e pelo menos 2 campos guiados corretos.
3. Nenhum item processado chega ao banco sem passar pelo filtro — verificado pelo teste do passo 9, com uma detecção forçada.
4. Campo guiado já preenchido nunca é sobrescrito pela extração (passo 10).
5. `agente_nw processar-fila` roda de ponta a ponta contra o Ollama real pelo menos uma vez (passo 12), com resultado relatado.
6. `scripts/verificar.sh` verde nos testes que não dependem do Ollama (passos 7, 9, 10); os que dependem (passo 8) rodados manualmente com resultado relatado, seguindo o mesmo padrão de "pulado com motivo" se o Ollama não estiver no ar.

---

## 8. Riscos e como reverter

| Risco | Controle |
|---|---|
| Lista de termos do passo 1 não cobre uma variação de escrita comum (com/sem acento, maiúscula) | normalização antes da comparação (passo 2); Sidarta pode ampliar a lista a qualquer momento editando só o YAML |
| Modelo de 4B ocasionalmente menciona categoria sensível mesmo instruído a não mencionar | é exatamente o que o filtro determinístico existe para pegar — dupla camada, testada isoladamente da qualidade do modelo |
| `atualizar_campos_guiados` grava um campo com valor de baixa qualidade que o usuário não teria escolhido | campo continua editável à mão depois (console do brief 010); a extração só preenche o que estava vazio, nunca é a única fonte de verdade |
| Termo sensível aparece dentro de um trecho de lastro legítimo de uma tag não sensível (ex.: tag "corrida" com trecho que menciona outra coisa sensível de passagem) | o filtro roda sobre o trecho inteiro, não só sobre a tag — qualquer termo sensível no trecho descarta a tag inteira, por segurança, mesmo que a tag em si fosse inofensiva |
| Reverter | Todos os arquivos deste brief são novos, exceto a função nova em `queries/perfis.py` (aditiva, sem alterar as funções existentes) e o registro do comando em `cli.py`. Remover os arquivos novos e a função nova desfaz o brief sem tocar em nada dos briefs anteriores |

---

## 9. Relatório final obrigatório

Preencher o bloco da seção 8 de `AGENTS.md`, com o caminho do script de verificação para colar no terminal. Sem esse bloco preenchido, o brief não está concluído.
