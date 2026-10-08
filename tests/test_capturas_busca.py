from __future__ import annotations

from dataclasses import dataclass, field

from agente_nw.coleta.capturas import busca
from agente_nw.coleta.capturas.busca import Candidato, ResultadoBusca


@dataclass
class _PaginaFake:
    resposta_estado: tuple[str, str] = ("https://example.com", "conteúdo qualquer" * 200)
    resposta_links: list[tuple[str, str]] = field(default_factory=list)
    url_recebida: str = ""
    fechada: bool = False

    def ir_para(self, url: str) -> None:
        self.url_recebida = url

    def estado(self) -> tuple[str, str]:
        return self.resposta_estado

    def coletar_links(self) -> list[tuple[str, str]]:
        return self.resposta_links

    def fechar(self) -> None:
        self.fechada = True


def test_construir_query_junta_nome_e_empresa_quando_ambos_presentes() -> None:
    assert busca._construir_query("Joaquim Millan", "Bienal") == "Joaquim Millan Bienal"


def test_construir_query_usa_so_o_nome_quando_empresa_ausente() -> None:
    assert busca._construir_query("Michel Viriato", None) == "Michel Viriato"
    assert busca._construir_query("Michel Viriato", "") == "Michel Viriato"


def test_filtrar_candidatos_linkedin_extrai_nome_descricao_link() -> None:
    links = [
        (
            "https://www.linkedin.com/in/joaquim-millan/",
            "Joaquim Millan\nCurador · Bienal\nSão Paulo",
        ),
        ("https://www.linkedin.com/company/bienal/", "Bienal de São Paulo"),
        ("https://www.linkedin.com/in/outra-pessoa/", "Outra Pessoa\nDesigner"),
    ]

    candidatos = busca._filtrar_candidatos("linkedin", links)

    assert len(candidatos) == 2
    assert candidatos[0].nome_exibido == "Joaquim Millan"
    assert "Curador" in candidatos[0].descricao
    assert candidatos[0].link.endswith("/in/joaquim-millan/")
    assert candidatos[1].nome_exibido == "Outra Pessoa"


def test_filtrar_candidatos_ignora_duplicatas_pelo_link_base() -> None:
    links = [
        ("https://www.linkedin.com/in/mesma-pessoa/", "Nome A\nlinha 1"),
        ("https://www.linkedin.com/in/mesma-pessoa/?foo=bar", "Nome A\nlinha 2"),
    ]

    candidatos = busca._filtrar_candidatos("linkedin", links)

    assert len(candidatos) == 1


def test_filtrar_candidatos_ignora_link_nao_de_perfil() -> None:
    links = [
        ("https://www.linkedin.com/feed/update/urn:activity:123", "post"),
        ("https://www.linkedin.com/jobs/view/456", "vaga"),
    ]

    candidatos = busca._filtrar_candidatos("linkedin", links)

    assert candidatos == []


def test_buscar_devolve_autenticado_falso_em_pagina_de_login() -> None:
    pagina = _PaginaFake(
        resposta_estado=("https://www.linkedin.com/login?session_redirect=%2F", "faça login")
    )

    resultado = busca.buscar(pagina, "linkedin", "Ana", None)

    assert resultado.autenticado is False
    assert resultado.motivo is not None
    assert resultado.candidatos == []


def test_buscar_devolve_autenticado_falso_em_texto_muito_curto() -> None:
    pagina = _PaginaFake(resposta_estado=("https://www.linkedin.com/feed", "carregando..."))

    resultado = busca.buscar(pagina, "linkedin", "Ana", None)

    assert resultado.autenticado is False


def test_buscar_montagem_completa_com_pagina_autenticada() -> None:
    texto_body = "algum texto bem grande do feed autenticado " * 30
    pagina = _PaginaFake(
        resposta_estado=("https://www.linkedin.com/search/results/people/?keywords=Ana", texto_body),
        resposta_links=[
            ("https://www.linkedin.com/in/ana-silva/", "Ana Silva\nMarketing"),
        ],
    )

    resultado = busca.buscar(pagina, "linkedin", "Ana Silva", "Acme")

    assert "Ana+Silva+Acme" in pagina.url_recebida
    assert resultado.autenticado is True
    assert resultado.candidatos == [
        Candidato(
            nome_exibido="Ana Silva",
            descricao="Marketing",
            link="https://www.linkedin.com/in/ana-silva/",
        )
    ]


def test_buscar_rede_sem_template_devolve_motivo_sem_lancar() -> None:
    pagina = _PaginaFake()

    resultado = busca.buscar(pagina, "outro", "Ana", None)

    assert isinstance(resultado, ResultadoBusca)
    assert resultado.autenticado is False
    assert resultado.motivo is not None
    assert "outro" in resultado.motivo
