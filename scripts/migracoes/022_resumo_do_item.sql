-- 022_resumo_do_item — brief 090: resumo guardado por item e cobertura do cartão.
--
-- `item.resumo`: o que o cartão e a qualificação leem de cada item, no lugar dos 300 primeiros caracteres.
-- É feito com o texto inteiro (em partes que cobrem tudo quando o texto não cabe numa chamada,
-- `nucleo/texto_integral.py`). `resumo_versao` é a versão da regra (`prompts/cartao.py::VERSAO_RESUMO_ITEM`):
-- resumo de outra versão é refeito antes de ser usado. `resumo_partes`: 0 = texto curto, o resumo é o
-- próprio texto, sem chamada ao modelo; 1 = texto inteiro numa chamada; N > 1 = lido em N partes.
-- `resumo_modelo`/`resumo_perfil`: proveniência (brief 066), nulos quando o resumo é o próprio texto.
-- NULL em tudo = item ainda sem resumo.
--
-- `assunto.cartao_versao`: versão do prompt que gerou o cartão. NULL = cartão gravado antes deste brief,
-- que continua válido até a regravação autorizada pelo dono (brief 095). A coluna `gerado_por_prompt_versao`
-- (migração 019) não serve para isso: qualificação e cartão escrevem nela, e as duas tinham a mesma versão.
-- `cartao_itens`: quantos itens o cartão cobriu (todos os do assunto com corpo). `cartao_niveis`: 1 = os
-- resumos de todos os itens couberam numa chamada; 2 ou mais = consolidados em níveis antes do cartão.

ALTER TABLE item ADD COLUMN resumo TEXT NULL;
ALTER TABLE item ADD COLUMN resumo_versao TEXT NULL;
ALTER TABLE item ADD COLUMN resumo_partes INTEGER NULL;
ALTER TABLE item ADD COLUMN resumo_modelo TEXT NULL;
ALTER TABLE item ADD COLUMN resumo_perfil TEXT NULL;

ALTER TABLE assunto ADD COLUMN cartao_versao TEXT NULL;
ALTER TABLE assunto ADD COLUMN cartao_itens INTEGER NULL;
ALTER TABLE assunto ADD COLUMN cartao_niveis INTEGER NULL;

INSERT INTO schema_version (versao, aplicada_em) VALUES (22, strftime('%Y-%m-%dT%H:%M:%fZ','now'));
