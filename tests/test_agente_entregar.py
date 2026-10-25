from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
GIT_REAL = shutil.which("git") or "git"

GIT_FALSO = f"""#!/usr/bin/env bash
if [ "$1" = push ]; then
  echo "$@" >> "$PUSH_LOG"
  exit "${{FAKE_PUSH_EXIT:-0}}"
fi
exec {GIT_REAL} "$@"
"""

VERIFICAR_FALSO = """#!/usr/bin/env bash
echo rodou >> "$(dirname "$0")/../gate_rodou.txt"
echo "ruff check: ok"
exit "${FAKE_GATE_EXIT:-0}"
"""


def _git(repo: Path, *args: str) -> str:
    saida = subprocess.run([GIT_REAL, *args], cwd=repo, capture_output=True, text=True, check=True)
    return saida.stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    pasta = tmp_path / "repo"
    (pasta / "scripts").mkdir(parents=True)
    for nome in ("agente_entregar.sh", "commitar.sh"):
        shutil.copy(RAIZ / "scripts" / nome, pasta / "scripts" / nome)
    (pasta / "scripts" / "verificar.sh").write_text(VERIFICAR_FALSO)
    for nome in ("agente_entregar.sh", "commitar.sh", "verificar.sh"):
        (pasta / "scripts" / nome).chmod(0o755)
    (pasta / ".gitignore").write_text("/logs/\n/gate_rodou.txt\n")
    (pasta / "base.txt").write_text("base\n")
    _git(pasta, "init", "-b", "main")
    _git(pasta, "config", "user.email", "teste@example.com")
    _git(pasta, "config", "user.name", "Teste")
    _git(pasta, "add", "--", ".gitignore", "base.txt", "scripts")
    _git(pasta, "commit", "-m", "inicial")
    (pasta / "logs").mkdir()
    (pasta / "novo.txt").write_text("novo\n")
    (pasta / "logs" / "commit_001.txt").write_text("feat: arquivo novo (brief 001)\n")
    (pasta / "logs" / "arquivos_001.txt").write_text("novo.txt\n")
    return pasta


@pytest.fixture
def ambiente(tmp_path: Path) -> dict[str, str]:
    bin_falso = tmp_path / "bin"
    bin_falso.mkdir()
    git = bin_falso / "git"
    git.write_text(GIT_FALSO)
    git.chmod(0o755)
    return {
        **os.environ,
        "PATH": f"{bin_falso}{os.pathsep}{os.environ['PATH']}",
        "PUSH_LOG": str(tmp_path / "push.log"),
    }


def _entregar(
    repo: Path, ambiente: dict[str, str], *args: str, extra: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "scripts/agente_entregar.sh", *args],
        cwd=repo,
        env={**ambiente, **(extra or {})},
        capture_output=True,
        text=True,
        check=False,
    )


def _pushes(ambiente: dict[str, str]) -> str:
    log = Path(ambiente["PUSH_LOG"])
    return log.read_text() if log.exists() else ""


def test_manifesto_completo_faz_gate_commit_push_e_renomeia(repo: Path, ambiente: dict[str, str]) -> None:
    antes = _git(repo, "rev-parse", "HEAD")

    resultado = _entregar(repo, ambiente)

    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    depois = _git(repo, "rev-parse", "HEAD")
    assert depois != antes
    assert _git(repo, "log", "-1", "--format=%s") == "feat: arquivo novo (brief 001)"
    assert "push" in _pushes(ambiente)
    assert (repo / "gate_rodou.txt").exists()
    assert not (repo / "logs" / "commit_001.txt").exists()
    assert (repo / "logs" / "entregue_001_commit.txt").exists()
    assert (repo / "logs" / "entregue_001_arquivos.txt").exists()
    linhas = resultado.stdout.strip().splitlines()
    assert len(linhas) <= 10
    curto = _git(repo, "rev-parse", "--short", "HEAD")
    assert linhas[-1] == f"✓ brief 001: commit {curto}, enviado ao GitHub"
    assert (repo / "logs" / "entregar_ultimo.txt").exists()


def test_arquivo_fora_da_lista_para_antes_do_gate(repo: Path, ambiente: dict[str, str]) -> None:
    (repo / "intruso.txt").write_text("fora\n")
    antes = _git(repo, "rev-parse", "HEAD")

    resultado = _entregar(repo, ambiente)

    assert resultado.returncode != 0
    assert "intruso.txt" in resultado.stdout + resultado.stderr
    assert _git(repo, "rev-parse", "HEAD") == antes
    assert not (repo / "gate_rodou.txt").exists()
    assert _pushes(ambiente) == ""
    assert (repo / "logs" / "commit_001.txt").exists()


def test_gate_falhando_para_sem_commit(repo: Path, ambiente: dict[str, str]) -> None:
    antes = _git(repo, "rev-parse", "HEAD")

    resultado = _entregar(repo, ambiente, extra={"FAKE_GATE_EXIT": "1"})

    assert resultado.returncode != 0
    assert _git(repo, "rev-parse", "HEAD") == antes
    assert _pushes(ambiente) == ""
    assert (repo / "logs" / "commit_001.txt").exists()


def test_simular_nao_toca_no_git_nem_roda_o_gate(repo: Path, ambiente: dict[str, str]) -> None:
    antes = _git(repo, "rev-parse", "HEAD")

    resultado = _entregar(repo, ambiente, "--simular", "001")

    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    assert _git(repo, "rev-parse", "HEAD") == antes
    assert not (repo / "gate_rodou.txt").exists()
    assert _pushes(ambiente) == ""
    assert (repo / "logs" / "commit_001.txt").exists()
    for passo in ("1.", "2.", "3.", "4.", "5.", "6.", "7."):
        assert passo in resultado.stdout


def test_push_que_falha_deixa_o_commit_local_e_avisa(repo: Path, ambiente: dict[str, str]) -> None:
    antes = _git(repo, "rev-parse", "HEAD")

    resultado = _entregar(repo, ambiente, extra={"FAKE_PUSH_EXIT": "1"})

    assert resultado.returncode != 0
    assert _git(repo, "rev-parse", "HEAD") != antes
    assert "git push" in resultado.stdout + resultado.stderr


def test_sem_argumento_usa_o_maior_numero_com_manifesto_completo(
    repo: Path, ambiente: dict[str, str]
) -> None:
    (repo / "logs" / "commit_002.txt").write_text("feat: sem lista (brief 002)\n")

    resultado = _entregar(repo, ambiente)

    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    assert "brief 001" in resultado.stdout.strip().splitlines()[-1]
