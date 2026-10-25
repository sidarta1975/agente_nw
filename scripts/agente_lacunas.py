#!/usr/bin/env python3
"""agente_lacunas.py — copia as lacunas de um relatório de brief para o docs/PLAN.md (brief 062).

Uso: scripts/agente_lacunas.py <NNN> [--raiz <pasta>] [--data AAAA-MM-DD]

Lê a tabela de `## Lacunas` de `docs/docs/doc_<NNN>_*.md` e acrescenta cada linha com destino diferente de
`nenhum` ao fim da seção certa do PLAN (backlog, pendência, dívida, decisão), no formato
`- [<NNN>-<#>] <lacuna> · <impacto> · <data>`. Não duplica (a marca `[<NNN>-<#>]` já no PLAN é pulada) e não
mexe em nenhuma outra linha. Imprime uma linha só e sai com 0 mesmo quando o relatório não está no formato:
a entrega já aconteceu.
"""

from __future__ import annotations

import argparse
import sys
import unicodedata
from datetime import date
from pathlib import Path

CABECALHO = ["#", "lacuna", "destino", "impacto"]
SECOES = {
    "backlog": "Backlog",
    "pendencia": "Pendências de Sidarta",
    "divida": "Dívidas conhecidas",
    "decisao": "Decisões em aberto",
}
ROTULOS = {
    "backlog": "no Backlog",
    "pendencia": "em Pendências",
    "divida": "em Dívidas",
    "decisao": "em Decisões",
}
SEM_FORMATO = "relatório sem tabela de lacunas no formato"


def _sem_acento(texto: str) -> str:
    decomposto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in decomposto if unicodedata.category(c) != "Mn").strip().lower()


def _celulas(linha: str) -> list[str]:
    return [c.strip() for c in linha.strip().strip("|").split("|")]


def ler_lacunas(texto: str) -> list[tuple[str, str, str, str]] | None:
    """Linhas (#, lacuna, destino, impacto) da última seção `## Lacunas`; [] se "Sem lacunas."; None se o
    formato não é o esperado."""
    linhas = texto.splitlines()
    inicios = [i for i, linha in enumerate(linhas) if linha.strip() == "## Lacunas"]
    if not inicios:
        return None
    corpo = linhas[inicios[-1] + 1 :]
    for linha in corpo:
        if linha.startswith("## "):
            corpo = corpo[: corpo.index(linha)]
            break
    if any(linha.strip().rstrip(".").lower() == "sem lacunas" for linha in corpo):
        return []
    tabela = [linha for linha in corpo if linha.strip().startswith("|")]
    if len(tabela) < 2 or [_sem_acento(c) for c in _celulas(tabela[0])] != CABECALHO:
        return None
    if not set(tabela[1].replace("|", "").replace(":", "").strip()) <= {"-", " "}:
        return None
    lacunas = []
    for linha in tabela[2:]:
        celulas = _celulas(linha)
        if len(celulas) != 4 or not celulas[0] or not celulas[1]:
            return None
        destino = _sem_acento(celulas[2])
        if destino != "nenhum" and destino not in SECOES:
            return None
        lacunas.append((celulas[0], celulas[1], destino, celulas[3]))
    return lacunas


def _inserir(linhas: list[str], titulo: str, nova: str) -> None:
    """Acrescenta `nova` depois da última linha com texto da seção `## titulo`."""
    inicio = next(i for i, linha in enumerate(linhas) if linha.strip() == f"## {titulo}")
    fim = len(linhas)
    for i in range(inicio + 1, len(linhas)):
        if linhas[i].startswith("## ") or linhas[i].strip() == "---":
            fim = i
            break
    ultima = inicio
    for i in range(inicio + 1, fim):
        if linhas[i].strip():
            ultima = i
    if ultima != inicio and linhas[ultima].strip() == "(nenhum)":
        linhas[ultima] = nova
    elif ultima == inicio:
        linhas[inicio + 1 : inicio + 1] = ["", nova]
    else:
        linhas.insert(ultima + 1, nova)


def main() -> int:
    analise = argparse.ArgumentParser()
    analise.add_argument("numero")
    analise.add_argument("--raiz", type=Path, default=Path(__file__).resolve().parents[1])
    analise.add_argument("--data", default=date.today().isoformat())
    args = analise.parse_args()

    relatorios = sorted((args.raiz / "docs" / "docs").glob(f"doc_{args.numero}_*.md"))
    if not relatorios:
        print(f"relatório do {args.numero} não encontrado em docs/docs/")
        return 0
    lacunas = ler_lacunas(relatorios[0].read_text())
    if lacunas is None:
        print(SEM_FORMATO)
        return 0
    if not lacunas:
        print("sem lacunas")
        return 0

    caminho = args.raiz / "docs" / "PLAN.md"
    plano = caminho.read_text()
    linhas = plano.split("\n")
    contagem = dict.fromkeys(SECOES, 0)
    for numero, texto, destino, impacto in lacunas:
        marca = f"[{args.numero}-{numero}]"
        if destino == "nenhum" or marca in plano:
            continue
        _inserir(linhas, SECOES[destino], f"- {marca} {texto} · {impacto} · {args.data}")
        contagem[destino] += 1
    caminho.write_text("\n".join(linhas))
    resumo = ", ".join(f"{contagem[d]} {ROTULOS[d]}" for d in SECOES)
    print(f"lacunas do {args.numero}: {resumo}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
