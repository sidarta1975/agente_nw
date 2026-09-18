from __future__ import annotations

import functools
import re
import unicodedata

import yaml

from config.container import RAIZ

_CAMINHO_TERMOS = RAIZ / "config" / "termos_sensiveis.yaml"


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return sem_acento.lower()


@functools.lru_cache(maxsize=1)
def _termos_por_categoria() -> tuple[tuple[str, tuple[str, ...]], ...]:
    dados = yaml.safe_load(_CAMINHO_TERMOS.read_text(encoding="utf-8")) or {}
    return tuple(
        (categoria, tuple(_normalizar(termo) for termo in termos)) for categoria, termos in dados.items()
    )


def verificar(texto: str) -> str | None:
    """Devolve a categoria sensível encontrada em ``texto``, ou ``None`` se limpo.

    Comparação por palavra/expressão inteira (limites de palavra via regex),
    sem diferenciar maiúscula de minúscula, ignorando acentuação. Devolve a
    primeira categoria (na ordem de ``config/termos_sensiveis.yaml``) cujo
    algum termo bater; não continua procurando outras categorias depois.
    """
    texto_normalizado = _normalizar(texto)
    for categoria, termos in _termos_por_categoria():
        for termo in termos:
            padrao = r"\b" + re.escape(termo) + r"\b"
            if re.search(padrao, texto_normalizado):
                return categoria
    return None
