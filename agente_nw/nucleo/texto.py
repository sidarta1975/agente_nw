from __future__ import annotations

import unicodedata


def sem_acento_e_caixa(texto: str) -> str:
    decomposto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in decomposto if not unicodedata.combining(c)).casefold().strip()
