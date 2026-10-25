---
name: executar
description: Executa um brief do agente_nw de ponta a ponta (testes, código, gate, commit, push, relatório). Uso /executar <NNN>.
disable-model-invocation: true
argument-hint: "<NNN>"
---

# /executar $ARGUMENTS

Execute o brief `$ARGUMENTS` sozinho, nesta ordem. Não peça ao usuário para rodar comando nenhum.

1. Abra `docs/briefs/brief_$ARGUMENTS_*.md`. Se não existir no disco, pare e diga isso.
2. Leia o que o AGENTS §1 manda e as seções citadas em "Seções a ler" do brief. Confira a linha "Depende de"; se não estiver satisfeita, pare.
3. Escreva o teste de aceite e os testes do brief **antes** do código.
4. Implemente só nos arquivos-alvo do brief.
5. Rode os testes do brief (`pytest tests/test_x.py -q`) até passarem.
6. Grave, antes de entregar:
   - o relatório `docs/docs/doc_$ARGUMENTS_<slug>_<data>.md`, com o bloco do AGENTS §8 e a saída dos comandos colada;
   - o manifesto: `logs/commit_$ARGUMENTS.txt` (mensagem do commit) e `logs/arquivos_$ARGUMENTS.txt` (um caminho por linha, só o que entra no commit);
   - as linhas Resumo, Doing e Done do `docs/PLAN.md`.
7. Rode `scripts/agente_entregar.sh $ARGUMENTS`. Ele roda o gate, commita só o manifesto e faz o push. Se falhar, corrija a causa e rode de novo, **no máximo 3 vezes**. Na terceira falha, pare e descreva no relatório o que falhou.
8. Termine com três linhas:
   - o caminho do relatório;
   - o que foi feito, com o hash do commit;
   - `Nada para você.` ou só o que exige Sidarta: teste com pessoa real, login em rede social, decisão de produto.

Regras que continuam valendo (a trava `.claude/hooks/guarda_comando.py` as impõe):
- git de escrita só por `scripts/agente_entregar.sh`; nunca `git add -A`;
- nunca o banco real (`agente.db`) nem leitura de rede social (`ler-rede-social`, `listas`, `pedir`, `extensao`);
- comandos de Sidarta não entram na resposta final, exceto quando a entrega parou na terceira falha.
