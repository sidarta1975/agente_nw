from __future__ import annotations

from agente_nw.nucleo.modelos.perfil import Perfil

ORDEM_IMPACTO: tuple[str, ...] = (
    "cargo",
    "setor",
    "empresa",
    "cidade",
    "linguas",
    "formacao",
    "naturalidade",
    "tem_filhos",
    "faixa_etaria",
)


def campos_faltando(perfil: Perfil) -> list[str]:
    faltando = []
    for campo in ORDEM_IMPACTO:
        valor = getattr(perfil, campo)
        vazio = valor is None or (isinstance(valor, list) and not valor)
        if vazio:
            faltando.append(campo)
    return faltando
