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
    aderencia_consulta: float | None = None


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


def avaliar_por_consulta(
    centroide_assunto: list[float],
    centroide_consulta: list[float],
    centroide_contato: list[float] | None,
    temas_usuario: list[tuple[str, str, list[float]]],
    conversavel: float,
    limiares: ConectorLimiares,
    termos_consulta: list[tuple[str, list[float]]] | None = None,
    tags_contato: list[tuple[str, list[float]]] | None = None,
) -> Avaliacao:
    """Pontuação em que o contexto da consulta é o sinal principal; contato e usuário só enriquecem."""
    aderencia_consulta = max(cosseno(centroide_assunto, centroide_consulta), 0.0)
    aderencia_contato = (
        max(cosseno(centroide_assunto, centroide_contato), 0.0) if centroide_contato is not None else 0.0
    )

    aderencia_usuario = 0.0
    for _nome, nivel, embedding_tema in temas_usuario:
        ponderado = max(cosseno(centroide_assunto, embedding_tema), 0.0) * limiares.peso_nivel[nivel]
        aderencia_usuario = max(aderencia_usuario, ponderado)

    # Quem sustenta o "conector": (nome, cosseno) de cada sinal que passou do seu limiar.
    sustentos: list[tuple[str, float]] = []
    if aderencia_consulta >= limiares.consulta.minima:
        pares_contexto = termos_consulta or []
        melhor_termo = max(
            ((nome, cosseno(centroide_assunto, vetor)) for nome, vetor in pares_contexto),
            key=lambda par: par[1],
            default=None,
        )
        sustentos.append(melhor_termo if melhor_termo is not None else ("", aderencia_consulta))
    for nome, nivel, embedding_tema in temas_usuario:
        cos_bruto = cosseno(centroide_assunto, embedding_tema)
        if nivel in ("dominio", "interesse") and cos_bruto >= limiares.adjacencia_minima:
            sustentos.append((nome, cos_bruto))
    if tags_contato:
        for nome, embedding_tag in tags_contato:
            cos_bruto = cosseno(centroide_assunto, embedding_tag)
            if cos_bruto >= limiares.adjacencia_minima:
                sustentos.append((nome, cos_bruto))
    elif centroide_contato is not None and aderencia_contato >= limiares.adjacencia_minima:
        sustentos.append(("", aderencia_contato))

    ponto_de_apoio: str | None
    if sustentos:
        tipo: TipoConector = "conector"
        nome_apoio = max(sustentos, key=lambda par: par[1])[0]
        ponto_de_apoio = nome_apoio or None
    elif conversavel >= limiares.conversavel_viavel:
        tipo = "viavel_com_esforco"
        ponto_de_apoio = None
    else:
        tipo = "fora_do_dominio"
        ponto_de_apoio = None

    score = (
        limiares.consulta.peso_consulta * aderencia_consulta
        + limiares.consulta.peso_contato * aderencia_contato
        + limiares.consulta.peso_usuario * aderencia_usuario
        + limiares.consulta.peso_conversavel * conversavel
    )

    return Avaliacao(
        aderencia_contato=aderencia_contato,
        aderencia_usuario=aderencia_usuario,
        conversavel=conversavel,
        score=score,
        tipo=tipo,
        ponto_de_apoio=ponto_de_apoio,
        aderencia_consulta=aderencia_consulta,
    )
