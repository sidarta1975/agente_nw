from __future__ import annotations

import atexit
import subprocess
import sys
from collections.abc import Callable

from agente_nw.ponte.servidor import (
    ID_EXTENSAO,
    PORTA_PADRAO,
    ErroDaExtensao,
    Ponte,
    PonteIndisponivel,
)

__all__ = [
    "ID_EXTENSAO",
    "PORTA_PADRAO",
    "ErroDaExtensao",
    "Ponte",
    "PonteIndisponivel",
    "abrir_ponte",
    "obter_ponte",
]

_PONTE: Ponte | None = None


def _abridor(aplicativo: str | None) -> Callable[[str], object] | None:
    """No macOS abre o endereço no aplicativo indicado (o padrão do sistema pode ser outro navegador)."""
    if not aplicativo or sys.platform != "darwin":
        return None

    def abrir(url: str) -> object:
        return subprocess.run(["open", "-a", aplicativo, url], check=False, capture_output=True)

    return abrir


def abrir_ponte(
    espera_conexao_s: float = 20.0, porta: int = PORTA_PADRAO, aplicativo: str | None = None
) -> Ponte:
    """Sobe a ponte (servidor local). O navegador só é aberto na primeira tarefa enviada."""
    ponte = Ponte(porta=porta, espera_conexao_s=espera_conexao_s, abrir_navegador=_abridor(aplicativo))
    ponte.iniciar()
    return ponte


def obter_ponte(espera_conexao_s: float = 20.0, aplicativo: str | None = None) -> Ponte:
    """A ponte única deste processo: criada na primeira chamada e fechada ao sair."""
    global _PONTE
    if _PONTE is None:
        _PONTE = abrir_ponte(espera_conexao_s, aplicativo=aplicativo)
        atexit.register(_PONTE.fechar)
    return _PONTE
