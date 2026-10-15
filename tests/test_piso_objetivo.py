from __future__ import annotations

from agente_nw.nucleo.modelos.configuracao import ConectorLimiares, ConsultaLimiares
from agente_nw.nucleo.relevancia.pontuacao import avaliar_por_consulta

LIMIARES = ConectorLimiares(
    adjacencia_minima=0.55,
    conversavel_viavel=0.8,
    consulta=ConsultaLimiares(
        minima=0.45,
        peso_consulta=50,
        peso_contato=25,
        peso_usuario=10,
        peso_conversavel=15,
        selecao_peso_consulta=0.7,
        selecao_peso_contato=0.3,
    ),
    peso_aderencia_contato=50,
    peso_aderencia_usuario=30,
    peso_conversavel=20,
    peso_nivel={"dominio": 1.0, "interesse": 0.7, "curiosidade": 0.4},
    candidatos_por_contato=10,
    itens_no_menu=5,
)


def _vetor(*valores: float) -> list[float]:
    return list(valores) + [0.0] * (1024 - len(valores))


CONSULTA = _vetor(1.0, 0.0)
ASSUNTO_FORA_DO_PEDIDO = _vetor(0.0, 1.0)


def test_contato_e_temas_nao_promovem_assunto_fora_do_objetivo() -> None:
    avaliacao = avaliar_por_consulta(
        ASSUNTO_FORA_DO_PEDIDO,
        CONSULTA,
        _vetor(0.0, 1.0),  # os posts do contato casam com o assunto
        [("manifestações", "dominio", _vetor(0.0, 1.0))],  # e um tema do usuário também
        0.95,
        LIMIARES,
        termos_consulta=[("eleição da OAB", CONSULTA)],
        tags_contato=[("direitos humanos", _vetor(0.0, 1.0))],
    )

    assert avaliacao.tipo == "fora_do_dominio"
    assert avaliacao.ponto_de_apoio is None
    assert avaliacao.aderencia_consulta == 0.0
    assert avaliacao.aderencia_contato == 1.0  # a nota continua registrada para quem for calibrar


def test_assunto_do_objetivo_com_contato_e_conector_e_cita_o_apoio() -> None:
    assunto = _vetor(1.0, 0.3)
    avaliacao = avaliar_por_consulta(
        assunto,
        CONSULTA,
        _vetor(0.0, 1.0),
        [],
        0.5,
        LIMIARES,
        termos_consulta=[("eleição da OAB", CONSULTA)],
        tags_contato=[("direitos humanos", _vetor(0.2, 1.0))],
    )

    assert avaliacao.tipo == "conector"
    assert avaliacao.ponto_de_apoio is not None
