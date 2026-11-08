# Brief 061 — Conversas do WhatsApp como fonte sobre a pessoa

**Repositório:** `/Users/sidarta48/github/agente_nw`
**Conjunto:** nenhum (brief isolado, direto na `main`)
**Arquivos-alvo:** `agente_nw/coleta/whatsapp/__init__.py`, `agente_nw/coleta/whatsapp/leitor.py`, `agente_nw/coleta/whatsapp/importador.py` (novos), `scripts/migracoes/015_conversa_whatsapp.sql` (nova), `agente_nw/nucleo/database/queries/conversa.py` (novo), `agente_nw/nucleo/modelos/configuracao.py` (bloco `WhatsappLimiares`), `config/limiares.yaml` (bloco `whatsapp`), `agente_nw/console/app.py`, `agente_nw/console/templates/pessoa.html`, `agente_nw/console/templates/whatsapp_confirmar.html` (novo), `agente_nw/nucleo/redacao.py`, `tests/fixtures/whatsapp_ios.txt`, `tests/fixtures/whatsapp_android.txt`, `tests/fixtures/whatsapp_ios.zip` (novos, com conversa inventada), `tests/test_whatsapp_leitor.py`, `tests/test_whatsapp_importador.py`, `tests/test_whatsapp_no_prompt.py` (novos), `docs/docs/doc_061_conversas_whatsapp_2026-10-25.md`, `logs/commit_061.txt`, `logs/arquivos_061.txt`
**Seções a ler:** ARQUITETURA §3 (contratos de dados), §8 (camada de LLM), §12 (banco); `perfil/extrator.py` e `nucleo/database/queries/fila_extracao.py` inteiros; em `nucleo/redacao.py`, o bloco HISTÓRICO e o corte por orçamento (brief 050)
**Modelo:** Opus: leitor de formato variável, migração e mudança no prompt de redação
**Teste de aceite:** `tests/test_whatsapp_leitor.py` e `tests/test_whatsapp_importador.py`
**Depende de:** brief 060
**Data:** 2026-10-25

---

## 1. Objetivo em uma frase

Na página da pessoa, Sidarta envia a conversa que exportou do WhatsApp (o `.zip` como veio, ou o `.txt`). O sistema guarda as mensagens, tira delas os fatos sobre a pessoa e usa as trocas recentes para acertar o tom da próxima mensagem. Isso serve sobretudo para quem não tem rede social.

---

## 2. Decisões de Sidarta (25/10)

- A conversa do WhatsApp entra como fonte, ao lado das redes sociais e do "contar algo".
- O arquivo pode ser o `.zip` exportado, sem abrir, ou o `.txt` de dentro dele. Uma pessoa pode ter mais de uma exportação: Sidarta tem duas para o mesmo amigo, e as duas entram sem duplicar mensagem.
- Tudo fica no Mac: o modelo é o Ollama local, e o arquivo enviado não é guardado; só o texto das mensagens vai para o banco.

---

## 3. Como fica

**3.1. Envio (página da pessoa).** Um bloco novo, "Conversas do WhatsApp", com um campo de arquivo que aceita vários arquivos `.zip` ou `.txt` (`multiple`, até 20 MB cada) e o botão "Enviar".
- O `.zip` é lido na memória (`zipfile`). Dentro dele, o leitor usa o `.txt` da conversa (`_chat.txt` no iPhone; no Android, o `.txt` com o nome da conversa). Fotos, áudios e outros arquivos do zip são ignorados.
- Nada do arquivo é gravado em disco.

**3.2. Leitor (`coleta/whatsapp/leitor.py`), função pura, sem banco nem LLM.** Reconhece os dois formatos em português do Brasil:
- iPhone: `[25/10/2026, 14:03:12] Nome: texto`
- Android: `25/10/2026 14:03 - Nome: texto`

Também precisa lidar com:
- variações de ano com dois dígitos e de segundos;
- o caractere invisível de direção (`‎`) que o iPhone coloca no começo das linhas;
- mensagens de várias linhas: linha sem data emendada à mensagem anterior.

Descarta:
- avisos do sistema (criptografia, "mudou o número", ligações);
- `<Mídia oculta>`, "imagem ocultada", "áudio omitido", "figurinha omitida";
- "Mensagem apagada" / "Esta mensagem foi apagada".

Devolve os participantes e a lista de mensagens: autor, data e hora, texto literal.

**3.3. Quem é quem (`whatsapp_confirmar.html`).** Depois do envio, uma página de confirmação mostra:
- os participantes encontrados;
- a quantidade de mensagens;
- o período, da primeira à última data.

Com exatamente dois participantes, o sistema já marca como "você" o que bate com o nome do usuário (tela "eu") e como contato o outro, e Sidarta só confirma. Se nenhum nome bater, a página pergunta "Qual destes é você?". Conversa com mais de dois participantes (grupo) é recusada com a mensagem "Por enquanto só conversa individual".

O conteúdo lido fica guardado só até a confirmação: em memória, no processo do console, com um identificador temporário. Fechar o console descarta.

**3.4. Banco (migração 015).** Tabela `conversa_mensagem`:
- `id`, `perfil_id`, `autor` (`contato` ou `usuario`), `enviada_em`, `texto`, `hash`, `importada_em`;
- `UNIQUE(perfil_id, hash)`, com `hash` = autor + data e hora + texto sem espaços repetidos.

Reenviar a mesma exportação, ou uma mais nova que repete as antigas, não duplica nada. A confirmação termina com "N mensagens novas, M já estavam". Apagar ou unir contato leva as mensagens junto, como já é feito com as notas (brief 050). O texto é gravado como veio (AGENTS §4).

**3.5. Fatos.** As mensagens **do contato**, nunca as de Sidarta, entram na fila de extração existente (`fila_extracao`, contrato `extrair_de_texto`):
- agrupadas por mês, do mais recente para o mais antigo;
- no máximo `whatsapp.meses_extraidos` meses (padrão 24);
- cada bloco com até `whatsapp.maximo_caracteres_bloco` caracteres (padrão 6000);
- origem `whatsapp:AAAA-MM`.

O fato fica com a data do mês. Assim a regra do fato antigo (marcação `[antigo]`, brief 046) vale sozinha.

O processamento roda em segundo plano, na `FilaDeTrabalho` que já existe, uma tarefa por vez, porque podem ser dezenas de chamadas ao modelo. A página da pessoa mostra "processando conversa… (x de y blocos)" e, ao fim, os fatos novos. Mês que já foi extraído não é extraído de novo.

**3.6. Tom da relação na redação.** Em `redacao.py`, o bloco HISTÓRICO passa a incluir as últimas `whatsapp.trocas_no_prompt` (padrão 10) mensagens trocadas com a pessoa, em ordem e com autor ("você" / nome), sob o título "Conversa recente no WhatsApp (para o tom; não é fato atual)". No corte por orçamento, esse bloco **sai antes** das notas do usuário, que continuam protegidas.

**3.7. Limiares.** Os três valores (`meses_extraidos`, `maximo_caracteres_bloco`, `trocas_no_prompt`) ficam em `config/limiares.yaml`, com o modelo Pydantic correspondente. Nenhum número fica no código.

---

## 4. Testes (escritos antes do código)

As fixtures são uma conversa inventada; nada de dado real no repositório.

- `tests/test_whatsapp_leitor.py`:
  - formato iPhone, Android, ano com dois dígitos;
  - mensagem de várias linhas;
  - descarte de mídia, aviso do sistema e mensagem apagada;
  - o `‎`;
  - `.zip` com `_chat.txt` e uma foto → só o texto;
  - grupo → participantes acima de dois.
- `tests/test_whatsapp_importador.py`:
  - importar → mensagens gravadas;
  - importar de novo → "0 novas";
  - importação sobreposta → só as novas;
  - só mensagens do contato vão para a fila;
  - agrupamento por mês e limite de meses;
  - unir contato leva as mensagens.
- `tests/test_whatsapp_no_prompt.py`:
  - as 10 últimas trocas aparecem no HISTÓRICO;
  - perto do limite de tokens, a conversa sai antes das notas.
- O LLM é sempre simulado.

---

## 5. Fora de escopo

Descrever as fotos da conversa; transcrever áudio; conversa de grupo; ler o WhatsApp direto do celular ou do WhatsApp Desktop; enviar mensagem.

---

## 6. Passos e aceite

Executar com `/executar 061`. Aceite: testes da seção 4 verdes, gate verde, commit e push pelo executor.

Pendência para Sidarta na resposta final:
1. Na página do amigo, enviar as duas exportações.
2. Conferir na confirmação que "você" e o amigo estão certos e que a segunda exportação não duplicou.
3. Depois que os fatos aparecerem, fazer um pedido para ele.
