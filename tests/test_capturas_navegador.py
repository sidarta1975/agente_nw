from __future__ import annotations

import random
from dataclasses import dataclass

from agente_nw.coleta.capturas import navegador


@dataclass
class _PaginaFake:
    """Página falsa cujo estado (url, texto) muda numa sequência declarada.

    O algoritmo chama `ir_para` uma vez e `estado` várias vezes. A cada
    chamada de `estado`, devolve o próximo item da lista `estados`;
    se acabar, repete o último. `rolar` só marca que rolou."""

    estados: list[tuple[str, str]]
    _chamadas_estado: int = 0
    rolagens: int = 0
    fechada: bool = False
    url_recebida: str = ""

    def ir_para(self, url: str) -> None:
        self.url_recebida = url

    def estado(self) -> tuple[str, str]:
        indice = min(self._chamadas_estado, len(self.estados) - 1)
        self._chamadas_estado += 1
        return self.estados[indice]

    def rolar(self) -> None:
        self.rolagens += 1

    def fechar(self) -> None:
        self.fechada = True


def _texto_longo(cabecalho: str, blocos: list[str]) -> str:
    corpo = "\n\n".join(blocos)
    preenchimento = "conteúdo variado suficiente para passar do mínimo. " * 30
    return f"{cabecalho}\n\n{corpo}\n\n{preenchimento}"


def test_pagina_autenticada_captura_blocos_do_texto_visivel() -> None:
    texto = _texto_longo(
        "feed do usuário",
        [
            "Publicação de exemplo com conteúdo suficiente para ser considerada um bloco válido.",
            "Segunda publicação distinta, também com tamanho aceitável para virar bloco.",
        ],
    )
    pagina = _PaginaFake(estados=[("https://exemplo.com/feed", texto)])

    resultado = navegador.ler(
        pagina,
        "https://exemplo.com/feed",
        dorme=lambda _s: None,
        aleatorio=random.Random(0),
        max_rolagens=1,
    )

    assert resultado.autenticado is True
    assert resultado.motivo is None
    assert any("Publicação de exemplo" in bloco for bloco in resultado.blocos)
    assert any("Segunda publicação" in bloco for bloco in resultado.blocos)


def test_pagina_de_login_por_url_e_prazo_esgotado_retorna_nao_autenticado() -> None:
    pagina = _PaginaFake(estados=[("https://exemplo.com/login?next=%2Ffeed", "faça login")])

    resultado = navegador.ler(
        pagina,
        "https://exemplo.com/feed",
        dorme=lambda _s: None,
        aleatorio=random.Random(0),
        max_esperas_login=3,
        espera_login_s=0.0,
        max_rolagens=1,
    )

    assert resultado.autenticado is False
    assert resultado.motivo is not None
    assert resultado.blocos == []


def test_pagina_de_login_por_texto_curto_e_login_concluido_dentro_do_prazo() -> None:
    texto_autenticado = _texto_longo(
        "feed",
        ["Bloco após login com tamanho suficiente para ser considerado válido pelo algoritmo."],
    )
    pagina = _PaginaFake(
        estados=[
            ("https://exemplo.com/feed", "carregando..."),
            ("https://exemplo.com/feed", "ainda carregando..."),
            ("https://exemplo.com/feed", texto_autenticado),
            ("https://exemplo.com/feed", texto_autenticado),
        ]
    )

    resultado = navegador.ler(
        pagina,
        "https://exemplo.com/feed",
        dorme=lambda _s: None,
        aleatorio=random.Random(0),
        max_esperas_login=5,
        espera_login_s=0.0,
        max_rolagens=1,
    )

    assert resultado.autenticado is True
    assert any("Bloco após login" in bloco for bloco in resultado.blocos)


def test_rolagem_acumula_blocos_unicos_sem_duplicar() -> None:
    texto_inicial = _texto_longo(
        "feed",
        ["Bloco A com tamanho suficiente para ser considerado válido pelo algoritmo."],
    )
    texto_apos_rolagem = _texto_longo(
        "feed",
        [
            "Bloco A com tamanho suficiente para ser considerado válido pelo algoritmo.",
            "Bloco B novo com tamanho igualmente suficiente para virar bloco extraído.",
        ],
    )
    pagina = _PaginaFake(
        estados=[
            ("https://exemplo.com/feed", texto_inicial),
            ("https://exemplo.com/feed", texto_apos_rolagem),
        ]
    )

    resultado = navegador.ler(
        pagina,
        "https://exemplo.com/feed",
        dorme=lambda _s: None,
        aleatorio=random.Random(0),
        max_rolagens=2,
    )

    assert resultado.autenticado is True
    a_count = sum(1 for b in resultado.blocos if "Bloco A" in b)
    b_count = sum(1 for b in resultado.blocos if "Bloco B" in b)
    assert a_count == 1
    assert b_count == 1
    assert pagina.rolagens == 1
