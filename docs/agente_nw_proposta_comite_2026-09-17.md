# agente_nw — Proposta para aprovação do comitê

**Data:** 17 de setembro de 2026
**Repositório:** `/Users/sidarta48/github/agente_nw` — hoje só documentação (`AGENTS.md`, `docs/`); nenhum código escrito
**Restrição vigente:** nenhuma API de modelo de linguagem, paga ou gratuita, em nenhuma das quatro etapas. Assinaturas de Gemini, Claude e GPT entram apenas na Etapa 4, operadas por pessoa.

---

## 1. O que o comitê aprova

Um pacote fechado:

1. O produto descrito na seção 2 e as decisões da seção 3.
2. O modelo de dados e os dois contratos do motor (seção 4), comuns às quatro etapas.
3. As quatro etapas, na ordem e com os critérios de passagem das seções 5 a 9.
4. A restrição de API mantida até nova decisão do comitê.
5. Início imediato da Etapa 1 com brief de execução.

---

## 2. O produto

O agente_nw dá ao usuário repertório para interações sociais mais interessantes e mais produtivas, com qualquer contato — relação pessoal, formal, de rede ou de trabalho. Para cada contato, um menu curto de assuntos do momento, escolhidos porque casam com as características que o usuário atribuiu a si mesmo e àquele contato, cada assunto com uma linha dizendo por quê.

Três regras definem o comportamento e valem em todas as etapas:

- **A relevância vem de classificação declarada.** O usuário atribui características (tags) a si e a cada contato. É esse cruzamento que decide o que é relevante para quem. O sistema não adivinha quem é o contato nem qual é a relação.
- **Lógica aditiva.** O agente trabalha com o que tiver. Contato só com tags: usa as tags. Tags mais sinal vindo de publicações do contato: o sinal soma. Contato sem dado nenhum: o sistema diz "sem assunto para este contato" e segue — não trava, não exige preenchimento prévio.
- **Sinal de rede social é reforço, nunca pré-requisito.** Entra por importação manual de publicações (Etapa 2) ou por análise em assistente pago (Etapa 4). Nenhuma raspagem automática nesta proposta.

O que fica fora, por decisão: escrever mensagem, sugerir tom, pontuar relacionamento, enviar qualquer coisa.

---

## 3. Decisões tomadas

| Decisão | Escolha |
|---|---|
| Produto | Menu de assuntos por contato. Não é lista de temas com "interessa a: Maria", não é gerador de mensagem |
| Origem da relevância | Características declaradas pelo usuário para si e para cada contato |
| Temas | Livres, escritos em linguagem natural. O sistema normaliza para tema com sinônimos e propõe tags novas ao ler texto sobre o contato. Quem classifica é a IA; o usuário confirma com um clique |
| Escala | Base dimensionada para 100 contatos. Menu gerado só para contatos marcados como ativos ou pedidos na hora |
| Hardware da Etapa 1 | Notebook de 8 GB de RAM, sem GPU, Windows, macOS ou Linux. Roda em qualquer máquina acima disso |
| Modelo da Etapa 1 | Qwen3 4B, quantização Q4_K_M, via Ollama (`qwen3:4b`) |
| Embeddings | `multilingual-e5-small` na Etapa 1 (cabe em 8 GB); `bge-m3` a partir de 16 GB na Etapa 2 |
| Interface | Console web local (Flask, `localhost:8765`) com três telas, mais exportação do menu em Markdown para pasta sincronizada |
| Roteamento de modelo | Declarado em `config/llm_routing.yaml`, com um perfil por faixa de hardware. Evoluir de modelo é trocar o perfil, não o código |
| API de LLM | Nenhuma, em nenhuma etapa |
| Dados de terceiros | Ficam no dispositivo. Saem apenas em pacote pseudonimizado, por ação do usuário (Etapa 4) |
| Exemplos de "conversável" | A IA escreve o conjunto inicial de exemplos positivos e negativos; o usuário aprova; o botão "não serve" no menu realimenta |
| Nome do pacote Python | `agente_nw`, igual à pasta. Fecha a decisão aberta nº 3 do `PLAN.md` |
| Origem dos briefs | `docs/briefs/`, fora do git. Fecha a decisão nº 2 |
| `AGENTS.md` no git | Commitado. É regra de executor, não documento de produto, e não contém dado pessoal. Fecha a decisão nº 1 |
| Processamento de importações | Em fila, na rodada seguinte, com botão "processar agora" no console. Fecha a decisão nº 4 |

---

## 4. Modelo de dados e contratos comuns às quatro etapas

O mesmo esquema serve às quatro etapas. O que muda entre elas é quem preenche cada tabela e com que qualidade.

### 4.1 Tabelas

| Tabela | Campos | Observação |
|---|---|---|
| `tema` | id, nome, descricao (frase corrida), sinonimos[], criado_em | A descrição é o que vira embedding |
| `perfil` | id, tipo (usuario/contato), nome, apelido, email, telefone, empresa, cargo, notas, ativo, gerar_agora, criado_em, atualizado_em | Um registro é o próprio usuário. `gerar_agora` é ligado pelo console ou pela agenda (Etapa 3) |
| `perfil_tema` | perfil_id, tema_id, peso 1–5, origem (declarada/sugerida/importada), confirmado, registrado_em | `origem` é o que implementa "sinal social soma, nunca condiciona" |
| `fonte` | id, nome, url_feed, dominio, tipo, confiabilidade 0–10 | |
| `item` | id, fonte_id, url_canonica, titulo, texto, publicado_em, coletado_em, hash, embedding, assunto_id | `texto` vive 90 dias |
| `assunto` | id, titulo_gerado, primeiro_visto, ultimo_visto, n_itens, n_fontes_independentes, status, centroide, temas[], substancial 0–1, conversavel 0–1, justificativa, resumo_cartao | Agrupamento por centróide, janela de 7 dias |
| `assunto_contato` | assunto_id, perfil_id, gerado_em, score, por_que, status (novo/usado/nao_serve/descartado), motivo | **É o menu.** Sem esta tabela o produto regride para lista por tema |
| `fato` | id, perfil_id, data_do_fato, tipo, conteudo, fonte, registrado_em | Só inserção, nunca editada. Alimentada pela importação de publicações |
| `fila_extracao` | id, perfil_id, texto, criado_em, processado, erro | Texto livre sobre um contato (cadastro, notas importadas, publicações coladas) esperando o modelo propor tags |
| `pacote_troca` | id, perfil_id ou nulo, direcao (exportado/importado), conteudo_json, pseudonimizado, criado_em, processado | Etapa 4 |

### 4.2 Os dois contratos do motor

Independentes de modelo. Todo módulo que precisa de inteligência chama uma destas duas funções e recebe JSON validado por esquema. Nenhum outro módulo sabe qual modelo está rodando.

**qualificar** — recebe um assunto (título, itens resumidos, fontes) e a lista de temas conhecidos. Devolve:

```json
{"substancial": 0.8, "conversavel": 0.7, "temas": ["credito_pj", "autonomos"], "justificativa": "regra nova, ainda em disputa, dá conversa sem ser especialista"}
```

**cruzar** — recebe um contato (apelido e tags com peso), as tags do usuário e até 10 assuntos candidatos. Devolve:

```json
{"menu": [{"assunto_id": 812, "score": 0.74, "por_que": "ele trabalha com crédito e vocês dois lidam com autônomos"}],
 "sem_assunto": false, "motivo": null}
```

Quando o contato não tem tag ou nenhum candidato casa, `sem_assunto` é `true` e `motivo` diz qual dos dois. É esse campo que implementa "zero dado, avisa, não trava".

Duas funções auxiliares, mesmo padrão: **rotular** (título de 6 a 10 palavras para um assunto novo) e **cartao** (três linhas do que aconteceu, para os assuntos que entraram em algum menu).

---

## 5. Etapa 1 — MVP com Qwen3 4B

### 5.1 Alvo

Notebook comum de 8 GB de RAM, sem GPU. O mesmo código roda na máquina de desenvolvimento (48 GB) sem alteração — só o perfil de roteamento muda na Etapa 2. Em máquina de 4 GB, `qwen3:1.7b` qualifica e rotula, mas não cruza: o menu fica para a Etapa 4 nessa faixa. Não é alvo desta etapa.

### 5.2 Fluxo diário (05h00, ou no primeiro login com recuperação de execução perdida)

1. **Coleta.** `feedparser` em 20 a 40 feeds de `fontes.yaml`, mais as consultas do Google News RSS geradas automaticamente dos temas. `trafilatura` extrai o corpo. URL canônica, hash de título, descarte de ruído estrutural (teaser abaixo de 400 caracteres, título de lista, patrocinado, mais de 7 dias na primeira aparição).
2. **Embedding e agrupamento.** `multilingual-e5-small` em CPU via `fastembed`; `sqlite-vec` no mesmo arquivo do banco. Comparação com os centróides dos assuntos abertos dos últimos 7 dias; cosseno ≥ 0,82 entra no assunto, senão abre novo. Fonte só conta como independente com domínio diferente e texto divergindo mais de 30%.
3. **Qualificação.** Os 15 assuntos mais próximos das descrições de tema do usuário vão ao modelo, um por chamada. Corte: `substancial` ≥ 0,6 e `conversavel` ≥ 0,6.
4. **Pré-seleção por contato.** Para cada contato ativo, embedding das tags dele contra os centróides → 10 candidatos. Sem modelo, custa milissegundos.
5. **Cruzamento.** Uma chamada por contato ativo: menu de até 5 assuntos com `por_que`, ou `sem_assunto`.
6. **Cartão.** Três linhas para cada assunto que entrou em pelo menos um menu.
7. **Entrega.** Console mostra o menu por contato; `menu_AAAA-MM-DD.md` é gravado na pasta de saída.

### 5.3 Configuração do modelo

| Parâmetro | qualificar / rotular | cruzar / cartão |
|---|---|---|
| Modelo | `qwen3:4b` Q4_K_M (~2,5 GB em disco) | idem |
| Modo de raciocínio | **desligado** (`think: false`) | idem |
| `format` | `json` com esquema | `json` com esquema |
| `num_ctx` | 2048 | 4096 |
| `temperature` | 0,2 | 0,3 |
| Itens por chamada | 1 | 1 |
| Exemplo resolvido no prompt | 1 | 1 |

O modo de raciocínio do Qwen3 é o detalhe que derruba esta etapa se ficar ligado: dobra o tempo de resposta e o texto de pensamento entra no JSON. Vai desligado em toda chamada, sem exceção. JSON inválido: uma nova tentativa com temperatura 0,1; segunda falha, o item vai para a fila de revisão com o erro registrado. `OLLAMA_KEEP_ALIVE=30m` durante o ciclo. Um exemplo resolvido dentro do prompt rende mais, nesta faixa, do que trocar de modelo.

**Orçamento de memória em 8 GB com Windows 11:** sistema 3,0–3,5 GB, pesos 2,5 GB, contexto 0,4 GB, Python com índice 0,5 GB — cerca de 7 GB. Cabe com o navegador fechado durante o ciclo, que roda de madrugada ou no login. Os embeddings rodam fora do Ollama (via `fastembed`), então não disputam memória com o modelo.

### 5.4 Orçamento de chamadas e tempo

800 itens coletados → 300 depois das regras → 40 assuntos → 15 qualificados (15 chamadas) → 10 contatos ativos cruzados (10 chamadas) → 12 cartões (12 chamadas). **Cerca de 37 chamadas por dia**, não 800.

Em CPU de notebook, o 4B produz 5 a 10 tokens por segundo; cada chamada devolve 100 a 300 tokens. Estimativa: 15 a 25 minutos de modelo, mais 10 de coleta e embeddings — **25 a 40 minutos de ciclo**, medidos na primeira semana. Ninguém está na frente da tela às cinco da manhã.

### 5.5 Interface

Flask em `localhost:8765`, só em `127.0.0.1`, sem framework de frontend. Três telas:

- **Contatos.** Lista e ficha. Na ficha: tags com peso e origem, marcar ativo, botão "gerar menu agora". Cadastro por texto livre: o usuário cola o que sabe da pessoa ("advogado tributarista, corre, gosta de vinho, cliente desde 2023"), o modelo propõe as tags com origem `sugerida`, o usuário confirma com um clique. O extrator nunca registra saúde, religião, política, sindicato, vida sexual, origem racial ou dados de menores, mesmo que estejam no texto.
- **Menu.** Por contato: assuntos, `por_que`, cartão expandível, botões "usei" e "não serve" (com motivo entre quatro fixos: não interessa a ele, velho, raso, não dá conversa).
- **Temas.** Edição em linguagem natural, sinônimos, sugestões pendentes de confirmação.

A exportação `menu_AAAA-MM-DD.md` traz um bloco por contato com caixas de marcação; um script lê as marcações de volta na rodada seguinte. É o que permite ler e marcar no celular via pasta sincronizada (Etapa 3).

### 5.6 Fora de escopo da Etapa 1

Raspagem ou extensão de navegador, sincronização, assistentes pagos, resumo completo do assunto (só o cartão), balanço semanal, multiusuário.

### 5.7 Critérios de aceite

1. Cinco dias seguidos de ciclo sem intervenção, no notebook de 8 GB.
2. Menu gerado para pelo menos 5 contatos ativos, com 3 ou mais assuntos cada; contato sem tag recebe `sem_assunto` e não trava o ciclo.
3. JSON válido na primeira tentativa em pelo menos 95% das chamadas.
4. Ciclo completo em no máximo 45 minutos de CPU.
5. Todo `assunto_id` presente em um menu existe no banco — zero invenção.
6. Meta de calibragem, não bloqueio: aproveitamento (marcados "usei" ÷ entregues) acima de 30% na segunda semana. Abaixo disso, o problema está nas descrições dos temas ou nos exemplos de "conversável", e o ajuste é neles.

### 5.8 Esforço

Três semanas, uma pessoa, Claude Code executando a partir de briefs. Semana 1: núcleo (esquema, contratos, cliente de LLM, roteamento) e coleta. Semana 2: agrupamento, qualificação, cruzamento, menu. Semana 3: console, exportação, medição de aceite.

---

## 6. Etapa 2 — Evolução do MVP para Qwen mais potentes

### 6.1 O que não muda

Código, banco, contratos, estrutura dos prompts, console. A evolução é um perfil novo em `llm_routing.yaml` e, a partir de 16 GB, uma migração única de embeddings.

### 6.2 Perfis de hardware

| Perfil | RAM | Modelo generativo | Embeddings | `num_ctx` (qualificar / cruzar / cartão) |
|---|---|---|---|---|
| `p8` | 8 GB | `qwen3:4b` | `multilingual-e5-small` (384 dim.) | 2048 / 4096 / 4096 |
| `p16` | 16 GB | `qwen3:8b` | `bge-m3` (1024 dim.) | 4096 / 8192 / 8192 |
| `p32` | 32 GB | `qwen3:14b` | `bge-m3` | 8192 / 16384 / 8192 |
| `p48` | 48 GB ou mais (Mac M-series) | `qwen3:30b-a3b` para qualificar e cruzar (mistura de especialistas, rápido); `qwen3:32b` para cartão e resumo completo | `bge-m3` | 8192 / 16384 / 16384 |

A troca de `e5-small` para `bge-m3` muda a dimensão do vetor; o script de migração recalcula os embeddings de itens e centróides em uma execução e não toca em mais nada. O `qwen2.5:14b` já instalado na máquina de desenvolvimento serve de linha de base de comparação, não de alvo.

### 6.3 O que cada degrau libera

- **8B:** resumo completo do assunto (linha do tempo, números com fonte, posições em disputa, "o que eu precisaria saber para não falar bobagem"); `por_que` mais específico; balanço semanal com calibragem automática de peso de tema e confiabilidade de fonte.
- **14B:** extração de tags a partir de publicações coladas **com lastro** — cada tag aponta para o trecho que a justifica; detecção de mudança de cargo, empresa ou cidade em texto colado, gravada como fato datado; menu para 30 contatos ativos em tempo aceitável.
- **30B-A3B / 32B:** síntese de perfil por contato em texto para o usuário ler; pesos de tema sugeridos a partir do histórico de "usei" e "não serve"; menu para 100 contatos em minutos.

### 6.4 Protocolo de promoção — decidido por medida, não por impressão

Separar 20 assuntos e 10 contatos. Rodar o perfil atual e o candidato no mesmo material. Registrar: percentual de JSON válido na primeira tentativa; concordância no menu (mesmos 3 primeiros assuntos, ou diferença de score menor que 0,10); tempo por chamada. Um perfil menor só é mantido numa tarefa com **JSON válido acima de 98%** e **concordância acima de 85%** com o perfil maior. Resultado registrado em ADR. O mesmo protocolo vale no sentido inverso: um modelo maior que não melhora a concordância não justifica o tempo extra.

### 6.5 Importação manual de publicações — o sinal social desta proposta

Tela "Colar publicações" na ficha do contato. O usuário copia o texto visível das publicações de alguém (LinkedIn, Instagram, X, blog) e cola. Nada é raspado; é o usuário lendo o que está público e trazendo para o sistema, dentro dos termos de uso de cada rede. O modelo devolve:

```json
{"tags_sugeridas": [{"tag": "cabotagem", "peso": 3, "trecho": "publicou sobre o novo terminal de cabotagem em Santos"}],
 "fatos_datados": [{"data": "2026-09-12", "tipo": "publicacao", "conteudo": "comentou o terminal de cabotagem em Santos", "fonte": "LinkedIn"}]}
```

Tags entram em `perfil_tema` com origem `sugerida` e `confirmado = false`; o usuário confirma uma a uma. Fatos entram em `fato`, só inserção. Em `p8` funciona sem lastro; em `p16` ou acima, com lastro obrigatório e tag sem trecho é cortada.

### 6.6 Esforço e aceite

Duas semanas. Semana 4: perfis, migração de embeddings, protocolo de medição, ADR. Semana 5: importação de publicações, resumo completo, balanço semanal. Passa quando: o perfil `p16` ou superior concorda em 85% ou mais com `p8` nos 3 primeiros assuntos de 10 contatos e entrega pelo menos um assunto durável que `p8` perdeu; migração de embeddings concluída sem perda de assunto; uma importação real de publicações produz tags confirmadas pelo usuário.

---

## 7. Etapa 3 — Integrações com Google One e outros serviços, sem API de LLM

### 7.1 Princípio

O Google One entrega armazenamento no Drive e o aplicativo do Gemini. Não dá chave de API nem altera cota de nada — e esta etapa não precisa disso. Tudo abaixo usa o que uma conta Google comum já oferece sem OAuth e sem chave: exportação de contatos, Google Alerts em RSS, Google News em RSS, endereço secreto da agenda em iCal, pasta do Drive sincronizada no computador, e Apps Script com gatilho de tempo. Nenhum modelo de linguagem roda fora da máquina.

### 7.2 Google Contatos → fichas

O usuário exporta em `contacts.google.com` (Exportar → Google CSV). O script cria ou atualiza `perfil` por e-mail ou telefone, transforma os marcadores do Google em tags com origem `importada`, e enfileira o campo "Notas" para o modelo local propor tags com origem `sugerida`. Reimportar é idempotente.

```python
# integracoes/google_contatos.py
import csv, sqlite3, sys

def campo(row, *prefixos):
    for k, v in row.items():
        if k and v and any(k.lower().startswith(p) for p in prefixos):
            return v.strip()
    return None

def importar(csv_path, db_path):
    db = sqlite3.connect(db_path)
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            nome = row.get("Name") or " ".join(x for x in [row.get("First Name"), row.get("Last Name")] if x)
            email = campo(row, "e-mail 1 - value")
            tel = campo(row, "phone 1 - value")
            if not (nome and (email or tel)):
                continue
            empresa = campo(row, "organization 1 - name", "organization name")
            cargo = campo(row, "organization 1 - title", "organization title")
            notas = campo(row, "notes")
            marcadores = [m.strip() for m in (campo(row, "group membership", "labels") or "").split(":::")
                          if m.strip() and not m.startswith("*")]
            pid = db.execute("SELECT id FROM perfil WHERE email=? OR telefone=?", (email, tel)).fetchone()
            if pid:
                db.execute("UPDATE perfil SET nome=?, empresa=?, cargo=?, notas=?, atualizado_em=datetime('now') WHERE id=?",
                           (nome, empresa, cargo, notas, pid[0]))
                pid = pid[0]
            else:
                pid = db.execute("INSERT INTO perfil(tipo,nome,email,telefone,empresa,cargo,notas,ativo,criado_em,atualizado_em) "
                                 "VALUES('contato',?,?,?,?,?,?,0,datetime('now'),datetime('now'))",
                                 (nome, email, tel, empresa, cargo, notas)).lastrowid
            for m in marcadores:
                tid = db.execute("INSERT OR IGNORE INTO tema(nome,descricao,criado_em) VALUES(?,?,datetime('now')) RETURNING id",
                                 (m.lower(), m)).fetchone() or db.execute("SELECT id FROM tema WHERE nome=?", (m.lower(),)).fetchone()
                db.execute("INSERT OR IGNORE INTO perfil_tema(perfil_id,tema_id,peso,origem,confirmado,registrado_em) "
                           "VALUES(?,?,3,'importada',0,datetime('now'))", (pid, tid[0]))
            if notas:
                db.execute("INSERT INTO fila_extracao(perfil_id,texto,criado_em) VALUES(?,?,datetime('now'))", (pid, notas))
    db.commit()

if __name__ == "__main__":
    importar(sys.argv[1], sys.argv[2])
```

Os nomes de coluna variam entre versões da exportação do Google; o script casa por prefixo e ignora o que não reconhece.

### 7.3 Google Alerts e Google News → fontes

Dois caminhos, ambos RSS. O Google News aceita consulta na URL e o script gera uma consulta por tema a partir do nome e dos sinônimos. O Google Alerts é criado à mão em `google.com/alerts` com entrega "Feed RSS", e a URL do feed é colada em `fontes.yaml`. O script abaixo gera as entradas do Google News; as do Alerts entram pelo mesmo arquivo.

```python
# integracoes/fontes_google.py
from urllib.parse import quote
import sqlite3, yaml, sys

def url_google_news(consulta):
    return f"https://news.google.com/rss/search?q={quote(consulta)}&hl=pt-BR&gl=BR&ceid=BR:pt-419"

def gerar(db_path, fontes_yaml):
    db = sqlite3.connect(db_path)
    fontes = yaml.safe_load(open(fontes_yaml, encoding="utf-8")) or {"feeds": []}
    existentes = {f["url"] for f in fontes["feeds"]}
    for nome, sinonimos in db.execute("SELECT nome, sinonimos FROM tema"):
        termos = [nome] + (yaml.safe_load(sinonimos) if sinonimos else [])
        consulta = " OR ".join(f'"{t}"' for t in termos[:4])
        url = url_google_news(consulta)
        if url not in existentes:
            fontes["feeds"].append({"nome": f"Google News · {nome}", "url": url, "tipo": "agregador", "confiabilidade": 5})
    yaml.safe_dump(fontes, open(fontes_yaml, "w", encoding="utf-8"), allow_unicode=True, sort_keys=False)

if __name__ == "__main__":
    gerar(sys.argv[1], sys.argv[2])
```

A codificação da consulta com `quote` é obrigatória; termo com espaço sem codificar é o erro mais comum nesse feed. Intervalo de 2 segundos entre chamadas ao Google News.

### 7.4 Pasta do Drive → menu no celular e marcação de volta

Sem script novo no lado do Google: a pasta de saída do agente passa a ser uma pasta do Drive para computador. O `menu_AAAA-MM-DD.md` aparece no celular no aplicativo do Drive ou no Obsidian em minutos. O usuário marca as caixas no celular; o script abaixo lê o arquivo na rodada seguinte e grava em `assunto_contato`.

Formato gerado pelo agente (o identificador fica em comentário HTML, invisível na leitura):

```markdown
## Ricardo  <!-- perfil:14 -->
### Crédito consignado para autônomos entra em vigor  <!-- ac:812 -->
Por quê: ele trabalha com crédito e vocês dois lidam com autônomos.
- [ ] usei
- [ ] não serve → motivo: ( ) não interessa a ele ( ) velho ( ) raso ( ) não dá conversa
```

```python
# integracoes/ler_marcacoes.py
import re, sqlite3, sys, pathlib

BLOCO = re.compile(r"<!-- ac:(\d+) -->(.*?)(?=<!-- ac:|\Z)", re.S)
MOTIVOS = {"não interessa a ele": "nao_interessa", "velho": "velho", "raso": "raso", "não dá conversa": "nao_da_conversa"}

def ler(md_path, db_path):
    db = sqlite3.connect(db_path)
    texto = pathlib.Path(md_path).read_text(encoding="utf-8")
    for ac_id, corpo in BLOCO.findall(texto):
        if re.search(r"- \[x\] usei", corpo, re.I):
            db.execute("UPDATE assunto_contato SET status='usado' WHERE rowid=?", (ac_id,))
        elif re.search(r"- \[x\] não serve", corpo, re.I):
            motivo = next((v for k, v in MOTIVOS.items() if re.search(rf"\(x\) {re.escape(k)}", corpo, re.I)), None)
            db.execute("UPDATE assunto_contato SET status='nao_serve', motivo=? WHERE rowid=?", (motivo, ac_id))
    db.commit()

if __name__ == "__main__":
    ler(sys.argv[1], sys.argv[2])
```

### 7.5 Google Agenda → menu antes da reunião

A agenda tem um "endereço secreto no formato iCal" (Configurações → a agenda → Integrar). É uma URL sem autenticação; fica em `config/local.yaml`, fora do git. O script baixa o `.ics`, pega os eventos das próximas 48 horas, extrai os e-mails dos convidados e, quando um deles bate com um `perfil`, marca o contato para "gerar menu agora" com prioridade. Resultado: antes de cada reunião com alguém da base, o menu daquela pessoa já está pronto.

```python
# integracoes/agenda_ical.py
import httpx, sqlite3, sys
from datetime import datetime, timedelta, timezone
from icalendar import Calendar

def convidados_proximos(url_ical, horas=48):
    cal = Calendar.from_ical(httpx.get(url_ical, timeout=30, follow_redirects=True).content)
    agora = datetime.now(timezone.utc); limite = agora + timedelta(hours=horas)
    emails = set()
    for ev in cal.walk("VEVENT"):
        ini = ev.get("DTSTART").dt
        if not isinstance(ini, datetime):
            continue
        ini = ini if ini.tzinfo else ini.replace(tzinfo=timezone.utc)
        if agora <= ini.astimezone(timezone.utc) <= limite:
            att = ev.get("ATTENDEE", [])
            for a in (att if isinstance(att, list) else [att]):
                emails.add(str(a).replace("mailto:", "").lower())
    return emails

def marcar(db_path, url_ical):
    db = sqlite3.connect(db_path)
    for email in convidados_proximos(url_ical):
        db.execute("UPDATE perfil SET ativo=1, gerar_agora=1 WHERE lower(email)=? AND tipo='contato'", (email,))
    db.commit()

if __name__ == "__main__":
    marcar(sys.argv[1], sys.argv[2])
```

Eventos recorrentes vêm como regra, não expandidos; a primeira versão considera só ocorrências únicas, o que cobre reuniões marcadas com pessoa de fora.

### 7.6 Apps Script → coleta noturna com o notebook desligado (opcional)

Só faz sentido se o notebook ficar desligado por dias. Um script numa conta Google comum, com gatilho diário, baixa os feeds e grava o XML bruto numa pasta do Drive; quando o notebook liga, o agente lê a pasta sincronizada em vez de chamar os feeds. Nenhum modelo, nenhuma inteligência no lado Google — só cobertura. A cota gratuita (20 mil chamadas de rede por dia, 90 minutos de gatilho) cobre 80 feeds com folga.

```javascript
// integracoes/coleta_noturna.gs — Apps Script, conta Google comum
const PASTA_ID = "id-da-pasta-agente_nw-no-drive";
const FEEDS = ["https://news.google.com/rss/search?q=...", "https://www.infomoney.com.br/feed/"]; // ou lidos de fontes.yaml copiado ao Drive

function coletaNoturna() {
  const hoje = Utilities.formatDate(new Date(), "America/Sao_Paulo", "yyyy-MM-dd");
  const pasta = DriveApp.getFolderById(PASTA_ID).createFolder("coleta_" + hoje);
  FEEDS.forEach((url, i) => {
    try {
      const xml = UrlFetchApp.fetch(url, {muteHttpExceptions: true, followRedirects: true}).getContentText();
      pasta.createFile("feed_" + String(i).padStart(3, "0") + ".xml", xml, "application/xml");
    } catch (e) {
      pasta.createFile("erro_" + i + ".txt", String(e));
    }
  });
}
// Gatilho: Gatilhos → adicionar → coletaNoturna → baseado em tempo → diário → 5h–6h
```

O mesmo script pode expor o `menu.json` mais recente numa página web simples (`doGet`), para leitura sem o Drive. Fica registrado, não entra no escopo desta etapa.

### 7.7 Outros serviços, todos por RSS ou REST público sem chave

| Serviço | Como entra | Para quê |
|---|---|---|
| YouTube (canal) | `https://www.youtube.com/feeds/videos.xml?channel_id=ID` | assunto de canais que os contatos seguem |
| Substack, Medium, blogs | `/feed` | texto longo, fonte de assunto durável |
| Reddit | `/r/<sub>/.rss` | assunto em comunidade especializada (não-obviedade) |
| Hacker News | `https://hnrss.org/frontpage` | tecnologia |
| Diário Oficial da União | RSS de `in.gov.br` | assunto oficial |
| BrasilAPI CNPJ | `https://brasilapi.com.br/api/cnpj/v1/<CNPJ>` — REST público, sem chave, ~3 chamadas/min | setor da empresa do contato vira tag `sugerida` |
| Obsidian | abre a pasta do Drive | leitura e marcação no computador e no celular |

Redes sociais não entram aqui: sem raspagem, conforme seção 2.

### 7.8 Esforço e aceite

Uma semana. Passa quando: um CSV real de contatos importa com tags; todos os temas têm feed do Google News gerado; o menu do dia aparece no celular em até 5 minutos após o ciclo; marcação feita no celular chega ao banco na rodada seguinte; contato com reunião nas próximas 48 horas recebe menu gerado com prioridade.

---

## 8. Etapa 4 — Gemini, Claude e GPT pagos, com pessoa fazendo a ponte

### 8.1 Princípio

As três assinaturas aceitam instruções fixas e arquivos anexados (Projetos no ChatGPT e no Claude, Gems no Gemini). Sem API. O agente exporta um pacote; a pessoa cola no assistente; o assistente devolve JSON; a pessoa cola de volta; o agente importa, valida e pede confirmação. Tudo que sai é pseudonimizado; o nome só volta na máquina.

### 8.2 Pacote de exportação

```json
{"versao": 1, "gerado_em": "2026-09-17T06:10:00-03:00", "pedido": "refinar_menu",
 "usuario": {"tags": ["direito tributário", "software jurídico", "corrida de rua"]},
 "contato": {"id_pseudo": "P-014", "cargo_generico": "diretor comercial", "setor": "logística",
             "tags": [{"tag": "cabotagem", "peso": 4}, {"tag": "ESG", "peso": 2}]},
 "assuntos_candidatos": [{"assunto_id": 812, "titulo": "...", "cartao": ["...", "...", "..."], "fontes": ["https://..."], "data": "2026-09-15"}],
 "menu_local": [{"assunto_id": 812, "score": 0.71, "por_que": "..."}],
 "publicacoes_coladas": null}
```

Regras do pacote: sem nome, telefone, e-mail; sem empresa quando ela for pequena o bastante para identificar a pessoa; `id_pseudo` gerado por contato e resolvido só localmente. Um teste automatizado percorre cada pacote antes de gravar em `pacote_troca` e recusa se encontrar nome, telefone ou e-mail de qualquer perfil.

### 8.3 Os três usos

**Refinar o menu.** O assistente reordena, reescreve o `por_que` e pode acrescentar até 2 assuntos que encontrou por busca própria, cada um com URL e data. O agente mostra a diferença entre o menu local e o refinado; o usuário aceita ou não. Assunto novo entra em `assunto` com fonte `assistente` e passa pela qualificação local como qualquer outro.

**Sugerir tags a partir de publicações.** A pessoa cola no pacote (`publicacoes_coladas`) o texto visível das publicações do contato, ou cola direto no assistente. O assistente devolve tags com o trecho que as justifica. Entram como `sugerida`, `confirmado = false`, confirmação uma a uma. É a análise de rede social desta proposta: sem raspagem, sem API, com pessoa lendo o que está público.

**Pesquisa profunda semanal.** Uma vez por semana, o usuário pede ao assistente (Deep Research no Gemini ou no ChatGPT, pesquisa no Claude) os assuntos das últimas duas semanas nos temas dele. O retorno entra como assuntos com fonte `pesquisa`, com URL obrigatória, e passa pela qualificação local.

### 8.4 Instrução fixa para o Projeto, Gem ou GPT

```
Você recebe um pacote JSON do agente_nw com: as características do usuário; as características
de UM contato identificado só por código (P-000); assuntos candidatos com fontes; e um pedido
(refinar_menu, sugerir_tags ou pesquisar_temas). Pode receber também publicações coladas.

Responda SOMENTE com JSON no esquema de retorno, sem texto antes ou depois, sem cerca de código.

Regras:
- Nunca tente identificar o contato. Nunca peça nome, empresa ou telefone.
- Todo assunto novo vem com URL real e data. Sem URL, não inclua.
- Toda tag sugerida vem com o trecho que a justifica, copiado do material recebido.
- Não extraia nem sugira: saúde, religião, política, sindicato, vida sexual, origem racial,
  dados de menores. Se aparecer no material, ignore.
- Não escreva mensagem, não sugira tom, não opine sobre a relação entre o usuário e o contato.
- Se não houver nada a acrescentar, devolva as listas vazias.

Esquema de retorno:
{"versao": 1, "contato_id_pseudo": "P-000",
 "menu_refinado": [{"assunto_id": 0, "score": 0.0, "por_que": ""}],
 "assuntos_novos": [{"titulo": "", "url": "", "data": "AAAA-MM-DD", "por_que": ""}],
 "tags_sugeridas": [{"tag": "", "peso": 1, "evidencia": ""}],
 "observacoes": ""}
```

### 8.5 Importação e validação

O importador aceita o JSON colado, tolera cerca de código e espaços, valida contra o esquema e, se falhar, mostra o campo que quebrou e pede nova colagem — nunca conserta JSON por expressão regular. Toda tag entra sem confirmação; todo assunto novo exige URL; o `por_que` refinado só substitui o local depois que o usuário aceita a diferença na tela. O pacote de ida e o de volta ficam em `pacote_troca` para auditoria.

### 8.6 Variante sem copiar e colar

Uma tarefa agendada do Claude (Cowork) com o conector do Drive lê o pacote que o agente deixou na pasta sincronizada e grava `retorno_AAAA-MM-DD.json` na mesma pasta; o agente importa na rodada seguinte. A pessoa age só na configuração e na confirmação das tags. Gemini e ChatGPT também têm tarefas agendadas, mas respondem no chat, e o retorno precisa ser colado. Nenhuma das três variantes usa API.

### 8.7 Esforço e aceite

Uma semana. Passa quando: ida e volta completa em cada uma das três plataformas com 3 contatos; tags importadas e confirmadas; diferença de menu exibida e aceita ou recusada; teste de pseudonimização passando em 100% dos pacotes gerados.

---

## 9. Cronograma e condições de passagem

| Etapa | Semanas | Entrega | Passa quando |
|---|---|---|---|
| 1 — MVP Qwen3 4B | 1 a 3 | ciclo diário, menu por contato, console, exportação | critérios da seção 5.7 |
| 2 — Evolução de modelo | 4 e 5 | perfis de hardware, migração de embeddings, importação de publicações, resumo completo, balanço semanal | seção 6.6 |
| 3 — Integrações Google e RSS | 6 | contatos, alerts, news, Drive, agenda, scripts da seção 7 | seção 7.8 |
| 4 — Ponte com assistentes pagos | 7 | exportação, instrução fixa, importação, pseudonimização | seção 8.7 |

Sequência fixa; cada etapa começa com a anterior certificada. As Etapas 3 e 4 são independentes entre si e podem ser invertidas se o comitê preferir. Estimativas assumem uma pessoa em tempo integral e Claude Code executando briefs.

---

## 10. Riscos e controles

| Risco | Controle |
|---|---|
| JSON quebrado ou resposta genérica no 4B | esquema forçado, modo de raciocínio desligado, um exemplo resolvido no prompt, uma nova tentativa, fila de revisão; menu só referencia `assunto_id` existente |
| "Conversável" é subjetivo | conjunto de exemplos positivos e negativos escrito pela IA e aprovado pelo usuário antes de calibrar; botão "não serve" com motivo fixo realimenta semanalmente |
| Release distribuído a quinze portais parece assunto denso | fonte só é independente com domínio diferente e texto divergindo mais de 30% |
| Feeds instáveis | adaptadores por fonte, hash por URL canônica e título normalizado, alerta quando um feed volta vazio dois dias seguidos |
| Dados pessoais de terceiros (LGPD) | tudo local por padrão; pacote pseudonimizado e testado antes de sair; extrator nunca registra categorias sensíveis; `notas` aceita fato datado, não opinião |
| Formatos do Google mudam (colunas do CSV, iCal) | leitores tolerantes, casamento por prefixo, erro explícito em vez de importação silenciosa errada |
| Câmara de eco (sempre os mesmos assuntos e contatos) | teto de 3 assuntos por tema por dia; métrica de concentração no balanço semanal |
| Ciclo não roda porque o notebook estava desligado | gatilho no login com atraso de 5 minutos e verificação no banco de "já rodou hoje"; cada etapa retomável |

---

## 11. Aprovação pedida

O comitê aprova, em bloco: o produto (seção 2), as decisões (seção 3), o modelo de dados e os contratos (seção 4), as quatro etapas com prazos e critérios (seções 5 a 9), a manutenção da restrição de API, e o início da Etapa 1 com brief de execução na semana seguinte à aprovação.

Aprovado, o próximo passo é atualizar `PLANO.md` e `ARQUITETURA.md` do repositório com o modelo de dados da seção 4 e a saída por contato, e escrever o brief da semana 1.
