# Brief 031 (v2) — Perfil de hardware `pro48` e seleção de perfil por máquina

**Repositório:** `/Users/sidarta48/github/agente_nw` (MacBook Pro M5 Pro, 48 GB) e `/Users/lilian/network` (MacBook Air M3, 16 GB)
**Depende de:** nenhum brief aberto. Não altera comportamento do Air enquanto o `config/local.yaml` do Air não for tocado.
**Data:** 2026-10-08
**Mudança em relação à v1:** o perfil `pro48` usa `qwen2.5:14b`, já instalado no Pro, em vez de `qwen3:30b-a3b`. Como o `qwen2.5` não tem modo de raciocínio, o cliente passa a omitir a chave `think` para perfis que declaram isso (seção 3.4). A troca para outro modelo, se vier a ser necessária, é uma alteração de YAML.

---

## 1. Objetivo em uma frase

O mesmo repositório roda com modelos pequenos no MacBook Air (16 GB) e com modelos grandes no MacBook Pro (48 GB), e a escolha de qual perfil usar fica em um arquivo por máquina, fora do git — sem cópia de pasta, sem ramo paralelo, sem segunda versão do projeto.

---

## 2. Contexto e o que já existe

O projeto já foi desenhado para isto. O `config/llm_routing.yaml` tem a estrutura `perfil_ativo` + `perfis`, e o `ClienteOllama` (`agente_nw/nucleo/llm.py`) lê tudo — modelo, `num_ctx`, temperatura, `format`, `think` — do perfil ativo. Só existe um perfil declarado, `air16`, e o `perfil_ativo` está gravado no próprio `llm_routing.yaml`, que é versionado. Resultado: para trocar de máquina hoje seria preciso editar um arquivo versionado, o que levaria à situação que se quer evitar (duas cópias divergentes do mesmo projeto).

O que já está pronto e será reaproveitado sem alteração de contrato:

- `Roteamento`, `PerfilRoteamento`, `TarefaRoteamento` em `agente_nw/nucleo/modelos/configuracao.py`, com o validador que exige `think: false` em toda tarefa.
- `config/container.py`: `configuracao()` carrega `local.yaml` (ou `local.exemplo.yaml` na ausência) e, separadamente, `llm_routing.yaml`.
- `config/local.yaml` já é por máquina e já está no `.gitignore` — é o lugar natural para a escolha do perfil.
- `agente_nw verificar-ambiente` (`cli.py`) já consulta `/api/tags` do Ollama e confere modelos obrigatórios, mas a lista `MODELOS_OBRIGATORIOS` é fixa no código, não derivada do perfil ativo.
- `dados/`, `saidas/`, `logs/`, `*.db`, `temas.yaml`, `fontes.yaml` já estão fora do git — cada máquina tem seus próprios dados. Decisão já tomada anteriormente e mantida aqui: o Air começou com banco próprio, vazio; não há migração de dados entre as máquinas neste brief.

---

## 3. Decisões tomadas agora

**3.1. Um único repositório, dois perfis declarados no mesmo arquivo.** O `llm_routing.yaml` passa a ter `air16` e `pro48`. Ambos são versionados e evoluem juntos: qualquer tarefa nova de LLM precisa ser declarada nos dois perfis (ver validador em 4.2). O `perfil_ativo` do `llm_routing.yaml` continua existindo e continua sendo `air16` — é o padrão seguro, porque o Air é a máquina de produção e é a mais restrita.

**3.2. A escolha da máquina vai para `config/local.yaml`, chave `perfil_llm`.** Opcional. Quando presente, sobrescreve o `perfil_ativo` do `llm_routing.yaml`. Quando ausente, vale o padrão (`air16`). O Air não precisa de nenhuma mudança: seu `local.yaml` não tem a chave e continua em `air16`. O Pro recebe `perfil_llm: pro48` no seu `local.yaml`.

**3.3. Modelos do perfil `pro48`.** Um único modelo de geração para todas as tarefas: `qwen2.5:14b` (denso, 9 GB, já instalado no Pro — nenhum download necessário). Decisão do usuário: testar primeiro com o que já está na máquina; se a qualidade ou a velocidade não satisfizerem, trocar por outro modelo é uma alteração de YAML no mesmo perfil, sem código novo. Com `bge-m3` residente, o total fica em torno de 10 GB — folga ampla em 48 GB. O `qwen3:8b`, usado hoje só em `prerotular_calibracao`, não entra no `pro48`: um único modelo de geração simplifica a memória e a verificação de ambiente. Embeddings continuam em `bge-m3` nos dois perfis, obrigatoriamente: os vetores gravados no banco têm 1024 posições e são comparados entre si; trocar o modelo de embedding em uma máquina só tornaria os bancos incomparáveis.

**3.4. O `qwen2.5` não tem modo de raciocínio — a chave `think` passa a ser omitida por perfil.** O cliente hoje envia `"think": false` em toda chamada a `/api/generate`. Isso é necessário para a família `qwen3` (sem a chave, o raciocínio fica ligado por padrão), mas o `qwen2.5` não possui essa capacidade e o Ollama pode recusar a chamada com erro 400 ("model does not support thinking") quando recebe a chave. Solução estrutural, não contorno: `PerfilRoteamento` ganha `enviar_think: bool = True`. No `pro48`, `enviar_think: false`, e `_chamar_generate` simplesmente não inclui a chave `think` no corpo da requisição. O campo `think: false` em cada tarefa continua obrigatório pelo validador (documenta a regra do produto "nunca raciocinar") e continua sendo enviado no `air16`. Teste de payload cobre os dois casos (4.7). Se o `pro48` um dia voltar para um modelo `qwen3`, basta remover `enviar_think: false` do perfil.

**3.5. Contextos do `pro48`.** `num_ctx: 8192` nas tarefas curtas (`qualificar`, `rotular`, `prerotular_calibracao`) e `num_ctx: 16384` nas tarefas que recebem texto longo (`cartao`, `cruzar_por_que`, `extrair_de_texto`). O `qwen2.5:14b` suporta até 32k de contexto; 16k é suficiente para os textos coletados e mantém a latência baixa. Temperaturas iguais às do `air16`. `format: json` mantido.

**3.6. Proteção contra rodar o perfil errado na máquina errada.** Cada perfil ganha o campo `memoria_minima_gb` (`air16: 16`, `pro48: 24`). O `verificar-ambiente` compara com a memória física da máquina (`sysctl -n hw.memsize`) e emite FALHA obrigatória se o perfil ativo exigir mais memória do que existe. É uma garantia estrutural: se alguém copiar um `local.yaml` do Pro para o Air, o ambiente recusa antes de o Ollama começar a trocar modelos em disco. O valor 24 para o `pro48` é deliberadamente acima do que o `qwen2.5:14b` precisa, porque o perfil é "o perfil da máquina grande" e vai receber modelos maiores com o tempo; o número é ajustado junto com o modelo.

**3.7. Lista de modelos obrigatórios derivada do perfil ativo.** `MODELOS_OBRIGATORIOS` deixa de ser constante e passa a ser calculada: conjunto dos `modelo` de todas as tarefas do perfil ativo mais o modelo de embeddings. Assim o `verificar-ambiente` no Pro pede `qwen2.5:14b` e `bge-m3`; no Air, `qwen3:4b`, `qwen3:8b` e `bge-m3`. Nunca mais uma lista fixa a manter em dois lugares.

**3.8. `verificar-ambiente` passa a informar o perfil.** Primeira linha da saída: `Perfil LLM ativo  OK  pro48 (definido em config/local.yaml)` ou `air16 (padrão de config/llm_routing.yaml)`. É a resposta direta à pergunta "em qual configuração esta máquina está rodando".

**3.9. LaunchAgent do Ollama sem mudança.** `OLLAMA_MAX_LOADED_MODELS=2` e `OLLAMA_KEEP_ALIVE=30m` servem aos dois perfis. Com um único modelo de geração no Pro, o limite de dois modelos carregados nunca é atingido de forma prejudicial.

---

## 4. Escopo

### 4.1. `config/llm_routing.yaml`

```yaml
perfil_ativo: air16   # padrão versionado; a máquina sobrescreve em config/local.yaml (perfil_llm)
perfis:
  air16:
    memoria_minima_gb: 16
    embeddings:
      modelo: bge-m3
    tarefas:
      qualificar:            {modelo: qwen3:4b, num_ctx: 2048, temperature: 0.2, format: json, think: false}
      rotular:               {modelo: qwen3:4b, num_ctx: 2048, temperature: 0.2, format: json, think: false}
      cartao:                {modelo: qwen3:4b, num_ctx: 4096, temperature: 0.3, format: json, think: false}
      cruzar_por_que:        {modelo: qwen3:4b, num_ctx: 4096, temperature: 0.3, format: json, think: false}
      extrair_de_texto:      {modelo: qwen3:4b, num_ctx: 4096, temperature: 0.2, format: json, think: false}
      prerotular_calibracao: {modelo: qwen3:8b, num_ctx: 2048, temperature: 0.1, format: json, think: false}
    nova_tentativa:
      temperature: 0.1
      maximo: 1
  pro48:
    memoria_minima_gb: 24
    enviar_think: false   # qwen2.5 não tem modo de raciocínio; a chave think não vai no payload
    embeddings:
      modelo: bge-m3
    tarefas:
      qualificar:            {modelo: qwen2.5:14b, num_ctx: 8192,  temperature: 0.2, format: json, think: false}
      rotular:               {modelo: qwen2.5:14b, num_ctx: 8192,  temperature: 0.2, format: json, think: false}
      cartao:                {modelo: qwen2.5:14b, num_ctx: 16384, temperature: 0.3, format: json, think: false}
      cruzar_por_que:        {modelo: qwen2.5:14b, num_ctx: 16384, temperature: 0.3, format: json, think: false}
      extrair_de_texto:      {modelo: qwen2.5:14b, num_ctx: 16384, temperature: 0.2, format: json, think: false}
      prerotular_calibracao: {modelo: qwen2.5:14b, num_ctx: 8192,  temperature: 0.1, format: json, think: false}
    nova_tentativa:
      temperature: 0.1
      maximo: 1
```

### 4.2. `agente_nw/nucleo/modelos/configuracao.py`

- `PerfilRoteamento` ganha `memoria_minima_gb: int = Field(ge=1)` e `enviar_think: bool = True`.
- `Roteamento` ganha um segundo validador `model_validator(mode="after")`: todos os perfis declaram exatamente o mesmo conjunto de nomes de tarefa e o mesmo modelo de embeddings. Mensagem de erro nomeia o perfil e as tarefas faltantes ou sobrando. Impede que uma tarefa nova seja declarada só em um perfil e falhe com `KeyError` na outra máquina semanas depois.
- `Configuracao` (o `local.yaml`) ganha `perfil_llm: str | None = None`.

### 4.3. `config/container.py`

Em `configuracao()`, depois de carregar `local`, carregar o dicionário bruto do `llm_routing.yaml`; se `local.perfil_llm` não for `None`, gravar `dados["perfil_ativo"] = local.perfil_llm` **antes** de chamar `Roteamento.model_validate` — assim o validador `perfil_ativo_existe` continua cobrindo o valor vindo do `local.yaml` (um `perfil_llm: pro40` com erro de digitação falha na carga, com a mesma mensagem de hoje).

Adicionar `origem_perfil_llm() -> str` que devolve `"config/local.yaml"` ou `"config/llm_routing.yaml"`, para a linha do `verificar-ambiente`.

### 4.3-A. `agente_nw/nucleo/llm.py`

Em `_chamar_generate`, montar o corpo sem a chave `think` e incluí-la (`"think": tarefa.think`) somente quando `perfil.enviar_think` for verdadeiro. Nenhuma outra alteração no cliente: `format`, `num_ctx`, temperatura, nova tentativa, fila de revisão e log de chamadas continuam iguais.

### 4.4. `config/local.exemplo.yaml`

```yaml
banco: dados/agente.db
pasta_saida: saidas
pasta_backups: dados/backups
ollama_url: http://127.0.0.1:11434
# perfil_llm: pro48   # perfil de config/llm_routing.yaml desta máquina; ausente = air16
```

### 4.5. `agente_nw/cli.py`

- Remover a constante `MODELOS_OBRIGATORIOS`; `_verificar_modelos` recebe o perfil ativo e deriva a lista (3.6). Ordem de exibição: modelos de geração em ordem alfabética, embeddings por último.
- Novo `_verificar_perfil_llm(roteamento, origem) -> ItemVerificacao` (3.7), sempre `ok=True`, obrigatório — é informativo.
- Novo `_verificar_memoria(perfil) -> ItemVerificacao` (3.5): lê `sysctl -n hw.memsize` via `subprocess` com `timeout=5`; em falha de leitura (Linux, erro), devolve `ok=True` com detalhe "não verificado" e `obrigatorio=False`, para não quebrar testes fora do macOS. Em macOS compara `memsize / 2**30` com `memoria_minima_gb`; detalhe no formato `"48 GB físicos, mínimo do perfil 40 GB"`.
- `verificar_ambiente` monta a lista com o item de perfil em primeiro lugar e o de memória logo após o de Ollama.

### 4.6. `AGENTS.md`

Atualizar o parágrafo sobre Ollama: o modelo por tarefa vem do **perfil ativo** de `config/llm_routing.yaml`, escolhido por `perfil_llm` em `config/local.yaml`; `air16` no Air (produção), `pro48` no Pro (desenvolvimento). Retirar a afirmação de que `qwen3:4b` é obrigatório em toda chamada — o obrigatório é `think: false`; o modelo depende do perfil. Manter a regra "verificar com `ollama list` antes de sugerir download".

### 4.7. Testes

- `tests/test_configuracao.py`: os testes existentes de `think` continuam valendo para `air16`; acrescentar o mesmo par para `pro48`.
- `test_perfis_declaram_as_mesmas_tarefas`: remover uma tarefa de `pro48` no dicionário carregado e esperar `ValidationError`.
- `test_perfil_llm_do_local_sobrescreve_padrao`: com um `local.yaml` temporário contendo `perfil_llm: pro48` (usar `monkeypatch` em `RAIZ` ou em `_carregar_yaml` e limpar o `lru_cache` de `configuracao`), `configuracao().roteamento.perfil_ativo == "pro48"`.
- `test_perfil_llm_inexistente_falha_na_carga`: `perfil_llm: pro40` → `ValidationError` com a mensagem de `perfil_ativo_existe`.
- `test_modelos_obrigatorios_derivados_do_perfil`: para `pro48`, a lista é `["qwen2.5:14b", "bge-m3"]`; para `air16`, `["qwen3:4b", "qwen3:8b", "bge-m3"]`.
- `tests/test_llm_payload.py`: além do teste existente (perfil `air16`, corpo contém `"think": false`), acrescentar `test_payload_omite_think_quando_perfil_pede`: com o roteamento carregado e `perfil_ativo` forçado para `pro48`, o corpo enviado a `/api/generate` **não contém** a chave `think`, e contém `"model": "qwen2.5:14b"` e `"format": "json"`.
- `tests/test_llm_log_chamadas.py` lê o perfil ativo do arquivo; continua passando porque o padrão versionado segue `air16`.

---

## 5. Procedimento por máquina (depois do merge)

**MacBook Pro (esta máquina, desenvolvimento):**
1. Nenhum download: `qwen2.5:14b` e `bge-m3` já estão instalados (`ollama list`).
2. Criar `config/local.yaml` a partir do `local.exemplo.yaml` se ainda não existir, e acrescentar `perfil_llm: pro48`.
3. `agente_nw verificar-ambiente` — a primeira linha deve mostrar `pro48 (definido em config/local.yaml)`, o item de memória deve mostrar 48 GB físicos e os modelos `qwen2.5:14b` e `bge-m3` presentes.
4. Reiniciar o LaunchAgent do Ollama (`launchctl kickstart -k gui/$(id -u)/br.agente_nw.ollama`) para descarregar `qwen3:4b` da memória.
5. Prova real com o modelo: `agente_nw qualificar --limite 3` (ou, na ausência de itens pendentes, `agente_nw cartao <assunto_id>` para um assunto existente). A chamada deve concluir sem erro 400 do Ollama e sem entrada nova em `fila_revisao`; conferir em `dados/logs/chamadas_llm.jsonl` que as linhas registram `sucesso: true` em 1 tentativa.

**MacBook Air (produção, usuário `lilian`):**
1. `git pull`.
2. Nada mais. O `local.yaml` do Air não tem `perfil_llm`; `verificar-ambiente` deve mostrar `air16 (padrão de config/llm_routing.yaml)` e os mesmos três modelos de sempre.

---

## 6. Fora de escopo, com justificativa

- **Ativar raciocínio (`think: true`) em qualquer perfil.** O `qwen2.5` nem possui a capacidade; para um eventual modelo `qwen3` maior no `pro48`, exigiria mudar o validador, revisar o tratamento da resposta e medir latência. É um brief próprio, se e quando o modelo do `pro48` for trocado.
- **Escolher agora o modelo definitivo do `pro48`.** Decisão do usuário: validar o funcionamento com `qwen2.5:14b` primeiro. Candidatos para a troca, se necessária: `qwen3:30b-a3b` (requer download, ~19 GB, e `enviar_think` volta a `true`) ou `qwen3:8b` em todas as tarefas (já instalado). Em ambos os casos a mudança é só no YAML.
- **Migrar dados entre as máquinas.** Decisão anterior mantida: bancos independentes. Se um dia for necessário, `agente_nw copiar-banco` e `restaurar-backup` já existem.
- **Perfil intermediário (por exemplo, para o Air com `qwen3:8b` em todas as tarefas).** Sem necessidade declarada; a estrutura comporta acrescentar depois.
- **Ajustar limiares (`config/limiares.yaml`) para o modelo maior.** Os limiares são do produto, não do hardware. Se o `qwen2.5:14b` mudar a distribuição de notas de qualificação, isso aparecerá no `certificar` e será tratado como calibração, não como configuração de máquina.
- **Exibir o perfil ativo no console web.** O `verificar-ambiente` cobre a necessidade; o console não precisa de mais uma informação de infraestrutura na tela.

---

## 7. Passos de execução

1. `configuracao.py`: `memoria_minima_gb`, `enviar_think`, `perfil_llm`, validador de tarefas idênticas entre perfis.
2. `llm_routing.yaml`: acrescentar `memoria_minima_gb` em `air16` e o perfil `pro48` completo (4.1).
3. `container.py`: sobrescrita de `perfil_ativo` a partir de `local.perfil_llm`; `origem_perfil_llm()`.
4. `llm.py`: chave `think` condicionada a `enviar_think` (4.3-A).
5. `local.exemplo.yaml`: linha comentada `perfil_llm`.
6. `cli.py`: `_verificar_perfil_llm`, `_verificar_memoria`, `_verificar_modelos` derivado do perfil; remover `MODELOS_OBRIGATORIOS`.
7. Testes da seção 4.7.
8. `AGENTS.md` (4.6).
9. `pytest`, `ruff`, `mypy` limpos.
10. Commit único: `feat(config): perfil de hardware pro48 e seleção de perfil por máquina via config/local.yaml`.

---

## 8. Critérios de aceite

- No Pro, com `perfil_llm: pro48` no `local.yaml`: `verificar-ambiente` retorna 0, primeira linha nomeia `pro48` e a origem `config/local.yaml`, lista exige `qwen2.5:14b` e `bge-m3`, item de memória em OK.
- No Pro, uma chamada real de qualificação ou cartão com `qwen2.5:14b` conclui com JSON válido em 1 tentativa, sem erro 400 e sem entrada em `fila_revisao` (passo 5 do procedimento).
- No Pro, com `perfil_llm` removido do `local.yaml`: `verificar-ambiente` nomeia `air16` e a origem `config/llm_routing.yaml`; nenhum outro arquivo foi alterado para isso.
- `perfil_llm: pro40` (inexistente): carga de configuração falha com mensagem que nomeia o perfil.
- No Air, após `git pull` e sem tocar no `local.yaml`: comportamento idêntico ao anterior ao brief; `verificar-ambiente` nomeia `air16`.
- `llm_routing.yaml` com uma tarefa a menos em qualquer perfil: validação falha nomeando o perfil e a tarefa.
- `git status` limpo depois de configurar o Pro: `local.yaml` permanece ignorado; nenhuma diferença de configuração de máquina chega ao repositório.
