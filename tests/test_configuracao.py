from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from agente_nw.nucleo.modelos.configuracao import Configuracao, Limiares, Roteamento, TemasArquivo

RAIZ = Path(__file__).resolve().parent.parent


def _carregar(caminho: Path) -> dict[str, object]:
    return yaml.safe_load(caminho.read_text(encoding="utf-8"))


def test_temas_exemplo_carrega_e_valida() -> None:
    temas = TemasArquivo.model_validate(_carregar(RAIZ / "temas.exemplo.yaml"))
    assert temas.usuario.temas
    assert {t.nivel for t in temas.usuario.temas} <= {"dominio", "interesse", "curiosidade"}


def test_local_exemplo_carrega_e_valida() -> None:
    config = Configuracao.model_validate(_carregar(RAIZ / "config" / "local.exemplo.yaml"))
    assert config.banco
    assert config.ollama_url.startswith("http")


def test_fontes_exemplo_carrega_como_yaml_valido() -> None:
    dados = _carregar(RAIZ / "fontes.exemplo.yaml")
    assert "feeds" in dados
    assert isinstance(dados["feeds"], list)
    for feed in dados["feeds"]:
        assert {"nome", "url", "tipo", "confiabilidade"} <= feed.keys()


def test_llm_routing_carrega_e_valida() -> None:
    roteamento = Roteamento.model_validate(_carregar(RAIZ / "config" / "llm_routing.yaml"))
    assert roteamento.perfil_ativo in roteamento.perfis


def test_perfil_sem_think_false_e_recusado() -> None:
    dados = _carregar(RAIZ / "config" / "llm_routing.yaml")
    perfil = dados["perfis"]["air16"]
    perfil["tarefas"]["qualificar"]["think"] = True
    with pytest.raises(ValidationError):
        Roteamento.model_validate(dados)


def test_perfil_sem_campo_think_e_recusado() -> None:
    dados = _carregar(RAIZ / "config" / "llm_routing.yaml")
    del dados["perfis"]["air16"]["tarefas"]["rotular"]["think"]
    with pytest.raises(ValidationError):
        Roteamento.model_validate(dados)


def test_limiares_carrega_e_tem_todas_as_chaves() -> None:
    limiares = Limiares.model_validate(_carregar(RAIZ / "config" / "limiares.yaml"))
    assert limiares.agrupamento.cosseno_mesmo_assunto == 0.77
    assert limiares.agrupamento.cosseno_republicacao == 0.94
    assert limiares.agrupamento.divergencia_minima_fonte_independente == 0.08
    assert limiares.agrupamento.janela_dias == 7
    assert limiares.agrupamento.itens_para_dividir == 12
    assert limiares.qualificacao.substancial_minimo == 0.6
    assert limiares.qualificacao.conversavel_minimo == 0.6
    assert limiares.qualificacao.teto_por_dia == 40
    assert limiares.conector.adjacencia_minima == 0.55
    assert limiares.conector.conversavel_viavel == 0.8
    assert limiares.conector.peso_aderencia_contato == 50
    assert limiares.conector.peso_aderencia_usuario == 30
    assert limiares.conector.peso_conversavel == 20
    assert limiares.conector.peso_nivel == {"dominio": 1.0, "interesse": 0.7, "curiosidade": 0.4}
    assert limiares.conector.candidatos_por_contato == 10
    assert limiares.conector.itens_no_menu == 5


def test_tema_com_nivel_invalido_falha() -> None:
    dados = _carregar(RAIZ / "temas.exemplo.yaml")
    dados["usuario"]["temas"][0]["nivel"] = "outro"
    with pytest.raises(ValidationError):
        TemasArquivo.model_validate(dados)


def test_tema_com_descricao_curta_falha() -> None:
    dados = _carregar(RAIZ / "temas.exemplo.yaml")
    dados["usuario"]["temas"][0]["descricao"] = "muito curta"
    with pytest.raises(ValidationError):
        TemasArquivo.model_validate(dados)


def test_tema_com_nome_duplicado_falha() -> None:
    dados = _carregar(RAIZ / "temas.exemplo.yaml")
    duplicado = dict(dados["usuario"]["temas"][0])
    dados["usuario"]["temas"].append(duplicado)
    with pytest.raises(ValidationError):
        TemasArquivo.model_validate(dados)
