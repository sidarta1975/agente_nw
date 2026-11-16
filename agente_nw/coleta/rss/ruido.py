from __future__ import annotations

import re
from datetime import datetime

from agente_nw.nucleo.modelos.configuracao import ColetaLimiares

_PALAVRAS_LISTA = (
    "melhor",
    "melhores",
    "motivo",
    "motivos",
    "dica",
    "dicas",
    "maneira",
    "maneiras",
    "coisa",
    "coisas",
    "razão",
    "razões",
    "erro",
    "erros",
)

_PADRAO_LISTA = re.compile(
    r"^\s*\d+\s+(" + "|".join(_PALAVRAS_LISTA) + r")\b",
    re.IGNORECASE,
)

_TERMOS_PATROCINADO = (
    "publicidade",
    "conteúdo patrocinado",
    "conteudo patrocinado",
    "publieditorial",
    "patrocinado por",
)


_LINHA_DE_DECLARACAO = 80
"""Tamanho máximo, em caracteres, da linha do corpo em que a marca de patrocinado vale (brief 083):
o formato de uma declaração ("Publicidade", "Conteúdo patrocinado", "Patrocinado por X"), não de um
parágrafo de reportagem que fala de publicidade."""


def _tem_termo_patrocinado(texto: str) -> bool:
    texto_lower = texto.lower()
    return any(termo in texto_lower for termo in _TERMOS_PATROCINADO)


def _corpo_declara_patrocinio(corpo: str) -> bool:
    """A marca é procurada em todas as linhas do corpo, mas só conta em linha curta (brief 083, P-004)."""
    return any(
        _tem_termo_patrocinado(linha)
        for linha in corpo.splitlines()
        if len(linha.strip()) <= _LINHA_DE_DECLARACAO
    )


def e_ruido(
    titulo: str,
    corpo: str | None,
    publicado_em: str | None,
    coletado_em: str,
    limiares: ColetaLimiares,
) -> tuple[bool, str | None]:
    """`corpo=None` é o item cuja extração do corpo falhou (brief 083): ele não é ruído por isso — é
    gravado sem corpo e não alimenta cartão, qualificação nem gancho. Os filtros de título e de data
    valem para ele também."""
    if corpo is not None and len(corpo) < limiares.teaser_minimo_caracteres:
        return True, "corpo abaixo do teaser mínimo"

    if _PADRAO_LISTA.match(titulo):
        return True, "título de lista"

    if _tem_termo_patrocinado(titulo) or (corpo is not None and _corpo_declara_patrocinio(corpo)):
        return True, "marcado como patrocinado"

    if publicado_em:
        try:
            data_publicacao = datetime.fromisoformat(publicado_em)
            data_coleta = datetime.fromisoformat(coletado_em)
            dias_ate_coleta = (data_coleta - data_publicacao).days
        except ValueError:
            dias_ate_coleta = 0
        if dias_ate_coleta > limiares.dias_max_primeira_aparicao:
            return True, "mais dias que o permitido entre publicação e primeira coleta"

    return False, None
