from __future__ import annotations

import sqlite3
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from agente_nw.coleta.capturas import extrator, imagens, navegador
from agente_nw.coleta.capturas.extrator import ClienteExtracao
from agente_nw.coleta.capturas.navegador import Pagina
from agente_nw.nucleo import sensivel
from agente_nw.nucleo.database.queries import fatos, redes_sociais
from agente_nw.nucleo.modelos.fato import Fato


@dataclass
class ResumoLeitura:
    perfil_id: int
    redes_lidas: int = 0
    redes_sem_sessao: int = 0
    blocos_capturados: int = 0
    imagens_descritas: int = 0
    fatos_gravados: int = 0
    motivos_sem_sessao: list[str] = field(default_factory=list)


# Os primeiros blocos de uma página costumam ser menu e cabeçalho: o limite de `maximo_blocos` vale
# para publicações gravadas, e examino até este múltiplo de blocos para encontrá-las.
_BLOCOS_EXAMINADOS_POR_PUBLICACAO = 4


def url_de_leitura(rede: str, link: str) -> str:
    """No LinkedIn as publicações ficam na página de atividade, não no perfil (que traz experiência,
    formação e menu). Outras redes e links que já apontam para a atividade ficam como estão."""
    if rede == "linkedin" and "/in/" in link and "/recent-activity" not in link:
        return link.split("?")[0].rstrip("/") + "/recent-activity/all/"
    return link


def _descrever_imagens(
    cliente_llm: ClienteExtracao,
    conexao: sqlite3.Connection,
    perfil_id: int,
    rede: str,
    link_da_rede: str,
    capturadas: list[imagens.ImagemCapturada],
    agora: str,
    resumo: ResumoLeitura,
    avisar: Callable[[str], None] | None,
) -> None:
    """Cada imagem publicada vira um fato com a descrição (a imagem não é gravada). A publicação que já
    tem fato de imagem não é descrita de novo."""
    tipo = f"imagem:{rede}"
    for numero, imagem in enumerate(capturadas, start=1):
        fonte = imagem.link or link_da_rede
        if imagem.link and fatos.existe(conexao, perfil_id, tipo, fonte):
            continue
        if avisar is not None:
            avisar(f"  {rede}: imagem {numero}/{len(capturadas)}")
        descricao = imagens.descrever(cliente_llm, imagem, rede)
        if descricao is None:
            continue
        legenda = f" (texto alternativo na rede: {imagem.alt})" if imagem.alt.strip() else ""
        fato = Fato(
            perfil_id=perfil_id,
            tipo=tipo,
            conteudo=f"Imagem publicada: {descricao}{legenda}",
            fonte=fonte,
            registrado_em=agora,
        )
        fatos.inserir(conexao, fato)
        resumo.imagens_descritas += 1
        resumo.fatos_gravados += 1


def ler_redes_sociais_do_contato(
    cliente_llm: ClienteExtracao,
    conexao: sqlite3.Connection,
    perfil_id: int,
    abrir_pagina: Callable[[Path], Pagina],
    pasta_navegador: Path,
    agora: str,
    dorme: Callable[[float], None] = time.sleep,
    max_esperas_login: int = 0,
    espera_login_s: float = 5.0,
    max_rolagens: int = 5,
    maximo_blocos: int | None = None,
    avisar: Callable[[str], None] | None = None,
    maximo_imagens: int = 0,
    largura_minima_imagem: int = 250,
) -> ResumoLeitura:
    """Executa a leitura de todas as redes sociais cadastradas para um contato,
    um link por vez, e grava fatos para cada bloco extraído com sucesso.

    Ausência de sessão ativa numa rede não interrompe a leitura das demais —
    é registrada em `motivos_sem_sessao` e o fluxo continua. Os parâmetros
    `dorme`, `max_esperas_login`, `espera_login_s` e `max_rolagens` são passados
    para `navegador.ler`; produção usa os padrões (sem espera de login — a sessão é a
    do Chrome do usuário —, 5 rolagens); testes injetam valores curtos. `maximo_blocos`
    limita as publicações gravadas por rede (examina os primeiros blocos, que são os mais recentes);
    `avisar` recebe uma linha de progresso por rede e por bloco."""
    resumo = ResumoLeitura(perfil_id=perfil_id)
    lista = redes_sociais.listar_por_perfil(conexao, perfil_id)

    for rede in lista:
        pasta_rede = pasta_navegador / rede.rede
        pagina = abrir_pagina(pasta_rede)
        try:
            captura = navegador.ler(
                pagina,
                url_de_leitura(rede.rede, rede.link),
                dorme=dorme,
                max_esperas_login=max_esperas_login,
                espera_login_s=espera_login_s,
                max_rolagens=max_rolagens,
                maximo_imagens=maximo_imagens,
                largura_minima_imagem=largura_minima_imagem,
            )
        finally:
            pagina.fechar()
        aviso_imagens = getattr(pagina, "aviso_imagens", None)
        if aviso_imagens and avisar is not None:
            avisar(f"AVISO: {rede.rede}: a extensão não leu as imagens ({aviso_imagens}). Recarregue-a.")

        if not captura.autenticado:
            resumo.redes_sem_sessao += 1
            resumo.motivos_sem_sessao.append(f"{rede.rede}: {captura.motivo}")
            continue

        resumo.redes_lidas += 1
        resumo.blocos_capturados += len(captura.blocos)

        blocos = (
            captura.blocos
            if maximo_blocos is None
            else captura.blocos[: maximo_blocos * _BLOCOS_EXAMINADOS_POR_PUBLICACAO]
        )
        if avisar is not None:
            avisar(f"{rede.rede}: {len(captura.blocos)} blocos na página; examino até {len(blocos)}...")
        gravados_na_rede = 0
        sensiveis = 0
        descartados = 0
        for numero, bloco in enumerate(blocos, start=1):
            if maximo_blocos is not None and gravados_na_rede >= maximo_blocos:
                break
            if avisar is not None:
                avisar(f"  {rede.rede}: bloco {numero}/{len(blocos)}")
            if sensivel.verificar(bloco) is not None:
                sensiveis += 1
                continue  # categoria sensível: o texto integral nunca chega ao banco
            extraido = extrator.extrair(cliente_llm, bloco, rede.rede)
            if extraido is None:
                descartados += 1
                continue
            fato = Fato(
                perfil_id=perfil_id,
                data_do_fato=extraido.data_do_fato,
                tipo=f"rede_social:{rede.rede}",
                conteudo=bloco,  # texto integral da publicação: texto de fonte externa não se altera
                fonte=rede.link,
                registrado_em=agora,
            )
            fatos.inserir(conexao, fato)
            resumo.fatos_gravados += 1
            gravados_na_rede += 1

        if avisar is not None and (sensiveis or descartados):
            avisar(
                f"{rede.rede}: {sensiveis} bloco(s) barrados pelo filtro sensível e {descartados} "
                f"descartados pelo modelo (interface ou sem publicação)"
            )
        _descrever_imagens(
            cliente_llm, conexao, perfil_id, rede.rede, rede.link, captura.imagens, agora, resumo, avisar
        )
        conexao.commit()

    return resumo
