from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel

from agente_nw.coleta.capturas import leitor
from agente_nw.coleta.capturas.extrator import RespostaCapturaRedeSocial
from agente_nw.coleta.capturas.imagens import ImagemCapturada, RespostaDescricaoImagem
from agente_nw.coleta.capturas.navegador import Pagina
from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import perfis, redes_sociais

AGORA = "2026-09-20T10:00:00+00:00"


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


@dataclass
class _PaginaFake:
    estados: list[tuple[str, str]] = field(default_factory=list)
    _indice_estado: int = 0
    fechada: bool = False

    def ir_para(self, url: str) -> None:
        pass

    def estado(self) -> tuple[str, str]:
        indice = min(self._indice_estado, len(self.estados) - 1)
        self._indice_estado += 1
        return self.estados[indice]

    def rolar(self) -> None:
        pass

    def fechar(self) -> None:
        self.fechada = True


class _ClienteLLMFake:
    def __init__(self, respostas_por_bloco: dict[str, RespostaCapturaRedeSocial]) -> None:
        self._respostas = respostas_por_bloco
        self.chamadas: list[str] = []

    def gerar_json(self, tarefa: str, prompt: str, esquema: type[BaseModel]) -> Any:
        self.chamadas.append(tarefa)
        for chave, resposta in self._respostas.items():
            if chave in prompt:
                return resposta
        return RespostaCapturaRedeSocial(descartar=True)


def _texto_com_bloco(bloco: str) -> str:
    preenchimento = "conteúdo genérico o suficiente para passar do mínimo. " * 30
    return f"cabeçalho\n\n{bloco}\n\n{preenchimento}"


def _criar_contato(conn: sqlite3.Connection, nome: str, telefone: str) -> int:
    contato = perfis.inserir_ou_atualizar_contato(conn, nome, telefone, None, None, None, None, AGORA)
    conn.commit()
    assert contato.id is not None
    return contato.id


def test_contato_sem_redes_devolve_resumo_zerado(conn: sqlite3.Connection, tmp_path: Path) -> None:
    perfil_id = _criar_contato(conn, "Ana", "+5511900000001")

    def _abrir(_pasta: Path) -> Pagina:
        raise AssertionError("não deveria abrir navegador sem redes cadastradas")

    resumo = leitor.ler_redes_sociais_do_contato(
        _ClienteLLMFake({}),
        conn,
        perfil_id,
        _abrir,
        tmp_path / "navegador",
        AGORA,
        dorme=lambda _s: None,
        max_esperas_login=1,
        espera_login_s=0.0,
        max_rolagens=1,
    )

    assert resumo.redes_lidas == 0
    assert resumo.redes_sem_sessao == 0
    assert resumo.fatos_gravados == 0


def test_rede_autenticada_com_bloco_valido_grava_fato_com_tipo_e_fonte(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    perfil_id = _criar_contato(conn, "Beto", "+5511900000002")
    redes_sociais.inserir(conn, perfil_id, "linkedin", "https://linkedin.com/in/beto", AGORA)
    conn.commit()

    bloco = "Publicou artigo sobre gestão de projetos hoje pela manhã"
    texto = _texto_com_bloco(bloco)
    pagina = _PaginaFake(estados=[("https://linkedin.com/in/beto", texto)])

    resposta = RespostaCapturaRedeSocial(
        descartar=False,
        data_do_fato="2026-09-19",
        tipo="publicacao",
        conteudo=bloco,
    )
    cliente = _ClienteLLMFake({bloco: resposta})

    resumo = leitor.ler_redes_sociais_do_contato(
        cliente,
        conn,
        perfil_id,
        lambda _p: pagina,
        tmp_path / "navegador",
        AGORA,
        dorme=lambda _s: None,
        max_esperas_login=1,
        espera_login_s=0.0,
        max_rolagens=1,
    )

    assert resumo.redes_lidas == 1
    assert resumo.redes_sem_sessao == 0
    assert resumo.fatos_gravados == 1
    assert pagina.fechada is True

    linha = conn.execute(
        "SELECT perfil_id, data_do_fato, tipo, conteudo, fonte, registrado_em FROM fato WHERE perfil_id = ?",
        (perfil_id,),
    ).fetchone()
    assert linha is not None
    assert linha["perfil_id"] == perfil_id
    assert linha["data_do_fato"] == "2026-09-19"
    assert linha["tipo"] == "rede_social:linkedin"
    assert linha["conteudo"] == bloco
    assert linha["fonte"] == "https://linkedin.com/in/beto"
    assert linha["registrado_em"] == AGORA


def test_fato_gravado_e_imutavel(conn: sqlite3.Connection, tmp_path: Path) -> None:
    perfil_id = _criar_contato(conn, "Carla", "+5511900000003")
    redes_sociais.inserir(conn, perfil_id, "x", "https://x.com/carla", AGORA)
    conn.commit()

    bloco = "Compartilhou notícia sobre novos livros de ficção científica"
    texto = _texto_com_bloco(bloco)
    pagina = _PaginaFake(estados=[("https://x.com/carla", texto)])
    resposta = RespostaCapturaRedeSocial(descartar=False, data_do_fato=None, tipo="repost", conteudo=bloco)
    cliente = _ClienteLLMFake({bloco: resposta})

    leitor.ler_redes_sociais_do_contato(
        cliente,
        conn,
        perfil_id,
        lambda _p: pagina,
        tmp_path / "navegador",
        AGORA,
        dorme=lambda _s: None,
        max_esperas_login=1,
        espera_login_s=0.0,
        max_rolagens=1,
    )

    with pytest.raises(sqlite3.IntegrityError, match="fato é só inserção"):
        conn.execute("UPDATE fato SET conteudo = 'y' WHERE perfil_id = ?", (perfil_id,))
    with pytest.raises(sqlite3.IntegrityError, match="fato é só inserção"):
        conn.execute("DELETE FROM fato WHERE perfil_id = ?", (perfil_id,))


def test_rede_sem_sessao_nao_derruba_e_registra_motivo(conn: sqlite3.Connection, tmp_path: Path) -> None:
    perfil_id = _criar_contato(conn, "Dora", "+5511900000004")
    redes_sociais.inserir(conn, perfil_id, "instagram", "https://instagram.com/login?next=%2Fdora", AGORA)
    conn.commit()

    pagina = _PaginaFake(estados=[("https://instagram.com/login?next=%2Fdora", "faça login para continuar")])
    cliente = _ClienteLLMFake({})

    resumo = leitor.ler_redes_sociais_do_contato(
        cliente,
        conn,
        perfil_id,
        lambda _p: pagina,
        tmp_path / "navegador",
        AGORA,
        dorme=lambda _s: None,
        max_esperas_login=2,
        espera_login_s=0.0,
        max_rolagens=1,
    )

    assert resumo.redes_lidas == 0
    assert resumo.redes_sem_sessao == 1
    assert resumo.fatos_gravados == 0
    assert any("instagram" in motivo for motivo in resumo.motivos_sem_sessao)
    (n_fatos,) = conn.execute("SELECT COUNT(*) FROM fato WHERE perfil_id = ?", (perfil_id,)).fetchone()
    assert n_fatos == 0


_ATIVIDADE = "https://www.linkedin.com/in/ana-lima/recent-activity/all/"


@pytest.mark.parametrize(
    ("rede", "link", "esperado"),
    [
        ("linkedin", "https://www.linkedin.com/in/ana-lima/", _ATIVIDADE),
        ("linkedin", "https://www.linkedin.com/in/ana-lima?x=1", _ATIVIDADE),
        ("linkedin", _ATIVIDADE, _ATIVIDADE),
        ("instagram", "https://www.instagram.com/ana/", "https://www.instagram.com/ana/"),
    ],
)
def test_url_de_leitura_leva_o_linkedin_para_a_atividade(rede: str, link: str, esperado: str) -> None:
    assert leitor.url_de_leitura(rede, link) == esperado


def test_maximo_de_blocos_limita_as_chamadas_ao_modelo_e_avisa_o_progresso(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    perfil_id = _criar_contato(conn, "Dora", "+5511900000004")
    redes_sociais.inserir(conn, perfil_id, "linkedin", "https://linkedin.com/in/dora", AGORA)
    conn.commit()
    blocos = [f"Publicação número {i} sobre um tema qualquer da semana" for i in range(5)]
    texto = ("preenchimento " * 40) + "\n\n" + "\n\n".join(blocos)
    pagina = _PaginaFake(estados=[("https://linkedin.com/in/dora/recent-activity/all/", texto)])
    cliente = _ClienteLLMFake({})
    linhas: list[str] = []

    resumo = leitor.ler_redes_sociais_do_contato(
        cliente,
        conn,
        perfil_id,
        lambda _p: pagina,
        tmp_path / "navegador",
        AGORA,
        dorme=lambda _s: None,
        max_rolagens=1,
        maximo_blocos=2,
        avisar=linhas.append,
    )

    assert len(cliente.chamadas) == 2
    assert resumo.blocos_capturados == 6
    assert any("extraindo 2" in linha for linha in linhas)
    assert [linha for linha in linhas if "bloco 2/2" in linha]


def test_o_fato_guarda_o_texto_integral_da_publicacao_e_nao_o_resumo_do_modelo(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    perfil_id = _criar_contato(conn, "Elisa", "+5511900000005")
    redes_sociais.inserir(conn, perfil_id, "linkedin", "https://linkedin.com/in/elisa", AGORA)
    conn.commit()
    bloco = "Hoje abri o escritório novo em Curitiba, depois de dois anos de planejamento e muita conversa."
    pagina = _PaginaFake(estados=[("https://linkedin.com/in/elisa", _texto_com_bloco(bloco))])
    resumo_do_modelo = RespostaCapturaRedeSocial(
        descartar=False, data_do_fato="2026-10-01", tipo="publicacao", conteudo="abriu escritório"
    )

    leitor.ler_redes_sociais_do_contato(
        _ClienteLLMFake({bloco: resumo_do_modelo}),
        conn,
        perfil_id,
        lambda _p: pagina,
        tmp_path / "navegador",
        AGORA,
        dorme=lambda _s: None,
        max_rolagens=1,
    )

    consulta = "SELECT data_do_fato, conteudo FROM fato WHERE perfil_id = ?"
    linha = conn.execute(consulta, (perfil_id,)).fetchone()
    assert linha["conteudo"] == bloco
    assert linha["data_do_fato"] == "2026-10-01"


def test_bloco_com_termo_sensivel_nao_vira_fato_nem_chega_ao_modelo(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    perfil_id = _criar_contato(conn, "Fábio", "+5511900000006")
    redes_sociais.inserir(conn, perfil_id, "linkedin", "https://linkedin.com/in/fabio", AGORA)
    conn.commit()
    bloco = "Hoje comecei o tratamento contra o câncer e queria agradecer a todos pelo apoio recebido."
    pagina = _PaginaFake(estados=[("https://linkedin.com/in/fabio", _texto_com_bloco(bloco))])
    cliente = _ClienteLLMFake({bloco: RespostaCapturaRedeSocial(descartar=False, conteudo=bloco)})

    leitor.ler_redes_sociais_do_contato(
        cliente,
        conn,
        perfil_id,
        lambda _p: pagina,
        tmp_path / "navegador",
        AGORA,
        dorme=lambda _s: None,
        max_rolagens=1,
    )

    assert conn.execute("SELECT COUNT(*) AS n FROM fato WHERE conteudo LIKE '%câncer%'").fetchone()["n"] == 0


class _PaginaComImagens(_PaginaFake):
    def __init__(self, estados: list[tuple[str, str]], imagens: list[ImagemCapturada]) -> None:
        super().__init__(estados=estados)
        self._imagens = imagens

    def imagens(self, maximo: int, largura_minima: int, ignorar: list[str]) -> list[ImagemCapturada]:
        return [i for i in self._imagens if i.src.split("?")[0] not in ignorar][:maximo]


class _ClienteVisaoFake(_ClienteLLMFake):
    def __init__(self) -> None:
        super().__init__({})
        self.imagens_enviadas: list[list[str] | None] = []

    def gerar_json(
        self, tarefa: str, prompt: str, esquema: type[BaseModel], imagens: list[str] | None = None
    ) -> Any:
        if tarefa == "descrever_imagem":
            self.chamadas.append(tarefa)
            self.imagens_enviadas.append(imagens)
            return RespostaDescricaoImagem(descricao="Cachorro dormindo num sofá azul.")
        return super().gerar_json(tarefa, prompt, esquema)


def _imagem(n: int, link: str) -> ImagemCapturada:
    return ImagemCapturada(f"https://cdn.test/{n}.jpg", f"alt {n}", link, "image/jpeg", "QUJD")


def test_imagem_publicada_vira_fato_com_a_descricao_e_nao_a_imagem(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    perfil_id = _criar_contato(conn, "Gil", "+5511900000007")
    redes_sociais.inserir(conn, perfil_id, "instagram", "https://instagram.com/gil", AGORA)
    conn.commit()
    pagina = _PaginaComImagens(
        [("https://instagram.com/gil", _texto_com_bloco("Bio do perfil do Gil, longa o bastante."))],
        [_imagem(1, "https://instagram.com/p/AAA/"), _imagem(2, "https://instagram.com/p/BBB/")],
    )
    cliente = _ClienteVisaoFake()

    def ler(maximo_imagens: int) -> leitor.ResumoLeitura:
        return leitor.ler_redes_sociais_do_contato(
            cliente,
            conn,
            perfil_id,
            lambda _p: pagina,
            tmp_path / "navegador",
            AGORA,
            dorme=lambda _s: None,
            max_rolagens=1,
            maximo_imagens=maximo_imagens,
        )

    resumo = ler(maximo_imagens=2)

    assert resumo.imagens_descritas == 2
    assert cliente.imagens_enviadas == [["QUJD"], ["QUJD"]]
    linhas = conn.execute(
        "SELECT tipo, conteudo, fonte FROM fato WHERE tipo LIKE 'imagem:%' ORDER BY id"
    ).fetchall()
    assert [(linha["tipo"], linha["fonte"]) for linha in linhas] == [
        ("imagem:instagram", "https://instagram.com/p/AAA/"),
        ("imagem:instagram", "https://instagram.com/p/BBB/"),
    ]
    assert linhas[0]["conteudo"] == (
        "Imagem publicada: Cachorro dormindo num sofá azul. (texto alternativo na rede: alt 1)"
    )
    # Uma segunda leitura não descreve de novo a publicação que já tem fato de imagem.
    segunda = ler(maximo_imagens=2)
    assert segunda.imagens_descritas == 0
    assert len(cliente.imagens_enviadas) == 2


def test_sem_maximo_de_imagens_nao_chama_o_modelo_de_visao(conn: sqlite3.Connection, tmp_path: Path) -> None:
    perfil_id = _criar_contato(conn, "Gil", "+5511900000008")
    redes_sociais.inserir(conn, perfil_id, "instagram", "https://instagram.com/gil", AGORA)
    conn.commit()
    pagina = _PaginaComImagens(
        [("https://instagram.com/gil", _texto_com_bloco("Bio do perfil do Gil, longa o bastante."))],
        [_imagem(1, "https://instagram.com/p/AAA/")],
    )
    cliente = _ClienteVisaoFake()

    leitor.ler_redes_sociais_do_contato(
        cliente,
        conn,
        perfil_id,
        lambda _p: pagina,
        tmp_path / "navegador",
        AGORA,
        dorme=lambda _s: None,
        max_rolagens=1,
    )

    assert "descrever_imagem" not in cliente.chamadas
