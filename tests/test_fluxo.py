from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import pytest

from agente_nw.nucleo import fluxo as fluxo_mod
from agente_nw.nucleo import localizacao as localizacao_mod
from agente_nw.nucleo.consulta import ItemMenu, ResultadoConsulta, ResumoRedeSocial
from agente_nw.nucleo.database import conexao as conexao_bd
from agente_nw.nucleo.database import migracoes
from agente_nw.nucleo.database.queries import (
    assuntos,
    consulta_contato,
    gancho_uso,
    pedidos,
    perfis,
    rede_sem_perfil,
    redes_sociais,
    sistema,
)
from agente_nw.nucleo.modelos.assunto import Assunto
from agente_nw.nucleo.modelos.localizacao import Localizacao, Opcao
from agente_nw.nucleo.modelos.pedido import PedidoExtraido
from agente_nw.nucleo.modelos.redacao import Gancho, Redacao
from tests.test_console_novo_contato import _limiares

AGORA = "2026-10-14T10:00:00+00:00"
REDES = ("linkedin", "instagram", "facebook", "x")


class ClienteLLMFalso:
    def __init__(self, nome: str = "Marta Quintela", falha: bool = False) -> None:
        self.nome = nome
        self.falha = falha
        self.frases: list[str] = []

    def gerar_json(self, tarefa_nome: str, prompt: str, esquema: Any, imagens: Any = None) -> Any:
        assert tarefa_nome == "extrair_pedido"
        self.frases.append(prompt)
        if self.falha:
            raise RuntimeError("modelo fora do ar")
        return PedidoExtraido(
            pessoa_nome=self.nome,
            objetivo="retomar",
            objetivo_texto="retomar o contato",
            meio="whatsapp",
            registro="cordial",
            assunto_principal="vela",
            termos_busca=["vela"],
            confianca=0.9,
        )


class Cenario:
    """Banco, dependências e os pontos de rede trocados por falsos."""

    def __init__(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self.caminho = tmp_path / "teste.db"
        self.conn = conexao_bd.abrir(self.caminho)
        migracoes.aplicar(self.conn)
        self.cliente = ClienteLLMFalso()
        self.chamadas_preparar: list[dict[str, Any]] = []
        self.fonte_noticias = "google"
        self.google_bloqueado_ate: str | None = None
        self.redes_localizadas: list[str] = []
        self.deps = fluxo_mod.Dependencias(
            caminho_banco=self.caminho,
            fabrica_llm=lambda _conn: self.cliente,
            fabrica_http=lambda: httpx.Client(transport=httpx.MockTransport(lambda _r: httpx.Response(200))),
            limiares=_limiares(),
            num_ctx_redacao=8192,
            caminho_fontes=tmp_path / "fontes.yaml",
            caminho_sentinela=tmp_path / "PARE",
            pasta_navegador=tmp_path / "navegador",
            abrir_pagina=lambda _p: None,
        )
        self.assunto_id = assuntos.inserir(
            self.conn,
            Assunto(
                titulo_gerado="Regata reúne veleiros",
                primeiro_visto=AGORA,
                ultimo_visto=AGORA,
                n_itens=1,
                status="novo",
                substancial=0.8,
                conversavel=0.8,
            ),
        )
        self.conn.commit()
        monkeypatch.setattr(fluxo_mod, "preparar", self._preparar)
        monkeypatch.setattr(fluxo_mod.redacao_mod, "redigir", self._redigir)
        monkeypatch.setattr(localizacao_mod, "localizar_rede", self._localizar_rede)
        self.localizacao_por_rede: dict[str, Localizacao] = {}

    def _preparar(self, **kwargs: Any) -> ResultadoConsulta:
        self.chamadas_preparar.append(kwargs)
        conexao = kwargs["conexao"]
        consulta = consulta_contato.inserir(conexao, kwargs["perfil_id"], AGORA, "{}", None, "[]")
        assert consulta.id is not None
        item = ItemMenu(
            ac_id=1, assunto_id=self.assunto_id, tipo="conector", titulo="Regata", por_que=None, score=80.0
        )
        return ResultadoConsulta(
            kwargs["perfil_id"],
            consulta.id,
            [item],
            ResumoRedeSocial(),
            "",
            fonte_noticias=self.fonte_noticias,
            google_bloqueado_ate=self.google_bloqueado_ate,
        )

    def _redigir(self, *_a: Any, **_kw: Any) -> Redacao:
        gancho = Gancho(
            assunto_id=self.assunto_id,
            titulo="Regata reúne veleiros",
            noticia="Uma regata reuniu veleiros.",
            por_que_para_esta_pessoa="Ela gosta de vela.",
            mensagem="Oi Marta, vi uma regata e lembrei de você.",
        )
        return Redacao(ganchos=[gancho], aviso=None, registro_usado="cordial")

    def _localizar_rede(self, *args: Any, **_kw: Any) -> Localizacao:
        rede = str(args[5])  # (conexao, llm, pedido, navegação, agora, rede)
        self.redes_localizadas.append(rede)
        return self.localizacao_por_rede.get(rede) or Localizacao(status="nenhum", rede=rede)

    def contato(self, nome: str = "Marta Quintela", curar: bool = False) -> int:
        contato = perfis.inserir_novo_contato(self.conn, nome, None, None, AGORA)
        assert contato.id is not None
        if curar:  # nenhuma rede pendente: o fluxo não pergunta nada
            link = "https://www.linkedin.com/in/marta"
            redes_sociais.inserir(self.conn, contato.id, "linkedin", link, AGORA)
            for rede in REDES[1:]:
                rede_sem_perfil.declarar(self.conn, contato.id, rede, AGORA)
        self.conn.commit()
        return contato.id

    def pedido(self, texto: str = "Falar com a Marta sobre vela") -> int:
        return fluxo_mod.criar_pedido(self.conn, texto, AGORA)

    def ler(self, pedido_id: int) -> pedidos.PedidoGravado:
        leitura = conexao_bd.abrir(self.caminho)
        try:
            gravado = pedidos.obter_por_id(leitura, pedido_id)
        finally:
            leitura.close()
        assert gravado is not None
        return gravado


@pytest.fixture
def cenario(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Cenario:
    return Cenario(tmp_path, monkeypatch)


def _opcao(rede: str, nome: str = "Marta Quintela") -> Opcao:
    return Opcao(rede=rede, nome=nome, cabecalho="Bancária", link=f"https://{rede}.com/marta", fonte="lista")


def test_contato_curado_em_todas_as_redes_conclui_com_ganchos(cenario: Cenario) -> None:
    cenario.contato(curar=True)
    pedido_id = cenario.pedido()

    fluxo_mod.executar_pedido(cenario.deps, pedido_id)

    gravado = cenario.ler(pedido_id)
    assert gravado.status == "concluido"
    assert gravado.consulta_id is not None
    assert cenario.redes_localizadas == []  # curadoria feita: não procura de novo
    entregues = gancho_uso.listar_por_consulta(cenario.conn, gravado.consulta_id)
    assert [(a, s) for a, s, _ in entregues] == [(cenario.assunto_id, "entregue")]
    assert cenario.chamadas_preparar[0]["ler_redes_sociais"] is True
    assert cenario.chamadas_preparar[0]["rodar_coleta"] is True


def test_rede_pendente_para_em_aguardando_pessoa_e_as_respostas_retomam(cenario: Cenario) -> None:
    perfil_id = cenario.contato()
    cenario.localizacao_por_rede = {
        "linkedin": Localizacao(
            status="claro", escolhido=_opcao("linkedin"), opcoes=[_opcao("linkedin")], rede="linkedin"
        ),
        "instagram": Localizacao(status="ambiguo", opcoes=[_opcao("instagram")], rede="instagram"),
    }
    pedido_id = cenario.pedido()

    fluxo_mod.executar_pedido(cenario.deps, pedido_id)

    gravado = cenario.ler(pedido_id)
    assert gravado.status == "aguardando_pessoa"
    assert cenario.chamadas_preparar == []  # nada de notícia nem de rede social antes de a pessoa estar certa
    assert {p["rede"] for p in fluxo_mod.perguntas_pendentes(gravado)} == set(REDES)

    assert fluxo_mod.decidir_rede(cenario.conn, pedido_id, "linkedin", "sugerido", AGORA) is None
    assert fluxo_mod.decidir_rede(cenario.conn, pedido_id, "instagram", "opcao", AGORA, indice=0) is None
    assert fluxo_mod.decidir_rede(cenario.conn, pedido_id, "facebook", "sem_perfil", AGORA) is None
    invalido = "https://exemplo.com/x"
    erro = fluxo_mod.decidir_rede(cenario.conn, pedido_id, "x", "link", AGORA, link=invalido)
    assert erro is not None and "Link não reconhecido" in erro
    assert not fluxo_mod.sem_perguntas(cenario.conn, pedido_id)
    certo = "https://x.com/marta"
    assert fluxo_mod.decidir_rede(cenario.conn, pedido_id, "x", "link", AGORA, link=certo) is None

    assert fluxo_mod.sem_perguntas(cenario.conn, pedido_id)
    gravadas = {r.rede: r.link for r in redes_sociais.listar_por_perfil(cenario.conn, perfil_id)}
    assert gravadas["linkedin"] == "https://linkedin.com/marta"
    assert gravadas["instagram"] == "https://instagram.com/marta"
    assert gravadas["x"] == "https://x.com/marta"
    assert rede_sem_perfil.listar_redes(cenario.conn, perfil_id) == {"facebook"}

    fluxo_mod.continuar_pedido(cenario.deps, pedido_id)

    assert cenario.ler(pedido_id).status == "concluido"
    assert len(cenario.chamadas_preparar) == 1


def test_homonimos_perguntam_qual_contato_e_o_pedido_recomeca_com_o_escolhido(cenario: Cenario) -> None:
    primeiro = cenario.contato("Marta Quintela", curar=True)
    segundo = cenario.contato("Marta Quintela Neto", curar=True)
    pedido_id = cenario.pedido()

    fluxo_mod.executar_pedido(cenario.deps, pedido_id)

    gravado = cenario.ler(pedido_id)
    assert gravado.status == "aguardando_pessoa"
    pergunta = fluxo_mod.perguntas_pendentes(gravado)[0]
    assert pergunta["tipo"] == "contato"
    assert {c["perfil_id"] for c in pergunta["candidatos"]} == {primeiro, segundo}

    assert fluxo_mod.decidir_contato(cenario.conn, pedido_id, 99999) == "Contato inválido."
    assert fluxo_mod.decidir_contato(cenario.conn, pedido_id, segundo) is None
    fluxo_mod.executar_pedido(cenario.deps, pedido_id)

    final = cenario.ler(pedido_id)
    assert final.status == "concluido"
    assert final.perfil_id == segundo


def test_correcao_cria_pedido_filho_pula_localizacao_rede_social_e_coleta(cenario: Cenario) -> None:
    perfil_id = cenario.contato(curar=True)
    pai_id = cenario.pedido()
    fluxo_mod.executar_pedido(cenario.deps, pai_id)
    sistema.progresso_gravar(
        cenario.conn, fluxo_mod.ETAPA_DA_COLETA, 1, "2026-10-14", datetime.now(UTC).isoformat()
    )
    cenario.conn.commit()
    cenario.chamadas_preparar.clear()

    filho_id = fluxo_mod.criar_correcao(cenario.conn, pai_id, "mais informal", AGORA)

    assert filho_id is not None
    filho = cenario.ler(filho_id)
    assert filho.pedido_pai_id == pai_id
    assert filho.perfil_id == perfil_id
    assert filho.texto.endswith("\nCorreção: mais informal")

    fluxo_mod.executar_pedido(cenario.deps, filho_id)

    assert cenario.ler(filho_id).status == "concluido"
    assert "Correção: mais informal" in cenario.cliente.frases[-1]
    chamada = cenario.chamadas_preparar[0]
    assert chamada["ler_redes_sociais"] is False
    assert chamada["rodar_coleta"] is False
    assert cenario.redes_localizadas == []


def test_correcao_refaz_a_coleta_quando_a_ultima_e_antiga(cenario: Cenario) -> None:
    cenario.contato(curar=True)
    pai_id = cenario.pedido()
    fluxo_mod.executar_pedido(cenario.deps, pai_id)
    antiga = (datetime.now(UTC) - timedelta(hours=5)).isoformat()
    sistema.progresso_gravar(cenario.conn, fluxo_mod.ETAPA_DA_COLETA, 1, "2026-10-14", antiga)
    cenario.conn.commit()
    cenario.chamadas_preparar.clear()
    filho_id = fluxo_mod.criar_correcao(cenario.conn, pai_id, "ele é do Rio", AGORA)
    assert filho_id is not None

    fluxo_mod.executar_pedido(cenario.deps, filho_id)

    assert cenario.chamadas_preparar[0]["rodar_coleta"] is True


def test_correcao_vazia_ou_de_pedido_sem_pessoa_nao_cria_pedido(cenario: Cenario) -> None:
    sem_pessoa = cenario.pedido()

    assert fluxo_mod.criar_correcao(cenario.conn, sem_pessoa, "mais informal", AGORA) is None
    assert fluxo_mod.criar_correcao(cenario.conn, 999, "mais informal", AGORA) is None


def test_erro_no_modelo_grava_status_erro_com_a_mensagem(cenario: Cenario) -> None:
    cenario.cliente.falha = True
    pedido_id = cenario.pedido()

    fluxo_mod.executar_pedido(cenario.deps, pedido_id)

    gravado = cenario.ler(pedido_id)
    assert gravado.status == "erro"
    assert gravado.erro is not None and "modelo fora do ar" in gravado.erro
    assert gravado.etapa == "Entendendo o pedido"


def test_pedido_que_ficou_processando_vira_erro_ao_reiniciar(cenario: Cenario) -> None:
    pedido_id = cenario.pedido()

    assert fluxo_mod.marcar_interrompidos(cenario.conn) == 1

    assert cenario.ler(pedido_id).status == "erro"


def test_fila_roda_uma_tarefa_por_vez_na_ordem() -> None:
    import threading

    fila = fluxo_mod.FilaDeTrabalho()
    ordem: list[int] = []
    terminou = threading.Event()

    def falha() -> None:
        raise RuntimeError("falha não derruba a fila")

    fila.enfileirar(lambda: ordem.append(1))
    fila.enfileirar(falha)
    fila.enfileirar(lambda: ordem.append(2))
    fila.enfileirar(terminou.set)

    assert terminou.wait(timeout=5)
    assert ordem == [1, 2]


def test_pessoas_recentes_conta_ganchos_usados(cenario: Cenario) -> None:
    perfil_id = cenario.contato(curar=True)
    pedido_id = cenario.pedido()
    fluxo_mod.executar_pedido(cenario.deps, pedido_id)
    consulta_id = cenario.ler(pedido_id).consulta_id
    assert consulta_id is not None
    gancho_uso.marcar(cenario.conn, consulta_id, cenario.assunto_id, "usado", AGORA)
    cenario.conn.commit()

    recentes = pedidos.pessoas_recentes(cenario.conn, 20)

    assert [(r.perfil_id, r.ganchos_usados) for r in recentes] == [(perfil_id, 1)]
