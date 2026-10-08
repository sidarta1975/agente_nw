from __future__ import annotations

import pytest

from agente_nw.cli import _classificar_processo, _porta_de

APP = "/Applications/Ollama.app/Contents/Resources/ollama serve"
BREW = "/opt/homebrew/bin/ollama serve"


def test_classifica_ollama_app() -> None:
    assert _classificar_processo(APP) == "Ollama.app"


def test_classifica_outra_instancia() -> None:
    assert _classificar_processo(BREW) == "outra instância"


def test_classifica_desconhecido() -> None:
    assert _classificar_processo("/usr/bin/python3 servidor.py") == "desconhecido"


@pytest.mark.parametrize(
    ("url", "porta"),
    [
        ("http://127.0.0.1:11434", 11434),
        ("http://127.0.0.1:11435", 11435),
        ("http://localhost:11434/", 11434),
    ],
)
def test_porta_de(url: str, porta: int) -> None:
    assert _porta_de(url) == porta
