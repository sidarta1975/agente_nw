from __future__ import annotations

import sqlite3
from collections.abc import Callable

from agente_nw.coleta.capturas.busca import REDES_SUPORTADAS
from agente_nw.nucleo import localizacao as localizacao_mod
from agente_nw.nucleo.database.queries import listas as queries_listas
from agente_nw.nucleo.modelos.localizacao import Localizacao, Opcao

_OPCOES_MOSTRADAS = 5
_POR_PAGINA = 20


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
) -> Opcao | None:
    for numero, opcao in enumerate(opcoes, start=1):
        saida(f"  {numero}. {_descrever(opcao)}")
    redes = list(dict.fromkeys(o.rede for o in opcoes))
    while True:
        resposta = entrada("número / l = mostrar a lista / c = colar um link / p = pular: ").strip()
        baixa = resposta.lower()
        if baixa.isdigit() and 1 <= int(baixa) <= len(opcoes):
            return opcoes[int(baixa) - 1]
        if baixa == "p":
            return None
        if baixa == "l":
            escolhida = _escolher_na_lista(conexao, redes, entrada, saida)
            if escolhida is not None:
                return escolhida
            continue
        if baixa == "c" or baixa.startswith("c "):
            link = resposta[1:].strip() or entrada("Cole o link do perfil: ").strip()
            do_link = localizacao_mod.opcao_do_link(conexao, link)
            if do_link is None:
                saida("Link não reconhecido (aceito: linkedin, instagram, facebook, x).")
                continue
            return do_link
        saida("Opção inválida.")


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
    for aviso in localizacao.avisos:
        saida(f"AVISO: {aviso}")

    escolhida: Opcao | None = None
    if localizacao.status == "claro" and localizacao.escolhido is not None:
        if sem_perguntar:
            escolhida = localizacao.escolhido
        else:
            saida(f"É esta pessoa? {_descrever(localizacao.escolhido)}")
            if entrada("[S/n] ").strip().lower() in ("", "s", "sim"):
                escolhida = localizacao.escolhido
            else:
                saida("Candidatos com esse nome:")
                escolhida = _menu(conexao, localizacao.opcoes, entrada, saida)
    elif not sem_perguntar:
        if localizacao.status == "nenhum":
            saida("Não achei nas suas listas.")
            if localizacao.opcoes:
                saida("A busca geral das redes trouxe:")
        else:
            saida("Mais de uma pessoa combina:")
        mostradas = localizacao.opcoes[:_OPCOES_MOSTRADAS]
        escolhida = _menu(conexao, mostradas, entrada, saida)

    if escolhida is None:
        saida("Sem rede social nesta consulta.")
        return None
    localizacao_mod.confirmar(conexao, perfil_id, escolhida, agora, substituir=substituir)
    saida(f"Gravado no contato: {escolhida.rede} {escolhida.link}")
    return escolhida
