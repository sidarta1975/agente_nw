from __future__ import annotations

import threading
from typing import Any

from agente_nw.perfil.importador import ContatoBruto


def solicitar_permissao() -> bool:
    from Contacts import (
        CNAuthorizationStatusAuthorized,
        CNAuthorizationStatusDenied,
        CNAuthorizationStatusRestricted,
        CNContactStore,
        CNEntityTypeContacts,
    )

    store = CNContactStore.alloc().init()
    status = CNContactStore.authorizationStatusForEntityType_(CNEntityTypeContacts)

    if status == CNAuthorizationStatusAuthorized:
        return True
    if status in (CNAuthorizationStatusDenied, CNAuthorizationStatusRestricted):
        return False

    concedida = False
    evento = threading.Event()

    def callback(granted: bool, error: Any) -> None:
        nonlocal concedida
        concedida = bool(granted)
        evento.set()

    store.requestAccessForEntityType_completionHandler_(CNEntityTypeContacts, callback)
    evento.wait()
    return concedida


def ler_contatos() -> list[ContatoBruto]:
    from Contacts import (
        CNContactEmailAddressesKey,
        CNContactFamilyNameKey,
        CNContactFetchRequest,
        CNContactGivenNameKey,
        CNContactJobTitleKey,
        CNContactNoteKey,
        CNContactOrganizationNameKey,
        CNContactPhoneNumbersKey,
        CNContactStore,
    )

    store = CNContactStore.alloc().init()
    chaves_principais = [
        CNContactGivenNameKey,
        CNContactFamilyNameKey,
        CNContactOrganizationNameKey,
        CNContactJobTitleKey,
        CNContactPhoneNumbersKey,
        CNContactEmailAddressesKey,
    ]
    pedido = CNContactFetchRequest.alloc().initWithKeysToFetch_(chaves_principais)

    contatos: list[ContatoBruto] = []
    notas_nao_lidas = 0

    def processar(contato: Any, _parar: Any) -> None:
        nonlocal notas_nao_lidas
        nome = f"{contato.givenName()} {contato.familyName()}".strip()
        telefones = [
            valor.value().stringValue() for valor in contato.phoneNumbers() if valor.value() is not None
        ]
        emails = [str(valor.value()) for valor in contato.emailAddresses() if valor.value() is not None]
        empresa = str(contato.organizationName()) or None
        cargo = str(contato.jobTitle()) or None

        nota = None
        try:
            completo, erro = store.unifiedContactWithIdentifier_keysToFetch_error_(
                contato.identifier(), [CNContactNoteKey], None
            )
            if erro is None and completo is not None:
                texto_nota = str(completo.note())
                nota = texto_nota if texto_nota else None
            else:
                notas_nao_lidas += 1
        except Exception:
            notas_nao_lidas += 1

        contatos.append(
            ContatoBruto(
                nome=nome if nome else (telefones[0] if telefones else (emails[0] if emails else "")),
                telefone=telefones[0] if telefones else None,
                email=emails[0] if emails else None,
                empresa=empresa,
                cargo=cargo,
                notas=nota,
            )
        )

    sucesso, erro = store.enumerateContactsWithFetchRequest_error_usingBlock_(pedido, None, processar)
    if not sucesso:
        raise RuntimeError(f"não foi possível ler a agenda do macOS: {erro}")

    if notas_nao_lidas:
        print(f"AVISO: {notas_nao_lidas} nota(s) não puderam ser lidas (restrição do macOS).")

    return contatos
