from __future__ import annotations

from agente_nw.nucleo.modelos.contexto_consulta import ContextoConsulta
from agente_nw.nucleo.prompts.cruzar_por_que import _EXEMPLO_SAIDA, construir_prompt
from agente_nw.nucleo.relevancia.cruzamento import sem_atribuicao


def test_prompt_proibe_atribuir_posicao_ao_contato() -> None:
    contexto = ContextoConsulta(
        assunto="eleição da OAB-SP em 2027",
        meio="telefone",
        objetivo="pedir apoio à chapa",
        interessa=["apoio"],
        evitar=[],
    )
    prompt = construir_prompt(
        "Luiz",
        ["direito eleitoral"],
        [("direito", "dominio")],
        [("Apoiadores de Lula ocupam Copacabana", "conector", "direito eleitoral")],
        contexto,
    )

    assert "nunca atribua ao contato opinião, posição, adesão" in prompt
    assert "Apoiadores de Lula ocupam Copacabana" in prompt
    assert "apoia" not in _EXEMPLO_SAIDA  # o exemplo do prompt não ensina a afirmar adesão


def test_exemplo_do_prompt_cita_so_temas_do_contato() -> None:
    prompt = construir_prompt("Luiz", [], [], [("Assunto", "conector", None)])

    assert "vela é um dos temas dela" in prompt
    assert "ela navega" not in prompt


def _contexto() -> ContextoConsulta:
    return ContextoConsulta(
        assunto="eleição da OAB-SP em 2027",
        meio="telefone",
        objetivo="convidá-lo para jantar e pedir apoio",
        interessa=[],
        evitar=[],
    )


def test_por_que_que_atribui_posicao_ao_contato_e_trocado() -> None:
    for frase in (
        "ele apoia, e você também busca apoio para o seu objetivo",
        "Ela defende essa causa e você precisa de apoio",
        "ele é contra a proposta, então serve de gancho",
    ):
        trocada = sem_atribuicao(frase, _contexto())
        assert trocada == "o assunto se liga ao que você quer: convidá-lo para jantar e pedir apoio"


def test_por_que_que_liga_ao_objetivo_ou_a_tema_fica_como_esta() -> None:
    for frase in (
        "vela é um dos temas dela, e você também curte esporte de resistência",
        "eleição da OAB-SP é um tema importante para vocês dois",
        "é a área que você domina e serve ao convite",
    ):
        assert sem_atribuicao(frase, _contexto()) == frase
