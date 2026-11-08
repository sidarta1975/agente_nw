# DOC 055 — documentos canônicos (relatório do brief 055)

## RELATÓRIO FINAL
- Brief executado: 055 — documentos canônicos: ler menos, nada desatualizado, regras novas valendo. Gate de dependência (commit do 050) conferido: `a283d4b` e `2c31eac`.
- Arquivos criados:
  - `docs/historico/2026-10-25_pre_055/` (cópias de `PLAN.md`, `PLANO.md`, `ARQUITETURA.md` e `AGENTS.md` de antes do brief)
  - `docs/historico/PLAN_historico_ate_2026-10-25.md`
  - `docs/briefs/_modelo.md`
  - `docs/docs/doc_055_documentos_canonicos_2026-10-25.md` (este)
  - `logs/commit_055.txt`
- Arquivos alterados (com resumo da mudança em uma linha cada):
  - `AGENTS.md`: §1 ordem de leitura nova; §2 em duas linhas; §3 só regras; §5 `commitar.sh`; §6 gate `verificar.sh`; §8 relatório em `docs/docs/`; §9 Resumo/Doing/Backlog/Done; §10 nova (briefs e numeração).
  - `docs/PLAN.md`: reescrito em Resumo/Doing/Backlog/Done/Pendências/Decisões/Dívidas/Armadilhas; histórico movido.
  - `docs/ARQUITETURA.md`: §2 (estrutura), §8 (LLM), §9 (verdade e tema, brief 046), §10 (rotas reais), §11 (sem agendamento) reescritas; frase de §1 e de §12 corrigidas.
  - `docs/PLANO.md`: §5 (estado dos perfis, `pro48` corrigido para `qwen2.5:14b`), §6 (numeração, relatório, histórico); célula "ciclo diário" da Etapa 1 marcada como removida.
- Arquivos preservados literalmente na área afetada: as 31 armadilhas do PLAN (linhas 46–78 do original, `diff` vazio); o histórico (linhas 82–178, `diff` vazio); §4, §7 e o texto de regra de §5/§6 do `AGENTS.md`; Decisões em aberto nº 1.
- Script de verificação (caminho completo, pronto para colar no terminal): nenhum `.py` foi tocado; não há gate de código neste brief. O gate completo continua `/Users/sidarta48/github/agente_nw/scripts/verificar.sh`, e não é necessário rodar.
- Comandos executados: `cp`/`cmp`/`wc`, `sed`, `diff`, `grep`, `ls`, `git status`, `git log` (só leitura) e scripts Python de edição de texto. Nenhum git de escrita, nenhuma suíte.
- Lista de arquivos para `git add` e texto sugerido do commit: só `AGENTS.md`. Mensagem em `logs/commit_055.txt`. Comando: `scripts/commitar.sh logs/commit_055.txt AGENTS.md`
- Pendências e decisões que ficaram abertas: ver "Lacunas" abaixo. Nenhuma exige decisão antes do commit.
- Resumo, Doing, Backlog e Done do `docs/PLAN.md` atualizados: sim

## Tamanhos antes e depois (`wc -c`)

| Documento | Antes | Depois |
|---|---|---|
| `AGENTS.md` | 13.627 | 11.396 |
| `docs/PLAN.md` (arquivo todo) | 57.951 | 20.839 |
| `docs/PLAN.md` até o fim de `## Dívidas conhecidas` | — | 7.270 |
| `docs/ARQUITETURA.md` | 17.316 | 22.363 |
| `docs/PLANO.md` | 11.902 | 13.394 |
| **Leitura obrigatória** (AGENTS + PLAN até Dívidas) | **100.796** (4 documentos) | **18.666** |
| `docs/historico/PLAN_historico_ate_2026-10-25.md` | — | 42.169 |

ARQUITETURA e PLANO cresceram: receberam a estrutura e a stack que saíram do AGENTS. Deixam de ser leitura obrigatória; entram por "Seções a ler" do brief.

## Fontes usadas na ARQUITETURA (conferidas em 2026-10-25)

- §2: `ls` de `agente_nw/`, `agente_nw/nucleo/`, `agente_nw/coleta/*`, `agente_nw/ponte/`, `extensao/`, `scripts/`, `config/`, `docs/`. Comandos da CLI: `agente_nw/cli.py` (`add_parser`; não há `ciclo`). Não existem `scripts/launchd/` nem `nucleo/sensivel.py`.
- §8: `config/llm_routing.yaml` linhas 1–44 (perfis `air16` e `pro48`, tarefas, `memoria_minima_gb`, `enviar_think`); `agente_nw/nucleo/modelos/configuracao.py:25` (`perfil_llm`); `agente_nw/cli.py:143–160` (verificação de memória); `AGENTS.md` (Ollama).
- §9: entrada do brief 046 do PLAN (histórico, "Atualização 2026-10-14"); `agente_nw/nucleo/prompts/cruzar_por_que.py:75` (regra de verdade); `agente_nw/nucleo/prompts/redigir_ganchos.py:157` (`_regras`); `config/limiares.yaml:20–21` (`conector.consulta.minima: 0.45`).
- §10: `agente_nw/console/app.py` linhas 181–821 (todos os `@app.route`); `agente_nw/ponte/servidor.py:15–16` (`HOST`, `PORTA_PADRAO`).
- §11: `grep -rn "PARE"` em `agente_nw/`, `config/`, `scripts/` (só `_MAX_PARES_*` de `calibracao.py`, nada de `dados/PARE`); `scripts/instalar_macos.sh` e `cli.py` sem `ciclo` nem `launchd`.

## Conferências da seção 8 (saída)

```
== 1. leitura obrigatória ==
AGENTS.md=   11396 PLAN(até fim de Dívidas)=    7270 soma=18666 (limite 25000; antes 100796)
== 2. histórico (diff do trecho movido) ==
linhas 82-178 idênticas
armadilhas idênticas
linhas não vazias do PLAN antigo ausentes no novo PLAN/histórico: []
== 3. desatualizado ==
docs/PLANO.md:75:| **1 — MVP Qwen3 4B** | 1 a 3 | Importação da agenda, ciclo diário (removido no brief 016), menu por contato, console, exportação Markdown | 5 dias segu
docs/ARQUITETURA.md:9:Fluxo da Etapa 1 (desenho original; o ciclo diário às 05h00 e seus LaunchAgents foram removidos no brief 016 — hoje cada etapa roda quando Sidarta a
docs/ARQUITETURA.md:97:Nome do pacote e da pasta é sempre `agente_nw`. Removidos: `scripts/launchd/` e os LaunchAgents (brief 016); o comando `ciclo` também não existe ma
docs/ARQUITETURA.md:206:**Servidor Ollama.** Sobe pelo próprio usuário, fora do aplicativo do Ollama (nunca o Ollama.app, nunca `brew services`), acessado pela `ollama_ur
docs/ARQUITETURA.md:210:O programa **não descarta conteúdo por tema** (política, saúde, religião…): quem decide que tema cabe numa mensagem é o usuário. O filtro de categ
docs/PLAN.md:78:8. **`launchctl setenv` não sobrevive a reboot.** Variáveis de ambiente do Ollama (`OLLAMA_MAX_LOADED_MODELS`, `OLLAMA_KEEP_ALIVE`) vão no plist do Launch
== 4. regras ==
1 git add -A
1 Git nunca roda de forma autônoma
1 Ollama.app
1 11435
1 think: false
2 127.0.0.1
1 copiar-banco
1 banco real só é tocado
2 Nunca rodam sozinhos
1 Mudança cirúrgica
1 isso funcionava antes
1 migração numerada
1 Restrições são estruturais
1 Quem decide que tema cabe
== 5 ==
ls: CLAUDE.local.md: No such file or directory
ls: CLAUDE.md: No such file or directory
== 6 ==
PLAN copia ok    57951
PLANO copia ok    11902
ARQUITETURA copia ok    17316
AGENTS.md
ARQUITETURA.md
PLAN.md
PLANO.md
== 7 ==
 M AGENTS.md
== tamanhos depois ==
   11396 AGENTS.md
   20839 docs/PLAN.md
   13394 docs/PLANO.md
   22363 docs/ARQUITETURA.md
    1816 docs/briefs/_modelo.md
   42169 docs/historico/PLAN_historico_ate_2026-10-25.md
  111977 total
```

Notas sobre as conferências:

- **Critério 3.** Restam 5 ocorrências em `AGENTS.md`, `ARQUITETURA`, `PLANO`, todas no passado ("removido no brief 016/046"). Resta também 1 ocorrência em `docs/PLAN.md:78`, a armadilha 8 ("vão no plist do LaunchAgent"). Ela é texto histórico de armadilha e o brief manda mantê-la literal (§3.5); fica como ocorrência conhecida.
- **Critério 6.** O `cmp` do passo 1 rodou antes de qualquer edição e passou nos três arquivos (PLAN 57.951, PLANO 11.902, ARQUITETURA 17.316 bytes). A linha "copia ok" da saída acima é só a conferência de existência e tamanho depois das edições, não uma segunda comparação com os originais.
- **Critério 7.** `git status --short` mostra só ` M AGENTS.md`.

## Lacunas (afirmações que contradizem o AGENTS vigente ou o código; não reescritas, como o brief manda)

1. `ARQUITETURA` §1 (fluxo): todo o desenho em oito passos é o ciclo da Etapa 1 com o menu por contato; o fluxo vivo é o pedido em texto livre (§10). Só a frase de abertura foi corrigida.
2. `ARQUITETURA` §3 (tabelas): faltam as tabelas criadas depois da 001 (`pedido`, `gancho_uso`, `nota_contato`, `rede_social`, `rede_sem_perfil`, cache de listas, `consulta_contato`, `progresso`…) e a `descarte_sensivel` aparece como ativa; ela está vazia desde o brief 046.
3. `ARQUITETURA` §4 e §5: contratos de `extrair_pedido`, `desempatar_perfil`, `redigir_ganchos`, `extrair_termos_contato`, `descrever_imagem` não estão descritos; a regra do conector não menciona o piso `conector.consulta.minima`.
4. `ARQUITETURA` §7: ainda diz "divergência de mais de 30%" para fonte independente; o valor vigente é 8% (`config/limiares.yaml`, armadilha 4).
5. `PLANO` §1 e §2: dizem que o software "não escreve mensagem"; desde os briefs 038/047 ele redige a mensagem base e os ganchos. §3 ainda lista "Categorias sensíveis" (filtro removido no 046) e "Interface com três telas" (hoje a tela única). §4 e §5 trazem Etapas e perfis `air16b`/`air16c`/`win8` de desenho antigo.
6. `PLAN`, nota fora do pedido: o teste `tests/test_extrator.py::test_extracao_real_produz_tags_e_campos_esperados` (Ollama real) deu `ReadTimeout` numa rodada em 25/10 e passou na seguinte (681 verdes). Não registrei como dívida: parece contenção de carga do Ollama, como a dívida 8 antiga (movida para o histórico).
7. As "Armadilhas novas" da atualização de 12/10 (brief 044) ficaram no arquivo de histórico, porque estão depois da linha 82. São três: X e Instagram bloqueiam automação; aba em segundo plano renderiza pela metade; `externally_connectable` e o relé da ponte. Consulta por `grep -n "Armadilhas novas"`.
8. Aviso do brief: "Números a reatribuir pelo Projeto" — os briefs 051 e 052 do Projeto (unificação do pedido e dos ganchos; auditoria de contaminação externa) estão no Backlog só pelo título.
9. Itens que escolhi nas Dívidas (julgamento, para Sidarta revisar): mantidas a 2, 4, 6 e 7 originais; movidas ao histórico a 1 e a 5 (marcadas "Resolvida"), a 3 (`fontes.yaml`, informativa) e a 8 (contenção na porta 11434, da era dos LaunchAgents). Acrescentadas a 9 e a 10, tiradas das "observações abertas" dos briefs 046 e 047.

## Lacunas

| # | Lacuna | Destino | Impacto |
|---|---|---|---|
| 1 | ARQUITETURA §1 (fluxo em oito passos), §3 (faltam tabelas posteriores à 001 e `descarte_sensivel` aparece ativa), §4 e §5 (sem os contratos de `extrair_pedido`, `desempatar_perfil`, `redigir_ganchos`, `extrair_termos_contato`, `descrever_imagem`; regra do conector sem o piso `conector.consulta.minima`) e §7 (diz 30% de divergência; o vigente é 8%) estão desatualizadas | dívida | degrada |
| 2 | PLANO §1 e §2 dizem que o software não escreve mensagem (escreve, desde o 038/047); §3 lista categorias sensíveis e três telas; §4 e §5 trazem Etapas e perfis `air16b`/`air16c`/`win8` de desenho antigo | dívida | degrada |
| 3 | Teste real do extrator (`test_extracao_real_produz_tags_e_campos_esperados`) deu ReadTimeout; o marcador `llm_real` do 057 o tirou do gate | nenhum | nice |
| 4 | As "Armadilhas novas" da atualização de 12/10 (brief 044) ficaram no arquivo de histórico; consulta por `grep -n "Armadilhas novas"` | nenhum | nice |
| 5 | Os briefs 051 e 052 do Projeto estavam no Backlog sem número; foram renumerados para 056 e feitos (auditoria) | nenhum | nice |
| 6 | Julgamento sobre as Dívidas: mantidas 2, 4, 6 e 7; movidas ao histórico 1, 3, 5 e 8; acrescentadas 9 e 10. Sidarta pode rever a escolha | decisão | nice |
