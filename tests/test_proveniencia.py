"""Proveniência do que a IA produziu (brief 066): versão obrigatória em cada módulo de prompt, o cliente
registra perfil, modelo, versão do prompt e latência, os registros gerados guardam quem os gerou e os
centróides guardam o modelo de embedding — e um centróide de outro modelo é tratado como ausente."""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

import httpx
import pytest
import yaml
from pydantic import BaseModel

from agente_nw.nucleo import redacao as redacao_mod
from agente_nw.nucleo.consulta import ResultadoConsulta, ResumoRedeSocial
from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import assuntos, consulta_contato, perfis, temas
from agente_nw.nucleo.llm import ClienteOllama
from agente_nw.nucleo.modelos.configuracao import Roteamento
from agente_nw.nucleo.modelos.pedido import PedidoExtraido
from agente_nw.nucleo.prompts import redigir_ganchos
from agente_nw.perfil import configurador
from tests.test_console_novo_contato import _limiares

RAIZ = Path(__file__).resolve().parent.parent
AGORA = "2026-11-02T10:00:00+00:00"


class _EsquemaTeste(BaseModel):
    ok: bool


def _dados_roteamento() -> dict[str, Any]:
    dados: dict[str, Any] = yaml.safe_load((RAIZ / "config" / "llm_routing.yaml").read_text(encoding="utf-8"))
    return dados


def _roteamento(modelo_embedding: str | None = None) -> Roteamento:
    dados = _dados_roteamento()
    if modelo_embedding is not None:
        for perfil in dados["perfis"].values():
            perfil["embeddings"]["modelo"] = modelo_embedding
    return Roteamento.model_validate(dados)


def _abrir(tmp_path: Path) -> sqlite3.Connection:
    conn = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conn)
    return conn


def _vetor(*valores: float) -> list[float]:
    # Armadilha 28: vec0 exige exatamente 1024 posições.
    return [*valores, *([0.0] * (1024 - len(valores)))]


def _cliente(
    conn: sqlite3.Connection,
    handler: Any,
    caminho_log: Path,
    roteamento: Roteamento | None = None,
) -> ClienteOllama:
    return ClienteOllama(
        httpx.Client(transport=httpx.MockTransport(handler)),
        conn,
        roteamento or _roteamento(),
        "http://ollama.invalido",
        caminho_log,
    )


def _handler_json(resposta: dict[str, Any]) -> Any:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/embed":
            corpo = json.loads(request.content)
            return httpx.Response(200, json={"embeddings": [_vetor(1.0) for _ in corpo["input"]]})
        return httpx.Response(200, json={"response": json.dumps(resposta)})

    return handler


# --- 3.1: versão obrigatória em cada módulo de prompt ---------------------------------------------


def test_carregar_aplicacao_com_modulo_de_prompt_sem_versao_falha_citando_o_modulo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from agente_nw.nucleo import prompts
    from config import container

    pasta_extra = tmp_path / "prompts_extra"
    pasta_extra.mkdir()
    (pasta_extra / "prompt_sem_versao.py").write_text(
        "def construir_prompt() -> str:\n    return 'x'\n", encoding="utf-8"
    )
    monkeypatch.setattr(prompts, "__path__", [*prompts.__path__, str(pasta_extra)])
    container.configuracao.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="prompt_sem_versao"):
            container.configuracao()
    finally:
        sys.modules.pop("agente_nw.nucleo.prompts.prompt_sem_versao", None)
        container.configuracao.cache_clear()


def test_todos_os_modulos_de_prompt_declaram_versao() -> None:
    from agente_nw.nucleo import prompts

    prompts.verificar_versoes()


# --- 3.2: o cliente registra o que usou -------------------------------------------------------------


def test_gerar_json_registra_perfil_modelo_versao_e_latencia_no_log(tmp_path: Path) -> None:
    conn = _abrir(tmp_path)
    caminho_log = tmp_path / "chamadas_llm.jsonl"
    roteamento = _roteamento()
    cliente = _cliente(conn, _handler_json({"ok": True}), caminho_log, roteamento)

    cliente.gerar_json("qualificar", "prompt", _EsquemaTeste, versao_prompt="2026-09-19-1")

    (linha,) = [json.loads(texto) for texto in caminho_log.read_text(encoding="utf-8").splitlines()]
    perfil_ativo = roteamento.perfil_ativo
    assert linha["perfil"] == perfil_ativo
    assert linha["modelo"] == roteamento.perfis[perfil_ativo].tarefas["qualificar"].modelo
    assert linha["versao_prompt"] == "2026-09-19-1"
    assert isinstance(linha["latencia_ms"], int | float)
    assert linha["latencia_ms"] >= 0
    # Campos que já existiam continuam lá.
    assert linha["tarefa"] == "qualificar"
    assert linha["sucesso"] is True


def test_gerar_json_sem_versao_de_prompt_registra_none(tmp_path: Path) -> None:
    conn = _abrir(tmp_path)
    caminho_log = tmp_path / "chamadas_llm.jsonl"
    cliente = _cliente(conn, _handler_json({"ok": True}), caminho_log)

    cliente.gerar_json("qualificar", "prompt", _EsquemaTeste)

    (linha,) = [json.loads(texto) for texto in caminho_log.read_text(encoding="utf-8").splitlines()]
    assert linha["versao_prompt"] is None


# --- 3.3: proveniência nos registros gerados ----------------------------------------------------------


def _pedido() -> PedidoExtraido:
    return PedidoExtraido.model_validate(
        {
            "objetivo": "pedir",
            "objetivo_texto": "pedir apoio na chapa da OAB",
            "registro": "cordial",
            "assunto_principal": "eleição da OAB",
            "termos_busca": ["OAB"],
            "confianca": 0.9,
        }
    )


def test_gancho_gravado_tem_as_tres_colunas_de_proveniencia_do_cliente(tmp_path: Path) -> None:
    conn = _abrir(tmp_path)
    contato = perfis.inserir_novo_contato(conn, "João", None, None, AGORA)
    assert contato.id is not None
    usuario = perfis.upsert_usuario(conn, "Rafael", AGORA)
    consulta = consulta_contato.inserir(conn, contato.id, AGORA, "{}", None, "[]")
    assert consulta.id is not None
    conn.commit()
    resposta = {"ganchos": [{"assunto_id": None, "mensagem": "Oi João, posso contar com seu apoio?"}]}
    cliente = _cliente(conn, _handler_json(resposta), tmp_path / "log.jsonl")
    resultado = ResultadoConsulta(contato.id, consulta.id, [], ResumoRedeSocial(), "")

    redacao = redacao_mod.redigir(cliente, conn, _pedido(), resultado, contato, usuario, AGORA, frase="x")
    redacao_mod.registrar(conn, consulta.id, redacao, AGORA)

    linha = conn.execute(
        "SELECT gerado_por_modelo, gerado_por_perfil, gerado_por_prompt_versao FROM gancho_uso "
        "WHERE consulta_id = ? AND assunto_id IS NULL",
        (consulta.id,),
    ).fetchone()
    esperado = cliente.proveniencia("redigir_ganchos", redigir_ganchos.VERSAO)
    assert linha["gerado_por_modelo"] == esperado.modelo
    assert linha["gerado_por_perfil"] == esperado.perfil
    assert linha["gerado_por_prompt_versao"] == redigir_ganchos.VERSAO
    assert esperado.modelo and esperado.perfil


def _colunas(conn: sqlite3.Connection, tabela: str) -> list[tuple[str, str, str]]:
    linhas = conn.execute(
        f"SELECT gerado_por_modelo, gerado_por_perfil, gerado_por_prompt_versao FROM {tabela}"  # noqa: S608
    ).fetchall()
    return [tuple(linha) for linha in linhas]


def test_extracao_grava_proveniencia_no_item_da_fila_e_no_fato(tmp_path: Path) -> None:
    from agente_nw.nucleo.database.queries import fila_extracao
    from agente_nw.nucleo.prompts import extrair_de_texto
    from agente_nw.perfil.extrator import processar_fila

    conn = _abrir(tmp_path)
    contato = perfis.inserir_novo_contato(conn, "João", None, None, AGORA)
    assert contato.id is not None
    fila_extracao.inserir(conn, contato.id, "João abriu um escritório em Curitiba.", "manual", AGORA)
    conn.commit()
    resposta = {"fatos_datados": [{"tipo": "trabalho", "conteudo": "abriu um escritório em Curitiba"}]}
    cliente = _cliente(conn, _handler_json(resposta), tmp_path / "log.jsonl")

    processar_fila(cliente, conn)

    esperado = cliente.proveniencia("extrair_de_texto", extrair_de_texto.VERSAO)
    trio = (esperado.modelo, esperado.perfil, extrair_de_texto.VERSAO)
    assert _colunas(conn, "fila_extracao") == [trio]
    assert _colunas(conn, "fato") == [trio]


def test_cartao_grava_proveniencia_no_assunto(tmp_path: Path) -> None:
    from agente_nw.nucleo.prompts import cartao
    from agente_nw.nucleo.relevancia import cartoes

    conn = _abrir(tmp_path)
    conn.execute(
        "INSERT INTO assunto (titulo_gerado, primeiro_visto, ultimo_visto, status) "
        "VALUES ('t', ?, ?, 'novo')",
        (AGORA, AGORA),
    )
    (assunto_id,) = conn.execute("SELECT MAX(id) FROM assunto").fetchone()
    conn.commit()
    cliente = _cliente(conn, _handler_json({"resumo": "Obras começam na orla."}), tmp_path / "log.jsonl")

    assert cartoes.gerar_cartao(cliente, conn, assunto_id) is not None

    esperado = cliente.proveniencia("cartao", cartao.VERSAO)
    assert _colunas(conn, "assunto") == [(esperado.modelo, esperado.perfil, cartao.VERSAO)]


# --- 3.4: proveniência do vetor, sem sobrescrever -------------------------------------------------------


def test_vetor_de_tema_calculado_hoje_grava_o_modelo_de_embedding_do_perfil_ativo(tmp_path: Path) -> None:
    conn = _abrir(tmp_path)
    roteamento = _roteamento()
    cliente = _cliente(conn, _handler_json({}), tmp_path / "log.jsonl", roteamento)
    from agente_nw.nucleo.modelos.configuracao import TemaUsuario

    configurador.salvar_perfil_usuario(
        conn,
        cliente,
        "Rafael",
        [
            TemaUsuario(
                nome="vela",
                descricao="vela oceânica em regatas de longa distância pelo litoral",
                nivel="interesse",
                peso=3,
            )
        ],
        AGORA,
    )

    (modelo_gravado,) = conn.execute("SELECT modelo_embedding FROM vetor_tema").fetchone()
    assert modelo_gravado == roteamento.perfis[roteamento.perfil_ativo].embeddings.modelo
    assert modelo_gravado == cliente.modelo_embedding


def test_centroide_de_outro_modelo_de_embedding_e_tratado_como_ausente_sem_apagar_a_linha(
    tmp_path: Path,
) -> None:
    conn = _abrir(tmp_path)
    cliente_antigo = _cliente(conn, _handler_json({}), tmp_path / "log.jsonl", _roteamento())
    cliente_novo = _cliente(conn, _handler_json({}), tmp_path / "log.jsonl", _roteamento("outro-embedding"))
    assert cliente_antigo.modelo_embedding != cliente_novo.modelo_embedding

    tema = temas.obter_ou_criar(conn, "vela", "vela oceânica", [], AGORA)
    assert tema.id is not None
    temas.gravar_embedding(conn, tema.id, _vetor(1.0), cliente_antigo.modelo_embedding)
    conn.execute(
        "INSERT INTO assunto (primeiro_visto, ultimo_visto, status) VALUES (?, ?, 'novo')", (AGORA, AGORA)
    )
    (assunto_id,) = conn.execute("SELECT MAX(id) FROM assunto").fetchone()
    assuntos.gravar_centroide(conn, assunto_id, _vetor(0.0, 1.0), cliente_antigo.modelo_embedding)
    contato = perfis.inserir_novo_contato(conn, "João", None, None, AGORA)
    assert contato.id is not None
    perfis.gravar_centroide(conn, contato.id, _vetor(1.0, 1.0), cliente_antigo.modelo_embedding)
    conn.commit()

    # Com o modelo antigo, os centróides são lidos normalmente.
    assert assuntos.obter_centroide(conn, assunto_id, cliente_antigo.modelo_embedding) is not None
    assert perfis.obter_centroide(conn, contato.id, cliente_antigo.modelo_embedding) is not None
    assert len(temas.listar_com_embedding(conn, cliente_antigo.modelo_embedding)) == 1

    # Trocado o modelo de embedding, o centróide antigo é ausente — não lido como se fosse do novo.
    assert assuntos.obter_centroide(conn, assunto_id, cliente_novo.modelo_embedding) is None
    assert perfis.obter_centroide(conn, contato.id, cliente_novo.modelo_embedding) is None
    assert temas.listar_com_embedding(conn, cliente_novo.modelo_embedding) == []

    # E nenhuma linha foi apagada ou sobrescrita.
    for tabela in ("vetor_tema", "vetor_assunto", "vetor_perfil"):
        linhas = conn.execute(f"SELECT modelo_embedding FROM {tabela}").fetchall()  # noqa: S608
        assert [linha["modelo_embedding"] for linha in linhas] == [cliente_antigo.modelo_embedding]


def test_pontuacao_de_relevancia_grava_a_tarefa_que_decidiu_a_linha(tmp_path: Path) -> None:
    """`assunto_contato`: o descarte pelo juízo do objetivo leva a proveniência de
    `avaliar_relacao_objetivo`; a linha que entra no menu, a de `cruzar_por_que` (o "por quê")."""
    from agente_nw.nucleo.prompts import avaliar_relacao_objetivo, cruzar_por_que
    from agente_nw.nucleo.relevancia.cruzamento import cruzar_contato_por_consulta
    from tests import test_gate_objetivo as gate

    conn = gate._abrir(tmp_path)
    perfil_id = gate._contato(conn)
    fora = gate._assunto(conn, "Manifestação reúne multidão na Avenida Paulista")
    oab = gate._assunto(conn, "OAB-SP abre processo disciplinar contra startup de ensino jurídico")
    cliente = gate._ClienteFalso()

    cruzar_contato_por_consulta(
        cliente, conn, perfil_id, gate._contexto(), gate.CENTROIDE_CONSULTA, _limiares(), gate.AGORA
    )

    linhas = {
        linha["assunto_id"]: (
            linha["gerado_por_modelo"],
            linha["gerado_por_perfil"],
            linha["gerado_por_prompt_versao"],
        )
        for linha in conn.execute("SELECT * FROM assunto_contato").fetchall()
    }
    gate_prov = cliente.proveniencia("avaliar_relacao_objetivo", avaliar_relacao_objetivo.VERSAO)
    por_que_prov = cliente.proveniencia("cruzar_por_que", cruzar_por_que.VERSAO)
    assert linhas[fora] == (gate_prov.modelo, gate_prov.perfil, avaliar_relacao_objetivo.VERSAO)
    assert linhas[oab] == (por_que_prov.modelo, por_que_prov.perfil, cruzar_por_que.VERSAO)
