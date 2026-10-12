from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from agente_nw.coleta.capturas.listas import PaginaLista
from agente_nw.nucleo import localizacao as localizacao_mod
from agente_nw.nucleo import pedido as pedido_mod
from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import fatos, listas, perfis, redes_sociais
from agente_nw.nucleo.localizacao import ContextoNavegacao
from agente_nw.nucleo.modelos.configuracao import ListasLimiares
from agente_nw.nucleo.modelos.lista_rede_social import EntradaLista
from agente_nw.nucleo.modelos.localizacao import RespostaDesempate
from agente_nw.nucleo.modelos.pedido import PedidoExtraido

AGORA = "2026-10-11T10:00:00+00:00"
LIMIARES = ListasLimiares(maximo_entradas=2000, pausa_rolagem_s=0, validade_dias=30)
URL_LINKEDIN = "https://www.linkedin.com/in/"


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


class _PaginaLogin:
    """Rede sem sessão: tudo cai na tela de login."""

    def ir_para(self, url: str) -> None:
        pass

    def estado(self) -> tuple[str, str]:
        return "https://exemplo.test/login", ""

    def rolar(self) -> None:
        pass

    def coletar_links(self) -> list[tuple[str, str]]:
        return []

    def fechar(self) -> None:
        pass


class _PaginaBusca(_PaginaLogin):
    """Rede com sessão ativa e um resultado de busca geral."""

    def estado(self) -> tuple[str, str]:
        return "https://www.linkedin.com/search/results/people/", "x" * 600

    def coletar_links(self) -> list[tuple[str, str]]:
        return [(f"{URL_LINKEDIN}zuleica-xavier/", "Zuleica Xavier\nProfessora de piano")]


def _abrir_pagina(pasta: Path) -> PaginaLista:
    return _PaginaBusca() if pasta.name == "linkedin" else _PaginaLogin()


def _navegacao(abrir: Callable[[Path], PaginaLista] = _abrir_pagina) -> ContextoNavegacao:
    return ContextoNavegacao(
        abrir_pagina=abrir,
        pasta_navegador=Path("navegador"),
        limiares=LIMIARES,
        usuarios_rede={},
        dorme=lambda _s: None,
    )


def _popular_linkedin(conn: sqlite3.Connection, pessoas: list[tuple[str, str]]) -> None:
    entradas = [
        EntradaLista(
            rede="linkedin",
            nome=nome,
            cabecalho=cabecalho,
            link=URL_LINKEDIN + nome.lower().replace(" ", "-"),
        )
        for nome, cabecalho in pessoas
    ]
    listas.substituir_lista(conn, "linkedin", entradas, AGORA)
    conn.commit()


def _pedido(nome: str = "Marcos", pistas: dict[str, str] | None = None, **mudancas: Any) -> PedidoExtraido:
    dados: dict[str, Any] = {
        "pessoa_nome": nome,
        "pessoa_pistas": pistas or {},
        "objetivo": "retomar",
        "objetivo_texto": "retomar o contato",
        "registro": "cordial",
        "assunto_principal": "tributação",
        "termos_busca": ["reforma tributária"],
        "confianca": 0.9,
    }
    dados.update(mudancas)
    return PedidoExtraido.model_validate(dados)


class _LLM:
    def __init__(
        self,
        indice: int | None = None,
        confianca: float = 0.9,
        pedido: PedidoExtraido | None = None,
    ) -> None:
        self.indice = indice
        self.confianca = confianca
        self.pedido = pedido
        self.chamadas: list[str] = []

    def gerar_json(self, tarefa_nome: str, prompt: str, esquema: type[Any]) -> Any:
        self.chamadas.append(tarefa_nome)
        if tarefa_nome == "desempatar_perfil":
            return RespostaDesempate(indice_escolhido=self.indice, confianca=self.confianca, motivo="teste")
        assert self.pedido is not None
        return self.pedido


def test_um_candidato_com_pista_casada_e_claro_sem_chamar_a_ia(conn: sqlite3.Connection) -> None:
    _popular_linkedin(
        conn,
        [
            ("Marcos Pinto", "Sócio, escritório tributarista, São Paulo"),
            ("Marcos Lima", "Engenheiro civil"),
        ],
    )
    llm = _LLM()

    resultado = localizacao_mod.localizar(
        conn, llm, _pedido(pistas={"profissao": "tributarista"}), _navegacao(), AGORA
    )

    assert resultado.status == "claro"
    assert resultado.escolhido is not None and resultado.escolhido.nome == "Marcos Pinto"
    assert llm.chamadas == []
    assert len(resultado.opcoes) == 2


def test_empate_com_ia_confiante_escolhe_o_indicado(conn: sqlite3.Connection) -> None:
    _popular_linkedin(conn, [("Marcos Aguiar", "Advogado em Recife"), ("Marcos Barros", "Advogado em Natal")])
    llm = _LLM(indice=2, confianca=0.9)

    resultado = localizacao_mod.localizar(
        conn, llm, _pedido(pistas={"profissao": "advogado"}), _navegacao(), AGORA
    )

    assert resultado.status == "claro"
    assert resultado.escolhido is not None and resultado.escolhido.nome == "Marcos Barros"
    assert llm.chamadas == ["desempatar_perfil"]


def test_empate_com_ia_insegura_vira_ambiguo(conn: sqlite3.Connection) -> None:
    _popular_linkedin(conn, [("Marcos Aguiar", "Advogado em Recife"), ("Marcos Barros", "Advogado em Natal")])
    llm = _LLM(indice=2, confianca=0.4)

    resultado = localizacao_mod.localizar(
        conn, llm, _pedido(pistas={"profissao": "advogado"}), _navegacao(), AGORA
    )

    assert resultado.status == "ambiguo"
    assert resultado.escolhido is None
    assert {o.nome for o in resultado.opcoes} == {"Marcos Aguiar", "Marcos Barros"}


def test_homonimos_sem_pistas_sao_ambiguos_e_nao_chamam_a_ia(conn: sqlite3.Connection) -> None:
    _popular_linkedin(conn, [("Marcos Aguiar", "Advogado"), ("Marcos Barros", "Médico")])
    llm = _LLM()

    resultado = localizacao_mod.localizar(conn, llm, _pedido(), _navegacao(), AGORA)

    assert resultado.status == "ambiguo"
    assert llm.chamadas == []


def test_pessoa_fora_das_listas_cai_na_busca_geral(conn: sqlite3.Connection) -> None:
    _popular_linkedin(conn, [("Marcos Aguiar", "Advogado")])

    resultado = localizacao_mod.localizar(conn, _LLM(), _pedido(nome="Zuleica"), _navegacao(), AGORA)

    assert resultado.status == "nenhum"
    assert resultado.fonte == "busca_geral"
    assert [o.nome for o in resultado.opcoes] == ["Zuleica Xavier"]
    assert resultado.opcoes[0].fonte == "busca_geral"


def test_ordem_das_redes() -> None:
    assert localizacao_mod.ordem_das_redes("cordial", {})[0] == "linkedin"
    assert localizacao_mod.ordem_das_redes("formal", {})[0] == "linkedin"
    assert localizacao_mod.ordem_das_redes("proximo", {})[0] == "instagram"
    assert localizacao_mod.ordem_das_redes("proximo", {"profissao": "médico"})[0] == "linkedin"
    todas = localizacao_mod.ordem_das_redes("cordial", {})
    assert sorted(todas) == ["facebook", "instagram", "linkedin"]


def test_confirmar_grava_rede_notas_vinculo_e_fato(conn: sqlite3.Connection) -> None:
    contato = perfis.inserir_novo_contato(conn, "Marcos Pinto", None, None, AGORA)
    assert contato.id is not None
    _popular_linkedin(conn, [("Marcos Pinto", "Sócio, escritório tributarista")])
    entrada = listas.listar_por_rede(conn, "linkedin")[0]

    localizacao_mod.confirmar(conn, contato.id, localizacao_mod.opcao_da_entrada(entrada), AGORA)

    assert [r.link for r in redes_sociais.listar_por_perfil(conn, contato.id)] == [entrada.link]
    atualizado = perfis.obter_por_id(conn, contato.id)
    assert atualizado is not None and atualizado.notas == "Sócio, escritório tributarista"
    assert listas.listar_por_rede(conn, "linkedin")[0].perfil_id == contato.id
    recentes = fatos.listar_recentes(conn, contato.id, 10)
    esperado = [("lista_rede_social", "Sócio, escritório tributarista")]
    assert [(f.tipo, f.conteudo) for f in recentes] == esperado

    localizacao_mod.confirmar(conn, contato.id, localizacao_mod.opcao_da_entrada(entrada), AGORA)
    assert len(redes_sociais.listar_por_perfil(conn, contato.id)) == 1
    assert len(fatos.listar_recentes(conn, contato.id, 10)) == 1


def test_link_no_pedido_grava_direto_sem_localizar(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _nao_deveria(*_a: Any, **_k: Any) -> None:
        raise AssertionError("localizar não deveria ser chamado")

    monkeypatch.setattr(localizacao_mod, "localizar", _nao_deveria)
    pedido = _pedido(nome="Renato", pistas={"link_rede_social": f"{URL_LINKEDIN}renato-alves/?trk=abc"})

    resultado = pedido_mod.processar(_LLM(pedido=pedido), conn, "frase", AGORA, navegacao=_navegacao())

    assert resultado.localizacao is None
    assert resultado.link_gravado is not None
    assert resultado.perfil is not None and resultado.perfil.id is not None
    redes = redes_sociais.listar_por_perfil(conn, resultado.perfil.id)
    assert [(r.rede, r.link) for r in redes] == [("linkedin", f"{URL_LINKEDIN}renato-alves")]


def test_contato_com_rede_gravada_nao_e_procurado_de_novo(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    contato = perfis.inserir_novo_contato(conn, "Renato Alves", None, None, AGORA)
    assert contato.id is not None
    redes_sociais.inserir(conn, contato.id, "linkedin", f"{URL_LINKEDIN}renato-alves", AGORA)
    conn.commit()

    def _nao_deveria(*_a: Any, **_k: Any) -> None:
        raise AssertionError("localizar não deveria ser chamado")

    monkeypatch.setattr(localizacao_mod, "localizar", _nao_deveria)

    resultado = pedido_mod.processar(
        _LLM(pedido=_pedido(nome="Renato")), conn, "frase", AGORA, navegacao=_navegacao()
    )

    assert resultado.localizacao is None


def test_trocar_perfil_reabre_a_localizacao(conn: sqlite3.Connection) -> None:
    contato = perfis.inserir_novo_contato(conn, "Renato Alves", None, None, AGORA)
    assert contato.id is not None
    redes_sociais.inserir(conn, contato.id, "linkedin", f"{URL_LINKEDIN}renato-antigo", AGORA)
    conn.commit()
    _popular_linkedin(conn, [("Renato Alves", "Engenheiro")])

    resultado = pedido_mod.processar(
        _LLM(pedido=_pedido(nome="Renato")),
        conn,
        "frase",
        AGORA,
        navegacao=_navegacao(),
        trocar_perfil=True,
    )

    assert resultado.localizacao is not None
    assert resultado.localizacao.status == "claro"


def test_x_nunca_entra_na_leitura_automatica(capsys: pytest.CaptureFixture[str]) -> None:
    import agente_nw.cli as cli

    assert "x" not in localizacao_mod.ordem_das_redes("proximo", {})
    assert cli.listas_atualizar_cmd("x", forcar=True) == 1
    assert "bloqueia navegador automatizado" in capsys.readouterr().out
