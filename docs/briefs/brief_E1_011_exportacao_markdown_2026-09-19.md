# Brief E1-011 — Exportação em Markdown e leitura de marcações

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Depende de:** brief 009 (regra do conector), certificado.

---

## 1. Objetivo em uma frase

Gerar todo dia um `menu_AAAA-MM-DD.md` que abre limpo no celular (Obsidian ou app do Drive), e ler de volta as marcações de "usei"/"não serve" que você fizer nele.

---

## 2. Contexto e o que já existe

Os nomes de comando já estão reservados em `agente_nw/cli.py` (`COMANDOS_RESERVADOS`): `exportar-menu` e `ler-marcacoes`, ambos apontando para este brief. `config/local.exemplo.yaml` já tem `pasta_saida: saidas` — falta só a função de fábrica em `config/container.py` que resolve esse caminho (mesmo padrão de `caminho_pasta_backups`). O pacote `agente_nw/nucleo/saidas/` já existe, vazio, esperando por este código — é onde ele vai.

O formato exato do arquivo e do parser de marcação já foi desenhado e está registrado em `docs/agente_nw_proposta_comite_v5_2026-09-17.md`, seção 7.4 — vou seguir esse desenho, só endurecendo o tratamento de erro e adaptando às convenções do projeto (Pydantic, `queries/`, testes). Reproduzo o formato exato na seção 4.

`assunto_contato.listar_do_dia(conexao, perfil_id, data)` já existe (brief 009), devolve ordenado por `score` decrescente. `assuntos.obter_por_id` e `perfis.obter_por_id` já existem para buscar título/cartão/nome.

---

## 3. Escopo

1. **`config/container.py`** (aditivo): `caminho_pasta_saida() -> Path`, mesmo padrão de `caminho_pasta_backups`.
2. **`agente_nw/nucleo/database/queries/assunto_contato.py`** (aditivo): `marcar_usado(conexao, ac_id) -> bool` e `marcar_nao_serve(conexao, ac_id, motivo) -> bool` — ambos só afetam a linha se `status='novo'` (`UPDATE ... WHERE id = ? AND status = 'novo'`), devolvem `True` só se de fato mudaram uma linha. É a guarda que impede marcação duplicada ou tardia de sobrescrever um resultado já resolvido.
3. **`agente_nw/nucleo/modelos/marcacao.py`** (novo): `Marcacao` — `{ac_id: int, resultado: Literal["usado", "nao_serve"], motivo: str | None}`, `frozen=True`.
4. **`agente_nw/nucleo/saidas/markdown.py`** (novo): `gerar(conexao, perfis_ativos, data) -> str` (monta o texto do arquivo) e `ler_marcacoes(texto) -> tuple[list[Marcacao], list[str]]` (marcações válidas + avisos de formato, nunca uma exceção que jogue tudo fora).
5. **`agente_nw/cli.py`**: tirar `exportar-menu` e `ler-marcacoes` de `COMANDOS_RESERVADOS`, implementar os dois comandos de verdade, cada um com `--data AAAA-MM-DD` opcional (default: hoje).

---

## 4. O formato, exatamente como já está na proposta ao comitê

```markdown
## Ricardo  <!-- perfil:14 -->
### Conectores
#### Crédito consignado para autônomos entra em vigor  <!-- ac:812 -->
Por quê: ele trabalha com crédito e vocês dois lidam com autônomos.
- [ ] usei
- [ ] não serve → motivo: ( ) não interessa a ele ( ) velho ( ) raso ( ) não dá conversa ( ) eu não domino
### Viáveis com esforço
#### Novo terminal de cabotagem em Santos  <!-- ac:799 -->
Por quê: é o setor dele; seu apoio é a parte tributária do assunto — leia o cartão antes.
Cartão: [resumo_cartao do assunto, as três linhas do brief 008]
- [ ] usei
- [ ] não serve → motivo: ( ) não interessa a ele ( ) velho ( ) raso ( ) não dá conversa ( ) eu não domino
```

**Decisão tomada, não estava no desenho original**: o cartão (resumo de 3 linhas do brief 008) entra só nos itens de "Viáveis com esforço", não nos "Conectores" — nos conectores você já domina o assunto do contato, o cartão só ocupa espaço; nos viáveis é exatamente onde ele cumpre o papel de "leia antes de puxar assunto".

**Nome do contato**: `apelido` se existir, senão `nome` — mesma regra já usada no `ficha` do brief 005.

**Contatos sem sugestão naquele dia** (sem tema confirmado, ou todos os candidatos deram `fora_do_dominio`) não geram bloco nenhum no arquivo — o Markdown é o documento que você lê para agir, não um relatório de auditoria; isso fica para o console (brief 010).

**Motivos de "não serve"**, mapeamento fixo (mesmos cinco da proposta ao comitê):

| Texto no arquivo | Gravado em `assunto_contato.motivo` |
|---|---|
| não interessa a ele | `nao_interessa` |
| velho | `velho` |
| raso | `raso` |
| não dá conversa | `nao_da_conversa` |
| eu não domino | `nao_domino` |

---

## 5. `gerar` — regras exatas

Para cada perfil ativo (`perfis.listar_ativos`), na ordem: buscar `assunto_contato.listar_do_dia(conexao, perfil.id, data)`, filtrar só `status == "novo"` (um `sem_assunto`/`fora_do_dominio` nunca chega a existir com `status="novo"` fora do escopo — os `fora_do_dominio` já nascem `descartado`, então o filtro é redundante mas explícito). Se a lista filtrada for vazia, pular o perfil inteiro (sem bloco). Senão: montar o bloco `## <nome> <!-- perfil:ID -->`, depois `### Conectores` com os itens de `tipo="conector"` (na ordem que já vêm, por `score`), depois `### Viáveis com esforço` com os de `tipo="viavel_com_esforco"` — omitir a seção inteira (nem o `###`) se não houver nenhum item daquele tipo para aquele contato.

Cada item: `#### <titulo_gerado do assunto> <!-- ac:<id do assunto_contato> -->`, depois `Por quê: <por_que>` (se `por_que` for `None` — caso de falha do brief 009 registrado — escrever `Por quê: (não gerado)` em vez de quebrar o arquivo), depois `Cartão: <resumo_cartao>` só se for viável, depois as duas linhas de checkbox fixas.

Se, no fim, nenhum perfil gerou bloco nenhum: o arquivo ainda é criado, só com um comentário `<!-- nenhuma sugestão hoje -->` — nunca a ausência do arquivo (o comando `ler-marcacoes` do dia seguinte precisa de um arquivo previsível para checar, mesmo vazio).

---

## 6. `ler_marcacoes` — regras exatas, "erro de formato gera aviso, não perda"

Percorre o texto bloco por `<!-- ac:(\d+) -->` (mesma regex da proposta). Para cada bloco: se tiver `- [x] usei` (case-insensitive), é `Marcacao(ac_id, "usado", None)`. Senão, se tiver `- [x] não serve`, procura qual dos cinco `( x )` está marcado — **exatamente um marcado**: se nenhum estiver marcado, ou mais de um estiver, é um aviso ("bloco ac:<id> marcado como não serve sem motivo claro"), a marcação inteira daquele bloco é descartada (não grava nada, não trava os outros blocos). Se nenhum dos dois estiver marcado (nem "usei" nem "não serve"), não é erro — é só um item ainda não decidido, ignorado silenciosamente, sem aviso (é o estado normal de "ainda não vi").

`ler-marcacoes` (comando): lê o arquivo do dia, roda `ler_marcacoes`, aplica cada `Marcacao` via `marcar_usado`/`marcar_nao_serve`; se a função de gravação devolver `False` (id não existe, ou já não estava mais `status='novo'`), isso também vira aviso ("ac:<id> não encontrado ou já resolvido"), não erro fatal. No fim, imprime quantas marcações foram aplicadas e lista os avisos, se houver — nunca lança exceção por causa de conteúdo malformado do arquivo (só por arquivo ausente, isso sim é erro real).

---

## 7. Fora de escopo, com justificativa

- **Console web (tela Menu com "usei"/"não serve" clicável).** É o brief 010 — o Markdown é o canal principal enquanto o console não existe, e continua sendo o canal do celular depois.
- **Sincronizar com a pasta do Drive de verdade.** A proposta ao comitê já resolveu isso como "não precisa de script novo — `pasta_saida` vira a pasta do Drive para computador quando configurada assim". Não há código a escrever aqui; é config do sistema operacional do computador, fora do repositório.
- **`calibrar-conector` (limiares 0,55/0,8 com dado real).** Combinado no brief 009: só faz sentido depois de existir histórico real de `usado`/`nao_serve` — este brief é o que começa a gerar esse histórico, não o que o consome.

---

## 8. Passos de execução

1. `config/container.py`: `caminho_pasta_saida`.
2. `queries/assunto_contato.py`: `marcar_usado`, `marcar_nao_serve`.
3. `tests/test_assunto_contato_marcacao.py`: marcar um `id` já `usado` de novo não muda nada e devolve `False`; marcar um `id` inexistente devolve `False`; marcar um `novo` de verdade devolve `True` e persiste.
4. `modelos/marcacao.py`.
5. `nucleo/saidas/markdown.py`: `gerar` e `ler_marcacoes`, conforme seções 5 e 6.
6. `tests/test_markdown_gerar.py`: contato sem sugestão não gera bloco; conector não leva `Cartão:`; viável leva; `por_que=None` não quebra, vira "(não gerado)"; nenhum perfil com sugestão ainda assim produz arquivo com o comentário de aviso.
7. `tests/test_markdown_ler.py`: "usei" marcado reconhecido; "não serve" com motivo único reconhecido e mapeado certo (testar os cinco); "não serve" sem nenhum motivo marcado vira aviso, não grava; "não serve" com dois motivos marcados vira aviso, não grava; bloco sem nenhuma marcação é ignorado sem aviso; texto com um bloco corrompido no meio não impede os outros blocos de serem lidos.
8. `cli.py`: remover as duas entradas de `COMANDOS_RESERVADOS`, implementar `exportar-menu --data` e `ler-marcacoes --data`.
9. `tests/test_cli_markdown.py`: `exportar-menu` sem `--data` usa a data de hoje; roda de ponta a ponta contra um banco de teste com um `assunto_contato` fake.
10. Rodar de verdade: `agente_nw exportar-menu` contra o estado real de hoje (mesmo que a maioria dos contatos ainda não tenha tema confirmado — o arquivo vai sair majoritariamente vazio, e está certo que saia assim); abrir o `.md` gerado e conferir visualmente que o formato bate com a seção 4; se houver pelo menos um `assunto_contato` de teste (ex.: o fixture "Ricardo Teste Brief004", já que não vamos fabricar dado em contato real — mesma decisão do brief 009), marcar manualmente uma caixa nele e rodar `agente_nw ler-marcacoes` para confirmar que a marcação chega ao banco com o motivo certo.
11. Atualizar `docs/PLAN.md`: brief 011 concluído; registrar que o canal de marcação real (você usando o arquivo de verdade, todo dia) é o que vai alimentar a calibração adiada do brief 009.

---

## 9. Critérios de aceite

1. Arquivo gerado é Markdown válido, sem nenhuma sintaxe que quebre a leitura em Obsidian ou no app do Drive (títulos `##`/`###`/`####`, comentários HTML, checkboxes `- [ ]` padrão — nenhum desses recursos é exótico, mas confirmar visualmente na execução real do passo 10).
2. Marcação feita manualmente no arquivo chega ao banco com o `motivo` certo (testado com o fixture, já que não há contato real com sugestão ainda).
3. Arquivo com bloco de formato errado gera aviso listado, nunca perde as marcações válidas dos outros blocos do mesmo arquivo.
4. `scripts/verificar.sh` verde.

---

## 10. Riscos e como reverter

| Risco | Controle |
|---|---|
| Nenhum contato real com tema confirmado ainda torna o teste do passo 10 dependente do fixture de teste | aceito e documentado, mesma situação do brief 009 — critério 2 provado por teste + fixture, não por contato real, até existir um |
| Emoji ou acento quebrando o parsing do checkbox em algum app de leitura | usar só ASCII nos marcadores de checkbox e nos parênteses de motivo, exatamente como na proposta ao comitê (já testada mentalmente contra Obsidian/Drive por você) |
| Reverter | Toda a mudança está em arquivos novos, mais duas funções aditivas em `queries/assunto_contato.py` e duas linhas removidas de `COMANDOS_RESERVADOS` |

---

## 11. Relatório final obrigatório

Preencher o bloco da seção 8 de `AGENTS.md`, com o caminho do script de verificação para colar no terminal. Sem esse bloco preenchido, o brief não está concluído.
