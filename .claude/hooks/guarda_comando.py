"""Hook PreToolUse da ferramenta Bash (brief 057, ajustado no 058).

Trava o que o AGENTS.md ainda veda ao modelo: git de escrita digitado direto (§5), o banco real e a leitura
de rede social (§6), e `rm -rf` fora de `logs/` e de pastas temporárias. O gate e a entrega
(`scripts/verificar.sh`, `scripts/agente_entregar.sh`, pytest) passaram ao executor no brief 058; o único
caminho para commitar é o `agente_entregar.sh`. O que Sidarta digita com `!` não passa por aqui.

Entrada: JSON do Claude Code na entrada padrão. Saída: código 2 e o motivo em stderr para bloquear; um JSON
com `permissionDecision: "ask"` para pedir confirmação; nada e código 0 para deixar passar.
"""

from __future__ import annotations

import json
import re
import shlex
import sys
from pathlib import Path

GIT_ESCRITA = {
    "add",
    "commit",
    "push",
    "merge",
    "rebase",
    "reset",
    "checkout",
    "switch",
    "restore",
    "clean",
    "stash",
    "worktree",
    "cherry-pick",
    "revert",
    "pull",
    "rm",
    "mv",
    "am",
}
GIT_BRANCH_ESCRITA = {"-D", "-d", "-m", "-M", "--delete", "--move"}
GIT_OPCAO_COM_VALOR = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}
SCRIPTS_DE_SIDARTA = {"commitar.sh"}
PASTAS_LIBERADAS_PARA_RM = ("/tmp", "/private/tmp", "/var/folders", "/private/var/folders")
RAIZ = Path(__file__).resolve().parents[2]
REDE_SOCIAL = {"ler-rede-social", "listas", "pedir", "extensao"}
PASSA_NA_PASTA_PRINCIPAL = {"verificar-ambiente", "copiar-banco"}
SEPARADORES = {"&&", "||", ";", ";;", "|", "|&", "&", "(", ")"}
ENVOLTORIOS = {
    "env",
    "command",
    "time",
    "nohup",
    "exec",
    "sudo",
    "nice",
    "xargs",
    "if",
    "then",
    "do",
    "else",
    "elif",
    "while",
    "until",
    "{",
    "!",
}
INTERPRETADORES_SHELL = {"bash", "sh", "zsh", "dash", "source", "."}
PROFUNDIDADE_MAXIMA = 3

MOTIVO_GIT = (
    "git de escrita é de Sidarta (AGENTS §5): deixe o manifesto em logs/ e termine com "
    "!scripts/agente_entregar.sh"
)
MOTIVO_COMMITAR = (
    "o commit só sai por scripts/agente_entregar.sh (AGENTS §5), que confere o gate e o manifesto"
)
MOTIVO_RM = (
    "rm recursivo só em logs/ e em pastas temporárias (AGENTS §4: mudança cirúrgica, nada de apagar à toa)"
)
MOTIVO_BANCO = (
    "o banco real só é tocado por operação autorizada por Sidarta (AGENTS §6): trabalhe numa cópia "
    "(agente_nw copiar-banco)"
)
MOTIVO_REDE = "leitura de rede social nunca roda sozinha (AGENTS §6): é Sidarta quem dispara"
MOTIVO_PERGUNTA = (
    "agente_nw nesta pasta usa o banco real (AGENTS §6): confirme, ou trabalhe numa cópia "
    "(agente_nw copiar-banco)"
)

BLOQUEAR = "bloquear"
PERGUNTAR = "perguntar"
PASSAR = "passar"

Decisao = tuple[str, str]


def _sem_heredoc(comando: str) -> list[str]:
    """Linhas do comando, sem o corpo dos heredocs (texto, não comando)."""
    linhas: list[str] = []
    delimitador: str | None = None
    for linha in comando.splitlines():
        if delimitador is not None:
            if linha.strip() == delimitador:
                delimitador = None
            continue
        linhas.append(linha)
        achado = re.search(r"<<-?\s*['\"]?(\w+)['\"]?", linha)
        if achado:
            delimitador = achado.group(1)
    return linhas


def _segmentos(comando: str) -> list[list[str]]:
    """Quebra o comando nos operadores do shell; cada segmento é uma lista de palavras."""
    segmentos: list[list[str]] = []
    for linha in _sem_heredoc(comando):
        try:
            lexer = shlex.shlex(linha, posix=True, punctuation_chars=True)
            lexer.whitespace_split = True
            lexer.commenters = ""
            palavras = list(lexer)
        except ValueError:
            palavras = linha.split()
        atual: list[str] = []
        for palavra in palavras:
            if palavra in SEPARADORES:
                if atual:
                    segmentos.append(atual)
                atual = []
            else:
                atual.append(palavra.strip("`"))
        if atual:
            segmentos.append(atual)
    return segmentos


def _programa(palavras: list[str]) -> tuple[str, list[str]]:
    """Programa que de fato roda no segmento e seus argumentos, sem prefixos de ambiente e envoltórios."""
    i = 0
    while i < len(palavras):
        palavra = palavras[i]
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", palavra):
            i += 1
        elif palavra in ENVOLTORIOS:
            i += 1
            while i < len(palavras) and palavras[i].startswith("-"):
                i += 1
        else:
            break
    if i >= len(palavras):
        return "", []
    return Path(palavras[i]).name, palavras[i + 1 :]


def _subcomando_git(argumentos: list[str]) -> tuple[str, list[str]]:
    i = 0
    while i < len(argumentos):
        argumento = argumentos[i]
        if argumento in GIT_OPCAO_COM_VALOR:
            i += 2
        elif argumento.startswith("-"):
            i += 1
        else:
            return argumento, argumentos[i + 1 :]
    return "", []


def _na_pasta_principal(cwd: str) -> bool:
    """A pasta principal tem `.git` como diretório; num worktree `.git` é um arquivo."""
    pasta = Path(cwd or ".").resolve()
    for candidata in (pasta, *pasta.parents):
        marca = candidata / ".git"
        if marca.is_dir():
            return True
        if marca.is_file():
            return False
    return True


def _rm_fora_do_liberado(argumentos: list[str], cwd: str) -> bool:
    """`rm` recursivo cujo alvo não está em logs/ nem numa pasta temporária."""
    recursivo = any(
        a == "--recursive" or (a.startswith("-") and not a.startswith("--") and ("r" in a or "R" in a))
        for a in argumentos
    )
    if not recursivo:
        return False
    base = Path(cwd or ".").resolve()
    for alvo in (a for a in argumentos if not a.startswith("-")):
        caminho = (base / alvo).resolve()
        if caminho == RAIZ / "logs" or (RAIZ / "logs") in caminho.parents:
            continue
        if any(caminho == Path(p) or Path(p) in caminho.parents for p in PASTAS_LIBERADAS_PARA_RM):
            continue
        return True
    return False


def _decidir_segmento(palavras: list[str], cwd: str, profundidade: int) -> Decisao:
    programa, argumentos = _programa(palavras)
    if not programa:
        return PASSAR, ""

    if programa in INTERPRETADORES_SHELL:
        for i, argumento in enumerate(argumentos):
            if argumento.startswith("-") and not argumento.startswith("--") and "c" in argumento:
                if i + 1 < len(argumentos) and profundidade < PROFUNDIDADE_MAXIMA:
                    return analisar(argumentos[i + 1], cwd, profundidade + 1)
                return PASSAR, ""
        roteiro = [a for a in argumentos if not a.startswith("-")]
        if roteiro:
            return _decidir_segmento(roteiro, cwd, profundidade)
        return PASSAR, ""

    if re.fullmatch(r"python[0-9.]*", programa) and "-m" in argumentos:
        i = argumentos.index("-m")
        if i + 1 < len(argumentos):
            programa, argumentos = argumentos[i + 1], argumentos[i + 2 :]

    if programa in SCRIPTS_DE_SIDARTA:
        return BLOQUEAR, MOTIVO_COMMITAR

    if programa == "rm" and _rm_fora_do_liberado(argumentos, cwd):
        return BLOQUEAR, MOTIVO_RM

    if programa == "git":
        subcomando, resto = _subcomando_git(argumentos)
        if subcomando in GIT_ESCRITA:
            return BLOQUEAR, MOTIVO_GIT
        if subcomando == "branch" and GIT_BRANCH_ESCRITA & set(resto):
            return BLOQUEAR, MOTIVO_GIT
        return PASSAR, ""

    if programa == "sqlite3" and any("agente.db" in a for a in argumentos):
        return BLOQUEAR, MOTIVO_BANCO

    if programa == "agente_nw" or programa.startswith("agente_nw."):
        if "--help" in argumentos or "-h" in argumentos:
            return PASSAR, ""
        subcomando = next((a for a in argumentos if not a.startswith("-")), "")
        if subcomando in REDE_SOCIAL:
            return BLOQUEAR, MOTIVO_REDE
        if not subcomando or subcomando in PASSA_NA_PASTA_PRINCIPAL:
            return PASSAR, ""
        if _na_pasta_principal(cwd):
            return PERGUNTAR, MOTIVO_PERGUNTA

    return PASSAR, ""


def analisar(comando: str, cwd: str, profundidade: int = 0) -> Decisao:
    """Bloquear vale mais que perguntar, que vale mais que passar."""
    resultado: Decisao = (PASSAR, "")
    for palavras in _segmentos(comando):
        decisao = _decidir_segmento(palavras, cwd, profundidade)
        if decisao[0] == BLOQUEAR:
            return decisao
        if decisao[0] == PERGUNTAR:
            resultado = decisao
    return resultado


def main() -> int:
    try:
        pedido = json.load(sys.stdin)
    except (ValueError, OSError):
        return 0
    if not isinstance(pedido, dict) or pedido.get("tool_name", "Bash") != "Bash":
        return 0
    entrada = pedido.get("tool_input")
    comando = entrada.get("command") if isinstance(entrada, dict) else None
    if not isinstance(comando, str):
        return 0

    decisao, motivo = analisar(comando, str(pedido.get("cwd") or ""))
    if decisao == BLOQUEAR:
        print(f"Bloqueado: {motivo}", file=sys.stderr)
        return 2
    if decisao == PERGUNTAR:
        saida = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "ask",
                "permissionDecisionReason": motivo,
            }
        }
        print(json.dumps(saida, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
