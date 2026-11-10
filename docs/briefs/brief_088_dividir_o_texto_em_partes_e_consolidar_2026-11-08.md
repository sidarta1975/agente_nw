# Brief 088 — Dividir o texto em partes que cobrem tudo e consolidar o resultado

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Conjunto:** correção do texto por inteiro (086 a 095)
**Arquivos-alvo:** `agente_nw/nucleo/texto_integral.py` (novo), `agente_nw/perfil/extrator.py` (`extrair_de_texto`), `agente_nw/coleta/capturas/extrator.py` (`extrair`), os prompts dessas duas tarefas em `agente_nw/nucleo/prompts/` (versão nova), uma migração nova para o registro de cobertura, o cliente de embeddings em `agente_nw/nucleo/llm.py` (função auxiliar `embeddar_em_partes`, sem mexer no que o brief 082 criou), `tests/test_texto_integral.py` (novo), mais o relatório, o manifesto e o PLAN
**Seções a ler:** relatório 079 (pontos de janela) e a seção 7 do relatório do agente_nw em `referencias/relatorios_projetos`; o relatório do sergio (peça única de texto integral, 500 caracteres de sobreposição, `lh_blocos`) e o do trf6 (média ponderada de vetor) na mesma pasta; brief 082 e seu relatório (erro de janela e estimador compartilhado); `nucleo/prompts/redigir_ganchos.py::cortar_por_tamanho`; brief 066 (vetor de outro critério conta como ausente); AGENTS §4 (cerco do dado externo) e §9
**Modelo:** Opus — base usada por várias tarefas; um erro de cobertura volta a esconder texto
**Esforço:** alto
**Teste de aceite:** `tests/test_texto_integral.py`
**Depende de:** briefs 082 e 087 executados (o erro de janela e a fila de revisão já existem)
**Ordem em série:** depois de 082 e 087; antes de 089, 090 e 091
**Data:** 2026-11-08

---

## 1. Objetivo em uma frase

Quando um texto não cabe numa chamada, o projeto o divide em partes consecutivas que somam exatamente o texto todo, processa cada parte e consolida o resultado por uma regra escrita para cada uso — em vez de recusar ou cortar.

## 2. Decisões (de Sidarta, já tomadas; seguem o sergio e o trf6)

**2.1. Uma só peça de divisão, `nucleo/texto_integral.py`.** Texto que cabe vai inteiro, sem marcação. Texto que não cabe é dividido em partes, preferindo fim de parágrafo, depois de linha, de frase e de espaço; só em último caso, no limite exato. **Sobreposição de 500 caracteres** entre partes vizinhas. Cada parte recebe no prompt o aviso "parte K de N de um documento maior" dentro do cerco do dado externo. O orçamento por parte vem do `num_ctx` da tarefa menos a folga do prompt, usando o estimador compartilhado do brief 082. Se o servidor recusar o prompt por tamanho, o orçamento é dividido ao meio, até 4 vezes.

**2.2. Teste de cobertura obrigatório:** reconstruir o texto a partir das partes (descontada a sobreposição) reproduz o original byte a byte, para textos de 1 caractere, vazios, com um só parágrafo gigante, sem espaços, com emoji, e de 34.195 caracteres (o maior item do banco de desenvolvimento).

**2.3. Consolidação por uso (cada uma escrita no docstring da função):**
- **Vetor** (`embeddar_em_partes`): média dos vetores das partes ponderada pelo número de caracteres, normalizada. Falha numa parte invalida o vetor (nunca vetor parcial).
- **`extrair_de_texto` e a extração de captura de rede social:** são listas de fatos; a consolidação é a união ordenada, com remoção de repetição exata e preservação da parte de origem. Parte sem resposta válida invalida o item inteiro (vai para a fila do brief 087). Fatos divergentes entre partes (mesmo campo, valores diferentes, quando o campo é único como "cidade") **não são decididos por voto**: viram aviso e o item fica para revisão humana.

**2.4. Registro de cobertura.** Uma coluna (ou tabela pequena, o executor escolhe depois de ler o esquema) grava, por item processado, em quantas partes foi lido (`1` = inteiro numa chamada; maior que 1 = em partes; vazio = processado antes deste brief) e a versão do processamento. Os prompts das duas tarefas sobem de versão, de modo que a proveniência diferencie o que foi lido por inteiro.

**2.5. O código antigo que cortava falha em voz alta.** Onde `extrair_de_texto` hoje manda `item.texto` sem conferir o tamanho, passa a chamar a divisão. Nenhuma chamada nova deste brief corta texto.

**2.6. Fora de escopo deste brief:** cartão, qualificação, vetor do agrupamento e dos fatos (briefs 089 e 090 usam esta peça); o corte de coleta (083).

## 3. Escopo (arquivos)

| Arquivo | Criar / alterar | O que muda |
|---|---|---|
| `nucleo/texto_integral.py` | criar | `dividir`, `reconstruir`, `consolidar_vetores`, `consolidar_fatos`. |
| `nucleo/llm.py` | alterar | `embeddar_em_partes` (usa `dividir` e o erro de janela do 082). |
| `perfil/extrator.py`, `coleta/capturas/extrator.py`, seus prompts | alterar | Chamam a divisão; versão de prompt nova. |
| migração nova | criar | Registro de cobertura (2.4). |
| `tests/test_texto_integral.py` | criar | Seção 4. |

## 4. Testes (cliente de LLM e de embedding falsos)

1. Cobertura byte a byte (2.2). 2. Texto curto produz **exatamente o mesmo prompt de antes**, caractere por caractere (prova de que nada muda no que já cabia). 3. Marcador único no meio e outro no último caractere de um texto de 300.000 caracteres chegam, cada um, a pelo menos um prompt enviado ao cliente falso. 4. Sobreposição de 500 entre vizinhas; aviso "parte K de N" presente e dentro do cerco. 5. Média ponderada normalizada: vetor de duas partes com pesos 3:1 confere com cálculo manual. 6. Parte inválida invalida o item e ele vai à fila (banco isolado). 7. Fatos iguais em partes vizinhas aparecem uma vez; fato único divergente vira aviso e revisão. 8. Servidor falso que recusa por tamanho: o orçamento cai à metade e o texto ainda é coberto por inteiro. 9. Registro de cobertura grava `1` para texto curto e `N` para texto dividido.

## 5. Fora de escopo

Os briefs 089 (vetores do agrupamento, do contato e do tema), 090 (cartão e qualificação) e 091 (redação); regravar dados antigos (095).

## 6. Passos de execução e critérios de aceite

Passos: conferir "Depende de"; ler o brief 082 e seu relatório; testes; implementar; relatório `doc_088_...` com a resposta a "algum texto é analisado só em parte?" por tarefa tocada (sim/não e prova); manifesto; PLAN; `scripts/agente_entregar.sh 088`. Aceite, com saída colada: (1) `pytest tests/test_texto_integral.py -q` verde; (2) teste 2 (prompt idêntico para texto curto) verde; (3) `grep` sem `item.texto` enviado cru ao modelo em `perfil/extrator.py`; (4) gate verde; (5) verificador do 079 devolve 0, com os pontos tratados atualizados no relatório 079 para `CORRIGIDO (brief 088)`.
