"""A verdade do brief 046 continua valendo quando a mensagem nasce de um molde: nada pode ficar falso
para o novo contato, mesmo que o molde traga o detalhe (brief 048)."""

from __future__ import annotations

from agente_nw.nucleo.modelos.pedido import PedidoExtraido
from agente_nw.nucleo.prompts import redigir_ganchos
from agente_nw.nucleo.prompts.redigir_ganchos import EntradaRedacao


def _pedido() -> PedidoExtraido:
    return PedidoExtraido.model_validate(
        {
            "objetivo": "pedir",
            "objetivo_texto": "pedir apoio na chapa da OAB",
            "registro": "cordial",
            "assunto_principal": "eleição da OAB",
            "termos_busca": ["OAB"],
            "confianca": 0.9,
        }
    )


def _entrada_com_molde(moldes: list[str]) -> EntradaRedacao:
    return EntradaRedacao(
        usuario_nome="Rafael",
        usuario_temas=[],
        contato_nome="Maria",
        contato_ficha=["cargo: advogado"],
        vinculo=None,
        tempo_sem_contato=None,
        fatos=[],
        cabecalho_rede=None,
        pedido=_pedido(),
        frase="pedir apoio",
        historico=[],
        assuntos=[],
        moldes=moldes,
    )


def test_a_regra_do_molde_proibe_deixar_algo_falso_para_quem_recebe_agora() -> None:
    regras = redigir_ganchos._regras()

    assert "nada da fonte pode sobrar na mensagem final" in regras
    assert "Ao adaptar uma mensagem-molde" in regras


def test_a_regra_de_verdade_do_046_continua_intocada() -> None:
    regras = redigir_ganchos._regras()

    assert "Sobre a pessoa, afirme só o que está nos fatos e na ficha acima." in regras
    assert (
        "Nunca infira opinião, posição ou adesão da pessoa a partir de manchete, foto ou assunto." in regras
    )


def test_o_bloco_de_moldes_tambem_proibe_inventar() -> None:
    molde = '[usei] "Luiz, parabéns pelo convite para o conselho editorial da revista jurídica."'

    bloco = redigir_ganchos._bloco_moldes(_entrada_com_molde([molde]))

    assert molde in bloco
    assert "nada pode ficar falso para quem recebe agora" in bloco


def test_sem_molde_a_regra_de_verdade_do_046_segue_valendo_sozinha() -> None:
    prompt = redigir_ganchos.construir_prompt(_entrada_com_molde([]))

    assert "MENSAGENS QUE JÁ FUNCIONARAM" not in prompt
    assert "Sobre a pessoa, afirme só o que está nos fatos e na ficha acima." in prompt
