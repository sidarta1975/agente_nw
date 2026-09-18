from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

NivelTema = Literal["dominio", "interesse", "curiosidade"]


class Configuracao(BaseModel):
    model_config = ConfigDict(frozen=True)

    banco: str
    pasta_saida: str
    pasta_backups: str
    ollama_url: str


class EmbeddingsRoteamento(BaseModel):
    model_config = ConfigDict(frozen=True)

    modelo: str


class TarefaRoteamento(BaseModel):
    model_config = ConfigDict(frozen=True)

    modelo: str
    num_ctx: int
    temperature: float
    format: str
    think: bool

    @field_validator("think")
    @classmethod
    def think_deve_ser_falso(cls, valor: bool) -> bool:
        if valor is not False:
            raise ValueError("think deve ser explicitamente false em toda tarefa")
        return valor


class NovaTentativaRoteamento(BaseModel):
    model_config = ConfigDict(frozen=True)

    temperature: float
    maximo: int


class PerfilRoteamento(BaseModel):
    model_config = ConfigDict(frozen=True)

    embeddings: EmbeddingsRoteamento
    tarefas: dict[str, TarefaRoteamento]
    nova_tentativa: NovaTentativaRoteamento


class Roteamento(BaseModel):
    model_config = ConfigDict(frozen=True)

    perfil_ativo: str
    perfis: dict[str, PerfilRoteamento]

    @model_validator(mode="after")
    def perfil_ativo_existe(self) -> Roteamento:
        if self.perfil_ativo not in self.perfis:
            raise ValueError(f"perfil_ativo '{self.perfil_ativo}' não está declarado em perfis")
        return self


class AgrupamentoLimiares(BaseModel):
    model_config = ConfigDict(frozen=True)

    cosseno_mesmo_assunto: float
    cosseno_republicacao: float
    divergencia_minima_fonte_independente: float
    janela_dias: int
    itens_para_dividir: int


class QualificacaoLimiares(BaseModel):
    model_config = ConfigDict(frozen=True)

    substancial_minimo: float
    conversavel_minimo: float
    teto_por_dia: int


class ConectorLimiares(BaseModel):
    model_config = ConfigDict(frozen=True)

    adjacencia_minima: float
    conversavel_viavel: float
    peso_aderencia_contato: float
    peso_aderencia_usuario: float
    peso_conversavel: float
    peso_nivel: dict[str, float]
    candidatos_por_contato: int
    itens_no_menu: int


class ColetaLimiares(BaseModel):
    model_config = ConfigDict(frozen=True)

    teaser_minimo_caracteres: int
    dias_max_primeira_aparicao: int
    retencao_texto_dias: int
    intervalo_google_news_segundos: float
    dias_alerta_feed_vazio: int


class Limiares(BaseModel):
    model_config = ConfigDict(frozen=True)

    agrupamento: AgrupamentoLimiares
    qualificacao: QualificacaoLimiares
    conector: ConectorLimiares
    coleta: ColetaLimiares


class TemaUsuario(BaseModel):
    model_config = ConfigDict(frozen=True)

    nome: str
    descricao: str
    sinonimos: list[str] = Field(default_factory=list)
    nivel: NivelTema
    peso: int = Field(ge=1, le=5)

    @field_validator("descricao")
    @classmethod
    def descricao_com_pelo_menos_oito_palavras(cls, valor: str) -> str:
        if len(valor.split()) < 8:
            raise ValueError(
                "descricao precisa de pelo menos 8 palavras — descrição curta demais rende embedding fraco"
            )
        return valor


class UsuarioTemas(BaseModel):
    model_config = ConfigDict(frozen=True)

    nome: str
    temas: list[TemaUsuario]


class TemasArquivo(BaseModel):
    model_config = ConfigDict(frozen=True)

    usuario: UsuarioTemas
    ignorar: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def nomes_de_tema_unicos(self) -> TemasArquivo:
        nomes = [tema.nome for tema in self.usuario.temas]
        if len(nomes) != len(set(nomes)):
            duplicados = {nome for nome in nomes if nomes.count(nome) > 1}
            raise ValueError(f"nome de tema duplicado: {', '.join(sorted(duplicados))}")
        return self


class FeedFonte(BaseModel):
    model_config = ConfigDict(frozen=True)

    nome: str
    url: str
    tipo: str
    confiabilidade: int = Field(default=5, ge=0, le=10)


class FontesArquivo(BaseModel):
    model_config = ConfigDict(frozen=True)

    feeds: list[FeedFonte]

    @model_validator(mode="after")
    def nomes_de_feed_unicos(self) -> FontesArquivo:
        nomes = [feed.nome for feed in self.feeds]
        if len(nomes) != len(set(nomes)):
            duplicados = {nome for nome in nomes if nomes.count(nome) > 1}
            raise ValueError(f"nome de feed duplicado: {', '.join(sorted(duplicados))}")
        return self
