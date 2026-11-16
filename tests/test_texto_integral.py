"""Teste de aceite do brief 088: o texto que não cabe numa chamada é dividido em partes que cobrem tudo,
cada parte é processada e o resultado é consolidado por uma regra escrita para cada uso.

Clientes de LLM e de embedding falsos, banco isolado em `tmp_path`: nada aqui chama o Ollama."""

from __future__ import annotations

import hashlib
import math
import random
import sqlite3
from pathlib import Path
from typing import Any, TypeVar

import pytest
from pydantic import BaseModel

from agente_nw.coleta.capturas import extrator as extrator_captura
from agente_nw.coleta.capturas.extrator import RespostaCapturaRedeSocial
from agente_nw.nucleo import texto_integral
from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import fila_extracao, fila_revisao, perfis
from agente_nw.nucleo.estimativa_tokens import estimar_tokens_conservador
from agente_nw.nucleo.llm import (
    LIMITE_TOKENS_EMBEDDING,
    FalhaJanela,
    FalhaJanelaEmbedding,
    FalhaJsonInvalido,
    embeddar_em_partes,
)
from agente_nw.nucleo.modelos.extracao import RespostaExtracaoTexto
from agente_nw.nucleo.prompts import extrair_captura_rede_social, extrair_de_texto
from agente_nw.nucleo.prompts.seguranca import MARCADOR_FIM, MARCADOR_INICIO
from agente_nw.nucleo.texto_integral import SOBREPOSICAO, dividir, reconstruir
from agente_nw.perfil import extrator
from tests.llm_falso import ProvenienciaFalsa

AGORA = "2026-11-16T00:00:00+00:00"
NUM_CTX = 4096

_EsquemaT = TypeVar("_EsquemaT", bound=BaseModel)


# --- textos de teste -----------------------------------------------------------------------------------


def _texto_longo(tamanho: int, semente: int = 88) -> str:
    """Texto determinístico com parágrafos, linhas, frases, acento e emoji, cortado em `tamanho`."""
    gerador = random.Random(semente)
    palavras = ["reunião", "contrato", "viagem", "Recife", "café", "😀", "projeto", "família", "obra", "x"]
    blocos: list[str] = []
    total = 0
    while total < tamanho:
        frase = " ".join(gerador.choice(palavras) for _ in range(gerador.randint(3, 18)))
        separador = gerador.choice([". ", "! ", "? ", "\n", "\n\n", " "])
        blocos.append(frase + separador)
        total += len(blocos[-1])
    return "".join(blocos)[:tamanho]


TEXTOS_DE_COBERTURA = {
    "vazio": "",
    "um caractere": "a",
    "um parágrafo gigante": "palavra comprida de um parágrafo só " * 4000,
    "sem espaços": "x" * 50_000,
    "emoji": "😀👩‍👩‍👧🇧🇷 olá " * 6000,
    "34.195 caracteres": _texto_longo(34_195),
}


def _cercado(prompt: str) -> str:
    """O que o prompt traz entre os marcadores do dado externo."""
    return prompt.split(MARCADOR_INICIO + "\n", 1)[1].rsplit("\n" + MARCADOR_FIM, 1)[0]


def _conteudo_da_parte(prompt: str) -> str:
    """O texto da parte, sem o aviso "parte K de N" da primeira linha do cerco."""
    cercado = _cercado(prompt)
    primeira, _, resto = cercado.partition("\n")
    return resto if primeira.startswith("[parte ") else cercado


# --- banco e clientes falsos ---------------------------------------------------------------------------


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(aberta)
    return aberta


def _item(conn: sqlite3.Connection, texto: str) -> Any:
    contato = perfis.inserir_novo_contato(conn, "Pessoa de Teste", None, None, AGORA)
    assert contato.id is not None
    item_id = fila_extracao.inserir(conn, contato.id, texto, "manual", AGORA)
    conn.commit()
    item = fila_extracao.obter(conn, item_id)
    assert item is not None
    return item


class _ClienteExtracaoFalso(ProvenienciaFalsa):
    """Responde a `extrair_de_texto` com o que `responder(prompt)` devolver; falha como o cliente real
    (linha na `fila_revisao` e `FalhaJsonInvalido`) quando devolve `None`, e recusa por tamanho
    (`FalhaJanela`, com linha na fila) o prompt acima de `recusar_acima_de` caracteres."""

    def __init__(
        self,
        conn: sqlite3.Connection,
        responder: Any = None,
        recusar_acima_de: int | None = None,
    ) -> None:
        self._conn = conn
        self._responder = responder or (lambda _prompt: RespostaExtracaoTexto())
        self._recusar_acima_de = recusar_acima_de
        self.prompts: list[str] = []
        self.aceitos: list[str] = []
        self.versoes: list[str | None] = []

    def num_ctx(self, tarefa_nome: str) -> int:
        return NUM_CTX

    def gerar_json(
        self,
        tarefa_nome: str,
        prompt: str,
        esquema: type[_EsquemaT],
        imagens: list[str] | None = None,
        versao_prompt: str | None = None,
    ) -> _EsquemaT:
        self.prompts.append(prompt)
        self.versoes.append(versao_prompt)
        if self._recusar_acima_de is not None and len(prompt) > self._recusar_acima_de:
            fila_id = fila_revisao.inserir(
                self._conn, tarefa_nome, prompt, "janela do modelo: cortado", AGORA
            )
            self._conn.commit()
            raise FalhaJanela(tarefa_nome, fila_id, "modelo-falso", "prompt_cortado", NUM_CTX, 0, NUM_CTX)
        resposta = self._responder(prompt)
        if resposta is None:
            fila_id = fila_revisao.inserir(self._conn, tarefa_nome, prompt, "1 validation error", AGORA)
            self._conn.commit()
            raise FalhaJsonInvalido(tarefa_nome, fila_id, "1 validation error")
        self.aceitos.append(prompt)
        return esquema.model_validate(resposta.model_dump())


# --- 1: cobertura byte a byte --------------------------------------------------------------------------


@pytest.mark.parametrize("nome", list(TEXTOS_DE_COBERTURA))
@pytest.mark.parametrize("orcamento", [1, 40, 700, 3000])
def test_reconstruir_as_partes_reproduz_o_original_byte_a_byte(nome: str, orcamento: int) -> None:
    texto = TEXTOS_DE_COBERTURA[nome]

    partes = dividir(texto, orcamento)

    assert reconstruir(partes).encode("utf-8") == texto.encode("utf-8")
    assert [p.indice for p in partes] == list(range(1, len(partes) + 1))
    assert all(p.total == len(partes) for p in partes)
    if len(partes) > 1:
        assert all(estimar_tokens_conservador(p.texto) <= orcamento for p in partes)


def test_texto_que_cabe_vai_inteiro_numa_parte_so() -> None:
    texto = TEXTOS_DE_COBERTURA["34.195 caracteres"]

    [parte] = dividir(texto, estimar_tokens_conservador(texto))

    assert parte.texto == texto
    assert (parte.indice, parte.total, parte.sobreposicao) == (1, 1, 0)


def test_texto_grande_e_dividido_em_varias_partes_e_prefere_fim_de_paragrafo() -> None:
    texto = "\n\n".join(f"Parágrafo {n}: " + "uma frase qualquer. " * 30 for n in range(40))

    partes = dividir(texto, 700)

    assert len(partes) > 1
    assert all(p.texto.endswith("\n\n") for p in partes[:-1])


def test_orcamento_menor_que_um_e_recusado() -> None:
    with pytest.raises(ValueError):
        dividir("texto", 0)


# --- 2: texto curto, o mesmo prompt de antes -------------------------------------------------------------

# Prompt da versão anterior ao brief 088 (commit badf676), para o texto curto abaixo: tamanho e SHA-256.
_TEXTO_CURTO = "Ana mora em Recife e gosta de surfe."
_PROMPT_ANTIGO_EXTRAIR = (2577, "7f41b4bf611403e0b9ba23e487df453accf2aff68a06c3a550d0ac13fca30b9e")
_BLOCO_CURTO = "Correu 10km no parque hoje"
_PROMPT_ANTIGO_CAPTURA = (1224, "e699e09c9dd0b9a68b7661e67b97878511943ec223774a18ba7b67b06aa82cef")


def _impressao(prompt: str) -> tuple[int, str]:
    return len(prompt), hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def test_texto_curto_produz_exatamente_o_mesmo_prompt_de_antes(conn: sqlite3.Connection) -> None:
    cliente = _ClienteExtracaoFalso(conn)

    extrator.processar_item(cliente, conn, _item(conn, _TEXTO_CURTO), extrator.ResumoProcessamento())

    [prompt] = cliente.prompts
    assert _impressao(prompt) == _PROMPT_ANTIGO_EXTRAIR
    assert cliente.versoes == [extrair_de_texto.VERSAO]


def test_bloco_curto_de_rede_social_produz_exatamente_o_mesmo_prompt_de_antes() -> None:
    cliente = _ClienteCapturaFalso(lambda _p: RespostaCapturaRedeSocial(descartar=False, conteudo="c"))

    extrator_captura.extrair(cliente, _BLOCO_CURTO, "instagram")

    [prompt] = cliente.prompts
    assert _impressao(prompt) == _PROMPT_ANTIGO_CAPTURA
    assert cliente.versoes == [extrair_captura_rede_social.VERSAO]


def test_as_duas_tarefas_sobem_de_versao() -> None:
    assert extrair_de_texto.VERSAO != "2026-11-02-1"
    assert extrair_captura_rede_social.VERSAO


# --- 3: marcador no meio e no último caractere de 300.000 caracteres ----------------------------------


def test_marcadores_do_meio_e_do_ultimo_caractere_chegam_a_um_prompt(conn: sqlite3.Connection) -> None:
    base = _texto_longo(300_000)
    meio = len(base) // 2
    texto = base[:meio] + "MARCADORDOMEIO" + base[meio:-1] + "☃"
    cliente = _ClienteExtracaoFalso(conn)

    erro = extrator.processar_item(cliente, conn, _item(conn, texto), extrator.ResumoProcessamento())

    assert erro is None
    assert len(cliente.prompts) > 1
    assert any("MARCADORDOMEIO" in prompt for prompt in cliente.prompts)
    assert any(prompt.endswith("☃\n" + MARCADOR_FIM + "\n") for prompt in cliente.prompts)
    assert reconstruir_dos_prompts(cliente.aceitos) == texto


def reconstruir_dos_prompts(prompts: list[str]) -> str:
    """O texto inteiro a partir dos prompts enviados, descontada a sobreposição entre vizinhas."""
    conteudos = [_conteudo_da_parte(prompt) for prompt in prompts]
    texto = conteudos[0]
    for conteudo in conteudos[1:]:
        sobra = next(n for n in range(min(len(texto), len(conteudo)), -1, -1) if texto.endswith(conteudo[:n]))
        texto += conteudo[sobra:]
    return texto


# --- 4: sobreposição de 500 e aviso "parte K de N" dentro do cerco -----------------------------------


def test_vizinhas_se_sobrepoem_em_500_caracteres() -> None:
    texto = TEXTOS_DE_COBERTURA["34.195 caracteres"]

    partes = dividir(texto, 1500)

    assert len(partes) > 2
    for anterior, parte in zip(partes, partes[1:], strict=False):
        assert parte.sobreposicao == SOBREPOSICAO == 500
        assert parte.texto[:500] == anterior.texto[-500:]
        assert parte.inicio == anterior.fim - 500


def test_aviso_parte_k_de_n_vai_dentro_do_cerco(conn: sqlite3.Connection) -> None:
    cliente = _ClienteExtracaoFalso(conn)

    extrator.processar_item(
        cliente, conn, _item(conn, TEXTOS_DE_COBERTURA["34.195 caracteres"]), extrator.ResumoProcessamento()
    )

    total = len(cliente.prompts)
    assert total > 1
    for numero, prompt in enumerate(cliente.prompts, start=1):
        aviso = f"[parte {numero} de {total} de um documento maior]"
        assert prompt.index(MARCADOR_INICIO) < prompt.index(aviso) < prompt.rindex(MARCADOR_FIM)
        assert _cercado(prompt).startswith(aviso + "\n")


# --- 5: média ponderada normalizada ----------------------------------------------------------------------


def _vetor(*valores: float) -> list[float]:
    return list(valores) + [0.0] * (1024 - len(valores))


def test_media_ponderada_normalizada_confere_com_calculo_manual() -> None:
    vetor = texto_integral.consolidar_vetores([_vetor(1.0, 0.0), _vetor(0.0, 1.0)], [3, 1])

    assert vetor[:2] == pytest.approx([3 / math.sqrt(10), 1 / math.sqrt(10)])
    assert math.fsum(v * v for v in vetor) == pytest.approx(1.0)


def _vetor_da_parte(texto: str) -> list[float]:
    return _vetor(1.0, 0.0) if texto.count("A") > texto.count("B") else _vetor(0.0, 1.0)


class _EmbeddadorFalso:
    """Vetor por parte: (1, 0) se a parte tem mais "A" que "B", senão (0, 1). Recusa por tamanho o
    texto acima de `recusar_acima_de` caracteres, como `FalhaJanelaEmbedding`."""

    def __init__(self, recusar_acima_de: int | None = None, falhar_em: str | None = None) -> None:
        self.recebidos: list[list[str]] = []
        self._recusar_acima_de = recusar_acima_de
        self._falhar_em = falhar_em

    def embeddar(self, textos: list[str]) -> list[list[float]]:
        self.recebidos.append(textos)
        vetores = []
        for texto in textos:
            if self._recusar_acima_de is not None and len(texto) > self._recusar_acima_de:
                raise FalhaJanelaEmbedding("bge-m3", LIMITE_TOKENS_EMBEDDING, 0, LIMITE_TOKENS_EMBEDDING)
            if self._falhar_em is not None and self._falhar_em in texto:
                raise ValueError("embedding com 3 posições, esperado 1024")
            vetores.append(_vetor_da_parte(texto))
        return vetores


def test_embeddar_em_partes_pondera_pelo_numero_de_caracteres_de_cada_parte() -> None:
    texto = "A" * 24_000 + " " + "B" * 9_000
    cliente = _EmbeddadorFalso()

    vetor = embeddar_em_partes(cliente, texto)

    partes = dividir(texto, LIMITE_TOKENS_EMBEDDING)
    assert [r[0] for r in cliente.recebidos] == [p.texto for p in partes]
    pesos = [len(p.texto) for p in partes]
    esperados = [_vetor_da_parte(p.texto) for p in partes]
    assert esperados == [_vetor(1.0, 0.0), _vetor(0.0, 1.0)]
    soma = [sum(peso * v[i] for peso, v in zip(pesos, esperados, strict=True)) for i in range(2)]
    norma = math.sqrt(soma[0] ** 2 + soma[1] ** 2)
    assert vetor[:2] == pytest.approx([soma[0] / norma, soma[1] / norma])


def test_embeddar_em_partes_texto_curto_devolve_o_vetor_de_uma_chamada_so() -> None:
    cliente = _EmbeddadorFalso()

    vetor = embeddar_em_partes(cliente, "Ana mora em Recife.")

    assert cliente.recebidos == [["Ana mora em Recife."]]
    assert vetor == _vetor(1.0, 0.0)


def test_falha_numa_parte_invalida_o_vetor() -> None:
    texto = "A" * 30_000 + " QUEBRA " + "B" * 30_000
    cliente = _EmbeddadorFalso(falhar_em="QUEBRA")

    with pytest.raises(ValueError):
        embeddar_em_partes(cliente, texto)


def test_embedding_recusado_por_tamanho_cai_a_metade_e_cobre_o_texto() -> None:
    texto = _texto_longo(60_000)
    cliente = _EmbeddadorFalso(recusar_acima_de=8_000)

    vetor = embeddar_em_partes(cliente, texto)

    aceitos = [r[0] for r in cliente.recebidos if len(r[0]) <= 8_000]
    assert len(aceitos) > 1
    assert reconstruir_de_textos(aceitos) == texto
    assert math.fsum(v * v for v in vetor) == pytest.approx(1.0)


def reconstruir_de_textos(textos: list[str]) -> str:
    texto = textos[0]
    for seguinte in textos[1:]:
        sobra = next(n for n in range(min(len(texto), len(seguinte)), -1, -1) if texto.endswith(seguinte[:n]))
        texto += seguinte[sobra:]
    return texto


# --- 6: parte inválida invalida o item -------------------------------------------------------------------


def test_parte_invalida_invalida_o_item_e_ele_vai_a_fila(conn: sqlite3.Connection) -> None:
    def responder(prompt: str) -> RespostaExtracaoTexto | None:
        if "[parte 2 de" in prompt:
            return None
        return RespostaExtracaoTexto.model_validate(
            {"fatos_datados": [{"tipo": "trabalho", "conteudo": "abriu um escritório"}]}
        )

    cliente = _ClienteExtracaoFalso(conn, responder)
    item = _item(conn, TEXTOS_DE_COBERTURA["34.195 caracteres"])
    resumo = extrator.ResumoProcessamento()

    erro = extrator.processar_item(cliente, conn, item, resumo)

    assert isinstance(erro, FalhaJsonInvalido)
    assert resumo.erros == 1 and resumo.fatos_gravados == 0
    assert conn.execute("SELECT COUNT(*) FROM fato").fetchone()[0] == 0
    [na_fila] = fila_revisao.listar(conn)
    marcado = fila_extracao.obter(conn, item.id)
    assert marcado is not None and f"(fila_revisao id={na_fila.id})" in (marcado.erro or "")
    linha = conn.execute(
        "SELECT processado, partes_lidas FROM fila_extracao WHERE id = ?", (item.id,)
    ).fetchone()
    assert (linha["processado"], linha["partes_lidas"]) == (0, None)


# --- 7: fatos iguais aparecem uma vez; fato único divergente vira revisão --------------------------------


def test_fatos_iguais_em_partes_vizinhas_aparecem_uma_vez(conn: sqlite3.Connection) -> None:
    resposta = RespostaExtracaoTexto.model_validate(
        {
            "campos": {"cidade": "Recife", "linguas": ["inglês"]},
            "tags_sugeridas": [{"tag": "surfe", "peso": 3, "trecho": "gosta de surfe"}],
            "fatos_datados": [{"data": "2026-10-01", "tipo": "viagem", "conteudo": "foi a Lisboa"}],
        }
    )
    cliente = _ClienteExtracaoFalso(conn, lambda _p: resposta)
    item = _item(conn, TEXTOS_DE_COBERTURA["34.195 caracteres"])
    resumo = extrator.ResumoProcessamento()

    assert extrator.processar_item(cliente, conn, item, resumo) is None

    assert len(cliente.prompts) > 1
    assert (resumo.tags_gravadas, resumo.fatos_gravados) == (1, 1)
    assert conn.execute("SELECT COUNT(*) FROM fato").fetchone()[0] == 1
    linha = conn.execute("SELECT cidade, linguas FROM perfil WHERE id = ?", (item.perfil_id,)).fetchone()
    assert linha["cidade"] == "Recife" and "inglês" in linha["linguas"]


def test_consolidar_fatos_e_uniao_ordenada_que_guarda_a_parte_de_origem() -> None:
    unidos = texto_integral.consolidar_fatos([["a", "b"], ["b", "c"], ["a", "d"]])

    assert [(f.parte, f.valor) for f in unidos] == [(1, "a"), (1, "b"), (2, "c"), (3, "d")]


def test_fato_unico_divergente_vira_aviso_e_revisao_sem_voto(conn: sqlite3.Connection) -> None:
    def responder(prompt: str) -> RespostaExtracaoTexto:
        cidade = "Recife" if "[parte 1 de" in prompt else "Olinda"
        return RespostaExtracaoTexto.model_validate(
            {
                "campos": {"cidade": cidade},
                "tags_sugeridas": [{"tag": "surfe", "peso": 3, "trecho": "gosta de surfe"}],
            }
        )

    cliente = _ClienteExtracaoFalso(conn, responder)
    item = _item(conn, TEXTOS_DE_COBERTURA["34.195 caracteres"])
    resumo = extrator.ResumoProcessamento()

    erro = extrator.processar_item(cliente, conn, item, resumo)

    assert isinstance(erro, extrator.DivergenciaEntrePartes)
    assert resumo.erros == 1 and resumo.tags_gravadas == 0
    assert conn.execute("SELECT cidade FROM perfil WHERE id = ?", (item.perfil_id,)).fetchone()[0] is None
    [na_fila] = fila_revisao.listar(conn)
    assert na_fila.tarefa == "extrair_de_texto"
    assert "cidade" in na_fila.erro and "Recife" not in na_fila.erro
    completo = fila_revisao.obter(conn, na_fila.id)
    assert completo is not None and "Recife" in completo.entrada and "Olinda" in completo.entrada
    marcado = fila_extracao.obter(conn, item.id)
    assert marcado is not None and f"(fila_revisao id={na_fila.id})" in (marcado.erro or "")


def test_consolidar_unicos_aponta_a_divergencia_sem_escolher_valor() -> None:
    valores, divergencias = texto_integral.consolidar_unicos(
        [{"cidade": "Recife", "cargo": "juíza"}, {"cidade": "Olinda"}, {"cargo": "juíza"}]
    )

    assert valores == {"cargo": "juíza"}
    [divergencia] = divergencias
    assert divergencia.campo == "cidade"
    assert [(v.parte, v.valor) for v in divergencia.valores] == [(1, "Recife"), (2, "Olinda")]


# --- 8: servidor que recusa por tamanho -----------------------------------------------------------------


def test_servidor_que_recusa_por_tamanho_divide_o_orcamento_e_cobre_tudo(conn: sqlite3.Connection) -> None:
    texto = TEXTOS_DE_COBERTURA["34.195 caracteres"]
    cliente = _ClienteExtracaoFalso(conn, recusar_acima_de=8_000)
    item = _item(conn, texto)

    erro = extrator.processar_item(cliente, conn, item, extrator.ResumoProcessamento())

    assert erro is None
    assert any(len(p) > 8_000 for p in cliente.prompts)
    assert reconstruir_dos_prompts(cliente.aceitos) == texto
    assert fila_revisao.listar(conn) == []
    linha = conn.execute("SELECT partes_lidas FROM fila_extracao WHERE id = ?", (item.id,)).fetchone()
    assert linha[0] == len(cliente.aceitos)


def test_recusa_de_texto_que_nao_se_divide_mais_vai_a_fila_uma_vez(conn: sqlite3.Connection) -> None:
    cliente = _ClienteExtracaoFalso(conn, recusar_acima_de=10)

    erro = extrator.processar_item(cliente, conn, _item(conn, _TEXTO_CURTO), extrator.ResumoProcessamento())

    assert isinstance(erro, FalhaJanela)
    assert len(cliente.prompts) == 1
    assert len(fila_revisao.listar(conn)) == 1


# --- 9: registro de cobertura ----------------------------------------------------------------------------


def test_registro_de_cobertura_grava_1_para_texto_curto_e_n_para_dividido(conn: sqlite3.Connection) -> None:
    cliente = _ClienteExtracaoFalso(conn)
    curto = _item(conn, _TEXTO_CURTO)
    longo = _item(conn, TEXTOS_DE_COBERTURA["34.195 caracteres"])
    antigo = _item(conn, "processado antes do brief 088")

    extrator.processar_item(cliente, conn, curto, extrator.ResumoProcessamento())
    antes = len(cliente.prompts)
    extrator.processar_item(cliente, conn, longo, extrator.ResumoProcessamento())

    def partes(item_id: int) -> int | None:
        valor = conn.execute("SELECT partes_lidas FROM fila_extracao WHERE id = ?", (item_id,)).fetchone()[0]
        return int(valor) if valor is not None else None

    assert partes(curto.id) == 1
    assert partes(longo.id) == len(cliente.prompts) - antes > 1
    assert partes(antigo.id) is None
    versao = conn.execute(
        "SELECT gerado_por_prompt_versao FROM fila_extracao WHERE id = ?", (longo.id,)
    ).fetchone()[0]
    assert versao == extrair_de_texto.VERSAO


# --- captura de rede social ------------------------------------------------------------------------------


class _ClienteCapturaFalso:
    def __init__(self, responder: Any, conn: sqlite3.Connection | None = None) -> None:
        self._responder = responder
        self._conn = conn
        self.prompts: list[str] = []
        self.versoes: list[str | None] = []

    def num_ctx(self, tarefa_nome: str) -> int:
        return NUM_CTX

    def gerar_json(
        self,
        tarefa: str,
        prompt: str,
        esquema: type[_EsquemaT],
        imagens: list[str] | None = None,
        versao_prompt: str | None = None,
    ) -> _EsquemaT:
        self.prompts.append(prompt)
        self.versoes.append(versao_prompt)
        resposta = self._responder(prompt)
        if resposta is None:
            assert self._conn is not None
            fila_id = fila_revisao.inserir(self._conn, tarefa, prompt, "1 validation error", AGORA)
            raise FalhaJsonInvalido(tarefa, fila_id, "1 validation error")
        return esquema.model_validate(resposta.model_dump())


def test_bloco_longo_de_rede_social_e_lido_em_partes_e_consolidado(conn: sqlite3.Connection) -> None:
    bloco = _texto_longo(40_000)

    def responder(prompt: str) -> RespostaCapturaRedeSocial:
        if "[parte 2 de" in prompt:
            return RespostaCapturaRedeSocial(descartar=True)
        return RespostaCapturaRedeSocial(descartar=False, data_do_fato="2026-10-01", conteudo="post")

    cliente = _ClienteCapturaFalso(responder, conn)

    resultado = extrator_captura.extrair(cliente, bloco, "linkedin", conexao=conn)

    assert len(cliente.prompts) > 2
    assert reconstruir_dos_prompts(cliente.prompts) == bloco
    assert resultado is not None
    assert (resultado.descartar, resultado.data_do_fato, resultado.conteudo) == (False, "2026-10-01", "post")
    assert fila_revisao.listar(conn) == []


def test_bloco_longo_com_data_divergente_vai_para_revisao(conn: sqlite3.Connection) -> None:
    def responder(prompt: str) -> RespostaCapturaRedeSocial:
        data = "2026-10-01" if "[parte 1 de" in prompt else "2025-03-09"
        return RespostaCapturaRedeSocial(descartar=False, data_do_fato=data, conteudo="post")

    cliente = _ClienteCapturaFalso(responder, conn)

    resultado = extrator_captura.extrair(cliente, _texto_longo(40_000), "linkedin", conexao=conn)

    assert resultado is None
    [na_fila] = fila_revisao.listar(conn)
    assert na_fila.tarefa == "extrair_captura_rede_social" and "data_do_fato" in na_fila.erro


def test_parte_invalida_de_bloco_longo_invalida_o_bloco(conn: sqlite3.Connection) -> None:
    def responder(prompt: str) -> RespostaCapturaRedeSocial | None:
        if "[parte 2 de" in prompt:
            return None
        return RespostaCapturaRedeSocial(descartar=False, conteudo="post")

    cliente = _ClienteCapturaFalso(responder, conn)

    assert extrator_captura.extrair(cliente, _texto_longo(40_000), "linkedin", conexao=conn) is None
    assert len(fila_revisao.listar(conn)) == 1
