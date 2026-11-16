"""Brief 083: nenhum texto some da coleta sem deixar rastro.

1. bloco acima de 5.000 caracteres é partido em pedaços que reproduzem o bloco (P-014);
2. o corte de 200.000 caracteres da página (no Chrome ou no programa) é registrado (P-013);
3. a marca de patrocinado é procurada em todas as linhas curtas do corpo (P-004);
4. item cujo corpo falhou é gravado e marcado, mas não chega ao cartão, à qualificação nem ao gancho (P-003).

Nenhum teste toca a internet, a extensão real ou o banco real."""

from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
from pathlib import Path
from typing import Any, cast

import httpx
import pytest

from agente_nw.coleta.capturas import leitor as leitor_capturas
from agente_nw.coleta.capturas import navegador
from agente_nw.coleta.capturas.extensao_backend import PaginaExtensao, aviso_de_corte
from agente_nw.coleta.capturas.extrator import RespostaCapturaRedeSocial
from agente_nw.coleta.rss.ruido import e_ruido
from agente_nw.nucleo import consulta, redacao
from agente_nw.nucleo.consulta import ItemMenu, ResumoRedeSocial
from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import assuntos, itens, perfis, redes_sociais
from agente_nw.nucleo.modelos.assunto import Assunto
from agente_nw.nucleo.modelos.cartao import RespostaCartao
from agente_nw.nucleo.modelos.configuracao import ColetaLimiares, ExtensaoLimiares
from agente_nw.nucleo.modelos.qualificacao import RespostaQualificar
from agente_nw.nucleo.modelos.rotulo import RespostaRotulo
from agente_nw.nucleo.relevancia import cartoes
from agente_nw.nucleo.relevancia.qualificador import qualificar_pendentes
from agente_nw.ponte import Ponte
from tests import coleta_falsa
from tests.llm_falso import ProvenienciaFalsa

RAIZ = Path(__file__).resolve().parent.parent
AGORA = "2026-11-16T10:00:00+00:00"


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(aberta)
    return aberta


# --------------------------------------------------------------------------------------
# 1. Bloco grande é partido, não descartado (P-014)
# --------------------------------------------------------------------------------------


def _frases(total: int) -> str:
    """Texto corrido, sem linha em branco, de exatamente `total` caracteres."""
    texto = ""
    numero = 0
    while len(texto) < total:
        texto += f"Esta é a frase de número {numero} de uma publicação muito longa. "
        numero += 1
    return texto[: total - 1] + "."


def _sem_palavra_cortada(pedacos: list[str]) -> bool:
    return all(
        not (anterior[-1].isalnum() and seguinte[0].isalnum())
        for anterior, seguinte in zip(pedacos, pedacos[1:], strict=False)
    )


def test_bloco_de_12000_caracteres_vira_3_pedacos_que_reproduzem_o_bloco() -> None:
    bloco = _frases(12_000)
    assert len(bloco) == 12_000

    pedacos = navegador.partir_bloco(bloco)

    assert len(pedacos) == 3
    assert all(len(pedaco) <= 5_000 for pedaco in pedacos)
    assert "".join(pedacos) == bloco
    assert _sem_palavra_cortada(pedacos)
    assert all(pedaco.endswith(". ") for pedaco in pedacos[:-1])  # fim de frase


def test_corte_prefere_fim_de_paragrafo() -> None:
    paragrafo = _frases(1_900) + "\n"
    bloco = paragrafo * 6  # 6 parágrafos de 1.901 caracteres, sem linha em branco entre eles

    pedacos = navegador.partir_bloco(bloco)

    assert "".join(pedacos) == bloco
    assert all(len(pedaco) <= 5_000 for pedaco in pedacos)
    assert all(pedaco.endswith("\n") for pedaco in pedacos)


def test_sem_frase_nem_paragrafo_corta_em_palavra() -> None:
    bloco = ("palavra " * 1_500).strip()  # 11.999 caracteres, sem ponto nem quebra de linha

    pedacos = navegador.partir_bloco(bloco)

    assert "".join(pedacos) == bloco
    assert all(len(pedaco) <= 5_000 for pedaco in pedacos)
    assert all(pedaco.endswith(" ") for pedaco in pedacos[:-1])
    assert _sem_palavra_cortada(pedacos)


def test_bloco_que_cabe_volta_inteiro() -> None:
    bloco = _frases(4_000)
    assert navegador.partir_bloco(bloco) == [bloco]


class _PaginaFixa:
    def __init__(self, texto: str) -> None:
        self.texto = texto

    def ir_para(self, url: str) -> None:
        pass

    def estado(self) -> tuple[str, str]:
        return "https://www.linkedin.com/in/ana/recent-activity/all/", self.texto

    def rolar(self) -> None:
        pass

    def fechar(self) -> None:
        pass


def test_leitura_parte_o_bloco_grande_descarta_o_curto_e_conta_uma_vez() -> None:
    grande = _frases(12_000)
    curto = "Curtir · Comentar · Enviar."  # 27 caracteres: menu, continua descartado
    assert len(curto) < 30
    medio = _frases(600)
    pagina = _PaginaFixa(f"{curto}\n\n{grande}\n\n{medio}")

    captura = navegador.ler(pagina, "https://x", dorme=lambda _s: None, max_rolagens=3)

    assert captura.autenticado
    assert curto not in captura.blocos
    assert captura.blocos_partidos == 1  # a mesma página lida 3 vezes conta o bloco uma vez só
    assert len(captura.blocos) == 4
    assert "".join(captura.blocos[:3]) == grande
    assert captura.blocos[3] == medio


def test_resumo_da_leitura_conta_os_blocos_partidos(conn: sqlite3.Connection, tmp_path: Path) -> None:
    contato = perfis.inserir_ou_atualizar_contato(
        conn, "Ana", "+5511900000083", None, None, None, None, AGORA
    )
    assert contato.id is not None
    redes_sociais.inserir(conn, contato.id, "linkedin", "https://www.linkedin.com/in/ana", AGORA)
    conn.commit()
    pagina = _PaginaFixa(f"{_frases(12_000)}\n\n{_frases(600)}")

    class _Cliente:
        def num_ctx(self, tarefa_nome: str) -> int:
            return 32_768

        def gerar_json(self, *_a: Any, **_k: Any) -> Any:
            return RespostaCapturaRedeSocial(descartar=True)

    avisos: list[str] = []
    resumo = leitor_capturas.ler_redes_sociais_do_contato(
        cast(Any, _Cliente()),
        conn,
        contato.id,
        lambda _p: pagina,
        tmp_path,
        AGORA,
        dorme=lambda _s: None,
        max_rolagens=1,
        avisar=avisos.append,
    )

    assert resumo.blocos_partidos == 1
    assert resumo.blocos_capturados == 4
    assert any("partido" in aviso for aviso in avisos)


# --------------------------------------------------------------------------------------
# 2. O corte de 200.000 caracteres deixa de ser silencioso (P-013)
# --------------------------------------------------------------------------------------


class _PonteFalsa:
    def __init__(self, estado: dict[str, Any]) -> None:
        self.tarefas: list[dict[str, Any]] = []
        self._estado = estado

    def enviar(self, tarefa: dict[str, Any], tempo_limite_s: float) -> dict[str, Any]:
        self.tarefas.append(tarefa)
        if tarefa["acao"] == "abrir":
            return {"aba_id": 3}
        if tarefa["acao"] == "estado":
            return self._estado
        return {}


def _linhas_do_log(caminho: Path) -> list[dict[str, Any]]:
    if not caminho.exists():
        return []
    return [json.loads(linha) for linha in caminho.read_text(encoding="utf-8").splitlines() if linha]


def _pagina_extensao(estado: dict[str, Any], caminho_log: Path) -> PaginaExtensao:
    return PaginaExtensao(cast(Ponte, _PonteFalsa(estado)), ExtensaoLimiares(), caminho_log=caminho_log)


def test_aviso_de_corte_no_formato_do_brief() -> None:
    assert aviso_de_corte(200_000, 350_000) == "página cortada em 200.000 de 350.000 caracteres"


def test_extensao_que_cortou_vira_linha_no_log_e_aviso_no_resumo(tmp_path: Path) -> None:
    log = tmp_path / "chamadas_llm.jsonl"
    pagina = _pagina_extensao(
        {"url": "https://x.com/ana", "texto": "a" * 200_000, "tamanho_original": 350_000, "cortado": True},
        log,
    )
    pagina.ir_para("https://x.com/ana")

    _url, texto = pagina.estado()
    pagina.estado()  # a mesma página lida de novo não repete o aviso

    assert len(texto) == 200_000
    assert pagina.avisos_corte == ["página cortada em 200.000 de 350.000 caracteres"]
    linhas = _linhas_do_log(log)
    assert len(linhas) == 1
    assert linhas[0]["corte_pagina"] is True
    assert linhas[0]["origem"] == "extensao"
    assert linhas[0]["maximo"] == 200_000
    assert linhas[0]["tamanho_original"] == 350_000
    assert linhas[0]["url"] == "https://x.com/ana"


def test_extensao_que_nao_cortou_nao_registra_nada(tmp_path: Path) -> None:
    log = tmp_path / "chamadas_llm.jsonl"
    pagina = _pagina_extensao(
        {"url": "https://x.com/ana", "texto": "b" * 5_000, "tamanho_original": 5_000, "cortado": False}, log
    )
    pagina.ir_para("https://x.com/ana")

    pagina.estado()

    assert pagina.avisos_corte == []
    assert _linhas_do_log(log) == []


def test_corte_do_lado_do_programa_tambem_e_registrado(tmp_path: Path) -> None:
    """Extensão antiga (sem `cortado`) que devolve mais do que o teto: o programa corta e avisa."""
    log = tmp_path / "chamadas_llm.jsonl"
    pagina = _pagina_extensao({"url": "https://x.com/ana", "texto": "c" * 350_000}, log)
    pagina.ir_para("https://x.com/ana")

    _url, texto = pagina.estado()

    assert len(texto) == 200_000
    assert pagina.avisos_corte == ["página cortada em 200.000 de 350.000 caracteres"]
    linhas = _linhas_do_log(log)
    assert [linha["origem"] for linha in linhas] == ["programa"]


def test_aviso_de_corte_chega_ao_resumo_da_leitura(conn: sqlite3.Connection, tmp_path: Path) -> None:
    contato = perfis.inserir_ou_atualizar_contato(
        conn, "Bia", "+5511900000084", None, None, None, None, AGORA
    )
    assert contato.id is not None
    redes_sociais.inserir(conn, contato.id, "x", "https://x.com/bia", AGORA)
    conn.commit()
    pagina = _pagina_extensao(
        {
            "url": "https://x.com/bia",
            "texto": _frases(1_000) + "\n\n" + "d" * 199_000,
            "tamanho_original": 350_000,
            "cortado": True,
        },
        tmp_path / "chamadas_llm.jsonl",
    )

    class _Cliente:
        def num_ctx(self, tarefa_nome: str) -> int:
            return 32_768

        def gerar_json(self, *_a: Any, **_k: Any) -> Any:
            return RespostaCapturaRedeSocial(descartar=True)

    resumo = leitor_capturas.ler_redes_sociais_do_contato(
        cast(Any, _Cliente()), conn, contato.id, lambda _p: pagina, tmp_path, AGORA, max_rolagens=1
    )

    assert resumo.avisos == ["x: página cortada em 200.000 de 350.000 caracteres"]
    texto = consulta._resumo_rede_para_texto(ResumoRedeSocial(redes_lidas=1, avisos=list(resumo.avisos)))
    assert texto is not None
    assert "página cortada em 200.000 de 350.000 caracteres" in texto


@pytest.mark.skipif(shutil.which("node") is None, reason="sem node nesta máquina")
@pytest.mark.parametrize(("tamanho", "cortado"), [(350_000, True), (5_000, False)])
def test_conteudo_js_devolve_tamanho_original_e_se_cortou(tamanho: int, cortado: bool) -> None:
    """O `estado` do `conteudo.js` rodado no node, com uma página falsa de `tamanho` caracteres."""
    script = (
        f"globalThis.document = {{ body: {{ innerText: 'e'.repeat({tamanho}) }} }};"
        "globalThis.location = { href: 'https://x.com/ana', hostname: 'x.com', pathname: '/ana' };"
        f"require({json.dumps(str(RAIZ / 'extensao' / 'conteudo.js'))});"
        "const r = globalThis.agenteNw.estado(200000);"
        "console.log(JSON.stringify({ n: r.texto.length, tamanho_original: r.tamanho_original,"
        " cortado: r.cortado, url: r.url }));"
    )
    saida = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True, timeout=30)
    resposta = json.loads(saida.stdout)
    assert resposta == {
        "n": min(tamanho, 200_000),
        "tamanho_original": tamanho,
        "cortado": cortado,
        "url": "https://x.com/ana",
    }


# --------------------------------------------------------------------------------------
# 3. O filtro de patrocinado olha o texto todo (P-004)
# --------------------------------------------------------------------------------------


def _limiares() -> ColetaLimiares:
    return coleta_falsa.limiares()


def _paragrafo_longo(numero: int) -> str:
    return (
        f"Parágrafo {numero} da reportagem, com informação apurada e contexto suficiente para o leitor. " * 2
    )


def test_publicidade_no_rodape_e_ruido() -> None:
    linhas = [_paragrafo_longo(n) for n in range(50)]
    linhas[39] = "Publicidade"
    corpo = "\n".join(linhas)

    ruido, motivo = e_ruido("Mercado cresce no trimestre", corpo, None, AGORA, _limiares())

    assert ruido
    assert motivo == "marcado como patrocinado"


def test_publicidade_no_meio_de_paragrafo_longo_nao_e_ruido() -> None:
    linhas = [_paragrafo_longo(n) for n in range(10)]
    linhas[4] = (
        "Segundo o levantamento, a publicidade infantil cresceu 12% no ano passado, e o setor discute "
        "novas regras de autorregulação com as agências e os anunciantes."
    )
    corpo = "\n".join(linhas)

    ruido, _motivo = e_ruido("Mercado cresce no trimestre", corpo, None, AGORA, _limiares())

    assert not ruido


def test_conteudo_patrocinado_na_primeira_linha_continua_ruido() -> None:
    corpo = "Conteúdo patrocinado\n" + "\n".join(_paragrafo_longo(n) for n in range(10))

    ruido, motivo = e_ruido("Mercado cresce no trimestre", corpo, None, AGORA, _limiares())

    assert ruido
    assert motivo == "marcado como patrocinado"


def test_corpo_curto_continua_abaixo_do_teaser_minimo() -> None:
    ruido, motivo = e_ruido("Mercado cresce", "Texto curto demais.", None, AGORA, _limiares())
    assert ruido
    assert motivo == "corpo abaixo do teaser mínimo"


# --------------------------------------------------------------------------------------
# 4. Item sem corpo não é julgado pela manchete (P-003, primeira parte)
# --------------------------------------------------------------------------------------


class _RedeComPaginaQuebrada(coleta_falsa.RedeFalsa):
    """A página da notícia número 1 de cada busca não abre (o corpo falha)."""

    def _atender(self, requisicao: httpx.Request) -> httpx.Response:
        if requisicao.url.host == "noticias.exemplo.com" and requisicao.url.path.endswith("-1"):
            self.pedidos.append(f"{requisicao.url.host}{requisicao.url.path}")
            return httpx.Response(500, text="erro")
        return super()._atender(requisicao)


def test_item_sem_corpo_e_gravado_marcado_e_contado(conn: sqlite3.Connection, tmp_path: Path) -> None:
    rede = _RedeComPaginaQuebrada(por_busca=3)

    resumo = coleta_falsa.coletar(rede, conn, tmp_path, ["reforma tributária"])

    linhas = conn.execute("SELECT titulo, texto FROM item ORDER BY id").fetchall()
    assert len(linhas) == 3
    sem_corpo = [linha["titulo"] for linha in linhas if linha["texto"] is None]
    assert len(sem_corpo) == 1
    assert "número 1" in sem_corpo[0]
    assert resumo.itens_novos == 3
    assert resumo.itens_so_manchete == 1
    assert resumo.descartados_ruido == 0


class _ClienteGravaPrompts(ProvenienciaFalsa):
    def __init__(self) -> None:
        self.prompts: dict[str, list[str]] = {}

    @property
    def modelo_embedding(self) -> str:
        return "bge-m3"

    def gerar_json(
        self, tarefa_nome: str, prompt: str, esquema: type[Any], versao_prompt: str | None = None
    ) -> Any:
        self.prompts.setdefault(tarefa_nome, []).append(prompt)
        if tarefa_nome == "rotular":
            return RespostaRotulo(titulo="Reforma tributária")
        if tarefa_nome == "qualificar":
            return RespostaQualificar(substancial=0.9, conversavel=0.9, justificativa="ok", temas=[])
        if tarefa_nome == "cartao":
            return RespostaCartao(resumo="Resumo do assunto sem números.")
        raise AssertionError(tarefa_nome)


def _vetor(*valores: float) -> list[float]:
    return list(valores) + [0.0] * (1024 - len(valores))


def _assunto_com_itens(conn: sqlite3.Connection, itens_do_assunto: list[tuple[str, str | None]]) -> int:
    from agente_nw.nucleo.database.queries import fontes, perfil_tema
    from agente_nw.nucleo.database.queries import temas as queries_temas
    from agente_nw.nucleo.modelos.item import Item

    usuario = perfis.upsert_usuario(conn, "Usuário", AGORA)
    assert usuario.id is not None
    tema = queries_temas.obter_ou_criar(conn, "tema", "descrição", [], AGORA)
    assert tema.id is not None
    queries_temas.gravar_embedding(conn, tema.id, _vetor(1.0), modelo_embedding="bge-m3")
    perfil_tema.vincular(conn, usuario.id, tema.id, 3, "declarada", "dominio", True, AGORA)
    fonte = fontes.obter_ou_criar(conn, "g1.globo.com", "https://g1.globo.com/rss", "g1.globo.com", "rss", 5)
    assert fonte.id is not None
    assunto_id = assuntos.inserir(
        conn, Assunto(primeiro_visto=AGORA, ultimo_visto=AGORA, n_itens=len(itens_do_assunto), status="novo")
    )
    assuntos.gravar_centroide(conn, assunto_id, _vetor(1.0), modelo_embedding="bge-m3")
    for numero, (titulo, texto) in enumerate(itens_do_assunto):
        itens.inserir(
            conn,
            Item(
                fonte_id=fonte.id,
                url_canonica=f"https://g1.globo.com/{assunto_id}/{numero}",
                titulo=titulo,
                texto=texto,
                coletado_em=AGORA,
                hash_titulo=f"h-{assunto_id}-{numero}",
                assunto_id=assunto_id,
            ),
        )
    conn.commit()
    return assunto_id


_COM_CORPO = "Manchete com corpo lido"
_SO_MANCHETE = "Manchete cujo corpo falhou"


def test_item_sem_corpo_nao_chega_a_qualificacao_ao_cartao_nem_ao_gancho(conn: sqlite3.Connection) -> None:
    assunto_id = _assunto_com_itens(
        conn, [(_COM_CORPO, "Corpo inteiro da notícia. " * 30), (_SO_MANCHETE, None)]
    )
    cliente = _ClienteGravaPrompts()

    resumo = qualificar_pendentes(cliente, conn, limite=10)
    cartao = cartoes.gerar_cartao(cliente, conn, assunto_id)
    para_redacao = redacao._assunto_para_redacao(
        conn, ItemMenu(ac_id=1, assunto_id=assunto_id, tipo="tema", titulo="Reforma", por_que=None, score=1.0)
    )

    assert resumo.qualificados == 1
    assert cartao is not None
    prompts = [p for lista in cliente.prompts.values() for p in lista]
    assert {"rotular", "qualificar", "cartao"} <= set(cliente.prompts)
    assert all(_COM_CORPO in prompt for prompt in prompts)
    assert all(_SO_MANCHETE not in prompt for prompt in prompts)
    assert all(_SO_MANCHETE not in manchete for manchete in para_redacao.manchetes)
    assert [link.titulo for link in para_redacao.links] == [_COM_CORPO]
    # o item continua no assunto (o agrupamento não muda neste brief)
    assert len(itens.listar_por_assunto(conn, assunto_id)) == 2


def test_assunto_so_de_manchetes_nao_e_qualificado(conn: sqlite3.Connection) -> None:
    _assunto_com_itens(conn, [(_SO_MANCHETE, None)])
    cliente = _ClienteGravaPrompts()

    resumo = qualificar_pendentes(cliente, conn, limite=10)

    assert cliente.prompts == {}
    assert resumo.qualificados == 0
    assert resumo.sem_corpo == 1
