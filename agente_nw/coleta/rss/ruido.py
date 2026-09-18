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


def _tem_termo_patrocinado(texto: str) -> bool:
    texto_lower = texto.lower()
    return any(termo in texto_lower for termo in _TERMOS_PATROCINADO)


def e_ruido(
    titulo: str,
    corpo: str | None,
    publicado_em: str | None,
    coletado_em: str,
    limiares: ColetaLimiares,
) -> tuple[bool, str | None]:
    if corpo is None or len(corpo) < limiares.teaser_minimo_caracteres:
        return True, "corpo abaixo do teaser mínimo"

    if _PADRAO_LISTA.match(titulo):
        return True, "título de lista"

    primeiras_linhas_corpo = "\n".join(corpo.splitlines()[:3])
    if _tem_termo_patrocinado(titulo) or _tem_termo_patrocinado(primeiras_linhas_corpo):
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
