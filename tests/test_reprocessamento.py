"""Brief 095: dano nos dados já gravados e reprocessamento.

`medir-dano` conta, numa cópia do banco e sem gravar, o que foi produzido pelo critério antigo (texto
cortado); `reprocessar` calcula o resultado novo num arquivo à parte (simulação, o padrão) e só grava no
banco com `--confirmo`, nunca dentro de uma série nem no banco real sem autorização escrita no PLAN.
Banco em `tmp_path`, embedding e LLM falsos."""

from __future__ import annotations

import hashlib
import random
import sqlite3
from pathlib import Path

import pytest

from agente_nw import cli
from agente_nw.manutencao import reprocessamento
from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import assuntos, fatos, fontes, itens, perfis, temas
from agente_nw.nucleo.llm import identificador_do_vetor
from agente_nw.nucleo.modelos.assunto import Assunto
from agente_nw.nucleo.modelos.cartao import RespostaCartao
from agente_nw.nucleo.modelos.fato import Fato
from agente_nw.nucleo.modelos.item import Item
from agente_nw.nucleo.modelos.proveniencia import Proveniencia
from agente_nw.nucleo.prompts import cartao as prompt_cartao
from agente_nw.nucleo.prompts import extrair_de_texto, redigir_ganchos
from config.container import caminho_banco
from tests.llm_falso import ProvenienciaFalsa

AGORA = "2026-11-16T10:00:00+00:00"
TERCEIRO = "SEGREDO-DE-TERCEIRO"
"""Marca posta em todo texto de terceiros do banco sintético: não pode aparecer em saída nenhuma."""

IDENTIFICADOR_NOVO = identificador_do_vetor("bge-m3")
CARTAO_ANTIGO = f"Cartão antigo, feito de cinco itens cortados. {TERCEIRO}"
CARTAO_NOVO = "Cartão novo, feito com o resumo de todos os itens."


def _abrir(caminho: Path) -> sqlite3.Connection:
    conn = conexao.abrir(caminho)
    migracoes.aplicar(conn)
    return conn


def _sha256(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def _vetor_do_texto(texto: str) -> list[float]:
    gerador = random.Random(texto)
    return [gerador.uniform(-1.0, 1.0) for _ in range(1024)]


def _texto(caracteres: int) -> str:
    bloco = f"O conselho aprovou o plano do porto e {TERCEIRO} comentou a votação. "
    return (bloco * (caracteres // len(bloco) + 1))[:caracteres]


class _Embeddador:
    """Embedding falso, já com o identificador do critério novo (como o `ClienteOllama`)."""

    modelo_embedding = IDENTIFICADOR_NOVO

    def __init__(self) -> None:
        self.chamadas = 0

    def embeddar(self, textos: list[str]) -> list[list[float]]:
        self.chamadas += 1
        return [_vetor_do_texto(texto) for texto in textos]


class _ClienteCartao(ProvenienciaFalsa):
    def __init__(self) -> None:
        self.chamadas = 0

    def gerar_json(
        self,
        tarefa_nome: str,
        prompt: str,
        esquema: type[RespostaCartao],
        *,
        versao_prompt: str | None = None,
    ) -> RespostaCartao:
        self.chamadas += 1
        return RespostaCartao(resumo=CARTAO_NOVO)


class _Falha:
    """Cliente que não pode ser chamado: a recusa vem antes de qualquer modelo."""

    modelo_embedding = IDENTIFICADOR_NOVO

    def __getattr__(self, nome: str) -> object:
        pytest.fail(f"o cliente não podia ser usado ({nome})")


def _item(conn: sqlite3.Connection, fonte_id: int, nome: str, texto: str | None) -> int:
    item_id = itens.inserir(
        conn,
        Item(
            fonte_id=fonte_id,
            url_canonica=f"https://exemplo.com/{nome}",
            titulo=f"{nome} {TERCEIRO}",
            texto=texto,
            publicado_em=AGORA,
            coletado_em=AGORA,
            hash_titulo=f"hash-{nome}",
        ),
    )
    assert item_id is not None
    return item_id


def _assunto(conn: sqlite3.Connection) -> int:
    return assuntos.inserir(
        conn,
        Assunto(
            titulo_gerado=f"Assunto {TERCEIRO}",
            primeiro_visto=AGORA,
            ultimo_visto=AGORA,
            n_itens=1,
            n_fontes_independentes=1,
            status="novo",
        ),
    )


def _banco_sintetico(caminho: Path) -> None:
    """Itens, cartões, ganchos, fatos, vetores e fila de revisão de versões diferentes.

    - itens: 100, 500 e 3.000 caracteres, mais um só com manchete. O de 100 tem resumo da versão atual,
      o de 3.000 tem resumo de outra versão, o de 500 não tem resumo;
    - assunto 1: cartão antigo (sem versão nem cobertura), itens de 100 e 3.000, centróide `bge-m3`;
    - assunto 2: cartão novo (versão atual, cobertura 1), item de 500, centróide do critério novo;
    - tema com vetor antigo; contato com centróide antigo; fato sem proveniência, fato de prompt antigo e
      fato da versão atual;
    - ganchos: um sem versão, um de prompt antigo, um da versão atual (este no assunto 2);
    - fila_extracao: um processado sem registro de partes, um com; fila_revisao: duas pendentes de
      `cartao`, uma de `extrair_de_texto`, uma resolvida."""
    conn = _abrir(caminho)
    fonte = fontes.obter_ou_criar(conn, "g1.globo.com", "https://g1.globo.com/rss", "g1", "rss", 5)
    assert fonte.id is not None

    curto = _item(conn, fonte.id, "curto", _texto(100))
    medio = _item(conn, fonte.id, "medio", _texto(500))
    longo = _item(conn, fonte.id, "longo", _texto(3_000))
    _item(conn, fonte.id, "manchete", None)
    conn.execute(
        "UPDATE item SET resumo = ?, resumo_versao = ?, resumo_partes = 0 WHERE id = ?",
        (_texto(100), prompt_cartao.VERSAO_RESUMO_ITEM, curto),
    )
    conn.execute(
        "UPDATE item SET resumo = ?, resumo_versao = 'resumo-item-antigo', resumo_partes = 1 WHERE id = ?",
        (f"resumo antigo {TERCEIRO}", longo),
    )

    antigo = _assunto(conn)
    novo = _assunto(conn)
    for item_id, assunto_id in ((curto, antigo), (longo, antigo), (medio, novo)):
        itens.vincular_assunto(conn, item_id, assunto_id)
        itens.gravar_embedding(conn, item_id, _vetor_do_texto(f"antigo-{item_id}"))
    assuntos.gravar_cartao(conn, antigo, CARTAO_ANTIGO)
    assuntos.gravar_cartao(
        conn,
        novo,
        f"Cartão já do critério novo. {TERCEIRO}",
        Proveniencia(modelo="m", perfil="pro48", prompt_versao=prompt_cartao.VERSAO),
        itens_cobertos=1,
        niveis=1,
    )
    assuntos.gravar_centroide(conn, antigo, _vetor_do_texto(f"antigo-{curto}"), "bge-m3")
    assuntos.gravar_centroide(conn, novo, _vetor_do_texto(f"antigo-{medio}"), IDENTIFICADOR_NOVO)

    tema = temas.obter_ou_criar(conn, f"Portos {TERCEIRO}", "infraestrutura portuária", [], AGORA)
    assert tema.id is not None
    temas.gravar_embedding(conn, tema.id, _vetor_do_texto("tema"), "bge-m3")

    contato = perfis.inserir_novo_contato(conn, f"João {TERCEIRO}", None, None, AGORA)
    assert contato.id is not None
    perfis.gravar_centroide(conn, contato.id, _vetor_do_texto("contato"), "bge-m3")
    for versao in (None, "2026-10-31-1", extrair_de_texto.VERSAO):
        fatos.inserir(
            conn,
            Fato(
                perfil_id=contato.id,
                tipo="publicacao",
                conteudo=f"fato {versao} {TERCEIRO}",
                registrado_em=AGORA,
            ),
            Proveniencia(modelo="m", perfil="pro48", prompt_versao=versao) if versao else None,
        )

    conn.execute(
        "INSERT INTO consulta_contato (perfil_id, criado_em, contexto_json, assuntos_entregues_json) "
        "VALUES (?, ?, ?, '[]')",
        (contato.id, AGORA, f'{{"objetivo": "{TERCEIRO}"}}'),
    )
    consulta_id = conn.execute("SELECT MAX(id) FROM consulta_contato").fetchone()[0]
    ganchos: tuple[tuple[int | None, str | None], ...] = (
        (None, None),
        (antigo, "2026-11-02-1"),
        (novo, redigir_ganchos.VERSAO),
    )
    for assunto_do_gancho, versao in ganchos:
        conn.execute(
            "INSERT INTO gancho_uso (consulta_id, assunto_id, status, gancho_json, atualizado_em, "
            "gerado_por_prompt_versao) VALUES (?, ?, 'entregue', ?, ?, ?)",
            (consulta_id, assunto_do_gancho, f'{{"texto": "{TERCEIRO}"}}', AGORA, versao),
        )

    for partes in (None, 1):
        conn.execute(
            "INSERT INTO fila_extracao (perfil_id, texto, origem, criado_em, processado, partes_lidas) "
            "VALUES (?, ?, 'colado', ?, 1, ?)",
            (contato.id, f"texto colado {TERCEIRO}", AGORA, partes),
        )
    for tarefa, resolvido in (("cartao", 0), ("cartao", 0), ("extrair_de_texto", 0), ("rotular", 1)):
        conn.execute(
            "INSERT INTO fila_revisao (tarefa, entrada, erro, criado_em, resolvido) VALUES (?, ?, ?, ?, ?)",
            (tarefa, f"entrada {TERCEIRO}", f"erro {TERCEIRO}", AGORA, resolvido),
        )
    conn.commit()
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    conn.close()


@pytest.fixture
def copia(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A cópia do banco; o "banco real" e o PLAN do CLI apontam para `tmp_path`, e nenhuma série."""
    caminho = tmp_path / "copia" / "copia.db"
    caminho.parent.mkdir()
    _banco_sintetico(caminho)
    monkeypatch.setattr(cli, "caminho_banco", lambda: tmp_path / "real" / "agente.db")
    plan = tmp_path / "PLAN_agente_nw.md"
    plan.write_text("# PLAN\n\nNada autorizado.\n", encoding="utf-8")
    monkeypatch.setattr(cli, "caminho_plan", lambda: plan)
    monkeypatch.delenv(reprocessamento.VARIAVEL_DA_SERIE, raising=False)
    return caminho


# --- 1. medir-dano conta certo -----------------------------------------------------------------------


def test_medir_dano_conta_o_que_veio_de_cada_versao(copia: Path) -> None:
    conn = reprocessamento.abrir_somente_leitura(copia)
    try:
        dano = reprocessamento.medir_dano(conn, IDENTIFICADOR_NOVO)
    finally:
        conn.close()

    assert dano.itens == 4
    assert dano.itens_com_corpo == 3
    assert dano.itens_acima_do_corte_do_vetor == 1
    assert dano.itens_acima_do_corte_do_cartao == 2
    assert dano.itens_sem_resumo_da_versao_atual == 2
    assert dano.vetores_de_item_sem_versao == 3
    assert dict((t, (o, n)) for t, o, n in dano.vetores_do_criterio_anterior) == {
        "vetor_tema": (1, 1),
        "vetor_assunto": (1, 2),
        "vetor_perfil": (1, 1),
    }
    assert dano.cartoes == 2
    assert dano.cartoes_de_versao_antiga == 1
    assert dano.cartoes_sem_cobertura == 1
    assert dano.ganchos == 3
    assert dano.ganchos_de_versao_antiga == 2
    assert dano.ganchos_em_assunto_de_cartao_antigo == 1
    assert dano.fatos == 3
    assert dano.fatos_de_versao_antiga == 2
    assert dict(dano.fatos_por_versao) == {None: 1, "2026-10-31-1": 1, extrair_de_texto.VERSAO: 1}
    assert dano.extracoes_sem_registro_de_partes == 1
    assert dano.fila_revisao_pendente == 3
    assert dict(dano.fila_revisao_por_tarefa) == {"cartao": 2, "extrair_de_texto": 1}


# --- 2. saída sem texto de terceiros; o banco não muda -----------------------------------------------


def test_medir_dano_no_cli_so_conta_e_nao_altera_o_banco(
    copia: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    hash_antes = _sha256(copia)

    codigo = cli.main(["medir-dano", "--banco", str(copia)])

    saida = capsys.readouterr().out
    assert codigo == 0
    assert TERCEIRO not in saida
    assert "Fonte" not in saida and "João" not in saida and "Portos" not in saida
    assert _sha256(copia) == hash_antes
    assert f"sha256 antes: {hash_antes}" in saida
    assert f"sha256 depois: {hash_antes}" in saida
    assert "Itens com texto acima de 2000 caracteres (corte antigo do vetor do item): 1" in saida
    assert "Cartões de versão antiga: 1" in saida
    assert "Fila de revisão pendente: 3" in saida


def test_reprocessar_simulado_nao_mostra_texto_de_terceiros(
    copia: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli, "_cliente_do_reprocessamento", lambda conn: _ClienteCartao())

    codigo = cli.main(["reprocessar", "--banco", str(copia), "--etapa", "cartoes", "--simular"])

    assert codigo == 0
    assert TERCEIRO not in capsys.readouterr().out


# --- 3. reprocessar em simulação não altera o banco ----------------------------------------------------


def test_reprocessar_vetores_em_simulacao_grava_a_parte_e_nao_altera_o_banco(
    copia: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    hash_antes = _sha256(copia)
    cliente = _Embeddador()
    monkeypatch.setattr(cli, "_cliente_do_reprocessamento", lambda conn: cliente)
    saida_simulacao = copia.parent / "simulacao.db"

    codigo = cli.main(
        ["reprocessar", "--banco", str(copia), "--etapa", "vetores", "--saida", str(saida_simulacao)]
    )

    saida = capsys.readouterr().out
    assert codigo == 0
    assert _sha256(copia) == hash_antes
    assert cliente.chamadas >= 4  # 3 itens e 1 tema
    assert "Itens com vetor novo: 3 de 3" in saida
    assert "Itens que trocariam de assunto:" in saida
    assert "Ganchos em assunto que mudaria:" in saida
    assert f"Simulação gravada em {saida_simulacao}" in saida

    simulado = reprocessamento.abrir_somente_leitura(saida_simulacao)
    try:
        assunto_ids = {
            int(linha[0])
            for linha in simulado.execute(
                "SELECT assunto_id FROM vetor_assunto WHERE modelo_embedding = ?", (IDENTIFICADOR_NOVO,)
            )
        }
        (temas_novos,) = simulado.execute(
            "SELECT COUNT(*) FROM vetor_tema WHERE modelo_embedding = ?", (IDENTIFICADOR_NOVO,)
        ).fetchone()
    finally:
        simulado.close()
    assert len(assunto_ids) == 2
    assert temas_novos == 1


def test_reprocessar_cartoes_em_simulacao_grava_a_parte_e_nao_altera_o_banco(
    copia: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    hash_antes = _sha256(copia)
    cliente = _ClienteCartao()
    monkeypatch.setattr(cli, "_cliente_do_reprocessamento", lambda conn: cliente)

    codigo = cli.main(["reprocessar", "--banco", str(copia), "--etapa", "cartoes", "--simular"])

    saida = capsys.readouterr().out
    assert codigo == 0
    assert _sha256(copia) == hash_antes
    assert "Cartões de versão antiga: 1" in saida
    assert "Cartões regravados: 1" in saida
    assert "Cartões que mudariam: 1" in saida
    assert "Ganchos em assunto que mudaria: 1" in saida

    arquivos = sorted(copia.parent.glob("copia.simulacao-cartoes-*.db"))
    assert len(arquivos) == 1
    simulado = reprocessamento.abrir_somente_leitura(arquivos[0])
    try:
        linhas = simulado.execute("SELECT resumo_cartao, cartao_versao FROM assunto ORDER BY id").fetchall()
    finally:
        simulado.close()
    assert linhas[0]["resumo_cartao"] == CARTAO_NOVO
    assert linhas[0]["cartao_versao"] == prompt_cartao.VERSAO

    original = reprocessamento.abrir_somente_leitura(copia)
    try:
        (cartao,) = original.execute("SELECT resumo_cartao FROM assunto ORDER BY id").fetchone()
    finally:
        original.close()
    assert cartao == CARTAO_ANTIGO


def test_simular_e_confirmo_juntos_sao_recusados(copia: Path, capsys: pytest.CaptureFixture[str]) -> None:
    hash_antes = _sha256(copia)

    codigo = cli.main(["reprocessar", "--banco", str(copia), "--etapa", "cartoes", "--simular", "--confirmo"])

    assert codigo == 1
    assert "FALHA" in capsys.readouterr().out
    assert _sha256(copia) == hash_antes


# --- 4. --confirmo dentro de uma série é recusado ------------------------------------------------------


def test_confirmo_dentro_de_uma_serie_e_recusado(
    copia: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    hash_antes = _sha256(copia)
    monkeypatch.setenv(reprocessamento.VARIAVEL_DA_SERIE, "1")
    monkeypatch.setattr(cli, "_cliente_do_reprocessamento", lambda conn: _Falha())

    codigo = cli.main(["reprocessar", "--banco", str(copia), "--etapa", "cartoes", "--confirmo"])

    assert codigo == 1
    assert "série" in capsys.readouterr().out
    assert _sha256(copia) == hash_antes


# --- 5. --confirmo no banco real sem autorização no PLAN é recusado ------------------------------------


def _banco_real(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    real = tmp_path / "real" / "agente.db"
    real.parent.mkdir()
    _banco_sintetico(real)
    monkeypatch.setattr(cli, "caminho_banco", lambda: real)
    return real


def test_confirmo_no_banco_real_sem_autorizacao_no_plan_e_recusado(
    copia: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    real = _banco_real(tmp_path, monkeypatch)
    cli.caminho_plan().write_text(
        "- reprocessar vetores: autorizado por Sidarta em 2026-11-20\n"  # outra etapa não vale
        "- reprocessar cartoes: a decidir\n",
        encoding="utf-8",
    )
    hash_antes = _sha256(real)
    monkeypatch.setattr(cli, "_cliente_do_reprocessamento", lambda conn: _Falha())

    codigo = cli.main(["reprocessar", "--banco", str(real), "--etapa", "cartoes", "--confirmo"])

    assert codigo == 1
    assert "autorizado por Sidarta em AAAA-MM-DD" in capsys.readouterr().out
    assert _sha256(real) == hash_antes


def test_confirmo_no_banco_real_com_autorizacao_da_etapa_grava(
    copia: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    real = _banco_real(tmp_path, monkeypatch)
    cli.caminho_plan().write_text(
        "- reprocessar cartoes: autorizado por Sidarta em 2026-11-20\n", encoding="utf-8"
    )
    monkeypatch.setattr(cli, "_cliente_do_reprocessamento", lambda conn: _ClienteCartao())

    codigo = cli.main(["reprocessar", "--banco", str(real), "--etapa", "cartoes", "--confirmo"])

    saida = capsys.readouterr().out
    assert codigo == 0, saida
    assert "Cópia de segurança antes de gravar:" in saida
    assert len(list(real.parent.glob("agente.antes-do-reprocessar-cartoes-*.db"))) == 1
    conn = reprocessamento.abrir_somente_leitura(real)
    try:
        (cartao,) = conn.execute("SELECT resumo_cartao FROM assunto ORDER BY id").fetchone()
    finally:
        conn.close()
    assert cartao == CARTAO_NOVO


def test_confirmo_numa_copia_grava_sem_autorizacao_no_plan(
    copia: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli, "_cliente_do_reprocessamento", lambda conn: _ClienteCartao())

    codigo = cli.main(["reprocessar", "--banco", str(copia), "--etapa", "cartoes", "--confirmo"])

    assert codigo == 0, capsys.readouterr().out
    conn = reprocessamento.abrir_somente_leitura(copia)
    try:
        (cartao,) = conn.execute("SELECT resumo_cartao FROM assunto ORDER BY id").fetchone()
    finally:
        conn.close()
    assert cartao == CARTAO_NOVO


# --- 6. o banco real (caminho de config) é recusado nos testes -----------------------------------------


def test_banco_real_de_config_e_recusado_sem_ser_aberto(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Sem trocar o `caminho_banco` do CLI: o caminho é o da configuração, e o arquivo nem é aberto."""
    real = caminho_banco()
    monkeypatch.delenv(reprocessamento.VARIAVEL_DA_SERIE, raising=False)
    monkeypatch.setattr(
        reprocessamento, "abrir_somente_leitura", lambda caminho: pytest.fail("abriu o banco real")
    )
    monkeypatch.setattr(cli, "_cliente_do_reprocessamento", lambda conn: _Falha())

    assert cli.main(["medir-dano", "--banco", str(real)]) == 1
    assert "banco real" in capsys.readouterr().out
    assert cli.main(["reprocessar", "--banco", str(real), "--etapa", "vetores", "--simular"]) == 1
    assert "banco real" in capsys.readouterr().out
    torto = real.parent / ".." / real.parent.name / real.name
    assert cli.main(["medir-dano", "--banco", str(torto)]) == 1


def test_banco_e_obrigatorio() -> None:
    with pytest.raises(SystemExit):
        cli.main(["medir-dano"])
    with pytest.raises(SystemExit):
        cli.main(["reprocessar", "--etapa", "vetores"])
