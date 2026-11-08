# Exceções aprovadas ao princípio do texto por inteiro

Quando o agente_nw **analisa** um texto — notícia, página de rede social, mensagem de WhatsApp,
comentário, histórico, fato, pedido —, ele analisa o texto **inteiro**. "Analisar" quer dizer que o
texto, ou o que sobrou dele, alimenta uma decisão: prompt de LLM, embedding, classificador,
deduplicação, agrupamento, ranqueamento ou filtro.

O princípio só pode ser quebrado com **justificativa aprovada por Sidarta**, registrada aqui. Sem uma
linha nesta tabela, o corte é violação do princípio — ainda que o código tenha um comentário
explicando, ainda que a razão pareça boa e ainda que o executor a tenha proposto.

**Quem escreve aqui é Sidarta** (ou um brief escrito por ele). O executor de brief nunca escreve nesta
tabela, nem marca um ponto como aprovado no relatório de auditoria: o princípio é do dono do projeto,
e quem audita não pode ser quem absolve (brief 079, item 3.1).

A coluna `Ponto` usa o identificador do relatório de auditoria mais recente
(`docs/docs/doc_079_auditoria_texto_por_inteiro_2026-11-08.md`, seção 3). O verificador
(`scripts/verificar_auditoria_texto.py`) só aceita o estado `EXCEÇÃO APROVADA` num ponto quando existe
aqui uma linha com o mesmo identificador e o texto `Aprovado por Sidarta em AAAA-MM-DD`.

| Ponto | Arquivo:função | O que é cortado | Justificativa aprovada | Aprovado por Sidarta em |
|---|---|---|---|---|
