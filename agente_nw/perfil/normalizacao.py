from __future__ import annotations

import phonenumbers


def telefone_e164(bruto: str | None) -> str | None:
    if bruto is None or not bruto.strip():
        return None

    try:
        numero = phonenumbers.parse(bruto, "BR")
    except phonenumbers.NumberParseException:
        return None

    if not phonenumbers.is_valid_number(numero):
        return None

    return phonenumbers.format_number(numero, phonenumbers.PhoneNumberFormat.E164)
