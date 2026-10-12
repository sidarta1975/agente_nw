from __future__ import annotations

import json
from pathlib import Path

import pytest

from agente_nw.coleta.capturas import listas
from agente_nw.nucleo.modelos.configuracao import ListasLimiares

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "listas"
LIMIARES = ListasLimiares(maximo_entradas=2000, pausa_rolagem_s=0, validade_dias=30)


def _links(rede: str) -> list[tuple[str, str]]:
    bruto = json.loads((FIXTURES / f"{rede}.json").read_text(encoding="utf-8"))
    return [(href, texto) for href, texto in bruto]


class _PaginaFalsa:
    def __init__(
        self,
        rodadas: list[list[tuple[str, str]]],
        url: str = "https://www.linkedin.com/mynetwork/invite-connect/connections/",
        texto: str = "x" * 600,
    ) -> None:
        self._rodadas = rodadas
        self._indice = 0
        self._url = url
        self._texto = texto
        self.urls: list[str] = []
        self.rolagens = 0
        self.fechada = False

    def ir_para(self, url: str) -> None:
        self.urls.append(url)

    def estado(self) -> tuple[str, str]:
        return self._url, self._texto

    def rolar(self) -> None:
        self.rolagens += 1
        self._indice = min(self._indice + 1, len(self._rodadas) - 1)

    def coletar_links(self) -> list[tuple[str, str]]:
        return self._rodadas[self._indice]

    def fechar(self) -> None:
        self.fechada = True


def test_linkedin_junta_foto_e_nome_do_mesmo_link_e_descarta_ruido() -> None:
    entradas = listas.parse_links("linkedin", _links("linkedin"))

    assert [e.nome for e in entradas] == ["Maria Souza", "Pedro Alves"]
    assert entradas[0].cabecalho == "Advogada tributarista · Souza & Lima"
    assert entradas[0].link == "https://www.linkedin.com/in/maria-souza-123"
    assert entradas[1].link == "https://www.linkedin.com/in/pedro-alves"


def test_instagram_usa_o_nome_de_exibicao_e_guarda_o_usuario_no_cabecalho() -> None:
    entradas = listas.parse_links("instagram", _links("instagram"))

    assert [e.nome for e in entradas] == ["Carla Dias", "Zé da Oficina"]
    assert entradas[0].cabecalho == "@carla.dias"
    assert entradas[1].cabecalho == "@oficina_do_ze · Marcenaria sob medida"


def test_x_ignora_caminhos_reservados() -> None:
    entradas = listas.parse_links("x", _links("x"))

    assert [e.nome for e in entradas] == ["Lucas Teixeira", "Ana Ribeiro"]
    assert entradas[0].cabecalho == "@lucas_t · Jornalista de economia"


def test_facebook_aceita_perfil_por_id_e_ignora_grupos() -> None:
    entradas = listas.parse_links("facebook", _links("facebook"))

    assert [e.nome for e in entradas] == ["Joana Melo", "Rui Faria"]
    assert entradas[1].link == "https://www.facebook.com/profile.php?id=100012345678"


def test_url_da_lista_por_rede() -> None:
    assert listas.url_da_lista("instagram", "fulano") == "https://www.instagram.com/fulano/following/"
    assert listas.url_da_lista("x", "fulano") == "https://x.com/fulano/following"
    assert listas.url_da_lista("instagram", None) is None
    assert listas.url_da_lista("linkedin", None) == (
        "https://www.linkedin.com/mynetwork/invite-connect/connections/"
    )


def test_usuario_e_lido_do_menu_da_pagina_inicial() -> None:
    menu = [
        ("https://www.instagram.com/explore/", "Explorar"),
        ("https://www.instagram.com/eu_mesmo/", "Perfil"),
    ]
    assert listas.parse_usuario_do_menu("instagram", menu) == "eu_mesmo"
    assert listas.parse_usuario_do_menu("instagram", menu[:1]) is None


def test_pagina_de_login_vira_sem_sessao() -> None:
    pagina = _PaginaFalsa([[]], url="https://www.linkedin.com/login", texto="")

    resultado = listas.ler_lista(
        pagina, "linkedin", None, LIMIARES, dorme=lambda _s: None, max_esperas_login=0
    )

    assert resultado.autenticado is False
    assert resultado.motivo is not None and "sem sessão" in resultado.motivo
    assert resultado.entradas == []


def test_instagram_sem_usuario_nao_abre_pagina_e_explica() -> None:
    pagina = _PaginaFalsa([[]])

    resultado = listas.ler_lista(pagina, "instagram", None, LIMIARES, dorme=lambda _s: None)

    assert resultado.autenticado is False
    assert resultado.motivo is not None and "redes.instagram.usuario" in resultado.motivo
    assert pagina.urls == []


def test_rolagem_acumula_ate_nao_haver_novidade() -> None:
    bruto = _links("linkedin")
    primeira = [bruto[1]]
    segunda = [bruto[1], bruto[2]]
    pagina = _PaginaFalsa([primeira, segunda, segunda, segunda, segunda, segunda])

    resultado = listas.ler_lista(pagina, "linkedin", None, LIMIARES, dorme=lambda _s: None)

    assert resultado.autenticado is True
    assert [e.nome for e in resultado.entradas] == ["Maria Souza", "Pedro Alves"]
    assert pagina.urls == ["https://www.linkedin.com/mynetwork/invite-connect/connections/"]
    assert pagina.rolagens >= 3


def test_maximo_de_entradas_trunca_a_leitura() -> None:
    pagina = _PaginaFalsa([_links("linkedin")])
    limiares = ListasLimiares(maximo_entradas=1, pausa_rolagem_s=0, validade_dias=30)

    resultado = listas.ler_lista(pagina, "linkedin", None, limiares, dorme=lambda _s: None)

    assert len(resultado.entradas) == 1
    assert resultado.truncada is True


@pytest.mark.parametrize("rede", ["linkedin", "instagram", "x", "facebook"])
def test_toda_rede_suportada_tem_url_de_lista(rede: str) -> None:
    assert listas.url_da_lista(rede, "alguem") is not None


def test_descobrir_usuario_le_o_menu_da_pagina_inicial() -> None:
    menu = [("https://x.com/eu_x", "Profile"), ("https://x.com/home", "Home")]
    pagina = _PaginaFalsa([menu], url="https://x.com/home")

    assert listas.descobrir_usuario(pagina, "x", dorme=lambda _s: None) == "eu_x"
