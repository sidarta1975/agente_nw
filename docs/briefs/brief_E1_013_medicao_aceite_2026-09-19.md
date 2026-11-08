# Brief E1-013 — Medição de aceite e certificação

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Depende de:** brief 012 (ciclo diário, LaunchAgents), certificado.
**Natureza diferente dos briefs anteriores**: não é um brief que se fecha numa sessão. A parte de código (seção 4) se escreve e testa agora; a medição de verdade (seção 5) precisa de cinco dias corridos passando, com você marcando o Markdown todo dia. O relatório final só existe depois do quinto dia.

---

## 1. Objetivo em uma frase

Rodar o ciclo cinco dias seguidos sem você mexer no banco na mão, medir os sete critérios de aceite da proposta ao comitê (seção 5.8) contra dado real, e fechar a Etapa 1 — ou abrir um brief 014 se alguma dívida travar a Etapa 2.

---

## 2. Contexto: os critérios da proposta precisam de dois ajustes antes de medir

Os sete critérios estão em `docs/agente_nw_proposta_comite_v5_2026-09-17.md`, seção 5.8. Dois deles foram escritos **antes** das correções que fizemos ao longo da execução real e não valem mais como estão escritos — não é uma reinterpretação frouxa, é o texto ficando defasado da implementação que você já aprovou passo a passo:

**Critério 2a, como estava escrito**: "tipo atribuído pela máquina concorda com o rótulo humano em 10 de 12 ou mais" + "limiares 0,55 e 0,8 calibrados com 30 linhas reais rotuladas pelo usuário (a IA pré-classifica; o usuário corrige)". **Como vamos medir de verdade**: os 12 casos do brief 009 são aritmética determinística, não um julgamento seu — o aceite é **12 de 12**, não 10 de 12 (não existe motivo pra tolerar erro em conta). Os limiares 0,55 e 0,8 **não foram calibrados com 30 linhas rotuladas por você** — foi decisão sua, tomada na certificação do brief 009, de adiar essa calibração para quando houver uso real de verdade (`status` `usado`/`nao_serve` de dias reais), em vez de fazer você rotular uma amostra sintética. Este brief não volta atrás nisso — mede o que existe (os 12 casos passando, os limiares documentados como não calibrados) e registra a calibração real como trabalho futuro, não como pendência bloqueadora.

**Critério 6, "amostra de 50 pares"**: o brief 007 rodou com 48 pares reais (dois a menos do que a proposta estimava, porque é a quantidade real de pares que existiam na banda de dúvida no dia da calibração, não um número escolhido). Medir 48, não forçar 50.

Fora esses dois ajustes, os outros cinco critérios (1, 3, 4, 5, 7) valem exatamente como escritos.

---

## 3. Os sete critérios, como vão ser medidos de verdade

| # | Critério (adaptado onde precisa) | Como medir |
|---|---|---|
| 1 | Cinco dias seguidos de ciclo sem intervenção manual no banco | `progresso` com `ciclo:backup` de cada um dos 5 dias, mais `git status` limpo em `dados/` em cada verificação (nenhuma escrita fora do ciclo) |
| 2 | Menu para 5+ contatos ativos, 3+ assuntos cada; sem tag recebe `sem_assunto` sem travar | Consulta em `assunto_contato` por dia; se no início da medição nenhum contato real tiver tema confirmado (situação herdada dos briefs 009/011), **você precisa confirmar tema real em pelo menos 5 contatos reais antes do dia 1 da medição** — é o próprio propósito da medição, não dá para medir sem uso real. Ver seção 5. |
| 2a | 12 casos do conector: 12 de 12. Limiares 0,55/0,8: documentados como não calibrados com dado real (decisão do brief 009, mantida) | `pytest tests/test_pontuacao.py -v` |
| 3 | JSON válido em pelo menos 95% das chamadas | **Não existe hoje um jeito de medir isso** — `gerar_json` tenta duas vezes e só registra a falha final em `fila_revisao`; não há registro de quantas vezes a primeira tentativa bastou. Escopo novo deste brief, seção 4.1 |
| 4 | Ciclo completo em até 20 minutos com 10 contatos ativos | Duração total no log de cada um dos 5 dias |
| 5 | Todo `assunto_id` num menu existe no banco — zero invenção | Consulta de integridade referencial explícita (seção 4.2) — reforça o que a `FOREIGN KEY` já deveria garantir, como prova auditável separada |
| 6 | Limiar de agrupamento calibrado (48 pares, não 50) e em ADR; `schema_version` com migração aplicada; backup diário gerado e **restaurado uma vez em teste de verdade** | ADR já existe (brief 007); `restaurar-backup` nunca foi exercitado contra um backup real de produção — fazer isso pelo menos uma vez durante os 5 dias, seção 5 |
| 7 | Filtro de categorias sensíveis: 30 frases (15 passam, 15 descartadas), 100% de acerto | Conferir se `tests/test_sensivel.py` já tem exatamente esse conjunto (brief 004) — se tiver menos de 30 casos ou não estiver na proporção 15/15, é uma dívida a registrar, não a fabricar agora só para bater o número |

**Indicador acompanhado, não critério de aceite**: aproveitamento (`usado` ÷ total entregue), por dia, desde o primeiro dia — linha de base, não meta.

**Duas verificações adicionais do brief 012, específicas desta medição**: variáveis do Ollama ativas depois do reboot do dia 12 (já feito) **e depois de um segundo reboot no meio da medição** (dia 15), com o ciclo rodando pelo gatilho de login do mesmo dia — prova que sobrevive a mais de um ciclo de reboot, não só ao primeiro teste.

---

## 4. Escopo de código

### 4.1 Instrumentar a validade de JSON (criador 3 não é medível hoje)

- **`agente_nw/nucleo/database/migracoes/00X_chamada_llm_log.sql`** — não precisa de tabela nova: usar log em arquivo, mais simples e sem risco no esquema (decisão tomada agora — ver próximo item).
- **`config/container.py`** (aditivo): `caminho_log_chamadas_llm() -> Path` → `dados/logs/chamadas_llm.jsonl`.
- **`agente_nw/nucleo/llm.py`**: `ClienteOllama.__init__` passa a receber `caminho_log: Path` (parâmetro novo, obrigatório — é uma peça central da operação, não opcional). Em `gerar_json`, depois de cada tentativa (sucesso ou não), acrescentar uma linha ao arquivo (criar a pasta se não existir): `{"tarefa": ..., "tentativas_usadas": 1 ou 2, "sucesso": true/false, "quando": agora}`. Uma falha ao escrever o log **nunca** pode derrubar a chamada real — envolver em `try/except` silencioso (é telemetria, não é o caminho crítico).
- **`config/container.py`**: `llm()` passa `caminho_log_chamadas_llm()` na construção do `ClienteOllama`.
- **Ajustar todos os pontos que hoje constroem `ClienteOllama` diretamente** (`cli.py` e testes que não usam fake) para passar o novo parâmetro — mesmo tipo de ajuste mecânico já feito no brief 008 com `test_importar_temas.py`.
- `tests/test_llm_log_chamadas.py`: sucesso na primeira tentativa grava `tentativas_usadas=1, sucesso=true`; sucesso só na segunda grava `tentativas_usadas=2, sucesso=true`; falha nas duas grava `sucesso=false` **e ainda** vai para `fila_revisao` como já acontecia (não substitui o mecanismo existente, só acrescenta o registro).

### 4.2 Consulta de integridade referencial (critério 5, prova auditável)

- **`queries/assunto_contato.py`** (aditivo): `contar_orfaos(conexao) -> int` — `SELECT COUNT(*) FROM assunto_contato ac LEFT JOIN assunto a ON a.id = ac.assunto_id WHERE a.id IS NULL`. Deve dar sempre zero (a `FOREIGN KEY` já impede a escrita), mas é a prova que entra no relatório, não uma suposição sobre o que o schema garante.

### 4.3 `agente_nw certificar` — o comando que junta tudo

Novo comando (não estava reservado antes — nome livre, primeiro brief a precisar dele): `agente_nw certificar --desde AAAA-MM-DD --ate AAAA-MM-DD`. Para cada dia no intervalo: lê o log de ciclo daquele dia (`dados/logs/ciclo_<dia>*.log`) e extrai a duração total e de cada etapa; conta `assunto_contato` por `perfil_id` e `tipo` daquele `gerado_em`; calcula aproveitamento do dia. No fim do intervalo: soma chamadas de `chamadas_llm.jsonl` e calcula a taxa de sucesso na primeira tentativa; roda `contar_orfaos`; imprime um resumo por dia e um resumo agregado. **Não decide sozinho se o critério passou ou falhou** — só reúne os números; a decisão de aceite é sua, lendo o relatório (mesmo espírito do resto do projeto: a máquina não se autocertifica).

- `tests/test_cli_certificar.py`: roda contra um banco/logs de teste fabricados, confirma que os números batem com o que foi fabricado.

---

## 5. O protocolo dos cinco dias — o que você faz

**Antes do dia 1 da medição**: confirmar tema real (via `ficha`/`confirmar-tags`, comandos do brief 005) em pelo menos 5 contatos reais de verdade — sem isso, o critério 2 não tem como ser medido contra realidade nenhuma, só contra o fixture de teste. É o próprio ponto da medição: ver o produto funcionando com gente de verdade.

**Cada um dos 5 dias**: o ciclo roda sozinho de madrugada (LaunchAgent do brief 012). Sua parte: abrir o `menu_<dia>.md` no Obsidian ou no Drive e marcar "usei"/"não serve" nos itens reais, como já validamos no brief 011 — 5 minutos.

**Dia 3 da medição (equivalente ao "dia 15" do calendário original)**: reiniciar o Mac de novo, deixar o ciclo disparar pelo gatilho de login, confirmar no log e no `launchctl` que o Ollama subiu certo de novo.

**Em algum ponto dos 5 dias**: rodar `agente_nw copiar-banco` seguido de `agente_nw restaurar-backup` contra um backup real do dia, confirmar que abre e tem os dados esperados — é a primeira vez que esse comando roda contra dado de produção de verdade, não só em teste automatizado.

**No dia útil seguinte ao quinto dia**: rodar `agente_nw certificar --desde <dia 1> --ate <dia 5>`, e junto com os resultados dos testes automatizados (12 casos, 30 frases sensíveis, integridade referencial), escrever o relatório final desta seção 6 abaixo. Você lê, autoriza os commits.

---

## 6. O relatório final de certificação — formato

Documento separado (não é o RELATÓRIO FINAL de brief comum — este vale para a Etapa 1 inteira), com os sete critérios da seção 3 marcados individualmente como cumprido / não cumprido / cumprido com ressalva, os números reais de cada um, as dívidas conhecidas consolidadas (a lista já vem crescendo desde o brief 005: nota do macOS não lida, curadoria real de tema, limiares do conector não calibrados, ferramenta desconhecida na porta 11434, e qualquer uma nova que apareça nestes 5 dias), e uma recomendação explícita: Etapa 1 certificada como está, ou lista do que falta.

**Se alguma dívida bloquear a Etapa 2** (ex.: critério 3 ou 7 vier abaixo do exigido, ou o reboot do dia 3 não recuperar): abre-se um brief 014 de correção pontual, escopo definido pela dívida específica encontrada — não escrito agora, porque ainda não existe.

**Se nada bloquear**: não existe brief 014. `docs/PLAN.md` atualizado com o estado final da Etapa 1.

---

## 7. Fora de escopo, com justificativa

- **Console web (brief 010).** Roda em paralelo, escrito enquanto o ciclo dos 5 dias avança sozinho — não é pré-requisito da medição, e a medição não depende dele (o Markdown já prova o ciclo completo desde o brief 011).
- **Calibração real dos limiares 0,55/0,8.** Cinco dias de `usado`/`nao_serve` é pouco dado para calibrar com confiança — registrar como trabalho de Etapa 2, não fabricar uma calibração apressada aqui.
- **Resolver a ferramenta desconhecida na porta 11434.** Decisão já tomada no brief 012: fica como risco conhecido, você investiga quando quiser.

---

## 8. Passos de execução (a parte de código, agora)

1. `container.py`: `caminho_log_chamadas_llm`.
2. `nucleo/llm.py`: parâmetro novo em `ClienteOllama`, gravação de log em `gerar_json`.
3. Ajustar `container.py` (`llm()`) e todo ponto de construção direta de `ClienteOllama` em `cli.py`/testes.
4. `tests/test_llm_log_chamadas.py`.
5. `queries/assunto_contato.py`: `contar_orfaos`.
6. `cli.py`: comando `certificar`.
7. `tests/test_cli_certificar.py`.
8. Conferir `tests/test_sensivel.py` contra o critério 7 (30 casos, 15/15) — se não bater, registrar como dívida agora, não completar a amostra artificialmente só para fechar o número.
9. A partir daqui, o trabalho passa a ser o protocolo da seção 5 — não tem mais "passo de código" até o dia útil seguinte ao quinto dia.

---

## 9. Riscos e como reverter

| Risco | Controle |
|---|---|
| `test_sensivel.py` não tiver exatamente 30 casos na proporção certa | registrar como dívida real, não fabricar casos só para bater o número do critério |
| Log de chamadas LLM falhar por permissão de disco ou pasta ausente | `try/except` silencioso — nunca derruba a chamada real ao modelo |
| Cinco dias corridos incluem fim de semana e você esquecer de marcar um dia | não invalida a medição sozinho — registrar no relatório qual dia ficou sem marcação e por quê |
| Reverter | Mudança em `ClienteOllama.__init__` é a única que toca código já em produção (assinatura nova, obrigatória) — reverter significa remover o parâmetro e as chamadas que o passam; todo o resto é aditivo |

---

## 10. Relatório final obrigatório

Para a parte de código (seção 8): preencher o bloco da seção 8 de `AGENTS.md` normalmente. Para a certificação da Etapa 1 inteira (depois do quinto dia): o documento da seção 6 desta brief, que substitui o RELATÓRIO FINAL padrão nesse momento específico.
