from __future__ import annotations

import atexit
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

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


def _comando_de_abertura(aplicativo: str, perfil: str | None, url: str) -> list[str]:
    """Comando que abre `url` no macOS. Com `perfil`, chama o executável do navegador, que entrega a
    aba ao Chrome já aberto naquele perfil (`open --args` só vale ao abrir uma instância nova, e sem o
    perfil a aba cai no último perfil usado, que pode ser um sem a extensão)."""
    executavel = Path("/Applications") / f"{aplicativo}.app" / "Contents" / "MacOS" / aplicativo
    if perfil and executavel.exists():
        return [str(executavel), f"--profile-directory={perfil}", url]
    return ["open", "-a", aplicativo, url]


def _abridor(aplicativo: str | None, perfil: str | None = None) -> Callable[[str], object] | None:
    """No macOS abre o endereço no aplicativo (e perfil) indicados; o padrão do sistema pode ser outro
    navegador."""
    if not aplicativo or sys.platform != "darwin":
        return None

    def abrir(url: str) -> object:
        # Popen sem esperar: numa instância nova o executável só termina quando o Chrome fecha.
        return subprocess.Popen(
            _comando_de_abertura(aplicativo, perfil, url),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

    return abrir


def abrir_ponte(
    espera_conexao_s: float = 20.0,
    porta: int = PORTA_PADRAO,
    aplicativo: str | None = None,
    perfil: str | None = None,
) -> Ponte:
    """Sobe a ponte (servidor local). O navegador só é aberto na primeira tarefa enviada."""
    ponte = Ponte(
        porta=porta,
        espera_conexao_s=espera_conexao_s,
        abrir_navegador=_abridor(aplicativo, perfil),
        aquecer=True,
    )
    ponte.iniciar()
    return ponte


def obter_ponte(
    espera_conexao_s: float = 20.0, aplicativo: str | None = None, perfil: str | None = None
) -> Ponte:
    """A ponte única deste processo: criada na primeira chamada e fechada ao sair."""
    global _PONTE
    if _PONTE is None:
        _PONTE = abrir_ponte(espera_conexao_s, aplicativo=aplicativo, perfil=perfil)
        atexit.register(_PONTE.fechar)
    return _PONTE
