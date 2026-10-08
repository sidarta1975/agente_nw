from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest

from agente_nw.coleta.capturas.leitor import ResumoLeitura
from agente_nw.coleta.capturas.navegador import Pagina
from agente_nw.nucleo import consulta as consulta_mod
from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import assunto_contato as assunto_contato_q
from agente_nw.nucleo.database.queries import assuntos as assuntos_q
from agente_nw.nucleo.database.queries import consulta_contato as consulta_contato_q
from agente_nw.nucleo.database.queries import perfis, redes_sociais
from agente_nw.nucleo.modelos.assunto import Assunto
from agente_nw.nucleo.modelos.assunto_contato import AssuntoContato
from agente_nw.nucleo.modelos.configuracao import (
    AgrupamentoLimiares,
    CartaoLimiares,
    ColetaLimiares,
    ConectorLimiares,
    Limiares,
    QualificacaoLimiares,
)
from agente_nw.nucleo.modelos.contexto_consulta import ContextoConsulta

AGORA = "2026-09-20T10:00:00+00:00"


def _limiares() -> Limiares:
    return Limiares(
        agrupamento=AgrupamentoLimiares(
            cosseno_mesmo_assunto=0.82,
            cosseno_republicacao=0.94,
            divergencia_minima_fonte_independente=0.08,
            janela_dias=7,
            itens_para_dividir=12,
        ),
        qualificacao=QualificacaoLimiares(substancial_minimo=0.6, conversavel_minimo=0.6, teto_por_dia=40),
        conector=ConectorLimiares(
            adjacencia_minima=0.55,
            conversavel_viavel=0.8,
            peso_aderencia_contato=50,
            peso_aderencia_usuario=30,
            peso_conversavel=20,
            peso_nivel={"dominio": 1.0, "interesse": 0.7, "curiosidade": 0.4},
            candidatos_por_contato=10,
            itens_no_menu=5,
        ),
        coleta=ColetaLimiares(
            teaser_minimo_caracteres=400,
            dias_max_primeira_aparicao=7,
            retencao_texto_dias=90,
            intervalo_google_news_segundos=0,
            dias_alerta_feed_vazio=2,
        ),
        cartao=CartaoLimiares(teto_por_dia=40),
    )


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


def _pagina_dummy(_pasta: Path) -> Pagina:
    raise AssertionError("abrir_pagina não deveria ser chamado quando leitor está mockado")


def _instalar_mocks_pipeline(
    monkeypatch: pytest.MonkeyPatch, resumo_leitor: ResumoLeitura, hook_cruzar: Any = None
) -> None:
    monkeypatch.setattr(consulta_mod.leitor_rss, "coletar", lambda *_a, **_kw: None)
    monkeypatch.setattr(consulta_mod.extrator_perfil, "processar_fila", lambda *_a, **_kw: None)
    monkeypatch.setattr(consulta_mod.agrupador, "agrupar", lambda *_a, **_kw: None)
    monkeypatch.setattr(consulta_mod.qualificador, "qualificar_pendentes", lambda *_a, **_kw: None)
    monkeypatch.setattr(
        consulta_mod.leitor_capturas,
        "ler_redes_sociais_do_contato",
        lambda *_a, **_kw: resumo_leitor,
    )
    monkeypatch.setattr(
        consulta_mod.cruzamento,
        "cruzar_contato",
        hook_cruzar if hook_cruzar is not None else (lambda *_a, **_kw: None),
    )


def _contexto_padrao() -> ContextoConsulta:
    return ContextoConsulta(
        assunto="reunião trimestral",
        meio="pessoalmente",
        objetivo="apresentar proposta e ouvir feedback",
        interessa=["vela", "leitura"],
        evitar=["política"],
        livre="ele mencionou o filho na última conversa",
    )


def test_preparar_com_rede_social_e_historico_grava_consulta_e_menu(
    monkeypatch: pytest.MonkeyPatch, conn: sqlite3.Connection, tmp_path: Path
) -> None:
    contato = perfis.inserir_ou_atualizar_contato(
        conn, "Ana", "+5511900001111", None, None, None, None, AGORA
    )
    assert contato.id is not None
    perfis.ativar(conn, contato.id)
    redes_sociais.inserir(conn, contato.id, "linkedin", "https://linkedin.com/in/ana", AGORA)
    consulta_contato_q.inserir(
        conn,
        contato.id,
        "2026-09-19T10:00:00+00:00",
        json.dumps({"assunto": "primeira aproximação", "meio": "whatsapp"}),
        "linkedin: 2 blocos, 1 fato",
        json.dumps([{"titulo": "regata oceânica"}]),
    )
    conn.commit()

    assunto_id = assuntos_q.inserir(
        conn,
        Assunto(
            titulo_gerado="livro novo sobre vela",
            primeiro_visto=AGORA,
            ultimo_visto=AGORA,
            status="novo",
        ),
    )

    def _cruzar_falso(_llm: Any, conexao: sqlite3.Connection, perfil_id: int, _l: Any, agora: str) -> None:
        registro = AssuntoContato(
            assunto_id=assunto_id,
            perfil_id=perfil_id,
            gerado_em=agora[:10],
            tipo="conector",
            aderencia_contato=0.8,
            aderencia_usuario=0.7,
            conversavel=0.9,
            score=76.0,
            por_que="lembra o interesse dele por vela",
            status="novo",
        )
        assunto_contato_q.inserir(conexao, registro)
        conexao.commit()

    resumo_leitor = ResumoLeitura(
        perfil_id=contato.id,
        redes_lidas=1,
        redes_sem_sessao=0,
        blocos_capturados=3,
        fatos_gravados=2,
        motivos_sem_sessao=[],
    )
    _instalar_mocks_pipeline(monkeypatch, resumo_leitor, hook_cruzar=_cruzar_falso)

    contexto = _contexto_padrao()
    resultado = consulta_mod.preparar(
        conexao=conn,
        cliente_llm=object(),
        cliente_http=object(),  # type: ignore[arg-type]
        perfil_id=contato.id,
        contexto=contexto,
        limiares=_limiares(),
        caminho_fontes=tmp_path / "fontes.yaml",  # não existe: coleta é pulada pelo guard
        caminho_sentinela=tmp_path / "PARE",
        abrir_pagina=_pagina_dummy,
        pasta_navegador=tmp_path / "navegador",
        agora=AGORA,
    )

    assert resultado.aviso is None
    assert len(resultado.itens_menu) == 1
    item = resultado.itens_menu[0]
    assert item.titulo == "livro novo sobre vela"
    assert item.tipo == "conector"
    assert "vela" in (item.por_que or "")
    assert resultado.resumo_rede_social.redes_lidas == 1
    assert "primeira aproximação" in resultado.historico_texto

    consultas = consulta_contato_q.listar_por_perfil(conn, contato.id)
    assert len(consultas) == 2
    consulta_nova = consultas[0]
    assert consulta_nova.id == resultado.consulta_id
    contexto_gravado = json.loads(consulta_nova.contexto_json)
    assert contexto_gravado["assunto"] == "reunião trimestral"
    assert contexto_gravado["meio"] == "pessoalmente"
    assert contexto_gravado["interessa"] == ["vela", "leitura"]
    assuntos_gravados = json.loads(consulta_nova.assuntos_entregues_json)
    assert assuntos_gravados[0]["titulo"] == "livro novo sobre vela"
    assert consulta_nova.resumo_redes_sociais is not None
    assert "redes lidas: 1" in consulta_nova.resumo_redes_sociais


def test_preparar_sem_rede_social_e_sem_historico_devolve_aviso_e_grava_consulta(
    monkeypatch: pytest.MonkeyPatch, conn: sqlite3.Connection, tmp_path: Path
) -> None:
    contato = perfis.inserir_ou_atualizar_contato(
        conn, "Beto", "+5511900002222", None, None, None, None, AGORA
    )
    assert contato.id is not None
    perfis.ativar(conn, contato.id)
    conn.commit()

    resumo_leitor = ResumoLeitura(perfil_id=contato.id)
    _instalar_mocks_pipeline(monkeypatch, resumo_leitor)

    contexto = _contexto_padrao()
    resultado = consulta_mod.preparar(
        conexao=conn,
        cliente_llm=object(),
        cliente_http=object(),  # type: ignore[arg-type]
        perfil_id=contato.id,
        contexto=contexto,
        limiares=_limiares(),
        caminho_fontes=tmp_path / "fontes.yaml",
        caminho_sentinela=tmp_path / "PARE",
        abrir_pagina=_pagina_dummy,
        pasta_navegador=tmp_path / "navegador",
        agora=AGORA,
    )

    assert resultado.aviso is not None
    assert resultado.itens_menu == []
    assert resultado.historico_texto == ""
    assert resultado.resumo_rede_social.redes_lidas == 0

    consultas = consulta_contato_q.listar_por_perfil(conn, contato.id)
    assert len(consultas) == 1
    assert consultas[0].id == resultado.consulta_id
    assert consultas[0].resumo_redes_sociais is None
    assuntos_gravados = json.loads(consultas[0].assuntos_entregues_json)
    assert assuntos_gravados == []


def test_preparar_pula_coleta_quando_fontes_yaml_ausente(
    monkeypatch: pytest.MonkeyPatch, conn: sqlite3.Connection, tmp_path: Path
) -> None:
    contato = perfis.inserir_ou_atualizar_contato(
        conn, "Carla", "+5511900003333", None, None, None, None, AGORA
    )
    assert contato.id is not None
    conn.commit()

    chamou_coletar = {"count": 0}

    def _coletar_espia(*_a: Any, **_kw: Any) -> None:
        chamou_coletar["count"] += 1

    monkeypatch.setattr(consulta_mod.leitor_rss, "coletar", _coletar_espia)
    monkeypatch.setattr(consulta_mod.extrator_perfil, "processar_fila", lambda *_a, **_kw: None)
    monkeypatch.setattr(consulta_mod.agrupador, "agrupar", lambda *_a, **_kw: None)
    monkeypatch.setattr(consulta_mod.qualificador, "qualificar_pendentes", lambda *_a, **_kw: None)
    monkeypatch.setattr(
        consulta_mod.leitor_capturas,
        "ler_redes_sociais_do_contato",
        lambda *_a, **_kw: ResumoLeitura(perfil_id=contato.id),
    )
    monkeypatch.setattr(consulta_mod.cruzamento, "cruzar_contato", lambda *_a, **_kw: None)

    consulta_mod.preparar(
        conexao=conn,
        cliente_llm=object(),
        cliente_http=object(),  # type: ignore[arg-type]
        perfil_id=contato.id,
        contexto=_contexto_padrao(),
        limiares=_limiares(),
        caminho_fontes=tmp_path / "nao_existe.yaml",
        caminho_sentinela=tmp_path / "PARE",
        abrir_pagina=_pagina_dummy,
        pasta_navegador=tmp_path / "navegador",
        agora=AGORA,
    )

    assert chamou_coletar["count"] == 0


def test_preparar_com_rodar_coleta_falso_pula_coleta_mesmo_com_fontes_existente(
    monkeypatch: pytest.MonkeyPatch, conn: sqlite3.Connection, tmp_path: Path
) -> None:
    contato = perfis.inserir_ou_atualizar_contato(
        conn, "Dora", "+5511900004444", None, None, None, None, AGORA
    )
    assert contato.id is not None
    conn.commit()

    caminho_fontes = tmp_path / "fontes.yaml"
    caminho_fontes.write_text("feeds: []\n", encoding="utf-8")

    chamou_coletar = {"count": 0}
    monkeypatch.setattr(
        consulta_mod.leitor_rss, "coletar", lambda *_a, **_kw: chamou_coletar.__setitem__("count", 1)
    )
    monkeypatch.setattr(consulta_mod.extrator_perfil, "processar_fila", lambda *_a, **_kw: None)
    monkeypatch.setattr(consulta_mod.agrupador, "agrupar", lambda *_a, **_kw: None)
    monkeypatch.setattr(consulta_mod.qualificador, "qualificar_pendentes", lambda *_a, **_kw: None)
    monkeypatch.setattr(
        consulta_mod.leitor_capturas,
        "ler_redes_sociais_do_contato",
        lambda *_a, **_kw: ResumoLeitura(perfil_id=contato.id),
    )
    monkeypatch.setattr(consulta_mod.cruzamento, "cruzar_contato", lambda *_a, **_kw: None)

    consulta_mod.preparar(
        conexao=conn,
        cliente_llm=object(),
        cliente_http=object(),  # type: ignore[arg-type]
        perfil_id=contato.id,
        contexto=_contexto_padrao(),
        limiares=_limiares(),
        caminho_fontes=caminho_fontes,
        caminho_sentinela=tmp_path / "PARE",
        abrir_pagina=_pagina_dummy,
        pasta_navegador=tmp_path / "navegador",
        agora=AGORA,
        rodar_coleta=False,
    )

    assert chamou_coletar["count"] == 0
