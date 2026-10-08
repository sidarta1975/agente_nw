from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import assunto_contato as assunto_contato_q
from agente_nw.nucleo.database.queries import assuntos as assuntos_q
from agente_nw.nucleo.database.queries import consulta_contato as consulta_contato_q
from agente_nw.nucleo.database.queries import fatos as fatos_q
from agente_nw.nucleo.database.queries import perfil_tema, perfis, redes_sociais
from agente_nw.nucleo.database.queries import temas as queries_temas
from agente_nw.nucleo.modelos.assunto import Assunto
from agente_nw.nucleo.modelos.assunto_contato import AssuntoContato
from agente_nw.nucleo.modelos.fato import Fato

AGORA = "2026-09-21T10:00:00+00:00"
DESCRICAO = "descrição bem completa com mais de oito palavras para embedding suficiente"


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    conexao_aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(conexao_aberta)
    return conexao_aberta


def _criar_contato(conn: sqlite3.Connection, nome: str, telefone: str | None = None) -> int:
    perfil = perfis.inserir_novo_contato(conn, nome, telefone, None, AGORA)
    conn.commit()
    assert perfil.id is not None
    return perfil.id


def _inserir_fato(conn: sqlite3.Connection, perfil_id: int, conteudo: str) -> int:
    fato_id = fatos_q.inserir(
        conn,
        Fato(
            perfil_id=perfil_id,
            tipo="teste",
            conteudo=conteudo,
            registrado_em=AGORA,
        ),
    )
    conn.commit()
    return fato_id


def _inserir_consulta(conn: sqlite3.Connection, perfil_id: int) -> int:
    registro = consulta_contato_q.inserir(conn, perfil_id, AGORA, "{}", None, "[]")
    conn.commit()
    assert registro.id is not None
    return registro.id


def test_contagem_historico_protegido_soma_fato_e_consulta_contato(
    conn: sqlite3.Connection,
) -> None:
    perfil_id = _criar_contato(conn, "Ana")
    _inserir_fato(conn, perfil_id, "algo")
    _inserir_consulta(conn, perfil_id)
    _inserir_consulta(conn, perfil_id)

    assert perfis.contagem_historico_protegido(conn, perfil_id) == (1, 2)


def test_apagar_contato_sem_historico_apaga_perfil_e_dependencias(
    conn: sqlite3.Connection,
) -> None:
    perfil_id = _criar_contato(conn, "Beto")
    redes_sociais.inserir(conn, perfil_id, "linkedin", "https://linkedin.com/in/beto", AGORA)
    tema = queries_temas.obter_ou_criar(conn, "vela", DESCRICAO, [], AGORA)
    assert tema.id is not None
    perfil_tema.vincular(conn, perfil_id, tema.id, 3, "sugerida", None, False, AGORA)
    conn.commit()

    perfis.apagar_contato_completo(conn, perfil_id)
    conn.commit()

    assert perfis.obter_por_id(conn, perfil_id) is None
    assert redes_sociais.listar_por_perfil(conn, perfil_id) == []
    assert perfil_tema.listar_por_perfil(conn, perfil_id) == []


def test_apagar_contato_com_fato_falha_por_integridade_de_banco(conn: sqlite3.Connection) -> None:
    # Salvaguarda: se alguém chamar apagar_contato_completo sem passar pela guarda
    # de contagem_historico_protegido, o banco recusa a operação — FK de fato.perfil_id
    # → perfil.id bloqueia o DELETE do perfil, e o trigger fato_sem_delete continuaria
    # bloqueando um DELETE direto em fato. O caminho correto no console faz a checagem
    # antes; este teste garante que o banco não deixa passar mesmo se a checagem falhar.
    perfil_id = _criar_contato(conn, "Carla")
    _inserir_fato(conn, perfil_id, "algo")

    with pytest.raises(sqlite3.IntegrityError):
        perfis.apagar_contato_completo(conn, perfil_id)


def test_unir_reatribui_redes_temas_fatos_e_consultas(conn: sqlite3.Connection) -> None:
    canonico_id = _criar_contato(conn, "Ana Canônica")
    duplicado_id = _criar_contato(conn, "Ana Duplicada")

    redes_sociais.inserir(conn, canonico_id, "linkedin", "https://linkedin.com/in/canonica", AGORA)
    redes_sociais.inserir(conn, duplicado_id, "instagram", "https://instagram.com/duplicada", AGORA)

    tema = queries_temas.obter_ou_criar(conn, "vela", DESCRICAO, [], AGORA)
    assert tema.id is not None
    perfil_tema.vincular(conn, duplicado_id, tema.id, 3, "sugerida", None, False, AGORA)

    _inserir_fato(conn, duplicado_id, "publicou artigo")
    _inserir_consulta(conn, duplicado_id)
    conn.commit()

    perfis.unir_contatos(conn, canonico_id, duplicado_id)
    conn.commit()

    assert perfis.obter_por_id(conn, duplicado_id) is None
    redes_canonico = redes_sociais.listar_por_perfil(conn, canonico_id)
    assert sorted(r.rede for r in redes_canonico) == ["instagram", "linkedin"]
    assert len(perfil_tema.listar_por_perfil(conn, canonico_id)) == 1
    (n_fatos,) = conn.execute("SELECT COUNT(*) FROM fato WHERE perfil_id = ?", (canonico_id,)).fetchone()
    assert n_fatos == 1
    (n_consultas,) = conn.execute(
        "SELECT COUNT(*) FROM consulta_contato WHERE perfil_id = ?", (canonico_id,)
    ).fetchone()
    assert n_consultas == 1


def test_unir_preenche_campos_vazios_do_canonico_sem_sobrescrever(
    conn: sqlite3.Connection,
) -> None:
    canonico_id = _criar_contato(conn, "Ana", telefone="+5511900001111")
    duplicado_id = _criar_contato(conn, "Ana Silva", telefone="+5511900002222")
    perfis.atualizar_ficha_manual(
        conn,
        duplicado_id,
        {"empresa": "Nova Empresa", "cidade": "São Paulo", "cargo": "Advogada"},
        AGORA,
    )
    perfis.atualizar_ficha_manual(conn, canonico_id, {"empresa": "Empresa Canônica"}, AGORA)
    conn.commit()

    perfis.unir_contatos(conn, canonico_id, duplicado_id)
    conn.commit()

    canonico = perfis.obter_por_id(conn, canonico_id)
    assert canonico is not None
    assert canonico.telefone == "+5511900001111"  # já preenchido, não sobrescrito
    assert canonico.empresa == "Empresa Canônica"  # já preenchido, não sobrescrito
    assert canonico.cidade == "São Paulo"  # veio do duplicado
    assert canonico.cargo == "Advogada"  # veio do duplicado


def test_unir_resolve_conflito_perfil_tema_pelo_canonico(conn: sqlite3.Connection) -> None:
    canonico_id = _criar_contato(conn, "Ana Canônica")
    duplicado_id = _criar_contato(conn, "Ana Duplicada")
    tema = queries_temas.obter_ou_criar(conn, "vela", DESCRICAO, [], AGORA)
    assert tema.id is not None
    perfil_tema.vincular(conn, canonico_id, tema.id, 5, "declarada", "dominio", True, AGORA)
    perfil_tema.vincular(conn, duplicado_id, tema.id, 3, "sugerida", None, False, AGORA)
    conn.commit()

    perfis.unir_contatos(conn, canonico_id, duplicado_id)
    conn.commit()

    tags = perfil_tema.listar_por_perfil(conn, canonico_id)
    assert len(tags) == 1
    assert tags[0].peso == 5
    assert tags[0].confirmado is True
    assert tags[0].nivel == "dominio"


def test_unir_resolve_conflito_assunto_contato_pelo_canonico(conn: sqlite3.Connection) -> None:
    canonico_id = _criar_contato(conn, "Ana Canônica")
    duplicado_id = _criar_contato(conn, "Ana Duplicada")
    assunto_id = assuntos_q.inserir(
        conn, Assunto(titulo_gerado="livro", primeiro_visto=AGORA, ultimo_visto=AGORA, status="novo")
    )

    def _reg(perfil_id: int, gerado_em: str, score: float, status: str) -> None:
        assunto_contato_q.inserir(
            conn,
            AssuntoContato(
                assunto_id=assunto_id,
                perfil_id=perfil_id,
                gerado_em=gerado_em,
                tipo="conector",
                aderencia_contato=0.5,
                aderencia_usuario=0.5,
                conversavel=0.5,
                score=score,
                status=status,  # type: ignore[arg-type]
            ),
        )

    _reg(canonico_id, "2026-09-21", 70.0, "usado")
    _reg(duplicado_id, "2026-09-21", 50.0, "novo")
    _reg(duplicado_id, "2026-09-20", 60.0, "novo")
    conn.commit()

    perfis.unir_contatos(conn, canonico_id, duplicado_id)
    conn.commit()

    linhas = conn.execute(
        "SELECT gerado_em, score, status FROM assunto_contato WHERE perfil_id = ? ORDER BY gerado_em",
        (canonico_id,),
    ).fetchall()
    assert len(linhas) == 2
    dia_atual = next(linha for linha in linhas if linha["gerado_em"] == "2026-09-21")
    assert dia_atual["score"] == 70.0  # o do canônico
    assert dia_atual["status"] == "usado"


def test_unir_mesmo_perfil_lanca_valor_erro(conn: sqlite3.Connection) -> None:
    perfil_id = _criar_contato(conn, "Ana")

    with pytest.raises(ValueError):
        perfis.unir_contatos(conn, perfil_id, perfil_id)


def test_gatilho_ainda_bloqueia_update_de_outras_colunas_de_fato(conn: sqlite3.Connection) -> None:
    perfil_id = _criar_contato(conn, "Ana")
    fato_id = _inserir_fato(conn, perfil_id, "original")

    with pytest.raises(sqlite3.IntegrityError, match="fato é só inserção"):
        conn.execute("UPDATE fato SET conteudo = 'outro' WHERE id = ?", (fato_id,))


def test_gatilho_ainda_bloqueia_update_de_outras_colunas_de_consulta_contato(
    conn: sqlite3.Connection,
) -> None:
    perfil_id = _criar_contato(conn, "Ana")
    consulta_id = _inserir_consulta(conn, perfil_id)

    with pytest.raises(sqlite3.IntegrityError, match="consulta_contato é só inserção"):
        conn.execute("UPDATE consulta_contato SET contexto_json = '{}' WHERE id = ?", (consulta_id,))


def test_gatilho_permite_update_apenas_de_perfil_id_em_fato(conn: sqlite3.Connection) -> None:
    perfil_a_id = _criar_contato(conn, "A")
    perfil_b_id = _criar_contato(conn, "B")
    fato_id = _inserir_fato(conn, perfil_a_id, "conteúdo")

    conn.execute("UPDATE fato SET perfil_id = ? WHERE id = ?", (perfil_b_id, fato_id))
    (novo_perfil_id,) = conn.execute("SELECT perfil_id FROM fato WHERE id = ?", (fato_id,)).fetchone()
    assert novo_perfil_id == perfil_b_id
