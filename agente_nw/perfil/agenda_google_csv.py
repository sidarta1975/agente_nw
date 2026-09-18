from __future__ import annotations

import csv
from pathlib import Path

from agente_nw.perfil.importador import ContatoBruto


def _campo(linha: dict[str, str], *prefixos: str) -> str | None:
    for chave, valor in linha.items():
        if chave and valor and any(chave.lower().startswith(prefixo) for prefixo in prefixos):
            return valor.strip()
    return None


def ler_contatos(caminho: Path) -> list[ContatoBruto]:
    contatos: list[ContatoBruto] = []

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

    return contatos
