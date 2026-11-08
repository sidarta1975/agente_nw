# Brief 036 — Extração do pedido em texto livre

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Base:** `main` em `a874326`.
**Plano:** v3.1 (2026-10-11), primeiro brief da sequência. Não depende de brief aberto.
**Data:** 2026-10-11

---

## 1. Objetivo em uma frase

O usuário escreve uma frase do seu jeito — *"Almoço quinta com o Marcos, sócio de escritório tributarista em SP, faz dois anos que não nos falamos, quero retomar sem parecer que estou pedindo algo"* — e o sistema, sem nenhum formulário, entende quem é a pessoa, o que o usuário quer e como, reconhece ou cria o contato, decide o que procurar na notícia e deixa tudo pronto para os briefs seguintes (localização do perfil, redação).

---

## 2. O que já existe e é reaproveitado

- `ContextoConsulta` (`nucleo/modelos/contexto_consulta.py`): `assunto`, `meio`, `objetivo`, `interessa`, `evitar`, `livre`. Hoje é preenchido pelo formulário de Preparar e pelo comando `preparar`. Passa a ser **produzido pela IA** a partir do texto; o modelo não muda, ganha campos (3.2).
- `ClienteOllama.gerar_json(tarefa, prompt, esquema)` (`nucleo/llm.py`): uma tentativa com a temperatura da tarefa, uma nova tentativa, fila de revisão em caso de JSON inválido. É o único caminho de chamada ao modelo; a tarefa nova usa esse caminho.
- `perfis.inserir_novo_contato`, `perfis.obter_por_telefone_ou_email`, `perfis.listar_todos`, `perfis.upsert_usuario` (`queries/perfis.py`); `perfil.tipo IN ('usuario','contato')`.
- `google_news.gerar_consultas_da_consulta(contexto, termos_contato)` (brief 034) e `consulta.preparar(...)` (briefs 018/034/035), que já recebem um `ContextoConsulta` e fazem coleta, seleção e cruzamento.
- Padrão de prompt em `nucleo/prompts/qualificar.py`: `construir_prompt(...)`, `ESQUEMA`, exemplo resolvido com cenário deliberadamente distante de qualquer entrada real.
- `verificar-ambiente` deriva os modelos obrigatórios do perfil ativo (brief 031); uma tarefa nova no `llm_routing.yaml` entra automaticamente.

---

## 3. Decisões

**3.1. Uma tarefa nova de LLM: `extrair_pedido`.** Declarada nos dois perfis de `config/llm_routing.yaml` (o validador do brief 031 exige): `air16` → `qwen3:4b`, `num_ctx: 4096`, `temperature: 0.1`; `pro48` → `qwen2.5:14b`, `num_ctx: 8192`, `temperature: 0.1`. `format: json`, `think: false`.

**3.2. O que a IA extrai (schema JSON, modelo `PedidoExtraido` em `nucleo/modelos/pedido.py`).**

| Campo | Tipo | Regra |
|---|---|---|
| `pessoa_nome` | `str` | nome como o usuário escreveu; `""` se a frase não menciona pessoa (ex.: "me dá assunto de IA para o pessoal da Parceira" → grupo, não pessoa) |
| `pessoa_pistas` | `dict[str, str]` | só chaves presentes na frase: `profissao`, `empresa`, `cidade`, `vinculo` (como o usuário conhece a pessoa), `tempo_sem_contato`, `link_rede_social` |
| `objetivo` | `Literal["retomar","agradecer","pedir","manter","apresentar","responder","outro"]` | |
| `objetivo_texto` | `str` | o objetivo nas palavras do usuário |
| `meio` | `MeioContato` (já existe) | padrão `"whatsapp"` se não dito; "almoço", "encontro", "reunião" → `"pessoalmente"` |
| `registro` | `Literal["proximo","cordial","formal"]` | inferido do vínculo e do tom da frase; padrão `"cordial"` |
| `assunto_principal` | `str` | o que a conversa deve girar, em até dez palavras; se o usuário não disse, a IA deduz da profissão/vínculo |
| `interessa` | `list[str]` | até 5 termos que o usuário quer |
| `evitar` | `list[str]` | termos que o usuário não quer |
| `termos_busca` | `list[str]` | 3 a 6 termos de busca de notícia, **gerados pela IA** a partir de profissão, empresa, assunto e atualidade provável (ex.: "sócio de escritório tributarista" → "reforma tributária", "Carf", "transação tributária") |
| `continuacao` | `bool` | verdadeiro quando a frase indica que a conversa já começou ("ele respondeu que…", "de novo") — o brief 041 consome; aqui só é extraído e gravado |
| `confianca` | `float` 0–1 | autoavaliação da extração; abaixo de 0,5 o resultado é mostrado com aviso |

Validações Pydantic: listas sem duplicatas (comparação sem acento e sem caixa); `termos_busca` entre 1 e 6 itens; `pessoa_nome` sem título ("Dr.", "Sr.") — o modelo recebe a instrução, o validador limpa se escapar.

**3.3. Prompt (`nucleo/prompts/extrair_pedido.py`).** Instruções em português; a frase do usuário entre marcadores; a lista de contatos já conhecidos (nome, empresa, cargo — até 50, os mais recentes) para o modelo reconhecer "o Marcos" como alguém que já existe; um exemplo resolvido com cenário distante de qualquer teste (padrão do projeto). Saída estritamente o JSON do schema. Sem raciocínio no texto.

**3.4. Reconhecimento ou criação do contato (`nucleo/pedido.py`, função `resolver_contato`).** Ordem:
1. Se `pessoa_nome` vazio → sem contato (pedido "de grupo"); o resultado segue sem perfil, para o brief 038 redigir sem contato.
2. Busca por nome normalizado (sem acento, sem caixa, prefixo de primeiro nome + sobrenome quando houver) em `perfil` com `tipo='contato'`. Um resultado → usa. Mais de um → escolhe o que casa mais pistas (`empresa`, `cidade`, `cargo` ~ `profissao`); se empate, o de `atualizado_em` mais recente, e o resultado marca `contato_ambiguo=True` com a lista dos candidatos (o brief 037 e a tela do 039 usam isso para perguntar). Nenhum → cria com `inserir_novo_contato`, preenchendo `empresa`, `cargo`, `cidade` e `notas` (vínculo e tempo sem contato) a partir das pistas; telefone e e-mail ficam vazios — o contato existe sem eles.
3. Pistas novas sobre contato já existente (empresa, cargo, cidade vazios no banco e presentes na frase) são gravadas; nunca sobrescrevem valor já preenchido.

**3.5. Perfil do usuário.** Se `perfis.obter_usuario` devolver `None`, criar com `upsert_usuario(nome=<usuário do sistema operacional>, …)` — `getpass.getuser()` com inicial maiúscula. Sem tema. O brief 040 refina; aqui basta existir, porque o motor exige.

**3.6. Do pedido ao contexto.** `pedido.para_contexto(pedido: PedidoExtraido) -> ContextoConsulta`: `assunto = assunto_principal`, `meio`, `objetivo = objetivo_texto`, `interessa`, `evitar`, `livre = frase original`. `ContextoConsulta` ganha dois campos opcionais, `registro: str | None = None` e `termos_busca: list[str] = []`, que o brief 034 passa a usar: `gerar_consultas_da_consulta` acrescenta uma consulta por termo de `termos_busca` (até 6), antes das do contato.

**3.7. Gravação.** Tabela nova `pedido` (migração `007_pedido.sql`): `id`, `perfil_id NULL`, `texto`, `extraido_json`, `confianca`, `contato_criado INTEGER`, `contato_ambiguo INTEGER`, `criado_em`. Todo pedido é gravado antes de qualquer outra etapa — é o histórico bruto que o brief 041 lê.

**3.8. Comando `agente_nw pedir "<frase>"`.** Faz 3.3 → 3.4 → 3.5 → 3.7 e imprime, em texto corrido legível:
```
Pessoa: Marcos (contato novo) — sócio, escritório tributarista, São Paulo; vínculo: conhecido profissional; sem contato há ~2 anos
Objetivo: retomar — "retomar sem parecer que estou pedindo algo"
Meio: pessoalmente · Registro: cordial
Assunto principal: reforma tributária e cenário dos escritórios
Interessa: — · Evitar: —
Buscar notícia sobre: reforma tributária; Carf; transação tributária; escritórios de advocacia tributária
Confiança: 0,82
```
Com `--preparar`, encadeia `consulta.preparar(...)` com o contexto produzido (sem leitura de rede social, até o brief 037) e imprime o menu como `preparar` faz hoje — é a ponte até o brief 038 substituir o menu pela redação. Com `--json`, imprime o `PedidoExtraido` bruto.

**3.9. O comando `preparar` e o formulário de Preparar continuam existindo** neste brief, intocados. Saem do caminho principal no brief 039.

**3.10. Sem confirmação interativa neste brief.** "É esta pessoa?" é do brief 037. Aqui, ambiguidade é só registrada (`contato_ambiguo`) e impressa como aviso: "Encontrei 2 contatos chamados Marcos; usei Marcos Silva (XYZ Advogados). Para trocar: `agente_nw pedir --contato <id> "<frase>"`."

---

## 4. Escopo (arquivos)

1. `config/llm_routing.yaml`: tarefa `extrair_pedido` nos dois perfis.
2. `nucleo/modelos/pedido.py`: `PedidoExtraido`, `ResultadoPedido` (pedido + perfil resolvido + flags + candidatos).
3. `nucleo/modelos/contexto_consulta.py`: campos `registro` e `termos_busca` (opcionais, compatíveis com tudo que já cria `ContextoConsulta`).
4. `nucleo/prompts/extrair_pedido.py`: `construir_prompt(frase, contatos_conhecidos)`, `ESQUEMA`.
5. `nucleo/pedido.py`: `extrair(cliente_llm, conexao, frase) -> PedidoExtraido`; `resolver_contato(conexao, pedido, agora, contato_id_forcado=None)`; `garantir_usuario(conexao, agora)`; `para_contexto(pedido)`; `registrar(conexao, ...)`; `processar(cliente_llm, conexao, frase, agora, contato_id_forcado=None) -> ResultadoPedido` que encadeia tudo.
6. `nucleo/database/queries/pedidos.py`: `inserir`, `listar_recentes(limite)`, `obter_por_id`.
7. `nucleo/database/queries/perfis.py`: `buscar_por_nome(conexao, nome) -> list[Perfil]` (normalização sem acento/caixa; `tipo='contato'`); `preencher_lacunas(conexao, perfil_id, campos: dict)` — só grava onde está vazio.
8. `coleta/rss/google_news.py`: `gerar_consultas_da_consulta` usa `contexto.termos_busca`.
9. `scripts/migracoes/007_pedido.sql`.
10. `cli.py`: comando `pedir` com `--preparar`, `--json`, `--contato <id>`.
11. `AGENTS.md`, seção 7, reescrita:

   > O usuário escreve um pedido em texto livre sobre uma pessoa ou um grupo e um objetivo. O sistema extrai quem, o quê, como e em que registro; reconhece ou cria o contato; decide sozinho o que buscar na notícia; localiza a pessoa nas redes do usuário com confirmação quando há dúvida; lê o que estiver disponível; seleciona assuntos e **redige o conteúdo** (ganchos e mensagens prontas no registro da relação). Nenhum cadastro é pré-requisito: contato, perfil do usuário, temas, tags e fatos são criados e mantidos pelo sistema; o usuário corrige em texto. Não existe envio de mensagem. Nunca rodam sozinhos: git, leitura de rede social, alteração de ficha de contato.

   E, na seção 3, acrescentar `extrair_pedido` à lista de tarefas de LLM.

---

## 5. Testes

- `tests/test_pedido_extrair.py` (cliente LLM falso devolvendo JSON controlado): schema valida; listas deduplicadas; `termos_busca` fora de 1–6 rejeitado; `pessoa_nome` com "Dr." limpo pelo validador.
- `tests/test_pedido_resolver_contato.py`: nome inexistente cria contato com empresa/cargo/cidade das pistas; nome existente único reaproveita e preenche só lacunas; dois homônimos → escolhe pelo casamento de pistas e marca `contato_ambiguo` com os dois candidatos; `contato_id_forcado` prevalece; `pessoa_nome` vazio → `perfil is None` sem erro.
- `tests/test_pedido_usuario.py`: banco sem usuário → `garantir_usuario` cria com o nome do sistema (monkeypatch em `getpass.getuser`).
- `tests/test_pedido_para_contexto.py`: campos mapeados; `livre` guarda a frase original; `termos_busca` chega ao `gerar_consultas_da_consulta` e vira feeds antes dos do contato.
- `tests/test_migracao_007.py`: tabela `pedido` existe.
- `tests/test_cli_pedir.py`: saída do comando contém "Pessoa:", "Objetivo:", "Buscar notícia sobre:"; `--json` imprime JSON válido; aviso de ambiguidade quando há homônimos.
- `tests/test_prompt_extrair_pedido.py`: o prompt contém a frase, os contatos conhecidos e o exemplo; o exemplo não contém nenhum nome usado nos testes.

---

## 6. Fora de escopo

- Confirmação "é esta pessoa?" e localização nas redes (brief 037).
- Redação de ganchos e mensagens (brief 038).
- Tela única e correção em texto (brief 039).
- Temas do usuário inferidos (brief 040).
- Continuação de conversa (brief 041): aqui `continuacao` é só extraído e gravado.
- Remoção de `preparar`, do formulário de Preparar ou de `importar-temas`.

---

## 7. Passos de execução

1. Migração 007 e `queries/pedidos.py`.
2. `llm_routing.yaml` (dois perfis) e `AGENTS.md`.
3. Modelos (`pedido.py`, campos novos em `contexto_consulta.py`).
4. Prompt `extrair_pedido`.
5. `queries/perfis.py`: `buscar_por_nome`, `preencher_lacunas`.
6. `nucleo/pedido.py`.
7. `google_news.py`: `termos_busca`.
8. `cli.py`: `pedir`.
9. Testes da seção 5.
10. Entregar lista para `git add` e mensagem sugerida: `feat(pedido): extração do pedido em texto livre, contato reconhecido ou criado pela IA, termos de busca gerados (brief 036)`.

`scripts/verificar.sh`, o teste real da seção 8 e o commit são passos de Sidarta, no terminal dele.

---

## 8. Critérios de aceite (teste real de Sidarta, no Pro)

Banco recém-criado (`agente_nw migrar`), sem usuário, sem contato, sem tema. Dez frases reais, escritas sem pensar em formulário, cobrindo: pessoa nova; pessoa já citada em frase anterior; homônimos (duas frases sobre pessoas diferentes com o mesmo primeiro nome e pistas distintas); frase de grupo sem pessoa; frase com "evitar"; frase presencial e frase de WhatsApp; frase com link de LinkedIn colado.

1. Em pelo menos 8 das 10, a saída de `agente_nw pedir` descreve corretamente pessoa, objetivo, meio e assunto principal, e os termos de busca fazem sentido para a profissão/assunto.
2. A pessoa citada pela segunda vez é reconhecida (não cria duplicata); os homônimos são distinguidos pelas pistas ou geram o aviso de ambiguidade.
3. O usuário foi criado sozinho; nenhum formulário foi aberto.
4. `agente_nw pedir --preparar "<frase>"` chega ao menu com pelo menos um item cujo "por quê" cita o pedido — mesmo com usuário sem tema e contato sem tag (brief 034 funcionando a partir do texto livre).
