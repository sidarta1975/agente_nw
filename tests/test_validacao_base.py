from __future__ import annotations

import pytest
from pydantic import ValidationError

from agente_nw.nucleo.modelos.redacao import MAXIMO_GANCHOS, Gancho, validar_ganchos


def _base(mensagem: str = "Oi, Irene! Vi seu trabalho e queria te convidar para um jantar.") -> Gancho:
    return Gancho(por_que_para_esta_pessoa="Pelo trabalho dela.", mensagem=mensagem)


def _noticia(assunto_id: int) -> Gancho:
    return Gancho(
        assunto_id=assunto_id,
        titulo="Título",
        noticia="Uma frase. Outra frase.",
        por_que_para_esta_pessoa="Ela trabalha com isso.",
        mensagem="Oi, Irene! Vi uma notícia e lembrei de você.",
    )


def test_a_base_pula_as_checagens_de_assunto() -> None:
    aceitos, motivos = validar_ganchos([_base()], "cordial", [], set(), "whatsapp", set())

    assert [g.assunto_id for g in aceitos] == [None] and motivos == []


def test_gancho_de_noticia_mantem_todas_as_checagens() -> None:
    ganchos = [_noticia(1), _noticia(1), _noticia(2), _noticia(3)]

    aceitos, motivos = validar_ganchos(ganchos, "cordial", [], {1, 3}, "whatsapp", {3})

    assert [g.assunto_id for g in aceitos] == [1]
    assert any("repetido" in m for m in motivos)
    assert any("não foi selecionado" in m for m in motivos)
    assert any("já usado" in m for m in motivos)


def test_a_base_respeita_evitar_e_limite_de_palavras() -> None:
    com_termo = _base("Oi! Vamos falar de eleição?")
    longa = _base(" ".join(["palavra"] * 200))

    aceitos, motivos = validar_ganchos([com_termo, longa], "cordial", ["eleicao"], set(), "whatsapp", set())

    assert aceitos == []
    assert any("eleicao" in m for m in motivos) and any("limite 80" in m for m in motivos)


def test_so_fica_uma_base_e_ela_vai_antes_e_o_limite_de_noticias_vale() -> None:
    ganchos = [_noticia(i) for i in range(1, MAXIMO_GANCHOS + 3)] + [_base(), _base()]
    validos = set(range(1, MAXIMO_GANCHOS + 3))

    aceitos, motivos = validar_ganchos(ganchos, "cordial", [], validos, "whatsapp", set())

    assert aceitos[0].assunto_id is None
    assert len(aceitos) == 1 + MAXIMO_GANCHOS
    assert any("já existe uma mensagem base" in m for m in motivos)


def test_gancho_com_assunto_sem_titulo_ou_noticia_nao_e_valido() -> None:
    with pytest.raises(ValidationError):
        Gancho(assunto_id=1, por_que_para_esta_pessoa="x", mensagem="y")


def test_base_sem_por_que_e_valida_mas_gancho_de_noticia_sem_por_que_nao() -> None:
    assert Gancho(mensagem="Oi, Irene!").por_que_para_esta_pessoa == ""
    with pytest.raises(ValidationError):
        Gancho(assunto_id=1, titulo="t", noticia="n", mensagem="Oi!")
