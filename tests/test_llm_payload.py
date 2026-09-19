from __future__ import annotations

import json
from pathlib import Path

import httpx
import yaml
from pydantic import BaseModel

from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.llm import ClienteOllama
from agente_nw.nucleo.modelos.configuracao import Roteamento

RAIZ = Path(__file__).resolve().parent.parent


class _EsquemaTeste(BaseModel):
    ok: bool


def test_corpo_da_chamada_tem_think_false_e_parametros_da_tarefa(tmp_path: Path) -> None:
    dados_roteamento = yaml.safe_load((RAIZ / "config" / "llm_routing.yaml").read_text(encoding="utf-8"))
    roteamento = Roteamento.model_validate(dados_roteamento)
    tarefa_qualificar = roteamento.perfis[roteamento.perfil_ativo].tarefas["qualificar"]

    capturado: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        capturado["corpo"] = json.loads(request.content)
        return httpx.Response(200, json={"response": json.dumps({"ok": True})})

    cliente_http = httpx.Client(transport=httpx.MockTransport(handler))
    conexao_bd = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_bd)

    cliente = ClienteOllama(
        cliente_http, conexao_bd, roteamento, "http://ollama.invalido", tmp_path / "chamadas_llm.jsonl"
    )
    resultado = cliente.gerar_json("qualificar", "prompt de teste", _EsquemaTeste)

    assert resultado.ok is True

    corpo = capturado["corpo"]
    assert isinstance(corpo, dict)
    assert corpo["think"] is False
    assert corpo["format"] == tarefa_qualificar.format
    assert corpo["options"]["num_ctx"] == tarefa_qualificar.num_ctx
    assert corpo["options"]["temperature"] == tarefa_qualificar.temperature

    conexao_bd.close()
