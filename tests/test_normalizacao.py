from __future__ import annotations

from agente_nw.perfil.normalizacao import telefone_e164


def test_numero_ja_em_e164() -> None:
    assert telefone_e164("+5511987654321") == "+5511987654321"


def test_numero_nacional_sem_codigo_de_pais_assume_br() -> None:
    assert telefone_e164("11987654321") == "+5511987654321"
    assert telefone_e164("(11) 98765-4321") == "+5511987654321"


def test_numero_claramente_invalido_devolve_none() -> None:
    assert telefone_e164("abc") is None
    assert telefone_e164("123") is None


def test_entrada_vazia_ou_nula_devolve_none() -> None:
    assert telefone_e164(None) is None
    assert telefone_e164("") is None
    assert telefone_e164("   ") is None
