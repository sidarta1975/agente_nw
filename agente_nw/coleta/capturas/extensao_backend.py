from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from agente_nw.nucleo.modelos.configuracao import ExtensaoLimiares
from agente_nw.ponte import ErroDaExtensao, Ponte, PonteIndisponivel, obter_ponte

__all__ = ["PaginaExtensao", "PonteIndisponivel", "abrir_pagina_extensao", "arquivar_navegador_antigo"]

_URL_INDISPONIVEL = "ponte://indisponivel"  # lido como "sem sessão" por quem consome a página


class PaginaExtensao:
    """`Pagina`/`PaginaLista`/`PaginaBusca` sobre a extensão do Chrome do usuário.

    Cada método vira uma tarefa para a ponte. Se a extensão não responder, a página fica
    "indisponível": `estado()` devolve uma URL e um texto que os chamadores já tratam como "sem
    sessão", `rolar`/`coletar_links` não fazem nada, e a ponte já avisou o usuário uma vez."""

    def __init__(self, ponte: Ponte, limiares: ExtensaoLimiares) -> None:
        self._ponte = ponte
        self._limiares = limiares
        self._aba_id: int | None = None
        self.motivo_indisponivel: str | None = None

    def _enviar(self, tarefa: dict[str, Any]) -> dict[str, Any] | None:
        if self.motivo_indisponivel is not None:
            return None
        try:
            return self._ponte.enviar(tarefa, self._limiares.tempo_limite_tarefa_s)
        except (PonteIndisponivel, ErroDaExtensao) as erro:
            self.motivo_indisponivel = str(erro)
            return None

    def ir_para(self, url: str) -> None:
        dados = self._enviar(
            {
                "acao": "abrir",
                "url": url,
                "ativa": not self._limiares.aba_em_segundo_plano,
                "pausa_s": self._limiares.pausa_entre_paginas_s,
            }
        )
        if dados is not None:
            self._aba_id = int(dados["aba_id"])

    def estado(self) -> tuple[str, str]:
        if self._aba_id is None:
            return _URL_INDISPONIVEL, ""
        dados = self._enviar(
            {"acao": "estado", "aba_id": self._aba_id, "maximo": self._limiares.maximo_caracteres_pagina}
        )
        if dados is None:
            return _URL_INDISPONIVEL, ""
        texto = str(dados.get("texto", ""))
        return str(dados.get("url", "")), texto[: self._limiares.maximo_caracteres_pagina]

    def rolar(self) -> None:
        if self._aba_id is None:
            return
        self._enviar(
            {
                "acao": "rolar",
                "aba_id": self._aba_id,
                "rotulos": list(self._limiares.textos_botao_mostrar_mais),
                "pausa_s": 1.5,
            }
        )

    def coletar_links(self) -> list[tuple[str, str]]:
        if self._aba_id is None:
            return []
        dados = self._enviar({"acao": "links", "aba_id": self._aba_id})
        if dados is None:
            return []
        itens = dados.get("links", [])
        return [(str(item[0]), str(item[1])) for item in itens] if isinstance(itens, list) else []

    def fechar(self) -> None:
        aba, self._aba_id = self._aba_id, None
        if aba is not None:
            self._enviar({"acao": "fechar", "aba_id": aba})


def arquivar_navegador_antigo(pasta_navegador: Path) -> Path | None:
    """Move os perfis do navegador separado (`dados/navegador/`) para `dados/_navegador_antigo/`,
    uma única vez e sem apagar nada. Devolve o destino se moveu."""
    destino = pasta_navegador.parent / "_navegador_antigo"
    if pasta_navegador.name != "navegador" or destino.exists():
        return None
    if not pasta_navegador.is_dir() or not any(pasta_navegador.iterdir()):
        return None
    shutil.move(str(pasta_navegador), str(destino))
    return destino


def abrir_pagina_extensao(pasta_ignorada: Path) -> PaginaExtensao:
    """Mesma assinatura do antigo `abrir_pagina_playwright`: o argumento (pasta do perfil do
    navegador separado) não é mais usado, a não ser para arquivar o perfil antigo na primeira vez."""
    from config.container import configuracao

    limiares = configuracao().limiares.extensao
    arquivar_navegador_antigo(pasta_ignorada.parent)
    return PaginaExtensao(obter_ponte(limiares.espera_extensao_s, limiares.navegador_app), limiares)
