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
- Testes: pytest. Tipagem: mypy strict. Lint: ruff. Suíte roda via `scripts/verificar.sh`, sempre por Sidarta no terminal — nunca pelo executor.

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
- **Git nunca roda de forma autônoma.** O executor prepara a lista de arquivos e o texto do commit no relatório final; Sidarta autoriza.
- Remoção de arquivo rastreado: `git rm`, com critérios explícitos e exclusão de `__init__.py`, `.gitkeep` e afins.
- Sidarta roda o git com `scripts/commitar.sh <arquivo_de_mensagem> <arquivos…>`, no terminal ou digitando `!scripts/commitar.sh …` dentro do Claude Code. O executor grava a mensagem do commit em `logs/commit_<NNN>.txt` e lista os arquivos no relatório. Push só por Sidarta.

## 6. Tarefas não assistidas

Não existem. Nenhuma etapa do sistema — coleta RSS, extração, agrupamento, qualificação, cruzamento, cartão, leitura de rede social, geração do menu — roda sem que Sidarta a dispare explicitamente pelo console ou pela CLI. Cada disparo é isolado, corresponde a uma consulta com contexto e escreve no banco quando termina.

Requisitos que continuam valendo em toda execução, mesmo sob demanda: idempotência e retomada, log em arquivo, SQLite nunca compartilhado entre processos, desenvolvimento sempre em cópia (`agente_nw copiar-banco`) — o banco real só é tocado por operação autorizada por Sidarta.

A coleta de notícias é resiliente a bloqueio (brief 045): host que responde 429/503 fica em cooldown no banco (`coleta.cooldown_bloqueio_minutos`) e não recebe pedido nem em outro pedido nem depois de reiniciar; cada pedido faz poucas buscas (`coleta.max_consultas_por_pedido`), reaproveita termo buscado há pouco (`coleta.horas_reuso_termo`) e, com o Google bloqueado, cai no Bing News RSS (`coleta/rss/fonte_alternativa.py`, sem chave). Sem notícia nenhuma o pedido conclui com ganchos das publicações e dos temas, e a tela diz de onde vieram as notícias.

A leitura das listas do usuário nas redes (conexões, seguidos, amigos) é sob demanda e com cache local; nunca periódica. A extensão nunca abre mais de uma aba de rede social por vez, respeita `extensao.pausa_entre_paginas_s` entre páginas da mesma rede e só lê (abrir, rolar, ler texto e links): nenhuma ação na rede além disso.

**Nunca rodam sozinhos:** git, leitura de rede social, alteração de ficha de contato, a suíte de testes padrão (`scripts/verificar.sh`, pytest, ruff, mypy) — o executor escreve e mantém o script; quem roda é Sidarta, no terminal dele.

O gate completo é `scripts/verificar.sh`, digitado por Sidarta no terminal ou com `!scripts/verificar.sh` dentro do Claude Code. O executor nunca o roda, nem em segundo plano.

## 7. Comportamento do software

O usuário escreve um pedido em texto livre sobre uma pessoa ou um grupo e um objetivo. O sistema extrai quem, o quê, como e em que registro; reconhece ou cria o contato; decide sozinho o que buscar na notícia; localiza a pessoa nas redes do usuário com confirmação quando há dúvida; lê o que estiver disponível; seleciona assuntos e **redige o conteúdo**: sempre uma mensagem base nascida do objetivo e da pessoa (com uma peculiaridade dela) e, havendo notícia ligada ao pedido, ganchos de notícia adicionais (brief 047), tudo no registro da relação. Nenhum cadastro é pré-requisito: contato, perfil do usuário, temas, tags e fatos são criados e mantidos pelo sistema; o usuário corrige em texto e pode comentar cada mensagem e anotar o contato; a nota vira contexto da próxima redação (brief 050). Não existe envio de mensagem. A interface principal é a tela única do console (brief 039): o usuário escreve a frase, confirma a pessoa quando perguntado, recebe os ganchos, marca "usei" ou "não serve" e corrige em texto livre; as telas antigas (contatos, menu, temas, eu) ficam em "bastidores". O pedido roda em segundo plano, uma tarefa por vez, com `pedido.status` e `pedido.etapa`. Nunca rodam sozinhos: git, leitura de rede social, alteração de ficha de contato.

## 8. Relatório final obrigatório

Todo brief termina com este bloco preenchido, escrito no relatório do brief, `docs/docs/doc_<NNN>_<slug>_<data>.md`, e não na resposta da conversa. Sem ele, a sessão é considerada incompleta. A resposta final da sessão tem três linhas: o caminho do relatório, uma linha do que foi feito e o comando que Sidarta roda. Sem saída de comando colada no relatório, não se escreve que algo passou.

Pendência só pode ser (a) decisão de produto, que cabe a Sidarta, ou (b) algo que exige a máquina ou a presença dele — login em rede social, teste com pessoa real, aprovação de limiar. Defeito, inconsistência, limpeza ou verificação que o executor consiga resolver ou rodar sozinho é resolvido antes do relatório, não listado. Quando um critério de aceite depende de rede social ou do modelo real, o executor roda o que está ao seu alcance (por exemplo `agente_nw listas ver --rede instagram --filtro a`) e cola a saída no relatório; o que fica para Sidarta é só o que exige Sidarta.

O executor não roda a suíte de testes padrão (pytest, ruff, mypy, `scripts/verificar.sh`) durante a sessão. Ele garante que o script está atualizado e funcional, e entrega no relatório o caminho completo, pronto para colar no terminal — quem roda e confirma o resultado é Sidarta.

```
## RELATÓRIO FINAL
- Brief executado:
- Arquivos criados:
- Arquivos alterados (com resumo da mudança em uma linha cada):
- Arquivos preservados literalmente na área afetada:
- Script de verificação (caminho completo, pronto para colar no terminal):
- Comandos executados:
- Lista de arquivos para `git add` e texto sugerido do commit:
- Pendências e decisões que ficaram abertas:
- Resumo, Doing, Backlog e Done do `docs/PLAN.md` atualizados: sim/não
```

## 9. Certificação

Uma tarefa só está certificada quando: Sidarta roda o script de verificação apresentado no relatório e confirma testes verdes, escopo respeitado (nada além do brief), relatório final completo e Resumo, Doing, Backlog e Done do `docs/PLAN.md` atualizados. Auditoria independente em doze passes é aplicada ao fim de cada fase de implementação, com validação cruzada em outro modelo.

## 10. Briefs e numeração

- Briefs e DOCs seguem uma única sequência numérica. O próximo número é o maior encontrado em `docs/briefs/` e `docs/docs/`, mais um.
- Todo brief escrito no Projeto é gravado em `docs/briefs/` antes de ser executado. O executor não executa brief que não esteja no disco.
- O cabeçalho do brief segue `docs/briefs/_modelo.md`: Conjunto, Arquivos-alvo, Seções a ler, Modelo, Teste de aceite.
- Havendo teste de aceite, o executor cria o teste antes do código.
- Não editar este arquivo, regra ou skill numa sessão de execução, salvo quando o brief tiver esse arquivo como alvo.
