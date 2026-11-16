# DOC 091: redação e busca do "evitar" com os fatos e os itens inteiros

**Brief:** `docs/briefs/brief_091_redacao_e_busca_do_evitar_2026-11-08.md`
**Data:** 2026-11-16
**Depende de:** 081 (concluído, `4f0dc51`; conferido no `git log` e no `docs/docs/doc_081_*` antes de começar).

## 1. O que mudou

- **Fatos inteiros na redação** (2.1). `redacao._fatos` e `_escolher_fatos` deixaram de cortar o fato em 600 caracteres: o fato vai inteiro ao prompt e ao embedding que o escolhe. Se o prompt passa do orçamento, `redigir_ganchos.cortar_por_tamanho` fica com os **4** fatos mais recentes (eram 5), inteiros e em ordem de data (da mais nova para a mais antiga; sem data na linha, vale a ordem recebida). O que sai é devolvido por `redigir_ganchos.fatos_nao_incluidos` e `redacao.redigir` o escreve no `aviso` da redação ("N fato(s) não incluído(s) na redação por tamanho do prompt: ..."), nunca em silêncio. `VERSAO` do prompt: `2026-11-16-1`.
- **`termos_do_contato`** (2.2): o corte de 300 caracteres (`_CARACTERES_POR_FATO`) saiu; cada fato vai inteiro.
- **`termo_evitado`** (2.3): ganhou o parâmetro opcional `conexao`; com ele procura o termo no título e no resumo do assunto **e** na manchete (título) e no resumo gravado (brief 090) de **todos** os itens do assunto. `selecionar_por_consulta` passa a conexão. A regra de decisão é a mesma: achou o termo, o assunto é evitado. Sem a conexão (chamada antiga), o comportamento é o de antes.
- **P-039** (2.4): código não alterado; a lacuna "decisão" está na seção Lacunas e o PLAN a recebe do `agente_entregar.sh`.

Fora da lista de arquivos-alvo, por consequência direta do item 2.1 (declarado aqui, como nos briefs 088 e 089):

- `agente_nw/nucleo/redacao.py`: o corte de 600 caracteres dos fatos vive aqui, não em `redigir_ganchos.py`; sem editá-lo o fato continuaria cortado. Mais o aviso dos fatos não incluídos.
- `tests/test_redacao_prompt.py`: **uma asserção antiga editada**, porque a decisão 2.1 muda o corte de 5 para 4 fatos (`fato 4:`/`fato 5:` virou `fato 3:`/`fato 4:`; o nome do teste, de "cinco" para "quatro").
- `docs/docs/doc_079_*.md`: tabela de certificação (linhas dos cinco arquivos tocados e linha nova do teste novo), apêndice A (linhas renumeradas pela correspondência entre a versão anterior e a atual, mais o bloco "Brief 091") e o estado de P-012, P-026 e P-027 em `CORRIGIDO (brief 091)`, conforme a autorização do cabeçalho do brief. Nenhum ponto novo.

## 2. Algum texto é analisado só em parte? (AGENTS §4), por ponto tocado

| Ponto | Resposta | Prova |
|---|---|---|
| fatos na redação (`redacao._fatos`, P-026) | **Não quanto ao tamanho do fato** (inteiro). **Sim quanto à quantidade:** 10 de 40 candidatos (4 por recência, 6 por semelhança) e, no corte por tamanho, os 4 mais recentes, com o que ficou fora listado no aviso. O teto de 10 de 40 não foi tocado e segue sem aprovação (lacuna 2). | `test_fato_de_3000_caracteres_chega_inteiro_ao_prompt`, `test_excesso_de_fatos_mantem_os_4_mais_recentes_e_lista_o_resto` |
| termos de busca do contato (`termos_do_contato`, P-027) | **Não quanto ao tamanho do fato** (inteiro). **Sim quanto à quantidade:** 12 de 30 fatos, não tocado (lacuna 2). | `test_fato_de_1000_caracteres_vai_inteiro_aos_termos_do_contato` |
| `termo_evitado` (P-012) | **Não.** Procura em título e resumo do assunto e em manchete e resumo de todos os itens do assunto. O **corpo** do item não é procurado (a proposta do P-012 era "o meio": título, resumo e manchetes). O item sem resumo gravado entra só pela manchete (lacuna 3). | `test_termo_so_na_manchete_do_nono_item_e_encontrado`, `test_termo_so_no_resumo_de_um_item_e_encontrado` |
| manchetes do assunto na redação (`_assunto_para_redacao`, P-031; não tocado) | **Sim:** 3 itens por assunto, só a manchete. Fora do escopo do brief (lacuna 2). | — |

## 3. Aceite

(1) `pytest tests/test_evitar_e_fatos_inteiros.py -q` verde (saída abaixo).
(2) `grep` sem corte fixo restante nos três pontos:

```
$ grep -nE "\[:(300|600)\]|_CARACTERES_POR_FATO|_TRECHO_DO_FATO" agente_nw/nucleo/redacao.py agente_nw/nucleo/termos_contato.py agente_nw/nucleo/relevancia/candidatos.py agente_nw/nucleo/prompts/redigir_ganchos.py
(sem saída; código 1)
```

(3) gate verde dentro do `scripts/agente_entregar.sh` (saída na seção 5).

## 4. Saída dos comandos

```
$ .venv/bin/pytest tests/test_evitar_e_fatos_inteiros.py -q
........                                                                 [100%]
8 passed in 0.74s

$ .venv/bin/python scripts/verificar_auditoria_texto.py
334 arquivos, 278 certificados, 49 cortam, 7 não analíticos, 0 não conferidos, 6 ponto(s) aguardando decisão de Sidarta
1760 ocorrência(s) da varredura mecânica, todas com destino no relatório
```

## 5. RELATÓRIO FINAL

- Brief executado: 091
- Arquivos criados: `tests/test_evitar_e_fatos_inteiros.py` (8 testes: os 5 do brief, mais ordem por data, termo só no resumo do item e regra antiga sem conexão); este relatório.
- Arquivos alterados:
  - `agente_nw/nucleo/prompts/redigir_ganchos.py`: 4 fatos mais recentes no corte, em ordem de data; `fatos_nao_incluidos`; `VERSAO` 2026-11-16-1.
  - `agente_nw/nucleo/redacao.py`: fato inteiro no prompt e no embedding; aviso dos fatos não incluídos.
  - `agente_nw/nucleo/termos_contato.py`: sem o corte de 300 caracteres.
  - `agente_nw/nucleo/relevancia/candidatos.py`: `termo_evitado` olha todos os itens do assunto (parâmetro `conexao`).
  - `tests/test_redacao_prompt.py`: asserção 5 → 4 fatos (consequência da decisão 2.1).
  - `docs/docs/doc_079_*.md`: tabela, apêndice A e estado de P-012, P-026 e P-027.
  - `docs/PLAN_agente_nw.md`: Resumo, Doing e Done.
- Arquivos preservados literalmente na área afetada: `cruzamento.py` (P-039), `historico.py`, `llm.py`, `config/`, os prompts de cartão e qualificação, `queries/itens.py` e `queries/fatos.py`.
- Script de verificação (o gate, saída do `scripts/verificar.sh` rodado antes da entrega; o `agente_entregar.sh` o roda de novo e decide):

```
ruff check: ok
ruff format: ok
mypy: ok
pytest: ok (1250 passed, 5 deselected in 50.61s)
```

- Comandos executados: `pytest` direcionado, `scripts/verificar_auditoria_texto.py`, `scripts/verificar.sh`, `grep` do aceite. Nenhum comando tocou o Ollama (os testes usam cliente falso), então o `porteiro` não foi consultado; nenhum comando tocou `agente.db` nem rede social.
- Manifesto do commit: `logs/commit_091.txt` e `logs/arquivos_091.txt` (conteúdo na entrega).
- Pendências e decisões que ficaram abertas: a decisão do número 5 (P-039); ver Lacunas.
- Resumo, Doing, Backlog e Done do `docs/PLAN_agente_nw.md` atualizados: sim (Backlog e Decisões em aberto recebem as lacunas pelo `agente_entregar.sh`).

Para você: decidir se o número 5 de `interessa` continua sendo o desejado (lacuna 1).

## Lacunas

| # | Lacuna | Destino | Impacto |
|---|---|---|---|
| 1 | P-039 (ponto de apoio com 5 interesses): registrado como inalterado e redundante enquanto `interessa` for 5 por contrato (2.4). O número 5 continua sendo o desejado? | decisão | nice |
| 2 | Continuam parciais, fora do que o brief mandou mudar: 10 de 40 fatos candidatos na redação (P-026), 12 de 30 fatos nos termos de busca (P-027) e 3 itens por assunto, só com a manchete, no prompt da redação (P-031). Nenhum desses tetos tem aprovação em `docs/EXCECOES_TEXTO_INTEGRAL.md` | backlog | degrada |
| 3 | `termo_evitado` usa o resumo do item só quando ele existe (brief 090 grava o resumo; item coletado antes e ainda sem resumo entra pela manchete apenas). Um termo que só aparece no corpo desse item passa o filtro até o resumo ser gerado | dívida | nice |
| 4 | Os fatos não incluídos por tamanho ficam no `aviso` da redação, não no `chamadas_llm.jsonl`: gravar ali exigiria mexer em `nucleo/llm.py`, que não é alvo deste brief | backlog | nice |
| 5 | Ganchos já gravados continuam como estavam (fatos de 600 caracteres, `evitar` antigo); regravar é do brief 095 e depende de Sidarta | nenhum | nice |
