# AGENTS.md — agente_nw

> Coloque este arquivo na raiz do repositório. Claude Code lê antes de qualquer tarefa.
> Padrão herdado dos repositórios lex_hub, pandora_96 e claw_planalto (ferramenta externa, não clonada nesta máquina).

---

## 1. Papel do executor

Você implementa briefs. Não tem latitude criativa. Se o brief não cobre algo, pare e registre no relatório final como pendência — não invente.

O Claude Code carrega este arquivo sozinho no início da sessão (versão 2.1.277 ou posterior; sem `CLAUDE.md` na pasta). Antes de alterar qualquer coisa, leia: `docs/PLAN.md` até o fim de `## Dívidas conhecidas`; as seções do PLANO, da ARQUITETURA e das armadilhas citadas em "Seções a ler" no cabeçalho do brief; o brief; o código existente da área afetada. O histórico (`docs/historico/`) é consultado por busca, nunca lido inteiro. Não criar `CLAUDE.md` nem `CLAUDE.local.md` neste repositório: com eles, o Claude Code deixa de ler este arquivo.

## 2. Estrutura do repositório

Estrutura do repositório: `docs/ARQUITETURA.md` §2. Nome do pacote e da pasta é sempre `agente_nw`; desvio de nomenclatura é corrigido imediatamente.

## 3. Stack

Descrição (perfis `air16`/`pro48`, tarefas de LLM, embeddings): `docs/ARQUITETURA.md` §8. Aqui só o que é regra.

- Python 3.12 do Homebrew; Bash para utilitários.
- SQLite em modo WAL, arquivo único em `dados/agente.db`, nunca compartilhado entre processos.
- Ollama para inferência local, subido pelo próprio usuário fora do aplicativo (nunca o Ollama.app, nunca `brew services`), acessado pela `ollama_url` de `config/local.yaml`. Rodar `ollama list` antes de sugerir download.
- No Pro, **não subir servidor próprio**: `ollama_url` aponta para a instância compartilhada já existente (`http://127.0.0.1:11435`, mantida pelo `cervello`); nunca parar ou reiniciar essa instância a partir deste projeto.
- `think: false` obrigatório em toda tarefa; o perfil pode omitir a chave do payload com `enviar_think: false`, para modelos sem modo de raciocínio.
- Saída estruturada do LLM sempre em modo JSON com esquema (`format: json`); `num_ctx` explícito em toda chamada.
- Contratos: Pydantic v2 com `frozen=True`. Arquitetura hexagonal; dependências via `config/container.py`.
- Console web (`http://localhost:8765`) e ponte da extensão (`127.0.0.1:8766`) só em `127.0.0.1`.
- Coleta em rede social: extensão do Chrome do usuário (`extensao/`), comandada pelo programa por uma ponte local (`ponte/`, token por execução); nunca navegador separado. Uma rede por vez, com pausa entre páginas, na hora da consulta, com a sessão do próprio usuário. Ações fixas: `ola`, `abrir`, `estado`, `rolar`, `links`, `imagens`, `fechar`. As imagens publicadas são baixadas só para serem descritas por um modelo de visão (tarefa `descrever_imagem`); a imagem nunca é gravada, só a descrição.
- Agendamento: não existe. Nenhuma tarefa periódica. Toda execução é disparada explicitamente por Sidarta pelo console ou pela CLI.
- Testes: pytest. Tipagem: mypy strict. Lint: ruff. Suíte roda via `scripts/verificar.sh`, pelo executor, dentro do `scripts/agente_entregar.sh` (§6).

## 4. Regras de alteração

- Mudança cirúrgica: só o que o brief pede.
- Código funcionando não se altera sem evidência de defeito.
- Sem variantes de depuração, sem arquivos paralelos de módulos existentes.
- Sem hardcode de caminhos: resolução dinâmica.
- Texto de fonte externa (notícia, perfil) nunca é alterado ao ser armazenado; limpeza roda antes do hash de deduplicação, não sobre o texto guardado.
- Restrições são estruturais, não procedurais: o que não deve ser visto a jusante é bloqueado na origem, não filtrado depois.
- Antes de diagnosticar erro: "isso funcionava antes?" Responder essa pergunta antes de tocar em código.
- Toda alteração de tabela é uma migração numerada em `scripts/migracoes/`. Nenhum brief cria ou altera tabela fora de migração.
- Quem decide que tema cabe numa mensagem é o usuário (brief 046): o programa não descarta conteúdo por tema (política, saúde, religião…). Em troca, a redação nunca afirma sobre a pessoa o que ela não disse (opinião, posição, adesão), trata fato `[antigo]` ou `[de imagem]` como não atual, e o motor só entrega assunto com relação com o objetivo do pedido (`conector.consulta.minima` é piso necessário).

## 5. Git

- **Proibido `git add -A`.** Adição arquivo por arquivo, com lista explícita.
- `git status` obrigatório antes de qualquer `add`; arquivo inesperado interrompe a operação.
- Trunk-based em `main`. Sem branches de longa duração, sem recursos avançados de git.
- O executor commita e faz push ao fim de cada brief, exclusivamente por `scripts/agente_entregar.sh`, que só commita com o gate verde e só os arquivos do manifesto. Git de escrita digitado direto continua bloqueado pela trava `.claude/hooks/guarda_comando.py`.
- Remoção de arquivo rastreado: `git rm`, com critérios explícitos e exclusão de `__init__.py`, `.gitkeep` e afins.
- O manifesto do commit é `logs/commit_<NNN>.txt` (mensagem) e `logs/arquivos_<NNN>.txt` (um caminho por linha), gravados pelo executor antes de entregar. `scripts/commitar.sh` é chamado pelo `agente_entregar.sh`; digitado direto pelo modelo, é bloqueado.

## 6. Tarefas não assistidas

Não existem. Nenhuma etapa do sistema — coleta RSS, extração, agrupamento, qualificação, cruzamento, cartão, leitura de rede social, geração do menu — roda sem que Sidarta a dispare explicitamente pelo console ou pela CLI. Cada disparo é isolado, corresponde a uma consulta com contexto e escreve no banco quando termina.

Requisitos que continuam valendo em toda execução, mesmo sob demanda: idempotência e retomada, log em arquivo, SQLite nunca compartilhado entre processos, desenvolvimento sempre em cópia (`agente_nw copiar-banco`) — o banco real só é tocado por operação autorizada por Sidarta.

A coleta de notícias é resiliente a bloqueio (brief 045): host que responde 429/503 fica em cooldown no banco (`coleta.cooldown_bloqueio_minutos`) e não recebe pedido nem em outro pedido nem depois de reiniciar; cada pedido faz poucas buscas (`coleta.max_consultas_por_pedido`), reaproveita termo buscado há pouco (`coleta.horas_reuso_termo`) e, com o Google bloqueado, cai no Bing News RSS (`coleta/rss/fonte_alternativa.py`, sem chave). Sem notícia nenhuma o pedido conclui com ganchos das publicações e dos temas, e a tela diz de onde vieram as notícias.

A leitura das listas do usuário nas redes (conexões, seguidos, amigos) é sob demanda e com cache local; nunca periódica. A extensão nunca abre mais de uma aba de rede social por vez, respeita `extensao.pausa_entre_paginas_s` entre páginas da mesma rede e só lê (abrir, rolar, ler texto e links): nenhuma ação na rede além disso.

**Nunca rodam sozinhos:** leitura de rede social, alteração de ficha de contato, operação no banco real.

O gate roda dentro do `scripts/agente_entregar.sh`, pelo executor. Teste direcionado (`pytest tests/test_x.py`) também é do executor. Testes que chamam o Ollama real levam o marcador `llm_real` e ficam fora do gate.

## 7. Comportamento do software

O usuário escreve um pedido em texto livre sobre uma pessoa ou um grupo e um objetivo. O sistema extrai quem, o quê, como e em que registro; reconhece ou cria o contato; decide sozinho o que buscar na notícia; localiza a pessoa nas redes do usuário com confirmação quando há dúvida; lê o que estiver disponível; seleciona assuntos e **redige o conteúdo**: sempre uma mensagem base nascida do objetivo e da pessoa (com uma peculiaridade dela) e, havendo notícia ligada ao pedido, ganchos de notícia adicionais (brief 047), tudo no registro da relação. Nenhum cadastro é pré-requisito: contato, perfil do usuário, temas, tags e fatos são criados e mantidos pelo sistema; o usuário corrige em texto e pode comentar cada mensagem e anotar o contato; a nota vira contexto da próxima redação (brief 050). Não existe envio de mensagem. A interface principal é a tela única do console (brief 039): o usuário escreve a frase, confirma a pessoa quando perguntado, recebe os ganchos, marca "usei" ou "não serve" e corrige em texto livre; as telas antigas (contatos, menu, temas, eu) ficam em "bastidores". O pedido roda em segundo plano, uma tarefa por vez, com `pedido.status` e `pedido.etapa`. Nunca rodam sozinhos: leitura de rede social, alteração de ficha de contato.

## 8. Relatório final obrigatório

Todo brief termina com este bloco preenchido, escrito no relatório do brief, `docs/docs/doc_<NNN>_<slug>_<data>.md`, e não na resposta da conversa. Sem ele, a sessão é considerada incompleta. A resposta final da sessão tem três linhas: o caminho do relatório, uma linha do que foi feito e `Nada para você.` ou só o que exige Sidarta (teste com pessoa real, login em rede social, decisão de produto). Comando para Sidarta digitar só aparece se a entrega parou na terceira falha do gate. Sem saída de comando colada no relatório, não se escreve que algo passou. O relatório termina com a seção `## Lacunas`, uma tabela `# | Lacuna | Destino | Impacto` (destino: `backlog`, `pendência`, `dívida`, `decisão` ou `nenhum`; sem lacunas: `Sem lacunas.`). O executor não copia lacunas para o `docs/PLAN.md` à mão: o `scripts/agente_entregar.sh` roda `scripts/agente_lacunas.py` e as leva ao Backlog, às Pendências, às Dívidas ou às Decisões em aberto.

Pendência só pode ser (a) decisão de produto, que cabe a Sidarta, ou (b) algo que exige a máquina ou a presença dele — login em rede social, teste com pessoa real, aprovação de limiar. Defeito, inconsistência, limpeza ou verificação que o executor consiga resolver ou rodar sozinho é resolvido antes do relatório, não listado. Quando um critério de aceite depende de rede social ou do modelo real, o executor roda o que está ao seu alcance (por exemplo `agente_nw listas ver --rede instagram --filtro a`) e cola a saída no relatório; o que fica para Sidarta é só o que exige Sidarta.

O executor roda o gate dentro do `scripts/agente_entregar.sh`, que só commita com ruff, mypy e pytest verdes, e cola no relatório a saída dos comandos. Se o gate falhar, corrige a causa e entrega de novo, no máximo 3 vezes; na terceira falha, para e descreve no relatório o que falhou.

```
## RELATÓRIO FINAL
- Brief executado:
- Arquivos criados:
- Arquivos alterados (com resumo da mudança em uma linha cada):
- Arquivos preservados literalmente na área afetada:
- Script de verificação (o gate, rodado pelo `scripts/agente_entregar.sh`; saída colada):
- Comandos executados:
- Manifesto do commit (`logs/arquivos_<NNN>.txt` e `logs/commit_<NNN>.txt`, conteúdo colado):
- Pendências e decisões que ficaram abertas:
- Resumo, Doing, Backlog e Done do `docs/PLAN.md` atualizados: sim/não
```

## 9. Certificação

Uma tarefa só está certificada quando: o gate fica verde dentro do `scripts/agente_entregar.sh` (commit e push feitos), escopo respeitado (nada além do brief), relatório final completo e Resumo, Doing, Backlog e Done do `docs/PLAN.md` atualizados. Auditoria independente em doze passes é aplicada ao fim de cada fase de implementação, com validação cruzada em outro modelo.

## 10. Briefs e numeração

- Briefs e DOCs seguem uma única sequência numérica. O próximo número é o maior encontrado em `docs/briefs/` e `docs/docs/`, mais um.
- Todo brief escrito no Projeto é gravado em `docs/briefs/` antes de ser executado. O executor não executa brief que não esteja no disco.
- O cabeçalho do brief segue `docs/briefs/_modelo.md`: Conjunto, Arquivos-alvo, Seções a ler, Modelo, Teste de aceite.
- Havendo teste de aceite, o executor cria o teste antes do código.
- Não editar este arquivo, regra ou skill numa sessão de execução, salvo quando o brief tiver esse arquivo como alvo.
- Todo brief é executado com `/executar <NNN>`.
