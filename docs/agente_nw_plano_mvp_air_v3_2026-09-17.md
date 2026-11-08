# agente_nw — Plano de execução do MVP (Etapa 1) — versão 3

**Data:** 17 de setembro de 2026
**Substitui:** as versões 1 e 2 do mesmo dia. Mudanças em relação à v2, todas da segunda revisão externa: comandos de linha para ativar contato e confirmar tags no brief da agenda (o único furo funcional); banco em modo WAL e console desenvolvido sobre cópia do backup, nunca sobre o banco em medição; amostra de calibração estratificada na banda de dúvida; 30 linhas reais rotuladas para calibrar os limiares do conector; Ollama instalado pela fórmula do Homebrew, sem o aplicativo; segundo reboot no meio da medição; versão 5 da proposta emitida antes do dia 1. Prazo e escopo inalterados.
**Base:** Proposta para aprovação do comitê, **versão 5** (a v4 com as cinco correções da seção 7 deste plano), emitida e aprovada antes do dia 1, para que o brief 000 reescreva os documentos-base a partir de um documento aprovado, não de uma v4 com emendas
**Máquina:** MacBook Air 2024, chip M3, 16 GB de memória unificada, macOS Sonoma 14.6
**Modelos:** `qwen3:4b` (geração, modo de raciocínio desligado) e `bge-m3` (embeddings); `qwen3:8b` só para pré-rotular a amostra de calibração
**Prazo:** três semanas e meia (17 dias úteis), 14 briefs, um brief por sessão de execução do Claude Code, uma sessão por vez
**Repositório:** `/Users/sidarta48/github/agente_nw` — hoje só documentação; o primeiro brief atualiza os documentos-base, o segundo cria o código

---

## 1. O que o MVP entrega

Um ciclo diário que roda sozinho às 05h00 (ou no primeiro login): lê 20 a 40 feeds, agrupa em assuntos, qualifica, cruza com os contatos ativos pela regra do conector e entrega, num arquivo Markdown e no console local, o menu de assuntos por contato — conectores no alto, viáveis com esforço abaixo, nada do que o usuário não teria como sustentar. A base de contatos nasce da agenda do Mac e do Google Contatos. O usuário marca "usei" ou "não serve", e isso fica registrado para a calibragem da Etapa 2.

Fora do MVP, por decisão da proposta: extensão do Chrome, exportação de conversa do WhatsApp, modelo de visão, resumo completo, balanço semanal, integrações Google além da importação de contatos, assistentes pagos.

---

## 2. Preparação da máquina (antes do brief 001, 40 minutos)

```bash
# Python 3.12 do Homebrew (traz o próprio SQLite e aceita carregar extensões, que o sqlite-vec exige)
brew install python@3.12
# Ollama: a FÓRMULA do Homebrew instala só o binário. O instalador oficial (e o cask) instala o aplicativo,
# que se registra no login e ocupa a porta 11434 — o conflito que o LaunchAgent do brief 012 quer evitar.
brew install ollama
# Não iniciar por `brew services start ollama`: isso cria um segundo LaunchAgent sem as variáveis.
ollama pull qwen3:4b
ollama pull bge-m3
ollama pull qwen3:8b        # só para a calibração do brief 007
# Até o brief 012 existir, nas sessões de desenvolvimento o servidor sobe assim, num terminal à parte:
OLLAMA_MAX_LOADED_MODELS=2 OLLAMA_KEEP_ALIVE=30m ollama serve
# Ambiente do projeto
cd ~/github/agente_nw && python3.12 -m venv .venv && source .venv/bin/activate
pip install feedparser trafilatura httpx pydantic pyyaml numpy sqlite-vec flask python-dateutil phonenumbers pyobjc-framework-Contacts pytest mypy ruff
```

A permissão de acesso à agenda é pedida pelo macOS na primeira execução do importador, em nome do aplicativo que o executa; o importador roda sempre do Terminal.

---

## 3. Regras de execução

1. **Uma sessão por vez.** Um brief por sessão do Claude Code, sem sessões simultâneas no mesmo repositório. A ordem da seção 4 já resolve o que o paralelismo tentaria resolver.
2. **Se não passar, não avança.** Nenhum brief começa enquanto o aceite do anterior estiver falhando. O executor corrige dentro do próprio brief até duas vezes; na terceira falha, para, registra no relatório final o que falhou e por quê, e aguarda. O template já tem "riscos e como reverter" e o relatório final obrigatório; isto é a regra que os liga.
3. **Git nunca roda sozinho.** O executor prepara a lista de arquivos e o texto do commit no relatório final; o usuário autoriza. `git add -A` é proibido.
4. **Configuração antes de código que a consome.** Os temas do usuário existem antes da coleta; os contatos ativos existem antes do cruzamento (seção 5).
5. **Ninguém desenvolve sobre o banco em medição.** Durante os cinco dias do brief 013, o único processo que escreve em `dados/agente.db` é o ciclo. O console é desenvolvido contra uma cópia restaurada do backup diário e só aponta para o banco real no dia da certificação. O banco roda em modo WAL desde a criação, para que leituras concorrentes (console, comandos de linha) nunca bloqueiem o ciclo.
6. **Datas, não números de dia.** Quando o dia 1 for fixado, o brief 000 reescreve o calendário da seção 5 em datas reais; os "dias corridos" da medição e os "dias úteis" do console deixam de poder divergir.

---

## 4. Os briefs, na ordem de execução

Nome dos arquivos: `brief_E1_NNN_<assunto>_<data>.md`, em `docs/briefs/`, fora do git, com cópia na aba Saídas. A numeração é a de identidade (não muda); a ordem de execução é a desta seção.

### Semana 1 — Fundação e primeira coleta

**000 — Atualizar os documentos-base** (dia 1)
`brief_E1_000_documentos_base`
Reescreve `PLANO.md`, `ARQUITETURA.md`, `PLAN.md` e `AGENTS.md` do repositório para refletir a Proposta v4 **com as correções da seção 7 deste plano**: pacote `agente_nw`; modelo de dados com `assunto_contato`; regra do conector com a regra do nível; perfis de hardware; saída por contato; contrato de extração de texto entre os contratos comuns. Acrescenta uma linha no cabeçalho de `PLANO.md` ("plano geral: fases e decisões fechadas") e de `PLAN.md` ("estado vivo: pendências, dívidas, decisões abertas; atualizado a cada commit") para que o papel de cada um fique explícito. Sem código.
Aceite: os quatro documentos não contradizem a v4 corrigida em nenhum ponto; `PLAN.md` lista os 13 briefs restantes como próximos passos, nesta ordem. Depende de: nada.

**001 — Esqueleto do repositório e configuração** (dia 2)
`brief_E1_001_esqueleto`
Estrutura de pastas da arquitetura, `pyproject.toml`, `.gitignore` com as regras de dado pessoal (`dados/`, `saidas/`, `capturas/`, `*.db`, `*.db-wal`, `*.db-shm`, `temas.yaml`, `fontes.yaml`, `config/local.yaml`, `*.csv`), `config/container.py`, `config/llm_routing.yaml` com o perfil `air16`, `config/limiares.yaml` com os valores iniciais (0,82 agrupar; 0,55 adjacência; 0,8 conversável; 0,6/0,6 qualificação), `temas.exemplo.yaml` (com o campo `nivel`) e `fontes.exemplo.yaml` versionados, comando `agente_nw importar-temas` que lê `temas.yaml` para o banco, script de verificação (`ruff`, `mypy --strict`, `pytest`), script de instalação para macOS.
Aceite: verificação verde; `sqlite3` do Python carrega o `sqlite-vec` (`enable_load_extension` funciona); `ollama list` mostra os três modelos; o container resolve cliente de LLM e conexão de banco sem nenhum módulo instanciar nada direto. Depende de: 000.

**002 — Esquema, migrações e backup** (dia 3)
`brief_E1_002_esquema_migracoes_backup`
`scripts/migracoes/001_inicial.sql` **só com as tabelas que a Etapa 1 usa**: `schema_version`, `tema`, `perfil`, `perfil_tema`, `fonte`, `item`, `assunto`, `assunto_contato`, `fato`, `fila_extracao`, `descarte_sensivel`, mais a tabela virtual do `sqlite-vec`. Restrições UNIQUE em `tema.nome` e `perfil_tema(perfil_id, tema_id)`; `assunto_contato.id` como chave primária. As tabelas da Etapa 2 (`conta`, `captura`, `midia_processada`, `conversa_tema`) e da Etapa 4 (`pacote_troca`) entram em migrações próprias quando as funcionalidades chegarem — é para isso que existe migração numerada. Executor de migrações na inicialização. **Banco em modo WAL desde a criação** (`PRAGMA journal_mode=WAL`), para leitura concorrente sem bloquear o ciclo. Modelos Pydantic v2 `frozen=True`, um módulo por entidade. Camada de consultas isolada. Backup diário pela API de backup do SQLite em `dados/backups/`, retenção de 7 dias, comando de restauração — e comando `agente_nw copiar-banco <destino>` que restaura o último backup numa cópia para desenvolvimento.
Aceite: banco criado do zero por migração; `schema_version` = 1; `journal_mode` responde `wal`; reimportar o mesmo tema não duplica; backup gerado e restaurado num banco temporário com contagem de linhas igual; leitura por um segundo processo durante uma escrita não bloqueia nem falha. Depende de: 001.

**003 — Cliente de LLM e embeddings** (dia 4)
`brief_E1_003_cliente_llm_embeddings`
Cliente único do Ollama: modelo resolvido pelo roteamento, `think: false` como parâmetro fixo do cliente (não do prompt), `format` com esquema JSON, `num_ctx` obrigatório, temperatura por tarefa, um item por chamada, uma nova tentativa com temperatura 0,1 em JSON inválido, fila de revisão na segunda falha. Embeddings pelo `/api/embed` com `bge-m3`, gravação no `sqlite-vec`, cosseno e centróide em `nucleo/vetores.py`.
Aceite (teste de fumaça; o percentual real é medido no brief 013): JSON válido em 20 de 20 chamadas de um prompt de exemplo; embedding de 100 textos em menos de 30 segundos; JSON propositalmente inválido cai na fila de revisão com o erro registrado; o teste falha se `think` não for `false`. Depende de: 002.

**006 — Coleta RSS e Google News** (dia 5 — antecipado para acumular material antes da calibração)
`brief_E1_006_coleta_rss`
Leitor de `fontes.yaml`; `feedparser` e `trafilatura`; URL canônica (sem `utm_*`, `fbclid`, âncora; um redirecionamento seguido); hash de título normalizado; ruído estrutural (corpo abaixo de 400 caracteres, título de lista, patrocinado, mais de 7 dias na primeira aparição); gerador de consultas do Google News a partir dos temas já importados (`quote` obrigatório, 2 segundos entre chamadas); regra de fonte independente (domínio diferente e texto divergindo mais de 30%); retenção de `item.texto` por 90 dias; progresso por etapa, retomável; parada por arquivo sentinela. Comando `agente_nw coletar`, que o usuário roda uma vez por dia até o brief 012 automatizar.
Aceite: 20 feeds reais mais as consultas dos temas do usuário coletados em menos de 8 minutos; duplicata por URL e por título rejeitada; feed vazio dois dias seguidos gera alerta; interromper e reexecutar continua de onde parou. Depende de: 003 e dos temas do usuário importados (seção 5).

**004 — Filtro de categorias sensíveis e extrator de texto** (dia 6)
`brief_E1_004_filtro_sensivel_extrator_texto`
`nucleo/sensivel.py`: listas de termos por categoria (saúde, religião, política, sindicato, vida sexual, origem racial, menores), descarte com registro em `descarte_sensivel` sem o trecho. Contrato `extrair_de_texto` (contratos comuns da proposta corrigida) com prompt, esquema e um exemplo resolvido; processador da `fila_extracao` que roda o modelo, aplica o filtro e grava tags `sugerida` não confirmadas, campos guiados e fatos datados.
Aceite: 30 frases (15 passam, 15 descartadas) com 100% de acerto; texto de cadastro de exemplo produz ao menos 4 tags e 2 campos guiados corretos; nenhum item da fila chega ao banco sem passar pelo filtro. Depende de: 003.

**005 — Importação da agenda** (dia 7)
`brief_E1_005_importacao_agenda`
Dois leitores idempotentes: agenda do macOS pelo framework de Contatos e CSV do Google Contatos. Telefone normalizado para E.164 com `phonenumbers` como chave de identidade; e-mail como segunda chave. Marcadores viram tags `importada`; notas vão para a `fila_extracao`; nada nasce ativo. Comando `agente_nw importar-agenda`, executado do Terminal (a permissão do macOS é concedida por aplicativo; o brief documenta isso e o erro explícito quando ela é negada). **Três comandos de linha que fazem as vezes do console até o dia 13:** `agente_nw ficha <telefone>` (mostra a ficha, as lacunas e as tags sugeridas numeradas), `agente_nw ativar <telefone>` e `agente_nw confirmar-tags <telefone> --todas` ou `--ids 1,3,5`. O telefone aceita qualquer formato; é normalizado antes da busca.
Aceite: a agenda real importa sem duplicar ninguém; rodar duas vezes deixa o mesmo número de perfis; contato com notas gera tags sugeridas depois de processada a fila; executado do Terminal, o pedido de permissão aparece uma vez e não volta; o usuário ativa 10 contatos e confirma as tags deles pelos três comandos, sem tocar no banco à mão. Depende de: 004.

### Semana 2 — Motor

**007 — Agrupamento em assuntos e calibração do limiar** (dia 8, com pelo menos dois dias de coleta acumulados)
`brief_E1_007_agrupamento_calibracao`
Agrupamento por centróide em janela de 7 dias, limiar de `limiares.yaml`, encerramento após 7 dias sem item, reabertura marcada como "volta ao noticiário", divisão de assunto com mais de 12 itens e dispersão alta. Ferramenta de calibração com **amostra estratificada**: dos 50 pares de itens, 35 sorteados na banda de dúvida (cosseno entre 0,70 e 0,92, em torno do valor inicial) e 15 fora dela como controle — metade claramente iguais, metade claramente distintos. Pares aleatórios seriam quase todos de assuntos obviamente diferentes e não diriam nada sobre onde fica o limiar. O **`qwen3:8b`**, com `think: false`, pré-rotula "mesmo assunto / assuntos diferentes"; o usuário revisa só as discordâncias; a ferramenta calcula o limiar de melhor separação, grava em `limiares.yaml` e escreve o ADR com a distribuição dos cossenos da amostra.
Aceite: limiar calibrado sobre coleta real de dois ou mais dias, com ao menos 30 pares dentro da banda de dúvida, e ADR escrito; com o limiar calibrado, cinco assuntos reais formados por mais de uma fonte independente; nenhum assunto com mais de 12 itens sem divisão. Depende de: 006.

**008 — Qualificação, rótulo, cartão e exemplos de conversabilidade** (dia 9)
`brief_E1_008_qualificacao_cartao`
Contrato `qualificar` com prompt, esquema e exemplo; candidatos pela união dos temas de todos os perfis ativos (teto de 40 por dia); corte 0,6/0,6; contrato `rotular`; contrato `cartao` para os assuntos que entrarem em algum menu. `prompts/exemplos_conversavel.yaml`: a IA escreve 10 exemplos positivos e 10 negativos no brief; o usuário aprova ou troca antes de o prompt ser fixado.
Aceite: 40 qualificações com JSON válido em 95% ou mais; um assunto que só toca temas de um contato (e nenhum do usuário) é qualificado; cartão sem número sem fonte entre parênteses. Depende de: 007.

**009 — Regra do conector e menu por contato** (dia 10)
`brief_E1_009_regra_conector_menu`
Centróide de perfil (média ponderada das descrições dos temas; nível do usuário com pesos 1,0 / 0,7 / 0,4); pré-seleção de 10 candidatos por contato; pontuação determinística 50/30/20; tipo pela regra corrigida — **conector exige aderência ≥ 0,55 a tema do usuário de nível domínio ou interesse; tema de nível curiosidade rende no máximo viável com esforço**; viável com esforço se conversabilidade ≥ 0,8; fora do domínio no resto, gravado como descartado; ordenação por tipo e score; os 5 primeiros; `cruzar` parte 2, em que o modelo só escreve o `por_que` e aponta o ponto de apoio nos viáveis; `sem_assunto` com motivo.
Dois conjuntos rotulados, com papéis diferentes. O **portão de aceite** são 12 casos montados à mão (4 conectores, 4 viáveis, 4 fora do domínio, com ao menos um caso em que o único apoio do usuário é tema de curiosidade). A **calibração** dos limiares 0,55 e 0,8 vem de 30 linhas reais de `assunto_contato` do ciclo daquele dia: a IA pré-classifica o tipo de cada uma, o usuário só corrige, e a ferramenta escolhe os limiares que maximizam a concordância, gravando em `limiares.yaml` e no ADR. Doze casos bastam para aceitar; não bastam para calibrar dois limiares.
Aceite: nos 12 casos, o tipo atribuído pela máquina concorda com o rótulo humano em 10 ou mais; as 30 linhas reais rotuladas e os limiares calibrados registrados no ADR; nenhum fora do domínio exibido; os descartes gravados com motivo; `por_que` de viável cita o ponto de apoio; contato sem tag recebe `sem_assunto` sem travar o ciclo. Depende de: 008 e 005, e dos contatos ativos marcados (seção 5).

**011 — Exportação em Markdown e leitura de marcações** (dia 11 — antecipado, porque é o canal de marcação durante a medição)
`brief_E1_011_exportacao_markdown`
Gerador de `menu_AAAA-MM-DD.md` na pasta de saída configurável, um bloco por contato com as duas faixas e o `id` de `assunto_contato` em comentário HTML; leitor de marcações (`[x] usei`, `[x] não serve` com um dos cinco motivos) que grava no banco na rodada seguinte.
Aceite: arquivo abre limpo no Obsidian e no app do Drive; marcação feita no arquivo chega ao banco com o motivo certo; arquivo com erro de formato gera aviso, não perda. Depende de: 009.

### Semana 3 e início da semana 4 — Operação, medição e console

**012 — Ciclo diário, LaunchAgents e agendamento** (dia 12 — no ar ao fim do dia)
`brief_E1_012_ciclo_diario_launchd`
Orquestrador `agente_nw ciclo`: coleta → embeddings → agrupamento → qualificação → pré-seleção e pontuação → cruzamento → cartões → exportação → backup, cada etapa gravando progresso e retomável. **Dois LaunchAgents:** um que sobe `ollama serve` com `OLLAMA_MAX_LOADED_MODELS=2` e `OLLAMA_KEEP_ALIVE=30m` no próprio plist (`EnvironmentVariables`), `RunAtLoad` e `KeepAlive` — o aplicativo de menu do Ollama não é usado, para não disputar a porta; e o do ciclo, com `StartCalendarInterval` às 05h00, recuperação de execução perdida, e segundo gatilho no login com 5 minutos de atraso que sai sem fazer nada se já rodou hoje. Log por execução com o tempo de cada etapa. Arquivo sentinela para parar. O brief confere que **não há Ollama.app nos itens de login nem serviço `ollama` do Homebrew ativo** — um segundo servidor na mesma porta, sem as variáveis, é exatamente a falha silenciosa que se quer evitar.
Aceite: ciclo completo com 10 contatos ativos em menos de 20 minutos; depois de reiniciar o Mac, o servidor do Ollama está no ar pelo LaunchAgent do projeto (e só por ele) com as duas variáveis ativas e os dois modelos carregam juntos sem descarregar um para o outro; Mac dormindo às 05h00 e acordado às 08h00 roda o ciclo até 08h05 e não roda de novo no dia; interrupção e reexecução completam sem duplicar assunto ou menu. Depende de: 011 e 009. **Não depende do console.**

**013 — Medição de aceite e certificação** (dias 13 a 17: cinco ciclos seguidos, do dia 13 ao 17 corridos, incluindo fim de semana; relatório no dia útil seguinte)
`brief_E1_013_medicao_aceite`
Roda os critérios da seção 5.8 da proposta por cinco dias seguidos com a marcação feita no Markdown, e produz o relatório de certificação: dias de ciclo sem intervenção; contatos com menu e assuntos por contato; percentual real de JSON válido; tempo de ciclo; invenção de `assunto_id` (zero); resultado dos 12 casos do conector e das 30 frases do filtro; ADRs dos limiares; backup restaurado; variáveis do Ollama ativas após o reboot do dia 12 **e após um segundo reboot no meio da medição (dia 15), com o ciclo rodando no login do mesmo dia** — o que prova que sobrevive a mais de um ciclo, não só ao teste; nenhuma escrita no banco real fora do ciclo durante os cinco dias; `git status` sem nada de `dados/`; aproveitamento registrado como linha de base. Atualiza `PLAN.md` com o estado real e as dívidas encontradas. Se alguma dívida bloquear a Etapa 2, abre um brief 014 de correção; se não, não existe brief 014.
Aceite: relatório com todos os critérios cumpridos, ou lista explícita do que falhou e por quê; `PLAN.md` atualizado; fase certificada. Depende de: 012.

**010 — Console web** (dias 13 a 16, em paralelo com a medição — o executor constrói enquanto o ciclo roda sozinho)
`brief_E1_010_console_web`
Flask em `127.0.0.1:8765`, sem framework de frontend, sem build. Três telas: Contatos (lista, ficha com tags por peso e origem, confirmação em lote, ativo, "gerar menu agora", indicador de lacunas por impacto, "Adicionar texto"); Menu (duas faixas, `por_que`, cartão expandível aberto por padrão nos viáveis, "usei" e "não serve" com os cinco motivos, contador de fora do domínio com lista sob clique); Temas (edição em linguagem natural, sinônimos, nível para os temas do usuário, sugestões pendentes). Botão "processar agora" para a fila. **Desenvolvido e testado contra uma cópia do banco** (`agente_nw copiar-banco`, restaurada do backup do dia), nunca contra `dados/agente.db` enquanto a medição corre; o caminho do banco é parâmetro de configuração e aponta para o real só no dia da certificação.
Aceite: o ciclo inteiro de marcar tags, ativar contato, ler menu e marcar "usei"/"não serve" acontece no navegador sem editar arquivo à mão; o servidor recusa conexão de outro endereço que não `127.0.0.1`; nenhuma escrita no banco real durante os dias de medição (verificado pelo relatório do 013 contra o log do ciclo); no dia da certificação, apontado para o banco real, lê o menu do dia sem erro. Depende de: 009. Não bloqueia 012 nem 013.

---

## 5. Calendário e o que o usuário faz

| Dia útil | Brief | O usuário faz | Tempo |
|---|---|---|---|
| antes do 1 | preparação da máquina (seção 2) | instala, puxa os três modelos | 40 min |
| 1 | 000 documentos-base | — | — |
| 2 | 001 esqueleto | **escreve `temas.yaml`: os próprios temas em frase corrida, com nível domínio / interesse / curiosidade** (o executor importa) | 20 min |
| 3 | 002 esquema | — | — |
| 4 | 003 cliente de LLM | — | — |
| 5 | 006 coleta | roda `agente_nw coletar` uma vez por dia até o brief 012 | 1 min/dia |
| 6 | 004 filtro e extrator | — | — |
| 7 | 005 agenda | concede a permissão de agenda no Terminal; exporta o CSV do Google Contatos; **marca 10 contatos como ativos e confirma as tags deles pelos comandos `ficha`, `ativar` e `confirmar-tags`** | 20 min |
| 8 | 007 calibração | revisa as discordâncias da pré-rotulagem dos 50 pares estratificados | 10 min |
| 9 | 008 qualificação | aprova ou troca os 20 exemplos de conversabilidade | 10 min |
| 10 | 009 conector | diz o tipo dos 12 casos montados e corrige a pré-classificação de 30 linhas reais do ciclo do dia | 10 min |
| 11 | 011 exportação | — | — |
| 12 | 012 ciclo e agendamento | reinicia o Mac uma vez para o teste de reboot | 5 min |
| 13–17 (corridos) | 013 medição, com 010 console em paralelo sobre cópia do banco | marca "usei" / "não serve" no Markdown todo dia; no dia 15, reinicia o Mac de novo | 5 min/dia |
| dia útil seguinte | 013 relatório e certificação; 010 apontado para o banco real | lê o relatório; autoriza os commits | 15 min |

Os números de dia viram datas no brief 000, quando o dia 1 for fixado (regra 6 da seção 3).

Total do usuário: cerca de duas horas em três semanas e meia, mais cinco minutos por dia na semana de medição. Em nenhum momento recebe lista para classificar: onde há classificação, a IA propõe e o usuário confirma.

---

## 6. Riscos específicos desta execução

| Risco | Onde é tratado |
|---|---|
| Modo de raciocínio do Qwen3 ligado quebra o JSON | 003: `think: false` é parâmetro fixo do cliente; o teste falha se ausente |
| Variáveis do Ollama somem após reboot e o ciclo dobra de tempo em silêncio | 012: LaunchAgent próprio do `ollama serve` com as variáveis no plist; 013 verifica após reboot |
| Calibração feita sobre material que não representa o uso | temas do usuário no dia 2, coleta no dia 5, calibração no dia 8 sobre dois ou mais dias reais |
| Limiar de agrupamento errado junta tudo ou fatia tudo | 007: calibração com amostra rotulada antes de qualquer assunto ir ao menu |
| Assunto de contato nunca chega ao menu | 008: candidatos pela união dos temas de todos os perfis ativos, testado explicitamente |
| Tema de curiosidade vira conector no topo sem preparação | 009: regra do nível no tipo; caso específico nos 12 de teste |
| Limiares 0,55 e 0,8 nunca calibrados | 009: aceite por concordância com rótulo humano, não por ordenação |
| Assunto fora do domínio do usuário aparece | 009: piso determinístico; 013 confere nos cinco dias |
| Permissão de agenda negada ou pedida pelo processo errado | 005: execução do Terminal documentada; erro explícito; CSV do Google como alternativa |
| Ciclo não roda porque o Mac dormia | 012: recuperação de execução perdida e gatilho no login testados com o Mac de fato dormindo |
| Dado pessoal vai para o git | 001: `.gitignore` nasce com as regras; 013 verifica `git status` |
| Brief seguinte começa com o anterior quebrado | regra 2 da seção 3 |
| Usuário sem meio de ativar contato ou confirmar tag antes do console | 005: três comandos de linha; o console só os substitui no dia 13 |
| Bug do console em desenvolvimento escreve no banco e invalida a medição | regra 5 da seção 3; 002: WAL e `copiar-banco`; 010 sobre cópia; 013 confere que só o ciclo escreveu |
| Amostra de calibração sem pares na faixa de dúvida devolve o chute inicial | 007: 35 dos 50 pares na banda 0,70–0,92 |
| Limiares do conector aceitos com 12 casos e nunca calibrados | 009: 30 linhas reais rotuladas além dos 12 casos |
| Dois servidores do Ollama na mesma porta, um sem as variáveis | preparação: fórmula do Homebrew, sem o aplicativo, sem `brew services`; 012 confere itens de login e serviços |

---

## 7. Correções da Proposta v4 que compõem a versão 5 (emitida e aprovada antes do dia 1)

1. **Tipo conector e nível.** Conector exige aderência ≥ 0,55 a tema do usuário de nível domínio ou interesse. Tema de curiosidade rende no máximo viável com esforço. A v4 dizia "sem o fator de nível", o que contradiz a própria definição de curiosidade.
2. **Aceite dos 12 casos.** Concordância do tipo atribuído com o rótulo humano (10 de 12 ou mais), que calibra 0,55 e 0,8 — e não "conectores acima de viáveis", que é verdadeiro por construção.
3. **Protocolo de promoção.** "Diferença de score menor que 10 pontos" (o score é 0–100), não 0,10.
4. **Seção 5.2 da v4** tem dois passos numerados como 6; renumerar.
5. **Contrato de extração de texto** sai da seção "Etapa 2" e entra nos contratos comuns, porque a Etapa 1 o usa para as notas da agenda.

Uma versão 5 da proposta com esses cinco pontos é emitida em separado, antes do brief 009 ser escrito.

---

## 8. Próximo passo

Aprovado este plano, o brief 000 é escrito e entregue na aba Saídas para execução imediata; os seguintes são escritos um a um, cada um depois do relatório final do anterior. Durante os cinco dias de medição, os briefs da Etapa 2 são escritos em paralelo.
