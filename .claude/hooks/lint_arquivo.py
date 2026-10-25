"""Hook PostToolUse (Edit|Write|MultiEdit), brief 058: formata e corrige o .py que acabou de ser editado.

Roda `ruff format` e `ruff check --fix` só nesse arquivo, com a configuração do projeto. Em silêncio quando
passa. Quando sobra erro que o ruff não corrige, devolve ao modelo (código 2, stderr) no máximo 3 linhas,
cada uma com o caminho, a linha e o código do erro.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
RUFF = RAIZ / ".venv" / "bin" / "ruff"
CONFIG = RAIZ / "pyproject.toml"
MAXIMO_LINHAS = 3
LIMITE_SEGUNDOS = 60


def _ruff(*argumentos: str) -> subprocess.CompletedProcess[str]:
    comando = [str(RUFF), *argumentos]
    return subprocess.run(comando, capture_output=True, text=True, check=False, timeout=LIMITE_SEGUNDOS)


def main() -> int:
    try:
        pedido = json.load(sys.stdin)
    except (ValueError, OSError):
        return 0
    entrada = pedido.get("tool_input") if isinstance(pedido, dict) else None
    caminho = entrada.get("file_path") if isinstance(entrada, dict) else None
    if not isinstance(caminho, str) or not caminho.endswith(".py"):
        return 0
    if not Path(caminho).is_file() or not RUFF.is_file():
        return 0

    base = ["--config", str(CONFIG), "--force-exclude"]
    try:
        _ruff("format", *base, caminho)
        verificacao = _ruff("check", "--fix", "--output-format", "concise", *base, caminho)
    except (subprocess.TimeoutExpired, OSError):
        return 0
    if verificacao.returncode == 0:
        return 0

    erros = []
    for linha in verificacao.stdout.splitlines():
        achado = re.match(r"^(.+?):(\d+):\d+: (\S+)", linha)
        if achado:
            erros.append(f"{achado.group(1)}:{achado.group(2)} {achado.group(3)}")
    if not erros:
        return 0
    print("\n".join(erros[:MAXIMO_LINHAS]), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
