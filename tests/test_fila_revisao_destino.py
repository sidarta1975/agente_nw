"""Brief 087: destino da fila de revisão — ver, reenviar e descartar o que o modelo não conseguiu.

Banco isolado em `tmp_path` e cliente de LLM falso; nenhum teste abre o banco real nem o Ollama.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import TypeVar

import pytest
from pydantic import BaseModel

import agente_nw.cli as cli
from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import fila_extracao, fila_revisao
from agente_nw.nucleo.llm import FalhaJsonInvalido
from agente_nw.perfil import extrator
from tests.llm_falso import ProvenienciaFalsa

AGORA = "2026-11-16T10:00:00+00:00"
ERRO_JSON = "1 validation error for RespostaExtracaoTexto\ncampos\n  Field required"
_EsquemaT = TypeVar("_EsquemaT", bound=BaseModel)
SEGREDO = "TEXTO-DE-TERCEIROS-NAO-PODE-APARECER"


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


def _item(conn: sqlite3.Connection, tarefa: str, erro: str, criado_em: str = AGORA) -> int:
    return fila_revisao.inserir(conn, tarefa, f"prompt com {SEGREDO}", erro, criado_em)


class _ClienteFake(ProvenienciaFalsa):
    """Responde ou falha como o `ClienteOllama`: na falha, grava na fila e levanta `FalhaJsonInvalido`."""

    def __init__(self, conn: sqlite3.Connection, falhar: bool) -> None:
        self._conn = conn
        self.falhar = falhar

    def gerar_json(
        self,
        tarefa_nome: str,
        prompt: str,
        esquema: type[_EsquemaT],
        imagens: list[str] | None = None,
        versao_prompt: str | None = None,
    ) -> _EsquemaT:
        if self.falhar:
            novo = fila_revisao.inserir(self._conn, tarefa_nome, prompt, ERRO_JSON, AGORA)
            self._conn.commit()
            raise FalhaJsonInvalido(tarefa_nome, novo, ERRO_JSON)
        return esquema.model_validate({})


def _extracao_que_falhou(conn: sqlite3.Connection, cliente: _ClienteFake) -> tuple[int, int]:
    """Um item de `fila_extracao` que falhou de verdade: devolve (id na fila de extração, id na revisão)."""
    conn.execute(
        "INSERT INTO perfil (tipo, nome, linguas, criado_em, atualizado_em) "
        "VALUES ('contato', 'A', '[]', ?, ?)",
        (AGORA, AGORA),
    )
    (perfil_id,) = conn.execute("SELECT id FROM perfil").fetchone()
    extracao_id = fila_extracao.inserir(conn, perfil_id, "texto livre", "cadastro", AGORA)
    conn.commit()
    cliente.falhar = True
    extrator.processar_fila(cliente, conn)
    (revisao_id,) = conn.execute("SELECT id FROM fila_revisao").fetchone()
    return extracao_id, revisao_id


def _reprocessar(conn: sqlite3.Connection, cliente: _ClienteFake) -> fila_revisao.Reprocessar:
    return extrator.reprocessador_de_item(cliente, conn)


# 1 -----------------------------------------------------------------------------------------------


def test_listar_agrupa_por_tarefa_e_erro_ordena_por_idade_e_nao_devolve_a_entrada(
    conn: sqlite3.Connection,
) -> None:
    _item(conn, "redigir_ganchos", "HTTP 500", "2026-11-10T00:00:00+00:00")
    velho = _item(conn, "extrair_de_texto", ERRO_JSON, "2026-11-01T00:00:00+00:00")
    novo = _item(conn, "extrair_de_texto", ERRO_JSON, "2026-11-05T00:00:00+00:00")
    _item(
        conn,
        "extrair_de_texto",
        "prediction aborted, token repeat limit reached",
        "2026-11-03T00:00:00+00:00",
    )
    conn.commit()

    itens = fila_revisao.listar(conn)

    assert [i.tarefa for i in itens] == ["extrair_de_texto"] * 3 + ["redigir_ganchos"]
    json_invalido = [i.id for i in itens if i.classe_do_erro == "json_invalido"]
    assert json_invalido == [velho, novo]  # mais velho primeiro
    assert not hasattr(itens[0], "entrada")
    assert SEGREDO not in repr(itens)

    contagem = {(c.tarefa, c.classe_do_erro): c.itens for c in fila_revisao.contar(conn)}
    assert contagem[("extrair_de_texto", "json_invalido")] == 2
    assert contagem[("extrair_de_texto", "geracao_degenerada")] == 1
    assert contagem[("redigir_ganchos", "transporte")] == 1


def test_obter_devolve_a_entrada_inteira_so_quando_pedido(conn: sqlite3.Connection) -> None:
    item_id = _item(conn, "extrair_de_texto", ERRO_JSON)
    completo = fila_revisao.obter(conn, item_id)
    assert completo is not None and SEGREDO in completo.entrada
    assert fila_revisao.obter(conn, 999) is None


def test_listar_esconde_o_que_ja_foi_resolvido(conn: sqlite3.Connection) -> None:
    resolvido = _item(conn, "extrair_de_texto", ERRO_JSON)
    aberto = _item(conn, "extrair_de_texto", ERRO_JSON)
    fila_revisao.descartar(conn, resolvido, "lixo", AGORA)

    assert [i.id for i in fila_revisao.listar(conn)] == [aberto]
    assert {i.id for i in fila_revisao.listar(conn, incluir_resolvidos=True)} == {resolvido, aberto}


# 2 -----------------------------------------------------------------------------------------------


def test_descartar_marca_resolvido_data_e_motivo_e_recusa_a_segunda_vez(conn: sqlite3.Connection) -> None:
    item_id = _item(conn, "extrair_de_texto", ERRO_JSON)

    fila_revisao.descartar(conn, item_id, "texto sem aproveitamento", AGORA)

    item = fila_revisao.obter(conn, item_id)
    assert item is not None
    assert (item.resolvido, item.resolvido_em, item.resolucao, item.motivo) == (
        True,
        AGORA,
        "descartado",
        "texto sem aproveitamento",
    )
    with pytest.raises(fila_revisao.ItemJaResolvido):
        fila_revisao.descartar(conn, item_id, "de novo", AGORA)
    reobtido = fila_revisao.obter(conn, item_id)
    assert reobtido is not None and reobtido.motivo == "texto sem aproveitamento"


def test_descartar_exige_motivo_e_item_existente(conn: sqlite3.Connection) -> None:
    item_id = _item(conn, "extrair_de_texto", ERRO_JSON)
    with pytest.raises(ValueError):
        fila_revisao.descartar(conn, item_id, "   ", AGORA)
    with pytest.raises(fila_revisao.ItemInexistente):
        fila_revisao.descartar(conn, 999, "x", AGORA)


# 3 -----------------------------------------------------------------------------------------------


def test_reenviar_com_resultado_valido_marca_reenviado_ok(conn: sqlite3.Connection) -> None:
    cliente = _ClienteFake(conn, falhar=True)
    extracao_id, revisao_id = _extracao_que_falhou(conn, cliente)
    cliente.falhar = False

    desfecho = fila_revisao.reenviar(conn, revisao_id, AGORA, _reprocessar(conn, cliente))

    assert desfecho == "reenviado_ok"
    item = fila_revisao.obter(conn, revisao_id)
    assert item is not None and item.resolvido is True and item.resolucao == "reenviado_ok"
    assert item.resolvido_em == AGORA
    (processado, erro) = conn.execute(
        "SELECT processado, erro FROM fila_extracao WHERE id = ?", (extracao_id,)
    ).fetchone()
    assert (processado, erro) == (1, None)


def test_reenviar_com_novo_erro_mantem_o_item_na_fila_sem_duplicar(conn: sqlite3.Connection) -> None:
    cliente = _ClienteFake(conn, falhar=True)
    extracao_id, revisao_id = _extracao_que_falhou(conn, cliente)

    desfecho = fila_revisao.reenviar(conn, revisao_id, AGORA, _reprocessar(conn, cliente))

    assert desfecho == "reenviado_falhou"
    item = fila_revisao.obter(conn, revisao_id)
    assert item is not None and item.resolvido is False and item.resolucao == "reenviado_falhou"
    (total,) = conn.execute("SELECT COUNT(*) FROM fila_revisao").fetchone()
    assert total == 1  # a falha do reenvio não abriu outra linha
    # o vínculo continua achando a linha: dá para reenviar de novo
    (erro,) = conn.execute("SELECT erro FROM fila_extracao WHERE id = ?", (extracao_id,)).fetchone()
    assert f"(fila_revisao id={revisao_id})" in erro

    cliente.falhar = False
    assert fila_revisao.reenviar(conn, revisao_id, AGORA, _reprocessar(conn, cliente)) == "reenviado_ok"


def test_reenviar_item_ja_resolvido_e_recusado(conn: sqlite3.Connection) -> None:
    cliente = _ClienteFake(conn, falhar=True)
    _, revisao_id = _extracao_que_falhou(conn, cliente)
    fila_revisao.descartar(conn, revisao_id, "x", AGORA)
    with pytest.raises(fila_revisao.ItemJaResolvido):
        fila_revisao.reenviar(conn, revisao_id, AGORA, _reprocessar(conn, cliente))


def test_reenviar_extracao_sem_linha_de_origem_diz_que_nao_ha_de_onde_reenviar(
    conn: sqlite3.Connection,
) -> None:
    item_id = _item(conn, "extrair_de_texto", ERRO_JSON)  # antigo: nenhuma fila_extracao aponta para ele
    cliente = _ClienteFake(conn, falhar=False)
    with pytest.raises(fila_revisao.SemCaminhoDeRepeticao):
        fila_revisao.reenviar(conn, item_id, AGORA, _reprocessar(conn, cliente))
    item = fila_revisao.obter(conn, item_id)
    assert item is not None and item.resolvido is False and item.resolucao is None


# 4 -----------------------------------------------------------------------------------------------


@pytest.mark.parametrize("tarefa", ["redigir_ganchos", "extrair_pedido", "qualquer_outra"])
def test_tarefa_sem_caminho_de_repeticao_diz_isso_e_nada_muda(conn: sqlite3.Connection, tarefa: str) -> None:
    item_id = _item(conn, tarefa, "HTTP 500")
    chamadas: list[int] = []

    with pytest.raises(fila_revisao.SemCaminhoDeRepeticao, match=tarefa):
        fila_revisao.reenviar(conn, item_id, AGORA, lambda n: chamadas.append(n))

    assert chamadas == []
    item = fila_revisao.obter(conn, item_id)
    assert item is not None
    assert (item.resolvido, item.resolucao, item.resolvido_em, item.motivo) == (False, None, None, None)


# 5 -----------------------------------------------------------------------------------------------


def test_migracao_aplica_em_banco_com_itens_antigos_sem_perder_linha(tmp_path: Path) -> None:
    antigas = tmp_path / "migracoes_ate_019"
    antigas.mkdir()
    for arquivo in migracoes.PASTA_MIGRACOES_PADRAO.glob("*.sql"):
        if int(arquivo.name.split("_", 1)[0]) <= 19:
            (antigas / arquivo.name).write_text(arquivo.read_text(encoding="utf-8"), encoding="utf-8")
    banco = conexao.abrir(tmp_path / "antigo.db")
    migracoes.aplicar(banco, antigas)
    for n in range(3):
        banco.execute(
            "INSERT INTO fila_revisao (tarefa, entrada, erro, criado_em, resolvido) VALUES (?, ?, ?, ?, 0)",
            ("extrair_de_texto", f"entrada {n}", "erro", AGORA),
        )
    banco.commit()

    assert migracoes.aplicar(banco) >= 1

    linhas = banco.execute(
        "SELECT entrada, resolvido, resolvido_em, resolucao, motivo FROM fila_revisao ORDER BY id"
    ).fetchall()
    assert len(linhas) == 3
    assert [tuple(linha) for linha in linhas] == [(f"entrada {n}", 0, None, None, None) for n in range(3)]


# 6 -----------------------------------------------------------------------------------------------


def _banco_do_teste(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Aponta o comando para um banco em `tmp_path` pelo mesmo caminho que ele usa em produção
    (`cli.banco()`, que sai de `config`); abrir o real derruba o teste."""
    caminho = tmp_path / "cli.db"
    monkeypatch.setattr(cli, "caminho_banco", lambda: caminho)
    monkeypatch.setattr(cli, "banco", lambda: _abrir(caminho))
    return caminho


def _abrir(caminho: Path) -> sqlite3.Connection:
    aberta = conexao.abrir(caminho)
    migracoes.aplicar(aberta)
    return aberta


def test_comando_ver_usa_o_banco_de_config_nao_mostra_a_entrada_e_inteiro_mostra(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    caminho = _banco_do_teste(tmp_path, monkeypatch)
    banco = _abrir(caminho)
    item_id = _item(banco, "extrair_de_texto", ERRO_JSON)
    banco.commit()
    banco.close()

    assert cli.main(["revisao", "ver"]) == 0
    saida = capsys.readouterr().out
    assert "extrair_de_texto" in saida and "json_invalido" in saida and str(item_id) in saida
    assert SEGREDO not in saida

    assert cli.main(["revisao", "ver", "--inteiro", str(item_id)]) == 0
    assert SEGREDO in capsys.readouterr().out


def test_comando_descartar_e_reenviar_pela_cli(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    caminho = _banco_do_teste(tmp_path, monkeypatch)
    banco = _abrir(caminho)
    sem_caminho = _item(banco, "redigir_ganchos", "HTTP 500")
    a_descartar = _item(banco, "extrair_de_texto", ERRO_JSON)
    banco.commit()
    banco.close()

    assert cli.main(["revisao", "reenviar", str(sem_caminho)]) == 1
    assert "redigir_ganchos" in capsys.readouterr().out

    assert cli.main(["revisao", "descartar", str(a_descartar), "--motivo", "sem valor"]) == 0
    assert cli.main(["revisao", "descartar", str(a_descartar), "--motivo", "sem valor"]) == 1
    assert "já foi resolvido" in capsys.readouterr().out


def test_ver_aceita_banco_explicito_e_nao_abre_o_de_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def _proibido() -> sqlite3.Connection:
        raise AssertionError("abriu o banco de config")

    monkeypatch.setattr(cli, "banco", _proibido)
    copia = tmp_path / "copia.db"
    banco = _abrir(copia)
    _item(banco, "extrair_de_texto", ERRO_JSON)
    banco.commit()
    banco.close()

    assert cli.main(["revisao", "ver", "--banco", str(copia)]) == 0
    assert "extrair_de_texto" in capsys.readouterr().out


def test_ajuda_mostra_os_tres_subcomandos(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as saida:
        cli.main(["revisao", "--help"])
    assert saida.value.code == 0
    texto = capsys.readouterr().out
    assert all(nome in texto for nome in ("ver", "descartar", "reenviar"))


# console -----------------------------------------------------------------------------------------


def test_tela_do_console_lista_sem_a_entrada_e_descarta(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import agente_nw.console.app as console_app
    from tests.test_console_contatos import _limiares

    caminho = tmp_path / "console.db"
    banco = _abrir(caminho)
    item_id = _item(banco, "extrair_de_texto", ERRO_JSON)
    banco.commit()
    banco.close()
    app = console_app.criar_app(caminho, tmp_path / "log.jsonl", object(), _limiares(), "http://unused")  # type: ignore[arg-type]
    client = app.test_client()

    pagina = client.get("/revisao").get_data(as_text=True)
    assert "extrair_de_texto" in pagina and "json_invalido" in pagina and "Reenviar" in pagina
    assert SEGREDO not in pagina

    client.post(f"/revisao/{item_id}/descartar", data={"motivo": "sem valor"})
    verificacao = _abrir(caminho)
    item = fila_revisao.obter(verificacao, item_id)
    assert item is not None and item.resolucao == "descartado" and item.motivo == "sem valor"
    assert "Nada esperando revisão" in client.get("/revisao").get_data(as_text=True)
