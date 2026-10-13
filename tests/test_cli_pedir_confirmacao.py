from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import agente_nw.cli as cli
from agente_nw.coleta.capturas.listas import PaginaLista
from agente_nw.nucleo import localizacao as localizacao_mod
from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import listas, perfis, rede_sem_perfil, redes_sociais
from agente_nw.nucleo.modelos.configuracao import ListasLimiares
from agente_nw.nucleo.modelos.lista_rede_social import EntradaLista
from agente_nw.nucleo.modelos.localizacao import RespostaDesempate
from agente_nw.nucleo.modelos.pedido import PedidoExtraido

URL = "https://www.linkedin.com/in/"


def _pedido(nome: str = "Marcos", pistas: dict[str, str] | None = None) -> PedidoExtraido:
    return PedidoExtraido.model_validate(
        {
            "pessoa_nome": nome,
            "pessoa_pistas": pistas or {},
            "objetivo": "retomar",
            "objetivo_texto": "retomar",
            "registro": "cordial",
            "assunto_principal": "tributação",
            "termos_busca": ["reforma tributária"],
            "confianca": 0.9,
        }
    )


class _LLM:
    def __init__(self, pedido: PedidoExtraido) -> None:
        self._pedido = pedido

    def gerar_json(self, tarefa_nome: str, prompt: str, esquema: type[Any]) -> Any:
        if tarefa_nome == "desempatar_perfil":
            return RespostaDesempate(indice_escolhido=None, confianca=0.1, motivo="sem certeza")
        return self._pedido


class _PaginaBuscaGeral:
    def __init__(self, rede: str) -> None:
        self._rede = rede

    def ir_para(self, url: str) -> None:
        pass

    def estado(self) -> tuple[str, str]:
        if self._rede == "linkedin":
            return "https://www.linkedin.com/search/results/people/", "x" * 600
        return "https://exemplo.test/login", ""

    def rolar(self) -> None:
        pass

    def coletar_links(self) -> list[tuple[str, str]]:
        if self._rede != "linkedin":
            return []
        return [(f"{URL}zuleica-xavier/", "Zuleica Xavier\nProfessora de piano")]

    def fechar(self) -> None:
        pass


def _abrir_pagina(pasta: Path) -> PaginaLista:
    return _PaginaBuscaGeral(pasta.name)


def _respostas(*itens: str) -> Any:
    """As respostas previstas, na ordem. As redes seguintes (sem ninguém para escolher) perguntam só
    o link do perfil; sem resposta prevista, o usuário aperta Enter e pula."""
    fila: Iterator[str] = iter(itens)

    def entrada(_pergunta: str) -> str:
        return next(fila, "")

    return entrada


def _sem_pergunta(_pergunta: str) -> str:
    raise AssertionError("não deveria perguntar nada")


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


@pytest.fixture
def agora_real() -> str:
    """As listas do teste são gravadas 'agora', para o cache valer na hora do pedido."""
    return datetime.now(UTC).isoformat()


def _popular(conn: sqlite3.Connection, agora: str, linkedin: list[tuple[str, str]]) -> None:
    for rede in ("linkedin", "instagram", "x", "facebook"):
        pessoas = linkedin if rede == "linkedin" else [("Filler Pessoa", "Qualquer")]
        entradas = [
            EntradaLista(
                rede=rede,
                nome=nome,
                cabecalho=cabecalho,
                link=f"https://exemplo.test/{rede}/{nome.lower().replace(' ', '-')}",
            )
            for nome, cabecalho in pessoas
        ]
        listas.substituir_lista(conn, rede, entradas, agora)
    conn.commit()


@pytest.fixture(autouse=True)
def _ambiente(conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "banco", lambda: conn)
    falsa = SimpleNamespace(
        limiares=SimpleNamespace(
            listas=ListasLimiares(maximo_entradas=2000, pausa_rolagem_s=0, validade_dias=30)
        ),
        local=SimpleNamespace(redes={}),
    )
    monkeypatch.setattr(cli, "configuracao", lambda: falsa)


def _redes_do_contato(conn: sqlite3.Connection) -> list[tuple[str, str]]:
    contatos = perfis.listar_todos(conn)
    assert len(contatos) == 1 and contatos[0].id is not None
    return [(r.rede, r.link) for r in redes_sociais.listar_por_perfil(conn, contatos[0].id)]


def _pedir(
    monkeypatch: pytest.MonkeyPatch,
    pedido: PedidoExtraido,
    entrada: Any,
    sem_perguntar: bool = False,
    trocar_perfil: bool = False,
) -> int:
    monkeypatch.setattr(cli, "llm", lambda: _LLM(pedido))
    return cli.pedir_cmd(
        "frase qualquer",
        False,
        False,
        None,
        sem_perguntar=sem_perguntar,
        trocar_perfil=trocar_perfil,
        entrada=entrada,
        abrir_pagina=_abrir_pagina,
    )


def _com_um_marcos(conn: sqlite3.Connection, agora: str) -> None:
    pessoas = [("Marcos Pinto", "Sócio, escritório tributarista"), ("Marcos Lima", "Engenheiro")]
    _popular(conn, agora, pessoas)


PISTA = {"profissao": "tributarista"}


def test_claro_e_s_confirma(
    conn: sqlite3.Connection,
    monkeypatch: pytest.MonkeyPatch,
    agora_real: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _com_um_marcos(conn, agora_real)

    _pedir(monkeypatch, _pedido(pistas=PISTA), _respostas("S"))

    assert "É esta pessoa? Marcos Pinto" in capsys.readouterr().out
    assert _redes_do_contato(conn) == [("linkedin", "https://exemplo.test/linkedin/marcos-pinto")]


def test_claro_e_enter_confirma(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch, agora_real: str
) -> None:
    _com_um_marcos(conn, agora_real)

    _pedir(monkeypatch, _pedido(pistas=PISTA), _respostas(""))

    assert len(_redes_do_contato(conn)) == 1


def test_claro_e_n_mostra_todos_os_candidatos_e_aceita_numero(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch, agora_real: str
) -> None:
    _com_um_marcos(conn, agora_real)

    _pedir(monkeypatch, _pedido(pistas=PISTA), _respostas("n", "2"))

    assert _redes_do_contato(conn) == [("linkedin", "https://exemplo.test/linkedin/marcos-lima")]


def test_ambiguo_aceita_numero(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch, agora_real: str
) -> None:
    _popular(conn, agora_real, [("Marcos Aguiar", "Advogado"), ("Marcos Barros", "Médico")])

    _pedir(monkeypatch, _pedido(), _respostas("2"))

    assert _redes_do_contato(conn) == [("linkedin", "https://exemplo.test/linkedin/marcos-barros")]


def test_ambiguo_opcao_l_filtra_a_lista_e_escolhe(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch, agora_real: str
) -> None:
    _popular(
        conn,
        agora_real,
        [("Marcos Aguiar", "Advogado"), ("Marcos Barros", "Médico"), ("Beatriz Nunes", "Contadora")],
    )

    _pedir(monkeypatch, _pedido(), _respostas("l", "", "contadora", "1"))

    assert _redes_do_contato(conn) == [("linkedin", "https://exemplo.test/linkedin/beatriz-nunes")]


def test_opcao_c_com_link_na_mesma_linha(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch, agora_real: str
) -> None:
    _popular(conn, agora_real, [("Marcos Aguiar", "Advogado"), ("Marcos Barros", "Médico")])

    _pedir(monkeypatch, _pedido(), _respostas("c https://www.linkedin.com/in/marcos-x/?trk=1"))

    assert _redes_do_contato(conn) == [("linkedin", "https://www.linkedin.com/in/marcos-x")]


def test_link_colado_direto_no_menu_vale_como_c(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch, agora_real: str
) -> None:
    _popular(conn, agora_real, [("Marcos Aguiar", "Advogado"), ("Marcos Barros", "Médico")])

    _pedir(monkeypatch, _pedido(), _respostas("https://www.linkedin.com/in/marcos-y/"))

    assert _redes_do_contato(conn) == [("linkedin", "https://www.linkedin.com/in/marcos-y")]


def test_opcao_c_pede_o_link_depois(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch, agora_real: str
) -> None:
    _popular(conn, agora_real, [("Marcos Aguiar", "Advogado"), ("Marcos Barros", "Médico")])

    respostas = _respostas("c", "link invalido", "c", "https://www.instagram.com/marcos.x/")
    _pedir(monkeypatch, _pedido(), respostas)

    assert _redes_do_contato(conn) == [("instagram", "https://www.instagram.com/marcos.x")]


def test_opcao_p_pula_sem_gravar(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch, agora_real: str
) -> None:
    _popular(conn, agora_real, [("Marcos Aguiar", "Advogado"), ("Marcos Barros", "Médico")])

    _pedir(monkeypatch, _pedido(), _respostas("p"))

    assert _redes_do_contato(conn) == []


def test_sem_perguntar_aceita_o_claro(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch, agora_real: str
) -> None:
    _com_um_marcos(conn, agora_real)

    _pedir(monkeypatch, _pedido(pistas=PISTA), _sem_pergunta, sem_perguntar=True)

    assert len(_redes_do_contato(conn)) == 1


def test_sem_perguntar_pula_o_ambiguo(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch, agora_real: str
) -> None:
    _popular(conn, agora_real, [("Marcos Aguiar", "Advogado"), ("Marcos Barros", "Médico")])

    _pedir(monkeypatch, _pedido(), _sem_pergunta, sem_perguntar=True)

    assert _redes_do_contato(conn) == []


def test_pessoa_fora_das_listas_mostra_a_busca_geral(
    conn: sqlite3.Connection,
    monkeypatch: pytest.MonkeyPatch,
    agora_real: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _com_um_marcos(conn, agora_real)

    _pedir(monkeypatch, _pedido(nome="Zuleica"), _respostas("1"))

    saida = capsys.readouterr().out
    assert "Não achei nas suas listas." in saida
    assert _redes_do_contato(conn) == [("linkedin", f"{URL}zuleica-xavier")]


def test_repetir_o_pedido_nao_pergunta_e_trocar_perfil_reabre(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch, agora_real: str
) -> None:
    _com_um_marcos(conn, agora_real)
    _pedir(monkeypatch, _pedido(pistas=PISTA), _respostas("S"))

    perguntas: list[str] = []

    def _anota(pergunta: str) -> str:
        perguntas.append(pergunta)
        return ""

    _pedir(monkeypatch, _pedido(pistas=PISTA), _anota)  # o LinkedIn já foi aprovado: não volta a perguntar

    assert perguntas and all("link do perfil" in p for p in perguntas)  # só as redes que faltam
    _pedir(monkeypatch, _pedido(pistas=PISTA), _respostas("n", "2"), trocar_perfil=True)
    assert _redes_do_contato(conn) == [("linkedin", "https://exemplo.test/linkedin/marcos-lima")]


def _contato_id(conn: sqlite3.Connection) -> int:
    contato_id = perfis.listar_todos(conn)[0].id
    assert contato_id is not None
    return contato_id


def test_n_no_menu_declara_sem_perfil_e_o_pedido_seguinte_nao_procura_mais(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch, agora_real: str
) -> None:
    _com_um_marcos(conn, agora_real)

    _pedir(monkeypatch, _pedido(pistas=PISTA), _respostas("n", "n"))  # não é ele; não tem perfil

    assert _redes_do_contato(conn) == []
    assert "linkedin" in rede_sem_perfil.listar_redes(conn, _contato_id(conn))
    procuradas: list[str] = []
    original = localizacao_mod.localizar_rede

    def _espia(*args: Any, **kwargs: Any) -> Any:
        procuradas.append(args[5])
        return original(*args, **kwargs)

    monkeypatch.setattr(localizacao_mod, "localizar_rede", _espia)
    _pedir(monkeypatch, _pedido(pistas=PISTA), _respostas())
    assert "linkedin" not in procuradas


def test_rede_sem_resultado_aceita_n_como_sem_perfil(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch, agora_real: str
) -> None:
    _com_um_marcos(conn, agora_real)

    _pedir(monkeypatch, _pedido(pistas=PISTA), _respostas("S", "n"))  # LinkedIn ok; facebook: sem perfil

    assert rede_sem_perfil.listar_redes(conn, _contato_id(conn)) == {"facebook"}


def test_gravar_perfil_numa_rede_tira_a_declaracao_de_sem_perfil(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch, agora_real: str
) -> None:
    _com_um_marcos(conn, agora_real)
    _pedir(monkeypatch, _pedido(pistas=PISTA), _respostas("n", "n"))
    assert "linkedin" in rede_sem_perfil.listar_redes(conn, _contato_id(conn))

    _pedir(monkeypatch, _pedido(pistas=PISTA), _respostas("S"), trocar_perfil=True)

    assert "linkedin" not in rede_sem_perfil.listar_redes(conn, _contato_id(conn))
    assert [r for r, _ in _redes_do_contato(conn)] == ["linkedin"]


def test_perfil_informado_grava_direto_e_a_rede_nao_e_procurada(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch, agora_real: str
) -> None:
    _com_um_marcos(conn, agora_real)
    monkeypatch.setattr(cli, "llm", lambda: _LLM(_pedido(pistas=PISTA)))

    cli.pedir_cmd(
        "frase qualquer",
        False,
        False,
        None,
        entrada=_respostas("S"),
        abrir_pagina=_abrir_pagina,
        perfis_informados=["https://www.instagram.com/marcos.z/", "isto não é link"],
    )

    redes = dict(_redes_do_contato(conn))
    assert redes["instagram"] == "https://www.instagram.com/marcos.z"


def test_extensao_instalar_mostra_a_pasta_e_o_passo_a_passo(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.extensao_instalar_cmd() == 0

    saida = capsys.readouterr().out
    assert "extensao" in saida
    assert "chrome://extensions" in saida
    assert "Carregar sem compactação" in saida
