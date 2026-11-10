from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
GIT_REAL = shutil.which("git") or "git"

# O `claude` falso faz o papel do `/executar`: imprime o JSON que o `-p --output-format json`
# imprimiria e, conforme o modo, cria (ou não) a prova de entrega — manifesto `entregue_*`,
# commit citando o brief e push. Nenhum teste chama o Claude Code de verdade.
CLAUDE_FALSO = f"""#!/usr/bin/env bash
NUMERO=""
for argumento in "$@"; do
  case "$argumento" in
    "/executar "*) NUMERO="${{argumento#/executar }}" ;;
  esac
done
echo "$@" >> "$CHAMADAS_LOG"
MODO="$(eval echo "\\$MODO_$NUMERO")"
[ -n "$MODO" ] || MODO="$MODO_PADRAO"
RESULTADO="relatório em docs/docs/doc_$NUMERO.md"
ERRO=false
ASSUNTO=success

entregar() {{
  echo "trabalho do $NUMERO" > "trabalho_$NUMERO.txt"
  echo "mensagem" > "logs/entregue_${{NUMERO}}_commit.txt"
  echo "trabalho_$NUMERO.txt" > "logs/entregue_${{NUMERO}}_arquivos.txt"
  {GIT_REAL} add -- "trabalho_$NUMERO.txt" >/dev/null
  {GIT_REAL} commit -q -m "feat: coisa (brief $NUMERO)"
}}

case "$MODO" in
  entrega)       entregar; {GIT_REAL} push -q origin main ;;
  sem_manifesto) : ;;
  sem_push)      entregar ;;
  parou)         RESULTADO="PAROU: o brief $NUMERO parou de propósito neste teste" ;;
  erro)          ERRO=true; ASSUNTO=error_max_turns ;;
  para_voce)     entregar; {GIT_REAL} push -q origin main
                 RESULTADO="docs/docs/doc_$NUMERO.md
feito, commit abc1234
Para você: recarregar a extensão no Chrome" ;;
esac

python3 - "$RESULTADO" "$ERRO" "$ASSUNTO" <<'FIM'
import json
import sys

print(
    json.dumps(
        {{
            "is_error": sys.argv[2] == "true",
            "subtype": sys.argv[3],
            "num_turns": 7,
            "total_cost_usd": 0.5,
            "result": sys.argv[1],
        }}
    )
)
FIM
"""

PMSET_FALSO = """#!/usr/bin/env bash
echo "Now drawing from '${FAKE_ENERGIA:-AC Power}'"
echo " -InternalBattery-0	100%; charged; 0:00 remaining present: true"
"""

CAFFEINATE_FALSO = """#!/usr/bin/env bash
echo "$@" >> "$CAFFEINATE_LOG"
while [ $# -gt 0 ] && [ "${1#-}" != "$1" ]; do shift; done
exec "$@"
"""

OSASCRIPT_FALSO = """#!/usr/bin/env bash
echo "$@" >> "$OSASCRIPT_LOG"
"""

CABECALHO = """# Brief {numero} — teste

**Modelo:** {modelo}
**Esforço:** {esforco}
**Depende de:** nada
**Ordem em série:** {ordem}
**Data:** 2026-11-10
"""


def _git(repo: Path, *args: str) -> str:
    saida = subprocess.run([GIT_REAL, *args], cwd=repo, capture_output=True, text=True, check=True)
    return saida.stdout.strip()


def _brief(
    repo: Path, numero: str, *, modelo: str = "Sonnet", esforco: str = "baixo", ordem: str = "livre"
) -> None:
    caminho = repo / "docs" / "briefs" / f"brief_{numero}_teste_2026-11-10.md"
    caminho.write_text(CABECALHO.format(numero=numero, modelo=modelo, esforco=esforco, ordem=ordem))


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    pasta = tmp_path / "repo"
    (pasta / "scripts").mkdir(parents=True)
    shutil.copy(RAIZ / "scripts" / "executar_serie.sh", pasta / "scripts" / "executar_serie.sh")
    (pasta / "scripts" / "executar_serie.sh").chmod(0o755)
    (pasta / "docs" / "briefs").mkdir(parents=True)
    (pasta / "logs").mkdir()
    (pasta / ".gitignore").write_text("/logs/\n")
    (pasta / "base.txt").write_text("base\n")
    _git(pasta, "init", "-b", "main")
    _git(pasta, "config", "user.email", "teste@example.com")
    _git(pasta, "config", "user.name", "Teste")
    _git(pasta, "add", "--", ".gitignore", "base.txt", "scripts", "docs")
    _git(pasta, "commit", "-m", "inicial")
    remoto = tmp_path / "remoto.git"
    subprocess.run([GIT_REAL, "init", "--bare", "-q", str(remoto)], check=True)
    _git(pasta, "remote", "add", "origin", str(remoto))
    _git(pasta, "push", "-q", "-u", "origin", "main")
    _brief(pasta, "080")
    _brief(pasta, "081")
    _git(pasta, "add", "--", "docs")
    _git(pasta, "commit", "-m", "briefs")
    _git(pasta, "push", "-q", "origin", "main")
    return pasta


@pytest.fixture
def ambiente(tmp_path: Path) -> dict[str, str]:
    bin_falso = tmp_path / "bin"
    bin_falso.mkdir()
    for nome, corpo in (
        ("claude", CLAUDE_FALSO),
        ("pmset", PMSET_FALSO),
        ("caffeinate", CAFFEINATE_FALSO),
        ("osascript", OSASCRIPT_FALSO),
    ):
        (bin_falso / nome).write_text(corpo)
        (bin_falso / nome).chmod(0o755)
    return {
        **os.environ,
        "PATH": f"{bin_falso}{os.pathsep}{os.environ['PATH']}",
        "CHAMADAS_LOG": str(tmp_path / "chamadas.log"),
        "CAFFEINATE_LOG": str(tmp_path / "caffeinate.log"),
        "OSASCRIPT_LOG": str(tmp_path / "osascript.log"),
        "MODO_PADRAO": "entrega",
    }


def _rodar(
    repo: Path, ambiente: dict[str, str], *briefs: str, extra: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "scripts/executar_serie.sh", *briefs],
        cwd=repo,
        env={**ambiente, **(extra or {})},
        capture_output=True,
        text=True,
        check=False,
    )


def _status(repo: Path) -> str:
    pastas = sorted((repo / "logs" / "serie").glob("*/STATUS.txt"))
    assert pastas, "nenhum STATUS.txt foi escrito"
    return pastas[-1].read_text()


def _chamadas(ambiente: dict[str, str]) -> str:
    log = Path(ambiente["CHAMADAS_LOG"])
    return log.read_text() if log.exists() else ""


def _log(ambiente: dict[str, str], chave: str) -> str:
    log = Path(ambiente[chave])
    return log.read_text() if log.exists() else ""


def test_dois_briefs_entregues_concluem_a_serie(repo: Path, ambiente: dict[str, str]) -> None:
    resultado = _rodar(repo, ambiente, "080", "081")

    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    status = _status(repo)
    assert "CONCLUÍDA" in status
    assert "080 entregue" in status
    assert "081 entregue" in status
    chamadas = _chamadas(ambiente)
    assert "/executar 080" in chamadas
    assert "/executar 081" in chamadas


def test_modelo_e_esforco_vem_do_cabecalho(repo: Path, ambiente: dict[str, str]) -> None:
    _brief(repo, "082", modelo="Opus — porque mexe no cliente", esforco="alto")
    _git(repo, "add", "--", "docs")
    _git(repo, "commit", "-m", "brief 082")
    _git(repo, "push", "-q", "origin", "main")

    resultado = _rodar(repo, ambiente, "080", "082")

    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    linhas = [linha for linha in _chamadas(ambiente).splitlines() if linha.strip()]
    chamada_080 = next(linha for linha in linhas if "/executar 080" in linha)
    chamada_082 = next(linha for linha in linhas if "/executar 082" in linha)
    assert "--model sonnet" in chamada_080
    assert "--effort low" in chamada_080
    assert "--model opus" in chamada_082
    assert "--effort high" in chamada_082
    assert "--permission-prompts none" in chamada_080


def test_saida_zero_sem_manifesto_para_e_nao_tenta_o_seguinte(repo: Path, ambiente: dict[str, str]) -> None:
    resultado = _rodar(repo, ambiente, "080", "081", extra={"MODO_080": "sem_manifesto"})

    assert resultado.returncode == 1
    assert "/executar 081" not in _chamadas(ambiente)
    status = _status(repo)
    assert "PAROU" in status
    assert "080" in status
    assert "manifesto" in status


def test_primeira_linha_com_parou_para_a_serie(repo: Path, ambiente: dict[str, str]) -> None:
    resultado = _rodar(repo, ambiente, "080", "081", extra={"MODO_080": "parou"})

    assert resultado.returncode == 1
    assert "/executar 081" not in _chamadas(ambiente)
    assert "PAROU: o brief 080 parou de propósito neste teste" in _status(repo)


def test_commit_sem_push_para_e_o_status_traz_o_comando_de_envio(
    repo: Path, ambiente: dict[str, str]
) -> None:
    resultado = _rodar(repo, ambiente, "080", "081", extra={"MODO_080": "sem_push"})

    assert resultado.returncode == 1
    assert "/executar 081" not in _chamadas(ambiente)
    status = _status(repo)
    assert "PAROU" in status
    assert "git push" in status


def test_arvore_suja_nem_comeca(repo: Path, ambiente: dict[str, str]) -> None:
    (repo / "intruso.txt").write_text("fora\n")

    resultado = _rodar(repo, ambiente, "080")

    assert resultado.returncode != 0
    assert "intruso.txt" in resultado.stdout + resultado.stderr
    assert _chamadas(ambiente) == ""


def test_pendente_de_envio_nem_comeca(repo: Path, ambiente: dict[str, str]) -> None:
    (repo / "outro.txt").write_text("outro\n")
    _git(repo, "add", "--", "outro.txt")
    _git(repo, "commit", "-m", "local, sem enviar")

    resultado = _rodar(repo, ambiente, "080")

    assert resultado.returncode != 0
    assert _chamadas(ambiente) == ""


def test_ordem_violada_e_recusada_antes_de_comecar(repo: Path, ambiente: dict[str, str]) -> None:
    _brief(repo, "080", ordem="antes de 081")
    _git(repo, "add", "--", "docs")
    _git(repo, "commit", "-m", "ordem")
    _git(repo, "push", "-q", "origin", "main")

    resultado = _rodar(repo, ambiente, "081", "080")

    assert resultado.returncode != 0
    assert "ordem" in (resultado.stdout + resultado.stderr).lower()
    assert _chamadas(ambiente) == ""


def test_campo_do_cabecalho_ausente_e_recusado(repo: Path, ambiente: dict[str, str]) -> None:
    caminho = repo / "docs" / "briefs" / "brief_080_teste_2026-11-10.md"
    caminho.write_text("# Brief 080 — teste\n\n**Modelo:** Sonnet\n**Esforço:** baixo\n")
    _git(repo, "add", "--", "docs")
    _git(repo, "commit", "-m", "cabecalho incompleto")
    _git(repo, "push", "-q", "origin", "main")

    resultado = _rodar(repo, ambiente, "080")

    assert resultado.returncode != 0
    assert "Ordem em série" in resultado.stdout + resultado.stderr
    assert _chamadas(ambiente) == ""


def test_dois_arquivos_para_o_mesmo_numero_e_recusado(repo: Path, ambiente: dict[str, str]) -> None:
    (repo / "docs" / "briefs" / "brief_080_outro_2026-11-10.md").write_text("# Brief 080 — outro\n")
    _git(repo, "add", "--", "docs")
    _git(repo, "commit", "-m", "duplicado")
    _git(repo, "push", "-q", "origin", "main")

    resultado = _rodar(repo, ambiente, "080")

    assert resultado.returncode != 0
    assert _chamadas(ambiente) == ""


def test_brief_ja_entregue_e_pulado(repo: Path, ambiente: dict[str, str]) -> None:
    (repo / "logs" / "entregue_080_commit.txt").write_text("mensagem\n")
    (repo / "logs" / "entregue_080_arquivos.txt").write_text("trabalho_080.txt\n")

    resultado = _rodar(repo, ambiente, "080", "081")

    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    assert "/executar 080" not in _chamadas(ambiente)
    assert "/executar 081" in _chamadas(ambiente)
    assert "080 pulado" in _status(repo)


def test_trava_de_instancia_recusa_a_segunda_serie(repo: Path, ambiente: dict[str, str]) -> None:
    (repo / "logs" / "serie").mkdir(parents=True)
    (repo / "logs" / "serie" / "TRAVA").write_text("12345\n")

    resultado = _rodar(repo, ambiente, "080")

    assert resultado.returncode != 0
    assert "TRAVA" in resultado.stdout + resultado.stderr
    assert _chamadas(ambiente) == ""


def test_trava_de_instancia_e_removida_no_fim(repo: Path, ambiente: dict[str, str]) -> None:
    resultado = _rodar(repo, ambiente, "080")

    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    assert not (repo / "logs" / "serie" / "TRAVA").exists()


def test_is_error_verdadeiro_para_a_serie(repo: Path, ambiente: dict[str, str]) -> None:
    resultado = _rodar(repo, ambiente, "080", "081", extra={"MODO_080": "erro"})

    assert resultado.returncode == 1
    assert "/executar 081" not in _chamadas(ambiente)
    status = _status(repo)
    assert "PAROU" in status
    assert "error_max_turns" in status


def test_para_voce_sem_parou_vira_pendencia_e_a_serie_segue(repo: Path, ambiente: dict[str, str]) -> None:
    resultado = _rodar(repo, ambiente, "080", "081", extra={"MODO_080": "para_voce"})

    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    assert "/executar 081" in _chamadas(ambiente)
    status = _status(repo)
    assert "CONCLUÍDA" in status
    assert "Para você: recarregar a extensão no Chrome" in status


def test_energia_na_bateria_nem_comeca(repo: Path, ambiente: dict[str, str]) -> None:
    resultado = _rodar(repo, ambiente, "080", extra={"FAKE_ENERGIA": "Battery Power"})

    assert resultado.returncode != 0
    assert "tomada" in (resultado.stdout + resultado.stderr).lower()
    assert _chamadas(ambiente) == ""


def test_caffeinate_e_osascript_sao_chamados(repo: Path, ambiente: dict[str, str]) -> None:
    resultado = _rodar(repo, ambiente, "080")

    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    assert "-dimsu" in _log(ambiente, "CAFFEINATE_LOG")
    assert "display notification" in _log(ambiente, "OSASCRIPT_LOG")


def test_osascript_tambem_avisa_na_parada(repo: Path, ambiente: dict[str, str]) -> None:
    resultado = _rodar(repo, ambiente, "080", extra={"MODO_080": "parou"})

    assert resultado.returncode == 1
    assert "display notification" in _log(ambiente, "OSASCRIPT_LOG")


def test_json_cru_de_cada_brief_fica_guardado(repo: Path, ambiente: dict[str, str]) -> None:
    resultado = _rodar(repo, ambiente, "080")

    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    jsons = sorted((repo / "logs" / "serie").glob("*/080.json"))
    assert jsons, "o JSON do brief não foi guardado"
    assert json.loads(jsons[-1].read_text())["subtype"] == "success"
    assert "custo" in _status(repo).lower()


def test_sem_brief_nenhum_na_linha_de_comando_recusa(repo: Path, ambiente: dict[str, str]) -> None:
    resultado = _rodar(repo, ambiente)

    assert resultado.returncode != 0
    assert "uso" in (resultado.stdout + resultado.stderr).lower()


def test_o_script_nao_tem_git_de_escrita_nem_simulacao() -> None:
    achado = subprocess.run(
        ["grep", "-nE", "git (add|commit|push)|--simular", str(RAIZ / "scripts" / "executar_serie.sh")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert achado.returncode == 1, achado.stdout
