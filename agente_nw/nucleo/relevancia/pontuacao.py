from __future__ import annotations

from dataclasses import dataclass

from agente_nw.nucleo.modelos.assunto_contato import TipoConector
from agente_nw.nucleo.modelos.configuracao import ConectorLimiares
from agente_nw.nucleo.vetores import cosseno


@dataclass
class Avaliacao:
    aderencia_contato: float
    aderencia_usuario: float
    conversavel: float
    score: float
    tipo: TipoConector
    ponto_de_apoio: str | None


def avaliar(
    centroide_assunto: list[float],
    centroide_contato: list[float],
    temas_usuario: list[tuple[str, str, list[float]]],
    conversavel: float,
    limiares: ConectorLimiares,
) -> Avaliacao:
    aderencia_contato = max(cosseno(centroide_assunto, centroide_contato), 0.0)

    melhor_ponderado = 0.0
    melhor_dominio_ou_interesse: float | None = None
    nome_melhor_dominio_ou_interesse: str | None = None
    melhor_qualquer: float | None = None
    nome_melhor_qualquer: str | None = None

    for nome, nivel, embedding_tema in temas_usuario:
        cos_bruto = cosseno(centroide_assunto, embedding_tema)
        cos_ponderado = max(cos_bruto, 0.0) * limiares.peso_nivel[nivel]
        melhor_ponderado = max(melhor_ponderado, cos_ponderado)

        if melhor_qualquer is None or cos_bruto > melhor_qualquer:
            melhor_qualquer = cos_bruto
            nome_melhor_qualquer = nome

        if nivel in ("dominio", "interesse") and (
            melhor_dominio_ou_interesse is None or cos_bruto > melhor_dominio_ou_interesse
        ):
            melhor_dominio_ou_interesse = cos_bruto
            nome_melhor_dominio_ou_interesse = nome

    aderencia_usuario = melhor_ponderado

    if melhor_dominio_ou_interesse is not None and melhor_dominio_ou_interesse >= limiares.adjacencia_minima:
        tipo: TipoConector = "conector"
        ponto_de_apoio = nome_melhor_dominio_ou_interesse
    elif (melhor_qualquer is not None and melhor_qualquer >= limiares.adjacencia_minima) or (
        conversavel >= limiares.conversavel_viavel
    ):
        tipo = "viavel_com_esforco"
        if melhor_qualquer is not None and melhor_qualquer >= limiares.adjacencia_minima:
            ponto_de_apoio = nome_melhor_qualquer
        else:
            ponto_de_apoio = None
    else:
        tipo = "fora_do_dominio"
        ponto_de_apoio = None

    score = (
        limiares.peso_aderencia_contato * aderencia_contato
        + limiares.peso_aderencia_usuario * aderencia_usuario
        + limiares.peso_conversavel * conversavel
    )

    return Avaliacao(
        aderencia_contato=aderencia_contato,
        aderencia_usuario=aderencia_usuario,
        conversavel=conversavel,
        score=score,
        tipo=tipo,
        ponto_de_apoio=ponto_de_apoio,
    )
