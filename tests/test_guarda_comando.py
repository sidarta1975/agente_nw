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
        "git add AGENTS_agente_nw.md",
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
        "agente_nw listas atualizar --rede instagram",
        "agente_nw listas",
        "agente_nw listas ver --rede x && agente_nw listas atualizar --rede x",
        "agente_nw listas atualizar --rede x ; agente_nw listas ver --rede x",
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
        "agente_nw listas ver --rede instagram --filtro a",
        "agente_nw listas ver --rede linkedin",
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
    pedido = {"tool_name": "Read", "tool_input": {"file_path": "x.md"}, "cwd": str(pasta_principal)}
    assert _executar(json.dumps(pedido)) == (0, "", "")


def test_entrada_ilegivel_nao_derruba_a_sessao() -> None:
    codigo, _saida, _erro = _executar("isto não é json")
    assert codigo == 0


# --- brief 086, item 2.10: leitura do agente_nw numa cópia do banco ------------------------------

RAIZ = Path(__file__).resolve().parent.parent
BANCO_REAL = RAIZ / "dados" / "agente.db"


def _decisao(saida: str) -> str:
    return str(json.loads(saida)["hookSpecificOutput"]["permissionDecision"])


@pytest.mark.parametrize(
    "comando",
    [
        "agente_nw comparar-vetores --banco /tmp/copia.db --amostra 50",
        "agente_nw comparar-vetores --banco=/tmp/copia.db",
        "agente_nw medir-dano --banco /tmp/copia.db",
        "agente_nw reprocessar --simular --banco /tmp/copia.db",
        "agente_nw copiar-banco /tmp/copia.db && agente_nw medir-dano --banco /tmp/copia.db",
    ],
)
def test_leitura_apontando_para_a_copia_passa(comando: str, pasta_principal: Path) -> None:
    assert _rodar(comando, pasta_principal) == (0, "", "")


@pytest.mark.parametrize(
    "comando",
    [
        "agente_nw comparar-vetores --amostra 50",
        "agente_nw medir-dano",
        "agente_nw reprocessar --simular",
    ],
)
def test_leitura_sem_apontar_a_copia_continua_perguntando(comando: str, pasta_principal: Path) -> None:
    codigo, saida, _erro = _rodar(comando, pasta_principal)
    assert codigo == 0
    assert _decisao(saida) == "ask"


@pytest.mark.parametrize(
    "comando",
    [
        "agente_nw medir-dano --banco dados/agente.db",
        "agente_nw medir-dano --banco=dados/agente.db",
        "agente_nw medir-dano --banco ./dados/agente.db",
        "agente_nw comparar-vetores --banco /tmp/copia.db --comparar dados/agente.db",
        "agente_nw medir-dano --banco /tmp/../Users/sidarta48/github/agente_nw/dados/agente.db",
        "agente_nw medir-dano --banco $BANCO",
        'agente_nw medir-dano --banco "$HOME/github/agente_nw/dados/x.db"',
        "agente_nw medir-dano --banco ~/github/agente_nw/dados/x.db",
        "agente_nw medir-dano --banco $(echo /tmp/copia.db)",
        "agente_nw medir-dano --banco /tmp/*.db",
        "agente_nw reprocessar --simular --confirmo --banco /tmp/copia.db",
        "agente_nw reprocessar --banco /tmp/copia.db",
        "agente_nw reprocessar --confirmo --banco /tmp/copia.db",
    ],
)
def test_tentativa_de_driblar_a_copia_e_bloqueada(comando: str, pasta_principal: Path) -> None:
    codigo, _saida, erro = _rodar(comando, pasta_principal)
    assert codigo == 2
    assert erro.strip()


def test_link_simbolico_para_o_banco_real_e_bloqueado(pasta_principal: Path) -> None:
    link = pasta_principal / "copia_link.db"
    link.symlink_to(BANCO_REAL)

    codigo, _saida, erro = _rodar(f"agente_nw medir-dano --banco {link}", pasta_principal)

    assert codigo == 2
    assert erro.strip()


def test_pasta_que_e_link_para_dados_e_bloqueada(pasta_principal: Path) -> None:
    pasta = pasta_principal / "pasta_link"
    pasta.symlink_to(RAIZ / "dados", target_is_directory=True)

    codigo, _saida, erro = _rodar(f"agente_nw medir-dano --banco {pasta}/nova.db", pasta_principal)

    assert codigo == 2
    assert erro.strip()


@pytest.mark.parametrize(
    "comando",
    [
        "agente_nw coletar --banco /tmp/copia.db",
        "agente_nw processar-fila --banco /tmp/copia.db",
        "agente_nw inventado --banco /tmp/copia.db",
    ],
)
def test_subcomando_fora_da_lista_de_leitura_continua_perguntando(
    comando: str, pasta_principal: Path
) -> None:
    codigo, saida, _erro = _rodar(comando, pasta_principal)
    assert codigo == 0
    assert _decisao(saida) == "ask"


@pytest.mark.parametrize(
    "comando",
    [
        "agente_nw ler-rede-social --banco /tmp/copia.db",
        "agente_nw listas atualizar --banco /tmp/copia.db",
        "agente_nw pedir --banco /tmp/copia.db",
        "agente_nw extensao testar --banco /tmp/copia.db",
    ],
)
def test_rede_social_continua_bloqueada_mesmo_com_copia(comando: str, pasta_principal: Path) -> None:
    codigo, _saida, erro = _rodar(comando, pasta_principal)
    assert codigo == 2
    assert erro.strip()


def test_worktree_list_e_leitura_e_passa(pasta_principal: Path) -> None:
    assert _rodar("git worktree list", pasta_principal) == (0, "", "")
    assert _rodar("git worktree list --porcelain", pasta_principal) == (0, "", "")


@pytest.mark.parametrize(
    "comando",
    [
        "git worktree add ../nova",
        "git worktree remove ../nova",
        "git worktree prune",
    ],
)
def test_worktree_de_escrita_continua_bloqueado(comando: str, pasta_principal: Path) -> None:
    codigo, _saida, erro = _rodar(comando, pasta_principal)
    assert codigo == 2
    assert erro.strip()
