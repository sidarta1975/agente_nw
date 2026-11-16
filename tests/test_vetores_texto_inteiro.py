"""Vetores calculados com o texto inteiro (brief 089): o vetor do item no agrupador, o centróide do contato
e o vetor do tema passam por `embeddar_em_partes` (brief 088), sem corte; o critério novo ganha versão
nova pelo mecanismo do brief 066 (vetor de versão antiga é ausente para quem pede o atual, e a linha
fica); `comparar-vetores` mede, numa cópia do banco e sem gravar, quantos itens mudariam de assunto."""

from __future__ import annotations

import hashlib
import json
import math
import random
import sqlite3
from pathlib import Path
from typing import Any

import httpx
import pytest
import yaml

from agente_nw import cli
from agente_nw.nucleo.agrupamento import agrupador
from agente_nw.nucleo.agrupamento import comparar_vetores as comparacao
from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import assuntos, fatos, fontes, itens, perfis, temas
from agente_nw.nucleo.llm import VERSAO_CRITERIO_VETOR, ClienteOllama, identificador_do_vetor
from agente_nw.nucleo.modelos.assunto import Assunto
from agente_nw.nucleo.modelos.configuracao import Roteamento, TemaUsuario
from agente_nw.nucleo.modelos.fato import Fato
from agente_nw.nucleo.modelos.item import Item
from agente_nw.perfil import configurador
from tests.llm_falso import MODELO_EMBEDDING, ProvenienciaFalsa
from tests.test_agrupador import _ClienteFake
from tests.test_agrupador import limiares as _fixture_limiares  # noqa: F401 — fixture reaproveitada

RAIZ = Path(__file__).resolve().parent.parent
AGORA = "2026-11-16T10:00:00+00:00"
MARCADOR = "Ω"

limiares = _fixture_limiares


def _abrir(caminho: Path) -> sqlite3.Connection:
    conn = conexao.abrir(caminho)
    migracoes.aplicar(conn)
    return conn


def _vetor_do_texto(texto: str) -> list[float]:
    """Um vetor de 1024 posições por texto, sempre o mesmo para o mesmo texto (armadilha 28)."""
    gerador = random.Random(texto)
    return [gerador.uniform(-1.0, 1.0) for _ in range(1024)]


def _angulo(graus: float) -> list[float]:
    radianos = math.radians(graus)
    return [math.cos(radianos), math.sin(radianos)] + [0.0] * 1022


class _Embeddador(ProvenienciaFalsa):
    """Registra cada chamada; com `falhar_com`, a chamada cujo texto contém essa marca falha."""

    def __init__(self, falhar_com: str | None = None) -> None:
        self.chamadas: list[list[str]] = []
        self._falhar_com = falhar_com

    def embeddar(self, textos: list[str]) -> list[list[float]]:
        self.chamadas.append(list(textos))
        if self._falhar_com is not None and any(self._falhar_com in texto for texto in textos):
            raise ValueError("embedding com 3 posições, esperado 1024")
        return [_vetor_do_texto(texto) for texto in textos]

    def textos(self) -> list[str]:
        return [texto for chamada in self.chamadas for texto in chamada]


def _fonte(conn: sqlite3.Connection, dominio: str = "g1.globo.com") -> int:
    fonte = fontes.obter_ou_criar(conn, dominio, f"https://{dominio}/rss", dominio, "rss", 5)
    assert fonte.id is not None
    return fonte.id


def _item(conn: sqlite3.Connection, fonte_id: int, titulo: str, texto: str | None) -> int:
    item_id = itens.inserir(
        conn,
        Item(
            fonte_id=fonte_id,
            url_canonica=f"https://exemplo.com/{titulo}",
            titulo=titulo,
            texto=texto,
            publicado_em=AGORA,
            coletado_em=AGORA,
            hash_titulo=f"hash-{titulo}",
        ),
    )
    assert item_id is not None
    return item_id


def _texto_longo(caracteres: int, final: str = "") -> str:
    """Texto com palavras e parágrafos, de exatamente `caracteres` caracteres, terminado por `final`."""
    bloco = "A comissão aprovou o relatório final sobre a reforma do porto. "
    corpo = (bloco * (caracteres // len(bloco) + 1))[: caracteres - len(final)]
    return corpo + final


def _contato(conn: sqlite3.Connection) -> int:
    contato = perfis.inserir_novo_contato(conn, "João", None, None, AGORA)
    assert contato.id is not None
    return contato.id


def _fato(conn: sqlite3.Connection, perfil_id: int, conteudo: str, data: str) -> None:
    fatos.inserir(
        conn,
        Fato(
            perfil_id=perfil_id, data_do_fato=data, tipo="publicacao", conteudo=conteudo, registrado_em=AGORA
        ),
    )


def _roteamento() -> Roteamento:
    dados: dict[str, Any] = yaml.safe_load((RAIZ / "config" / "llm_routing.yaml").read_text(encoding="utf-8"))
    return Roteamento.model_validate(dados)


def _cliente_ollama(conn: sqlite3.Connection, tmp_path: Path) -> ClienteOllama:
    def handler(request: httpx.Request) -> httpx.Response:
        corpo = json.loads(request.content)
        return httpx.Response(200, json={"embeddings": [_vetor_do_texto(t) for t in corpo["input"]]})

    return ClienteOllama(
        httpx.Client(transport=httpx.MockTransport(handler)),
        conn,
        _roteamento(),
        "http://ollama.invalido",
        tmp_path / "log.jsonl",
    )


def _sha256(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


# --- 1. texto curto: o mesmo vetor de antes ---------------------------------------------------------


def test_item_curto_e_embeddado_com_o_mesmo_texto_e_o_mesmo_vetor_de_antes(
    tmp_path: Path, limiares: Any
) -> None:
    conn = _abrir(tmp_path / "teste.db")
    fonte_id = _fonte(conn)
    texto = "O porto de Santos bateu recorde de movimentação em outubro."
    item_id = _item(conn, fonte_id, "Recorde em Santos", texto)
    so_titulo_id = _item(conn, fonte_id, "Só manchete", None)
    conn.commit()
    cliente = _Embeddador()

    agrupador.agrupar(cliente, conn, limiares, tmp_path / "PARE", data_referencia=AGORA)

    antes = f"Recorde em Santos\n\n{texto}"  # o texto de antes: título, linha em branco, corpo (< 2.000)
    assert cliente.chamadas == [[antes], ["Só manchete"]]
    assert itens.obter_embedding(conn, item_id) == pytest.approx(_vetor_do_texto(antes), abs=1e-6)
    assert itens.obter_embedding(conn, so_titulo_id) == pytest.approx(
        _vetor_do_texto("Só manchete"), abs=1e-6
    )


def test_centroide_do_contato_com_fatos_curtos_usa_o_mesmo_texto_de_antes(tmp_path: Path) -> None:
    conn = _abrir(tmp_path / "teste.db")
    perfil_id = _contato(conn)
    _fato(conn, perfil_id, "Publicou sobre regatas em Ilhabela.", "2026-11-02")
    _fato(conn, perfil_id, "Comentou a reforma do porto.", "2026-11-01")
    conn.commit()
    cliente = _Embeddador()

    vetor = perfis.calcular_centroide_do_contato(conn, perfil_id, cliente)

    antes = "Publicou sobre regatas em Ilhabela.\nComentou a reforma do porto."
    assert cliente.chamadas == [[antes]]
    assert vetor == _vetor_do_texto(antes)


def test_tema_sem_sinonimos_continua_com_o_texto_de_antes() -> None:
    assert configurador.texto_do_tema("vela", "vela oceânica em regatas longas", []) == (
        "vela: vela oceânica em regatas longas"
    )


# --- 2. o último caractere de um texto de 20.000 chega ao embedding --------------------------------


def test_marcador_no_ultimo_caractere_de_item_de_20_mil_chega_ao_embedding(
    tmp_path: Path, limiares: Any
) -> None:
    conn = _abrir(tmp_path / "teste.db")
    texto = _texto_longo(20_000, final=MARCADOR)
    assert len(texto) == 20_000 and texto[-1] == MARCADOR
    item_id = _item(conn, _fonte(conn), "Reforma do porto", texto)
    conn.commit()
    cliente = _Embeddador()

    agrupador.agrupar(cliente, conn, limiares, tmp_path / "PARE", data_referencia=AGORA)

    assert any(texto_enviado.endswith(MARCADOR) for texto_enviado in cliente.textos())
    assert sum(len(t) for t in cliente.textos()) >= len(texto)
    assert itens.obter_embedding(conn, item_id) is not None


def test_marcador_no_ultimo_caractere_de_fato_de_20_mil_chega_ao_centroide(tmp_path: Path) -> None:
    conn = _abrir(tmp_path / "teste.db")
    perfil_id = _contato(conn)
    _fato(conn, perfil_id, _texto_longo(20_000, final=MARCADOR), "2026-11-02")
    _fato(conn, perfil_id, "Fato curto e mais antigo.", "2026-10-01")
    conn.commit()
    cliente = _Embeddador()

    assert perfis.calcular_centroide_do_contato(conn, perfil_id, cliente) is not None

    assert any(MARCADOR in texto_enviado for texto_enviado in cliente.textos())
    assert any("Fato curto e mais antigo." in texto_enviado for texto_enviado in cliente.textos())


def test_item_maior_que_uma_chamada_e_embeddado_em_partes_que_cobrem_tudo(
    tmp_path: Path, limiares: Any
) -> None:
    conn = _abrir(tmp_path / "teste.db")
    texto = _texto_longo(100_000, final=MARCADOR)
    _item(conn, _fonte(conn), "Relatório", texto)
    conn.commit()
    cliente = _Embeddador()

    agrupador.agrupar(cliente, conn, limiares, tmp_path / "PARE", data_referencia=AGORA)

    assert len(cliente.chamadas) > 1  # uma chamada por parte
    assert all(len(chamada) == 1 for chamada in cliente.chamadas)
    assert cliente.textos()[0].startswith("Relatório\n\n")
    assert cliente.textos()[-1].endswith(MARCADOR)


# --- 3. o vetor do tema inclui descrição e sinônimos -----------------------------------------------


def test_vetor_do_tema_inclui_nome_descricao_e_sinonimos(tmp_path: Path) -> None:
    conn = _abrir(tmp_path / "teste.db")
    cliente = _Embeddador()
    tema = TemaUsuario(
        nome="cerâmica",
        descricao="peças de cerâmica feitas à mão em torno e forno a lenha",
        sinonimos=["olaria", "barro"],
        nivel="interesse",
        peso=3,
    )

    configurador.salvar_perfil_usuario(conn, cliente, "Rafael", [tema], AGORA)

    (texto_enviado,) = cliente.textos()
    assert "cerâmica" in texto_enviado
    assert "peças de cerâmica feitas à mão em torno e forno a lenha" in texto_enviado
    assert "olaria" in texto_enviado and "barro" in texto_enviado
    assert texto_enviado == configurador.texto_do_tema(tema.nome, tema.descricao, tema.sinonimos)
    (gravado,) = temas.listar_com_embedding(conn, MODELO_EMBEDDING)
    assert gravado[1] == pytest.approx(_vetor_do_texto(texto_enviado), abs=1e-6)


def test_texto_do_tema_sem_descricao_e_com_sinonimos() -> None:
    assert configurador.texto_do_tema("vela", "", ["regata"]) == "vela\nSinônimos: regata"


# --- 4. versão antiga é ausente onde o brief 066 já trata vetor de outro modelo como ausente ----------


def test_criterio_novo_tem_versao_propria_no_identificador_do_vetor(tmp_path: Path) -> None:
    conn = _abrir(tmp_path / "teste.db")
    cliente = _cliente_ollama(conn, tmp_path)
    modelo = _roteamento().perfis[_roteamento().perfil_ativo].embeddings.modelo

    assert cliente.modelo_embedding == identificador_do_vetor(modelo)
    assert cliente.modelo_embedding != modelo  # o que os vetores de antes deste brief gravaram
    assert VERSAO_CRITERIO_VETOR in cliente.modelo_embedding


def test_vetor_de_versao_antiga_e_ausente_para_quem_pede_o_atual_e_a_linha_fica(tmp_path: Path) -> None:
    conn = _abrir(tmp_path / "teste.db")
    cliente = _cliente_ollama(conn, tmp_path)
    antigo = _roteamento().perfis[_roteamento().perfil_ativo].embeddings.modelo  # "bge-m3", sem versão

    tema = temas.obter_ou_criar(conn, "vela", "vela oceânica", [], AGORA)
    assert tema.id is not None
    temas.gravar_embedding(conn, tema.id, _angulo(0), antigo)
    assunto_id = assuntos.inserir(
        conn,
        Assunto(primeiro_visto=AGORA, ultimo_visto=AGORA, n_itens=1, n_fontes_independentes=1, status="novo"),
    )
    assuntos.gravar_centroide(conn, assunto_id, _angulo(0), antigo)
    perfil_id = _contato(conn)
    perfis.gravar_centroide(conn, perfil_id, _angulo(0), antigo)
    conn.commit()

    assert temas.listar_com_embedding(conn, cliente.modelo_embedding) == []
    assert assuntos.obter_centroide(conn, assunto_id, cliente.modelo_embedding) is None
    assert perfis.obter_centroide(conn, perfil_id, cliente.modelo_embedding) is None
    # válido para leitura: a linha antiga continua no banco, intacta, e é lida pelo identificador dela
    assert len(temas.listar_com_embedding(conn, antigo)) == 1
    assert assuntos.obter_centroide(conn, assunto_id, antigo) is not None
    assert perfis.obter_centroide(conn, perfil_id, antigo) is not None


def test_agrupador_nao_vincula_item_a_centroide_de_versao_antiga_nem_o_regrava(
    tmp_path: Path, limiares: Any
) -> None:
    conn = _abrir(tmp_path / "teste.db")
    fonte_id = _fonte(conn)
    assunto_antigo = assuntos.inserir(
        conn,
        Assunto(primeiro_visto=AGORA, ultimo_visto=AGORA, n_itens=1, n_fontes_independentes=1, status="novo"),
    )
    assuntos.gravar_centroide(conn, assunto_antigo, _angulo(0), "bge-m3")  # critério de antes
    _item(conn, fonte_id, "item-a", None)
    conn.commit()
    cliente = _ClienteFake({"item-a": _angulo(0)})  # idêntico ao centróide antigo
    cliente.modelo_embedding = identificador_do_vetor("bge-m3")

    resumo = agrupador.agrupar(cliente, conn, limiares, tmp_path / "PARE", data_referencia=AGORA)

    assert resumo.assuntos_criados == 1
    (assunto_do_item,) = conn.execute("SELECT assunto_id FROM item WHERE titulo = 'item-a'").fetchone()
    assert assunto_do_item != assunto_antigo
    linhas = conn.execute(
        "SELECT modelo_embedding FROM vetor_assunto WHERE assunto_id = ?", (assunto_antigo,)
    )
    assert [linha["modelo_embedding"] for linha in linhas] == ["bge-m3"]


# --- 5. comparar-vetores: só leitura, sobre a cópia, recusa o banco real ---------------------------


def _banco_para_comparar(caminho: Path) -> None:
    """Dois assuntos com centróide do critério antigo e itens com o vetor antigo gravado."""
    conn = _abrir(caminho)
    fonte_id = _fonte(conn)
    for numero in range(3):
        assunto_id = assuntos.inserir(
            conn,
            Assunto(
                primeiro_visto=AGORA, ultimo_visto=AGORA, n_itens=1, n_fontes_independentes=1, status="novo"
            ),
        )
        texto = _texto_longo(3_000 + numero * 30_000, final=f" fim {numero}")
        item_id = _item(conn, fonte_id, f"item-{numero}", texto)
        vetor_antigo = _vetor_do_texto(f"item-{numero}\n\n{texto[:2000]}")
        itens.gravar_embedding(conn, item_id, vetor_antigo)
        itens.vincular_assunto(conn, item_id, assunto_id)
        assuntos.gravar_centroide(conn, assunto_id, vetor_antigo, "bge-m3")
    conn.commit()
    conn.close()


def test_comparar_vetores_nao_escreve_no_banco(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    copia = tmp_path / "copia.db"
    _banco_para_comparar(copia)
    for sufixo in ("-wal", "-shm"):
        assert not Path(f"{copia}{sufixo}").exists()
    hash_antes = _sha256(copia)
    cliente = _Embeddador()
    monkeypatch.setattr(cli, "caminho_banco", lambda: tmp_path / "real" / "agente.db")
    monkeypatch.setattr(cli, "_cliente_de_embedding", lambda: cliente)

    codigo = cli.main(["comparar-vetores", "--amostra", "10", "--banco", str(copia)])

    saida = capsys.readouterr().out
    assert codigo == 0
    assert _sha256(copia) == hash_antes
    assert f"sha256 antes: {hash_antes}" in saida
    assert f"sha256 depois: {hash_antes}" in saida
    assert "Itens na amostra: 3" in saida
    assert "Itens que trocariam de assunto:" in saida
    assert "Cosseno entre o vetor antigo e o novo: menor " in saida
    assert len(cliente.chamadas) > 3  # o item de 63.000 caracteres foi lido em partes


def test_comparar_vetores_recusa_o_caminho_do_banco_real(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    real = tmp_path / "dados" / "agente.db"
    _banco_para_comparar(real)
    hash_antes = _sha256(real)
    monkeypatch.setattr(cli, "caminho_banco", lambda: real)
    monkeypatch.setattr(cli, "_cliente_de_embedding", lambda: pytest.fail("não pode chamar o modelo"))

    caminho_torto = tmp_path / "dados" / ".." / "dados" / "agente.db"
    codigo = cli.main(["comparar-vetores", "--amostra", "5", "--banco", str(caminho_torto)])

    assert codigo == 1
    assert "banco real" in capsys.readouterr().out
    assert _sha256(real) == hash_antes


def test_comparar_vetores_exige_o_caminho_do_banco() -> None:
    with pytest.raises(SystemExit) as saida:
        cli.main(["comparar-vetores", "--amostra", "5"])
    assert saida.value.code == 2


def test_comparacao_conta_trocas_fusoes_separacoes_e_republicacoes(limiares: Any) -> None:
    """Cinco itens, com os vetores antigo e novo escolhidos à mão, e dois assuntos com centróide."""
    centroides = {1: _angulo(0), 2: _angulo(90)}
    amostra = [
        comparacao.Comparado(item_id=1, assunto_id=1, antigo=_angulo(0), novo=_angulo(0)),  # fica no 1
        comparacao.Comparado(item_id=2, assunto_id=1, antigo=_angulo(1), novo=_angulo(89)),  # 1 → 2
        comparacao.Comparado(item_id=3, assunto_id=2, antigo=_angulo(90), novo=_angulo(90)),  # fica no 2
        comparacao.Comparado(item_id=4, assunto_id=2, antigo=_angulo(91), novo=_angulo(45)),  # 2 → novo
        comparacao.Comparado(item_id=5, assunto_id=1, antigo=_angulo(0.5), novo=_angulo(40)),  # 1 → novo
    ]

    resultado = comparacao.contar(amostra, centroides, limiares)

    assert resultado.itens_que_trocariam_de_assunto == 3
    # o assunto 2 passa a receber itens que antes iam para o 1 e para o 2: fusão
    assert resultado.assuntos_que_se_fundiriam == 1
    # o 1 manda seus itens para três destinos (1, 2, novo) e o 2 para dois (2, novo): separação
    assert resultado.assuntos_que_se_separariam == 2
    # itens 1, 2 e 5 eram republicação um do outro no assunto 1 (cosseno ≥ 0,94), e 3 e 4 no assunto 2;
    # com o vetor novo, nenhum par passa de 0,94: os cinco deixam de ser republicação
    assert resultado.republicados_antes == 5
    assert resultado.republicacoes_que_mudariam == 5


# --- 6. falha numa parte invalida o vetor do item: o item fica sem vetor -----------------------------


def test_falha_numa_parte_deixa_o_item_sem_vetor_e_o_agrupamento_segue(tmp_path: Path, limiares: Any) -> None:
    conn = _abrir(tmp_path / "teste.db")
    fonte_id = _fonte(conn)
    meio = 50_000
    texto = _texto_longo(meio) + " FALHA_AQUI " + _texto_longo(meio)
    item_quebrado = _item(conn, fonte_id, "Longo", texto)
    item_bom = _item(conn, fonte_id, "Curto", "Texto curto que cabe.")
    conn.commit()
    cliente = _Embeddador(falhar_com="FALHA_AQUI")

    resumo = agrupador.agrupar(cliente, conn, limiares, tmp_path / "PARE", data_referencia=AGORA)

    assert len(cliente.chamadas) > 2  # a falha foi numa parte do meio, não na primeira chamada
    assert itens.obter_embedding(conn, item_quebrado) is None
    (assunto_do_quebrado,) = conn.execute(
        "SELECT assunto_id FROM item WHERE id = ?", (item_quebrado,)
    ).fetchone()
    assert assunto_do_quebrado is None
    assert resumo.itens_sem_vetor == 1
    assert itens.obter_embedding(conn, item_bom) is not None
    assert resumo.itens_embeddados == 1


def test_falha_numa_parte_do_centroide_nao_devolve_vetor_parcial(tmp_path: Path) -> None:
    conn = _abrir(tmp_path / "teste.db")
    perfil_id = _contato(conn)
    _fato(conn, perfil_id, _texto_longo(50_000) + " FALHA_AQUI " + _texto_longo(50_000), "2026-11-02")
    conn.commit()

    with pytest.raises(ValueError):
        perfis.calcular_centroide_do_contato(conn, perfil_id, _Embeddador(falhar_com="FALHA_AQUI"))
