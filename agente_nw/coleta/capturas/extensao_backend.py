from __future__ import annotations

import json
import shutil
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from agente_nw.coleta.capturas.imagens import ImagemCapturada
from agente_nw.coleta.capturas.navegador import MIN_CHARS_AUTENTICADO, URL_LOGIN_SUBSTRINGS
from agente_nw.nucleo.modelos.configuracao import ExtensaoLimiares
from agente_nw.ponte import ErroDaExtensao, Ponte, PonteIndisponivel, obter_ponte

__all__ = [
    "PaginaExtensao",
    "PonteIndisponivel",
    "abrir_pagina_extensao",
    "arquivar_navegador_antigo",
    "aviso_de_corte",
]

_PASSO_RENDER_S = 1.0
_URL_INDISPONIVEL = "ponte://indisponivel"  # lido como "sem sessão" por quem consome a página


def _milhar(numero: int) -> str:
    return f"{numero:,}".replace(",", ".")


def aviso_de_corte(maximo: int, tamanho_original: int) -> str:
    """A frase do resumo da leitura quando a página passou do teto (brief 083, P-013)."""
    return f"página cortada em {_milhar(maximo)} de {_milhar(tamanho_original)} caracteres"


def _registrar_corte(caminho_log: Path, origem: str, url: str, maximo: int, tamanho_original: int) -> None:
    """Uma linha `"corte_pagina": true` no `chamadas_llm.jsonl`, no padrão do aviso do `porteiro`
    (brief 077): falha de escrita nunca derruba a leitura."""
    try:
        caminho_log.parent.mkdir(parents=True, exist_ok=True)
        linha = json.dumps(
            {
                "corte_pagina": True,
                "origem": origem,  # "extensao": cortado dentro do Chrome; "programa": cortado aqui
                "url": url,
                "quando": datetime.now(UTC).isoformat(),
                "maximo": maximo,
                "tamanho_original": tamanho_original,
                "aviso": aviso_de_corte(maximo, tamanho_original),
            },
            ensure_ascii=False,
        )
        with caminho_log.open("a", encoding="utf-8") as arquivo:
            arquivo.write(linha + "\n")
    except Exception:
        pass


class PaginaExtensao:
    """`Pagina`/`PaginaLista`/`PaginaBusca` sobre a extensão do Chrome do usuário.

    Cada método vira uma tarefa para a ponte. Se a extensão não responder, a página fica
    "indisponível": `estado()` devolve uma URL e um texto que os chamadores já tratam como "sem
    sessão", `rolar`/`coletar_links` não fazem nada, e a ponte já avisou o usuário uma vez."""

    def __init__(
        self,
        ponte: Ponte,
        limiares: ExtensaoLimiares,
        dorme: Callable[[float], None] = time.sleep,
        maximo_entradas: int = 2000,
        caminho_log: Path | None = None,
    ) -> None:
        self._maximo_entradas = maximo_entradas
        self._caminho_log = caminho_log
        self.avisos_corte: list[str] = []  # "página cortada em N de M caracteres", sem repetição
        self._ponte = ponte
        self._dorme = dorme
        self._limiares = limiares
        self._aba_id: int | None = None
        self.motivo_indisponivel: str | None = None
        self.aviso_imagens: str | None = None  # a extensão não leu as imagens (a página segue disponível)

    def _enviar(self, tarefa: dict[str, Any], so_esta_falha: bool = False) -> dict[str, Any] | None:
        """`so_esta_falha`: um erro da extensão nesta tarefa não derruba a página inteira (a ponte sim)."""
        if self.motivo_indisponivel is not None:
            return None
        try:
            return self._ponte.enviar(tarefa, self._limiares.tempo_limite_tarefa_s)
        except ErroDaExtensao as erro:
            if so_esta_falha:
                self.aviso_imagens = str(erro)
            else:
                self.motivo_indisponivel = str(erro)
            return None
        except PonteIndisponivel as erro:
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
        """Lê a página; se o texto ainda for curto (X e Instagram desenham depois de carregar) e a
        URL não for de login, espera até `espera_render_s` e lê de novo."""
        esperado = 0.0
        while True:
            url, texto = self._ler_estado()
            ainda_desenhando = len(texto.strip()) < MIN_CHARS_AUTENTICADO and not any(
                marca in url.lower() for marca in URL_LOGIN_SUBSTRINGS
            )
            if not ainda_desenhando or url == _URL_INDISPONIVEL or esperado >= self._limiares.espera_render_s:
                return url, texto
            self._dorme(_PASSO_RENDER_S)
            esperado += _PASSO_RENDER_S

    def _ler_estado(self) -> tuple[str, str]:
        if self._aba_id is None:
            return _URL_INDISPONIVEL, ""
        dados = self._enviar(
            {"acao": "estado", "aba_id": self._aba_id, "maximo": self._limiares.maximo_caracteres_pagina}
        )
        if dados is None:
            return _URL_INDISPONIVEL, ""
        url = str(dados.get("url", ""))
        texto = str(dados.get("texto", ""))
        maximo = self._limiares.maximo_caracteres_pagina
        if dados.get("cortado") is True:
            self._avisar_corte("extensao", url, maximo, int(dados.get("tamanho_original") or len(texto)))
        elif len(texto) > maximo:  # extensão sem o campo `cortado` (versão antiga): o corte é daqui
            self._avisar_corte("programa", url, maximo, len(texto))
        return url, texto[:maximo]

    def _avisar_corte(self, origem: str, url: str, maximo: int, tamanho_original: int) -> None:
        """O corte da página nunca é silencioso (brief 083): vira aviso no resumo da leitura e linha no
        `chamadas_llm.jsonl`, uma vez por página e tamanho (a mesma página relida não repete)."""
        aviso = aviso_de_corte(maximo, tamanho_original)
        if aviso in self.avisos_corte:
            return
        self.avisos_corte.append(aviso)
        if self._caminho_log is not None:
            _registrar_corte(self._caminho_log, origem, url, maximo, tamanho_original)

    def rolar(self) -> None:
        if self._aba_id is None:
            return
        self._enviar(
            {
                "acao": "rolar",
                "aba_id": self._aba_id,
                "rotulos": list(self._limiares.textos_botao_mostrar_mais),
                "pausa_s": 1.5,
                "maximo_entradas": self._maximo_entradas,
                "pausa_pagina_s": self._limiares.pausa_entre_paginas_s,
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

    def imagens(
        self, maximo: int, largura_minima: int, ignorar: list[str] | None = None
    ) -> list[ImagemCapturada]:
        """Imagens publicadas na página (bytes em base64, só para serem descritas). Pula as `ignorar`."""
        if self._aba_id is None:
            return []
        dados = self._enviar(
            {
                "acao": "imagens",
                "aba_id": self._aba_id,
                "maximo": maximo,
                "largura_minima": largura_minima,
                "ignorar": list(ignorar or []),
            },
            so_esta_falha=True,
        )
        if dados is None:
            return []
        itens = dados.get("imagens", [])
        if not isinstance(itens, list):
            return []
        return [
            ImagemCapturada(
                src=str(item.get("src", "")),
                alt=str(item.get("alt", "")),
                link=str(item.get("link", "")),
                mime=str(item.get("mime", "")),
                dados_base64=str(item.get("dados", "")),
            )
            for item in itens
            if isinstance(item, dict) and item.get("dados")
        ]

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
    from config.container import caminho_log_chamadas_llm, configuracao

    todos = configuracao().limiares
    limiares = todos.extensao
    arquivar_navegador_antigo(pasta_ignorada.parent)
    return PaginaExtensao(
        obter_ponte(limiares.espera_extensao_s, limiares.navegador_app, limiares.navegador_perfil),
        limiares,
        maximo_entradas=todos.listas.maximo_entradas,
        caminho_log=caminho_log_chamadas_llm(),
    )
