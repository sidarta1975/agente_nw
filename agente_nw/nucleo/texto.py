from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher


def sem_acento_e_caixa(texto: str) -> str:
    decomposto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in decomposto if not unicodedata.combining(c)).casefold().strip()


def _palavras(texto: str) -> list[str]:
    """Palavras sem acento, caixa e pontuação ("Silva, CFA" vira "silva", "cfa")."""
    return re.sub(r"[^\w]+", " ", sem_acento_e_caixa(texto)).split()


def casa_nome(busca: str, nome: str) -> bool:
    """O primeiro nome da busca bate por inteiro com o primeiro do `nome`; cada palavra seguinte da
    busca precisa ser prefixo de alguma palavra seguinte do `nome`. "Marcos" casa todos os Marcos."""
    termos = _palavras(busca)
    palavras = _palavras(nome)
    if not termos or not palavras or palavras[0] != termos[0]:
        return False
    return all(any(p.startswith(termo) for p in palavras[1:]) for termo in termos[1:])


def _parecido_palavra(termo: str, palavra: str) -> float:
    if len(termo) >= 3 and palavra.startswith(termo):
        return 0.9
    return SequenceMatcher(None, termo, palavra).ratio()


def similaridade_nome(busca: str, nome: str) -> float:
    """De 0 a 1: quão provável é que `nome` seja a pessoa de `busca`. Tolera apelido ("Leo" para
    "Leonardo"), erro de digitação, sufixos ("CFA") e nomes do meio. Cada palavra da busca é comparada
    com a melhor palavra do nome; a média é a nota, e o primeiro nome pesa o dobro."""
    termos = _palavras(busca)
    palavras = _palavras(nome)
    if not termos or not palavras:
        return 0.0
    notas = [max(_parecido_palavra(t, p) for p in palavras) for t in termos]
    pesos = [2.0] + [1.0] * (len(notas) - 1)
    return sum(n * w for n, w in zip(notas, pesos, strict=True)) / sum(pesos)
