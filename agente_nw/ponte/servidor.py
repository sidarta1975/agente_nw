from __future__ import annotations

import itertools
import json
import queue
import secrets
import threading
import time
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from typing import Any
from urllib.parse import parse_qs, urlparse

HOST = "127.0.0.1"
PORTA_PADRAO = 8766
ID_EXTENSAO = "noicodbmhccmanolhjlbfjhamdbokgan"  # derivado da `key` de extensao/manifest.json
LONG_POLL_S = 25.0
_TENTATIVAS_DE_AQUECIMENTO = 3
_LIMITE_DO_AQUECIMENTO_S = 15.0
SEM_CONTATO_S = 8.0  # sem poll ativo há tanto tempo, com tarefa na fila: a aba da ponte foi fechada


class PonteIndisponivel(Exception):
    """A extensão (ou a aba da ponte) não respondeu a tempo."""


class ErroDaExtensao(Exception):
    """A extensão respondeu com erro (ex.: rede fora da lista permitida)."""


def _avisar_no_terminal(texto: str) -> None:
    print(f"AVISO: {texto}", flush=True)


class Ponte:
    """Servidor local que liga o programa à extensão do Chrome, passando pela página-ponte.

    O programa chama `enviar(tarefa)`; a página-ponte (aberta no Chrome do usuário) busca a tarefa
    em `GET /tarefa`, repassa à extensão e devolve a resposta em `POST /resultado`. Tudo exige o
    token gerado nesta execução, e o servidor só escuta em 127.0.0.1."""

    def __init__(
        self,
        porta: int = PORTA_PADRAO,
        abrir_navegador: Callable[[str], object] | None = None,
        espera_conexao_s: float = 20.0,
        long_poll_s: float = LONG_POLL_S,
        sem_contato_s: float = SEM_CONTATO_S,
        avisar: Callable[[str], None] = _avisar_no_terminal,
        aquecer: bool = False,
        limite_do_aquecimento_s: float = _LIMITE_DO_AQUECIMENTO_S,
    ) -> None:
        self.token = secrets.token_urlsafe(24)
        self._porta_pedida = porta
        self._abrir_navegador = abrir_navegador
        self._espera_conexao_s = espera_conexao_s
        self._long_poll_s = long_poll_s
        self._sem_contato_s = sem_contato_s
        self._avisar = avisar
        self._tarefas: queue.Queue[dict[str, Any]] = queue.Queue()
        self._resultados: dict[int, dict[str, Any]] = {}
        self._eventos: dict[int, threading.Event] = {}
        self._trava = threading.Lock()
        self._ids = itertools.count(1)
        self._servidor: ThreadingHTTPServer | None = None
        self._encerrado = threading.Event()
        self._navegador_aberto = False
        self._polls_ativos = 0
        self._ultima_atividade: float | None = None
        self._puxadas: set[int] = set()
        self._falha: str | None = None
        self._aquecer = aquecer
        self._limite_do_aquecimento_s = limite_do_aquecimento_s
        self._aquecida = False

    # ---- ciclo de vida -------------------------------------------------------------------------

    @property
    def porta(self) -> int:
        assert self._servidor is not None, "ponte não iniciada"
        return int(self._servidor.socket.getsockname()[1])

    @property
    def url(self) -> str:
        return f"http://{HOST}:{self.porta}/ponte?token={self.token}"

    def iniciar(self) -> None:
        if self._servidor is not None:
            return
        ponte = self

        class Atendente(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: Any) -> None:
                pass

            def _token_ok(self) -> bool:
                consulta = parse_qs(urlparse(self.path).query)
                return consulta.get("token", [""])[0] == ponte.token

            def _responder(self, codigo: int, corpo: bytes, tipo: str) -> None:
                self.send_response(codigo)
                self.send_header("Content-Type", tipo)
                self.send_header("Content-Length", str(len(corpo)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(corpo)

            def _json(self, codigo: int, dados: dict[str, Any]) -> None:
                self._responder(codigo, json.dumps(dados).encode(), "application/json")

            def do_GET(self) -> None:
                caminho = urlparse(self.path).path
                if not self._token_ok():
                    self._json(403, {"erro": "token inválido"})
                elif caminho == "/ponte":
                    self._responder(200, ponte._pagina().encode(), "text/html; charset=utf-8")
                elif caminho == "/tarefa":
                    self._json(200, ponte._proxima_tarefa())
                else:
                    self._json(404, {"erro": "não existe"})

            def do_POST(self) -> None:
                if not self._token_ok():
                    self._json(403, {"erro": "token inválido"})
                elif urlparse(self.path).path != "/resultado":
                    self._json(404, {"erro": "não existe"})
                else:
                    tamanho = int(self.headers.get("Content-Length", "0"))
                    try:
                        dados = json.loads(self.rfile.read(tamanho) or b"{}")
                    except json.JSONDecodeError:
                        self._json(400, {"erro": "JSON inválido"})
                        return
                    ponte._registrar_resultado(dados)
                    self._json(200, {})

        try:
            self._servidor = ThreadingHTTPServer((HOST, self._porta_pedida), Atendente)
        except OSError as erro:
            raise PonteIndisponivel(
                f"não consegui abrir a ponte em {HOST}:{self._porta_pedida} ({erro}) — "
                "há outro agente_nw aberto?"
            ) from erro
        self._servidor.daemon_threads = True
        threading.Thread(target=self._servidor.serve_forever, daemon=True).start()

    def fechar(self) -> None:
        self._encerrado.set()
        if self._servidor is not None:
            self._servidor.shutdown()
            self._servidor.server_close()
            self._servidor = None

    # ---- lado do servidor (chamado pelas threads do atendente) ----------------------------------

    def _pagina(self) -> str:
        modelo = resources.files("agente_nw.ponte").joinpath("ponte.html").read_text(encoding="utf-8")
        return modelo.replace("__TOKEN__", self.token).replace("__ID_EXTENSAO__", ID_EXTENSAO)

    def _proxima_tarefa(self) -> dict[str, Any]:
        with self._trava:
            self._polls_ativos += 1
        try:
            fim = time.monotonic() + self._long_poll_s
            while not self._encerrado.is_set():
                restante = fim - time.monotonic()
                if restante <= 0:
                    break
                try:
                    tarefa = self._tarefas.get(timeout=min(0.25, restante))
                except queue.Empty:
                    continue
                with self._trava:
                    self._puxadas.add(int(tarefa["id"]))
                return tarefa
            return {}
        finally:
            with self._trava:
                self._polls_ativos -= 1
                self._ultima_atividade = time.monotonic()

    def _registrar_resultado(self, dados: dict[str, Any]) -> None:
        identificador = dados.get("id")
        if not isinstance(identificador, int):
            return
        with self._trava:
            evento = self._eventos.get(identificador)
            if evento is None:
                return
            self._resultados[identificador] = dados
        evento.set()

    # ---- lado do programa -----------------------------------------------------------------------

    def _abrir_pagina_da_ponte(self) -> None:
        if self._navegador_aberto:
            return
        self._navegador_aberto = True
        print(
            f"Ponte do navegador: {self.url}\n"
            "(se não abriu no Chrome com a extensão, cole este endereço nele e deixe a aba aberta)",
            flush=True,
        )
        if self._abrir_navegador is None:
            import webbrowser

            webbrowser.open(self.url)
        else:
            self._abrir_navegador(self.url)

    def _falhar(self, motivo: str) -> PonteIndisponivel:
        if self._falha is None:
            self._falha = motivo
            self._avisar(
                f"{motivo} Deixe aberta a aba 'agente_nw — ponte' no Chrome com a extensão "
                "instalada (agente_nw extensao testar)."
            )
        return PonteIndisponivel(motivo)

    def _aquecer_extensao(self) -> None:
        """O service worker do Chrome (manifest v3) dorme quando fica parado e a primeira mensagem que
        o acorda pode se perder. Um `ola` curto, repetido, acorda a extensão antes da primeira tarefa
        de verdade; só depois de todas as tentativas sem resposta a ponte é declarada indisponível."""
        for _ in range(_TENTATIVAS_DE_AQUECIMENTO):
            try:
                self._enviar({"acao": "ola"}, self._limite_do_aquecimento_s, definitivo=False)
            except PonteIndisponivel:
                if self._falha is not None:
                    raise
                continue
            self._aquecida = True
            return
        raise self._falhar("a extensão não respondeu a tempo.")

    def enviar(self, tarefa: dict[str, Any], tempo_limite_s: float) -> dict[str, Any]:
        """Entrega a tarefa à extensão e devolve os `dados` da resposta. Depois da primeira falha,
        as chamadas seguintes falham na hora (sem esperar o tempo limite de novo)."""
        if self._falha is not None:
            raise PonteIndisponivel(self._falha)
        if self._aquecer and not self._aquecida:
            self._aquecer_extensao()
        return self._enviar(tarefa, tempo_limite_s, definitivo=True)

    def _enviar(self, tarefa: dict[str, Any], tempo_limite_s: float, definitivo: bool) -> dict[str, Any]:
        self.iniciar()
        self._abrir_pagina_da_ponte()

        identificador = next(self._ids)
        evento = threading.Event()
        with self._trava:
            self._eventos[identificador] = evento
        self._tarefas.put({"id": identificador, "tarefa": tarefa})

        inicio = time.monotonic()
        try:
            while not evento.wait(timeout=0.25):
                decorrido = time.monotonic() - inicio
                if decorrido >= tempo_limite_s:
                    if not definitivo:
                        raise PonteIndisponivel("a extensão não respondeu a tempo.")
                    raise self._falhar("a extensão não respondeu a tempo.")
                if identificador in self._puxadas or self._polls_ativos > 0:
                    continue
                ultima = self._ultima_atividade
                if ultima is None:
                    if decorrido >= self._espera_conexao_s:
                        raise self._falhar("a página da ponte não conectou.")
                elif time.monotonic() - ultima > self._sem_contato_s:
                    raise self._falhar("a aba da ponte foi fechada.")
            with self._trava:
                resposta = self._resultados.pop(identificador)
        finally:
            with self._trava:
                self._eventos.pop(identificador, None)
                self._resultados.pop(identificador, None)
                self._puxadas.discard(identificador)

        if not resposta.get("ok"):
            raise ErroDaExtensao(str(resposta.get("erro") or "erro desconhecido na extensão"))
        dados = resposta.get("dados")
        return dados if isinstance(dados, dict) else {}
