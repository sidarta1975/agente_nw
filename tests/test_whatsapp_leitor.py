"""Leitor da exportação do WhatsApp: formato iPhone e Android, descartes e zip (brief 061)."""

from __future__ import annotations

from pathlib import Path

from agente_nw.coleta.whatsapp import leitor

_FIXTURES = Path(__file__).parent / "fixtures"


def _mensagens_esperadas() -> list[tuple[str, str]]:
    """(autor, texto) das três mensagens reais do fixture (as outras são descarte)."""
    return [
        ("Joana Prado", "Bom dia! Vamos marcar aquele café?"),
        ("Caio Serra", "Combinado, mas me conta antes\no que você achou da proposta que te mandei ontem."),
        ("Caio Serra", "Topo sim, que tal sábado de manhã?"),
    ]


def test_formato_iphone_le_mensagens_e_descarta_o_resto() -> None:
    texto = (_FIXTURES / "whatsapp_ios.txt").read_text(encoding="utf-8")

    conversa = leitor.ler_conversa(texto)

    assert conversa.participantes == ("Joana Prado", "Caio Serra")
    assert [(m.autor, m.texto) for m in conversa.mensagens] == _mensagens_esperadas()
    assert conversa.mensagens[0].quando.isoformat() == "2026-10-25T09:10:00"
    assert conversa.mensagens[1].quando.isoformat() == "2026-10-25T09:11:05"


def test_formato_android_le_mensagens_e_descarta_o_resto() -> None:
    texto = (_FIXTURES / "whatsapp_android.txt").read_text(encoding="utf-8")

    conversa = leitor.ler_conversa(texto)

    assert conversa.participantes == ("Joana Prado", "Caio Serra")
    assert [(m.autor, m.texto) for m in conversa.mensagens] == _mensagens_esperadas()
    assert conversa.mensagens[0].quando.isoformat() == "2026-10-25T09:10:00"


def test_ano_com_dois_digitos() -> None:
    conversa = leitor.ler_conversa("25/10/26 09:10 - Joana Prado: Oi")

    assert conversa.mensagens[0].quando.year == 2026


def test_mensagem_de_varias_linhas_emenda_na_anterior() -> None:
    texto = "[01/02/2026, 08:00:00] Joana Prado: primeira linha\nsegunda linha\nterceira linha"

    conversa = leitor.ler_conversa(texto)

    assert len(conversa.mensagens) == 1
    assert conversa.mensagens[0].texto == "primeira linha\nsegunda linha\nterceira linha"


def test_descarta_midia_aviso_do_sistema_e_mensagem_apagada() -> None:
    texto = "\n".join(
        [
            "[01/02/2026, 08:00:00] Joana Prado: <Mídia oculta>",
            "[01/02/2026, 08:01:00] Joana Prado: áudio omitido",
            "[01/02/2026, 08:02:00] Joana Prado: figurinha omitida",
            "[01/02/2026, 08:03:00] Joana Prado: Mensagem apagada",
            "[01/02/2026, 08:04:00] As mensagens agora são protegidas com a criptografia de ponta a ponta.",
            "[01/02/2026, 08:05:00] Joana Prado: esta mensagem fica",
        ]
    )

    conversa = leitor.ler_conversa(texto)

    assert [m.texto for m in conversa.mensagens] == ["esta mensagem fica"]


def test_caractere_invisivel_de_direcao_no_comeco_da_linha() -> None:
    texto = "‎[01/02/2026, 08:00:00] Joana Prado: oi"

    conversa = leitor.ler_conversa(texto)

    assert conversa.mensagens[0].texto == "oi"


def test_zip_com_chat_txt_e_uma_foto_le_so_o_texto() -> None:
    dados = (_FIXTURES / "whatsapp_ios.zip").read_bytes()

    conversa = leitor.ler_arquivo("whatsapp_ios.zip", dados)

    assert [(m.autor, m.texto) for m in conversa.mensagens] == _mensagens_esperadas()


def test_txt_fora_do_zip_le_direto() -> None:
    dados = (_FIXTURES / "whatsapp_android.txt").read_bytes()

    conversa = leitor.ler_arquivo("conversa.txt", dados)

    assert [(m.autor, m.texto) for m in conversa.mensagens] == _mensagens_esperadas()


def test_grupo_tem_mais_de_dois_participantes() -> None:
    texto = "\n".join(
        [
            "[01/02/2026, 08:00:00] Joana Prado: oi pessoal",
            "[01/02/2026, 08:01:00] Caio Serra: oi!",
            "[01/02/2026, 08:02:00] Renata Alves: e aí",
        ]
    )

    conversa = leitor.ler_conversa(texto)

    assert len(conversa.participantes) == 3
