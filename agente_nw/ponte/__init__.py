from __future__ import annotations

import atexit

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


def abrir_ponte(espera_conexao_s: float = 20.0, porta: int = PORTA_PADRAO) -> Ponte:
    """Sobe a ponte (servidor local). O navegador só é aberto na primeira tarefa enviada."""
    ponte = Ponte(porta=porta, espera_conexao_s=espera_conexao_s)
    ponte.iniciar()
    return ponte


def obter_ponte(espera_conexao_s: float = 20.0) -> Ponte:
    """A ponte única deste processo: criada na primeira chamada e fechada ao sair."""
    global _PONTE
    if _PONTE is None:
        _PONTE = abrir_ponte(espera_conexao_s)
        atexit.register(_PONTE.fechar)
    return _PONTE
