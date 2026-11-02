"""Módulos de prompt. Todo módulo deste pacote declara `VERSAO = "AAAA-MM-DD-n"` (data do último ajuste
de conteúdo do prompt e um número sequencial no dia) — brief 066. `verificar_versoes` roda na carga da
configuração (`config.container.configuracao`) e impede o start se algum módulo não declarar."""

from __future__ import annotations

import importlib
import pkgutil
import re

_FORMATO_VERSAO = re.compile(r"^\d{4}-\d{2}-\d{2}-\d+$")


def verificar_versoes() -> None:
    """Falha com `RuntimeError` citando cada módulo de prompt sem `VERSAO` no formato `AAAA-MM-DD-n`."""
    faltando: list[str] = []
    for modulo_info in pkgutil.iter_modules(__path__):
        if modulo_info.ispkg:
            continue
        modulo = importlib.import_module(f"{__name__}.{modulo_info.name}")
        versao = getattr(modulo, "VERSAO", None)
        if not isinstance(versao, str) or _FORMATO_VERSAO.fullmatch(versao) is None:
            faltando.append(modulo_info.name)
    if faltando:
        raise RuntimeError(
            'módulo(s) de prompt sem VERSAO = "AAAA-MM-DD-n" em agente_nw/nucleo/prompts/: '
            + ", ".join(sorted(faltando))
        )
