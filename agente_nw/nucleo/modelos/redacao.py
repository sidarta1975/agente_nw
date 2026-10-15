from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from agente_nw.nucleo.modelos.contexto_consulta import MeioContato
from agente_nw.nucleo.modelos.pedido import RegistroPedido
from agente_nw.nucleo.texto import sem_acento_e_caixa

LIMITE_PALAVRAS_MENSAGEM: dict[str, int] = {"proximo": 60, "cordial": 80, "formal": 110}
MAXIMO_PALAVRAS_TITULO = 12
MAXIMO_GANCHOS = 4


class LinkNoticia(BaseModel):
    """Notícia real que sustenta o gancho; vem do banco, nunca do modelo."""

    model_config = ConfigDict(frozen=True)

    veiculo: str
    titulo: str
    url: str
    texto: str | None = None  # texto integral da notícia no momento da entrega (fica no histórico)


class Gancho(BaseModel):
    """Uma mensagem pronta. Com `assunto_id` é um gancho de notícia; sem ele (`None`) é a mensagem base,
    que nasce do objetivo e da pessoa e cita uma peculiaridade dela (brief 047)."""

    model_config = ConfigDict(frozen=True)

    assunto_id: int | None = None
    titulo: str | None = None
    noticia: str | None = None
    peculiaridade: str | None = None
    por_que_para_esta_pessoa: str = ""
    mensagem: str = Field(min_length=1)
    abordagem_presencial: str | None = None
    links: list[LinkNoticia] = Field(default_factory=list)

    @field_validator("por_que_para_esta_pessoa", "mensagem")
    @classmethod
    def sem_espacos_nas_pontas(cls, valor: str) -> str:
        return valor.strip()

    @field_validator("titulo", "noticia", "peculiaridade", "abordagem_presencial")
    @classmethod
    def vazio_vira_none(cls, valor: str | None) -> str | None:
        limpo = (valor or "").strip()
        return limpo or None

    @model_validator(mode="after")
    def gancho_de_noticia_tem_titulo_e_noticia(self) -> Gancho:
        if self.assunto_id is not None and (
            self.titulo is None or self.noticia is None or not self.por_que_para_esta_pessoa
        ):
            raise ValueError("gancho de notícia exige titulo, noticia e por_que_para_esta_pessoa")
        return self

    @property
    def e_base(self) -> bool:
        return self.assunto_id is None


class RespostaRedacao(BaseModel):
    """O que o modelo devolve (tarefa `redigir_ganchos`), antes da validação de conteúdo."""

    model_config = ConfigDict(frozen=True)

    ganchos: list[Gancho] = Field(default_factory=list)
    aviso: str | None = None


class Redacao(BaseModel):
    """O que o sistema entrega: ganchos já validados e, se houver, um aviso."""

    model_config = ConfigDict(frozen=True)

    ganchos: list[Gancho] = Field(default_factory=list)
    aviso: str | None = None
    registro_usado: RegistroPedido


def _palavras(texto: str) -> int:
    return len(texto.split())


def validar_ganchos(
    ganchos: list[Gancho],
    registro: RegistroPedido,
    evitar: list[str],
    assuntos_validos: set[int],
    meio: MeioContato,
    usados: set[int],
) -> tuple[list[Gancho], list[str]]:
    """Fica com os ganchos que obedecem às regras de redação; devolve também o motivo de cada descarte.

    Descarta: mensagem base repetida, assunto fora dos selecionados, assunto repetido, assunto já usado
    antes, mensagem com termo de `evitar`, mensagem acima do limite do registro e título acima de doze
    palavras. A mensagem base (sem assunto) pula as checagens de assunto e vai sempre em primeiro; fica
    uma base e até `MAXIMO_GANCHOS` ganchos de notícia. A abordagem presencial só fica quando o meio é
    "pessoalmente"."""
    limite = LIMITE_PALAVRAS_MENSAGEM[registro]
    termos_evitar = [t for t in (sem_acento_e_caixa(e) for e in evitar) if t]
    base: list[Gancho] = []
    aceitos: list[Gancho] = []
    motivos: list[str] = []
    vistos: set[int] = set()
    for gancho in ganchos:
        rotulo = "mensagem base" if gancho.assunto_id is None else f"gancho do assunto {gancho.assunto_id}"
        if gancho.assunto_id is None and base:
            motivos.append(f"{rotulo} descartada: já existe uma mensagem base")
        elif gancho.assunto_id is not None and gancho.assunto_id not in assuntos_validos:
            motivos.append(f"{rotulo} descartado: assunto que não foi selecionado")
        elif gancho.assunto_id is not None and gancho.assunto_id in vistos:
            motivos.append(f"{rotulo} descartado: assunto repetido")
        elif gancho.assunto_id is not None and gancho.assunto_id in usados:
            motivos.append(f"{rotulo} descartado: assunto já usado antes com esta pessoa")
        else:
            mensagem_normal = sem_acento_e_caixa(gancho.mensagem)
            achado = next((t for t in termos_evitar if t in mensagem_normal), None)
            if achado is not None:
                motivos.append(f"{rotulo} descartado: a mensagem cita '{achado}', que o pedido manda evitar")
            elif _palavras(gancho.mensagem) > limite:
                motivos.append(
                    f"{rotulo} descartado: mensagem com {_palavras(gancho.mensagem)} palavras "
                    f"(limite {limite} no registro {registro})"
                )
            elif _palavras(gancho.titulo or "") > MAXIMO_PALAVRAS_TITULO:
                motivos.append(f"{rotulo} descartado: título com mais de {MAXIMO_PALAVRAS_TITULO} palavras")
            else:
                if meio != "pessoalmente" and gancho.abordagem_presencial is not None:
                    gancho = gancho.model_copy(update={"abordagem_presencial": None})
                if gancho.assunto_id is None:
                    base.append(gancho)
                else:
                    vistos.add(gancho.assunto_id)
                    aceitos.append(gancho)
    return [*base, *aceitos[:MAXIMO_GANCHOS]], motivos
