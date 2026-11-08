# Doc 076 — Com chave cadastrada, o programa usa a API; sem chave, continua no Ollama

**Brief:** `docs/briefs/brief_076_selecao_provedor_por_chave_2026-11-03.md`
**Data:** 2026-11-03

Terceiro e último do conjunto `ia_api` (074 `9598a8e`, 075 `8a5d7eb`).

## O que foi feito

### 1. Bloco `ia_api` em `config/local.yaml` (opcional)

`agente_nw/nucleo/modelos/configuracao.py` ganhou `ProvedorApi` (`chave`, `modelo`) e
`ConfiguracaoIaApi` (`provedor` + os três sub-blocos opcionais), os dois `frozen=True` como todo o
arquivo, e `Configuracao` ganhou `ia_api: ConfiguracaoIaApi = Field(default_factory=ConfiguracaoIaApi)`.
Com o bloco ausente — o caso do `local.exemplo.yaml` e de todo instalador existente — vira o padrão
`provedor: "auto"` com os três `None`, e a seleção cai no Ollama. Há teste que valida literalmente o
`config/local.exemplo.yaml` do disco contra `Configuracao` para garantir isso
(`test_configuracao_sem_ia_api_no_yaml_vira_o_padrao_de_ollama`).

`config/local.exemplo.yaml` documenta o bloco inteiro comentado, com o aviso de que embeddings
continuam no Ollama local e por isso o Ollama ainda precisa estar de pé.

### 2. `selecionar_cliente_llm`, o único lugar que decide o provedor

Fica em `config/container.py` (uma das duas opções que o item 3.3 do brief deixou ao executor;
escolhida porque `container.py` já é o arquivo-alvo deste brief, e `nucleo/llm.py` não é). Faz os
quatro passos do brief, nessa ordem: constrói sempre um `ClienteOllama` (é o cliente de embeddings);
decide o provedor; devolve o próprio `ClienteOllama` se a decisão for `ollama`; senão constrói o
cliente de API passando aquele `ClienteOllama` como `cliente_embeddings`.

Prioridade do `provedor: auto`: Anthropic, Gemini, OpenAI — a primeira com `chave` **e** `modelo`
preenchidos (chave só com espaços não conta, tem teste). `provedor` explícito vence a prioridade; sem o
sub-bloco correspondente preenchido, `ValueError` citando o nome do provedor e o arquivo, na construção
do cliente, não na primeira chamada.

Os quatro lugares que construíam `ClienteOllama` direto agora chamam essa função: `container.llm()` e
as três de `agente_nw/console/app.py` (`_cliente_llm`, `fabrica_llm` dentro de `_dependencias`, e a do
`_processar_whatsapp_em_fundo`). Há teste lendo os dois arquivos para garantir que não sobrou nenhuma
construção direta fora da própria função.

### 3. `AGENTS.md` §3 e `docs/ARQUITETURA.md` §8

Acrescentada no `AGENTS.md` §3, depois da linha do `think: false`, a regra do item 3.4 — com os dois
fatos que o brief exige preservados (API opcional e só com chave; embeddings sempre locais) e mais dois
que vieram dos itens 3.3 e 3.6: só `selecionar_cliente_llm` decide o provedor, e com chave cadastrada o
texto dos prompts sai da máquina de Sidarta para o servidor do provedor. Nenhuma seção nova: é
acréscimo dentro da §3, como o brief determina (a §13 segue livre).

`docs/ARQUITETURA.md` §8 ganhou um parágrafo novo antes de "Servidor Ollama", descrevendo a base comum
do 074, os três clientes do 075, o mecanismo de seleção, a ordem de prioridade e a invariante dos
embeddings. Nada do que já estava escrito sobre Ollama e perfis foi reescrito.

## Dois arquivos fora da lista de Arquivos-alvo, e por quê

O brief listou os alvos supondo que `console/app.py` já alcançava a configuração e que o resto do
produto era indiferente ao provedor. As duas coisas estavam a um arquivo de distância, e sem elas o
brief não tem como ficar verde nem funcionar:

**`agente_nw/cli.py` (uma linha).** As três construções de cliente em `app.py` precisam do bloco
`ia_api`, e `app.py` não tem acesso a ele: `criar_app` recebe `roteamento`, `limiares` e `ollama_url`
como parâmetros, de quem o chama. `criar_app` ganhou `ia_api: ConfiguracaoIaApi | None = None` (sexto
parâmetro, antes dos que já eram só por palavra-chave, então nenhum chamador existente quebrou) e
`cli.py:1272` passa `cfg.local.ia_api` — o `cfg` já estava na linha de cima. A alternativa era `app.py`
chamar `container.configuracao()` por dentro, que lê o `config/local.yaml` real: aí, no dia em que
Sidarta cadastrasse uma chave, os 14 arquivos de teste do console passariam a montar cliente de API
dentro da suíte. Injeção explícita é o padrão deste `criar_app` e mantém o teste hermético.

**`agente_nw/perfil/extrator.py` (um `Protocol` local).** `processar_fila` anotava
`cliente_llm: ClienteOllama` concretamente — é um dos três módulos que o item 2 do brief 075 já havia
apontado como importadores do nome. Com a seleção ligada, os quatro chamadores passam um cliente que
pode ser de API, e `mypy --strict` (parte do gate) reprova em quatro pontos. Declarado
`ClienteExtracaoPerfil(Protocol)` com `gerar_json` e `proveniencia`, exatamente o padrão que
`coleta/capturas/extrator.py` e `nucleo/relevancia/qualificador.py` já usam. Nenhuma mudança de
comportamento: só a anotação.

## Os 14 arquivos de teste do console

`app.py` não tem mais o nome `ClienteOllama`, e 14 arquivos de teste injetavam o cliente falso com
`monkeypatch.setattr(console_app, "ClienteOllama", _ClienteLLMFake)`. A costura mudou de lugar junto
com o código: agora é `monkeypatch.setattr(console_app, "selecionar_cliente_llm", ...)`, e por isso
`app.py` importa a função para o seu próprio namespace (`from config.container import ClienteLLM,
selecionar_cliente_llm`) em vez de chamá-la por `container.`. Foi uma substituição mecânica de uma
linha por arquivo: **nenhuma asserção de nenhum desses testes mudou**, e os 956 testes passam.

## Testes (escritos antes do código)

`tests/test_selecao_provedor.py`, 22 casos:

| Caso | Cobre |
|---|---|
| `test_sem_bloco_ia_api_devolve_cliente_ollama`, `test_bloco_ia_api_vazio_...` | o comportamento de hoje, inalterado |
| `test_configuracao_sem_ia_api_no_yaml_vira_o_padrao_de_ollama` | o `local.exemplo.yaml` real valida sem o bloco |
| `test_provedor_ollama_explicito_ignora_chave_cadastrada` | `provedor: ollama` com chave cadastrada segue local |
| `test_auto_com_so_anthropic/gemini/openai_...` | cada provedor sozinho |
| `test_auto_com_anthropic_e_openai_prefere_anthropic`, `test_auto_com_gemini_e_openai_prefere_gemini` | a ordem fixa do item 3.2 |
| `test_auto_com_chave_em_branco_nao_conta_como_cadastrada` | chave só com espaços não liga o provedor |
| `test_provedor_openai_explicito_vence_a_prioridade_da_anthropic` | override explícito |
| `test_provedor_explicito_sem_o_sub_bloco_falha_na_inicializacao` (×3) | `ValueError` citando o provedor, na inicialização |
| `test_provedor_desconhecido_nao_passa_pela_validacao_do_modelo` | `Literal` do Pydantic barra nome inválido |
| `test_cliente_de_api_recebe_um_cliente_ollama_como_cliente_de_embeddings` (×3) | o `ClienteOllama` do passo 1 é o `cliente_embeddings` do cliente devolvido |
| `test_proveniencia_do_cliente_escolhido_registra_o_modelo_da_api` (×3) | o modelo registrado é o da API |
| `test_nenhuma_construcao_direta_de_cliente_fora_da_selecao` | nenhum `ClienteOllama(`/`ClienteAnthropic(`/… em `app.py`, e as três chamadas da seleção |

Nenhum exige chave real, variável de ambiente ou internet.

## Arquivos preservados literalmente na área afetada

- `agente_nw/nucleo/llm.py` — **não tocado** neste brief (fechado pelos 074 e 075).
- `nucleo/prompts/*` — não tocados: o cerco de dado de terceiro do brief 068 já vale igual para as
  chamadas de API (item 3.6 e seção 5 do brief).
- As asserções dos 14 arquivos de teste do console — só a linha de `monkeypatch` mudou.
- `config/local.yaml` — não tocado: continua sem bloco `ia_api`, então nada mudou de comportamento
  nesta máquina até Sidarta cadastrar uma chave.

## RELATÓRIO FINAL

- **Brief executado:** 076 — com chave cadastrada, o programa usa a API; sem chave, continua no Ollama
  (conjunto `ia_api`, 3/3).
- **Arquivos criados:** `tests/test_selecao_provedor.py`,
  `docs/docs/doc_076_selecao_provedor_por_chave_2026-11-03.md`, `logs/commit_076.txt`,
  `logs/arquivos_076.txt`.
- **Arquivos alterados (resumo em uma linha cada):**
  - `agente_nw/nucleo/modelos/configuracao.py` — `ProvedorApi` e `ConfiguracaoIaApi` novos, e
    `Configuracao.ia_api` com padrão que não exige nada do YAML.
  - `config/container.py` — `selecionar_cliente_llm` (o único lugar que decide o provedor), a ordem de
    prioridade, o alias `ClienteLLM`, e `llm()` passando a usar a seleção.
  - `agente_nw/console/app.py` — as três construções de cliente passam pela seleção; `criar_app` ganhou
    o parâmetro `ia_api`.
  - `agente_nw/cli.py` — `console_cmd` passa `cfg.local.ia_api` ao `criar_app`.
  - `agente_nw/perfil/extrator.py` — `processar_fila` passa a pedir um `Protocol` local
    (`ClienteExtracaoPerfil`) em vez do `ClienteOllama` concreto.
  - `config/local.exemplo.yaml` — bloco `ia_api` documentado, comentado.
  - `AGENTS.md` — §3 ganhou a regra da geração por API e da invariante dos embeddings.
  - `docs/ARQUITETURA.md` — §8 ganhou o parágrafo do conjunto `ia_api` (fora do git, como todo `docs/`).
  - 14 arquivos de teste do console — a costura de injeção do cliente falso mudou de
    `ClienteOllama` para `selecionar_cliente_llm`; nenhuma asserção alterada.
- **Arquivos preservados literalmente na área afetada:** `agente_nw/nucleo/llm.py`,
  `nucleo/prompts/*`, `config/local.yaml`.
- **Script de verificação (o gate, rodado pelo `scripts/agente_entregar.sh`; saída colada):** ver
  "Saída do gate" abaixo.
- **Comandos executados:**
  - `.venv/bin/python -m pytest tests/test_selecao_provedor.py -q` → `22 passed`
  - `.venv/bin/python -m pytest -q` → `956 passed, 5 deselected`
  - `.venv/bin/python -m ruff check .` → `All checks passed!`
  - `.venv/bin/python -m ruff format --check .` → `287 files already formatted`
  - `.venv/bin/python -m mypy agente_nw` → `Success: no issues found in 122 source files`
  - `git status --short` (conferência do manifesto, antes do `add`)
  - `git ls-files docs/ | wc -l` → `0` (por isso `docs/ARQUITETURA.md` não entra no manifesto)
  - `scripts/agente_entregar.sh 076`
- **Manifesto do commit (`logs/arquivos_076.txt` e `logs/commit_076.txt`):** ver abaixo.
- **Pendências e decisões que ficaram abertas:** cadastrar uma chave real e conferir o
  `chamadas_llm.jsonl` — só Sidarta pode (seção 6 do brief); mais as lacunas abaixo.
- **Resumo, Doing, Backlog e Done do `docs/PLAN.md` atualizados:** sim.

## Saída do gate

```
$ scripts/agente_entregar.sh 076
manifesto 076: 22 arquivo(s)
ruff check: ok
ruff format: ok
mypy: ok
pytest: ok (956 passed, 5 deselected in 21.99s)
lacunas do 076: 1 no Backlog, 0 em Pendências, 1 em Dívidas, 1 em Decisões
✓ brief 076: commit 7d59d7b, enviado ao GitHub
```

956 testes: os 934 do brief 075 mais os 22 de `tests/test_selecao_provedor.py`.

## Manifesto

`logs/arquivos_076.txt`:

```
AGENTS.md
agente_nw/nucleo/modelos/configuracao.py
config/container.py
config/local.exemplo.yaml
agente_nw/console/app.py
agente_nw/cli.py
agente_nw/perfil/extrator.py
tests/test_selecao_provedor.py
tests/test_console_apagar_unir.py
tests/test_console_busca_rede_social.py
tests/test_console_configurar_perfil.py
tests/test_console_contatos.py
tests/test_console_editar_ficha.py
tests/test_console_eu.py
tests/test_console_menu.py
tests/test_console_novo_contato.py
tests/test_console_preparar.py
tests/test_console_redes_sociais.py
tests/test_console_sem_usuario.py
tests/test_console_tela_unica.py
tests/test_console_temas.py
tests/test_whatsapp_importador.py
```

`logs/commit_076.txt`:

```
feat(llm): com chave cadastrada em ia_api a geracao vai para a API; sem chave, Ollama (brief 076)
```

## Lacunas

| # | Lacuna | Destino | Impacto |
|---|--------|---------|---------|
| 1 | A chave de API fica em texto puro em `config/local.yaml` (decisão do brief, seção 5: o arquivo já é o lugar do que é específico da máquina e já é ignorado pelo git). Não há nada impedindo que ela vá para a tela: nenhum comando do produto imprime a configuração hoje, mas também não existe máscara — um `print(cfg.local)` futuro exibiria a chave inteira. Sidarta decide se vale um tipo que esconde o valor na repr | decisão | nice |
| 2 | Não há comando que diga qual provedor está ativo. Depois de cadastrar a chave, a única forma de confirmar que a geração saiu do Ollama é abrir `dados/logs/chamadas_llm.jsonl` e olhar o campo `modelo` — é o que a pendência de aceite do brief manda fazer. Um `agente_nw verificar-ambiente` que informasse o provedor de geração escolhido pouparia isso | backlog | nice |
| 3 | `selecionar_cliente_llm` mora em `config/container.py` e `agente_nw/console/app.py` passou a importar dele (`from config.container import ClienteLLM, selecionar_cliente_llm`), o que soma uma dependência do console à camada de configuração além do `container.http()` que já havia. Arquitetura hexagonal estrita poria a função em `nucleo/`, mas `nucleo/llm.py` não era arquivo-alvo deste brief | dívida | nice |
