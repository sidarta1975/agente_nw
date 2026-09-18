from __future__ import annotations

from agente_nw.nucleo.modelos.extracao import RespostaExtracaoTexto

ESQUEMA = RespostaExtracaoTexto

_GUIA_CAMPOS = """\
- cidade: a cidade onde a pessoa mora ou trabalha hoje.
- naturalidade: a cidade onde a pessoa nasceu.
- linguas: lista de idiomas que a pessoa fala, além do português.
- formacao: curso, área ou instituição de formação da pessoa.
- cargo: o cargo ou função que a pessoa ocupa hoje.
- setor: o setor ou ramo de atividade da empresa ou área da pessoa.
- empresa: o nome da empresa onde a pessoa trabalha.
- tem_filhos: verdadeiro ou falso, só se o texto mencionar filhos de forma explícita.
- faixa_etaria: uma faixa aproximada de idade (ex.: "30-40"), nunca a idade exata.\
"""

_CATEGORIAS_PROIBIDAS = """\
- saúde (doenças, tratamentos, condições físicas ou mentais)
- religião
- posição política ou partidária
- sindicalização ou participação em movimento sindical
- orientação ou vida sexual
- raça, etnia ou cor
- dados de menores de idade (nome, idade exata ou identificação de filhos menores)\
"""

_EXEMPLO_ENTRADA = (
    "Beatriz é advogada tributarista em Belo Horizonte. Joga xadrez nas noites de "
    "sexta e participa de um clube de leitura de ficção científica."
)

# Duas tags no exemplo, de propósito: um exemplo com uma tag só não ensina o modelo
# a fechar um objeto de tag e abrir o próximo corretamente — era exatamente onde a
# geração real quebrava (primeira tag sempre certa, segunda tag com chave errada ou
# JSON truncado). O nome, cidade e cargo do exemplo são deliberadamente diferentes
# de qualquer texto real de teste — um exemplo parecido demais com a entrada real
# (mesmo nome, mesma cidade, mesmo cargo) faz o modelo copiar conteúdo do exemplo
# em vez de extrair só o que está no texto de verdade (visto na prática: "cabotagem"
# aparecendo numa extração que não mencionava cabotagem). Ver docs/PLAN.md, dívida
# sobre confiabilidade do extrator (brief 004).
_EXEMPLO_SAIDA = (
    '{"campos": {"cidade": "Belo Horizonte", "cargo": "advogada tributarista"}, '
    '"tags_sugeridas": ['
    '{"tag": "xadrez", "peso": 2, "trecho": "joga xadrez nas noites de sexta"}, '
    '{"tag": "ficção científica", "peso": 2, '
    '"trecho": "participa de um clube de leitura de ficção científica"}'
    "], "
    '"fatos_datados": []}'
)


def construir_prompt(texto: str) -> str:
    """Monta o prompt do contrato ``extrair_de_texto`` para um texto livre.

    A saída deve validar contra :class:`RespostaExtracaoTexto` (``ESQUEMA``
    acima) — é esse o vínculo entre este prompt e o esquema do passo 3 do
    brief: quem chama ``ClienteOllama.gerar_json`` passa os dois juntos.
    """
    return f"""\
Você recebe um texto livre sobre um contato de uma agenda pessoal e extrai só
o que está explicitamente escrito — nunca infira nem invente o que não está
no texto.

Responda só com um objeto JSON, sem texto antes ou depois, no formato exato:
{{"campos": {{...}}, "tags_sugeridas": [...], "fatos_datados": [...]}}

"campos" — só estes campos, e só quando o texto disser algo explícito sobre
eles (omita ou deixe nulo o que não estiver no texto):
{_GUIA_CAMPOS}

"tags_sugeridas" — cada tema, assunto ou interesse do contato que o texto
revele, como uma lista de objetos {{"tag": "...", "peso": 1 a 5, "trecho":
"..."}}. "peso" é o quão central o tema parece ser para a pessoa (1 = citado
de passagem, 5 = claramente central). "trecho" é a frase do texto original
que justifica a tag — sempre obrigatório, nunca invente um trecho que não
esteja no texto.

"fatos_datados" — eventos ou acontecimentos com data, como uma lista de
objetos {{"data": "AAAA-MM-DD ou null", "tipo": "...", "conteudo": "...",
"fonte": "... ou null"}}. Se o texto não mencionar nenhum evento datado,
devolva uma lista vazia.

Nunca extraia nem mencione, em nenhum campo, tag ou fato, informação sobre
estas categorias — se o texto tocar em uma delas, simplesmente ignore aquele
trecho e extraia só o resto:
{_CATEGORIAS_PROIBIDAS}

Exemplo resolvido:
Texto: "{_EXEMPLO_ENTRADA}"
JSON: {_EXEMPLO_SAIDA}

Texto a processar:
"{texto}"
"""
