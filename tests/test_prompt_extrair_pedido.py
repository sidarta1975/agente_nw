from __future__ import annotations

from agente_nw.nucleo.prompts import extrair_pedido

# Nomes usados nos testes do brief 036 — o exemplo resolvido do prompt não pode conter nenhum.
_NOMES_DE_TESTE = ["Renato", "Zelia", "Estaleiro Atlântico", "Banco Alfa", "Recife"]


def test_prompt_contem_a_frase_os_contatos_e_o_exemplo() -> None:
    prompt = extrair_pedido.construir_prompt(
        "Café com a Marta amanhã", [("Marta Lins", "Editora Sul", "editora")]
    )

    assert "Café com a Marta amanhã" in prompt
    assert "Marta Lins (editora, Editora Sul)" in prompt
    assert "Exemplo resolvido" in prompt
    assert '"pessoa_nome"' in prompt


def test_prompt_sem_contatos_diz_que_nao_ha() -> None:
    assert "(nenhum contato conhecido)" in extrair_pedido.construir_prompt("frase", [])


def test_exemplo_nao_usa_nomes_dos_testes() -> None:
    exemplo = extrair_pedido._EXEMPLO_FRASE + extrair_pedido._EXEMPLO_SAIDA
    for nome in _NOMES_DE_TESTE:
        assert nome not in exemplo
