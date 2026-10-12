from __future__ import annotations

import unicodedata


def sem_acento_e_caixa(texto: str) -> str:
    decomposto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in decomposto if not unicodedata.combining(c)).casefold().strip()


def casa_nome(busca: str, nome: str) -> bool:
    """O primeiro nome da busca bate por inteiro com o primeiro do `nome`; cada palavra seguinte da
    busca precisa ser prefixo de alguma palavra seguinte do `nome`. "Marcos" casa todos os Marcos."""
    termos = sem_acento_e_caixa(busca).split()
    palavras = sem_acento_e_caixa(nome).split()
    if not termos or not palavras or palavras[0] != termos[0]:
        return False
    return all(any(p.startswith(termo) for p in palavras[1:]) for termo in termos[1:])
