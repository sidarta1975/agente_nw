from __future__ import annotations

from typing import Any

from agente_nw.coleta.capturas import imagens
from agente_nw.coleta.capturas.imagens import ImagemCapturada, RespostaDescricaoImagem
from agente_nw.nucleo.llm import FalhaJsonInvalido


def _imagem(alt: str = "") -> ImagemCapturada:
    return ImagemCapturada(
        src="https://cdn.test/a.jpg",
        alt=alt,
        link="https://x.test/p/1/",
        mime="image/jpeg",
        dados_base64="QUJD",
    )


class _Visao:
    def __init__(self, resposta: RespostaDescricaoImagem | Exception) -> None:
        self._resposta = resposta
        self.chamadas: list[dict[str, Any]] = []

    def gerar_json(
        self, tarefa: str, prompt: str, esquema: type[Any], imagens: list[str] | None = None
    ) -> Any:
        self.chamadas.append({"tarefa": tarefa, "prompt": prompt, "imagens": imagens})
        if isinstance(self._resposta, Exception):
            raise self._resposta
        return self._resposta


def test_descrever_envia_a_imagem_ao_modelo_de_visao_e_devolve_o_texto() -> None:
    visao = _Visao(RespostaDescricaoImagem(descricao="  Duas pessoas numa praia ao pôr do sol.  "))

    texto = imagens.descrever(visao, _imagem(alt="foto de praia"), "instagram")

    assert texto == "Duas pessoas numa praia ao pôr do sol."
    assert visao.chamadas[0]["tarefa"] == "descrever_imagem"
    assert visao.chamadas[0]["imagens"] == ["QUJD"]
    assert "foto de praia" in visao.chamadas[0]["prompt"] and "instagram" in visao.chamadas[0]["prompt"]


def test_modelo_que_descarta_ou_devolve_vazio_nao_gera_descricao() -> None:
    descartada = _Visao(RespostaDescricaoImagem(descartar=True, descricao="x"))
    vazia = _Visao(RespostaDescricaoImagem(descricao="  "))

    assert imagens.descrever(descartada, _imagem(), "x") is None
    assert imagens.descrever(vazia, _imagem(), "x") is None


def test_descricao_de_qualquer_tema_e_mantida() -> None:
    texto = "Pessoa com camiseta de campanha política em ato, ao lado de um hospital."
    visao = _Visao(RespostaDescricaoImagem(descricao=texto))

    assert imagens.descrever(visao, _imagem(), "instagram") == texto


def test_falha_do_modelo_nao_derruba_o_chamador() -> None:
    visao = _Visao(FalhaJsonInvalido("descrever_imagem", 1, "json inválido"))

    assert imagens.descrever(visao, _imagem(), "instagram") is None
