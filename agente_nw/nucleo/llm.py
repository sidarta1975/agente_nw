from __future__ import annotations

import json
import sqlite3
import subprocess
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, Protocol, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from agente_nw.nucleo.database.queries import fila_revisao
from agente_nw.nucleo.estimativa_tokens import estimar_tokens_conservador
from agente_nw.nucleo.modelos.configuracao import Roteamento, TarefaRoteamento
from agente_nw.nucleo.modelos.proveniencia import Proveniencia
from agente_nw.nucleo.texto_integral import Parte, consolidar_vetores, processar_dividindo

EsquemaT = TypeVar("EsquemaT", bound=BaseModel)

_SEED = 42
_INTERVALOS_BACKOFF_TRANSPORTE: tuple[float, ...] = (2, 4, 8, 16)
"""Erro de conexão/timeout/HTTP contra o provedor — no caso do Ollama, servidor local,
compartilhado, que pode estar carregando ou descarregando um modelo no momento exato da
chamada. Camada separada da nova tentativa por temperatura, que é só para falha de conteúdo
(JSON inválido/geração degenerada)."""


class _GeracaoDegenerada(Exception):
    """O provedor abortou a geração (ex.: "prediction aborted, token repeat limit reached",
    quando o modelo entra num loop de repetição). É falha da tentativa, não da rede —
    tratada em ``gerar_json`` igual a JSON inválido: conta para a nova tentativa e,
    esgotada, vai para ``fila_revisao`` em vez de derrubar o chamador. Quem detecta é o
    ``_chamar`` de cada provedor, porque a forma de dizer isso é específica dele."""


class FalhaJsonInvalido(RuntimeError):
    def __init__(self, tarefa: str, fila_revisao_id: int, erro: str) -> None:
        super().__init__(
            f"tarefa '{tarefa}' falhou a validação de JSON (fila_revisao id={fila_revisao_id}): {erro}"
        )
        self.tarefa = tarefa
        self.fila_revisao_id = fila_revisao_id
        self.erro = erro


LIMITE_TOKENS_EMBEDDING = 8192
"""Janela do `bge-m3`, o modelo de embedding dos dois perfis (`bert.context_length` em `/api/show`).
Acima disso o Ollama corta a entrada do embedding em silêncio (brief 082, decisão 2.4)."""

MotivoJanela = Literal[
    "prompt_estimado_acima_da_janela", "prompt_cortado", "resposta_cortada", "embedding_acima_do_limite"
]

_DESCRICAO_MOTIVO: dict[str, str] = {
    "prompt_estimado_acima_da_janela": "prompt estimado acima da janela, recusado antes da chamada",
    "prompt_cortado": "prompt cortado pelo servidor",
    "resposta_cortada": "resposta cortada por tamanho",
    "embedding_acima_do_limite": "texto do embedding acima do limite do modelo",
}


class JanelaEstourada(Exception):
    """O que não coube na janela do modelo (brief 082): prompt acima do `num_ctx`, resposta cortada por
    `num_predict` ou texto de embedding acima do limite. Base comum dos dois erros concretos, para quem
    for tratar o estouro (o brief 088, dividindo o texto) capturar um tipo só. Nunca se responde "com o
    que coube": o resultado da chamada não é usado.

    `tokens_medidos` e `tokens_estimados` são sempre da entrada (prompt ou texto do embedding); `limite`
    é o `num_ctx` (prompt), o `num_predict` (resposta) ou `LIMITE_TOKENS_EMBEDDING`."""

    tarefa: str
    modelo: str
    motivo: MotivoJanela
    tokens_medidos: int | None
    tokens_estimados: int
    limite: int

    def _guardar_medida(
        self,
        tarefa: str,
        modelo: str,
        motivo: MotivoJanela,
        tokens_medidos: int | None,
        tokens_estimados: int,
        limite: int,
    ) -> None:
        self.tarefa = tarefa
        self.modelo = modelo
        self.motivo = motivo
        self.tokens_medidos = tokens_medidos
        self.tokens_estimados = tokens_estimados
        self.limite = limite


def _texto_do_estouro(
    motivo: MotivoJanela, tokens_medidos: int | None, tokens_estimados: int, limite: int
) -> str:
    """Sem as palavras que `fila_revisao.classe_do_erro` lê como JSON ou transporte."""
    if motivo == "resposta_cortada":
        return f"janela do modelo: {_DESCRICAO_MOTIVO[motivo]} (limite de saída={limite} tokens)"
    medida = f"medidos={tokens_medidos}" if tokens_medidos is not None else f"estimados={tokens_estimados}"
    return f"janela do modelo: {_DESCRICAO_MOTIVO[motivo]} (tokens {medida}, limite={limite})"


class FalhaJanela(FalhaJsonInvalido, JanelaEstourada):
    """Estouro de janela numa chamada de geração. Subclasse de `FalhaJsonInvalido` porque é o erro que
    todos os chamadores das 15 tarefas já tratam: o item cai no mesmo caminho de qualquer falha de LLM,
    com a mesma linha em `fila_revisao` (e o mesmo `(fila_revisao id=N)` no texto)."""

    def __init__(
        self,
        tarefa: str,
        fila_revisao_id: int,
        modelo: str,
        motivo: MotivoJanela,
        tokens_medidos: int | None,
        tokens_estimados: int,
        limite: int,
    ) -> None:
        erro = _texto_do_estouro(motivo, tokens_medidos, tokens_estimados, limite)
        super().__init__(tarefa, fila_revisao_id, erro)
        RuntimeError.__init__(self, f"tarefa '{tarefa}' recusada (fila_revisao id={fila_revisao_id}): {erro}")
        self._guardar_medida(tarefa, modelo, motivo, tokens_medidos, tokens_estimados, limite)


class FalhaJanelaEmbedding(ValueError, JanelaEstourada):
    """Texto de embedding acima do limite do modelo. Subclasse de `ValueError`, o que `embeddar` já
    levantava para vetor inválido: os chamadores tratam igual. Embedding não tem `fila_revisao`."""

    def __init__(self, modelo: str, tokens_medidos: int | None, tokens_estimados: int, limite: int) -> None:
        motivo: MotivoJanela = "embedding_acima_do_limite"
        super().__init__(_texto_do_estouro(motivo, tokens_medidos, tokens_estimados, limite))
        self._guardar_medida("embeddings", modelo, motivo, tokens_medidos, tokens_estimados, limite)


@dataclass(frozen=True)
class _RespostaBruta:
    """O que cada provedor devolve de uma chamada: o texto e as medidas de janela que ele informa.
    `tokens_prompt`: tokens do prompt realmente lidos (`prompt_eval_count` do Ollama), quando há.
    `parada`: o motivo de parada cru do provedor; `cortada`: se esse motivo é "parou por tamanho"."""

    texto: str
    tokens_prompt: int | None = None
    parada: str | None = None
    cortada: bool = False


def _registrar_estouro(
    caminho_log: Path,
    tarefa: str,
    modelo: str,
    perfil: str,
    motivo: MotivoJanela,
    tokens_medidos: int | None,
    tokens_estimados: int,
    num_ctx: int,
    num_predict: int | None = None,
    parada: str | None = None,
) -> None:
    """Uma linha `"janela": true` no `chamadas_llm.jsonl`, no padrão do aviso do `porteiro` (brief 077):
    falha de escrita nunca derruba quem chamou."""
    try:
        caminho_log.parent.mkdir(parents=True, exist_ok=True)
        linha = json.dumps(
            {
                "janela": True,
                "tarefa": tarefa,
                "modelo": modelo,
                "perfil": perfil,
                "quando": datetime.now(UTC).isoformat(),
                "motivo": motivo,
                "tokens_medidos": tokens_medidos,
                "tokens_estimados": tokens_estimados,
                "num_ctx": num_ctx,
                "num_predict": num_predict,
                "parada": parada,
            },
            ensure_ascii=False,
        )
        with caminho_log.open("a", encoding="utf-8") as arquivo:
            arquivo.write(linha + "\n")
    except Exception:
        pass


class _ClienteLLMBase(ABC):
    """Orquestração de `gerar_json` que não depende de provedor (brief 074): nova tentativa por
    temperatura, backoff de transporte, validação do JSON contra o esquema Pydantic, log da chamada
    e `fila_revisao` quando tudo se esgota. Cada provedor implementa só `_chamar`.

    Não é contrato público: os módulos do produto recebem um cliente concreto (`ClienteOllama` e,
    a partir do brief 075, os clientes de API) e usam `gerar_json`/`proveniencia`/`embeddar`."""

    def __init__(
        self,
        conexao_bd: sqlite3.Connection,
        roteamento: Roteamento,
        caminho_log: Path,
    ) -> None:
        self._conexao = conexao_bd
        self._roteamento = roteamento
        self._caminho_log = caminho_log

    @abstractmethod
    def _chamar(
        self,
        tarefa: TarefaRoteamento,
        prompt: str,
        temperature: float,
        imagens: list[str] | None,
        esquema: type[BaseModel],
    ) -> _RespostaBruta:
        """Uma chamada ao provedor, sem nova tentativa: devolve o texto bruto da resposta e as medidas de
        janela que o provedor informa (brief 082). Levanta `_GeracaoDegenerada` quando o provedor avisa
        que a geração degenerou, e
        `httpx.HTTPStatusError`/`httpx.RequestError` em falha de transporte — o backoff e a nova
        tentativa por temperatura ficam aqui na base, iguais para todo provedor.

        `esquema` está na assinatura para os clientes de API forçarem o formato de saída com
        `esquema.model_json_schema()`; o Ollama recebe o formato pelo `format` da tarefa e o ignora."""

    def _janela_de_entrada(self, tarefa: TarefaRoteamento) -> int | None:
        """Janela contra a qual o prompt é conferido, antes (estimativa) e depois (medida) da chamada.
        `None` na base: os provedores de API não cortam o prompt em silêncio (recusam com erro HTTP) e o
        `num_ctx` da tarefa é a janela do modelo local. O `ClienteOllama` devolve o `num_ctx`."""
        return None

    def num_ctx(self, tarefa_nome: str) -> int:
        """`num_ctx` declarado da tarefa no perfil ativo: de onde quem divide o texto em partes tira o
        orçamento de cada parte (brief 088, `texto_integral.orcamento_do_texto`)."""
        return self._tarefa(tarefa_nome).num_ctx

    def proveniencia(self, tarefa_nome: str, versao_prompt: str | None = None) -> Proveniencia:
        """Perfil ativo, modelo da tarefa e versão do prompt — o que `gerar_json` usa e registra no log,
        para quem grava o resultado da geração (brief 066)."""
        return Proveniencia(
            modelo=self._tarefa(tarefa_nome).modelo,
            perfil=self._roteamento.perfil_ativo,
            prompt_versao=versao_prompt,
        )

    def _registrar_log_chamada(
        self,
        tarefa_nome: str,
        tentativas_usadas: int,
        sucesso: bool,
        falhas_transporte: int,
        proveniencia: Proveniencia,
        inicio: float,
    ) -> None:
        try:
            self._caminho_log.parent.mkdir(parents=True, exist_ok=True)
            linha = json.dumps(
                {
                    "tarefa": tarefa_nome,
                    "tentativas_usadas": tentativas_usadas,
                    "sucesso": sucesso,
                    "falhas_transporte": falhas_transporte,
                    "quando": datetime.now(UTC).isoformat(),
                    "perfil": proveniencia.perfil,
                    "modelo": proveniencia.modelo,
                    "versao_prompt": proveniencia.prompt_versao,
                    "latencia_ms": round((time.monotonic() - inicio) * 1000),
                },
                ensure_ascii=False,
            )
            with self._caminho_log.open("a", encoding="utf-8") as arquivo:
                arquivo.write(linha + "\n")
        except Exception:
            pass

    def _tarefa(self, nome: str) -> TarefaRoteamento:
        perfil = self._roteamento.perfis[self._roteamento.perfil_ativo]
        if nome not in perfil.tarefas:
            raise KeyError(
                f"tarefa '{nome}' não está declarada no perfil '{self._roteamento.perfil_ativo}' "
                "de config/llm_routing.yaml"
            )
        return perfil.tarefas[nome]

    def _chamar_com_backoff(
        self,
        tarefa: TarefaRoteamento,
        prompt: str,
        temperature: float,
        imagens: list[str] | None,
        esquema: type[BaseModel],
    ) -> tuple[_RespostaBruta, int]:
        """Nova tentativa só para erro de transporte (conexão, timeout, HTTP) — não para geração
        degenerada, que é falha de tentativa e segue para a nova tentativa por temperatura."""
        ultimo_erro: httpx.HTTPStatusError | httpx.RequestError | None = None
        falhas = 0
        for espera in (0.0, *_INTERVALOS_BACKOFF_TRANSPORTE):
            if espera:
                time.sleep(espera)
            try:
                return self._chamar(tarefa, prompt, temperature, imagens, esquema), falhas
            except _GeracaoDegenerada:
                raise
            except (httpx.HTTPStatusError, httpx.RequestError) as erro:
                falhas += 1
                ultimo_erro = erro
        assert ultimo_erro is not None
        raise ultimo_erro

    def _ir_para_fila_revisao(self, tarefa_nome: str, prompt: str, erro: str) -> FalhaJsonInvalido:
        agora = datetime.now(UTC).isoformat()
        fila_id = fila_revisao.inserir(self._conexao, tarefa_nome, prompt, erro, agora)
        self._conexao.commit()
        return FalhaJsonInvalido(tarefa_nome, fila_id, erro)

    def _recusar_por_janela(
        self,
        tarefa_nome: str,
        tarefa: TarefaRoteamento,
        proveniencia: Proveniencia,
        prompt: str,
        motivo: MotivoJanela,
        tokens_medidos: int | None,
        tokens_estimados: int,
        parada: str | None = None,
    ) -> FalhaJanela:
        """Registra o estouro, põe o item na `fila_revisao` e devolve o erro de janela (2.3)."""
        limite = tarefa.num_predict if motivo == "resposta_cortada" else tarefa.num_ctx
        _registrar_estouro(
            self._caminho_log,
            tarefa_nome,
            proveniencia.modelo,
            proveniencia.perfil,
            motivo,
            tokens_medidos,
            tokens_estimados,
            tarefa.num_ctx,
            tarefa.num_predict if motivo == "resposta_cortada" else None,
            parada,
        )
        erro = _texto_do_estouro(motivo, tokens_medidos, tokens_estimados, limite)
        fila_id = fila_revisao.inserir(
            self._conexao, tarefa_nome, prompt, erro, datetime.now(UTC).isoformat()
        )
        self._conexao.commit()
        return FalhaJanela(
            tarefa_nome, fila_id, proveniencia.modelo, motivo, tokens_medidos, tokens_estimados, limite
        )

    def gerar_json(
        self,
        tarefa_nome: str,
        prompt: str,
        esquema: type[EsquemaT],
        imagens: list[str] | None = None,
        versao_prompt: str | None = None,
    ) -> EsquemaT:
        """`imagens`: imagens em base64 para modelos com visão (tarefa `descrever_imagem`).
        `versao_prompt`: `VERSAO` do módulo de prompt (brief 066); só vai para o log. A latência
        registrada é a da chamada inteira, com novas tentativas e esperas do backoff.

        Janela (brief 082): prompt estimado acima do `num_ctx` é recusado sem chamar o provedor; prompt
        que o provedor diz ter cortado, ou resposta que parou por tamanho, é recusado sem nova tentativa
        (o mesmo prompt corta de novo). Nos três casos, `FalhaJanela` com o item na `fila_revisao`."""
        inicio = time.monotonic()
        tarefa = self._tarefa(tarefa_nome)
        proveniencia = self.proveniencia(tarefa_nome, versao_prompt)
        nova_tentativa = self._roteamento.perfis[self._roteamento.perfil_ativo].nova_tentativa

        janela = self._janela_de_entrada(tarefa)
        estimados = estimar_tokens_conservador(prompt)
        if janela is not None and estimados > janela:
            raise self._recusar_por_janela(
                tarefa_nome, tarefa, proveniencia, prompt, "prompt_estimado_acima_da_janela", None, estimados
            )

        ultimo_erro = ""
        falhas_transporte_total = 0
        tentativas = (tarefa.temperature, nova_tentativa.temperature)
        for indice, temperatura in enumerate(tentativas, start=1):
            try:
                resposta, falhas_transporte = self._chamar_com_backoff(
                    tarefa, prompt, temperatura, imagens, esquema
                )
            except (httpx.HTTPStatusError, httpx.RequestError) as erro:
                falhas_transporte_total += len(_INTERVALOS_BACKOFF_TRANSPORTE) + 1
                self._registrar_log_chamada(
                    tarefa_nome, indice, False, falhas_transporte_total, proveniencia, inicio
                )
                raise self._ir_para_fila_revisao(tarefa_nome, prompt, str(erro)) from erro
            except _GeracaoDegenerada as erro:
                ultimo_erro = str(erro)
                continue

            falhas_transporte_total += falhas_transporte
            motivo: MotivoJanela | None = None
            if janela is not None and resposta.tokens_prompt is not None and resposta.tokens_prompt >= janela:
                motivo = "prompt_cortado"
            elif resposta.cortada:
                motivo = "resposta_cortada"
            if motivo is not None:
                self._registrar_log_chamada(
                    tarefa_nome, indice, False, falhas_transporte_total, proveniencia, inicio
                )
                raise self._recusar_por_janela(
                    tarefa_nome,
                    tarefa,
                    proveniencia,
                    prompt,
                    motivo,
                    resposta.tokens_prompt,
                    estimados,
                    resposta.parada,
                )
            try:
                bruto = json.loads(resposta.texto)
                resultado = esquema.model_validate(bruto)
                self._registrar_log_chamada(
                    tarefa_nome, indice, True, falhas_transporte_total, proveniencia, inicio
                )
                return resultado
            except (json.JSONDecodeError, ValidationError) as erro:
                ultimo_erro = str(erro)

        self._registrar_log_chamada(
            tarefa_nome, len(tentativas), False, falhas_transporte_total, proveniencia, inicio
        )
        raise self._ir_para_fila_revisao(tarefa_nome, prompt, ultimo_erro)


_PORTEIRO_PYTHON = "/opt/homebrew/bin/python3"
_PORTEIRO_BIN = "/Users/sidarta48/github/porteiro_local/bin/porteiro"
"""Caminho completo, com o Python na frente, como o `INTEGRACAO.md §4.1` do `porteiro` exige: um
LaunchAgent ou um ambiente virtual pode não ver `~/.local/bin` nem escolher um Python ≥ 3.11."""

_PORTEIRO_TIMEOUT_S = 30.0
_PORTEIRO_ESPERA_S = 60.0
_PORTEIRO_CONSULTAS_LOTE = 16
"""16 consultas e 15 esperas de 60 s entre elas, os "até 15 min" do `INTEGRACAO.md §6`, com a
primeira consulta imediata — o mesmo número do exemplo do §9 daquele documento."""

_AVISO_MEMORIA_CHEIA = "rodou com memória cheia segundo o porteiro"
_AVISO_SEM_SERVIDOR = "servidor Ollama da porta consultada não respondeu"
_AVISO_PORTEIRO_INDISPONIVEL = "porteiro indisponível ou com erro, seguiu como se não existisse"
_AVISOS_PORTEIRO: dict[int, str] = {
    1: _AVISO_MEMORIA_CHEIA,
    2: _AVISO_SEM_SERVIDOR,
    3: _AVISO_PORTEIRO_INDISPONIVEL,
}

ModoPorteiro = Literal["lote", "interativo"]


def _consultar_porteiro(modelo: str, porta: int) -> dict[str, object] | None:
    """Uma consulta ao `porteiro` (`cabe`, nunca `status`), ou `None` quando ele não está
    disponível: programa ausente, mais de 30 s, JSON ilegível ou JSON sem `codigo_de_saida`.
    `None` vale o mesmo que o código `3` — seguir como se o `porteiro` não existisse. Nunca
    levanta: a falta do `porteiro` não é erro deste projeto (`INTEGRACAO.md §6` e §8)."""
    try:
        processo = subprocess.run(
            [_PORTEIRO_PYTHON, _PORTEIRO_BIN, "cabe", modelo, "--porta", str(porta), "--json"],
            capture_output=True,
            text=True,
            timeout=_PORTEIRO_TIMEOUT_S,
        )
        resposta = json.loads(processo.stdout)
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return None
    if not isinstance(resposta, dict) or "codigo_de_saida" not in resposta:
        return None
    return resposta


class ClienteOllama(_ClienteLLMBase):
    def __init__(
        self,
        http_client: httpx.Client,
        conexao_bd: sqlite3.Connection,
        roteamento: Roteamento,
        ollama_url: str,
        caminho_log: Path,
        modo_porteiro: ModoPorteiro = "lote",
    ) -> None:
        """`modo_porteiro`: `"lote"` (padrão, todo comando da CLI) espera até 15 min quando o
        `porteiro` diz que o modelo não cabe; `"interativo"` (o console, com uma pessoa esperando)
        consulta uma vez e nunca espera. Em nenhum dos dois o `porteiro` impede a chamada."""
        super().__init__(conexao_bd, roteamento, caminho_log)
        self._http = http_client
        self._ollama_url = ollama_url
        self._modo_porteiro = modo_porteiro
        self._modelos_verificados_porteiro: set[str] = set()
        """Uma consulta por modelo, por cliente — nunca dentro de um laço, item por item
        (`INTEGRACAO.md §8`). Cada processo de lote cria o seu cliente, então o conjunto vazio
        equivale a "uma vez no início do lote"."""

    def _janela_de_entrada(self, tarefa: TarefaRoteamento) -> int | None:
        """O `num_ctx` da tarefa: acima dele o Ollama corta o prompt em silêncio (armadilha 1)."""
        return tarefa.num_ctx

    @property
    def modelo_embedding(self) -> str:
        """Modelo de embedding do perfil ativo — gravado com cada centróide e conferido na leitura
        (brief 066): vetor de outro modelo é tratado como ausente."""
        return self._roteamento.perfis[self._roteamento.perfil_ativo].embeddings.modelo

    def _registrar_aviso_porteiro(self, modelo: str, resposta: dict[str, object] | None) -> None:
        """Uma linha no mesmo `chamadas_llm.jsonl` das chamadas, só quando há o que avisar. Mesmo
        padrão de `_registrar_log_chamada`: falha de escrita nunca derruba a chamada de LLM."""
        codigo = resposta.get("codigo_de_saida") if resposta is not None else None
        try:
            self._caminho_log.parent.mkdir(parents=True, exist_ok=True)
            linha = json.dumps(
                {
                    "porteiro": True,
                    "modelo": modelo,
                    "porta": httpx.URL(self._ollama_url).port,
                    "quando": datetime.now(UTC).isoformat(),
                    "codigo_de_saida": codigo,
                    "razao": resposta.get("razao") if resposta is not None else None,
                    "aviso": _AVISOS_PORTEIRO.get(codigo if isinstance(codigo, int) else 3)
                    or _AVISO_PORTEIRO_INDISPONIVEL,
                },
                ensure_ascii=False,
            )
            with self._caminho_log.open("a", encoding="utf-8") as arquivo:
                arquivo.write(linha + "\n")
        except Exception:
            pass

    def _verificar_porteiro_antes_de_carregar(self, modelo: str) -> None:
        """Pergunta ao `porteiro` se este modelo cabe na memória da porta deste projeto, uma vez por
        modelo. Nunca impede a chamada nem levanta: no modo `lote`, o código `1` adia por até 15
        min e depois roda assim mesmo; qualquer outro código roda na hora. O que não for `0` vira
        aviso no log. O modelo e a porta nunca mudam por causa da resposta (`INTEGRACAO.md §8`)."""
        if modelo in self._modelos_verificados_porteiro:
            return
        self._modelos_verificados_porteiro.add(modelo)

        porta = httpx.URL(self._ollama_url).port
        if porta is None:
            return

        consultas = _PORTEIRO_CONSULTAS_LOTE if self._modo_porteiro == "lote" else 1
        resposta: dict[str, object] | None = None
        for restantes in range(consultas, 0, -1):
            resposta = _consultar_porteiro(modelo, porta)
            if resposta is None:
                break
            codigo = resposta.get("codigo_de_saida")
            if codigo == 0:
                return
            if codigo != 1:  # 2 e 3 rodam na hora, com aviso; só o 1 manda esperar
                break
            if restantes > 1:
                time.sleep(_PORTEIRO_ESPERA_S)

        self._registrar_aviso_porteiro(modelo, resposta)

    def _chamar(
        self,
        tarefa: TarefaRoteamento,
        prompt: str,
        temperature: float,
        imagens: list[str] | None,
        esquema: type[BaseModel],
    ) -> _RespostaBruta:
        """`esquema` não é usado: o formato de saída do Ollama vem do `format` da tarefa
        (a string `"json"` do YAML), não de um esquema enviado no payload. As medidas de janela são
        `prompt_eval_count` (tokens do prompt lidos) e `done_reason` (`"length"`: parou no
        `num_predict`), conferidos numa resposta real do Ollama 0.34 no brief 082."""
        corpo: dict[str, object] = {
            "model": tarefa.modelo,
            "prompt": prompt,
            "format": tarefa.format,
            "stream": False,
            "options": {
                "num_ctx": tarefa.num_ctx,
                "temperature": temperature,
                "seed": _SEED,
                "num_predict": tarefa.num_predict,
            },
        }
        if imagens:
            corpo["images"] = imagens
        if self._roteamento.perfis[self._roteamento.perfil_ativo].enviar_think:
            corpo["think"] = tarefa.think
        self._verificar_porteiro_antes_de_carregar(tarefa.modelo)
        resposta = self._http.post(f"{self._ollama_url}/api/generate", json=corpo)
        if resposta.status_code == 500:
            try:
                mensagem_erro = str(resposta.json().get("error", ""))
            except Exception:
                mensagem_erro = ""
            if "token repeat limit" in mensagem_erro:
                raise _GeracaoDegenerada(mensagem_erro)
        resposta.raise_for_status()
        dados: dict[str, object] = resposta.json()
        texto = dados["response"]
        assert isinstance(texto, str)
        parada = dados.get("done_reason")
        return _RespostaBruta(
            texto=texto,
            tokens_prompt=_inteiro_ou_none(dados.get("prompt_eval_count")),
            parada=parada if isinstance(parada, str) else None,
            cortada=parada == "length",
        )

    def _recusar_embedding(
        self, modelo: str, tokens_medidos: int | None, tokens_estimados: int
    ) -> FalhaJanelaEmbedding:
        _registrar_estouro(
            self._caminho_log,
            "embeddings",
            modelo,
            self._roteamento.perfil_ativo,
            "embedding_acima_do_limite",
            tokens_medidos,
            tokens_estimados,
            LIMITE_TOKENS_EMBEDDING,
        )
        return FalhaJanelaEmbedding(modelo, tokens_medidos, tokens_estimados, LIMITE_TOKENS_EMBEDDING)

    def embeddar(self, textos: list[str]) -> list[list[float]]:
        """Cada texto é conferido contra `LIMITE_TOKENS_EMBEDDING` antes (estimativa) e, quando é um texto
        só, depois (`prompt_eval_count`, que no `/api/embed` é a soma de todos os textos do pedido):
        acima do limite, `FalhaJanelaEmbedding` com registro, nunca um vetor do texto cortado."""
        perfil = self._roteamento.perfis[self._roteamento.perfil_ativo]
        modelo = perfil.embeddings.modelo
        for texto in textos:
            estimados = estimar_tokens_conservador(texto)
            if estimados > LIMITE_TOKENS_EMBEDDING:
                raise self._recusar_embedding(modelo, None, estimados)
        corpo = {"model": modelo, "input": textos}
        self._verificar_porteiro_antes_de_carregar(modelo)
        resposta = self._http.post(f"{self._ollama_url}/api/embed", json=corpo)
        resposta.raise_for_status()
        dados: dict[str, object] = resposta.json()
        medidos = _inteiro_ou_none(dados.get("prompt_eval_count"))
        if len(textos) == 1 and medidos is not None and medidos >= LIMITE_TOKENS_EMBEDDING:
            raise self._recusar_embedding(modelo, medidos, estimar_tokens_conservador(textos[0]))
        vetores_brutos = dados["embeddings"]
        assert isinstance(vetores_brutos, list)
        vetores: list[list[float]] = [[float(valor) for valor in vetor] for vetor in vetores_brutos]

        for vetor in vetores:
            if len(vetor) != 1024:
                raise ValueError(f"embedding com {len(vetor)} posições, esperado 1024")

        return vetores


def _inteiro_ou_none(valor: object) -> int | None:
    return valor if isinstance(valor, int) and not isinstance(valor, bool) else None


_MEDIA_TYPE_IMAGEM = "image/jpeg"
"""As imagens publicadas chegam à tarefa `descrever_imagem` só como base64: `ImagemCapturada.mime`
guarda o `content-type` real que a extensão leu, mas `coleta/capturas/imagens.py` passa apenas
`dados_base64` para `gerar_json`. Sem o mime real chegando até aqui, os clientes de API assumem
`image/jpeg` (brief 075, item 3.2). O Ollama não precisa disso: aceita a base64 sem rótulo."""


class _ClienteApiBase(_ClienteLLMBase):
    """O que os três clientes de API têm igual (brief 075): a chave, o modelo único do provedor e os
    embeddings por composição com o `ClienteOllama` local. Cada provedor implementa só `_chamar`.

    Fica numa base privada em vez de repetido três vezes pelo mesmo motivo do brief 074: a
    composição do item 3.5 e a proveniência são idênticas nos três, e código igual copiado é o que
    aquele brief existiu para acabar."""

    def __init__(
        self,
        http_client: httpx.Client,
        conexao_bd: sqlite3.Connection,
        roteamento: Roteamento,
        chave: str,
        modelo: str,
        caminho_log: Path,
        cliente_embeddings: ClienteOllama,
    ) -> None:
        super().__init__(conexao_bd, roteamento, caminho_log)
        self._http = http_client
        self._chave = chave
        self._modelo = modelo
        self._cliente_embeddings = cliente_embeddings

    def proveniencia(self, tarefa_nome: str, versao_prompt: str | None = None) -> Proveniencia:
        """O modelo registrado é o do provedor de API, não o do `llm_routing.yaml` — é por este
        campo, no `chamadas_llm.jsonl`, que se confere qual provedor atendeu a chamada."""
        return Proveniencia(
            modelo=self._modelo,
            perfil=self._roteamento.perfil_ativo,
            prompt_versao=versao_prompt,
        )

    @property
    def modelo_embedding(self) -> str:
        """Repasse: embeddings são sempre do Ollama local, qualquer que seja o provedor de geração
        (brief 075, item 3.5) — a Anthropic não tem endpoint de embedding e trocar de modelo
        invalidaria todo centróide já gravado (brief 066)."""
        return self._cliente_embeddings.modelo_embedding

    def embeddar(self, textos: list[str]) -> list[list[float]]:
        """Repasse ao `ClienteOllama` injetado; nunca uma reimplementação (brief 075, item 3.5)."""
        return self._cliente_embeddings.embeddar(textos)


class ClienteAnthropic(_ClienteApiBase):
    """`POST /v1/messages`. O esquema é forçado por uma tool única, obrigatória por `tool_choice`:
    a resposta vem no bloco `tool_use`, já como dict conferido contra o `input_schema`."""

    _URL = "https://api.anthropic.com/v1/messages"
    _VERSAO_API = "2023-06-01"
    _NOME_TOOL = "responder"
    _PARADAS_POR_TAMANHO = frozenset({"max_tokens", "model_context_window_exceeded"})
    """`stop_reason` de resposta cortada: no `max_tokens` (= `num_predict`) ou na janela do modelo."""

    def _chamar(
        self,
        tarefa: TarefaRoteamento,
        prompt: str,
        temperature: float,
        imagens: list[str] | None,
        esquema: type[BaseModel],
    ) -> _RespostaBruta:
        conteudo: list[dict[str, object]] = [
            {
                "type": "image",
                "source": {"type": "base64", "media_type": _MEDIA_TYPE_IMAGEM, "data": imagem},
            }
            for imagem in imagens or []
        ]
        conteudo.append({"type": "text", "text": prompt})
        corpo: dict[str, object] = {
            "model": self._modelo,
            "max_tokens": tarefa.num_predict,
            "temperature": temperature,
            "tools": [
                {
                    "name": self._NOME_TOOL,
                    "description": "Devolve a resposta da tarefa no formato pedido.",
                    "input_schema": esquema.model_json_schema(),
                }
            ],
            "tool_choice": {"type": "tool", "name": self._NOME_TOOL},
            "messages": [{"role": "user", "content": conteudo}],
        }
        resposta = self._http.post(
            self._URL,
            json=corpo,
            headers={
                "x-api-key": self._chave,
                "anthropic-version": self._VERSAO_API,
                "content-type": "application/json",
            },
        )
        resposta.raise_for_status()
        dados = resposta.json()
        parada = dados.get("stop_reason") if isinstance(dados, dict) else None
        return _RespostaBruta(
            texto=_texto_da_resposta_anthropic(dados),
            parada=parada if isinstance(parada, str) else None,
            cortada=parada in self._PARADAS_POR_TAMANHO,
        )


class ClienteGemini(_ClienteApiBase):
    """`POST /v1beta/models/{modelo}:generateContent`. O esquema é forçado por
    `generationConfig.response_schema`, com `response_mime_type: application/json`."""

    _URL_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

    def _chamar(
        self,
        tarefa: TarefaRoteamento,
        prompt: str,
        temperature: float,
        imagens: list[str] | None,
        esquema: type[BaseModel],
    ) -> _RespostaBruta:
        partes: list[dict[str, object]] = [
            {"inlineData": {"mimeType": _MEDIA_TYPE_IMAGEM, "data": imagem}} for imagem in imagens or []
        ]
        partes.append({"text": prompt})
        corpo: dict[str, object] = {
            "contents": [{"role": "user", "parts": partes}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": tarefa.num_predict,
                "response_mime_type": "application/json",
                "response_schema": esquema.model_json_schema(),
            },
        }
        resposta = self._http.post(
            f"{self._URL_BASE}/{self._modelo}:generateContent",
            json=corpo,
            # A chave vai no header, nunca em `?key=`: `str(httpx.HTTPStatusError)` carrega a URL e
            # `_ir_para_fila_revisao` grava esse texto no banco — chave na URL viraria chave gravada.
            headers={"x-goog-api-key": self._chave, "content-type": "application/json"},
        )
        resposta.raise_for_status()
        dados = resposta.json()
        parada = _parada_gemini(dados)
        return _RespostaBruta(
            texto=_texto_da_resposta_gemini(dados), parada=parada, cortada=parada == "MAX_TOKENS"
        )


class ClienteOpenAI(_ClienteApiBase):
    """`POST /v1/chat/completions`. O esquema é forçado por
    `response_format: {"type": "json_schema", ...}`; a resposta já vem como string JSON."""

    _URL = "https://api.openai.com/v1/chat/completions"

    def _chamar(
        self,
        tarefa: TarefaRoteamento,
        prompt: str,
        temperature: float,
        imagens: list[str] | None,
        esquema: type[BaseModel],
    ) -> _RespostaBruta:
        conteudo: list[dict[str, object]] = [{"type": "text", "text": prompt}]
        conteudo.extend(
            {
                "type": "image_url",
                "image_url": {"url": f"data:{_MEDIA_TYPE_IMAGEM};base64,{imagem}"},
            }
            for imagem in imagens or []
        )
        corpo: dict[str, object] = {
            "model": self._modelo,
            "max_tokens": tarefa.num_predict,
            "temperature": temperature,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": esquema.__name__,
                    "schema": esquema.model_json_schema(),
                    "strict": True,
                },
            },
            "messages": [{"role": "user", "content": conteudo}],
        }
        resposta = self._http.post(
            self._URL,
            json=corpo,
            headers={
                "Authorization": f"Bearer {self._chave}",
                "content-type": "application/json",
            },
        )
        resposta.raise_for_status()
        dados = resposta.json()
        parada = _parada_openai(dados)
        return _RespostaBruta(
            texto=_texto_da_resposta_openai(dados), parada=parada, cortada=parada == "length"
        )


def _texto_da_resposta_anthropic(dados: object) -> str:
    """O bloco `tool_use` reserializado para texto, para a base fazer o mesmo `json.loads` que faz
    com o Ollama. Sem bloco `tool_use`, devolve o texto que vier (ou vazio): resposta 200 sem o que
    se pediu é falha de **conteúdo**, e quem trata é `gerar_json` — nova tentativa por temperatura
    e, esgotada, `fila_revisao`. Nenhuma exceção nova escapa daqui (armadilha do brief 067)."""
    blocos = dados.get("content", []) if isinstance(dados, dict) else []
    if not isinstance(blocos, list):
        return ""
    for bloco in blocos:
        if isinstance(bloco, dict) and bloco.get("type") == "tool_use":
            return json.dumps(bloco.get("input", {}), ensure_ascii=False)
    textos = [
        str(bloco.get("text", ""))
        for bloco in blocos
        if isinstance(bloco, dict) and bloco.get("type") == "text"
    ]
    return "".join(textos)


def _texto_da_resposta_gemini(dados: object) -> str:
    """`candidates[0].content.parts[*].text`. Resposta fora dessa forma devolve vazio, que a base
    trata como conteúdo inválido — ver `_texto_da_resposta_anthropic`."""
    if not isinstance(dados, dict):
        return ""
    candidatos = dados.get("candidates")
    if not isinstance(candidatos, list) or not candidatos:
        return ""
    primeiro = candidatos[0]
    conteudo = primeiro.get("content") if isinstance(primeiro, dict) else None
    partes = conteudo.get("parts") if isinstance(conteudo, dict) else None
    if not isinstance(partes, list):
        return ""
    return "".join(str(parte.get("text", "")) for parte in partes if isinstance(parte, dict))


def _texto_da_resposta_openai(dados: object) -> str:
    """`choices[0].message.content`. Resposta fora dessa forma devolve vazio, que a base trata como
    conteúdo inválido — ver `_texto_da_resposta_anthropic`."""
    if not isinstance(dados, dict):
        return ""
    escolhas = dados.get("choices")
    if not isinstance(escolhas, list) or not escolhas:
        return ""
    primeira = escolhas[0]
    mensagem = primeira.get("message") if isinstance(primeira, dict) else None
    if not isinstance(mensagem, dict):
        return ""
    conteudo = mensagem.get("content")
    return conteudo if isinstance(conteudo, str) else ""


def _primeiro_da_lista(dados: object, chave: str) -> dict[str, object] | None:
    lista = dados.get(chave) if isinstance(dados, dict) else None
    if not isinstance(lista, list) or not lista or not isinstance(lista[0], dict):
        return None
    return lista[0]


def _parada_gemini(dados: object) -> str | None:
    """`candidates[0].finishReason` (`"MAX_TOKENS"`: parou no `maxOutputTokens`)."""
    candidato = _primeiro_da_lista(dados, "candidates")
    parada = candidato.get("finishReason") if candidato is not None else None
    return parada if isinstance(parada, str) else None


def _parada_openai(dados: object) -> str | None:
    """`choices[0].finish_reason` (`"length"`: parou no `max_tokens`)."""
    escolha = _primeiro_da_lista(dados, "choices")
    parada = escolha.get("finish_reason") if escolha is not None else None
    return parada if isinstance(parada, str) else None


class _Embeddador(Protocol):
    def embeddar(self, textos: list[str]) -> list[list[float]]: ...


def embeddar_em_partes(cliente: _Embeddador, texto: str) -> list[float]:
    """Vetor de um texto de qualquer tamanho, sem cortar nada (brief 088).

    Regra de consolidação: o texto é dividido por `texto_integral.dividir` com orçamento de
    `LIMITE_TOKENS_EMBEDDING`; cada parte é embeddada numa chamada própria (assim a medida do servidor
    confere cada parte, brief 082); o vetor é a **média dos vetores das partes ponderada pelo número de
    caracteres de cada parte, normalizada**. Texto que cabe vai inteiro numa chamada só e volta o vetor
    dela, sem mudança nenhuma. **Falha numa parte invalida o vetor**: a exceção sobe e nenhum vetor
    parcial é devolvido. Se o servidor recusar uma parte por tamanho (`FalhaJanelaEmbedding`), o
    orçamento cai à metade, até 4 vezes (`texto_integral.processar_dividindo`)."""

    def vetores_das_partes(partes: list[Parte]) -> list[list[float]]:
        return [cliente.embeddar([parte.texto])[0] for parte in partes]

    vetores, partes = processar_dividindo(
        texto, LIMITE_TOKENS_EMBEDDING, vetores_das_partes, FalhaJanelaEmbedding
    )
    if len(partes) == 1:
        return vetores[0]
    return consolidar_vetores(vetores, [len(parte.texto) for parte in partes])
