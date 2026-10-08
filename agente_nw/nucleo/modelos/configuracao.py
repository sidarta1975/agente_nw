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
    perfil_llm: str | None = None


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

    memoria_minima_gb: int = Field(ge=1)
    enviar_think: bool = True
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

    @model_validator(mode="after")
    def perfis_declaram_as_mesmas_tarefas(self) -> Roteamento:
        referencia_nome, referencia = next(iter(self.perfis.items()))
        esperadas = set(referencia.tarefas)
        for nome, perfil in self.perfis.items():
            faltando = esperadas - set(perfil.tarefas)
            sobrando = set(perfil.tarefas) - esperadas
            if faltando or sobrando:
                raise ValueError(
                    f"perfil '{nome}' difere de '{referencia_nome}' nas tarefas: "
                    f"faltando {sorted(faltando)}, sobrando {sorted(sobrando)}"
                )
            if perfil.embeddings.modelo != referencia.embeddings.modelo:
                raise ValueError(
                    f"perfil '{nome}' usa embeddings '{perfil.embeddings.modelo}', "
                    f"diferente de '{referencia_nome}' ('{referencia.embeddings.modelo}')"
                )
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


class ConsultaLimiares(BaseModel):
    """Calibração do caminho por consulta (brief 034/035)."""

    model_config = ConfigDict(frozen=True)

    minima: float
    peso_consulta: float
    peso_contato: float
    peso_usuario: float
    peso_conversavel: float
    selecao_peso_consulta: float
    selecao_peso_contato: float

    @model_validator(mode="after")
    def pesos_somam_o_esperado(self) -> ConsultaLimiares:
        soma_score = self.peso_consulta + self.peso_contato + self.peso_usuario + self.peso_conversavel
        if abs(soma_score - 100) > 1e-9:
            raise ValueError(f"pesos do score devem somar 100, somam {soma_score}")
        soma_selecao = self.selecao_peso_consulta + self.selecao_peso_contato
        if abs(soma_selecao - 1) > 1e-9:
            raise ValueError(f"pesos da seleção devem somar 1, somam {soma_selecao}")
        return self


class ConectorLimiares(BaseModel):
    model_config = ConfigDict(frozen=True)

    adjacencia_minima: float
    consulta: ConsultaLimiares
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


class CartaoLimiares(BaseModel):
    model_config = ConfigDict(frozen=True)

    teto_por_dia: int


class Limiares(BaseModel):
    model_config = ConfigDict(frozen=True)

    agrupamento: AgrupamentoLimiares
    qualificacao: QualificacaoLimiares
    conector: ConectorLimiares
    coleta: ColetaLimiares
    cartao: CartaoLimiares


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
