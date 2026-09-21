from __future__ import annotations

import sqlite3
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from agente_nw.coleta.capturas import extrator, navegador
from agente_nw.coleta.capturas.extrator import ClienteExtracao
from agente_nw.coleta.capturas.navegador import Pagina
from agente_nw.nucleo.database.queries import fatos, redes_sociais
from agente_nw.nucleo.modelos.fato import Fato


@dataclass
class ResumoLeitura:
    perfil_id: int
    redes_lidas: int = 0
    redes_sem_sessao: int = 0
    blocos_capturados: int = 0
    fatos_gravados: int = 0
    motivos_sem_sessao: list[str] = field(default_factory=list)


def ler_redes_sociais_do_contato(
    cliente_llm: ClienteExtracao,
    conexao: sqlite3.Connection,
    perfil_id: int,
    abrir_pagina: Callable[[Path], Pagina],
    pasta_navegador: Path,
    agora: str,
    dorme: Callable[[float], None] = time.sleep,
    max_esperas_login: int = 36,
    espera_login_s: float = 5.0,
    max_rolagens: int = 5,
) -> ResumoLeitura:
    """Executa a leitura de todas as redes sociais cadastradas para um contato,
    um link por vez, e grava fatos para cada bloco extraído com sucesso.

    Ausência de sessão ativa numa rede não interrompe a leitura das demais —
    é registrada em `motivos_sem_sessao` e o fluxo continua. Os parâmetros
    `dorme`, `max_esperas_login`, `espera_login_s` e `max_rolagens` são passados
    para `navegador.ler`; produção usa os padrões (3 min de espera por login,
    5 rolagens); testes injetam valores curtos."""
    resumo = ResumoLeitura(perfil_id=perfil_id)
    lista = redes_sociais.listar_por_perfil(conexao, perfil_id)

    for rede in lista:
        pasta_rede = pasta_navegador / rede.rede
        pagina = abrir_pagina(pasta_rede)
        try:
            captura = navegador.ler(
                pagina,
                rede.link,
                dorme=dorme,
                max_esperas_login=max_esperas_login,
                espera_login_s=espera_login_s,
                max_rolagens=max_rolagens,
            )
        finally:
            pagina.fechar()

        if not captura.autenticado:
            resumo.redes_sem_sessao += 1
            resumo.motivos_sem_sessao.append(f"{rede.rede}: {captura.motivo}")
            continue

        resumo.redes_lidas += 1
        resumo.blocos_capturados += len(captura.blocos)

        for bloco in captura.blocos:
            extraido = extrator.extrair(cliente_llm, bloco, rede.rede)
            if extraido is None:
                continue
            fato = Fato(
                perfil_id=perfil_id,
                data_do_fato=extraido.data_do_fato,
                tipo=f"rede_social:{rede.rede}",
                conteudo=extraido.conteudo,
                fonte=rede.link,
                registrado_em=agora,
            )
            fatos.inserir(conexao, fato)
            resumo.fatos_gravados += 1

        conexao.commit()

    return resumo
