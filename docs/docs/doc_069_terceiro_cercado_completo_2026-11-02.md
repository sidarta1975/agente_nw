# DOC 069 — o resto do dado de terceiro em `redigir_ganchos` também entra cercado (relatório do brief 069)

## RELATÓRIO FINAL
- Brief executado: 069. Dependência: brief 068 (`ea66368`), conferida com `git log`.
- Arquivos criados: este relatório, `logs/commit_069.txt`, `logs/arquivos_069.txt`.
- Arquivos alterados (uma linha cada):
  - `agente_nw/nucleo/prompts/redigir_ganchos.py`: `cabecalho_rede`, `fatos` (um bloco só), `por_que` e o bloco inteiro de `entrada.historico` passam por `cercar_dado_externo`; `tem_dado_externo` considera `_bloco_para_quem`; `VERSAO` de `2026-11-02-2` para `2026-11-02-3` (convenção do brief 066: o texto do prompt mudou).
  - `tests/test_seguranca_prompt.py`: 8 casos novos (seção 4 do brief) e um ajuste no caso do 068.
- Arquivos preservados literalmente na área afetada: `seguranca.py`, `historico.py`, os outros oito módulos de prompt, `contato_ficha`, `vinculo`, `tempo_sem_contato`, `contexto_relacao`, rótulos fixos, `notas`.
- Script de verificação: `scripts/verificar.sh`, pelo `scripts/agente_entregar.sh`.
- Manifesto: `logs/arquivos_069.txt` (2 arquivos), `logs/commit_069.txt`.
- Resumo, Doing, Backlog e Done do `docs/PLAN.md` atualizados: sim; a decisão [068-1] saiu de Decisões em aberto, porque este brief a resolve.

## Decisões do executor

- **`fatos` num bloco só:** um par de marcadores para todos os fatos (`- fato` por linha dentro do cerco).
- **Instrução antes de "PARA QUEM":** com `cabecalho_rede` ou `fatos` cercados, o primeiro bloco cercado passou a estar em "PARA QUEM", que vem antes do lugar onde `INSTRUCAO_DADO_EXTERNO` ficava. Movi a instrução para logo antes de "PARA QUEM" (quando há dado externo), mantendo a regra do 068 de ela vir uma vez só e antes do primeiro bloco cercado. O brief não pedia a mudança de posição; sem ela a regra do 068 era violada.
- **Caso do 068 ajustado:** `test_redigir_ganchos_cerca_noticia_e_whatsapp_mas_nao_a_nota_do_usuario` contava 4 pares; com o `por_que` cercado são 5 (título, por que, resumo, manchetes, conversa). Troquei o número e o comentário; a asserção da nota do usuário fora do cerco não mudou.

## Conferências

```
$ grep -n "cercar_dado_externo" agente_nw/nucleo/prompts/redigir_ganchos.py
118  _bloco_para_quem: cabecalho_rede
122  _bloco_para_quem: fatos
145  _bloco_historico: conversa do WhatsApp (068)
156  _bloco_historico: entrada.historico
181  _bloco_assuntos: título (068)
182  _bloco_assuntos: por_que
184  _bloco_assuntos: resumo (068)
187  _bloco_assuntos: manchetes (068)

$ pytest tests/test_seguranca_prompt.py tests/test_proveniencia.py -q
33 passed in 1.45s
```

## Lacunas

Sem lacunas.
