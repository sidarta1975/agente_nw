# Brief 083 — Fim da perda silenciosa de texto na coleta

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Conjunto:** auditoria do texto por inteiro (080 a 083)
**Arquivos-alvo:** `agente_nw/coleta/capturas/navegador.py` (`_extrair_blocos`), `agente_nw/coleta/capturas/extensao_backend.py`, `extensao/conteudo.js` (e `extensao/background.js` se repassar o texto), `agente_nw/coleta/rss/ruido.py` (`e_ruido`), `agente_nw/coleta/rss/leitor.py` (item sem corpo), os pontos que montam cartão e qualificação (só para ignorar item sem corpo), `tests/test_coleta_sem_perda_silenciosa.py` (novo), mais o relatório, o manifesto e o PLAN
**Seções a ler:** relatório 079, pontos P-003, P-004, P-013, P-014; PLAN: armadilhas da coleta de redes sociais e da extensão; brief 044 (extensão do Chrome); `coleta/whatsapp/conversa.py` (`_em_blocos`, como modelo de partir sem perder)
**Modelo:** Opus — toca o JavaScript da extensão e a coleta de rede social; um engano aqui perde dado ou quebra a leitura
**Esforço:** médio
**Teste de aceite:** `tests/test_coleta_sem_perda_silenciosa.py`
**Depende de:** brief 079 executado. Independente dos outros da série.
**Ordem em série:** livre
**Data:** 2026-11-08

---

## 1. Objetivo em uma frase

Nenhum texto some da coleta sem deixar rastro: o post longo é lido em pedaços, o corte feito dentro do Chrome é avisado, o item sem corpo não é julgado pela manchete e o filtro de patrocinado olha o texto todo.

## 2. Decisões (de Sidarta, já tomadas)

**2.1. Bloco grande é partido, não descartado (P-014).** Blocos acima de 5.000 caracteres são divididos em pedaços de, no máximo, 5.000, **cortando em fim de parágrafo, ou de frase se não houver parágrafo, ou de palavra em último caso**, nunca no meio de uma palavra, e **nenhum caractere se perde** (a concatenação dos pedaços reproduz o bloco). O piso de 30 caracteres (menu, rótulo) fica. O resumo da leitura passa a contar quantos blocos foram partidos.

**2.2. O corte de 200.000 caracteres dentro do Chrome não muda de número, mas deixa de ser silencioso (P-013).** A extensão devolve também o tamanho original e se cortou; o programa registra uma linha de aviso em `chamadas_llm.jsonl` (padrão do brief 077) e mostra no resumo da leitura "página cortada em 200.000 de N caracteres". O corte do lado do programa (`extensao_backend.py`, mesmo teto) recebe o mesmo tratamento.

**2.3. Item sem corpo não é julgado pela manchete (P-003).** Quando a extração do corpo falha, o item continua gravado (a manchete serve para contar e para o usuário ver), mas fica **marcado como sem corpo** — usando o que o esquema já permitir (por exemplo, corpo nulo); só se não houver como distinguir, uma coluna nova com migração segundo a convenção do projeto — e **não alimenta cartão, qualificação nem gancho**. O agrupamento por vetor de manchete **não muda** neste brief (ele é tratado na série futura sobre o corpo da notícia). O resumo da coleta passa a dizer quantos itens ficaram só com manchete. O corte do teaser mínimo de 400 caracteres (P-003, segunda parte) continua como está e aguarda decisão separada.

**2.4. O filtro de patrocinado olha o texto todo (P-004).** As marcas de `_TERMOS_PATROCINADO` passam a ser procuradas em **todas as linhas** do corpo, mas uma marca só vale quando aparece numa linha **curta (até 80 caracteres)** — o formato de uma declaração ("Publicidade", "Conteúdo patrocinado", "Patrocinado por X"). Assim a palavra "publicidade" no meio de uma reportagem sobre o setor não derruba uma notícia boa, e um aviso no rodapé deixa de passar.

## 3. Escopo (arquivos)

| Arquivo | O que muda |
|---|---|
| `coleta/capturas/navegador.py` | 2.1. |
| `extensao/conteudo.js`, `extensao/background.js` (se preciso), `coleta/capturas/extensao_backend.py`, contrato em `nucleo/modelos/configuracao.py` só se for obrigatório | 2.2. |
| `coleta/rss/ruido.py` | 2.4. |
| `coleta/rss/leitor.py` e pontos de cartão/qualificação | 2.3. |
| `tests/test_coleta_sem_perda_silenciosa.py` | Seção 4. |

## 4. Testes

1. Bloco de 12.000 caracteres vira 3 pedaços ≤ 5.000; a concatenação é idêntica; nenhum pedaço termina no meio de uma palavra; bloco de 20 caracteres continua descartado; o resumo conta 1 bloco partido.
2. Resposta da extensão com `cortado: true` e tamanho original 350.000 → linha no `chamadas_llm.jsonl` e menção no resumo; com `cortado: false` → nada.
3. Texto com a linha "Publicidade" no rodapé (linha 40 de 50) → ruído; texto com "a publicidade infantil cresceu" no meio de um parágrafo longo → **não** é ruído; "Conteúdo patrocinado" na primeira linha continua sendo ruído (regressão).
4. Item cujo corpo falhou: gravado, marcado, e **não** aparece na lista de itens do cartão nem na qualificação; o resumo da coleta o conta.
5. Se a extensão tiver teste JavaScript no projeto, um caso novo para o retorno com `cortado`; se não tiver, o executor registra "sem teste JS no projeto" nas Lacunas e testa o lado Python com a resposta simulada.

Testes que usam banco usam `conexao.abrir(tmp_path/...)`, nunca o banco real.

## 5. Fora de escopo

O vetor de manchete do item sem corpo; o teaser mínimo de 400; o teto de 5.000 como filtro de menu além do piso; subir ou baixar 200.000; qualquer leitura real de rede social (o executor não lê rede social).

## 6. Passos de execução

1. Conferir "Depende de". 2. Ler os arquivos-alvo inteiros; 3. testes; 4. implementar; 5. relatório `doc_083_...` com tabela `Ponto do 079 | O que mudou | Teste`; atualizar no relatório 079 os pontos P-003 (primeira parte), P-004, P-013 e P-014 para `CORRIGIDO (brief 083)`; 6. manifesto, PLAN; `scripts/agente_entregar.sh 083`; 7. três linhas finais. Mudança de JavaScript não testável aqui vai para "Para você: recarregar a extensão no Chrome e abrir uma página longa" se o executor não puder provar de outra forma.

## 7. Critérios de aceite

1. `pytest tests/test_coleta_sem_perda_silenciosa.py -q` verde, saída colada.
2. Gate do `agente_entregar.sh` verde.
3. Verificador do 079 devolve 0.
4. `git diff --stat` mostra só os arquivos do escopo.
