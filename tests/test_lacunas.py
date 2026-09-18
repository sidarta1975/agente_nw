from __future__ import annotations

from agente_nw.nucleo.modelos.perfil import Perfil
from agente_nw.perfil.lacunas import ORDEM_IMPACTO, campos_faltando

_CAMPOS_BASE = {
    "tipo": "contato",
    "nome": "Fulano",
    "criado_em": "2026-01-01T00:00:00+00:00",
    "atualizado_em": "2026-01-01T00:00:00+00:00",
}


def test_perfil_totalmente_vazio_devolve_ordem_inteira() -> None:
    perfil = Perfil(**_CAMPOS_BASE)
    assert campos_faltando(perfil) == list(ORDEM_IMPACTO)


def test_perfil_parcialmente_preenchido_devolve_so_os_vazios_na_ordem() -> None:
    perfil = Perfil(**_CAMPOS_BASE, cargo="Advogado", cidade="Santos", linguas=["inglês"])
    faltando = campos_faltando(perfil)

    assert "cargo" not in faltando
    assert "cidade" not in faltando
    assert "linguas" not in faltando
    assert faltando == ["setor", "empresa", "formacao", "naturalidade", "tem_filhos", "faixa_etaria"]


def test_tem_filhos_false_nao_conta_como_vazio() -> None:
    perfil = Perfil(**_CAMPOS_BASE, tem_filhos=False)
    assert "tem_filhos" not in campos_faltando(perfil)
