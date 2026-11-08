# Brief E1-005 — Importação da agenda

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Depende de:** brief 004 (concluído e certificado)
**Fecha a semana 1** do plano de execução.

---

## 1. Objetivo em uma frase

Dar à base de contatos sua origem real — agenda do macOS e CSV do Google Contatos, os dois idempotentes pela chave telefone — e três comandos de linha que fazem as vezes do console até ele existir.

---

## 2. Contexto e o que já existe

`queries/perfis.py` já tem tudo que os dois leitores precisam: `inserir_ou_atualizar_contato` (upsert por telefone ou e-mail), `obter_por_telefone_ou_email`, `ativar`. Nenhuma das duas é alterada. `queries/perfil_tema.py` já tem `vincular` (aceita `origem="importada"`) e `confirmar`; `queries/temas.py` já tem `obter_por_nome`/`obter_ou_criar`. `queries/fila_extracao.py` (criada no brief 004) tem `listar_pendentes`, `marcar_processado`, `marcar_erro`, mas **não tem `inserir`** — ninguém precisou inserir na fila até agora, só consumir dela; este brief acrescenta essa função, sem tocar nas três que já existem.

`phonenumbers` e `pyobjc-framework-Contacts` já são dependências do projeto desde o brief 001, nunca usadas até agora. `agente_nw/perfil/` já existe com `extrator.py`; este brief acrescenta os módulos de leitura, sem tocar no que já está lá.

A permissão de acesso à agenda no macOS é concedida por **aplicativo**, não por script — quem pede é o Terminal (ou o terminal que estiver rodando o Python), e o sistema lembra a decisão para esse aplicativo. Negada uma vez, o macOS não pergunta de novo sozinho; é preciso liberar manualmente em Ajustes do Sistema → Privacidade e Segurança → Contatos.

---

## 3. Escopo

1. **`agente_nw/perfil/normalizacao.py`**: `telefone_e164(bruto: str | None) -> str | None` — usa `phonenumbers`, região padrão `BR` quando o número não tem código de país; devolve `None` (nunca lança exceção) se não conseguir normalizar, para nunca travar uma importação por causa de um número mal formatado.
2. **`agente_nw/perfil/lacunas.py`**: `ORDEM_IMPACTO` (lista fixa dos campos guiados, na ordem de impacto da proposta: `cargo, setor, empresa, cidade, linguas, formacao, naturalidade, tem_filhos, faixa_etaria`) e `campos_faltando(perfil: Perfil) -> list[str]`, que devolve os nomes dos campos vazios, nessa ordem.
3. **`agente_nw/perfil/agenda_macos.py`**: `solicitar_permissao() -> bool` (bloqueia até o usuário decidir, via `CNContactStore`) e `ler_contatos() -> list[ContatoBruto]`, buscando nome, telefones, e-mails, empresa, cargo e nota — cada campo lido isoladamente, para que a falta de um (em especial a nota, que pode estar bloqueada por uma restrição do próprio macOS a apps não assinados) não derrube a leitura dos demais.
4. **`agente_nw/perfil/agenda_google_csv.py`**: leitor do CSV exportado de `contacts.google.com`, casando colunas por prefixo (mesma lógica tolerante do script da proposta), extraindo nome, telefone, e-mail, empresa, cargo, notas e os marcadores (coluna "Group Membership").
5. **`agente_nw/perfil/importador.py`**: `importar(contatos: list[ContatoBruto], conexao) -> ResumoImportacao` — comum aos dois leitores: normaliza telefone, faz upsert via `queries/perfis.inserir_ou_atualizar_contato`, grava marcadores como temas/tags (`origem="importada"`), enfileira nota não vazia em `fila_extracao` (`origem="notas_agenda"`), nunca marca o contato como ativo.
6. **`queries/fila_extracao.py`**, função nova `inserir(conexao, perfil_id, texto, origem, agora) -> int`.
7. **`agente_nw/cli.py`**: `importar-agenda --fonte {macos,csv} [--arquivo CAMINHO]` (sai de `COMANDOS_RESERVADOS`); `ficha <telefone>` (sai de `COMANDOS_RESERVADOS`); `ativar <telefone>` (sai de `COMANDOS_RESERVADOS`); `confirmar-tags <telefone> [--todas | --ids 1,3,5]` (sai de `COMANDOS_RESERVADOS`).

---

## 4. Fora de escopo, com justificativa

- **Grupos de contato do macOS como origem de marcador.** O CSV do Google já cobre "marcador vira tag" de forma direta (coluna própria); replicar isso a partir de `CNGroup` do macOS exigiria uma segunda consulta e casamento por identificador, para um ganho pequeno (nem todo mundo organiza a agenda do Mac em grupos). Fica de fora agora; se um dia for pedido, é aditivo — não quebra nada deste brief.
- **Sincronização contínua ou automática da agenda.** Os dois comandos são rodados à mão; agendar isso é trabalho do ciclo diário (brief 012), e mesmo lá a proposta não pede sincronização automática da agenda, só da coleta.
- **Editar campo de perfil pelos três comandos de linha.** `ficha`, `ativar` e `confirmar-tags` mostram e confirmam o que já está no banco; escrever um campo à mão (cidade, cargo etc.) é trabalho do console (brief 010) — os comandos de linha são ponte mínima, não substituto completo.

---

## 5. Decisões tomadas e deixadas abertas

**Tomadas:**

- **Falha ao normalizar um telefone nunca derruba a importação inteira.** Um número mal formatado no meio de duzentos contatos é esperado; `telefone_e164` devolve `None` para esse contato (que ainda pode entrar pelo e-mail) e a importação segue.
- **Leitura de nota do macOS é best-effort, isolada das demais.** Contatos com nota bloqueada pelo sistema entram sem nota, não travam a leitura dos outros campos. Fica registrado no resumo do comando quantas notas não puderam ser lidas, para Sidarta saber se essa restrição está ativa na máquina dele.
- **Ordem de impacto dos campos guiados é fixa, definida neste brief** (seção 3, item 2), direto da tabela da proposta — não é algo a calibrar depois; é só uma prioridade de exibição.
- **A ordem de exibição das tags não confirmadas em `ficha` é a mesma usada por `confirmar-tags --ids`** — por `tema_id` ascendente, a mesma ordem que `perfil_tema.listar_por_perfil` já devolve. Os dois comandos rodam em processos separados; sem uma ordem determinística do banco, os números mostrados numa chamada não bateriam com os da outra.
- **Telefone é sempre a chave de busca dos três comandos de linha**, aceitando qualquer formato de entrada — normalizado internamente antes de procurar, igual à importação.

**Deixadas abertas:**

- Se a restrição de nota do macOS afetar todos os contatos na prática (não só alguns), fica registrado como achado em `docs/PLAN.md` — não há solução de código para uma permissão que o sistema operacional nega por política.

---

## 6. Passos de execução

1. `agente_nw/perfil/normalizacao.py`: `telefone_e164`, com testes cobrindo número já em E.164, número nacional sem código de país (assume BR), número claramente inválido (devolve `None`, não lança).
2. `agente_nw/perfil/lacunas.py`: `ORDEM_IMPACTO` e `campos_faltando`, com teste para um perfil com todos os campos vazios (devolve a lista inteira, na ordem) e um com metade preenchida (devolve só os vazios, na mesma ordem relativa).
3. `agente_nw/perfil/agenda_macos.py`: `solicitar_permissao` e `ler_contatos`, com os campos e o tratamento de falha isolada da seção 3, item 3. Sem teste automatizado contra a agenda real (não dá para simular em CI) — validado no passo 10.
4. `agente_nw/perfil/agenda_google_csv.py`: leitor de CSV, com um arquivo de teste de 5 linhas fabricado (nomes de coluna como o Google exporta hoje, um contato sem telefone mas com e-mail, um com marcadores, um com nota) em `tests/fixtures/contatos_exemplo.csv`.
5. `queries/fila_extracao.py`: acrescentar `inserir`, sem tocar nas três funções existentes.
6. `agente_nw/perfil/importador.py`: `importar`, conforme a seção 3, item 5.
7. `tests/test_importador.py`: rodar `importar` duas vezes com os mesmos 5 contatos fabricados do passo 4 — segunda rodada não duplica nenhum perfil; contato com nota gera uma linha em `fila_extracao` com `origem="notas_agenda"`; contato com marcador gera `perfil_tema` com `origem="importada"`; nenhum contato nasce `ativo`.
8. `cli.py`: os quatro comandos da seção 3, item 7. `ficha` imprime nome, cada campo guiado (ou "(vazio)" na ordem de `campos_faltando` para os que faltam), `ativo`/`gerar_agora`, e a lista de tags não confirmadas numerada a partir de 1 (tags já confirmadas aparecem à parte, sem número). `confirmar-tags --ids` valida que cada índice existe na lista atual antes de confirmar; índice fora do intervalo é reportado e ignorado, sem interromper os demais.
9. `tests/test_cli_agenda.py`: `ficha` de um telefone inexistente devolve mensagem clara, não traceback; `confirmar-tags --ids 1,99` (um válido, um fora do intervalo) confirma o primeiro e reporta o segundo como inválido; `confirmar-tags --todas` confirma todas as pendentes de um perfil de teste.
10. Rodar de verdade, nesta ordem: `agente_nw importar-agenda --fonte macos` (primeira vez concede a permissão pelo Terminal — conferir que aparece uma vez só); rodar de novo e confirmar (`SELECT COUNT(*) FROM perfil`) que o número de perfis não mudou; exportar o CSV real do Google Contatos e rodar `agente_nw importar-agenda --fonte csv --arquivo <caminho>`; escolher 10 contatos reais e, para cada um, `agente_nw ficha <telefone>`, `agente_nw ativar <telefone>` e `agente_nw confirmar-tags <telefone> --todas` (ou `--ids`, conforme fizer sentido para aquele contato).
11. Rodar `agente_nw processar-fila` (do brief 004) sobre as notas reais que entraram na fila, para confirmar a ponta a ponta: agenda → nota → tags sugeridas → `ficha` mostrando a tag nova → `confirmar-tags`.
12. Atualizar `docs/PLAN.md`: brief 005 concluído, semana 1 fechada; próximo é 007 (agrupamento e calibração), que passa a depender de pelo menos dois dias de coleta acumulada (brief 006) — não deste brief diretamente, mas o calendário do plano os encadeia; registrar quantos contatos reais foram importados e quantos ficaram ativos; registrar se a restrição de nota do macOS apareceu na prática.

---

## 7. Critérios de aceite

1. A agenda real do macOS importa sem duplicar ninguém; rodar `importar-agenda --fonte macos` duas vezes deixa o mesmo número de perfis.
2. O CSV real do Google Contatos importa; um contato presente nos dois leitores (mesmo telefone) não vira dois perfis.
3. Um contato com nota gera tag sugerida depois de `agente_nw processar-fila` — verificado de ponta a ponta no passo 11.
4. A permissão de acesso à agenda, pedida do Terminal, aparece uma vez e não volta a ser pedida na segunda execução.
5. Dez contatos reais ativados e com as tags confirmadas pelos três comandos de linha, sem nenhuma escrita direta no banco.
6. `scripts/verificar.sh` verde nos testes que não dependem da agenda real ou do Ollama (passos 1, 2, 4, 7, 9); os que dependem (passos 3, 10, 11) rodados manualmente com resultado relatado.

---

## 8. Riscos e como reverter

| Risco | Controle |
|---|---|
| macOS nega acesso à nota de todos os contatos, por restrição de entitlement do sistema | leitura isolada por campo (passo 3); resumo do comando informa quantas notas faltaram; sem isso, o resto da importação (nome, telefone, empresa, cargo) continua funcionando |
| Colunas do CSV do Google mudarem de nome numa exportação futura | casamento por prefixo, como o script original da proposta já previa; contato sem nome nem telefone nem e-mail é ignorado, não quebra o processo |
| Permissão negada por engano na primeira execução | mensagem de erro explícita apontando o caminho em Ajustes do Sistema para liberar manualmente |
| Número de telefone em formato incomum (ramal, DDI errado) normaliza para algo errado, criando duplicata | região padrão BR cobre o caso comum de Sidarta; se acontecer, o e-mail como segunda chave evita duplicata total; casos residuais ficam para revisão manual no console (brief 010) |
| Reverter | Todos os arquivos deste brief são novos, exceto a função nova em `queries/fila_extracao.py` (aditiva) e os quatro comandos novos em `cli.py` (voltam a `COMANDOS_RESERVADOS` removendo o registro) |

---

## 9. Relatório final obrigatório

Preencher o bloco da seção 8 de `AGENTS.md`, com o caminho do script de verificação para colar no terminal. Sem esse bloco preenchido, o brief não está concluído.
