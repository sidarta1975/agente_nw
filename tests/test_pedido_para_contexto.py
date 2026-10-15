from __future__ import annotations

from typing import Any

from agente_nw.coleta.rss.google_news import gerar_consultas_da_consulta
from agente_nw.nucleo import pedido as pedido_mod
from agente_nw.nucleo.modelos.pedido import PedidoExtraido


def _pedido() -> PedidoExtraido:
    dados: dict[str, Any] = {
        "pessoa_nome": "Renato",
        "objetivo": "agradecer",
        "objetivo_texto": "agradecer pela indicação",
        "meio": "pessoalmente",
        "registro": "proximo",
        "assunto_principal": "construção naval",
        "interessa": ["estaleiros"],
        "evitar": ["política"],
        "termos_busca": ["estaleiros", "construção naval", "Petrobras"],
        "confianca": 0.9,
    }
    return PedidoExtraido.model_validate(dados)


def test_campos_mapeados_e_livre_guarda_a_frase_original() -> None:
    contexto = pedido_mod.para_contexto(_pedido(), "Almoço com o Renato, agradecer pela indicação")

    assert contexto.assunto == "construção naval"
    assert contexto.meio == "pessoalmente"
    assert contexto.objetivo == "agradecer pela indicação"
    assert contexto.interessa == ["estaleiros"]
    assert contexto.evitar == ["política"]
    assert contexto.livre == "Almoço com o Renato, agradecer pela indicação"
    assert contexto.registro == "proximo"
    assert contexto.termos_busca == ["estaleiros", "construção naval", "Petrobras"]


def test_termos_de_busca_vem_depois_do_contato_e_sem_repetir_o_interessa() -> None:
    contexto = pedido_mod.para_contexto(_pedido(), "frase")

    feeds = gerar_consultas_da_consulta(contexto, ["tag do contato"], maximo=10)

    nomes = [feed.nome for feed in feeds]
    # assunto + contato + 2 termos_busca: "construção naval" já é o assunto e "estaleiros" já está
    # nos termos_busca, então o interessa não acrescenta nada
    assert len(feeds) == 1 + 1 + 2
    posicao_contato = next(i for i, n in enumerate(nomes) if "contato:" in n)
    posicoes_busca = [i for i, n in enumerate(nomes) if "busca:" in n]
    assert len(posicoes_busca) == 2
    assert posicao_contato < min(posicoes_busca)
    assert not any("interessa:" in n for n in nomes)
