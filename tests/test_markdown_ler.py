from __future__ import annotations

import pytest

from agente_nw.nucleo.saidas.markdown import ler_marcacoes


def _bloco(ac_id: int, corpo: str) -> str:
    return f"#### Título  <!-- ac:{ac_id} -->\nPor quê: x\n{corpo}\n"


def test_usei_marcado_e_reconhecido() -> None:
    texto = _bloco(1, "- [x] usei")

    marcacoes, avisos = ler_marcacoes(texto)

    assert avisos == []
    assert len(marcacoes) == 1
    assert marcacoes[0].ac_id == 1
    assert marcacoes[0].resultado == "usado"
    assert marcacoes[0].motivo is None


@pytest.mark.parametrize(
    "posicao,codigo_esperado",
    [(0, "nao_interessa"), (1, "velho"), (2, "raso"), (3, "nao_da_conversa"), (4, "nao_domino")],
)
def test_nao_serve_com_cada_um_dos_cinco_motivos(posicao: int, codigo_esperado: str) -> None:
    marcadores = ["( )"] * 5
    marcadores[posicao] = "(x)"
    linha = (
        "- [x] não serve → motivo: "
        f"{marcadores[0]} não interessa a ele {marcadores[1]} velho {marcadores[2]} raso "
        f"{marcadores[3]} não dá conversa {marcadores[4]} eu não domino"
    )
    texto = _bloco(1, linha)

    marcacoes, avisos = ler_marcacoes(texto)

    assert avisos == []
    assert len(marcacoes) == 1
    assert marcacoes[0].resultado == "nao_serve"
    assert marcacoes[0].motivo == codigo_esperado


def test_nao_serve_sem_motivo_marcado_vira_aviso_nao_grava() -> None:
    linha = (
        "- [x] não serve → motivo: ( ) não interessa a ele ( ) velho ( ) raso "
        "( ) não dá conversa ( ) eu não domino"
    )
    texto = _bloco(1, linha)

    marcacoes, avisos = ler_marcacoes(texto)

    assert marcacoes == []
    assert len(avisos) == 1
    assert "ac:1" in avisos[0]


def test_nao_serve_com_dois_motivos_marcados_vira_aviso_nao_grava() -> None:
    linha = (
        "- [x] não serve → motivo: (x) não interessa a ele (x) velho ( ) raso "
        "( ) não dá conversa ( ) eu não domino"
    )
    texto = _bloco(1, linha)

    marcacoes, avisos = ler_marcacoes(texto)

    assert marcacoes == []
    assert len(avisos) == 1


def test_bloco_sem_nenhuma_marcacao_e_ignorado_sem_aviso() -> None:
    linha_nao_serve = (
        "- [ ] não serve → motivo: ( ) não interessa a ele ( ) velho ( ) raso "
        "( ) não dá conversa ( ) eu não domino"
    )
    texto = _bloco(1, f"- [ ] usei\n{linha_nao_serve}")

    marcacoes, avisos = ler_marcacoes(texto)

    assert marcacoes == []
    assert avisos == []


def test_bloco_corrompido_no_meio_nao_impede_os_outros() -> None:
    texto = (
        _bloco(1, "- [x] usei")
        + _bloco(2, "isso aqui não é nem usei nem não serve, texto qualquer corrompido")
        + _bloco(3, "- [x] usei")
    )

    marcacoes, avisos = ler_marcacoes(texto)

    ids = {m.ac_id for m in marcacoes}
    assert ids == {1, 3}
    assert avisos == []
