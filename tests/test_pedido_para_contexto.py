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


def test_termos_de_busca_viram_feeds_antes_dos_do_contato() -> None:
    contexto = pedido_mod.para_contexto(_pedido(), "frase")

    feeds = gerar_consultas_da_consulta(contexto, ["tag do contato"])

    nomes = [feed.nome for feed in feeds]
    assert len(feeds) == 1 + 1 + 3 + 1  # assunto + interessa + termos_busca + contato
    posicoes_busca = [i for i, n in enumerate(nomes) if "busca:" in n]
    posicao_contato = next(i for i, n in enumerate(nomes) if "contato:" in n)
    assert len(posicoes_busca) == 3
    assert max(posicoes_busca) < posicao_contato
