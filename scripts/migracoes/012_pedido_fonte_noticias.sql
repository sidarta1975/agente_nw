-- 012_pedido_fonte_noticias — brief 045. De onde vieram as notícias de um pedido (google, alternativa,
-- reaproveitada, nenhuma) e, quando o Google estava bloqueado, até quando. A tela e o terminal mostram.

ALTER TABLE pedido ADD COLUMN noticias_fonte TEXT;
ALTER TABLE pedido ADD COLUMN noticias_bloqueado_ate TEXT;

INSERT INTO schema_version (versao, aplicada_em) VALUES (12, strftime('%Y-%m-%dT%H:%M:%fZ','now'));
