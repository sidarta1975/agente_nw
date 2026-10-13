from __future__ import annotations

from agente_nw.nucleo.modelos.pedido import PedidoExtraido
from agente_nw.nucleo.prompts import redigir_ganchos as prompt
from agente_nw.nucleo.prompts.redigir_ganchos import AssuntoParaRedacao, EntradaRedacao

# Nomes que aparecem nos testes e nas frases de teste do projeto: o exemplo do prompt não pode usá-los.
NOMES_DOS_TESTES = ("Marina", "Joaquim", "Zuleica", "Renato", "Carla", "Marcos", "Leonardo")


def _pedido() -> PedidoExtraido:
    return PedidoExtraido.model_validate(
        {
            "pessoa_nome": "Vera",
            "pessoa_pistas": {"vinculo": "ex-chefe"},
            "objetivo": "agradecer",
            "objetivo_texto": "agradecer a indicação",
            "meio": "whatsapp",
            "registro": "proximo",
            "assunto_principal": "aviação regional",
            "interessa": ["aviação"],
            "evitar": ["futebol"],
            "termos_busca": ["aviação regional"],
            "confianca": 0.9,
        }
    )


def _entrada(fatos: int = 2, historico: int = 1, palavras_por_linha: int = 5) -> EntradaRedacao:
    linha = " ".join(["texto"] * palavras_por_linha)
    return EntradaRedacao(
        usuario_nome="Davi Pires",
        usuario_temas=[("aviação", "interesse")],
        contato_nome="Vera Lacerda",
        contato_ficha=["cargo: diretora", "cidade: Recife"],
        vinculo="ex-chefe",
        tempo_sem_contato="três anos",
        fatos=[f"fato {i}: {linha}" for i in range(fatos)],
        cabecalho_rede="linkedin: diretora de operações",
        pedido=_pedido(),
        frase="Agradecer a Vera pela indicação",
        historico=[f"consulta {i}: {linha}" for i in range(historico)],
        assuntos=[
            AssuntoParaRedacao(
                assunto_id=7,
                titulo="Companhia regional compra seis aviões",
                por_que="ela dirige operações",
                resumo="A compra foi anunciada hoje.",
                manchetes=["Jornal do Ar, 2026-10-01: Companhia compra seis aviões"],
            )
        ],
    )


def test_o_prompt_traz_os_blocos_na_ordem() -> None:
    texto = prompt.construir_prompt(_entrada())

    ordem = [
        "QUEM ESCREVE:",
        "PARA QUEM:",
        "O PEDIDO:",
        "HISTÓRICO",
        "ASSUNTOS SELECIONADOS:",
        "REGRAS DE REDAÇÃO:",
        "EXEMPLO RESOLVIDO",
    ]
    posicoes = [texto.index(marca) for marca in ordem]
    assert posicoes == sorted(posicoes)
    assert "[assunto 7] Companhia regional compra seis aviões" in texto
    assert "Evitar: futebol" in texto
    assert "Davi Pires" in texto and "aviação (interesse)" in texto


def test_prompt_pequeno_nao_e_cortado() -> None:
    texto = prompt.construir_prompt(_entrada(fatos=10, historico=3))

    assert "fato 9:" in texto
    assert "consulta 2:" in texto


def test_prompt_grande_corta_historico_para_um_e_fatos_para_cinco() -> None:
    entrada = _entrada(fatos=10, historico=3, palavras_por_linha=700)
    assert prompt.estimar_tokens(prompt.construir_prompt(entrada, limite_tokens=10**9)) > 6000

    texto = prompt.construir_prompt(entrada, limite_tokens=6000)

    assert "fato 4:" in texto and "fato 5:" not in texto
    assert "consulta 0:" in texto and "consulta 1:" not in texto


def test_o_exemplo_nao_usa_nomes_dos_testes() -> None:
    for nome in NOMES_DOS_TESTES:
        assert nome not in prompt._EXEMPLO


def test_estimativa_e_palavras_vezes_um_virgula_quatro() -> None:
    assert prompt.estimar_tokens(" ".join(["a"] * 100)) == 140


def test_o_contexto_da_relacao_aparece_no_bloco_da_pessoa() -> None:
    from dataclasses import replace

    entrada = replace(_entrada(), contexto_relacao=["família", "amigos"])

    texto = prompt.construir_prompt(entrada)

    assert "Contexto da relação: família, amigos." in texto
    assert texto.index("Contexto da relação") < texto.index("O PEDIDO:")
    assert "Contexto da relação" not in prompt.construir_prompt(_entrada())
