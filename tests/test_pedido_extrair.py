from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from agente_nw.nucleo import pedido as pedido_mod
from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.modelos.pedido import PedidoExtraido


def base(**mudancas: Any) -> dict[str, Any]:
    dados: dict[str, Any] = {
        "pessoa_nome": "Renato",
        "pessoa_pistas": {"profissao": "engenheiro naval", "empresa": ""},
        "objetivo": "retomar",
        "objetivo_texto": "retomar o contato",
        "meio": "pessoalmente",
        "registro": "cordial",
        "assunto_principal": "construção naval no Brasil",
        "interessa": ["estaleiros"],
        "evitar": [],
        "termos_busca": ["estaleiros", "construção naval", "Petrobras"],
        "continuacao": False,
        "confianca": 0.8,
    }
    dados.update(mudancas)
    return dados


class _ClienteFalso:
    def __init__(self, dados: dict[str, Any]) -> None:
        self._dados = dados
        self.prompts: list[str] = []

    def gerar_json(self, tarefa_nome: str, prompt: str, esquema: type[Any]) -> Any:
        assert tarefa_nome == "extrair_pedido"
        self.prompts.append(prompt)
        return esquema.model_validate(self._dados)


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


def test_schema_valida_e_descarta_pista_vazia() -> None:
    pedido = PedidoExtraido.model_validate(base())
    assert pedido.pessoa_pistas == {"profissao": "engenheiro naval"}
    assert pedido.meio == "pessoalmente"


def test_listas_sao_deduplicadas_sem_acento_e_sem_caixa() -> None:
    pedido = PedidoExtraido.model_validate(
        base(interessa=["Política", "politica", "vela"], termos_busca=["Câmbio", "cambio", "juros"])
    )
    assert pedido.interessa == ["Política", "vela"]
    assert pedido.termos_busca == ["Câmbio", "juros"]


def test_termos_de_busca_vazios_sao_rejeitados() -> None:
    with pytest.raises(ValidationError):
        PedidoExtraido.model_validate(base(termos_busca=[]))


def test_termos_de_busca_acima_de_seis_sao_cortados() -> None:
    pedido = PedidoExtraido.model_validate(base(termos_busca=["a", "b", "c", "d", "e", "f", "g"]))
    assert pedido.termos_busca == ["a", "b", "c", "d", "e", "f"]


@pytest.mark.parametrize("bruto", ["Dr. Renato Alves", "dra. Renato Alves", "Sr Renato Alves"])
def test_titulo_do_nome_e_limpo(bruto: str) -> None:
    assert PedidoExtraido.model_validate(base(pessoa_nome=bruto)).pessoa_nome == "Renato Alves"


def test_extrair_monta_prompt_com_a_frase_e_chama_a_tarefa(conn: sqlite3.Connection) -> None:
    cliente = _ClienteFalso(base())
    pedido = pedido_mod.extrair(cliente, conn, "Café com o Renato amanhã")
    assert pedido.pessoa_nome == "Renato"
    assert "Café com o Renato amanhã" in cliente.prompts[0]


def test_rotulo_inventado_pelo_modelo_vira_neutro_sem_derrubar_o_pedido() -> None:
    pedido = PedidoExtraido(**base(objetivo="conversar", meio="Zap", registro="Descontraído"))

    assert pedido.objetivo == "outro"
    assert pedido.meio == "outro"
    assert pedido.registro == "cordial"
    assert pedido.objetivo_texto == "retomar o contato"


def test_rotulo_valido_com_caixa_diferente_e_aceito() -> None:
    pedido = PedidoExtraido(**base(objetivo="Retomar", registro="FORMAL"))

    assert pedido.objetivo == "retomar"
    assert pedido.registro == "formal"
