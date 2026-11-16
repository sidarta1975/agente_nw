# Brief 100 — As exceções aprovadas em 2026-11-16 e a regra de manutenção da guarda

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Conjunto:** correção do texto por inteiro (segunda rodada, 098 a 100) — este é o último
**Arquivos-alvo:** `docs/EXCECOES_TEXTO_INTEGRAL.md`, `docs/docs/doc_079_auditoria_texto_por_inteiro_2026-11-08.md` (só o estado e a linha de decisão dos pontos aprovados aqui), `AGENTS_agente_nw.md` (§4, a regra do item 2.3 — **este brief tem o AGENTS como alvo, por isso pode editá-lo**), `tests/test_sem_corte_de_texto.py` e a tabela de cortes não analíticos do registro (só os trechos que este brief alterar), mais o relatório, o manifesto e o PLAN
**Seções a ler:** brief 079 (decisões 3.1 e 3.8: quem pode escrever no registro); brief 080 inteiro (o formato das sete colunas do registro, item 2.4); relatório do brief 093 inteiro (as lacunas [093-1] a [093-6] e a guarda do gate); relatório do brief 094 (os pontos novos, para não confundir identificador); o ponto P-039 no relatório 079; `docs/EXCECOES_TEXTO_INTEGRAL.md` inteiro; AGENTS §4 e §10
**Modelo:** Opus — escreve no registro de exceções e no AGENTS, onde errar identificador ou alcance aprova o que Sidarta não aprovou
**Esforço:** alto
**Teste de aceite:** `python scripts/verificar_auditoria_texto.py` devolve 0 e o resumo mostra os pontos aprovados fora da lista de "aguardando"
**Depende de:** briefs 093, 094, 098 e 099 executados (o 098 fecha a condição do P-033 e o 099 tira o corte que Sidarta recusou)
**Ordem em série:** depois de 098 e 099 (último da rodada)
**Data:** 2026-11-16
**Relatório 079 (autorização de Sidarta, 2026-11-16):** este brief pode atualizar a seção 6 (tabela de certificação: linha nova para arquivo que ele criar, contagem de linhas dos que ele alterar) e o apêndice A (destino das ocorrências novas da varredura) do relatório 079, só para os arquivos que ele mesmo criar ou alterar, sem criar ponto novo.
**Guarda do 093 (autorização de Sidarta, 2026-11-16):** este brief pode atualizar as listas de `tests/test_sem_corte_de_texto.py` e a tabela de cortes não analíticos do registro para os trechos que ele mesmo criar ou alterar, sem aprovar exceção nova.

---

## 1. Objetivo em uma frase

Gravar no registro oficial as seis exceções que Sidarta aprovou em 2026-11-16 (e só elas), com o valor e a condição de validade de cada uma, e escrever no AGENTS a regra que deixa cada brief manter a guarda do gate sem aprovar exceção nova.

## 2. Decisões (de Sidarta, 2026-11-16)

**2.1. Este brief é o ato de Sidarta.** A regra do brief 079 (3.1 e 3.8) diz que só ele escreve no registro, "ou um brief dele". Este é esse brief: a aprovação foi dada por escrito na conversa de 2026-11-16, depois dos relatórios dos briefs 093 e 094. O executor **não aprova nada além da tabela de 2.2**; ponto que não está nela continua `AGUARDANDO DECISÃO DE SIDARTA`.

**2.2. Aprovados nesta data, com a condição que mantém cada um válido:**

| O que foi aprovado | Valor aprovado | Condição que mantém a exceção válida |
|---|---|---|
| Página de rede social lida até um teto de caracteres | 200.000 caracteres (valor do código, com arquivo e linha) | Vale enquanto o **aviso do corte continuar visível** para o usuário; se o aviso aparecer com frequência, a exceção é reavaliada. |
| Assuntos por rodada | 40 | Vale porque é o **grupo de candidatos do gate**, não texto cortado: nenhum texto de item deixa de ser lido por causa dele. |
| Histórico da redação | 5 consultas lidas, 3 usadas | Vale enquanto o corte for de **quantas conversas** entram, nunca de caracteres do que o usuário escreveu. |
| Notas e moldes na redação | 5 notas, 2 moldes | A mesma condição: teto de itens, não de caracteres. |
| Termos de busca | 6 | Vale como custo de rede (é o mesmo motivo do P-005, já aprovado em 2026-11-08). |
| P-039, interesses no ponto de apoio da consulta | 5 | Vale enquanto o **contrato do pedido mantiver `interessa` em 5**; se esse número mudar, a exceção cai. |

O executor localiza, para cada linha, o ponto correspondente no relatório 079 (os cinco primeiros vêm das lacunas [093-1] a [093-5]; o último é o P-039) e **confere no código** o valor aprovado, com arquivo e linha, antes de gravar. Se um dos cinco não tiver ponto no relatório 079, ele entra no registro pela descrição e o relatório deste brief diz que ponto não existia — sem inventar identificador.

**2.3. O corte de 100 caracteres da mensagem anterior NÃO foi aprovado.** Sidarta recusou: a mensagem entra inteira, e quem faz isso é o brief 099. Nenhuma linha dele entra no registro; se o executor encontrar esse corte ainda no código, o brief 099 não foi entregue e este brief **para**.

**2.4. Regra nova no AGENTS §4, em uma frase: cada brief pode atualizar as listas de `tests/test_sem_corte_de_texto.py` e a tabela de cortes não analíticos do registro para os trechos que ele mesmo criar ou alterar, sem aprovar exceção nova — aprovar exceção continua sendo só de Sidarta.** *Razão: sem isso, a guarda que o brief 093 pôs no gate pára qualquer brief que toque numa linha já classificada, e o executor não tem como seguir sem decisão de Sidarta a cada linha.*

**2.5. P-018, registrado como decisão tomada:** a descrição de imagem continua em 2 a 5 frases e, **quando houver texto legível na imagem, ele é transcrito inteiro em campo separado**. Este brief só registra a decisão no relatório 079 (no texto do ponto) e no seu próprio relatório; a implementação é brief do segundo conjunto, não deste.

## 3. Escopo (arquivos)

| Arquivo | O que muda |
|---|---|
| `docs/EXCECOES_TEXTO_INTEGRAL.md` | Seis linhas novas, nas sete colunas do brief 080 (item 2.4), cada uma com "Aprovado por Sidarta em 2026-11-16". A linha do P-033 (valor do estimador) já foi atualizada pelo brief 098 e **não** é tocada aqui. |
| `docs/docs/doc_079_...md` | Nos pontos aprovados: estado `EXCEÇÃO APROVADA` e a linha `Decisão de Sidarta: aprovar exceção (2026-11-16), alcance conforme o registro`. No P-018, a decisão de 2.5 no texto do ponto, sem mudar o estado. Os números do resumo acompanham. |
| `AGENTS_agente_nw.md` | §4: a frase de 2.4, nada mais. |
| `tests/test_sem_corte_de_texto.py` e a tabela de cortes não analíticos | Só os trechos que este brief alterar. |

## 4. Testes

Não há código novo. O teste é o verificador, rodado sobre o relatório e o registro alterados: `EXCEÇÃO APROVADA` só vale com a linha correspondente no registro, e é isso que prova que cada aprovação foi gravada direito. Se o verificador reclamar de coerência, corrigir o **relatório e o registro**, não o verificador. Além dele: `pytest tests/test_sem_corte_de_texto.py -q` verde, para a guarda do 093 continuar valendo.

## 5. Fora de escopo

Aprovar qualquer ponto fora da tabela 2.2. Implementar o P-018 (segundo conjunto). Mudar código de produção. Regravar vetor ou cartão. Mexer no verificador.

## 6. Passos de execução

1. Conferir "Depende de", inclusive que `grep -n "\[:100\]" agente_nw/nucleo/historico.py` não devolve nada (2.3). 2. Ler os relatórios 093 e 094 e localizar os pontos das seis linhas. 3. Conferir no código o valor de cada uma, com arquivo e linha. 4. Gravar as seis linhas no registro e atualizar os pontos no relatório 079. 5. A frase do AGENTS §4. 6. Rodar o verificador e `pytest tests/test_sem_corte_de_texto.py -q`, colando as saídas. 7. Relatório `doc_100_...`, manifesto, PLAN; `scripts/agente_entregar.sh 100`. 8. Três linhas finais.

## 7. Critérios de aceite

1. O registro tem seis linhas novas, uma por linha da tabela 2.2, todas com valor aprovado (arquivo e linha), condição preenchida e "Aprovado por Sidarta em 2026-11-16".
2. O verificador devolve 0 e o resumo mostra quantos pontos ainda aguardam decisão, com o número antes e depois colados no relatório.
3. `pytest tests/test_sem_corte_de_texto.py -q` verde.
4. O AGENTS §4 tem a frase de 2.4 e nada mais mudado (`git diff -- AGENTS_agente_nw.md` colado no relatório).
5. Gate verde.
6. O relatório traz a tabela `O que foi aprovado | Ponto do 079 | Arquivo:linha do valor | Condição` das seis, e diz explicitamente que o corte de 100 caracteres **não** foi aprovado e que o brief 099 o removeu.
