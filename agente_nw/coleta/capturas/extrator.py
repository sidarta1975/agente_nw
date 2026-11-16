from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from typing import Protocol, TypeVar

from pydantic import BaseModel, ConfigDict

from agente_nw.nucleo import texto_integral
from agente_nw.nucleo.database.queries import fila_revisao
from agente_nw.nucleo.llm import FalhaJsonInvalido, JanelaEstourada
from agente_nw.nucleo.prompts.extrair_captura_rede_social import (
    VERSAO,
    construir_prompt,
    construir_prompt_de_parte,
)
from agente_nw.nucleo.texto_integral import Parte


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
    def gerar_json(
        self,
        tarefa: str,
        prompt: str,
        esquema: type[_EsquemaT],
        imagens: list[str] | None = None,
        versao_prompt: str | None = None,
    ) -> _EsquemaT: ...

    def num_ctx(self, tarefa_nome: str) -> int: ...


_TAREFA = "extrair_captura_rede_social"
_MOTIVO_REFEITO = "estouro de janela refeito em partes menores (brief 088)"

__all__ = ["ClienteExtracao", "RespostaCapturaRedeSocial", "construir_prompt", "extrair"]


def _consolidar(
    respostas: list[RespostaCapturaRedeSocial], bloco: str, conexao: sqlite3.Connection | None
) -> RespostaCapturaRedeSocial | None:
    """Regra de consolidação do bloco lido em partes (brief 088). As partes que o modelo descartou não
    contam; se todas foram descartadas, o bloco é descartado. `data_do_fato` e `tipo` são campos únicos:
    o valor igual em todas as partes que o deram é aceito, e valores diferentes **não são decididos por
    voto** — o bloco vai para a `fila_revisao` com o aviso (quando há `conexao`) e não é gravado.
    `conteudo` é a união ordenada dos conteúdos das partes, sem repetição exata, um por linha."""
    validas = [r for r in respostas if not r.descartar and r.conteudo.strip()]
    if not validas:
        return None
    unicos, divergencias = texto_integral.consolidar_unicos(
        [r.model_dump(include={"data_do_fato", "tipo"}, exclude_none=True) for r in validas]
    )
    if divergencias:
        if conexao is not None:
            aviso = "; ".join(d.descrever() for d in divergencias)
            valores = "\n".join(d.descrever_com_valores() for d in divergencias)
            fila_revisao.inserir(
                conexao,
                _TAREFA,
                f"Valores divergentes entre as partes:\n{valores}\n\nBloco:\n{bloco}",
                f"divergência entre partes, sem voto: {aviso}",
                datetime.now(UTC).isoformat(),
            )
            conexao.commit()
        return None
    conteudos = texto_integral.consolidar_fatos([[r.conteudo] for r in validas])
    data = unicos.get("data_do_fato")
    return RespostaCapturaRedeSocial(
        descartar=False,
        data_do_fato=data if isinstance(data, str) else None,
        tipo=str(unicos.get("tipo", "publicacao")),
        conteudo="\n".join(c.valor for c in conteudos),
    )


def extrair(
    cliente_llm: ClienteExtracao, bloco: str, rede: str, conexao: sqlite3.Connection | None = None
) -> RespostaCapturaRedeSocial | None:
    """Devolve a resposta extraída, ou `None` se o bloco deve ser descartado
    (LLM disse `descartar` ou falhou a validação de JSON após as tentativas
    do cliente). Nunca lança para o chamador.

    Bloco que não cabe numa chamada é lido em partes (`nucleo/texto_integral.py`, brief 088): parte sem
    resposta válida invalida o bloco inteiro (a parte já está na `fila_revisao`); a consolidação é a de
    `_consolidar`. `conexao` é onde a divergência entre partes vai para a revisão humana e onde se
    resolvem os estouros de janela superados por uma divisão menor."""
    orcamento = texto_integral.orcamento_do_texto(cliente_llm.num_ctx(_TAREFA), construir_prompt("", rede))

    def processar(partes: list[Parte]) -> list[RespostaCapturaRedeSocial]:
        return [
            cliente_llm.gerar_json(
                _TAREFA,
                construir_prompt_de_parte(parte, rede),
                RespostaCapturaRedeSocial,
                versao_prompt=VERSAO,
            )
            for parte in partes
        ]

    def refazer(erro: BaseException) -> None:
        if conexao is not None and isinstance(erro, FalhaJsonInvalido):
            fila_revisao.descartar(
                conexao, erro.fila_revisao_id, _MOTIVO_REFEITO, datetime.now(UTC).isoformat()
            )

    try:
        respostas, partes = texto_integral.processar_dividindo(
            bloco, orcamento, processar, JanelaEstourada, refazer
        )
    except FalhaJsonInvalido:
        return None
    if len(partes) == 1:
        [resposta] = respostas
        if resposta.descartar or not resposta.conteudo.strip():
            return None
        return resposta
    return _consolidar(respostas, bloco, conexao)
