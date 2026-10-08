from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from agente_nw.coleta.capturas import extrator
from agente_nw.coleta.capturas.extrator import RespostaCapturaRedeSocial
from agente_nw.nucleo.llm import FalhaJsonInvalido


class _ClienteFake:
    def __init__(self, resposta_ou_erro: object) -> None:
        self._resposta_ou_erro = resposta_ou_erro
        self.tarefa_recebida: str | None = None
        self.prompt_recebido: str | None = None

    def gerar_json(self, tarefa: str, prompt: str, esquema: type[BaseModel]) -> Any:
        self.tarefa_recebida = tarefa
        self.prompt_recebido = prompt
        if isinstance(self._resposta_ou_erro, Exception):
            raise self._resposta_ou_erro
        return self._resposta_ou_erro


def test_extrair_publicacao_valida_devolve_resposta() -> None:
    resposta = RespostaCapturaRedeSocial(
        descartar=False,
        data_do_fato="2026-09-18",
        tipo="publicacao",
        conteudo="Correu 10km no parque hoje",
    )
    cliente = _ClienteFake(resposta)

    resultado = extrator.extrair(cliente, "Correu 10km no parque hoje", "instagram")

    assert resultado is not None
    assert resultado.conteudo == "Correu 10km no parque hoje"
    assert resultado.data_do_fato == "2026-09-18"
    assert cliente.tarefa_recebida == "extrair_captura_rede_social"


def test_extrair_descartar_true_devolve_none() -> None:
    resposta = RespostaCapturaRedeSocial(descartar=True)
    cliente = _ClienteFake(resposta)

    resultado = extrator.extrair(cliente, "Menu · Início · Notificações", "linkedin")

    assert resultado is None


def test_extrair_conteudo_vazio_mesmo_com_descartar_false_devolve_none() -> None:
    resposta = RespostaCapturaRedeSocial(descartar=False, conteudo="   ")
    cliente = _ClienteFake(resposta)

    resultado = extrator.extrair(cliente, "algum bloco", "x")

    assert resultado is None


def test_extrair_falha_json_invalido_devolve_none_sem_levantar() -> None:
    cliente = _ClienteFake(FalhaJsonInvalido("extrair_captura_rede_social", 1, "json ruim"))

    resultado = extrator.extrair(cliente, "algum bloco", "facebook")

    assert resultado is None
