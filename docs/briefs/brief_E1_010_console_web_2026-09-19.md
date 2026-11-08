# Brief E1-010 — Console web

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Depende de:** brief 009 (regra do conector), certificado. **Não bloqueia nem depende de 012/013** — roda em paralelo com os cinco dias de medição do brief 013.

---

## 1. Objetivo em uma frase

Três telas num navegador local (Contatos, Menu, Temas) que substituem os comandos de terminal do dia a dia — sem tocar no banco real enquanto a medição do brief 013 estiver correndo.

---

## 2. Contexto e o que já existe

Praticamente toda a lógica de negócio já existe e este brief só a expõe em HTML — não há regra nova de produto aqui, é encanamento. `Flask` já está em `pyproject.toml` desde o esqueleto inicial (brief 001), não precisa instalar nada novo.

Tudo que as três telas precisam já está construído: `perfis.listar_ativos`/`obter_por_telefone_ou_email`/`ativar`, `perfil_tema.listar_por_perfil`/`confirmar`, `campos_faltando`/`ORDEM_IMPACTO` (lacunas), `fila_extracao.inserir` (aceita `origem` livre — serve direto para "Adicionar texto", sem precisar de código novo), `extrator.processar_fila`, `cruzamento.cruzar_contato`, `assunto_contato.listar_do_dia` (já traz **todas** as linhas do dia, inclusive os `descartado`/`fora_do_dominio` — não precisa de consulta nova para o contador), `assunto_contato.marcar_usado`/`marcar_nao_serve`, `temas.listar`/`obter_por_id`/`gravar_embedding`.

Faltam só três consultas pequenas (seção 3) e a camada Flask em si.

---

## 3. Escopo

1. **`queries/perfis.py`** (aditivo): `listar_todos(conexao) -> list[Perfil]` — todos os contatos (não só ativos), ordenado por nome. A tela Contatos precisa listar quem ainda não foi ativado, não só quem já foi.
2. **`queries/temas.py`** (aditivo): `atualizar(conexao, tema_id, descricao, sinonimos) -> None`.
3. **`queries/perfil_tema.py`** (aditivo): `atualizar_nivel(conexao, perfil_id, tema_id, nivel) -> None`.
4. **`agente_nw/console/`** (novo pacote): `app.py` (fábrica Flask), `templates/` (Jinja2 puro), sem CSS separado além de um bloco `<style>` inline no `base.html` — sem build, sem framework de frontend, exatamente como o plano pede.
5. **`agente_nw/cli.py`**: comando `console --banco <caminho> [--porta 8765]`.

---

## 4. Decisões de segurança e isolamento, tomadas agora

**`--banco` é obrigatório, sem valor padrão.** Não existe um "se você não disser, uso o banco real" — o comando falha pedindo o caminho se `--banco` não for passado. É a garantia estrutural (não um lembrete escrito em algum lugar) de que ninguém aponta sem querer para `dados/agente.db` enquanto a medição do brief 013 corre. No dia da certificação, apontar deliberadamente para `dados/agente.db`.

**`app.run(host="127.0.0.1", port=porta)`, sem flag para mudar o host.** Não é configuração de aplicação, é o soquete só aceitando conexão local — o critério "recusa conexão de outro endereço" fica garantido pelo sistema operacional, não por uma checagem que alguém poderia esquecer de escrever.

**Log de chamadas LLM separado do log de produção.** O console, quando aberto contra uma cópia do banco (o normal, durante os 5 dias de medição), não pode escrever no mesmo `dados/logs/chamadas_llm.jsonl` que o `agente_nw certificar` do brief 013 vai ler para medir o critério de JSON válido — senão suas chamadas de teste no console contaminam a métrica real do produto rodando sozinho. O `ClienteOllama` do console usa `dados/logs/console_chamadas_llm.jsonl`, caminho diferente, sempre.

**Sem tela de login, sem CSRF token.** Ferramenta de um usuário único, na própria máquina, atrás de loopback — autenticação de verdade seria complexidade sem benefício real aqui. Documentar essa escolha, não escondê-la.

**Decisão sobre "sugestões pendentes" da tela Temas**: o plano não detalha o que isso significa exatamente. Interpretação adotada: são as linhas de `perfil_tema` do **usuário** (não de contatos) com `confirmado=False` — temas que a extração sugeriu para o próprio usuário (de notas ou textos que ele mesmo adicionou) e que ainda não viraram parte declarada do seu perfil de interesses. Confirmar uma sugestão pendente é o mesmo `perfil_tema.confirmar` já usado em outros lugares.

---

## 5. As três telas

### Contatos (`/contatos`)
Lista todos (não só ativos), nome, indicador de quantas lacunas de `ORDEM_IMPACTO` faltam (não os nomes dos campos, só a contagem — o detalhe fica na ficha), se está ativo. Clicar leva à ficha (`/contatos/<id>`).

### Ficha (`/contatos/<id>`)
Campos e lacunas nomeadas (reaproveitar exatamente `campos_faltando`), tags confirmadas e não confirmadas com peso e origem, formulário de confirmação em lote (checkboxes, um `POST` para todas as marcadas de uma vez — reaproveita `perfil_tema.confirmar`), botão "ativar" (se ainda não ativo), campo de texto livre com botão "adicionar" (`fila_extracao.inserir(..., origem="manual", ...)`), botão "gerar menu agora" (chama `cruzamento.cruzar_contato` só para este contato, na hora, e redireciona para `/menu/<id>` do dia de hoje).

### Menu (`/menu` e `/menu/<perfil_id>`)
`/menu` lista os contatos com menu gerado hoje. `/menu/<perfil_id>`: duas faixas (Conectores, Viáveis com esforço), cada item com `por_que`; nos viáveis, o cartão (`resumo_cartao`) dentro de um `<details open>` — expandido por padrão, mas o usuário pode fechar clicando, sem precisar de nenhum JavaScript para isso. Cada item tem "usei" e "não serve" com os cinco motivos (mesmo mapeamento fixo do brief 011), cada botão um formulário próprio que reaproveita `marcar_usado`/`marcar_nao_serve`. Contador de "fora do domínio" (itens com `status="descartado"` do dia) com uma lista que só aparece ao clicar — de novo, `<details>`, sem JavaScript.

### Temas (`/temas`)
Lista dos temas do usuário: nome, descrição (editável em linguagem natural, formulário simples), sinônimos (lista editável), nível (seletor domínio/interesse/curiosidade, grava via `perfil_tema.atualizar_nivel`). Seção separada "Sugestões pendentes" conforme a decisão da seção 4.

---

## 6. Fora de escopo, com justificativa

- **Autenticação de verdade, HTTPS, hardening de produção.** Ferramenta pessoal, local, atrás de loopback — fora de propósito para o MVP.
- **JavaScript de qualquer tipo.** O plano pede "sem framework de frontend, sem build" — formulários HTML puros e `<details>` cobrem tudo que as três telas precisam sem exceção.
- **Apontar automaticamente para o banco real no dia da certificação.** É uma ação deliberada sua (`--banco dados/agente.db`), não um comportamento automático do sistema.

---

## 7. Passos de execução

1. `queries/perfis.py`: `listar_todos`.
2. `queries/temas.py`: `atualizar` (regravar a descrição/sinônimos e reembeddar, mesmo padrão do conserto do brief 008).
3. `queries/perfil_tema.py`: `atualizar_nivel`.
4. `tests/test_perfis_listar_todos.py`, `tests/test_temas_atualizar.py`, `tests/test_perfil_tema_nivel.py`.
5. `agente_nw/console/app.py`: fábrica `criar_app(caminho_banco, caminho_log_llm) -> Flask`, todas as rotas da seção 5.
6. Templates Jinja2: `base.html` (com o `<style>` inline), `contatos.html`, `ficha.html`, `menu.html`, `temas.html`.
7. `cli.py`: comando `console --banco --porta`.
8. `tests/test_console_contatos.py`, `tests/test_console_menu.py`, `tests/test_console_temas.py` — usando o cliente de teste do Flask (`app.test_client()`) contra um banco de teste isolado, sem subir servidor de verdade.
9. Rodar de verdade: `agente_nw copiar-banco` para uma cópia local, `agente_nw console --banco <cópia>`, abrir `http://127.0.0.1:8765` no navegador e passar pelo fluxo completo pelo menos uma vez — ativar um contato, confirmar tags, gerar menu, marcar usei/não serve, editar um tema — confirmando visualmente que nenhuma etapa precisa do terminal.
10. Atualizar `docs/PLAN.md`.

---

## 8. Critérios de aceite

1. O ciclo inteiro — marcar tags, ativar contato, ler menu, marcar usei/não serve — acontece no navegador, sem editar arquivo nem rodar comando à mão (confirmado no passo 9).
2. `--banco` sem valor: comando falha com mensagem clara, não inicia com um caminho padrão silencioso.
3. Rodando com `host="127.0.0.1"`: tentativa de conexão por outro endereço não chega à aplicação (garantido pelo soquete, não por lógica de aplicação — confirmar que não há flag `--host` no comando).
4. Nenhuma escrita no banco real durante os dias de medição do brief 013 — verificado pelo relatório do 013 contra o log do ciclo, não por este brief isoladamente.
5. `scripts/verificar.sh` verde.

---

## 9. Riscos e como reverter

| Risco | Controle |
|---|---|
| Esquecer e apontar o console para `dados/agente.db` durante a medição | `--banco` obrigatório reduz o risco, mas não elimina esquecimento — por isso o critério 4 é verificado de fora, pelo brief 013, não confiado só à disciplina do momento |
| Console e ciclo automático escrevendo ao mesmo tempo na cópia, gerando `SQLITE_BUSY` | banco já usa WAL (brief 002) — concorrência entre o console (numa cópia) e o ciclo (no banco real) não se toca, são arquivos diferentes; risco só existiria se apontados para o mesmo arquivo, o que a regra do `--banco` obrigatório já desestimula |
| Reverter | Pacote `agente_nw/console/` inteiro é novo e pode ser apagado sem afetar o resto; as três funções aditivas em `queries/` não tocam nenhuma função existente |

---

## 10. Relatório final obrigatório

Preencher o bloco da seção 8 de `AGENTS.md`, com o caminho do script de verificação para colar no terminal. Sem esse bloco preenchido, o brief não está concluído.
