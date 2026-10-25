from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parent.parent / ".claude" / "hooks" / "guarda_comando.py"


def _executar(entrada: str) -> tuple[int, str, str]:
    comando = [sys.executable, str(HOOK)]
    saida = subprocess.run(comando, input=entrada, capture_output=True, text=True, check=False)
    return saida.returncode, saida.stdout, saida.stderr


def _rodar(comando: str, cwd: Path) -> tuple[int, str, str]:
    return _executar(json.dumps({"tool_name": "Bash", "tool_input": {"command": comando}, "cwd": str(cwd)}))


@pytest.fixture
def pasta_principal(tmp_path: Path) -> Path:
    (tmp_path / ".git").mkdir()
    return tmp_path


@pytest.mark.parametrize(
    "comando",
    [
        "git commit -m x",
        "git add AGENTS.md",
        "git push",
        "git -C . push origin main",
        "git reset --hard",
        "git stash",
        "git branch -D velha",
        "git push --force",
        "rm -rf /Users/sidarta48/github/agente_nw/docs",
        "rm -rf /Users/sidarta48/github",
        "cd /tmp && rm -rf /etc/x",
        "git worktree add ../x",
        "cd /tmp && git commit -m x",
        "echo ok; git add .",
        "bash -c 'git commit -m x'",
        "echo $(git add .)",
        "bash scripts/commitar.sh logs/commit_1.txt a.py",
        "sqlite3 dados/agente.db .tables",
        'agente_nw pedir "mensagem para o Ricardo"',
        "agente_nw ler-rede-social --rede x",
        "agente_nw listas ver --rede instagram",
        "agente_nw extensao testar",
    ],
)
def test_bloqueia(comando: str, pasta_principal: Path) -> None:
    codigo, _saida, erro = _rodar(comando, pasta_principal)
    assert codigo == 2
    assert erro.strip()


@pytest.mark.parametrize(
    "comando",
    [
        "git status",
        "git diff --stat",
        "git log --oneline -3",
        "git show HEAD",
        "git branch",
        "pytest",
        "pytest -q tests/",
        ".venv/bin/pytest -q",
        "python -m pytest",
        "mypy agente_nw",
        "ruff format .",
        "scripts/verificar.sh",
        "scripts/agente_entregar.sh 058",
        "./scripts/agente_entregar.sh --simular 058",
        "rm -rf logs/velho",
        "rm -rf /tmp/qualquer",
        "rm arquivo.txt",
        "pytest tests/test_x.py -q",
        ".venv/bin/pytest -q tests/test_x.py::test_a",
        "pytest -m llm_real tests/test_extrator.py",
        "ruff check .",
        "ls docs",
        "cat scripts/verificar.sh",
        "grep -n commitar scripts/commitar.sh",
        "agente_nw copiar-banco",
        "agente_nw verificar-ambiente",
        "agente_nw --help",
        "agente_nw ficha --help",
    ],
)
def test_deixa_passar_em_silencio(comando: str, pasta_principal: Path) -> None:
    codigo, saida, erro = _rodar(comando, pasta_principal)
    assert codigo == 0
    assert saida == ""
    assert erro == ""


def test_subcomando_do_programa_na_pasta_principal_pede_confirmacao(pasta_principal: Path) -> None:
    codigo, saida, _erro = _rodar("agente_nw ficha 3", pasta_principal)
    assert codigo == 0
    decisao = json.loads(saida)["hookSpecificOutput"]
    assert decisao["hookEventName"] == "PreToolUse"
    assert decisao["permissionDecision"] == "ask"
    assert decisao["permissionDecisionReason"]


def test_subcomando_do_programa_fora_da_pasta_principal_passa(tmp_path: Path) -> None:
    (tmp_path / ".git").write_text("gitdir: ../principal/.git/worktrees/dev\n")
    assert _rodar("agente_nw ficha 3", tmp_path) == (0, "", "")


def test_bloqueio_vale_tambem_fora_da_pasta_principal(tmp_path: Path) -> None:
    (tmp_path / ".git").write_text("gitdir: ../principal/.git/worktrees/dev\n")
    codigo, _saida, _erro = _rodar("git commit -m x", tmp_path)
    assert codigo == 2


def test_ferramenta_que_nao_e_bash_passa(pasta_principal: Path) -> None:
    pedido = {"tool_name": "Read", "tool_input": {"file_path": "AGENTS.md"}, "cwd": str(pasta_principal)}
    assert _executar(json.dumps(pedido)) == (0, "", "")


def test_entrada_ilegivel_nao_derruba_a_sessao() -> None:
    codigo, _saida, _erro = _executar("isto não é json")
    assert codigo == 0
