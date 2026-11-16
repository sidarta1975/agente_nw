from __future__ import annotations

import csv
import sys
from pathlib import Path

from agente_nw.perfil.importador import ContatoBruto


def _campo(linha: dict[str, str], *prefixos: str) -> str | None:
    for chave, valor in linha.items():
        if chave and valor and any(chave.lower().startswith(prefixo) for prefixo in prefixos):
            return valor.strip()
    return None


def ler_contatos(caminho: Path) -> list[ContatoBruto]:
    """O limite padrão do `csv` (131.072 caracteres por campo) derrubaria a leitura de uma agenda com um
    campo longo (notas); sobe o limite durante a leitura e o devolve ao valor anterior (brief 092, P-044)."""
    contatos: list[ContatoBruto] = []

    limite_anterior = csv.field_size_limit(sys.maxsize)
    try:
        _ler_linhas(caminho, contatos)
    finally:
        csv.field_size_limit(limite_anterior)
    return contatos


def _ler_linhas(caminho: Path, contatos: list[ContatoBruto]) -> None:
    with open(caminho, encoding="utf-8-sig", newline="") as arquivo:
        for linha in csv.DictReader(arquivo):
            nome = linha.get("Name") or " ".join(
                parte for parte in (linha.get("First Name"), linha.get("Last Name")) if parte
            )
            if not nome or not nome.strip():
                continue

            marcadores_bruto = _campo(linha, "group membership", "labels") or ""
            marcadores = [
                marcador.strip()
                for marcador in marcadores_bruto.split(":::")
                if marcador.strip() and not marcador.startswith("*")
            ]

            contatos.append(
                ContatoBruto(
                    nome=nome.strip(),
                    telefone=_campo(linha, "phone 1 - value"),
                    email=_campo(linha, "e-mail 1 - value"),
                    empresa=_campo(linha, "organization 1 - name", "organization name"),
                    cargo=_campo(linha, "organization 1 - title", "organization title"),
                    notas=_campo(linha, "notes"),
                    marcadores=marcadores,
                )
            )
