from __future__ import annotations

import sqlite3
from collections.abc import Callable

from agente_nw.coleta.capturas.busca import REDES_SUPORTADAS
from agente_nw.nucleo import localizacao as localizacao_mod
from agente_nw.nucleo import orquestracao
from agente_nw.nucleo.database.queries import listas as queries_listas
from agente_nw.nucleo.database.queries import rede_sem_perfil
from agente_nw.nucleo.modelos.localizacao import Localizacao, Opcao
from agente_nw.nucleo.orquestracao import Encaminhamento

_OPCOES_MOSTRADAS = 5
_POR_PAGINA = 20


class _SemPerfil:
    """O usuário declarou que o contato não tem conta nesta rede."""


_SEM_PERFIL = _SemPerfil()


def _descrever(opcao: Opcao) -> str:
    cabecalho = f" — {opcao.cabecalho}" if opcao.cabecalho else ""
    return f"{opcao.nome}{cabecalho} [{opcao.rede}] {opcao.link}"


def _escolher_na_lista(
    conexao: sqlite3.Connection,
    redes_preferidas: list[str],
    entrada: Callable[[str], str],
    saida: Callable[[str], None],
) -> Opcao | None:
    """Opção "l": mostra a lista inteira de uma rede, 20 por vez, com filtro por texto."""
    candidatas = dict.fromkeys([*redes_preferidas, *REDES_SUPORTADAS])
    com_lista = [r for r in candidatas if queries_listas.contar_por_rede(conexao, r) > 0]
    if not com_lista:
        saida("Nenhuma lista lida ainda. Rode: agente_nw listas atualizar")
        return None
    rede = com_lista[0]
    if len(com_lista) > 1:
        resposta = entrada(f"Rede [{'/'.join(com_lista)}] (Enter = {rede}): ").strip().lower()
        if resposta in com_lista:
            rede = resposta
    filtro = entrada("Filtro por nome, cargo ou empresa (Enter = tudo): ").strip()
    entradas = (
        queries_listas.filtrar_por_texto(conexao, rede, filtro)
        if filtro
        else queries_listas.listar_por_rede(conexao, rede)
    )
    if not entradas:
        saida("Nada encontrado com esse filtro.")
        return None

    for inicio in range(0, len(entradas), _POR_PAGINA):
        for numero, item in enumerate(entradas[inicio : inicio + _POR_PAGINA], start=inicio + 1):
            saida(f"  {numero}. {_descrever(localizacao_mod.opcao_da_entrada(item))}")
        restantes = len(entradas) - (inicio + _POR_PAGINA)
        sufixo = f" / Enter = mais ({restantes} restantes)" if restantes > 0 else ""
        resposta = entrada(f"número{sufixo} / q = voltar: ").strip().lower()
        if resposta == "q":
            return None
        if resposta.isdigit() and 1 <= int(resposta) <= len(entradas):
            return localizacao_mod.opcao_da_entrada(entradas[int(resposta) - 1])
    return None


def _menu(
    conexao: sqlite3.Connection,
    opcoes: list[Opcao],
    entrada: Callable[[str], str],
    saida: Callable[[str], None],
    permitir_sem_perfil: bool = False,
) -> Opcao | _SemPerfil | None:
    for numero, opcao in enumerate(opcoes, start=1):
        saida(f"  {numero}. {_descrever(opcao)}")
    redes = list(dict.fromkeys(o.rede for o in opcoes))
    sem_perfil = " / n = não tem perfil nesta rede" if permitir_sem_perfil else ""
    while True:
        pergunta = f"número / l = mostrar a lista / c = colar um link{sem_perfil} / p = pular: "
        resposta = entrada(pergunta).strip()
        baixa = resposta.lower()
        if baixa.isdigit() and 1 <= int(baixa) <= len(opcoes):
            return opcoes[int(baixa) - 1]
        if baixa == "p":
            return None
        if baixa == "n" and permitir_sem_perfil:
            return _SEM_PERFIL
        if baixa == "l":
            escolhida = _escolher_na_lista(conexao, redes, entrada, saida)
            if escolhida is not None:
                return escolhida
            continue
        link_colado = baixa.startswith(("http://", "https://", "www."))
        if link_colado or baixa == "c" or baixa.startswith("c "):
            if link_colado:
                link = resposta
            else:
                link = resposta[1:].strip() or entrada("Cole o link do perfil: ").strip()
            do_link = localizacao_mod.opcao_do_link(conexao, link)
            if do_link is None:
                saida("Link não reconhecido (aceito: linkedin, instagram, facebook, x).")
                continue
            return do_link
        saida("Opção inválida.")


def _pedir_link(
    conexao: sqlite3.Connection,
    rede: str | None,
    entrada: Callable[[str], str],
    saida: Callable[[str], None],
) -> Opcao | _SemPerfil | None:
    """Rede em que não apareceu ninguém: o usuário cola o perfil certo (o nome na conta pode ser
    outro), declara que não há perfil ali (n) ou decide depois (Enter)."""
    onde = f" em {rede}" if rede else ""
    saida(f"Não achei a pessoa{onde} nas suas listas nem na busca geral.")
    sem_perfil = ", n = não tem perfil nesta rede" if rede else ""
    while True:
        resposta = entrada(f"Cole o link do perfil{sem_perfil}, ou Enter para decidir depois: ").strip()
        if not resposta or resposta.lower() == "p":
            return None
        if resposta.lower() in ("n", "nao", "não") and rede:
            return _SEM_PERFIL
        do_link = localizacao_mod.opcao_do_link(conexao, resposta)
        if do_link is not None:
            return do_link
        saida("Link não reconhecido (aceito: linkedin, instagram, facebook, x).")


def conduzir(
    conexao: sqlite3.Connection,
    perfil_id: int,
    localizacao: Localizacao,
    agora: str,
    entrada: Callable[[str], str] = input,
    saida: Callable[[str], None] = print,
    sem_perguntar: bool = False,
    substituir: bool = False,
) -> Opcao | None:
    """Confirmação no terminal. Devolve a opção gravada no contato, ou None se o usuário pulou."""
    if localizacao.rede is not None:
        saida(f"\n=== Rede social: {localizacao.rede} ===")
    for aviso in localizacao.avisos:
        saida(f"AVISO: {aviso}")

    permitir = localizacao.rede is not None
    escolhida: Opcao | _SemPerfil | None = None
    encaminhamento = orquestracao.encaminhar_localizacao(localizacao, sem_perguntar)
    if encaminhamento is Encaminhamento.GRAVAR_ESCOLHIDO:
        escolhida = localizacao.escolhido
    elif encaminhamento is Encaminhamento.CONFIRMAR_ESCOLHIDO:
        assert localizacao.escolhido is not None
        saida(f"É esta pessoa? {_descrever(localizacao.escolhido)}")
        if entrada("[S/n] ").strip().lower() in ("", "s", "sim"):
            escolhida = localizacao.escolhido
        else:
            saida("Candidatos com esse nome:")
            escolhida = _menu(conexao, localizacao.opcoes, entrada, saida, permitir)
    elif encaminhamento is Encaminhamento.CONFIRMAR_UNICA:
        unica = localizacao.opcoes[0]
        if localizacao.status == "nenhum":
            saida("Não achei nas suas listas.")
            saida("A busca geral das redes trouxe:")
        saida(f"É esta pessoa? {_descrever(unica)}")
        resposta = entrada("[S/n/p = pular] ").strip().lower()
        if resposta in ("", "s", "sim", "1"):
            escolhida = unica
        elif resposta != "p":
            escolhida = _menu(conexao, [unica], entrada, saida, permitir)
    elif encaminhamento is Encaminhamento.PEDIR_LINK:
        escolhida = _pedir_link(conexao, localizacao.rede, entrada, saida)
    elif encaminhamento is Encaminhamento.ESCOLHER:
        if localizacao.status == "nenhum":
            saida("Não achei nas suas listas.")
            if localizacao.opcoes:
                saida("A busca geral das redes trouxe:")
        else:
            saida("Mais de uma pessoa combina:")
        mostradas = localizacao.opcoes[:_OPCOES_MOSTRADAS]
        escolhida = _menu(conexao, mostradas, entrada, saida, permitir)

    if isinstance(escolhida, _SemPerfil):
        assert localizacao.rede is not None
        rede_sem_perfil.declarar(conexao, perfil_id, localizacao.rede, agora)
        conexao.commit()
        saida(f"Registrado: sem perfil em {localizacao.rede}. Não procuro mais nessa rede.")
        return None
    if escolhida is None:
        saida("Sem rede social nesta consulta.")
        return None
    localizacao_mod.confirmar(conexao, perfil_id, escolhida, agora, substituir=substituir)
    saida(f"Gravado no contato: {escolhida.rede} {escolhida.link}")
    return escolhida
