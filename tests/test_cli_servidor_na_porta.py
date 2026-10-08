from __future__ import annotations

import pytest

from agente_nw.cli import _classificar_processo, _porta_de

APP = "/Applications/Ollama.app/Contents/Resources/ollama serve"
BREW = "/opt/homebrew/bin/ollama serve"


def test_classifica_ollama_app() -> None:
    assert _classificar_processo(APP, 100, {}) == "Ollama.app"


def test_classifica_launchagent_do_projeto_quando_pid_coincide() -> None:
    assert _classificar_processo(BREW, 200, {"br.agente_nw.ollama": 200}) == "LaunchAgent do projeto"


def test_classifica_outra_instancia_sem_rotulo_ou_com_pid_diferente() -> None:
    assert _classificar_processo(BREW, 300, {}) == "outra instância"
    assert _classificar_processo(BREW, 300, {"br.agente_nw.ollama": 999}) == "outra instância"


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
