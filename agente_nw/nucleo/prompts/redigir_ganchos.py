from __future__ import annotations

from dataclasses import dataclass, field, replace

from agente_nw.nucleo.modelos.pedido import PedidoExtraido
from agente_nw.nucleo.modelos.redacao import (
    LIMITE_PALAVRAS_MENSAGEM,
    MAXIMO_GANCHOS,
    MAXIMO_PALAVRAS_TITULO,
    LinkNoticia,
    RespostaRedacao,
)

ESQUEMA = RespostaRedacao

LIMITE_TOKENS_PADRAO = 6000
_TOKENS_POR_PALAVRA = 1.4
_HISTORICO_NO_CORTE = 1
_FATOS_NO_CORTE = 5

# Cenário do exemplo deliberadamente distante de qualquer entrada real de teste (armadilha 24,
# docs/PLAN.md): evita que o modelo copie o exemplo em vez de ler os dados. Os textos do exemplo
# respeitam os limites do registro "cordial".
_EXEMPLO = """\
QUEM ESCREVE: Rafael Quintela. Temas dele: cerâmica (interesse), mercado editorial (domínio).
PARA QUEM: Helena Brandão — dona de livraria, Curitiba. Vínculo: vizinha de prédio.
Tempo sem contato: dois anos.
Fatos recentes sobre a pessoa:
- 2026-09-20 (instagram): Helena publicou fotos do clube de leitura de sábado na livraria.
O PEDIDO: objetivo: retomar ("voltar a falar com ela"). Meio: pessoalmente. Registro: cordial.
Assunto principal: livrarias independentes. Interessa: eventos. Evitar: preço do aluguel.
HISTÓRICO: (nenhuma consulta anterior)
ASSUNTOS SELECIONADOS:
[assunto 41] Feira do livro de Paranaguá terá selo para livrarias independentes
  Por que serve: ela vende livros e você conhece o mercado editorial.
  Resumo: A feira criou um selo que dá estande gratuito a livrarias de até três funcionários.
  Manchetes: Gazeta do Litoral, 2026-09-30: Feira do livro cria selo para livrarias pequenas
JSON:
{"ganchos": [{"assunto_id": null, "peculiaridade": "o clube de leitura de sábado na livraria", \
"por_que_para_esta_pessoa": "Retoma a conversa pelo clube de leitura que ela mantém na livraria, sem \
pedir nada.", \
"mensagem": "Oi, Helena, tudo bem? Faz tempo que a gente não se fala. Vi as fotos do clube de leitura de \
sábado na sua livraria e fiquei com vontade de passar aí. Como está tudo por aí? Um abraço!", \
"abordagem_presencial": "Comece pelo clube de leitura: pergunte como foi o último sábado."}, \
{"assunto_id": 41, "titulo": "Feira de Paranaguá abre estande gratuito a livrarias pequenas", \
"noticia": "A feira do livro de Paranaguá criou um selo que dá estande gratuito a livrarias de até três \
funcionários. A notícia saiu na Gazeta do Litoral em 30 de setembro.", \
"peculiaridade": null, \
"por_que_para_esta_pessoa": "Ela tem uma livraria independente e você conhece o mercado editorial, então \
o assunto retoma a conversa sem pedir nada.", \
"mensagem": "Oi, Helena, tudo bem? Faz tempo que a gente não se fala. Vi que a feira do livro de Paranaguá \
vai dar estande gratuito para livrarias pequenas e lembrei de você. Se tiver interesse, posso te contar \
o que li. Um abraço!", \
"abordagem_presencial": "Comece perguntando como vai a livraria e conte que leu sobre o selo da feira de \
Paranaguá; pergunte se ela já conhecia."}], "aviso": null}
"""


@dataclass(frozen=True)
class AssuntoParaRedacao:
    assunto_id: int
    titulo: str
    por_que: str | None
    resumo: str | None
    manchetes: list[str] = field(default_factory=list)  # "veículo, data: título"
    links: list[LinkNoticia] = field(default_factory=list)  # as mesmas notícias, com o endereço


@dataclass(frozen=True)
class EntradaRedacao:
    usuario_nome: str
    usuario_temas: list[tuple[str, str]]  # (tema, nível)
    contato_nome: str
    contato_ficha: list[str]  # "cargo: ...", "empresa: ...", "cidade: ..."
    vinculo: str | None
    tempo_sem_contato: str | None
    fatos: list[str]
    cabecalho_rede: str | None
    pedido: PedidoExtraido
    frase: str
    historico: list[str]
    assuntos: list[AssuntoParaRedacao]
    contexto_relacao: list[str] = field(default_factory=list)  # tags: família, amigos, trabalho...
    notas: list[str] = field(default_factory=list)  # notas do usuário sobre o contato (brief 050)


def estimar_tokens(texto: str) -> int:
    """Contagem aproximada: palavras × 1,4."""
    return int(len(texto.split()) * _TOKENS_POR_PALAVRA)


def _lista(valores: list[str]) -> str:
    return "; ".join(valores) if valores else "(nada informado)"


def _bloco_quem_escreve(entrada: EntradaRedacao) -> str:
    temas = ", ".join(f"{nome} ({nivel})" for nome, nivel in entrada.usuario_temas) or "(nenhum informado)"
    return f"QUEM ESCREVE: {entrada.usuario_nome}. Temas dele: {temas}."


def _bloco_para_quem(entrada: EntradaRedacao) -> str:
    ficha = ", ".join(entrada.contato_ficha) or "sem cargo, empresa ou cidade conhecidos"
    linhas = [
        f"PARA QUEM: {entrada.contato_nome} — {ficha}. Vínculo: {entrada.vinculo or 'não informado'}. "
        f"Tempo sem contato: {entrada.tempo_sem_contato or 'não informado'}."
    ]
    if entrada.contexto_relacao:
        linhas.append(f"Contexto da relação: {', '.join(entrada.contexto_relacao)}.")
    if entrada.cabecalho_rede:
        linhas.append(f"Na rede social: {entrada.cabecalho_rede}")
    if entrada.fatos:
        linhas.append("Fatos recentes sobre a pessoa:")
        linhas.extend(f"- {fato}" for fato in entrada.fatos)
    else:
        linhas.append("Fatos recentes sobre a pessoa: (nenhum)")
    return "\n".join(linhas)


def _bloco_pedido(entrada: EntradaRedacao) -> str:
    pedido = entrada.pedido
    return (
        f'O PEDIDO: objetivo: {pedido.objetivo} ("{pedido.objetivo_texto}"). Meio: {pedido.meio}. '
        f"Registro: {pedido.registro}.\n"
        f"Assunto principal: {pedido.assunto_principal}. Interessa: {_lista(pedido.interessa)}. "
        f"Evitar: {_lista(pedido.evitar)}.\n"
        f'Frase original do usuário: "{entrada.frase}"'
    )


def _bloco_historico(entrada: EntradaRedacao) -> str:
    notas = ""
    if entrada.notas:
        notas = "\nNotas do usuário sobre esta pessoa (valem como fato dito por ele):\n" + "\n".join(
            f"- {nota}" for nota in entrada.notas
        )
    if not entrada.historico:
        return "HISTÓRICO: (nenhuma consulta anterior)" + notas
    return (
        "HISTÓRICO (consultas anteriores; não repita o que já foi usado; comentário do usuário diz por que "
        "uma mensagem serviu ou não):\n" + "\n".join(entrada.historico) + notas
    )


def _bloco_assuntos(entrada: EntradaRedacao) -> str:
    linhas = ["ASSUNTOS SELECIONADOS:"]
    if not entrada.assuntos:
        linhas.append("(nenhum — escreva só a mensagem base)")
    for assunto in entrada.assuntos:
        linhas.append(f"[assunto {assunto.assunto_id}] {assunto.titulo}")
        linhas.append(f"  Por que serve: {assunto.por_que or '(sem justificativa)'}")
        linhas.append(f"  Resumo: {assunto.resumo or '(sem resumo)'}")
        manchetes = " | ".join(assunto.manchetes) if assunto.manchetes else "(sem manchetes)"
        linhas.append(f"  Manchetes: {manchetes}")
    return "\n".join(linhas)


def _regras() -> str:
    limites = "; ".join(
        f"{registro}: até {palavras} palavras" for registro, palavras in LIMITE_PALAVRAS_MENSAGEM.items()
    )
    return f"""\
REGRAS DE REDAÇÃO:
- A espinha da mensagem é o objetivo do pedido e a pessoa; a notícia é opcional. Devolva SEMPRE, em primeiro \
lugar, uma mensagem base: "assunto_id": null, "titulo": null, "noticia": null. Ela serve ao objetivo do \
pedido (convite, pedido, retomada...) e cita uma "peculiaridade" concreta da pessoa, tirada de um dos fatos \
acima (um detalhe específico, não só o cargo); copie em "peculiaridade" o detalhe usado. Se não houver fato \
utilizável, use o que a ficha dá (cargo, cidade), deixe "peculiaridade" null e não invente nada. \
"por_que_para_esta_pessoa" e "mensagem" nunca ficam vazios.
- Depois da base, de 0 a {MAXIMO_GANCHOS} ganchos de notícia, um por assunto, sem repetir "assunto_id" e só \
com os números que aparecem acima. Inclua o gancho só se a notícia se liga de verdade ao objetivo do pedido; \
na dúvida, não inclua. Nunca invente notícia.
- Cada gancho de notícia tem: "assunto_id", "titulo" (até {MAXIMO_PALAVRAS_TITULO} palavras), \
"noticia" (duas frases, só com o que está nas manchetes e no resumo; proibido inventar número, nome ou \
data), \
"por_que_para_esta_pessoa" (uma frase que cite o vínculo ou o objetivo), "mensagem" (texto pronto para \
enviar) e "abordagem_presencial" (uma ou duas frases de como puxar o assunto; preencha só quando o meio \
for "pessoalmente", senão use null). A mensagem base tem os mesmos campos, com "titulo" e "noticia" null.
- A mensagem segue o registro do pedido. Limites: {limites}. "proximo": primeira pessoa, informal, sem \
saudação formal. "cordial": cumprimento leve. "formal": tratamento e fecho. Português do Brasil, sem emojis \
(salvo no registro "proximo"), no máximo um ponto de exclamação, nunca "espero que esta mensagem o \
encontre bem".
- Na mensagem base o objetivo é o centro, dito de forma explícita (convite, pedido, agradecimento...), com a \
peculiaridade como abertura. O objetivo molda a mensagem: "retomar" reconhece o tempo sem contato sem \
pedir desculpa; "agradecer" \
põe o agradecimento antes do gancho; "pedir" põe o pedido depois do gancho e o torna explícito; \
"responder" continua o fio da conversa; "apresentar" diz em uma linha quem é o usuário antes do gancho, \
mas só se a pessoa não o conhece bem.
- Pese a força do vínculo. Vínculo forte (família, amigo próximo, convívio frequente): a pessoa sabe quem \
é o usuário e como vocês se ligam, então não explique o parentesco nem se apresente ("sou cunhado da sua \
esposa"). Vínculo fraco (conhecido, contato profissional, pouco contato, tempo sem falar): lembrar de onde \
se conhecem pode ser parte útil da mensagem, e o vínculo pode servir de abertura. Na dúvida, siga o \
tempo sem contato e o contexto da relação acima.
- Instruções de forma que estão na frase original do usuário (número de parágrafos, tamanho, tom) valem \
mais que os padrões acima: cumpra-as na "mensagem", separando parágrafos com uma linha em branco.
- O contexto da relação (família, amigos, trabalho...) diz que assuntos cabem e que tom usar; respeite-o. \
Assunto de trabalho não vai para mensagem a familiar, nem o contrário.
- Nada do que o pedido manda evitar pode aparecer na mensagem.
- Não invente local, data, horário, prazo, nome de evento ou de lugar para o que o usuário propõe (jantar, \
ligação, encontro): só cite o que a frase do pedido diz. Um lugar ou evento que aparece nos fatos é da \
pessoa, não do convite. Sem data ou local no pedido, convide sem marcar ("combinamos a data com você").
- Sobre a pessoa, afirme só o que está nos fatos e na ficha acima. Fato marcado [antigo] ou [de imagem] \
não vale como posição atual dela: se usar, com ressalva ("há um tempo", "numa imagem que publicou"). Nunca \
infira opinião, posição ou adesão da pessoa a partir de manchete, foto ou assunto.
- Não repita uma mensagem que o histórico mostra como usada.
- Decida sozinho se continua uma conversa anterior ou abre assunto novo: se o histórico traz um gancho \
entregue ou usado com esta pessoa e o pedido indica seguimento, faça a mensagem retomar esse fio; \
senão, trate como conversa nova. Nunca faça perguntas ao usuário.
- Responda só com um objeto JSON, sem texto antes ou depois: \
{{"ganchos": [{{"assunto_id": null, "titulo": null, "noticia": null, \
"peculiaridade": "o detalhe da pessoa usado", "por_que_para_esta_pessoa": "uma frase", \
"mensagem": "o texto pronto", "abordagem_presencial": null}}], "aviso": null}}"""


def _montar(entrada: EntradaRedacao) -> str:
    return "\n\n".join(
        [
            "Você redige, em nome do usuário, mensagens prontas para uma pessoa específica: uma mensagem "
            "base a partir do objetivo e da pessoa e, se houver, ganchos de notícia dos assuntos "
            "selecionados.",
            _bloco_quem_escreve(entrada),
            _bloco_para_quem(entrada),
            _bloco_pedido(entrada),
            _bloco_historico(entrada),
            _bloco_assuntos(entrada),
            _regras(),
            "EXEMPLO RESOLVIDO (outro cenário; só o formato e o tom valem):\n" + _EXEMPLO,
            "AGORA FAÇA O MESMO PARA OS DADOS ACIMA. JSON:",
        ]
    )


def cortar_por_tamanho(entrada: EntradaRedacao, limite_tokens: int = LIMITE_TOKENS_PADRAO) -> EntradaRedacao:
    """Se o prompt estimado passa de `limite_tokens`, fica com 1 consulta de histórico e 5 fatos."""
    if estimar_tokens(_montar(entrada)) <= limite_tokens:
        return entrada
    return replace(
        entrada, historico=entrada.historico[:_HISTORICO_NO_CORTE], fatos=entrada.fatos[:_FATOS_NO_CORTE]
    )


def construir_prompt(entrada: EntradaRedacao, limite_tokens: int = LIMITE_TOKENS_PADRAO) -> str:
    return _montar(cortar_por_tamanho(entrada, limite_tokens))
