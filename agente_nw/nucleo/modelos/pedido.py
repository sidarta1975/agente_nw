from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from agente_nw.nucleo.modelos.contexto_consulta import MeioContato
from agente_nw.nucleo.modelos.localizacao import Localizacao, Opcao
from agente_nw.nucleo.modelos.perfil import Perfil
from agente_nw.nucleo.texto import sem_acento_e_caixa

ObjetivoPedido = Literal["retomar", "agradecer", "pedir", "manter", "apresentar", "responder", "outro"]
RegistroPedido = Literal["proximo", "cordial", "formal"]

CHAVES_DE_PISTA = ("profissao", "empresa", "cidade", "vinculo", "tempo_sem_contato", "link_rede_social")
_MAXIMO_INTERESSA = 5
_MAXIMO_TERMOS_BUSCA = 6
_TITULO_NO_INICIO = re.compile(r"^(dr|dra|sr|sra|prof|profa|doutor|doutora|seu|dona)\.?\s+", re.IGNORECASE)


def _sem_duplicatas(valores: list[str]) -> list[str]:
    vistos: set[str] = set()
    unicos: list[str] = []
    for valor in valores:
        limpo = valor.strip()
        chave = sem_acento_e_caixa(limpo)
        if not chave or chave in vistos:
            continue
        vistos.add(chave)
        unicos.append(limpo)
    return unicos


class PedidoExtraido(BaseModel):
    """Pedido em texto livre entendido pela IA (tarefa `extrair_pedido`)."""

    model_config = ConfigDict(frozen=True)

    pessoa_nome: str = ""
    pessoa_pistas: dict[str, str] = Field(default_factory=dict)
    objetivo: ObjetivoPedido
    objetivo_texto: str
    meio: MeioContato = "whatsapp"
    registro: RegistroPedido = "cordial"
    assunto_principal: str
    interessa: list[str] = Field(default_factory=list)
    evitar: list[str] = Field(default_factory=list)
    termos_busca: list[str]
    continuacao: bool = False
    confianca: float = Field(ge=0, le=1)

    @field_validator("objetivo", "meio", "registro", mode="before")
    @classmethod
    def rotulo_desconhecido_vira_neutro(cls, valor: Any, info: ValidationInfo) -> Any:
        """O modelo às vezes inventa um rótulo ("conversar"). O sentido fica em `objetivo_texto`; o
        rótulo cai no valor neutro em vez de derrubar o pedido inteiro."""
        permitidos = {
            "objetivo": (get_args(ObjetivoPedido), "outro"),
            "meio": (get_args(MeioContato), "outro"),
            "registro": (get_args(RegistroPedido), "cordial"),
        }[str(info.field_name)]
        normalizado = sem_acento_e_caixa(valor) if isinstance(valor, str) else valor
        return normalizado if normalizado in permitidos[0] else permitidos[1]

    @field_validator("pessoa_nome")
    @classmethod
    def sem_titulo(cls, valor: str) -> str:
        limpo = valor.strip()
        while _TITULO_NO_INICIO.match(limpo):
            limpo = _TITULO_NO_INICIO.sub("", limpo, count=1).strip()
        return limpo

    @field_validator("pessoa_pistas")
    @classmethod
    def so_pistas_conhecidas_e_preenchidas(cls, valor: dict[str, str]) -> dict[str, str]:
        return {
            chave: texto.strip()
            for chave, texto in valor.items()
            if chave in CHAVES_DE_PISTA and isinstance(texto, str) and texto.strip()
        }

    @field_validator("interessa", "evitar")
    @classmethod
    def lista_sem_duplicatas(cls, valor: list[str]) -> list[str]:
        return _sem_duplicatas(valor)[:_MAXIMO_INTERESSA]

    @field_validator("termos_busca")
    @classmethod
    def termos_pelo_menos_um_no_maximo_seis(cls, valor: list[str]) -> list[str]:
        """Sem termo não há o que coletar; acima de seis, corta em vez de rejeitar —
        o modelo tende a listar demais, e uma nova tentativa custa mais do que o corte."""
        unicos = _sem_duplicatas(valor)
        if not unicos:
            raise ValueError("termos_busca precisa de pelo menos um termo")
        return unicos[:_MAXIMO_TERMOS_BUSCA]


@dataclass
class ResultadoPedido:
    pedido_id: int
    pedido: PedidoExtraido
    perfil: Perfil | None
    contato_criado: bool = False
    contato_ambiguo: bool = False
    candidatos: list[Perfil] = field(default_factory=list)
    # Curadoria por rede (brief 037): uma localização para cada rede em que o contato ainda não tem perfil.
    localizacoes: list[Localizacao] = field(default_factory=list)
    links_nao_reconhecidos: list[str] = field(default_factory=list)  # de --perfil
    link_gravado: Opcao | None = None  # o pedido trouxe o link da pessoa e ele foi gravado direto
