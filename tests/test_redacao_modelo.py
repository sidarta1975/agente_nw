from __future__ import annotations

import pytest
from pydantic import ValidationError

from agente_nw.nucleo.modelos.redacao import (
    MAXIMO_GANCHOS,
    Gancho,
    Redacao,
    validar_ganchos,
)


def _mensagem(palavras: int) -> str:
    return " ".join(["palavra"] * palavras)


def _gancho(
    assunto_id: int = 1, mensagem: str = "Oi, vi uma notícia e lembrei de você.", **extra: object
) -> Gancho:
    dados: dict[str, object] = {
        "assunto_id": assunto_id,
        "titulo": "Título curto",
        "noticia": "Primeira frase. Segunda frase.",
        "por_que_para_esta_pessoa": "Ela trabalha com isso.",
        "mensagem": mensagem,
    }
    dados.update(extra)
    return Gancho.model_validate(dados)


def _validar(
    ganchos: list[Gancho],
    registro: str = "cordial",
    evitar: list[str] | None = None,
    validos: set[int] | None = None,
    meio: str = "whatsapp",
    usados: set[int] | None = None,
) -> tuple[list[Gancho], list[str]]:
    return validar_ganchos(
        ganchos,
        registro,
        evitar or [],
        validos if validos is not None else {1, 2, 3, 4, 5},
        meio,
        usados or set(),
    )


@pytest.mark.parametrize(("registro", "limite"), [("proximo", 60), ("cordial", 80), ("formal", 110)])
def test_limite_de_palavras_por_registro(registro: str, limite: int) -> None:
    dentro, motivos_dentro = _validar([_gancho(mensagem=_mensagem(limite))], registro)
    fora, motivos_fora = _validar([_gancho(mensagem=_mensagem(limite + 1))], registro)

    assert len(dentro) == 1 and motivos_dentro == []
    assert fora == []
    assert f"limite {limite}" in motivos_fora[0]


def test_termo_de_evitar_na_mensagem_rejeita_o_gancho_e_explica() -> None:
    ganchos = [_gancho(1, "Vi uma matéria sobre POLÍTICA hoje."), _gancho(2)]

    aceitos, motivos = _validar(ganchos, evitar=["politica"])

    assert [g.assunto_id for g in aceitos] == [2]
    assert "politica" in motivos[0]


def test_assunto_desconhecido_e_rejeitado() -> None:
    aceitos, motivos = _validar([_gancho(99)], validos={1, 2})

    assert aceitos == []
    assert "não foi selecionado" in motivos[0]


def test_assunto_duplicado_fica_so_o_primeiro() -> None:
    aceitos, motivos = _validar([_gancho(1, "Primeira versão."), _gancho(1, "Segunda versão.")])

    assert [g.mensagem for g in aceitos] == ["Primeira versão."]
    assert "repetido" in motivos[0]


def test_assunto_ja_usado_e_rejeitado() -> None:
    aceitos, motivos = _validar([_gancho(1), _gancho(2)], usados={1})

    assert [g.assunto_id for g in aceitos] == [2]
    assert "já usado" in motivos[0]


def test_titulo_com_mais_de_doze_palavras_e_rejeitado() -> None:
    aceitos, motivos = _validar([_gancho(titulo=_mensagem(13))])

    assert aceitos == []
    assert "título" in motivos[0]


def test_abordagem_presencial_so_fica_quando_o_meio_e_pessoalmente() -> None:
    com_abordagem = _gancho(abordagem_presencial="Comece perguntando da família.")

    presencial, _ = _validar([com_abordagem], meio="pessoalmente")
    zap, _ = _validar([com_abordagem], meio="whatsapp")

    assert presencial[0].abordagem_presencial == "Comece perguntando da família."
    assert zap[0].abordagem_presencial is None


def test_abordagem_vazia_vira_none() -> None:
    assert _gancho(abordagem_presencial="   ").abordagem_presencial is None


def test_campo_obrigatorio_vazio_nao_valida() -> None:
    with pytest.raises(ValidationError):
        _gancho(mensagem="")


def test_no_maximo_quatro_ganchos() -> None:
    aceitos, _ = _validar([_gancho(i) for i in range(1, 6)])

    assert len(aceitos) == MAXIMO_GANCHOS


def test_lista_vazia_e_aceita_com_aviso() -> None:
    redacao = Redacao(ganchos=[], aviso="Nenhum assunto qualificado.", registro_usado="cordial")

    assert redacao.ganchos == []
    assert redacao.aviso == "Nenhum assunto qualificado."
