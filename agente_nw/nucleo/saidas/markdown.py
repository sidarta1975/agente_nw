from __future__ import annotations

import re
import sqlite3

from agente_nw.nucleo.database.queries import assunto_contato, assuntos
from agente_nw.nucleo.modelos.assunto_contato import AssuntoContato
from agente_nw.nucleo.modelos.marcacao import Marcacao
from agente_nw.nucleo.modelos.perfil import Perfil

_LINHA_USEI = "- [ ] usei"
_LINHA_NAO_SERVE = (
    "- [ ] não serve → motivo: ( ) não interessa a ele ( ) velho ( ) raso "
    "( ) não dá conversa ( ) eu não domino"
)

_MOTIVOS: list[tuple[str, str]] = [
    ("não interessa a ele", "nao_interessa"),
    ("velho", "velho"),
    ("raso", "raso"),
    ("não dá conversa", "nao_da_conversa"),
    ("eu não domino", "nao_domino"),
]

_PADRAO_BLOCO = re.compile(r"<!-- ac:(\d+) -->")
_PADRAO_USEI = re.compile(r"-\s*\[x\]\s*usei", re.IGNORECASE)
_PADRAO_NAO_SERVE = re.compile(r"-\s*\[x\]\s*n[ãa]o serve", re.IGNORECASE)
_PADRAO_LINHA_NAO_SERVE = re.compile(r"n[ãa]o serve.*", re.IGNORECASE)
_PADRAO_PARENTESES = re.compile(r"\(([xX ]?)\)")


def _bloco_item(conexao: sqlite3.Connection, registro: AssuntoContato, com_cartao: bool) -> list[str]:
    assunto = assuntos.obter_por_id(conexao, registro.assunto_id)
    titulo = assunto.titulo_gerado if assunto is not None and assunto.titulo_gerado else "(sem título)"
    por_que = registro.por_que if registro.por_que is not None else "(não gerado)"

    linhas = [f"#### {titulo}  <!-- ac:{registro.id} -->", f"Por quê: {por_que}"]
    if com_cartao:
        cartao = assunto.resumo_cartao if assunto is not None and assunto.resumo_cartao else "(não gerado)"
        linhas.append(f"Cartão: {cartao}")
    linhas.append(_LINHA_USEI)
    linhas.append(_LINHA_NAO_SERVE)
    return linhas


def gerar(conexao: sqlite3.Connection, perfis_ativos: list[Perfil], data: str) -> str:
    linhas: list[str] = []

    for perfil in perfis_ativos:
        assert perfil.id is not None
        registros = [r for r in assunto_contato.listar_do_dia(conexao, perfil.id, data) if r.status == "novo"]
        if not registros:
            continue

        nome = perfil.apelido or perfil.nome
        linhas.append(f"## {nome}  <!-- perfil:{perfil.id} -->")

        conectores = [r for r in registros if r.tipo == "conector"]
        viaveis = [r for r in registros if r.tipo == "viavel_com_esforco"]

        if conectores:
            linhas.append("### Conectores")
            for registro in conectores:
                linhas.extend(_bloco_item(conexao, registro, com_cartao=False))

        if viaveis:
            linhas.append("### Viáveis com esforço")
            for registro in viaveis:
                linhas.extend(_bloco_item(conexao, registro, com_cartao=True))

    if not linhas:
        return "<!-- nenhuma sugestão hoje -->\n"

    return "\n".join(linhas) + "\n"


def _motivos_marcados(bloco: str) -> list[str]:
    match = _PADRAO_LINHA_NAO_SERVE.search(bloco)
    if match is None:
        return []
    marcadores = _PADRAO_PARENTESES.findall(match.group(0))
    return [
        codigo
        for marcador, (_texto, codigo) in zip(marcadores, _MOTIVOS, strict=False)
        if marcador.strip().lower() == "x"
    ]


def ler_marcacoes(texto: str) -> tuple[list[Marcacao], list[str]]:
    marcacoes: list[Marcacao] = []
    avisos: list[str] = []

    posicoes = list(_PADRAO_BLOCO.finditer(texto))
    for indice, match in enumerate(posicoes):
        ac_id = int(match.group(1))
        inicio = match.end()
        fim = posicoes[indice + 1].start() if indice + 1 < len(posicoes) else len(texto)
        bloco = texto[inicio:fim]

        if _PADRAO_USEI.search(bloco):
            marcacoes.append(Marcacao(ac_id=ac_id, resultado="usado", motivo=None))
            continue

        if _PADRAO_NAO_SERVE.search(bloco):
            motivos_marcados = _motivos_marcados(bloco)
            if len(motivos_marcados) != 1:
                avisos.append(f"bloco ac:{ac_id} marcado como não serve sem motivo claro")
                continue
            marcacoes.append(Marcacao(ac_id=ac_id, resultado="nao_serve", motivo=motivos_marcados[0]))
            continue

    return marcacoes, avisos
