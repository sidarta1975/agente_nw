from __future__ import annotations

from pathlib import Path
from typing import Any

from agente_nw.coleta.capturas.navegador import Pagina


class PaginaPlaywright:
    """Implementação de `Pagina` sobre Playwright, com contexto persistente.

    O `user_data_dir` é dedicado por rede social — é o que preserva a sessão de
    login do usuário entre chamadas. `headless=False` é obrigatório: quando não
    houver sessão ativa, o usuário precisa ver a janela para logar."""

    def __init__(self, pasta_perfil: Path, headless: bool = False) -> None:
        from playwright.sync_api import sync_playwright

        pasta_perfil.mkdir(parents=True, exist_ok=True)
        self._runtime = sync_playwright().start()
        self._contexto: Any = self._runtime.chromium.launch_persistent_context(
            user_data_dir=str(pasta_perfil),
            headless=headless,
        )
        self._pagina: Any = self._contexto.pages[0] if self._contexto.pages else self._contexto.new_page()

    def ir_para(self, url: str) -> None:
        self._pagina.goto(url, wait_until="domcontentloaded", timeout=30000)
        self._pagina.wait_for_timeout(2000)

    def estado(self) -> tuple[str, str]:
        url = str(self._pagina.url)
        try:
            texto = str(self._pagina.locator("body").inner_text(timeout=5000))
        except Exception:
            texto = ""
        return url, texto

    def rolar(self) -> None:
        # Rola a janela e toda área com rolagem própria (listas em painel/modal) e aperta o botão
        # de "mostrar mais", que é como o LinkedIn carrega o resto da lista.
        script = (
            "(() => { "
            "window.scrollTo(0, document.body.scrollHeight); "
            "document.querySelectorAll('*').forEach(e => { "
            "  const o = getComputedStyle(e).overflowY; "
            "  if ((o === 'auto' || o === 'scroll') && e.scrollHeight > e.clientHeight + 20) "
            "    e.scrollTop = e.scrollHeight; "
            "}); "
            "const rotulo = /^(show more|mostrar mais|ver mais|carregar mais|load more)/i; "
            "Array.from(document.querySelectorAll('button')).forEach(b => { "
            "  if (rotulo.test((b.innerText || '').trim())) b.click(); "
            "}); "
            "})()"
        )
        self._pagina.evaluate(script)
        self._pagina.wait_for_timeout(1500)

    def coletar_links(self) -> list[tuple[str, str]]:
        """Devolve `[(href_absoluto, texto_visível_do_container)]` para cada
        `<a href>` na página. O texto do container é o `innerText` do ancestral
        mais próximo entre `li`, `article` ou `div` — o suficiente pra pegar
        nome do candidato + descrição adjacente em resultados de busca."""
        script = (
            "Array.from(document.querySelectorAll('a[href]')).map(a => { "
            "  const c = a.closest('li, article, div'); "
            "  return [a.href, c ? c.innerText.trim() : (a.innerText || '')]; "
            "})"
        )
        try:
            resultado = self._pagina.evaluate(script)
        except Exception:
            return []
        return [(str(item[0]), str(item[1])) for item in resultado]

    def fechar(self) -> None:
        try:
            self._contexto.close()
        finally:
            self._runtime.stop()


def abrir_pagina_playwright(pasta_perfil: Path) -> Pagina:
    """Fábrica de `Pagina` que o orquestrador injeta em produção."""
    return PaginaPlaywright(pasta_perfil, headless=False)
