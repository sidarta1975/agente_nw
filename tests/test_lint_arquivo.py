from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / ".claude" / "hooks" / "lint_arquivo.py"


def _rodar(caminho: Path | str) -> subprocess.CompletedProcess[str]:
    pedido = {"tool_name": "Edit", "tool_input": {"file_path": str(caminho)}}
    comando = [sys.executable, str(HOOK)]
    return subprocess.run(comando, input=json.dumps(pedido), capture_output=True, text=True, check=False)


def test_arquivo_mal_formatado_sai_formatado_e_sem_mensagem(tmp_path: Path) -> None:
    arquivo = tmp_path / "mal.py"
    arquivo.write_text("x = {'a':1,'b':2}\n")

    resultado = _rodar(arquivo)

    assert (resultado.returncode, resultado.stdout, resultado.stderr) == (0, "", "")
    assert arquivo.read_text() == 'x = {"a": 1, "b": 2}\n'


def test_import_sem_uso_e_removido_em_silencio(tmp_path: Path) -> None:
    arquivo = tmp_path / "sobra.py"
    arquivo.write_text("import os\n\nx = 1\n")

    resultado = _rodar(arquivo)

    assert (resultado.returncode, resultado.stdout, resultado.stderr) == (0, "", "")
    assert "import os" not in arquivo.read_text()


def test_erro_que_o_ruff_nao_corrige_volta_em_ate_tres_linhas(tmp_path: Path) -> None:
    arquivo = tmp_path / "quebrado.py"
    arquivo.write_text("a = nome1\nb = nome2\nc = nome3\nd = nome4\n")

    resultado = _rodar(arquivo)

    linhas = resultado.stderr.strip().splitlines()
    assert resultado.returncode == 2
    assert 1 <= len(linhas) <= 3
    assert all(str(arquivo) in linha and "F821" in linha for linha in linhas)


def test_arquivo_que_nao_e_python_nao_e_tocado(tmp_path: Path) -> None:
    arquivo = tmp_path / "nota.md"
    arquivo.write_text("x = {'a':1}\n")

    resultado = _rodar(arquivo)

    assert (resultado.returncode, resultado.stdout, resultado.stderr) == (0, "", "")
    assert arquivo.read_text() == "x = {'a':1}\n"


def test_arquivo_inexistente_e_entrada_sem_caminho_passam(tmp_path: Path) -> None:
    assert _rodar(tmp_path / "nao_existe.py").returncode == 0
    comando = [sys.executable, str(HOOK)]
    vazio = subprocess.run(comando, input="{}", capture_output=True, text=True, check=False)
    assert (vazio.returncode, vazio.stdout, vazio.stderr) == (0, "", "")
