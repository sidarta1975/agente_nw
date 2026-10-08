from __future__ import annotations

from typing import Protocol, TypeVar

from pydantic import BaseModel, ConfigDict

from agente_nw.nucleo.llm import FalhaJsonInvalido


class RespostaCapturaRedeSocial(BaseModel):
    """Extração estruturada de um bloco capturado da página de uma rede social.

    Se `descartar` for verdadeiro, o bloco não é uma publicação/curtida/comentário
    (é UI, propaganda, sugestão de conexão, etc.) e o orquestrador o ignora."""

    model_config = ConfigDict(frozen=True)

    descartar: bool
    data_do_fato: str | None = None
    tipo: str = "publicacao"
    conteudo: str = ""


_EsquemaT = TypeVar("_EsquemaT", bound=BaseModel)


class ClienteExtracao(Protocol):
    def gerar_json(self, tarefa: str, prompt: str, esquema: type[_EsquemaT]) -> _EsquemaT: ...


_CATEGORIAS_PROIBIDAS = """\
- saúde (doenças, tratamentos, condições físicas ou mentais)
- religião
- posição política ou partidária
- sindicalização ou participação em movimento sindical
- orientação ou vida sexual
- raça, etnia ou cor
- dados de menores de idade\
"""


def construir_prompt(bloco: str, rede: str) -> str:
    return f"""\
Você recebe um bloco de texto capturado da página de uma rede social ({rede}).
O bloco pode ser uma publicação, uma curtida, um comentário, uma reação — ou
pode ser texto de interface (menu, rodapé, propaganda, sugestão de conexão,
notificação do sistema).

Responda só com um objeto JSON, sem texto antes ou depois, com este formato:
{{"descartar": bool, "data_do_fato": "AAAA-MM-DD" ou null, "tipo": "...", "conteudo": "..."}}

Se o bloco NÃO for uma publicação/curtida/comentário atribuível a alguém
(por exemplo: menu de navegação, botão, propaganda, sugestão, texto de
sistema, campo vazio), devolva {{"descartar": true, "data_do_fato": null,
"tipo": "", "conteudo": ""}}.

Se for uma publicação/curtida/comentário, devolva descartar=false e preencha:
- data_do_fato: só se houver data explícita no texto (formato AAAA-MM-DD).
  Datas relativas ("2 dias atrás", "há 3 horas") devem devolver null.
- tipo: uma palavra curta que classifique — "publicacao", "curtida",
  "comentario", "reacao", "repost".
- conteudo: o texto essencial da publicação, limpo, sem sugestões laterais
  nem prompts de interface. Sem chamar atenção do modelo para nada que não
  esteja no bloco.

Nunca extraia informação sobre estas categorias sensíveis; se o bloco tocar
em uma delas, devolva descartar=true e não repita o trecho:
{_CATEGORIAS_PROIBIDAS}

Bloco a processar:
"{bloco}"
"""


def extrair(cliente_llm: ClienteExtracao, bloco: str, rede: str) -> RespostaCapturaRedeSocial | None:
    """Devolve a resposta extraída, ou `None` se o bloco deve ser descartado
    (LLM disse `descartar` ou falhou a validação de JSON após as tentativas
    do cliente). Nunca lança para o chamador."""
    prompt = construir_prompt(bloco, rede)
    try:
        resposta = cliente_llm.gerar_json("extrair_captura_rede_social", prompt, RespostaCapturaRedeSocial)
    except FalhaJsonInvalido:
        return None
    if resposta.descartar or not resposta.conteudo.strip():
        return None
    return resposta
